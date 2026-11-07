"""File-based, project-scoped memory events. No network or language-model calls."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import uuid

SKILL_ROOT = Path(__file__).resolve().parents[1]
KINDS = {"fact", "finding", "decision", "constraint", "hypothesis", "lesson", "question", "next_step"}
EPISTEMIC = {"user_reported", "source_reported", "analyst_inference", "verified_observation"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, name, maximum=8000):
    require(isinstance(value, str) and 0 < len(value.strip()) <= maximum, f"Invalid {name}")
    return value.strip()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def timestamp(value):
    parsed = datetime.fromisoformat(text(value, "timestamp", 64).replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "Timestamps need an explicit timezone")
    return parsed.astimezone(timezone.utc)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path):
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, f"Duplicate JSON key: {k}")
            out[k] = v
        return out

    def number(value):
        result = float(value)
        require(math.isfinite(result), "Non-finite JSON number")
        return result

    def invalid(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=invalid)


def linked(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0)
                                        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    except FileNotFoundError:
        return False


def inside(root, relative):
    require(isinstance(relative, str) and relative and "\\" not in relative
            and not re.search(r"[:\x00-\x1f]", relative), "Use a project-relative POSIX path")
    rel = PurePosixPath(relative)
    require(not rel.is_absolute() and ".." not in rel.parts and bool(rel.parts), "Unsafe relative path")
    path = root.joinpath(*rel.parts)
    require(path.resolve().is_relative_to(root) and path.resolve() != root, "Path escapes project or names root")
    for part in (path, *path.parents):
        if part == root:
            break
        require(not linked(part), f"Linked path is not supported: {part}")
    return path


def project_root(project):
    root = Path(project).expanduser().resolve()
    require(root.is_dir(), "Research project does not exist")
    require(root != SKILL_ROOT.parent and SKILL_ROOT.parent not in root.parents,
            "Store research memory outside the skill source package")
    require(not any((p / "SKILL.md").is_file() for p in (root, *root.parents)), "Not a research project: skill directory")
    return root


def registry_id(root):
    p = inside(root, "project.json")
    if not p.exists():
        return None
    value = read_json(p)
    # A foreign project.json is not silently treated as our registry.
    if isinstance(value, dict) and value.get("layout_version") == "1.0" and value.get("schema_version") == "1.0":
        return text(value.get("project_id"), "registry project_id", 128)
    return None


@contextmanager
def writer(root):
    path = inside(root, "Memory/.write.lock")
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), "created_at": now()}))
    try:
        yield
    finally:
        path.unlink()


def atomic(path, value, exclusive=False):
    """Publish a complete file. Exclusive links never overwrite an existing event."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n") if not isinstance(value, str) else value
    fd, temp = tempfile.mkstemp(prefix=".memory-tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        if exclusive:
            os.link(temp, path)
        else:
            os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def file_fingerprint(path):
    before = path.stat()
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Source changed while hashing")
    return {"bytes": after.st_size, "sha256": sha.hexdigest()}


def source_shape(source):
    require(isinstance(source, dict), "Source must be an object")
    kind = source.get("kind")
    require(kind in {"file", "conversation", "web"}, "Unknown source kind")
    text(source.get("locator"), "source locator", 1000)
    if kind == "file":
        text(source.get("path"), "source path", 1000)
        require(type(source.get("bytes")) is int and source["bytes"] >= 0
                and re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")), "Invalid file fingerprint")
    else:
        text(source.get("excerpt"), "durable source excerpt", 3000)
    if "excerpt" in source:
        text(source["excerpt"], "source excerpt", 3000)
    if kind == "web":
        require(re.match(r"https?://[^\s]+\Z", source.get("url", "")), "Invalid source URL")
        datetime.strptime(source.get("accessed_on", ""), "%Y-%m-%d")


def prepare_sources(root, sources):
    require(isinstance(sources, list) and 0 < len(sources) <= 20, "Supply 1-20 explicit sources")
    result = []
    for raw in sources:
        require(isinstance(raw, dict), "Source must be an object")
        item = {k: v for k, v in raw.items() if k not in {"sha256", "bytes"}}
        if item.get("kind") == "file":
            p = inside(root, item.get("path"))
            rel = p.relative_to(root).as_posix()
            folded = rel.casefold()
            require(not (folded == "memory" or folded.startswith("memory/")) or folded.startswith("memory/notes/"),
                    "Generated memory cannot serve as its own evidence")
            require(not any(s.casefold().startswith(".env") or s.casefold() == ".git"
                            for s in p.relative_to(root).parts),
                    "Do not ingest credential or git internals")
            require(p.is_file(), f"Missing source file: {rel}")
            item.update(path=rel, **file_fingerprint(p))
            if "excerpt" in item:
                require(p.stat().st_size <= 8 * 1024 * 1024, "For large/binary files use locator and hash, without text excerpt")
                require(item["excerpt"] in p.read_text(encoding="utf-8-sig"), "Excerpt does not occur in source text")
        source_shape(item)
        result.append(item)
    return result


def entry_shape(item):
    require(isinstance(item, dict) and item.get("kind") in KINDS, "Unknown memory kind")
    require(item.get("epistemic") in EPISTEMIC, "Explicit epistemic status required")
    for name, limit in (("text", 8000), ("scope", 160), ("slot", 160)):
        text(item.get(name), name, limit)
    require(item.get("priority") in {"high", "normal", "low"}, "Invalid priority")
    require(isinstance(item.get("rationale"), str) and len(item["rationale"]) <= 4000, "Invalid rationale")
    if item["kind"] in {"decision", "lesson"} or item.get("supersedes"):
        text(item["rationale"], "decision/lesson/revision rationale", 4000)
    for field in ("depends_on", "supersedes", "tags"):
        value = item.get(field)
        require(isinstance(value, list) and len(value) == len(set(value))
                and all(isinstance(x, str) and x.strip() for x in value), f"Invalid {field}")
    require(not set(item["depends_on"]) & set(item["supersedes"]),
            "A replacement cannot depend on the memory it invalidates")
    if item.get("observed_at"):
        timestamp(item["observed_at"])
    if item.get("review_after"):
        timestamp(item["review_after"])
    require(isinstance(item.get("sources"), list) and item["sources"], "Memory needs sources")
    for s in item["sources"]:
        source_shape(s)


def apply_event(records, event):
    entries, changes = event.get("entries"), event.get("changes")
    require(isinstance(entries, list) and isinstance(changes, list) and (entries or changes), "Empty/invalid event")
    new_ids = set()
    for item in entries:
        entry_shape(item)
        mid = f"MEM-{len(records) + 1:04d}"
        require(item.get("id") == mid and mid not in new_ids, "Memory IDs must be consecutive and immutable")
        for parent in item["depends_on"] + item["supersedes"]:
            require(parent in records and parent not in new_ids, "References must point to earlier captured memory")
        for parent in item["supersedes"]:
            old = records[parent]
            require(old["status"] == "active" and (old["scope"], old["slot"]) == (item["scope"], item["slot"]),
                    "Only active memory in the same scope/slot may be superseded")
            old.update(status="superseded", status_reason=item["rationale"], status_event=event["event_id"])
        records[mid] = {**item, "status": "active", "recorded_at": event["recorded_at"],
                        "event_id": event["event_id"], "status_event": event["event_id"], "status_reason": None}
        new_ids.add(mid)
    changed = set()
    for change in changes:
        require(isinstance(change, dict), "Invalid state change")
        mid = change.get("id")
        require(mid in records and mid not in new_ids and mid not in changed, "Unknown, new or duplicate state target")
        require(records[mid]["status"] == "active", "Only active memory may be resolved or retracted")
        require(change.get("status") in {"resolved", "retracted"}, "Invalid closing state")
        if change["status"] == "resolved":
            require(records[mid]["kind"] in {"question", "next_step"}, "Resolve only an open question or next step")
        text(change.get("reason"), "closing reason", 4000)
        require(isinstance(change.get("sources"), list) and change["sources"], "Closing needs evidence")
        for s in change["sources"]:
            source_shape(s)
        records[mid].update(status=change["status"], status_reason=change["reason"], status_event=event["event_id"],
                            resolution_sources=change["sources"])
        changed.add(mid)


def load(root, at=None):
    header = read_json(inside(root, "Memory/memory.json"))
    require(isinstance(header, dict) and header.get("schema_version") == "1.0", "Unsupported memory schema")
    text(header.get("memory_id"), "memory_id", 128)
    text(header.get("name"), "project name", 500)
    current_id = registry_id(root)
    require(not header.get("project_id") or header["project_id"] == current_id, "Project identity differs from memory binding")
    folder = inside(root, "Memory/events")
    require(folder.is_dir(), "Missing event store")
    records, all_events, selected, captures = {}, [], [], {}
    previous = digest(header)
    previous_time = timestamp(header["created_at"])
    cutoff = timestamp(at) if at else None
    for seq, path in enumerate(sorted(folder.glob("*.json")), 1):
        inside(root, path.relative_to(root).as_posix())
        require(path.name == f"EVT-{seq:06d}.json", "Event gap or unrecognized event file")
        event = read_json(path)
        require(isinstance(event, dict) and event.get("schema_version") == "1.0"
                and event.get("event_id") == path.stem and event.get("memory_id") == header["memory_id"], "Event identity mismatch")
        actual_hash = event.get("event_hash")
        require(actual_hash == digest({k: v for k, v in event.items() if k != "event_hash"})
                and event.get("previous_hash") == previous, "Event integrity or history chain mismatch")
        recorded = timestamp(event["recorded_at"])
        require(recorded >= previous_time, "Event clock moved backwards")
        capture_id = text(event.get("capture_id"), "capture_id", 128)
        require(capture_id not in captures, "Duplicate capture ID in history")
        captures[capture_id] = event
        # Validate the entire history, even when the requested cutoff is earlier.
        apply_event(records, event)
        all_events.append(event)
        if cutoff is None or recorded <= cutoff:
            selected.append(event)
        previous, previous_time = actual_hash, recorded
    if cutoff is not None:
        records = {}
        for event in selected:
            apply_event(records, event)
    return {"header": header, "records": records, "events": selected, "all_events": all_events,
            "captures": captures, "last_hash": previous, "at": at}


def initialize(root, name, dry_run=False):
    text(name, "project name", 500)
    memory = inside(root, "Memory")
    require(not memory.exists() or (memory.is_dir() and not any(memory.iterdir())),
            "Memory already contains files; read/adapt it rather than overwriting")
    header = {"schema_version": "1.0", "memory_id": "MEMORY_" + uuid.uuid4().hex[:12],
              "project_id": registry_id(root), "name": name, "created_at": now()}
    if not dry_run:
        memory.mkdir(exist_ok=True)
        with writer(root):
            inside(root, "Memory/events").mkdir(exist_ok=False)
            atomic(inside(root, "Memory/memory.json"), header, exclusive=True)
    return {"ok": True, "dry_run": dry_run, "memory_id": header["memory_id"]}


def capture(root, spec, dry_run=False):
    require(isinstance(spec, dict) and spec.get("schema_version") == "1.0", "Invalid capture spec")
    text(spec.get("capture_id"), "capture_id", 128)
    text(spec.get("label"), "capture label", 500)

    def commit():
        state = load(root)
        old = state["captures"].get(spec["capture_id"])
        spec_hash = digest(spec)
        if old:
            require(old["spec_hash"] == spec_hash, "capture_id already used for different input")
            return {"ok": True, "dry_run": dry_run, "idempotent": True, "event_id": old["event_id"],
                    "memory_ids": [x["id"] for x in old["entries"]]}
        entries, changes = [], []
        require(isinstance(spec.get("items", []), list) and isinstance(spec.get("changes", []), list), "Invalid batch lists")
        require(len(spec.get("items", [])) + len(spec.get("changes", [])) <= 100, "Capture at most 100 explicit changes at once")
        for index, raw in enumerate(spec.get("items", []), 1):
            require(isinstance(raw, dict), "Memory item must be an object")
            item = {"id": f"MEM-{len(state['records']) + index:04d}", "kind": raw.get("kind"),
                    "scope": raw.get("scope", "project"), "slot": raw.get("slot"), "text": raw.get("text"),
                    "epistemic": raw.get("epistemic"), "rationale": raw.get("rationale", ""),
                    "priority": raw.get("priority", "normal"), "tags": raw.get("tags", []),
                    "depends_on": raw.get("depends_on", []), "supersedes": raw.get("supersedes", []),
                    "observed_at": raw.get("observed_at"), "review_after": raw.get("review_after"),
                    "sources": prepare_sources(root, raw.get("sources"))}
            entries.append(item)
        for raw in spec.get("changes", []):
            require(isinstance(raw, dict), "State change must be an object")
            changes.append({"id": raw.get("id"), "status": raw.get("status"), "reason": raw.get("reason"),
                            "sources": prepare_sources(root, raw.get("sources"))})
        seq = len(state["all_events"]) + 1
        event = {"schema_version": "1.0", "event_id": f"EVT-{seq:06d}", "memory_id": state["header"]["memory_id"],
                 "recorded_at": now(), "capture_id": spec["capture_id"], "spec_hash": spec_hash,
                 "label": spec["label"], "previous_hash": state["last_hash"], "entries": entries, "changes": changes}
        if state["all_events"]:
            require(timestamp(event["recorded_at"]) >= timestamp(state["all_events"][-1]["recorded_at"]), "Clock moved backwards")
        apply_event(state["records"], event)
        event["event_hash"] = digest(event)
        if not dry_run:
            atomic(inside(root, "Memory/events/" + event["event_id"] + ".json"), event, exclusive=True)
        return {"ok": True, "dry_run": dry_run, "idempotent": False, "event_id": event["event_id"],
                "memory_ids": [x["id"] for x in entries]}

    if dry_run:
        return commit()
    with writer(root):
        return commit()


def assess(root, state):
    """Freshness is reuse eligibility, never a scientific truth score."""
    records = state["records"]
    groups, conflicts, checks, memo = {}, [], {}, {}
    for mid, item in records.items():
        if item["status"] == "active":
            groups.setdefault((item["scope"], item["slot"]), []).append(mid)
    for (scope, slot), ids in groups.items():
        if len(ids) > 1:
            conflicts.append({"scope": scope, "slot": slot, "ids": ids})
    conflicting = {mid for c in conflicts for mid in c["ids"]}

    def source_check(s):
        if s["kind"] != "file":
            return "recorded_excerpt"  # Preserved claim, not independently verified.
        key = (s["path"], s["sha256"], s["bytes"])
        if key not in checks:
            try:
                p = inside(root, s["path"])
                checks[key] = "unchanged" if file_fingerprint(p) == {k: s[k] for k in ("sha256", "bytes")} else "changed"
            except (ValueError, OSError):
                checks[key] = "missing_or_unreadable"
        return checks[key]

    def check(mid):
        if mid in memo:
            return memo[mid]
        r = records[mid]
        sources = [{"kind": s["kind"], "locator": s["locator"], "path": s.get("path"), "url": s.get("url"),
                    "freshness": source_check(s)} for s in r["sources"]]
        resolution_sources = [{"kind": s["kind"], "locator": s["locator"], "path": s.get("path"),
                               "url": s.get("url"), "freshness": source_check(s)}
                              for s in r.get("resolution_sources", [])]
        reasons = []
        if r["status"] != "active":
            reasons.append("historical:" + r["status"])
        if mid in conflicting:
            reasons.append("unresolved_conflict")
        if any(s["freshness"] in {"changed", "missing_or_unreadable"} for s in sources):
            reasons.append("source_drift")
        if any(s["freshness"] in {"changed", "missing_or_unreadable"} for s in resolution_sources):
            reasons.append("resolution_source_drift")
        if r.get("review_after") and timestamp(r["review_after"]) <= timestamp(now()):
            reasons.append("review_due")
        for dep in r["depends_on"]:
            # Replay guarantees that every dependency precedes its child.
            if not memo[dep]["usable"]:
                reasons.append("dependency_needs_review:" + dep)
        memo[mid] = {"usable": not reasons, "reasons": reasons, "sources": sources,
                     "resolution_sources": resolution_sources}
        return memo[mid]

    for mid in records:
        check(mid)
    return memo, conflicts
