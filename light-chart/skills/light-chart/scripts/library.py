"""Rank shipped implementations and route scientific tasks to usable resources."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent


def _index():
    entries = []
    for name in ('catalog.json', 'capabilities.json', 'implementations.json', 'domain-layouts.json'):
        path = ROOT / 'assets/library' / name
        if path.exists():
            entries.extend(json.loads(path.read_text(encoding='utf-8'))['entries'])
    return entries


def _vocabulary():
    return json.loads((ROOT / 'assets/library/implementations.json').read_text(encoding='utf-8'))['concepts']


def _contains(text, term):
    if re.search(r'[\u4e00-\u9fff]', term):
        return term.casefold() in text.casefold()
    return re.search(r'(?<![a-z0-9_])' + re.escape(term.casefold()) + r'(?![a-z0-9_])', text.casefold()) is not None


def concepts_for(query):
    concepts=[key for key, aliases in _vocabulary().items()
              if any(_contains(query, term) for term in [key, *aliases])]
    # A specific matrix name does not additionally request an arbitrary matrix.
    for narrow in ('confusion-counts', 'expression-heatmap'):
        if narrow in concepts and 'heatmap' in concepts:
            remainder = query
            for term in [narrow, *_vocabulary()[narrow]]:
                remainder = re.sub(re.escape(term), '', remainder, flags=re.IGNORECASE)
            if not any(_contains(remainder, t) for t in ['heatmap', *_vocabulary()['heatmap']]):
                concepts.remove('heatmap')
    if 'survival' in concepts and 'table' in concepts and re.search(r'(?i)risk table|风险表',query):
        if not re.search(r'(?i)latex|booktabs|论文表格|数值表',query):
            concepts.remove('table')
    return concepts


def _body(row):
    path = ROOT / row['path']
    if path.suffix.lower() in {'.md', '.py', '.r'}:
        return path.read_text(encoding='utf-8', errors='replace')
    return ''


def _symbols(row):
    """Declared callable identifiers, including legacy slash-separated entries."""
    values = row.get('symbols')
    if values is None:
        values = re.split(r'\s*/\s*', row.get('symbol', ''))
    return [s for s in values if isinstance(s, str) and re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', s)]


def _requests_symbol(task, symbol):
    return re.search(r'(?<![\w.])'+re.escape(symbol)+r'(?![\w.])', task) is not None


def _visual_relevance(row, query, terms):
    """Rank observed reference structure, without adding callable coverage."""
    aliases = row.get('domain_aliases', [])
    domain = [alias for alias in aliases if _contains(query, alias)]
    # A recognized chart concept must not suppress a requested scientific domain
    # or evidence role. The bounded bonus applies only to visual references.
    metadata = ' '.join(str(row.get(k, '')) for k in
                        ('title', 'tags', 'question', 'evidence_roles', 'layout', 'search_terms'))
    stop = {'a', 'an', 'and', 'at', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with'}
    lexical = [t for t in terms if len(t) > 1 and t not in stop and _contains(metadata, t)]
    score = (32 if domain else 0) + min(24, 4 * len(lexical))
    requested_counterexample = any(_contains(query, t) for t in ('counterexample', '反例'))
    if row.get('reference_role') == 'counterexample' and not requested_counterexample:
        score -= 16
    return score, list(dict.fromkeys([*domain, *lexical]))


def search(query='', kind=None, backend=None, limit=12):
    if limit < 1:
        raise ValueError('limit must be positive')
    vocabulary = _vocabulary()
    concepts = concepts_for(query)
    terms = re.findall(r'[a-z0-9_+-]+|[\u4e00-\u9fff]+', query.casefold())
    hits = []
    for row in _index():
        if kind and row['kind'] != kind:
            continue
        if backend and row.get('backend', 'any') not in {backend, 'any'}:
            continue
        metadata = ' '.join(str(row.get(k, '')) for k in ('id', 'title', 'tags', 'path', 'notes', 'symbol', 'symbols'))
        explicit = set(row.get('concepts', []))
        matched = [c for c in concepts if c in explicit or any(
            _contains(metadata, a) for a in [c, *vocabulary[c]])]
        score = sum(45 if c in explicit else 12 for c in matched)
        if concepts and not matched:
            body = _body(row)
            matched = [c for c in concepts if any(_contains(body, a) for a in [c, *vocabulary[c]])]
            score = len(matched) * 2
        elif not concepts and terms:
            direct = [t for t in terms if _contains(metadata, t)]
            if not direct:
                direct = [t for t in terms if _contains(_body(row), t)]
                score = len(direct)
            else:
                score = len(direct) * 10
            matched = direct
        if row['kind'] == 'visual-reference':
            bonus, visual_matches = _visual_relevance(row, query, terms)
            score += bonus
            matched = list(dict.fromkeys([*matched, *visual_matches]))
            if row.get('reference_role') == 'counterexample' and not any(
                    _contains(query, t) for t in ('counterexample', '反例')):
                # A densely tagged failed draft must not outrank a useful
                # positive merely because it mentions more chart concepts.
                score = min(score, 8)
        if terms and not matched:
            continue
        if row['kind'] == 'implementation' and score >= 12:
            score += 20
        if query and _contains(row['title'], query.strip()):
            score += 10
        path = ROOT / row['path']
        if not path.is_file():
            raise FileNotFoundError(path)
        hit = {**row, 'absolute_path': str(path),
               'match': {'score': score, 'concepts': matched}}
        if row['kind'] == 'visual-reference':
            preview = ROOT / row['preview'] if row.get('preview') else None
            if preview is not None and not preview.is_file():
                raise FileNotFoundError(preview)
            hit['absolute_preview_path'] = str(preview) if preview is not None else None
        hits.append((score, hit))
    hits.sort(key=lambda pair: (-pair[0], pair[1]['id']))
    return [row for _, row in hits[:limit]]


def route(task, backend=None, limit=8):
    """Resolve all requested concepts before applying a display limit.

    Full-text matches help discover source material, but cannot certify a
    callable implementation. A callable covers only its declared concepts (or
    an explicitly requested function symbol). ``limit`` is a soft display limit:
    the smallest set needed to cover requested concepts is never truncated.
    """
    if limit < 1:
        raise ValueError('limit must be positive')
    if not isinstance(task, str):
        raise TypeError('task must be text')
    if backend is None:
        # A named language takes priority over a style/library mention. A lone
        # statistical r (Pearson r, adjusted R2, etc.) is not an R instruction.
        if _contains(task, 'python'):
            backend='python'
        elif re.search(r'(?i)(?:\b(?:in|using|with)\s+R\b|\bR\s+(?:language|code|script|ggplot|heatmap|plot)\b|(?:用|使用)\s*R(?![a-z0-9_])|(?<![a-z0-9_])R\s*语言)', task) or re.match(r'(?i)^\s*R(?:$|\s|:|：|语言|绘图)', task):
            backend='r'
        elif re.search(r'(?i)matplotlib|seaborn',task):
            backend='python'
        elif re.search(r'(?i)ggplot|ComplexHeatmap',task):
            backend='r'
    concepts=concepts_for(task)
    # Retrieval limits must not change the statement of scientific capability.
    hits = search(task, backend=backend, limit=max(1, len(_index()))) if task.strip() else []
    # Symbols are matched only against explicit declarations, never file text.
    declared_symbol_rows = [r for r in _index() if r['kind'] == 'implementation' and r.get('status') == 'callable'
                           and any(_requests_symbol(task, s) for s in _symbols(r))]
    symbol_rows = [r for r in declared_symbol_rows if not backend or r.get('backend', 'any') in {backend, 'any'}]
    hit_ids = {r['id'] for r in hits}
    hits.extend({**r, 'absolute_path': str(ROOT / r['path'])} for r in symbol_rows if r['id'] not in hit_ids)
    requested_symbols = list(dict.fromkeys(s for r in declared_symbol_rows for s in _symbols(r) if _requests_symbol(task, s)))
    available = [r for r in hits if r['kind'] == 'implementation' and r.get('status') == 'callable' and (
        set(r.get('concepts', [])) & set(concepts) or
        any(_requests_symbol(task, s) for s in _symbols(r)))]
    implementations, chosen = [], set()
    for concept in concepts:
        match=next((r for r in available if concept in r.get('concepts', [])), None)
        if match is not None and match['id'] not in chosen:
            implementations.append(match); chosen.add(match['id'])
    for symbol in requested_symbols:
        match = next((r for r in available if symbol in _symbols(r)), None)
        if match is not None and match['id'] not in chosen:
            implementations.append(match); chosen.add(match['id'])
    for row in available:
        if len(implementations) >= max(limit, len(chosen)):
            break
        if row['id'] not in chosen:
            implementations.append(row); chosen.add(row['id'])
    # A symbol query has no vocabulary concept and still resolves directly.
    if not implementations and available:
        implementations=available[:limit]
    references, seen = [], set()
    for row in implementations:
        for ref in row.get('sources', []):
            if ref['path'] in seen:
                continue
            if not (ROOT / ref['path']).is_file():
                raise FileNotFoundError(ref['path'])
            seen.add(ref['path'])
            references.append({**ref, 'absolute_path': str(ROOT / ref['path'])})
    covered=set().union(*(set(r.get('concepts',[])) for r in available))
    unsupported=[c for c in concepts if c not in covered]
    missing_symbols=[s for s in requested_symbols if not any(s in _symbols(r) for r in available)]
    return {'task': task, 'backend': backend, 'concepts': concepts,
            'requested_symbols': requested_symbols,
            'symbol_coverage': {s:[r['id'] for r in available if s in _symbols(r)] for s in requested_symbols},
            'unimplemented_symbols': missing_symbols,
            'entrypoints': implementations,
            'related': [r for r in hits if r['kind'] != 'implementation' or r.get('status') != 'callable'][:limit],
            'source_routes': references,
            'unimplemented_concepts': unsupported,
            'concept_coverage': {c: {'status': 'callable' if c in covered else 'adaptation_required',
                'entrypoint_ids': [r['id'] for r in available if c in r.get('concepts', [])]}
                for c in concepts},
            'display_limit': limit,
            'limit_exceeded_for_coverage': len(implementations) > limit,
            'decision_boundary': 'Read actual inputs/reference before choosing; resources are not scientific validation.',
            'status': ('partial_implementation' if unsupported or missing_symbols else 'implementation_found') if implementations else
                'adaptation_required' if hits or requested_symbols else 'no_match'}


def plan(source, spec, backend=None, *, sources=None, profile=None):
    """Resolve data semantics before retrieving a construction's implementation."""
    from chart_plan import plan_chart
    result = plan_chart(source, spec, sources=sources, profile=profile)
    backend = backend or spec.get('backend')
    for candidate in result['candidates']:
        chosen_backend = backend or candidate.get('backend')
        resources = route(candidate['query'], backend=chosen_backend)
        if chosen_backend is None:
            actual = {r.get('backend') for r in resources['entrypoints']} & {'python','r'}
            # Use the real callable's backend. Where both are available, the
            # normal Python default is a choice, never a substitute for an
            # explicitly requested native R implementation.
            chosen_backend = 'python' if 'python' in actual else 'r' if 'r' in actual else None
            if chosen_backend:
                resources = route(candidate['query'], backend=chosen_backend)
        if chosen_backend:
            candidate['backend'] = chosen_backend
        candidate['resources'] = resources
    result['backend'] = backend or (result.get('recommended') or {}).get('backend')
    return result


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['search', 'list', 'route', 'plan'])
    parser.add_argument('--query', default='')
    parser.add_argument('--kind', choices=['source-pattern', 'reference', 'visual-reference', 'workflow', 'implementation'])
    parser.add_argument('--backend', choices=['python', 'r'])
    parser.add_argument('--limit', type=int, default=12)
    parser.add_argument('--data', help='Actual CSV/TSV/XLSX for plan')
    parser.add_argument('--spec', help='JSON declaring intent and column roles for plan')
    parser.add_argument('--out', help='Save the JSON decision')
    args = parser.parse_args()
    if args.command == 'plan':
        if not args.data or not args.spec:
            parser.error('plan requires --data and --spec')
        result = plan(args.data, json.loads(Path(args.spec).read_text(encoding='utf-8')), args.backend)
    else:
        result = route(args.query, args.backend, args.limit) if args.command == 'route' else search(
            args.query, args.kind, args.backend, args.limit)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload+'\n', encoding='utf-8')
    print(payload)


if __name__ == '__main__':
    main()
