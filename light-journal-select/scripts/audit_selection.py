#!/usr/bin/env python3
"""Audit a local journal-selection evidence packet; no network or ranking.

Exit 0: coherent packet. Exit 1: a recommended candidate lacks required evidence
or fails a gate. Exit 2: unreadable or structurally invalid packet.
Source classifications and factual assertions are supplied by the researcher;
this program cannot verify their truth or manuscript-journal similarity.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys


class PacketError(ValueError):
    """A packet is not valid input for this audit."""


SOURCE_KINDS = {
    "official_journal", "official_index", "official_policy", "primary_article",
    "metadata", "author_input", "secondary",
}
FACET_KINDS = {
    "identity": {"official_journal", "official_index"},
    "scope": {"official_journal", "official_policy"},
    "article_type": {"official_journal", "official_policy"},
}
CHECK_KINDS = {
    'indexing': {'official_index'},
    'metric': {'official_index', 'official_policy'},
    'fees': {'official_journal', 'official_policy', 'author_input'},
    'open_access': {'official_journal', 'official_policy', 'author_input'},
    'deadline': {'official_journal', 'official_policy', 'author_input'},
    'other': None,
}


def need(condition, message):
    if not condition:
        raise PacketError(message)


def obj(value, where):
    need(isinstance(value, dict), f"{where}: expected an object")
    return value


def array(value, where):
    need(isinstance(value, list), f"{where}: expected an array")
    return value


def text_value(value, where):
    need(isinstance(value, str) and bool(value.strip()), f"{where}: expected nonempty text")
    return value


def choice(value, allowed, where):
    need(isinstance(value, str) and value in allowed,
         f"{where}: expected one of {', '.join(sorted(allowed))}")
    return value


def iso_date(value, where):
    text_value(value, where)
    need(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)), f"{where}: use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PacketError(f"{where}: invalid date") from exc


def index_rows(rows, where):
    indexed = {}
    for i, row in enumerate(array(rows, where)):
        row = obj(row, f"{where}[{i}]")
        key = text_value(row.get("id"), f"{where}[{i}].id")
        need(key not in indexed, f"{where}: duplicate id {key}")
        indexed[key] = row
    return indexed


def references(row, sources, where, required=False, kinds=None):
    ids = array(row.get("source_ids", []), f"{where}.source_ids")
    for source_id in ids:
        text_value(source_id, f"{where}.source_ids item")
        need(source_id in sources, f"{where}: unknown source id {source_id}")
    need(len(ids) == len(set(ids)), f"{where}: duplicate source references")
    if required:
        need(bool(ids), f"{where}: source evidence is required")
    if required and kinds:
        need(any(sources[s]["kind"] in kinds for s in ids),
             f"{where}: requires source kind in {', '.join(sorted(kinds))}")
    return ids


def bound_references(row, sources, where, candidate_id, target, *, required=False,
                     kinds=None, article_type=False, route=False):
    """Check declared applicability, not whether a webpage truly supports it."""
    ids = references(row, sources, where, required=required, kinds=kinds)
    for sid in ids:
        def applies(binding):
            if binding['candidate_id'] != candidate_id:
                return False
            for field, mandatory in (('article_type', article_type), ('publication_route', route)):
                if mandatory and field not in binding:
                    return False
                if field in binding and binding[field] != target[field]:
                    return False
            return True
        need(any(applies(b) for b in sources[sid]['applies_to']),
             f'{where}: source {sid} applicability does not cover this candidate/type/route')


def validate_modern_context(packet, candidates):
    research = obj(packet.get('research'), 'research')
    text_value(research.get('basis'), 'research.basis')
    seen = set()
    for i, item in enumerate(array(research.get('inputs'), 'research.inputs')):
        where = f'research.inputs[{i}]'
        item = obj(item, where)
        path = text_value(item.get('path'), where + '.path')
        need(chr(0) not in path, where + ': invalid path')
        need(path not in seen, where + ': duplicate input path')
        seen.add(path)
        digest = text_value(item.get('sha256'), where + '.sha256')
        need(bool(re.fullmatch('[0-9a-f]{64}', digest)), where + ': invalid SHA-256')
    decision = obj(packet.get('decision'), 'decision')
    status = choice(decision.get('status'), {'proposed', 'author_selected', 'delegated', 'unselected'}, 'decision.status')
    text_value(decision.get('basis'), 'decision.basis')
    target_id = decision.get('target_id')
    if status == 'unselected':
        need(target_id is None, 'decision: unselected must have a null target_id')
    else:
        text_value(target_id, 'decision.target_id')
        need(target_id in candidates, 'decision: unknown target_id')


def input_integrity(packet, packet_dir):
    inputs = packet['research']['inputs']
    if not inputs:
        return 'not_bound', [], ['No file snapshot bound; research.basis must identify the actual message/material version.']
    if packet_dir is None:
        return 'not_checked', ['File snapshots require packet_dir; inputs were not checked'], []
    errors, seen = [], set()
    for item in inputs:
        try:
            path = (Path(packet_dir) / item['path']).resolve()
            need(path not in seen, 'research.inputs: duplicate resolved input path')
            seen.add(path)
            if not path.is_file():
                errors.append(f"Unavailable input snapshot: {item['path']} (not a regular file)")
                continue
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != item['sha256']:
                errors.append(f"Changed input snapshot: {item['path']}")
        except (OSError, ValueError, RuntimeError) as exc:
            if isinstance(exc, PacketError):
                raise
            errors.append(f"Unavailable input snapshot: {item['path']} ({type(exc).__name__})")
    return ('failed' if errors else 'matched'), errors, []


def validate(packet, today=None):
    packet = obj(packet, "packet")
    choice(packet.get('schema_version'), {'1.0', '1.1'}, 'schema_version')
    modern = packet['schema_version'] == '1.1'
    as_of = iso_date(packet.get("as_of"), "as_of")
    need(as_of <= (today or date.today()), 'as_of: future conclusions cannot be treated as verified')
    constraints = index_rows(packet.get("constraints"), "constraints")
    sources = index_rows(packet.get("sources"), "sources")
    candidates = index_rows(packet.get("candidates"), "candidates")
    if modern:
        validate_modern_context(packet, candidates)
    for key, row in constraints.items():
        where = f"constraint {key}"
        text_value(row.get("requirement"), where + ".requirement")
        need(type(row.get("hard")) is bool, where + ".hard: expected boolean")
        origin = choice(row.get("origin"), {"user", "institution", "funder", "assumption"}, where + ".origin")
        need(origin != "assumption" or not row["hard"], where + ": an assumption cannot be a hard constraint")
        if modern:
            choice(row.get('kind'), set(CHECK_KINDS), where + '.kind')
    for key, row in sources.items():
        where = f"source {key}"
        choice(row.get("kind"), SOURCE_KINDS, where + ".kind")
        text_value(row.get("locator"), where + ".locator")
        accessed = iso_date(row.get("accessed_on"), where + ".accessed_on")
        need(accessed <= as_of, where + ": access date is after as_of")
        if modern:
            seen = set()
            for binding in array(row.get('applies_to'), where + '.applies_to'):
                binding = obj(binding, where + '.applicability')
                need(set(binding) <= {'candidate_id', 'article_type', 'publication_route'},
                     where + ': unknown applicability field')
                cid = text_value(binding.get('candidate_id'), where + '.applicability.candidate_id')
                need(cid in candidates, where + ': applicability references an unknown candidate')
                for field in ('article_type', 'publication_route'):
                    if field in binding:
                        text_value(binding[field], where + '.applicability.' + field)
                signature = (cid, binding.get('article_type'), binding.get('publication_route'))
                need(signature not in seen, where + ': duplicate applicability')
                seen.add(signature)
    for key, row in candidates.items():
        where = f"candidate {key}"
        text_value(row.get("name"), where + ".name")
        need(type(row.get("recommended")) is bool, where + ".recommended: expected boolean")
        if modern:
            target = obj(row.get('target'), where + '.target')
            for field in ('publisher', 'homepage', 'article_type', 'publication_route'):
                text_value(target.get(field), where + '.target.' + field)
            issns = array(target.get('issns'), where + '.target.issns')
            for issn in issns:
                text_value(issn, where + '.target.issn')
                need(bool(re.fullmatch('[0-9]{4}-[0-9]{3}[0-9X]', issn)), where + ': invalid ISSN format')
            need(len(issns) == len(set(issns)), where + ': duplicate ISSNs')
            choice(target.get('submission_stage'), {'planning', 'initial', 'revision', 'transfer', 'production'},
                   where + '.target.submission_stage')
        seen = set()
        for check in array(row.get("checks"), where + ".checks"):
            check = obj(check, where + ".check")
            cid = text_value(check.get("constraint_id"), where + ".check.constraint_id")
            need(cid in constraints, where + f": unknown constraint id {cid}")
            need(cid not in seen, where + f": duplicate check for {cid}")
            seen.add(cid)
            status = choice(check.get("status"), {"pass", "fail", "unknown"}, where + f".check {cid}")
            text_value(check.get("basis"), where + f".check {cid}.basis")
            if modern:
                kind = constraints[cid]['kind']
                bound_references(check, sources, where + f'.check {cid}', key, target,
                                 required=status != 'unknown', kinds=CHECK_KINDS[kind],
                                 article_type=status != 'unknown' and kind in {'fees', 'open_access'},
                                 route=status != 'unknown' and kind in {'fees', 'open_access'})
            else:
                references(check, sources, where + f".check {cid}", required=status != "unknown")
        for facet, kinds in FACET_KINDS.items():
            evidence = obj(row.get(facet), where + "." + facet)
            statuses = {'pass', 'fail', 'unknown'} if modern else {'verified', 'unverified'}
            status = choice(evidence.get("status"), statuses, where + "." + facet)
            text_value(evidence.get("basis"), where + "." + facet + ".basis")
            if modern:
                bound_references(evidence, sources, where + '.' + facet, key, target,
                                 required=status != 'unknown', kinds=kinds,
                                 article_type=status != 'unknown' and facet == 'article_type')
            else:
                references(evidence, sources, where + "." + facet, required=status == "verified", kinds=kinds)
        fit = obj(row.get("fit"), where + ".fit")
        choice(fit.get("band"), {"strong", "plausible", "weak", "unknown", "mismatch"}, where + ".fit.band")
        text_value(fit.get("rationale"), where + ".fit.rationale")
        text_value(fit.get("counterevidence"), where + ".fit.counterevidence")
        for i, comparable in enumerate(array(row.get("comparables"), where + ".comparables")):
            item = obj(comparable, where + f".comparables[{i}]")
            loc = where + f".comparables[{i}]"
            for field in ("title", "locator", "shared_axes", "important_difference"):
                text_value(item.get(field), loc + "." + field)
            need(type(item.get("year")) is int and 1000 <= item["year"] <= 9999,
                 loc + ".year: expected a four-digit year")
            if 'published_on' in item:
                need(iso_date(item['published_on'], loc + '.published_on') <= as_of,
                     loc + ': future publication cannot be a published precedent')
            need(item['year'] <= as_of.year or 'published_on' in item,
                 loc + '.year: future issue year needs an already-published online date')
            status = choice(item.get("status"), {"verified", "unverified"}, loc + ".status")
            if modern:
                bound_references(item, sources, loc, key, target, required=status == 'verified',
                                 kinds={'primary_article', 'metadata'})
            else:
                references(item, sources, loc, required=status == "verified", kinds={"primary_article", "metadata"})
        exception = row.get("precedent_exception")
        if exception is not None:
            exception = obj(exception, where + ".precedent_exception")
            text_value(exception.get("reason"), where + ".precedent_exception.reason")
            if modern:
                bound_references(exception, sources, where + '.precedent_exception', key, target,
                                 required=True, kinds={'official_journal', 'official_policy'})
            else:
                references(exception, sources, where + ".precedent_exception", required=True,
                           kinds={"official_journal", "official_policy"})
    return constraints, candidates


def audit(packet, packet_dir=None, today=None):
    """Return a deterministic structural/gating audit, never a recommendation score."""
    constraints, candidates = validate(packet, today=today)
    modern = packet['schema_version'] == '1.1'
    errors, results = [], []
    integrity, warnings = 'not_bound', []
    if modern:
        integrity, input_errors, warnings = input_integrity(packet, packet_dir)
        errors.extend(input_errors)
    else:
        warnings.append('Legacy 1.0: candidate/type/route binding, input snapshots and decision authority were not checked.')
    hard = {key for key, row in constraints.items() if row["hard"]}
    for key, row in candidates.items():
        checks = {item["constraint_id"]: item for item in row["checks"]}
        failed = sorted(cid for cid in hard if checks.get(cid, {}).get("status") == "fail")
        unknown = sorted(cid for cid in hard if checks.get(cid, {}).get("status", "unknown") == "unknown")
        mismatch = row["fit"]["band"] == "mismatch"
        facet_failed = modern and any(row[f]['status'] == 'fail' for f in FACET_KINDS)
        facet_unknown = modern and any(row[f]['status'] == 'unknown' for f in FACET_KINDS)
        eligibility = 'excluded' if failed or mismatch or facet_failed else 'conditional' if unknown or facet_unknown else 'eligible'
        missing = []
        if failed:
            missing.append("failed hard constraints: " + ", ".join(failed))
        if unknown:
            missing.append("unresolved hard constraints: " + ", ".join(unknown))
        if row["fit"]["band"] not in {"strong", "plausible"}:
            missing.append("fit is " + row["fit"]["band"])
        for facet in FACET_KINDS:
            if row[facet]['status'] != ('pass' if modern else 'verified'):
                missing.append(facet + ' is ' + row[facet]['status'])
        if modern and integrity in {'failed', 'not_checked'}:
            missing.append('research input snapshots did not match or were not checked')
        has_comparable = any(p["status"] == "verified" for p in row["comparables"])
        has_exception = row.get("precedent_exception") is not None
        if not has_comparable and not has_exception:
            missing.append("no verified comparable or sourced precedent exception")
        ready = not missing
        if row["recommended"] and not ready:
            errors.append(f"{key}: recommended despite " + "; ".join(missing))
        results.append({
            "id": key, "eligibility": eligibility, "recommendation_ready": ready,
            "failed_hard_constraints": failed, "unknown_hard_constraints": unknown,
            "missing_for_recommendation": missing,
            "uses_precedent_exception": has_exception and not has_comparable,
        })
    handoff = None
    if modern:
        decision = packet['decision']
        selected = next((r for r in results if r['id'] == decision['target_id']), None)
        handoff = {**decision, 'target_authorized': decision['status'] in {'author_selected', 'delegated'},
                   'evidence_ready': bool(selected and selected['recommendation_ready'])}
        if selected and not handoff['evidence_ready']:
            warnings.append('Selected/proposed target is not evidence-ready; retain the decision and disclose unresolved gates.')
    return {
        "valid": not errors, "as_of": packet["as_of"], "errors": errors,
        'audit_level': 'bound_1.1' if modern else 'legacy_1.0',
        'input_integrity': integrity, 'warnings': warnings, 'handoff': handoff,
        "candidates": results,
        "limitations": "Checks declared structure/applicability and only listed local file hashes. Does not verify facts, URLs, actual source provenance, unlisted dependencies, scientific similarity, decision authority, or ranking.",
    }


def unique_json_object(pairs):
    """Do not silently accept duplicate JSON keys such as two conflicting statuses."""
    row = {}
    for key, value in pairs:
        need(key not in row, f"duplicate JSON key: {key}")
        row[key] = value
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="Local UTF-8 JSON evidence packet")
    args = parser.parse_args(argv)
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_json_object)
        result = audit(packet, packet_dir=args.packet.resolve().parent)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        result = {"valid": False, "errors": [str(exc)], "candidates": []}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
