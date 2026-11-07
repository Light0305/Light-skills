#!/usr/bin/env python3
"""Local, read-only experiment intake and auditable analysis handoffs (stdlib).

No model calls, network, scientific inference, experiment execution or upstream writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
ROUTES = {"stay", "light-experiment", "light-design", "light-idea", "light-journal-select", "light-chart", "light-write", "stop", "hold"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path):
    def bad_constant(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    def finite_float(value):
        result = float(value)
        require(math.isfinite(result), "JSON number overflow")
        return result
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=unique_object, parse_constant=bad_constant, parse_float=finite_float)


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def linked(path):
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)()) or bool(
        getattr(path.lstat(), "st_file_attributes", 0) & 0x400)


def plain_file(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        require(not linked(part), f"Linked/reparse input or ancestor: {part}")
    require(path.is_file(), f"Not a regular file: {path}")
    return path


def inside(root, relative):
    require(nonempty(relative), "Missing relative path")
    rel = Path(relative)
    require(not rel.is_absolute() and not rel.drive and ".." not in rel.parts,
            f"Unsafe relative path: {relative}")
    candidate = root / rel
    resolved = candidate.resolve()
    require(root in resolved.parents, f"Path escapes workspace: {relative}")
    for part in (candidate, *candidate.parents):
        if part == root:
            break
        if part.exists() or part.is_symlink():
            require(not linked(part), f"Linked output path: {part}")
    return candidate


def fingerprint(path):
    path = plain_file(path)
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def overlaps(a, b):
    return a == b or a in b.parents or b in a.parents


def assessment_records(root, run_id):
    folder = root / 'runs' / run_id
    directory = folder / 'assessments'
    require(not directory.exists() or not linked(directory), 'Linked assessments directory')
    paths = sorted(directory.glob('*.json'))
    previous, verified, current = None, bool(paths), {}
    for path in paths:
        receipt = read(plain_file(path))
        current = receipt.get('assessment', {})
        if 'sha256' in receipt:
            canonical = json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
            require(hashlib.sha256(canonical).hexdigest() == receipt['sha256'], 'Assessment content drift')
            require(current.get('run_id') == run_id, 'Assessment binding mismatch')
            require(receipt.get('supersedes') == previous, 'Assessment correction chain is broken')
        else:
            verified = False  # Old excerpts remain readable, not certified receipts.
        previous = path.name
    present = {path.stem for path in paths}
    for path in sorted((root / 'events').glob('*.json')):
        event = read(plain_file(path))
        if event.get('event_type') == 'run_assessed' and event.get('payload', {}).get('run_id') == run_id:
            require(event['payload'].get('assessment_id') in present, 'Missing recorded assessment; cannot fall back to older QC')
    return paths, current, verified


def sealed_records(folder):
    path = folder / 'manifest.json'
    if not path.exists():
        return None
    manifest = read(plain_file(path))
    require(manifest.get('schema_version') == '1.0', 'Unsupported run manifest')
    require(not manifest.get('unarchived_links_or_special_files'), 'Unarchived special files in run')
    records = {}
    for row in manifest['records']:
        relative = row['path']
        inside(folder, relative)
        require(relative not in records, 'Duplicate sealed record path')
        require(type(row.get('bytes')) is int and row['bytes'] >= 0
                and isinstance(row.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Invalid sealed fingerprint')
        records[relative] = row
    return records


def check_sealed_file(folder, path, records):
    relative = path.relative_to(folder).as_posix()
    require(relative in records, f'File absent from run seal: {relative}')
    require(fingerprint(path) == {k: records[relative][k] for k in ('bytes', 'sha256')}, f'Sealed input drift: {relative}')


def collect_execution(root, source_id):
    root = Path(root).resolve()
    campaign = read(plain_file(root / "campaign.json"))
    require(campaign.get("schema_version") == "1.0" and nonempty(campaign.get("campaign_id")),
            "Expected light-experiment schema 1.0 campaign; external files use --input")
    design_path = plain_file(root / "inputs/design/design.json")
    design = read(design_path)
    require(design.get("design_id") == campaign.get("design_id")
            and design.get("version") == campaign.get("design_version")
            and design.get("selection") == campaign.get("selection"), "Campaign/design identity mismatch")
    files = [(root / "campaign.json", "campaign"), (design_path, "design")]
    identities = {}
    for field, key in (('claims', 'claim_id'), ('experiments', 'experiment_id')):
        values = design.get(field, [])
        require(isinstance(values, list), f'Invalid native {field}')
        ids = [value.get(key) for value in values]
        require(all(isinstance(i, str) and ID.fullmatch(i) for i in ids)
                and len(ids) == len(set(ids)), f'Invalid/duplicate native {key}')
        identities[field] = set(ids)
    require(all(set(e.get('claim_ids', [])) <= identities['claims'] for e in design.get('experiments', [])),
            'Experiment references an unknown claim')
    for name in ("upstream.json", "inputs/design/context.json", "inputs/design/plan.md", "execution-report.md"):
        if (root / name).exists():
            files.append((plain_file(root / name), "execution_metadata"))
    for directory in ("inputs/design/protocols", "events"):
        base = root / directory
        if base.exists():
            require(not linked(base), f"Linked metadata directory: {base}")
            for folder, dirs, names in os.walk(base, followlinks=False):
                require(not any(linked(Path(folder) / d) for d in dirs), "Linked metadata subdirectory")
                files.extend((plain_file(Path(folder) / n), "execution_metadata") for n in sorted(names))
    runs = []
    run_root = root / "runs"
    if run_root.exists():
        require(not linked(run_root), "Linked runs directory")
        for folder in sorted(run_root.iterdir()):
            require(not linked(folder), f"Linked run directory: {folder}")
            if not folder.is_dir():
                continue
            require(ID.fullmatch(folder.name), "Invalid run directory ID")
            spec = read(plain_file(folder / "spec.json"))
            require(spec.get("run_id") == folder.name, "Run identity mismatch")
            run_start = len(files)
            files.append((folder / "spec.json", "run_spec"))
            result = None
            for name in ("result.json", "manifest.json", "started.json", "prepared.json", "environment.json", "input-manifest.json"):
                path = folder / name
                if path.exists():
                    plain_file(path)
                    files.append((path, "run_metadata"))
                    if name == "result.json":
                        result = read(path)
                        require(result.get("run_id") == folder.name, "Result identity mismatch")
            assessment_files, assessment, assessment_verified = assessment_records(root, folder.name)
            files.extend((p, 'run_assessment') for p in assessment_files)
            records = sealed_records(folder)
            if records is not None:
                for path, role in files[run_start:]:
                    if path.parent == folder and path.name != 'manifest.json':
                        check_sealed_file(folder, path, records)
            experiment = next((e for e in design.get('experiments', [])
                               if e.get('experiment_id') == spec.get('experiment_id')), None)
            require(experiment is not None, 'Run references an unknown experiment')
            state = result.get("process_status") if result else (
                "running_or_interrupted" if (folder / "started.json").exists() else "not_started")
            runs.append({"run_ref": f"{source_id}/{folder.name}", "experiment_id": spec.get("experiment_id"),
                         "task_id": spec.get("task_id"), "kind": spec.get("kind"), "unit": spec.get("unit"),
                         "parent_run_id": spec.get("parent_run_id"), "process_status": state,
                         "artifacts_ok": result.get("artifacts_ok") if result else None,
                         "input_drift_after": result.get("input_drift_after") if result else None,
                         "qc_status": assessment.get("qc_status", "unknown"),
                         "upstream_outcome": assessment.get("outcome", "not_evaluated"),
                         'claim_refs': [f'{source_id}/{cid}' for cid in experiment.get('claim_ids', [])],
                         'depends_on_runs': [f'{source_id}/{rid}' for rid in spec.get('depends_on_runs', [])],
                         'seal_status': 'selected_files_only' if records is not None else 'missing',
                         'assessment_verified': assessment_verified,
                         'assessment_file_sha256': fingerprint(assessment_files[-1])['sha256'] if assessment_files else None,
                         'termination_confirmed': result.get('termination_confirmed') if result else None})
    execution = {"source_id": source_id, "path": str(root), "campaign_id": campaign["campaign_id"],
                 "design_id": campaign.get("design_id"), "design_version": campaign.get("design_version"),
                 "selection": campaign.get("selection"), "execution_scope": campaign.get("execution_scope"),
                 "claims": design.get("claims", []), "experiments": design.get("experiments", []), "runs": runs}
    return execution, sorted(files, key=lambda item: str(item[0]))


def ingest(executions, inputs, out, parent=None):
    out = Path(out).resolve()
    require(not overlaps(ROOT, out), "Research output must be outside the skill source/installation")
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())), "Output must be new or empty")
    context = {"schema_version": "1.0", "created_at": now(), "executions": [], "inputs": [], "warnings": [], "parent": None}
    candidates, seen_roots = [], set()
    for i, source in enumerate(executions, 1):
        source = Path(source).resolve()
        require(source not in seen_roots and not overlaps(source, out), "Duplicate/overlapping execution workspace")
        seen_roots.add(source)
        execution, files = collect_execution(source, f"EX{i:02d}")
        context["executions"].append(execution)
        candidates.extend((p, role, True) for p, role in files)
    candidates.extend((plain_file(p), "analysis_input", False) for p in inputs)
    if parent:
        p = plain_file(parent)
        previous = read(p)
        require(ID.fullmatch(previous.get("analysis_id", ""))
                and type(previous.get("round")) is int and previous["round"] >= 1,
                "Invalid parent analysis identity/round")
        context["parent"] = {"analysis_id": previous["analysis_id"], "round": previous["round"],
                             "loop_decision": previous.get("loop_decision")}
        candidates.append((p, "parent_analysis", True))
    require(candidates, "Supply at least one execution or explicit input file")
    prepared, seen = [], set()
    for p, role, snapshot in candidates:
        p = plain_file(p)
        require(not overlaps(out, p), "Input cannot overlap the output directory")
        if str(p) in seen:
            continue
        seen.add(str(p))
        info = fingerprint(p)
        require(not snapshot or info["bytes"] <= 16 * 1024 * 1024, "Metadata exceeds 16 MiB; use explicit --input")
        prepared.append((p, role, snapshot, info))
    bindings = {}
    for execution in context['executions']:
        for run in execution['runs']:
            folder = Path(execution['path']) / 'runs' / run['run_ref'].split('/', 1)[1]
            records = sealed_records(folder)
            for path, role, _, _ in prepared:
                if role != 'analysis_input' or folder not in path.parents:
                    continue
                relative = path.relative_to(folder).as_posix()
                if not (relative.startswith('outputs/') or relative in {'stdout.log', 'stderr.log'}):
                    continue
                if records is not None:
                    check_sealed_file(folder, path, records)
                bindings[str(path)] = {'run_ref': run['run_ref'], 'sealed': records is not None}
    out.mkdir(parents=True, exist_ok=True)
    for i, (p, role, snapshot, info) in enumerate(prepared, 1):
        input_id = f"S{i:04d}"
        row = {"input_id": input_id, "path": str(p), "role": role, **info, "snapshot": None}
        if snapshot:
            rel = f"inputs/{input_id}{p.suffix}"
            target = inside(out, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = p.read_bytes()
            require(hashlib.sha256(data).hexdigest() == info["sha256"], "Input changed during intake")
            with target.open("xb") as stream:
                stream.write(data)
            row["snapshot"] = rel
        row.update(bindings.get(str(p), {}))
        context["inputs"].append(row)
    context['warnings'].append('Bounded intake: seals checked for listed run metadata and selected raw inputs only. Other outputs/code snapshots are not rehashed; use native experiment verify when needed.')
    if any(r['seal_status'] == 'missing' or not r['assessment_verified']
           for e in context['executions'] for r in e['runs']):
        context['warnings'].append('Some run seals or verifiable QC receipts are missing; inspection is allowed, decisive native-run findings require verified records.')
    if any(r["process_status"] != "succeeded" for e in context["executions"] for r in e["runs"]):
        context["warnings"].append("Incomplete/failed/unstarted attempts present; separate them from valid scientific negatives.")
    analysis_id = "A_" + uuid.uuid4().hex[:12]
    analysis = read(ROOT / "templates/analysis.example.json")
    analysis.update(analysis_id=analysis_id, round=(context["parent"]["round"] + 1 if parent else 1),
                    parent_analysis_id=(context["parent"]["analysis_id"] if parent else None))
    write_new(out / "context.json", context)
    write_new(out / "receipt.json", {"schema_version": "1.0", "analysis_id": analysis_id,
                                    "context": fingerprint(out / "context.json"), "created_at": now()})
    write_new(out / "analysis.json", analysis)
    write_new(out / "analysis-plan.json", read(ROOT / "templates/analysis-plan.example.json"))
    return {"ok": True, "workspace": str(out), "analysis_id": analysis_id,
            "inputs": len(context["inputs"]), "executions": len(context["executions"]), "warnings": context["warnings"]}


def load_workspace(workspace):
    root = Path(workspace).resolve()
    context, receipt = read(root / "context.json"), read(root / "receipt.json")
    require(context.get("schema_version") == receipt.get("schema_version") == "1.0", "Unsupported intake schema")
    require(fingerprint(root / "context.json") == receipt["context"], "Context changed after intake; create a new analysis")
    return root, context, receipt


def check_plan(plan):
    require(plan.get("schema_version") == "1.0", "Unsupported plan schema")
    require(plan.get("timing") in {"inherited", "prospective", "retrospective", "unknown"}, "Invalid plan timing")
    for field in ("question", "estimand", "independent_unit", "comparison", "data_scope", "analysis_method",
                  "uncertainty", "missing_and_exclusions", "multiplicity", "decision_thresholds", "timing_basis", "result_access"):
        require(nonempty(plan.get(field)), f"Plan needs {field}")
    require(isinstance(plan.get("sensitivity_branches"), list), "Plan sensitivity_branches must be a list")


def freeze_plan(workspace):
    root, _, _ = load_workspace(workspace)
    plan = read(root / "analysis-plan.json")
    check_plan(plan)
    write_new(root / "plan-lock.json", {"schema_version": "1.0", "recorded_at": now(),
              "plan": fingerprint(root / "analysis-plan.json"), "timing_claim": plan["timing"],
              "boundary": "Local specification freeze; not proof of preregistration or first data access."})
    return {"ok": True, "timing": plan["timing"], "warning": "Freeze does not certify prospectivity."}


def register_artifact(workspace, artifact_id, file, input_ids, codes, command, environment):
    root, context, _ = load_workspace(workspace)
    require(ID.fullmatch(artifact_id), "Invalid artifact ID")
    known = {x["input_id"] for x in context["inputs"]}
    require(input_ids and set(input_ids) <= known, "Supply real input IDs")
    path = inside(root, file)
    require(Path(file).parts[0] in {"derived", "figures"}, "Artifact must be in derived/ or figures/")
    require(codes and nonempty(command) and nonempty(environment), "Need code, actual command and environment record")
    code_records = []
    for code in codes:
        code_path = inside(root, code)
        require(Path(code).parts[0] == "code", "Analysis code must be under code/")
        code_records.append({"path": code, **fingerprint(code_path)})
    record = {"schema_version": "1.0", "artifact_id": artifact_id, "path": file, **fingerprint(path),
              "input_ids": input_ids, "code": code_records, "command": command, "environment": environment,
              "recorded_at": now(), "boundary": "Records supplied execution provenance; does not execute or attest the command."}
    write_new(inside(root, f"artifacts/{artifact_id}.json"), record)
    return {"ok": True, "artifact_id": artifact_id, "path": file}


def handoff_sources(root):
    paths = [root / name for name in ('context.json', 'receipt.json', 'analysis.json',
             'analysis-plan.json', 'plan-lock.json', 'analysis-report.md')]
    paths.extend(sorted((root / 'artifacts').glob('*.json')))
    return [{'path': p.relative_to(root).as_posix(), **fingerprint(p)} for p in paths]


def usable_run(ref, runs, executions, warnings, checked, visiting=None):
    if ref in checked:
        return
    visiting = set() if visiting is None else visiting
    require(ref not in visiting and ref in runs, f'Invalid/cyclic run prerequisite: {ref}')
    visiting.add(ref)
    run = runs[ref]
    require(run['process_status'] == 'succeeded' and run['artifacts_ok'] is True
            and not run.get('input_drift_after') and run.get('termination_confirmed') is not False, f'Unusable run: {ref}')
    require(run.get('qc_status') == 'passed' and run.get('assessment_verified') is True, f'Run needs verifiable passed QC: {ref}')
    require(run.get('seal_status') == 'selected_files_only', f'Run seal missing; re-ingest verified records: {ref}')
    execution = executions[ref.split('/', 1)[0]]
    source = Path(execution['path'])
    if source.is_dir():
        try:
            paths, current, verified = assessment_records(source, ref.split('/', 1)[1])
        except OSError:
            warnings.append(f'Current QC unavailable; only frozen assessment retained: {ref}')
        else:
            require(verified and current.get('qc_status') == 'passed', f'Current QC revoked or unverifiable: {ref}')
            if fingerprint(paths[-1])['sha256'] != run.get('assessment_file_sha256'):
                warnings.append(f'Current passed QC differs from frozen receipt; review correction and re-ingest to adopt it: {ref}')
    else:
        warnings.append(f'Execution unavailable; current QC cannot be checked: {ref}')
    for dependency in run.get('depends_on_runs', []):
        usable_run(dependency, runs, executions, warnings, checked, visiting)
    visiting.remove(ref)
    checked.add(ref)


def verify(workspace):
    errors, warnings = [], []
    try:
        root, context, receipt = load_workspace(workspace)
        warnings.extend(context.get("warnings", []))
        for row in context["inputs"]:
            expected = {k: row[k] for k in ("bytes", "sha256")}
            if row.get("snapshot"):
                require(fingerprint(inside(root, row["snapshot"])) == expected, f"Snapshot drift: {row['input_id']}")
                try:
                    if fingerprint(row["path"]) != expected:
                        warnings.append(f"Upstream metadata changed after snapshot: {row['input_id']}")
                except (OSError, ValueError):
                    warnings.append(f"Original metadata unavailable; frozen copy retained: {row['input_id']}")
            else:
                require(fingerprint(row["path"]) == expected, f"Input drift: {row['input_id']}")
        analysis = read(root / "analysis.json")
        require(analysis.get("schema_version") == "1.0" and analysis.get("analysis_id") == receipt["analysis_id"], "Analysis identity mismatch")
        require(analysis.get("status") in {"draft", "complete"}, "Invalid analysis status")
        complete = analysis["status"] == "complete"
        require(type(analysis.get("round")) is int and analysis["round"] >= 1, "Invalid round")
        parent = context.get("parent")
        require(analysis.get("parent_analysis_id") == (parent["analysis_id"] if parent else None)
                and analysis["round"] == (parent["round"] + 1 if parent else 1), "Lineage mismatch")
        require(analysis.get("data_kind") in {"measured", "simulation", "synthetic_validation", "illustrative", "mixed", "unknown"}, "Invalid data kind")
        require(isinstance(analysis.get("history"), list) and isinstance(analysis.get("exclusions"), list)
                and isinstance(analysis.get("deviations"), list), "History/exclusions/deviations must be lists")
        plan = read(root / "analysis-plan.json")
        if (root / "plan-lock.json").exists():
            require(fingerprint(root / "analysis-plan.json") == read(root / "plan-lock.json")["plan"], "Plan changed after freeze")
            check_plan(plan)
        elif complete:
            raise ValueError("Complete analysis requires a frozen plan, including retrospective plans")
        if plan.get("timing") == "unknown":
            warnings.append("Plan timing unknown; cannot claim prospective confirmation")
        input_rows = {r['input_id']: r for r in context['inputs']}
        inputs = set(input_rows)
        executions = {e['source_id']: e for e in context['executions']}
        checked_runs = set()
        runs = {r["run_ref"]: r for e in context["executions"] for r in e["runs"]}
        claims = {f"{e['source_id']}/{c['claim_id']}" for e in context["executions"] for c in e["claims"]}
        artifacts = {}
        if (root / "artifacts").exists():
            require(not linked(root / "artifacts"), "Linked artifact registry")
            for path in sorted((root / "artifacts").glob("*.json")):
                item = read(plain_file(path))
                aid = item.get("artifact_id")
                require(isinstance(aid, str) and ID.fullmatch(aid) and aid not in artifacts and path.stem == aid, "Invalid/duplicate artifact ID")
                require(Path(item["path"]).parts[0] in {"derived", "figures"}, "Invalid artifact location")
                require(fingerprint(inside(root, item["path"])) == {k: item[k] for k in ("bytes", "sha256")}, f"Artifact drift: {aid}")
                require(item["input_ids"] and set(item["input_ids"]) <= inputs, "Unknown artifact inputs")
                require(item["code"] and nonempty(item.get("command")) and nonempty(item.get("environment")), "Missing artifact provenance")
                for code in item["code"]:
                    require(Path(code["path"]).parts[0] == "code", "Invalid code location")
                    require(fingerprint(inside(root, code["path"])) == {k: code[k] for k in ("bytes", "sha256")}, f"Analysis code drift: {code['path']}")
                artifacts[aid] = item
        findings = analysis.get("findings")
        require(isinstance(findings, list), "findings must be a list")
        finding_ids = set()
        for finding in findings:
            fid = finding.get("finding_id")
            require(isinstance(fid, str) and ID.fullmatch(fid) and fid not in finding_ids, "Invalid/duplicate finding ID")
            finding_ids.add(fid)
            require(finding.get("mode") in {"confirmatory", "exploratory", "descriptive"}, "Invalid finding mode")
            require(finding.get("validity") in {"usable", "compromised", "unknown"}, "Invalid validity")
            outcome = finding.get("outcome")
            require(outcome in {"support", "falsify", "inconclusive", "not_evaluated"}, "Invalid outcome")
            require(nonempty(finding.get("statement")) and nonempty(finding.get("validity_basis")), "Finding needs statement and validity basis")
            require(isinstance(finding.get("run_refs"), list) and set(finding["run_refs"]) <= runs.keys(), "Unknown run reference")
            require(isinstance(finding.get("claim_refs"), list) and set(finding["claim_refs"]) <= claims, "Unknown claim reference")
            evidence = finding.get("evidence")
            require(isinstance(evidence, list), "evidence must be a list")
            evidence_inputs = set()
            for ref in evidence:
                require(nonempty(ref.get("locator")), "Evidence needs a specific locator")
                require(('input_id' in ref) != ('artifact_id' in ref), 'Supply exactly one evidence reference field')
                require((ref.get("input_id") in inputs) != (ref.get("artifact_id") in artifacts), "Evidence must reference exactly one known input OR artifact")
                if 'input_id' in ref:
                    evidence_inputs.add(ref['input_id'])
                else:
                    evidence_inputs.update(artifacts[ref['artifact_id']]['input_ids'])
            if finding['run_refs'] and finding['claim_refs']:
                bound_claims = {claim for ref in finding['run_refs'] for claim in runs[ref].get('claim_refs', [])}
                require(set(finding['claim_refs']) <= bound_claims, 'Claim is outside the referenced run experiments')
            require(isinstance(finding.get("estimates"), list) and isinstance(finding.get("limitations"), list), "Estimates/limitations must be lists")
            for estimate in finding["estimates"]:
                require(nonempty(estimate.get("name")) and nonempty(estimate.get("unit")), "Estimate needs name/unit")
                require(estimate.get("value") is None or number(estimate["value"]), "Non-finite estimate")
                for field in ("n_independent", "n_observations"):
                    require(estimate.get(field) is None or (type(estimate[field]) is int and estimate[field] > 0), "Counts must be positive integers or null")
                ni, no = estimate.get("n_independent"), estimate.get("n_observations")
                require(ni is None or no is None or ni <= no, "Independent N exceeds observations")
                interval = estimate.get("interval")
                if interval is not None:
                    require(number(interval.get("level")) and 0 < interval["level"] < 1, "Invalid interval level")
                    require(number(interval.get("lower")) and number(interval.get("upper"))
                            and interval["lower"] <= interval["upper"], "Invalid interval bounds")
                    require(all(nonempty(interval.get(k)) for k in ("type", "method", "uncertainty_scope")), "Interval needs type/method/scope")
            if finding["mode"] == "confirmatory":
                require(plan.get("timing") in {"inherited", "prospective"}, "Retrospective/unknown plan cannot certify confirmatory finding")
            if outcome in {"support", "falsify"}:
                require(finding["validity"] == "usable" and evidence, "Decisive finding requires usable evidence")
                require(analysis["data_kind"] != "unknown", "Unknown data origin cannot support decisive findings")
                for ref in finding["run_refs"]:
                    r = runs[ref]
                    task_failure = r['process_status'] in {'failed', 'timed_out'} and not r.get('input_drift_after') and r.get('termination_confirmed') is not False
                    if task_failure:
                        require(nonempty(finding.get('failure_outcome_basis')), 'Failed run needs an explicit task-outcome rationale')
                    else:
                        usable_run(ref, runs, executions, warnings, checked_runs)
                    raw_evidence = [input_rows[i] for i in evidence_inputs if input_rows[i].get('run_ref') == ref]
                    require(raw_evidence and (task_failure or any(i.get('sealed') for i in raw_evidence)),
                            f'Finding needs selected raw evidence for run, directly or through a registered artifact: {ref}')
            if complete:
                require(evidence, "Complete findings require evidence, including evidence of a gap")
        decision = analysis.get("loop_decision", {})
        require(decision.get("route") in ROUTES, "Invalid loop route")
        require(isinstance(decision.get("finding_ids"), list) and set(decision["finding_ids"]) <= finding_ids, "Unknown decision finding IDs")
        if complete:
            require(findings and decision["finding_ids"], "Complete analysis needs findings and a grounded decision")
            for key in ("reason", "target_question", "next_action", "stop_rule", "reentry_condition", "execution_authorization"):
                require(nonempty(decision.get(key)), f"Decision needs {key}")
            require(isinstance(decision.get("predictions"), list), "predictions must be a list")
            if decision["route"] not in {"stop", "hold", "light-chart", "light-write", 'light-journal-select'}:
                require(decision["predictions"] and all(nonempty(p.get("result")) and nonempty(p.get("decision")) for p in decision["predictions"]), "Next research action needs result-to-decision predictions")
            budget = decision.get("budget", {})
            require(budget.get("status") in {"bounded", "unknown", "not_applicable"} and nonempty(budget.get("basis")), "Decision budget needs status/basis")
            if budget["status"] == "bounded":
                require(nonempty(budget.get("limit")), "Bounded budget needs an actual limit")
            if budget["status"] == "unknown":
                warnings.append("Next-step budget unknown; no new experiment execution authorized by this record")
            require(plain_file(root / "analysis-report.md").stat().st_size > 0, "Complete analysis needs a report")
        else:
            warnings.append("Draft analysis; structure passing is not a finished analysis")
        if (root / "handoff.json").exists():
            packet = read(root / 'handoff.json')
            require(packet['analysis_sha256'] == fingerprint(root / 'analysis.json')['sha256'], 'Handoff is stale; export a new analysis version')
            if 'sources' in packet:
                require(packet['sources'] == handoff_sources(root), 'Handoff sources are stale; retain old export and create a revised analysis')
            else:
                warnings.append('Legacy handoff only binds analysis.json; report/plan/provenance closure was not recorded')
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "boundary": "Listed-file integrity and relationships only; no numeric, statistical, causal or routing certification."}


def export_handoff(workspace):
    result = verify(workspace)
    require(result["ok"], "; ".join(result["errors"]))
    root, context, _ = load_workspace(workspace)
    analysis = read(root / "analysis.json")
    require(analysis["status"] == "complete", "Finish the analysis before exporting a handoff")
    selected = set(analysis["loop_decision"]["finding_ids"])
    packet = {"schema_version": "1.0", "packet_type": "analysis_feedback", "created_at": now(),
              "analysis_id": analysis["analysis_id"], "round": analysis["round"],
              "parent_analysis_id": analysis["parent_analysis_id"], "analysis_sha256": fingerprint(root / "analysis.json")["sha256"],
              "analysis_workspace": str(root), "data_kind": analysis["data_kind"],
              "executions": context["executions"], "decision": analysis["loop_decision"],
              "trigger_findings": [f for f in analysis["findings"] if f["finding_id"] in selected],
              "history": analysis["history"], "warnings": result["warnings"],
              'sources': handoff_sources(root),
              "boundary": "Revision brief, not a native idea/design import API, readiness declaration or experiment authorization."}
    write_new(root / "handoff.json", packet)
    return {"ok": True, "path": str(root / "handoff.json"), "route": packet["decision"]["route"]}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--execution", action="append", default=[])
    p.add_argument("--input", action="append", default=[])
    p.add_argument("--parent", help="Previous analysis.json; retains lineage and prior decision")
    p.add_argument("--out", required=True)
    for name in ("freeze-plan", "verify", "export-handoff"):
        sub.add_parser(name).add_argument("--workspace", required=True)
    p = sub.add_parser("register-artifact")
    for name in ("workspace", "artifact-id", "file", "command", "environment"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--input-id", action="append", required=True)
    p.add_argument("--code", action="append", required=True)
    args = parser.parse_args()
    try:
        if args.action == "ingest":
            result = ingest(args.execution, args.input, args.out, args.parent)
        elif args.action == "freeze-plan":
            result = freeze_plan(args.workspace)
        elif args.action == "register-artifact":
            result = register_artifact(args.workspace, args.artifact_id, args.file, args.input_id, args.code, args.command, args.environment)
        elif args.action == "export-handoff":
            result = export_handoff(args.workspace)
        else:
            result = verify(args.workspace)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0 if result["ok"] else 1
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
