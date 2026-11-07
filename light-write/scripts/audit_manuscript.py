"""Read-only checks of a declared manuscript packet, never a scientific review.

Exit 0: listed checks passed, possibly with unresolved-claim warnings.
Exit 1: file drift or a declared text/evidence link failed.
Exit 2: malformed packet. No network, drafting, execution, or file writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


class PacketError(ValueError):
    pass


def need(test, message):
    if not test:
        raise PacketError(message)


def obj(value, where):
    need(isinstance(value, dict), where + ': expected object')
    return value


def text(value, where):
    need(isinstance(value, str) and bool(value.strip()), where + ': expected nonempty text')
    return value


def rows(value, where):
    need(isinstance(value, list), where + ': expected array')
    return value


def unique_keys(pairs):
    value = {}
    for key, child in pairs:
        need(key not in value, 'Duplicate JSON key: ' + key)
        value[key] = child
    return value


def reject_constant(value):
    raise PacketError('Non-JSON numeric constant: ' + value)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_keys,
                      parse_constant=reject_constant)


def file_ref(row, where, base):
    obj(row, where)
    path = text(row.get('path'), where + '.path')
    need(chr(0) not in path, where + ': invalid path')
    digest = text(row.get('sha256'), where + '.sha256')
    need(bool(re.fullmatch('[0-9a-f]{64}', digest)), where + ': invalid SHA-256')
    try:
        return (base / path).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise PacketError(where + ': cannot resolve file path') from error


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def audit(packet, packet_dir):
    packet = obj(packet, 'packet')
    need(packet.get('schema_version') == '1.0', 'schema_version: expected 1.0')
    text(packet.get('basis'), 'basis')
    need(packet_dir is not None, 'packet_dir is required; no unchecked file pass')
    base = Path(packet_dir).resolve()
    manuscript = obj(packet.get('manuscript'), 'manuscript')
    for field in ('paper_id', 'revision'):
        text(manuscript.get(field), 'manuscript.' + field)
    draft_path = file_ref(manuscript, 'manuscript', base)
    errors, warnings, sources, files = [], [], {}, []
    for i, source in enumerate(rows(packet.get('sources'), 'sources')):
        source = obj(source, f'sources[{i}]')
        sid = text(source.get('id'), f'sources[{i}].id')
        need(sid not in sources, 'Duplicate source ID: ' + sid)
        text(source.get('role'), f'source {sid}.role')
        path = file_ref(source, f'source {sid}', base)
        need(path != draft_path, 'A manuscript cannot be its own evidence source: ' + sid)
        sources[sid] = (source, path)
    if not sources:
        warnings.append('No local research sources bound; basis must describe message-only material and its limits.')

    def checked(row, path, label):
        try:
            if not path.is_file():
                raise OSError('not a regular file')
            matched = sha256(path) == row['sha256']
            if not matched:
                errors.append(label + ': changed file')
            files.append({'label': label, 'path': str(path), 'matched': matched})
            return matched
        except (OSError, ValueError) as error:
            errors.append(label + ': unavailable file (' + type(error).__name__ + ')')
            files.append({'label': label, 'path': str(path), 'matched': False})
            return False

    draft_ok = checked(manuscript, draft_path, 'manuscript')
    for sid, (source, path) in sources.items():
        checked(source, path, 'source ' + sid)

    cache = {}
    def content(path, label):
        if path not in cache:
            try:
                cache[path] = path.read_text(encoding='utf-8-sig')
            except (OSError, UnicodeError):
                errors.append(label + ': text check requires readable UTF-8 text')
                cache[path] = None
        return cache[path]

    claim_ids, unresolved = set(), []
    for i, claim in enumerate(rows(packet.get('claims', []), 'claims')):
        claim = obj(claim, f'claims[{i}]')
        cid = text(claim.get('id'), f'claims[{i}].id')
        need(cid not in claim_ids, 'Duplicate claim ID: ' + cid)
        claim_ids.add(cid)
        anchor = text(claim.get('anchor'), f'claim {cid}.anchor')
        status = text(claim.get('status'), f'claim {cid}.status')
        need(status in {'supported', 'interpretation', 'planned', 'needs_evidence', 'disputed'},
             'Invalid claim status: ' + cid)
        text(claim.get('boundary'), f'claim {cid}.boundary')
        evidence = rows(claim.get('evidence'), f'claim {cid}.evidence')
        if status in {'supported', 'interpretation'}:
            need(bool(evidence), f'claim {cid}: supporting source references are required')
        for item in evidence:
            item = obj(item, f'claim {cid}.evidence item')
            sid = text(item.get('source_id'), f'claim {cid}.source_id')
            need(sid in sources, f'claim {cid}: unknown source {sid}')
            text(item.get('locator'), f'claim {cid}.locator')
        if draft_ok:
            body = content(draft_path, 'manuscript')
            if body is not None and anchor not in body:
                errors.append(f'claim {cid}: anchor absent from manuscript')
        if status in {'planned', 'needs_evidence', 'disputed'}:
            unresolved.append(cid)
    if not claim_ids:
        warnings.append('No claim anchors declared; no evidence-to-prose link was checked.')
    if unresolved:
        warnings.append('Claims require author/scientific review: ' + ', '.join(unresolved))

    for i, item in enumerate(rows(packet.get('protected_literals', []), 'protected_literals')):
        item = obj(item, f'protected_literals[{i}]')
        sid = text(item.get('source_id'), f'protected_literals[{i}].source_id')
        need(sid in sources, f'protected_literals[{i}]: unknown source {sid}')
        literal = text(item.get('text'), f'protected_literals[{i}].text')
        source_text = content(sources[sid][1], 'source ' + sid)
        body = content(draft_path, 'manuscript') if draft_ok else None
        if source_text is not None and literal not in source_text:
            errors.append(f'protected_literals[{i}]: literal absent from cited source')
        if body is not None and literal not in body:
            errors.append(f'protected_literals[{i}]: literal absent from manuscript')

    parent = packet.get('parent')
    if parent is not None:
        parent_path = file_ref(parent, 'parent', base)
        need(parent_path != draft_path, 'Parent must be a prior packet, not the manuscript')
        if checked(parent, parent_path, 'parent'):
            previous = obj(read_json(parent_path), 'parent packet')
            need(previous.get('schema_version') == '1.0', 'Unsupported parent packet version')
            prior = obj(previous.get('manuscript'), 'parent manuscript')
            text(prior.get('paper_id'), 'parent manuscript.paper_id')
            text(prior.get('revision'), 'parent manuscript.revision')
            need(prior.get('paper_id') == manuscript['paper_id'], 'Parent belongs to another paper')
            need(prior.get('revision') != manuscript['revision'], 'Revision must differ from parent')
            # Historical inputs may legitimately be stale; never re-audit or rewrite them.
    return {'checks_passed': not errors, 'paper_id': manuscript['paper_id'],
            'revision': manuscript['revision'], 'errors': errors, 'warnings': warnings,
            'files': files, 'claim_count': len(claim_ids), 'unresolved_claims': unresolved,
            'boundary': 'Only listed file bytes, declared anchors and literal presence. No semantic, scientific, citation, visual, permission or submission-readiness certification.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path, help='Local UTF-8 manuscript packet JSON')
    args = parser.parse_args(argv)
    try:
        result = audit(read_json(args.packet), args.packet.resolve().parent)
        status = 0 if result['checks_passed'] else 1
    except (OSError, ValueError, UnicodeError, RecursionError, RuntimeError) as error:
        result, status = {'checks_passed': False, 'errors': [str(error)]}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
