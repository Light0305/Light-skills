#!/usr/bin/env python3
"""Offline material snapshots and review-record consistency checks; no scientific review."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROLES = {"manuscript", "figure", "supplement", "data", "code", "context", "reference", "render", "venue"}
CORE_ROLES = {"manuscript", "figure", "supplement", "render"}
CHECKS = {"claims", "methods", "statistics", "figures", "numerical", "literature", "reproducibility", "ethics", "venue"}
CATEGORIES = {"claim", "methods", "statistics", "figure", "numerical", "novelty", "citation", "reproducibility", "ethics", "submission", "presentation"}
CLOSED = {"verified", "dismissed"}
OWNERS = {"light-write", "light-chart", "light-diagram", "light-anaysis", "light-design", "light-experiment", "light-journal-select", "figure-workflow", "author", "specialist"}
REASSESS_FIELDS = ("severity", "category", "basis", "blocking", "required", "observation", "impact", "closure_test")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_at(value, at):
    require(isinstance(value, dict), f"{at}: expected object")
    return value


def array_at(value, at):
    require(isinstance(value, list), f"{at}: expected array")
    return value


def text_at(value, at):
    require(isinstance(value, str) and bool(value.strip()), f"{at}: expected nonempty string")
    return value


def bool_at(value, at):
    require(type(value) is bool, f"{at}: expected boolean")
    return value


def enum_at(value, options, at):
    text_at(value, at)
    require(value in options, f"{at}: must be one of {', '.join(sorted(options))}")
    return value


def strings_at(value, at):
    for index, item in enumerate(array_at(value, at)):
        text_at(item, f"{at}[{index}]")
    return value


def load_json(path):
    path = Path(path)
    require(path.stat().st_size <= 8 * 1024 * 1024, f"JSON is too large: {path}")
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=no_duplicates)


def dump_new(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def digest_file(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def packet_digest(materials):
    fields = ("id", "role", "path", "sha256", "bytes")
    canonical = [{key: m[key] for key in fields} for m in materials]
    data = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def freeze_packet(output, specs):
    inputs = []
    seen = set()
    for spec in specs:
        role, separator, name = spec.partition("=")
        require(separator and name, "--file must be role=path")
        enum_at(role, ROLES, "file role")
        source = Path(name).expanduser().resolve(strict=True)
        require(source.is_file(), f"Input must be a regular file: {source}")
        require(source not in seen, f"Duplicate input file: {source}")
        seen.add(source)
        inputs.append((role, source))
    require(inputs, "Supply at least one --file")
    output = Path(output).expanduser().resolve()
    require(not output.exists(), f"Output already exists; use a new round directory: {output}")
    output.mkdir(parents=True, exist_ok=False)
    marker = output / ".incomplete"
    marker.write_text("Snapshot incomplete; do not use until packet.json exists and verify passes.\n", encoding="utf-8")
    (output / "materials").mkdir()
    materials = []
    for index, (role, source) in enumerate(inputs, 1):
        mid = f"M{index:03d}"
        relative = Path("materials") / f"{mid}-{source.name}"
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as reader, (output / relative).open("xb") as writer:
            while chunk := reader.read(1024 * 1024):
                writer.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        copied = digest.hexdigest()
        require(digest_file(source) == (copied, size), f"Source changed while copying: {source}; snapshot incomplete")
        materials.append({"id": mid, "role": role, "path": relative.as_posix(), "source": str(source), "sha256": copied, "bytes": size})
    packet = {"schema_version": "1.0", "packet_id": packet_digest(materials), "created_at": datetime.now(timezone.utc).isoformat(), "materials": materials}
    template = Path(__file__).resolve().parents[1] / "assets" / "review-record.template.json"
    stub = load_json(template)
    stub["packet_id"] = packet["packet_id"]
    stub["coverage"] = [{"material_id": m["id"], "status": "not_read", "notes": "尚未读取；冻结仅记录版本。"} for m in materials]
    dump_new(output / "review.stub.json", stub)
    dump_new(output / "packet.json", packet)
    marker.unlink()
    return packet


def verify_packet(root):
    root = Path(root).expanduser().resolve(strict=True)
    require(not (root / ".incomplete").exists(), "Snapshot has .incomplete marker")
    packet = object_at(load_json(root / "packet.json"), "packet")
    require(packet.get("schema_version") == "1.0", "Unsupported packet schema_version")
    materials = array_at(packet.get("materials"), "materials")
    require(materials, "Packet contains no materials")
    ids, paths = set(), set()
    for m in materials:
        object_at(m, "material")
        mid = text_at(m.get("id"), "material.id")
        require(re.fullmatch(r"M\d{3,}", mid), "Invalid material ID")
        require(mid not in ids, f"Duplicate material ID: {mid}")
        ids.add(mid)
        enum_at(m.get("role"), ROLES, f"{mid}.role")
        relative = text_at(m.get("path"), f"{mid}.path")
        require(not Path(relative).is_absolute(), f"{mid}: material path must be relative")
        path = (root / relative).resolve(strict=True)
        require(path.is_relative_to(root) and path != root, f"{mid}: path escapes packet")
        require(path not in paths and path.is_file(), f"{mid}: duplicate path or non-file")
        paths.add(path)
        require(type(m.get("bytes")) is int and m["bytes"] >= 0, f"{mid}: invalid byte count")
        expected = text_at(m.get("sha256"), f"{mid}.sha256")
        require(re.fullmatch(r"[0-9a-f]{64}", expected), f"{mid}: invalid SHA-256")
        require(digest_file(path) == (expected, m["bytes"]), f"{mid}: material hash or size changed")
    require(packet.get("packet_id") == packet_digest(materials), "Packet ID does not match material manifest")
    return packet


def validate_record(record, packet):
    r = object_at(record, "review")
    enum_at(r.get("schema_version"), {"1.0", "1.1"}, "review.schema_version")
    current_schema = r["schema_version"] == "1.1"
    require(r.get("packet_id") == packet["packet_id"], "Review refers to a different packet version")
    enum_at(r.get("review_status"), {"draft", "final"}, "review_status")
    enum_at(r.get("scope"), {"full", "focused", "recheck"}, "scope")
    parent = r.get("previous_review")
    if parent is not None:
        require(current_schema, "previous_review requires review schema 1.1")
        object_at(parent, "previous_review")
        require(re.fullmatch(r"sha256:[0-9a-f]{64}", text_at(parent.get("packet_id"), "previous_review.packet_id")), "Invalid previous packet_id")
        require(re.fullmatch(r"[0-9a-f]{64}", text_at(parent.get("record_sha256"), "previous_review.record_sha256")), "Invalid previous record SHA-256")
    require(not (current_schema and r["scope"] == "recheck" and parent is None), "Schema 1.1 recheck requires previous_review")
    complete = bool_at(r.get("assessment_complete"), "assessment_complete")
    require(not (complete and r["scope"] == "focused"), "Focused review cannot be a complete assessment")
    text_at(r.get("summary"), "summary")
    strings_at(r.get("strengths"), "strengths")
    strings_at(r.get("limitations"), "limitations")
    materials = {m["id"]: m for m in packet["materials"]}

    def pointer(p, at, read=False):
        object_at(p, at)
        require(p.get("material_id") in materials, f"{at}: unknown material_id")
        text_at(p.get("anchor"), at + ".anchor")
        if read:
            require(coverage[p["material_id"]]["status"] in {"inspected", "partial"}, f"{at}: evidence requires inspected or partial material coverage")

    def evidence(value, at, required=False):
        array_at(value, at)
        require(not required or value, f"{at}: evidence is required")
        for index, p in enumerate(value):
            pointer(p, f"{at}[{index}]", read=True)

    def unique(items, field, at):
        result = {}
        for item in array_at(items, at):
            object_at(item, at)
            key = text_at(item.get(field), at + "." + field)
            require(key not in result, f"{at}: duplicate {field} {key}")
            result[key] = item
        return result

    coverage = unique(r.get("coverage"), "material_id", "coverage")
    require(set(coverage) == set(materials), "coverage must contain every packet material exactly once")
    for mid, item in coverage.items():
        enum_at(item.get("status"), {"inspected", "partial", "unreadable", "not_read", "not_applicable"}, f"coverage.{mid}.status")
        text_at(item.get("notes"), f"coverage.{mid}.notes")
        if complete and materials[mid]["role"] in CORE_ROLES:
            require(item["status"] == "inspected", f"Complete assessment requires inspected core material {mid}")
    checks = unique(r.get("checks"), "check", "checks")
    require(set(checks) == CHECKS, "checks must contain each of the nine defined checks exactly once")
    for key, item in checks.items():
        status = enum_at(item.get("status"), {"passed", "issue", "not_assessable", "not_applicable"}, key + ".status")
        text_at(item.get("notes"), key + ".notes")
        evidence(item.get("evidence"), key + ".evidence", status in {"passed", "issue"})

    claims = unique(r.get("claims"), "id", "claims")
    for cid, item in claims.items():
        text_at(item.get("text"), cid + ".text")
        bool_at(item.get("central"), cid + ".central")
        pointer(item.get("location"), cid + ".location")
        state = enum_at(item.get("assessment"), {"supported", "limited", "unsupported", "contradicted", "not_assessable"}, cid + ".assessment")
        if state != "not_assessable":
            pointer(item["location"], cid + ".location", read=True)
        evidence(item.get("evidence"), cid + ".evidence", state in {"supported", "limited", "contradicted"})
    if complete and r["review_status"] == "final":
        require(any(c["central"] for c in claims.values()), "Complete final assessment needs at least one central claim")

    sources = unique(r.get("sources"), "id", "sources")
    for sid, item in sources.items():
        text_at(item.get("title"), sid + ".title")
        url = urlparse(text_at(item.get("url"), sid + ".url"))
        require(url.scheme in {"https", "http"} and url.netloc, sid + ": expected public source URL")
        date.fromisoformat(text_at(item.get("accessed_on"), sid + ".accessed_on"))
        enum_at(item.get("access"), {"full_text", "metadata", "unavailable"}, sid + ".access")
        text_at(item.get("use"), sid + ".use")

    issues = unique(r.get("issues"), "id", "issues")
    for iid, item in issues.items():
        require(re.fullmatch(r"LR-\d{3,}", iid), f"{iid}: expected stable LR-001 style ID")
        severity = enum_at(item.get("severity"), {"critical", "major", "minor"}, iid + ".severity")
        enum_at(item.get("category"), CATEGORIES, iid + ".category")
        enum_at(item.get("basis"), {"review", "audit", "venue"}, iid + ".basis")
        enum_at(item.get("evidence_status"), {"confirmed", "reporting_gap", "unresolved"}, iid + ".evidence_status")
        enum_at(item.get("confidence"), {"high", "medium", "low"}, iid + ".confidence")
        blocking = bool_at(item.get("blocking"), iid + ".blocking")
        required = bool_at(item.get("required"), iid + ".required")
        status = enum_at(item.get("status"), {"open", "addressed", "verified", "dismissed", "deferred"}, iid + ".status")
        require(not blocking or required, f"{iid}: blocking issue must be required")
        require(severity != "critical" or (blocking and required), f"{iid}: critical must be required and blocking")
        require(severity != "major" or required, f"{iid}: major must be required")
        require(severity != "minor" or not blocking, f"{iid}: minor cannot be blocking")
        for key in ("observation", "impact", "suggested_fix", "closure_test"):
            text_at(item.get(key), iid + "." + key)
        enum_at(item.get("owner"), OWNERS, iid + ".owner")
        pointer(item.get("location"), iid + ".location")
        evidence(item.get("evidence"), iid + ".evidence", True)
        for key, known in (("claim_ids", claims), ("source_ids", sources)):
            refs = strings_at(item.get(key), iid + "." + key)
            require(len(set(refs)) == len(refs) and all(ref in known for ref in refs), f"{iid}.{key}: duplicate or unknown ID")
        evidence(item.get("resolution_evidence"), iid + ".resolution_evidence", status in CLOSED)
        if current_schema and status in CLOSED:
            closure = object_at(item.get("closure_check"), iid + ".closure_check")
            require(closure.get("packet_id") == packet["packet_id"], f"{iid}: closure_check must bind the current packet")
            method = enum_at(closure.get("method"), {"rechecked", "unchanged_evidence"}, iid + ".closure_check.method")
            text_at(closure.get("notes"), iid + ".closure_check.notes")
            require(method != "unchanged_evidence" or parent is not None, f"{iid}: unchanged evidence requires previous_review")
        if "reassessment" in item:
            require(current_schema and parent is not None, f"{iid}: reassessment requires schema 1.1 and previous_review")
            change = object_at(item["reassessment"], iid + ".reassessment")
            text_at(change.get("reason"), iid + ".reassessment.reason")
            evidence(change.get("evidence"), iid + ".reassessment.evidence", True)
        if status == "dismissed":
            text_at(item.get("dismissal_reason"), iid + ".dismissal_reason")

    readiness = object_at(r.get("readiness"), "readiness")
    text_at(readiness.get("rationale"), "readiness.rationale")
    active = [i for i in issues.values() if i["status"] not in CLOSED]
    for dimension in ("scientific", "submission"):
        options = {"hold", "revise", "ready", "not_assessable"}
        if dimension == "submission":
            options.add("not_requested")
        value = enum_at(readiness.get(dimension), options, "readiness." + dimension)
        relevant = active if dimension == "submission" else [i for i in active if i["category"] != "submission"]
        # An established scientific blocker prevents submission-ready, but it
        # does not imply that the venue/file dimension has already been checked.
        blockers = [i for i in relevant if i["blocking"] and (dimension == "scientific" or i["category"] == "submission")]
        if blockers and value != "not_requested":
            require(value == "hold", f"{dimension}: active blocking issues require hold")
        if value != "ready":
            continue
        require(r["review_status"] == "final", "Ready is only valid in a final record")
        require(not any(i["required"] for i in relevant), f"{dimension}: required issues remain unclosed")
        if dimension == "scientific":
            require(complete, "Scientific ready requires a complete assessment")
            require(any(m["role"] == "manuscript" for m in materials.values()), "Scientific ready requires manuscript material")
            require(all(checks[k]["status"] in {"passed", "not_applicable"} for k in CHECKS - {"venue"}), "Scientific checks remain incomplete or contain issues")
            require(all(c["assessment"] in {"supported", "limited"} for c in claims.values() if c["central"]), "Central claims remain unsupported, contradicted, or unassessed")
        else:
            require(checks["venue"]["status"] == "passed", "Submission ready requires verified venue check")
            require(readiness.get("scientific") == "ready", "Submission ready requires scientific ready")
    return {"materials": len(materials), "claims": len(claims), "issues": len(issues), "open_required": sum(i["required"] for i in active), "review_status": r["review_status"], "lineage": "not_checked"}


def validate_transition(record, packet, previous_record, previous_packet, previous_sha256):
    """Check one immediate parent, without claiming to verify scientific repair."""
    validate_record(record, packet)
    validate_record(previous_record, previous_packet)
    require(record["schema_version"] == "1.1", "Cross-round checks require review schema 1.1")
    parent = object_at(record.get("previous_review"), "previous_review")
    require(parent["packet_id"] == previous_packet["packet_id"], "Previous packet binding does not match")
    require(parent["record_sha256"] == previous_sha256, "Previous review record hash changed or does not match")
    old = {i["id"]: i for i in previous_record["issues"]}
    new = {i["id"]: i for i in record["issues"]}
    require(set(old) <= set(new), "Previous issues must remain traceable; missing: " + ", ".join(sorted(set(old) - set(new))))
    highest = max((int(i.split("-")[1]) for i in old), default=0)
    for iid in set(new) - set(old):
        require(int(iid.split("-")[1]) > highest, f"{iid}: allocate a new ID above the previous maximum")

    def signatures(pointers, manifest):
        materials = {m["id"]: m for m in manifest["materials"]}
        return sorted((materials[p["material_id"]]["role"], materials[p["material_id"]]["sha256"], materials[p["material_id"]]["bytes"], p["anchor"]) for p in pointers)

    for iid, item in new.items():
        prior = old.get(iid)
        changed = [key for key in REASSESS_FIELDS if prior and item[key] != prior[key]]
        require(not changed or "reassessment" in item, f"{iid}: changed {', '.join(changed)} requires reason and current evidence")
        if item["status"] in CLOSED and item["closure_check"]["method"] == "unchanged_evidence":
            require(prior is not None and prior["status"] == item["status"], f"{iid}: cannot inherit an unclosed or differently closed issue")
            require(not changed, f"{iid}: reassessed issue needs a new closure check")
            require(item.get("dismissal_reason") == prior.get("dismissal_reason"), f"{iid}: dismissal reason changed; recheck closure")
            for key in ("evidence", "resolution_evidence"):
                require(signatures(item[key], packet) == signatures(prior[key], previous_packet), f"{iid}: {key} changed; recheck closure")
            require(signatures([item["location"]], packet) == signatures([prior["location"]], previous_packet), f"{iid}: issue location changed; recheck closure")
    return {"lineage": "immediate_parent_checked", "previous_issues": len(old), "new_issues": len(set(new) - set(old))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="Copy only named files to a NEW packet directory")
    freeze.add_argument("--out", required=True)
    freeze.add_argument("--file", action="append", required=True, help="role=path; repeat for each file")
    for command in ("verify", "validate"):
        child = sub.add_parser(command)
        child.add_argument("--packet", required=True)
        if command == "validate":
            child.add_argument("--record", required=True)
            child.add_argument("--previous-packet", help="Immediate previous round packet directory; pair with --previous-record")
            child.add_argument("--previous-record", help="Immediate previous round review JSON; pair with --previous-packet")
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            p = freeze_packet(args.out, args.file)
            result = {"packet_id": p["packet_id"], "materials": len(p["materials"])}
        else:
            p = verify_packet(args.packet)
            result = {"packet_id": p["packet_id"], "materials": len(p["materials"])}
            if args.command == "validate":
                require(bool(args.previous_packet) == bool(args.previous_record), "Supply both --previous-packet and --previous-record")
                record = load_json(args.record)
                result.update(validate_record(record, p))
                require(record.get("previous_review") is None or args.previous_packet, "Bound review requires --previous-packet and --previous-record")
                if args.previous_packet:
                    previous_packet = verify_packet(args.previous_packet)
                    previous_path = Path(args.previous_record).expanduser().resolve(strict=True)
                    before = digest_file(previous_path)
                    previous_record = load_json(previous_path)
                    require(digest_file(previous_path) == before, "Previous review changed while reading")
                    result.update(validate_transition(record, p, previous_record, previous_packet, before[0]))
                elif record["scope"] == "recheck":
                    result["warning"] = "Legacy unbound recheck: issue continuity and closure inheritance were not checked."
        print(json.dumps({"ok": True, **result, "meaning": "Version/record consistency only; scientific judgments and claimed checks are not verified."}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
