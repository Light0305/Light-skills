#!/usr/bin/env python3
"""Freeze light-idea input and check plan structure; never run research tasks."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
READY = {"ready_for_pilot", "ready_for_execution"}
STATES = {"draft", "needs_input", "hold"} | READY
TABLES = {"claims": "claim_id", "sources": "source_id", "evidence": "evidence_id",
          "resources": "resource_id", "gates": "gate_id",
          "experiments": "experiment_id", "tasks": "task_id"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def positive_int(value):
    return type(value) is int and value > 0


def populated(value):
    return isinstance(value, str) and bool(value.strip())


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_index(records, field, label):
    found = {}
    for record in records:
        key = record.get(field)
        if not isinstance(key, str) or not ID.fullmatch(key):
            raise ValueError(f"{label}: invalid {field}")
        if key in found:
            raise ValueError(f"Duplicate {field} in {label}: {key}")
        found[key] = record
    return found


def ingest(source: Path, idea_id: str, out: Path):
    source, out = source.resolve(), out.resolve()
    if source == out or source in out.parents or out in source.parents:
        raise ValueError("Output and upstream must be separate, non-overlapping directories")
    if not ID.fullmatch(idea_id):
        raise ValueError("idea-id must be a safe local ID, e.g. I01")
    targets = [out / n for n in ("context.json", "design.json", "plan.md")]
    if any(p.exists() for p in targets):
        raise ValueError("Output already contains plan files; choose a new directory/version")
    fingerprints, notes = [], []

    def take(name, kind="json", required=False):
        path = source / name
        if not path.exists():
            if required:
                raise ValueError(f"Missing required input: {path}")
            return None
        data = path.read_bytes()
        fingerprints.append({"path": str(path.resolve()), "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
        text = data.decode("utf-8-sig")
        if kind == "json":
            return json.loads(text)
        if kind == "jsonl":
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            if any(not isinstance(r, dict) for r in rows):
                raise ValueError(f"Expected JSON objects in {path}")
            return rows
        notes.append({"path": str(path.resolve()), "text": text})
        return text

    ideas = take("ideas.json", required=True)
    if not isinstance(ideas, dict) or ideas.get("schema_version") != "1.0":
        raise ValueError("Supported ideas.json schema_version is 1.0")
    candidates = ideas.get("ideas")
    if not isinstance(candidates, list) or any(not isinstance(x, dict) for x in candidates):
        raise ValueError("ideas must be an array of objects")
    selected = [x for x in candidates if x.get("idea_id") == idea_id]
    if len(selected) != 1 or not positive_int(selected[0].get("version")):
        raise ValueError("Select exactly one existing idea with a positive integer version")
    idea = selected[0]
    upstream = take("context.json") or {}
    if not isinstance(upstream, dict):
        raise ValueError("Upstream context must be an object")
    evidence = take("evidence.jsonl", "jsonl") or []
    external = take("external_papers.jsonl", "jsonl") or []
    searches = take("novelty_log.jsonl", "jsonl") or []
    take("decision.md", "text")
    take(f"cards/{idea_id}.md", "text")
    # A bounded snapshot of the selected idea's explicit support and prior art.
    wanted = idea.get("basis_evidence_ids", [])
    prior = idea.get("prior_art", [])
    if not isinstance(wanted, list) or not isinstance(prior, list):
        raise ValueError("basis_evidence_ids and prior_art must be arrays")
    if any(not isinstance(eid, str) or not ID.fullmatch(eid) for eid in wanted):
        raise ValueError("basis_evidence_ids must contain valid evidence IDs")
    input_index(evidence, "evidence_id", "upstream evidence")
    wanted = set(wanted)
    for item in prior:
        if not isinstance(item, dict) or not isinstance(item.get("evidence_ids", []), list):
            raise ValueError("prior_art entries must have an evidence_ids array")
        if any(not isinstance(eid, str) or not ID.fullmatch(eid) for eid in item.get("evidence_ids", [])):
            raise ValueError("prior_art evidence_ids must contain valid IDs")
        wanted.update(item.get("evidence_ids", []))
    relevant = [e for e in evidence if e.get("evidence_id") in wanted]
    paper_ids = {e.get("paper_id") for e in relevant} | {p.get("paper_id") for p in prior}
    papers = upstream.get("papers", [])
    if not isinstance(papers, list) or any(not isinstance(p, dict) for p in papers):
        raise ValueError("Upstream papers must be an array of objects")
    paper_map = input_index(papers, "paper_id", "upstream papers")
    input_index(external, "paper_id", "external papers")
    for paper in external:
        key = paper.get("paper_id")
        if key in paper_map and paper_map[key] != paper:
            raise ValueError(f"Conflicting upstream paper ID: {key}")
        paper_map[key] = paper
    warnings = []
    # Follow only selected evidence and declared PDF identities, not every file
    # from an unrelated part of the upstream literature library.
    for ev in relevant:
        raw, expected = ev.get("source_file"), ev.get("source_sha256")
        if not raw:
            warnings.append(f"{ev['evidence_id']}: no local evidence source is bound; host source review remains necessary")
            continue
        if not populated(raw) or not Path(raw).is_absolute():
            raise ValueError("Evidence source_file must be an absolute path")
        path = Path(raw)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Source missing or empty for {ev['evidence_id']}: {path}")
        digest = digest_file(path)
        if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or digest != expected):
            raise ValueError(f"Source bytes differ from the reviewed evidence {ev['evidence_id']}: {path}")
        if expected is None:
            warnings.append(f"{ev['evidence_id']}: source_sha256 is unrecorded; this import records current bytes, not prior reading consistency")
        fingerprints.append({"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest})
    for pid in paper_ids:
        paper = paper_map.get(pid, {})
        if not paper.get("pdf_sha256"):
            continue
        assets = paper.get("assets", {})
        raw = assets.get("paper.pdf") if isinstance(assets, dict) else None
        if not populated(raw) or not Path(raw).is_absolute() or not Path(raw).is_file():
            raise ValueError(f"Selected paper {pid} has a recorded PDF identity but no local source")
        path = Path(raw)
        if digest_file(path) != paper["pdf_sha256"]:
            raise ValueError(f"Source PDF bytes differ for selected paper {pid}: {path}")
        fingerprints.append({"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": paper["pdf_sha256"]})
    # Shared sources can legitimately support several selected claims.
    fingerprints = list({item["path"]: item for item in fingerprints}.values())
    found = {e.get("evidence_id") for e in relevant}
    if wanted - found:
        warnings.append("Upstream idea refers to missing evidence: " + ", ".join(sorted(wanted - found)))
    if idea.get("status") != "recommended":
        warnings.append("Selected upstream idea is not recommended; selection is preserved, not upgraded")
    context = {"schema_version": "1.0", "mode": "light-idea",
               "upstream_directory": str(source), "idea": idea,
               "constraints": ideas.get("constraints", {}),
               "papers": [p for k, p in paper_map.items() if k in paper_ids],
               "evidence": relevant,
               "novelty_log": [n for n in searches if idea_id in n.get("idea_ids", [])],
               "narrative_inputs": notes, "input_files": fingerprints, "warnings": warnings}
    plan = read_json(ROOT / "templates/design.example.json")
    plan["selection"] = {"idea_id": idea_id, "idea_version": idea["version"]}
    plan["constraints"] = ideas.get("constraints", {})
    out.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against a concurrent writer.
    for path, value in ((out / "context.json", context), (out / "design.json", plan)):
        with path.open("x", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
    with (out / "plan.md").open("x", encoding="utf-8") as f:
        f.write((ROOT / "templates/plan.md").read_text(encoding="utf-8"))
    return {"ok": True, "workspace": str(out), "selection": plan["selection"],
            "status": "draft", "warnings": warnings}


def verify(workspace: Path):
    workspace = workspace.resolve()
    plan = read_json(workspace / "design.json")
    context = read_json(workspace / "context.json")
    errors, warnings = [], []

    def error(message):
        errors.append(message)

    def obj(value, label):
        if not isinstance(value, dict):
            error(f"{label}: expected object")
            return {}
        return value

    def rows(value, label):
        if not isinstance(value, list):
            error(f"{label}: expected array")
            return []
        result = []
        for i, row in enumerate(value):
            if not isinstance(row, dict):
                error(f"{label}[{i}]: expected object")
            else:
                result.append(row)
        return result

    def strings(value, label):
        if not isinstance(value, list) or any(not populated(x) for x in value):
            error(f"{label}: expected array of non-empty strings")
            return []
        if len(value) != len(set(value)):
            error(f"{label}: duplicate values")
        return value

    def fields(row, names, label):
        for name in names:
            if not populated(row.get(name)):
                error(f"{label}.{name}: required non-empty text")

    def index(items, key, label):
        found = {}
        for row in items:
            value = row.get(key)
            if not isinstance(value, str) or not ID.fullmatch(value):
                error(f"{label}.{key}: invalid ID")
            elif value in found:
                error(f"{label}: duplicate ID {value}")
            else:
                found[value] = row
        return found

    def refs(value, known, label):
        values = strings(value, label)
        for ref in values:
            if ref not in known:
                error(f"{label}: unknown reference {ref}")
        return values

    plan, context = obj(plan, "design"), obj(context, "context")
    if plan.get("schema_version") != "1.0" or context.get("schema_version") != "1.0":
        error("Unsupported or missing schema_version")
    if not isinstance(plan.get("design_id"), str) or not ID.fullmatch(plan["design_id"]):
        error("Invalid design_id")
    if not positive_int(plan.get("version")):
        error("Design version must be a positive integer")
    state = plan.get("status")
    if not isinstance(state, str) or state not in STATES:
        error("Unknown plan status")
        state = "invalid"
    selected = obj(plan.get("selection"), "selection")
    if not populated(selected.get("idea_id")) or not positive_int(selected.get("idea_version")):
        error("selection needs an idea ID and positive integer idea_version")
    idea = obj(context.get("idea"), "context.idea")
    if not populated(idea.get("idea_id")) or not positive_int(idea.get("version")):
        error("Context idea needs an ID and positive integer version")
    if selected.get("idea_id") != idea.get("idea_id") or selected.get("idea_version") != idea.get("version"):
        error("Plan selection does not match frozen idea ID/version")
    obj(plan.get("constraints"), "constraints")
    strings(plan.get("execution_scope"), "execution_scope")
    rows(plan.get("history"), "history")
    tables = {name: index(rows(plan.get(name), name), key, name) for name, key in TABLES.items()}
    upstream_e = index(rows(context.get("evidence", []), "context.evidence"), "evidence_id", "context.evidence")
    overlap = set(upstream_e) & set(tables["evidence"])
    if overlap:
        error("Evidence IDs collide with upstream: " + ", ".join(sorted(overlap)))
    all_evidence = {**upstream_e, **tables["evidence"]}
    scoped_evidence = set()
    for exp_id in strings(plan.get("execution_scope"), "execution_scope"):
        exp = tables["experiments"].get(exp_id, {})
        for cid in strings(exp.get("claim_ids", []), exp_id + ".claim_ids"):
            for eid in strings(tables["claims"].get(cid, {}).get("evidence_ids", []), cid + ".evidence_ids"):
                scoped_evidence.add(eid)
    required_sources = {ev.get("source_id") for eid, ev in tables["evidence"].items()
                        if eid in scoped_evidence and ev.get("verified") is True and isinstance(ev.get("source_id"), str)}
    for key, source in tables["sources"].items():
        fields(source, ["title"], key)
        if not populated(source.get("url")) and not populated(source.get("path")):
            error(f"{key}: source needs url or path")
        raw = source.get("path")
        if populated(raw):
            path = Path(raw)
            if not path.is_absolute():
                path = (workspace / path).resolve()
                if not path.is_relative_to(workspace):
                    error(f"{key}: relative source path escapes workspace")
                    continue
            expected = source.get("sha256")
            required = state in READY and key in required_sources
            issue = error if required or expected is not None else warnings.append
            if not path.is_file() or path.stat().st_size == 0:
                issue(f"{key}: local source missing or empty: {path}")
            elif expected is not None:
                if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or digest_file(path) != expected:
                    error(f"{key}: local source fingerprint drift or invalid sha256: {path}")
            elif required:
                error(f"{key}: checked evidence in execution_scope needs the reviewed source sha256")
            else:
                warnings.append(f"{key}: local source hash is unrecorded")
    for key, ev in tables["evidence"].items():
        refs([ev.get("source_id")], tables["sources"], key + ".source_id")
        fields(ev, ["statement", "locator"], key)
        if not isinstance(ev.get("access_level"), str) or ev["access_level"] not in {"metadata", "abstract", "full_text"}:
            error(f"{key}: invalid access_level")
        if type(ev.get("verified")) is not bool:
            error(f"{key}: verified must be boolean")
    for key, claim in tables["claims"].items():
        fields(claim, ["statement", "prediction", "rival", "scope"], key)
        refs(claim.get("evidence_ids"), all_evidence, key + ".evidence_ids")
    for key, resource in tables["resources"].items():
        fields(resource, ["name"], key)
        if not isinstance(resource.get("status"), str) or resource["status"] not in {"available", "unknown", "unavailable"}:
            error(f"{key}: invalid resource status")
    for key, gate in tables["gates"].items():
        fields(gate, ["description"], key)
        gate_state = gate.get("status")
        if not isinstance(gate_state, str) or gate_state not in {"confirmed", "unknown", "blocked", "not_applicable"}:
            error(f"{key}: invalid gate status")
        if isinstance(gate_state, str) and gate_state in {"confirmed", "not_applicable"}:
            fields(gate, ["basis"], key)
    for key, exp in tables["experiments"].items():
        fields(exp, ["name"], key)
        if not isinstance(exp.get("stage"), str) or exp["stage"] not in {"pilot", "exploratory", "confirmatory"}:
            error(f"{key}: invalid stage")
        refs(exp.get("claim_ids"), tables["claims"], key + ".claim_ids")
        refs(exp.get("resource_ids"), tables["resources"], key + ".resource_ids")
        refs(exp.get("gate_ids"), tables["gates"], key + ".gate_ids")
        size = obj(exp.get("sample_size"), key + ".sample_size")
        if not isinstance(size.get("status"), str) or size["status"] not in {"pending", "justified", "not_applicable"}:
            error(f"{key}: invalid sample_size.status")
        n = size.get("n")
        if n is not None and not positive_int(n):
            error(f"{key}: sample_size.n must be null or a positive integer")
    dependency_map = {}
    for key, task in tables["tasks"].items():
        refs([task.get("experiment_id")], tables["experiments"], key + ".experiment_id")
        dependency_map[key] = refs(task.get("depends_on"), tables["tasks"], key + ".depends_on")
    # Iterative topological elimination avoids recursion depth limits.
    remaining = {k: set(v) & set(dependency_map) for k, v in dependency_map.items()}
    while remaining:
        roots = {k for k, deps in remaining.items() if not deps}
        if not roots:
            error("Task dependency graph contains a cycle")
            break
        remaining = {k: deps - roots for k, deps in remaining.items() if k not in roots}
    scope = refs(plan.get("execution_scope"), tables["experiments"], "execution_scope")
    if state in READY:
        fields(plan, ["objective"], "design")
        fields(obj(plan.get("budget"), "budget"), ["summary", "basis", "limit"], "budget")
        fields(obj(plan.get("review"), "review"), ["strongest_objection", "response", "residual_risk"], "review")
        if not scope:
            error("Ready plan requires a non-empty execution_scope")
        if state == "ready_for_execution" and set(scope) != set(tables["experiments"]):
            error("ready_for_execution must cover all planned experiments")
        covered_claims = set()
        for key in scope:
            exp = tables["experiments"].get(key, {})
            if state == "ready_for_pilot" and exp.get("stage") != "pilot":
                error(f"{key}: ready_for_pilot scope can contain only pilot experiments")
            fields(exp, ["purpose", "design", "allocation", "procedure", "analysis"], key)
            if not exp.get("claim_ids"):
                error(f"{key}: ready experiment must address at least one claim")
            covered_claims.update(strings(exp.get("claim_ids"), key + ".claim_ids"))
            fields(obj(exp.get("units"), key + ".units"), ["allocation", "independent", "observation"], key + ".units")
            conditions = strings(exp.get("conditions"), key + ".conditions")
            if not conditions:
                error(f"{key}: conditions must describe the planned setting(s)")
            fields(obj(exp.get("measurement"), key + ".measurement"),
                   ["primary", "operationalization", "timepoint", "qc"], key + ".measurement")
            size = obj(exp.get("sample_size"), key + ".sample_size")
            fields(size, ["method", "basis", "n_definition"], key + ".sample_size")
            if size.get("status") == "pending":
                error(f"{key}: sample-size/information rationale is pending")
            if size.get("status") == "justified" and not positive_int(size.get("n")):
                error(f"{key}: justified quantitative sample size requires n")
            if size.get("status") == "not_applicable" and size.get("n") is not None:
                error(f"{key}: not_applicable sample size must have n=null")
            fields(obj(exp.get("decisions"), key + ".decisions"),
                   ["support", "falsify", "inconclusive", "stop"], key + ".decisions")
            for rid in strings(exp.get("resource_ids"), key + ".resource_ids"):
                resource = tables["resources"].get(rid, {})
                if resource.get("status") != "available":
                    error(f"{key}: resource {rid} is not available")
                fields(resource, ["specification", "locator", "basis"], rid)
            for gid in strings(exp.get("gate_ids"), key + ".gate_ids"):
                gate_state = tables["gates"].get(gid, {}).get("status")
                if not isinstance(gate_state, str) or gate_state not in {"confirmed", "not_applicable"}:
                    error(f"{key}: gate {gid} is unresolved")
            tasks = [t for t in tables["tasks"].values() if t.get("experiment_id") == key]
            if not tasks:
                error(f"{key}: no execution tasks")
            for task in tasks:
                tid = task["task_id"]
                fields(task, ["action", "acceptance", "owner", "effort"], tid)
                for name in ("inputs", "outputs"):
                    if not strings(task.get(name), tid + "." + name):
                        error(f"{tid}.{name}: ready task needs at least one entry")
                for dep in dependency_map.get(tid, []):
                    if tables["tasks"].get(dep, {}).get("experiment_id") not in scope:
                        error(f"{tid}: dependency {dep} lies outside execution_scope")
        if state == "ready_for_execution" and covered_claims != set(tables["claims"]):
            error("Every declared claim needs an experiment in the full execution plan")
    else:
        warnings.append("Draft/hold/input-needed plan is not declared ready for execution")
    for key, claim in tables["claims"].items():
        for eid in strings(claim.get("evidence_ids"), key + ".evidence_ids"):
            if all_evidence.get(eid, {}).get("verified") is not True:
                warnings.append(f"{key}: cited evidence {eid} is not marked verified; inspect its role")
    mode = context.get("mode")
    files = rows(context.get("input_files"), "context.input_files")
    if not isinstance(mode, str) or mode not in {"light-idea", "standalone"}:
        error("context.mode must be light-idea or standalone")
    if mode == "light-idea" and not files:
        error("Imported context requires upstream fingerprints")
    if mode == "standalone":
        warnings.append("Standalone brief: no light-idea verification is implied")
    for entry in files:
        raw = entry.get("path")
        if not populated(raw) or not Path(raw).is_absolute():
            error("Input fingerprint requires an absolute path")
            continue
        path = Path(raw)
        if not path.is_file():
            error(f"Upstream input missing: {path}")
        else:
            if path.stat().st_size != entry.get("bytes") or digest_file(path) != entry.get("sha256"):
                error(f"Upstream input drift: {path}")
    for eid, ev in upstream_e.items():
        raw, expected = ev.get("source_file"), ev.get("source_sha256")
        if populated(raw) and expected is not None:
            path = Path(raw)
            if (not path.is_absolute() or not path.is_file() or path.stat().st_size == 0
                    or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                    or digest_file(path) != expected):
                error(f"{eid}: reviewed evidence source missing, changed or invalid")
    narrative = workspace / "plan.md"
    if not narrative.is_file() or narrative.stat().st_size == 0:
        message = "plan.md is missing or empty; provide a human-readable handoff"
        if state in READY:
            error(message)
        else:
            warnings.append(message)
    warnings.extend(strings(context.get("warnings", []), "context.warnings"))
    return {"ok": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)),
            "counts": {name: len(table) for name, table in tables.items()}}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("ingest", help="Freeze a selected light-idea artifact without overwriting")
    imp.add_argument("--ideas", type=Path, required=True)
    imp.add_argument("--idea-id", required=True)
    imp.add_argument("--out", type=Path, required=True)
    check = sub.add_parser("verify", help="Check record consistency, scope and input drift")
    check.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (ingest(args.ideas, args.idea_id, args.out) if args.command == "ingest"
                  else verify(args.workspace))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)], "warnings": []}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
