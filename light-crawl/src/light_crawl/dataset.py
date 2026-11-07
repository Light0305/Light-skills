"""Explicit, versioned research-data handoffs; never automatic scientific acceptance."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from .integrity import case_path, fingerprint
from .state import CaseStore, LightCrawlError
from .utils import read_json, utc_now
from .verify import verify_case


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _evidence(store: CaseStore) -> dict:
    rows = store.evidence()
    _require(all(isinstance(row, dict) and isinstance(row.get('evidence_id'), str) for row in rows), 'Invalid evidence records')
    result = {row['evidence_id']: row for row in rows}
    _require(len(result) == len(rows), 'Duplicate evidence identity')
    return result


def export_dataset(store: CaseStore, spec_path: Path, out: Path) -> dict:
    try:
        spec = read_json(Path(spec_path))
        _require(isinstance(spec, dict), 'Dataset spec must be an object')
        _require(isinstance(spec.get('purpose'), str) and spec['purpose'].strip(), 'State the research/diagnostic purpose')
        _require(spec.get('intent') in ('research_input', 'diagnostic'), 'intent must be research_input or diagnostic')
        selection = spec.get('selection')
        _require(isinstance(selection, dict) and all(isinstance(selection.get(k), str) and selection[k].strip()
            for k in ('unit', 'inclusion', 'exclusion', 'time_range')), 'selection needs unit, inclusion, exclusion and time_range; state unknown explicitly')
        fields = spec.get('fields')
        _require(isinstance(fields, list) and fields and all(isinstance(f, dict) and
            all(isinstance(f.get(k), str) and f[k].strip() for k in ('name', 'meaning', 'unit', 'missing')) for f in fields),
            'Describe each field name, meaning, unit and missing-value semantics')
        _require(len({f['name'] for f in fields}) == len(fields), 'Duplicate field names')
        coverage = spec.get('coverage')
        _require(isinstance(coverage, dict) and all(k in coverage for k in
            ('expected_records', 'obtained_records', 'missingness', 'duplicates', 'failures')), 'Record coverage, missingness, duplicates and failures; use null/unknown where unassessed')
        for key in ('expected_records', 'obtained_records'):
            _require(coverage[key] is None or (type(coverage[key]) is int and coverage[key] >= 0), 'Record counts must be null or nonnegative integers')
        _require(isinstance(coverage['failures'], list), 'failures must be a list')
        _require(isinstance(spec.get('limitations'), list), 'limitations must be a list')
        report = verify_case(store.directory)
        _require(report.ok, '; '.join(f.message for f in report.failures))
        evidence = _evidence(store)
        supplied = spec.get('files')
        _require(isinstance(supplied, list) and supplied, 'Explicitly select dataset files')
        ids = [row.get('id') for row in supplied if isinstance(row, dict)]
        _require(len(ids) == len(supplied) and all(isinstance(i, str) and i.strip() for i in ids) and len(set(ids)) == len(ids), 'Unique nonempty file IDs are required')
        rows, selected, warnings = [], {}, []
        source_files = {name: fingerprint(store.directory / name) for name in ('scope.md', 'target.json')}
        paths = set()
        for row in supplied:
            _require(row.get('role') in ('raw', 'derived', 'code'), 'File role must be raw, derived or code')
            value = row.get('path')
            _require(isinstance(value, str) and value.strip(), 'Explicit file path required')
            path = Path(value) if Path(value).is_absolute() else case_path(store.directory, value)
            path = path.absolute()
            info = fingerprint(path)
            _require(str(path.resolve()) not in paths, 'Select each physical file once; do not relabel data as code')
            paths.add(str(path.resolve()))
            refs = row.get('evidence_ids', [])
            deps = row.get('input_ids', [])
            _require(isinstance(refs, list) and all(isinstance(i, str) and i in evidence for i in refs), 'Unknown evidence ID')
            _require(isinstance(deps, list) and all(isinstance(i, str) and i in ids and i != row['id'] for i in deps), 'Unknown/self input dependency')
            if row['role'] == 'raw':
                _require(refs and not deps, 'Raw inputs need source evidence and cannot declare derived dependencies')
                try:
                    relative = path.resolve().relative_to(store.directory.resolve()).as_posix()
                except ValueError:
                    relative = ''
                if store.state.artifacts.get(relative, {}).get('kind') == 'capture_body':
                    _require(any(evidence[ref].get('metadata', {}).get('capture_meta') for ref in refs),
                        'A captured raw file must cite its actual capture evidence')
                for ref in refs:
                    entry = evidence[ref]
                    selected[ref] = entry
                    meta_ref = entry.get('metadata', {}).get('capture_meta')
                    if meta_ref:
                        meta_path = case_path(store.directory, meta_ref)
                        meta = read_json(meta_path)
                        source_files[meta_ref] = fingerprint(meta_path)
                        request = meta_path.parent / 'request.json'
                        source_files[request.relative_to(store.directory).as_posix()] = fingerprint(request)
                        linked = case_path(store.directory, meta['body_path'])
                        _require(linked.resolve() == path.resolve(), 'Capture evidence does not identify the selected raw file')
                        _require(info == {k: meta.get(k) for k in ('bytes', 'sha256')}, 'Raw data changed after capture')
                        if meta.get('truncated') or not 200 <= meta.get('status', 0) < 300:
                            _require(spec['intent'] == 'diagnostic', 'Truncated/error responses are diagnostic evidence, not research_input')
                            warnings.append(f'{row["id"]}: truncated/error response retained for diagnosis')
                    else:
                        warnings.append(f'{row["id"]}: source is operator-recorded; no capture seal independently checked')
            if row['role'] == 'derived':
                _require(deps and isinstance(row.get('command'), str) and row['command'].strip() and
                    isinstance(row.get('environment'), str) and row['environment'].strip(),
                    'Derived data needs input_ids, command and environment; registration does not prove execution')
            rows.append({**row, 'path': str(path.resolve()), **info})
        by_id = {row['id']: row for row in rows}
        visiting, complete = set(), {}
        def ancestors(identity):
            _require(identity not in visiting, 'Dataset lineage contains a cycle')
            if identity in complete:
                return complete[identity]
            visiting.add(identity)
            result = {identity}
            for child in by_id[identity].get('input_ids', []):
                result.update(ancestors(child))
            visiting.remove(identity)
            complete[identity] = result
            return result
        for row in rows:
            family = [by_id[i] for i in ancestors(row['id'])]
            if row['role'] == 'derived':
                _require(any(r['role'] == 'raw' for r in family) and any(r['role'] == 'code' for r in family),
                    'Derived data needs a raw-data and code lineage')
        _require(any(r['role'] == 'raw' for r in rows), 'Include the raw source, not only a derived result')
        out = Path(out).absolute()
        _require(not out.exists(), 'Preserve prior dataset exports; choose a new output path')
        export_id = 'DS-' + uuid.uuid4().hex
        packet = {'schema_version': 1, 'packet_type': 'acquisition_dataset', 'export_id': export_id, 'created_at': utc_now(),
            'case_id': store.state.case_id, 'case_dir': str(store.directory.resolve()),
            'target': store.state.target, 'spec': spec, 'files': rows,
            'source_evidence': selected, 'source_files': source_files, 'warnings': sorted(set(warnings)),
            'boundary': 'Recorded metadata and listed-file integrity only; no certification of completeness, independence, authenticity, licence or scientific suitability.'}
        for row in rows:
            _require(fingerprint(Path(row['path'])) == {k: row[k] for k in ('bytes', 'sha256')}, 'Input changed during export')
        payload = json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(payload)
        store.add_evidence(phase=store.state.phase, source='light-crawl dataset export', action='register immutable dataset handoff',
            observation=f'export={export_id}; files={len(rows)}; intent={spec["intent"]}', artifact=str(out.resolve()),
            metadata={'export_id': export_id, **fingerprint(out)})
        return {'ok': True, 'path': str(out.resolve()), 'files': len(rows), 'warnings': packet['warnings']}
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
        raise LightCrawlError(str(error)) from error


def check_dataset(path: Path) -> dict:
    errors, warnings = [], []
    try:
        packet = read_json(Path(path))
        _require(isinstance(packet, dict) and packet.get('schema_version') == 1 and
            packet.get('packet_type') == 'acquisition_dataset', 'Unknown dataset handoff')
        _require(isinstance(packet.get('files'), list) and packet['files'], 'Dataset files missing')
        for row in packet['files']:
            _require(fingerprint(Path(row['path'])) == {k: row.get(k) for k in ('bytes', 'sha256')},
                f'Dataset file changed/missing: {row.get("id")}')
        root = Path(packet['case_dir'])
        if (root / 'case.json').is_file():
            store = CaseStore.load(root)
            _require(store.state.case_id == packet['case_id'], 'Source case identity changed')
            current = _evidence(store)
            exports = [e for e in current.values() if e.get('source') == 'light-crawl dataset export'
                and e.get('metadata', {}).get('export_id') == packet.get('export_id')]
            _require(len(exports) == 1, 'Dataset export receipt missing/ambiguous in source case')
            receipt = exports[0]['metadata']
            _require(fingerprint(Path(path)) == {k: receipt.get(k) for k in ('bytes', 'sha256')}, 'Dataset export changed; preserve it and issue a revised version')
            for relative, info in packet['source_files'].items():
                _require(fingerprint(case_path(root, relative)) == info, f'Source metadata changed: {relative}')
            for key, value in packet['source_evidence'].items():
                _require(current.get(key) == value, f'Source evidence changed/deleted: {key}')
        else:
            warnings.append('Source case unavailable; checked retained files only, not current source evidence')
        warnings.extend(packet.get('warnings', []))
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
        errors.append(str(error))
    return {'ok': not errors, 'errors': errors, 'warnings': warnings}
