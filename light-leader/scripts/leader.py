#!/usr/bin/env python3
"""Local research workflow ledger. Records work; never executes a skill or job."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- light-leader:generated; edit workflow through leader.py -->"
STATES = {"pending", "running", "blocked", "completed", "failed", "cancelled"}
TRANSITIONS = {"pending": {"running", "blocked", "cancelled"},
               "running": {"completed", "failed", "blocked", "cancelled"},
               "blocked": {"pending", "cancelled"}, "completed": set(),
               "failed": set(), "cancelled": set()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label, maximum=8000):
    require(isinstance(value, str) and 0 < len(value.strip()) <= maximum, f"Invalid {label}")
    return value.strip()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, f"Duplicate JSON key: {k}")
            result[k] = v
        return result

    def number(raw):
        value = float(raw)
        require(math.isfinite(value), "Non-finite number")
        return value

    def invalid(raw):
        raise ValueError(f"Invalid JSON constant: {raw}")

    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=invalid)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


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
    require(not rel.is_absolute() and ".." not in rel.parts and rel.parts, "Unsafe relative path")
    path = root.joinpath(*rel.parts)
    require(path.resolve().is_relative_to(root) and path.resolve() != root, "Path escapes project")
    for part in (path, *path.parents):
        if part == root:
            break
        require(not linked(part), f"Linked path is not supported: {part}")
    return path


def project_root(value):
    root = Path(value).expanduser().resolve()
    require(root.is_dir(), "Project does not exist")
    require(root != ROOT.parent and ROOT.parent not in root.parents,
            "Store project outputs outside the skill source package")
    require(not any((p / "SKILL.md").is_file() for p in (root, *root.parents)), "Not a research project")
    return root


def registry_id(root):
    path = inside(root, "project.json")
    if not path.exists():
        return None
    value = read(path)
    if isinstance(value, dict) and value.get("schema_version") == value.get("layout_version") == "1.0":
        return text(value.get("project_id"), "project_id", 128)
    return None


def fingerprint(path):
    require(path.is_file(), f"Missing source file: {path}")
    value, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
            size += len(chunk)
    return {"sha256": value.hexdigest(), "bytes": size}


def refs(root, values, bind):
    require(isinstance(values, list) and len(values) <= 100, "Expected at most 100 file references")
    result = []
    for value in values:
        require(isinstance(value, dict), "File reference must be an object")
        path = inside(root, value.get("path"))
        rel = path.relative_to(root).as_posix()
        require(rel.split("/")[0].casefold() != "workflow", "Workflow cannot cite itself as evidence")
        require(not any(x.casefold().startswith(".env") or x.casefold() == ".git"
                        for x in path.relative_to(root).parts), "Private configuration is not workflow evidence")
        record = {"path": rel, "locator": text(value.get("locator"), "source locator", 2000)}
        if bind:
            record.update(fingerprint(path))
        else:
            require(isinstance(value.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", value["sha256"])
                    and type(value.get("bytes")) is int and value["bytes"] >= 0, "Invalid source fingerprint")
            record.update(sha256=value["sha256"], bytes=value["bytes"])
        result.append(record)
    return result


def strings(value, label, nonempty=False):
    require(isinstance(value, list) and len(value) <= 100 and (value or not nonempty), f"Invalid {label}")
    result = [text(x, label, 2000) for x in value]
    require(len(set(result)) == len(result), f"Duplicate {label}")
    return result


def objective(value, number):
    require(isinstance(value, dict), "Objective must be an object")
    return {"id": f"OBJ-{number:04d}", "goal": text(value.get("goal"), "goal"),
            "scope": text(value.get("scope"), "scope"),
            "success": strings(value.get("success"), "success criteria", True),
            "stop_rule": text(value.get("stop_rule"), "stop rule"),
            "authorization_basis": text(value.get("authorization_basis"), "authorization basis"),
            "status": "active"}


def catalog(roots=None):
    routes = read(ROOT / "assets/routes.json")
    search = [Path(x).expanduser().resolve() for x in roots] if roots else [ROOT.parent]
    for route in routes:
        entries = []
        for base in search:
            for relative in route["entries"]:
                path = base / relative / "SKILL.md"
                if path.is_file():
                    entries.append(str(path.resolve()))
        route["available_entries"] = sorted(set(entries))
    return routes


def assessment(root, state):
    result = {}
    for key, task in state["tasks"].items():
        reasons = []
        if task["superseded_by"]:
            reasons.append("superseded_by: " + ", ".join(task["superseded_by"]))
        for ref in task["inputs"] + task.get("evidence", []):
            try:
                path = inside(root, ref["path"])
                current = fingerprint(path)
                if current != {k: ref[k] for k in ("bytes", "sha256")}:
                    reasons.append("source_changed: " + ref["path"])
            except (OSError, ValueError) as exc:
                reasons.append("source_unavailable: " + ref["path"] + ": " + str(exc))
        result[key] = reasons
    # Dependencies can reference a later-listed task; converge independently of insertion order.
    for _ in state["tasks"]:
        changed = False
        for key, task in state["tasks"].items():
            for parent in task["depends_on"]:
                reason = "dependency_unusable: " + parent
                if (state["tasks"][parent]["status"] != "completed" or result[parent]) and reason not in result[key]:
                    result[key].append(reason)
                    changed = True
        if not changed:
            break
    return result


def execution_recovery(task):
    """Return the native entry when blocked work may still have an active process."""
    if task["status"] != "blocked" or task.get("replacement_reconciliation"):
        return None
    starts = [u for u in task["updates"] if u["status"] == "running"]
    return starts[-1]["execution_ref"] if starts else None


def execute(root, state, raw, bind=True):
    require(isinstance(raw, dict), "Operation must be an object")
    action = raw.get("action")
    op = {"action": action}
    tasks = state["tasks"]
    if action == "objective":
        require(not any(t["status"] == "running" for t in tasks.values()), "Reconcile running tasks before replacing the objective")
        if bind:
            require(not any(execution_recovery(t) for t in tasks.values()),
                    "Reconcile blocked native execution before replacing the objective")
        op["reason"] = text(raw.get("reason"), "objective change reason")
        value = objective(raw.get("objective"), state["objective_count"] + 1)
        state["objective_count"] += 1
        state["objective"] = dict(value)
        op["objective"] = value
        return op
    if action == "close":
        status = raw.get("status")
        require(state["objective"]["status"] == "active" and status in {"complete", "hold", "stopped"}, "Invalid objective closure")
        op.update(status=status, reason=text(raw.get("reason"), "closure reason"))
        if status == "complete":
            require(not any(t["status"] == "running" for t in tasks.values()), "Running tasks remain")
            if bind:
                require(not any(execution_recovery(t) for t in tasks.values()),
                        "Reconcile blocked native execution before completing the objective")
            required = [t for t in tasks.values() if t["objective_id"] == state["objective"]["id"]
                        and t["required"] and not t["superseded_by"]]
            require(required and all(t["status"] == "completed" for t in required), "Required work remains")
            if bind:
                checks = assessment(root, state)
                require(not any(checks[t["id"]] for t in required), "Required results need review")
        state["objective"]["status"] = status
        state["objective"]["closure_reason"] = op["reason"]
        return op
    if action == "add":
        require(state["objective"]["status"] == "active", "Set a new active objective before adding work")
        key = raw.get("id")
        require(isinstance(key, str) and re.fullmatch(r"T\d{4,}", key) and key not in tasks, "New unique task ID required")
        known = {x["id"] for x in read(ROOT / "assets/routes.json")}
        require(raw.get("skill") in known, "Unknown skill route")
        deps = strings(raw.get("depends_on", []), "dependencies")
        require(all(x in tasks and x != key for x in deps), "Dependencies must refer to existing tasks")
        prior = raw.get("supersedes")
        require(prior is None or (prior in tasks and tasks[prior]["status"] != "running"), "Unknown or running superseded task")
        require(type(raw.get("required", True)) is bool, "required must be boolean")
        require(prior is None or not tasks[prior]["required"] or raw.get("required", True),
                "Replacement must preserve required responsibility; change objective explicitly to change scope")
        workspace = text(raw.get("workspace"), "workspace", 1000)
        inside(root, workspace)
        budget = raw.get("budget")
        require(isinstance(budget, dict) and budget.get("status") in {"bounded", "unknown", "not_applicable"}, "Invalid budget")
        budget = {"status": budget["status"], "basis": text(budget.get("basis"), "budget basis")}
        if budget["status"] == "bounded":
            budget["limits"] = text(raw["budget"].get("limits"), "actual budget limits")
        op.update(id=key, skill=raw["skill"], title=text(raw.get("title"), "task title", 500),
                  question=text(raw.get("question"), "task question"), workspace=workspace,
                  inputs=refs(root, raw.get("inputs", []), bind), depends_on=deps,
                  expected_outputs=strings(raw.get("expected_outputs"), "expected outputs", True),
                  acceptance=text(raw.get("acceptance"), "acceptance criteria"),
                  stop_rule=text(raw.get("stop_rule"), "task stop rule"),
                  required=raw.get("required", True), budget=budget, supersedes=prior)
        for relative in op["expected_outputs"]:
            inside(root, relative)
        if prior:
            op["reason"] = text(raw.get("reason"), "revision reason")
            if bind and execution_recovery(tasks[prior]):
                text(raw.get("reconciliation"), "Reconcile blocked native execution before replacement")
            if "reconciliation" in raw:
                op["reconciliation"] = text(raw["reconciliation"], "native execution reconciliation")
            # Preserve previous work but make the supersession visible on reads.
            tasks[prior]["superseded_by"].append(key)
            if op.get("reconciliation"):
                tasks[prior]["replacement_reconciliation"] = op["reconciliation"]
        tasks[key] = {k: v for k, v in op.items() if k != "action"}
        tasks[key].update(status="pending", objective_id=state["objective"]["id"], superseded_by=[], updates=[])
        return op
    require(action == "transition" and raw.get("id") in tasks, "Unknown operation or task")
    key, status = raw["id"], raw.get("status")
    task = tasks[key]
    require(task["objective_id"] == state["objective"]["id"], "Task belongs to a previous objective; create a new task")
    require(state["objective"]["status"] == "active" or
            (task["status"] == "running" and status in {"completed", "failed", "blocked", "cancelled"}) or
            (task["status"] == "blocked" and status == "cancelled"),
            "Closed objective allows reconciliation only; set a new objective to resume work")
    require(status in TRANSITIONS[task["status"]], f"Invalid transition: {task['status']} -> {status}")
    op.update(id=key, status=status, reason=text(raw.get("reason"), "transition reason"))
    if status == "running":
        require(not task["superseded_by"], "Task superseded; use its replacement")
        if bind:
            require(not assessment(root, state)[key], "Inputs/dependencies need review before starting")
        op["execution_ref"] = text(raw.get("execution_ref"), "execution reference (native run/job/workspace)")
        require(task["budget"]["status"] != "unknown", "Resolve actual execution budget before starting this task")
    if task["status"] == "blocked" or (task["status"] == "running" and status == "cancelled"):
        op["reconciliation"] = text(raw.get("reconciliation"), "reconciliation of existing work/process")
    if status == "completed":
        op["evidence"] = refs(root, raw.get("evidence", []), bind)
        require(op["evidence"], "Completion needs actual output evidence")
        require(set(task["expected_outputs"]).issubset({x["path"] for x in op["evidence"]}), "Completion evidence must cover expected outputs")
        op["verification"] = text(raw.get("verification"), "verification performed and limits")
        if bind:
            require(not assessment(root, state)[key], "Inputs/dependencies changed; revise rather than silently rebinding")
        task["evidence"] = op["evidence"]
        task["verification"] = op["verification"]
    task["updates"].append(op)
    task["status"] = status
    return op


def load(root):
    data = read(inside(root, "Workflow/workflow.json"))
    require(isinstance(data, dict) and data.get("schema_version") == "1.0", "Unsupported workflow file")
    require(isinstance(data.get("workflow_id"), str) and data["workflow_id"].startswith("WF_"), "Invalid workflow identity")
    current_id = registry_id(root)
    require(not data.get("project_id") or data["project_id"] == current_id, "Workflow belongs to another project or its bound registry is missing")
    state = {"objective": objective(data["initial_objective"], 1), "objective_count": 1, "tasks": {}}
    require(isinstance(data.get("events"), list), "Events must be a list")
    seen = set()
    for revision, event in enumerate(data["events"], 1):
        require(event.get("revision") == revision and event.get("request_id") not in seen, "Invalid revision/request history")
        text(event.get("request_id"), "request_id", 128)
        text(event.get("recorded_at"), "event timestamp", 80)
        seen.add(event["request_id"])
        require(event.get("event_hash") == digest({k: v for k, v in event.items() if k != "event_hash"}), "Workflow event changed")
        require(isinstance(event.get("operations"), list) and 0 < len(event["operations"]) <= 100, "Invalid event operations")
        for operation in event["operations"]:
            normalized = execute(root, state, operation, bind=False)
            require(normalized == operation, "Malformed normalized operation")
    require(data.get("revision") == len(data["events"]), "Workflow revision mismatch")
    return data, state


@contextmanager
def lock(root):
    directory = inside(root, "Workflow")
    directory.mkdir(exist_ok=True)
    path = inside(root, "Workflow/.write.lock")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Workflow write lock exists; inspect the writer before recovering it")
    try:
        os.write(fd, f"pid={os.getpid()}\n".encode())
        yield
    finally:
        os.close(fd)
        path.unlink()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".leader-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def render(root):
    data, state = load(root)
    goal = state["objective"]
    lines = [MARKER, "# 项目工作流", "", f"当前目标：{goal['goal']}", "",
             f"范围：{goal['scope']}", "", f"目标状态：{goal['status']}；修订：{data['revision']}", "",
             "这里只记录工作交接。科学结论、验收和执行状态回专业文件核对。", ""]
    checks = assessment(root, state)
    for key, task in state["tasks"].items():
        lines.extend([f"- {key} [{task['status']}] {task['title']} → {task['skill']}；{task['workspace']}"])
        if checks[key]:
            lines.append("  需复核：" + "; ".join(checks[key]))
        if task["superseded_by"]:
            lines.append("  后继任务：" + ", ".join(task["superseded_by"]))
    path = inside(root, "Workflow/00-Workflow总览.md")
    require(not path.exists() or path.read_text(encoding="utf-8").startswith(MARKER), "Refuse to replace a handwritten workflow overview")
    atomic(path, ("\n".join(lines) + "\n").encode("utf-8"))
    return {"ok": True, "path": str(path)}


def mutate(root, command, spec, dry_run=False):
    def perform():
        path = inside(root, "Workflow/workflow.json")
        if command == "init":
            require(not path.exists(), "Workflow already exists; resume it")
            overview = inside(root, "Workflow/00-Workflow总览.md")
            require(not overview.exists(), "Existing overview; inspect it before initializing")
            value = objective(spec.get("objective"), 1)
            data = {"schema_version": "1.0", "workflow_id": "WF_" + uuid.uuid4().hex,
                    "project_id": registry_id(root), "created_at": now(),
                    "initial_objective": value, "revision": 0, "events": []}
            result = {"ok": True, "revision": 0, "workflow_id": data["workflow_id"]}
        else:
            data, state = load(root)
            request_id = text(spec.get("request_id"), "request_id", 128)
            request_hash = digest(spec)
            existing = next((x for x in data["events"] if x["request_id"] == request_id), None)
            if existing:
                require(existing["request_hash"] == request_hash, "request_id reused with different content")
                return {"ok": True, "idempotent": True, "revision": data["revision"], "applied_revision": existing["revision"]}
            require(type(spec.get("expected_revision")) is int and spec["expected_revision"] == data["revision"], "Stale revision; reread and reconcile before applying")
            raw_ops = spec.get("operations")
            require(isinstance(raw_ops, list) and 0 < len(raw_ops) <= 100, "Expected 1..100 operations")
            operations = [execute(root, state, op) for op in raw_ops]
            event = {"revision": data["revision"] + 1, "request_id": request_id,
                     "request_hash": request_hash, "recorded_at": now(), "operations": operations}
            event["event_hash"] = digest(event)
            data["events"].append(event)
            data["revision"] += 1
            result = {"ok": True, "revision": data["revision"], "operations": len(operations)}
        if dry_run:
            result["dry_run"] = True
            return result
        atomic(path, json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8") + b"\n")
        try:
            result["view"] = render(root)["path"]
        except (ValueError, OSError) as exc:
            result["view_warning"] = "Workflow committed; render needs repair: " + str(exc)
        return result
    if dry_run:
        return perform()
    with lock(root):
        return perform()


def report(root, command, task_id=None):
    data, state = load(root)
    checks = assessment(root, state)
    warnings = []
    recovery = []
    for key, task in state["tasks"].items():
        if task["status"] == "running":
            warnings.append({"id": key, "reason": "Reconcile the recorded native run/job/work before any repeat"})
        native = execution_recovery(task)
        if native:
            recovery.append({"id": key, "execution_ref": native,
                             "reason": "Blocked after execution began; inspect native process/output before retry or scope change"})
    if task_id:
        require(task_id in state["tasks"], "Unknown task")
        return {"ok": True, "revision": data["revision"], "task": state["tasks"][task_id],
                "needs_review": checks[task_id]}
    candidates = [t for key, t in state["tasks"].items() if t["status"] == "pending"
                  and not t["superseded_by"] and t["objective_id"] == state["objective"]["id"]
                  and not checks[key] and state["objective"]["status"] == "active"
                  and t["budget"]["status"] != "unknown"]
    affected = [{"id": key, "reasons": value} for key, value in checks.items() if value
                and state["tasks"][key]["objective_id"] == state["objective"]["id"]
                and not state["tasks"][key]["superseded_by"]]
    result = {"ok": not affected if command == "verify" else True,
              "integrity_ok": True, "revision": data["revision"], "objective": state["objective"],
              "tasks": list(state["tasks"].values()) if command != "next" else candidates,
              "needs_review": affected, "running": warnings, "recovery_required": recovery,
              "boundary": "Candidate readiness is file/dependency bookkeeping, not scientific acceptance, tool availability or execution authorization."}
    return result


def resume(root, memory_skill=None, query="", max_chars=6000):
    """Read both native ledgers without treating memory text as executable instructions."""
    require(type(max_chars) is int and max_chars >= 256, "max-chars must be at least 256")
    workflow = report(root, "status") if inside(root, "Workflow/workflow.json").is_file() else None
    candidates = report(root, "next")["tasks"] if workflow else []
    memory = {"status": "not_initialized"}
    # Discover only trusted skill entry paths, never code provided by a research project.
    if inside(root, "Memory").exists():
        entries = [Path(memory_skill).expanduser().resolve()] if memory_skill else [
            Path(p).parent for r in catalog() if r["id"] == "light-memory" for p in r["available_entries"]]
        script = next((p / "scripts/memory.py" for p in entries if (p / "scripts/memory.py").is_file()), None)
        if script is None:
            memory = {"status": "reader_unavailable", "reason": "Read the existing Memory with its installed light-memory; pass --memory-skill when needed"}
        else:
            try:
                process = subprocess.run([sys.executable, "-X", "utf8", "-B", str(script), "context",
                                          "--project", str(root), "--query", query, "--max-chars", str(max_chars)],
                                         capture_output=True, text=True, encoding="utf-8", timeout=30)
                if process.returncode != 0:
                    memory = {"status": "read_failed", "reason": (process.stderr or process.stdout).strip()[:2000]}
                else:
                    packet = json.loads(process.stdout)
                    require(isinstance(packet, dict) and packet.get("ok") is True, "Invalid memory context response")
                    memory = {"status": "read", "packet": packet}
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                memory = {"status": "read_failed", "reason": str(exc)[:2000]}
    return {"ok": True, "workflow": workflow, "candidates": candidates, "memory": memory,
            "boundary": "Read-only recovery packet. Recheck original sources and native jobs; memory and candidates do not authorize execution or establish scientific readiness."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("catalog")
    p.add_argument("--skills-root", action="append")
    for name in ("init", "apply", "status", "next", "show", "verify", "render", "history", "resume"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        if name in {"init", "apply"}:
            p.add_argument("--spec", required=True)
            p.add_argument("--dry-run", action="store_true")
        if name == "show":
            p.add_argument("--id", required=True)
        if name == "resume":
            p.add_argument("--memory-skill", help="Installed light-memory directory; optional sibling discovery")
            p.add_argument("--query", default="")
            p.add_argument("--max-chars", type=int, default=6000)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = {"ok": True, "routes": catalog(args.skills_root)}
        else:
            root = project_root(args.project)
            if args.command in {"init", "apply"}:
                spec = read(args.spec)
                require(isinstance(spec, dict), "Spec must be an object")
                result = mutate(root, args.command, spec, args.dry_run)
            elif args.command == "render":
                with lock(root):
                    result = render(root)
            elif args.command == "history":
                data, _ = load(root)
                result = {"ok": True, "workflow_id": data["workflow_id"], "events": data["events"]}
            elif args.command == "resume":
                result = resume(root, args.memory_skill, args.query, args.max_chars)
            else:
                result = report(root, args.command, getattr(args, "id", None))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0 if result["ok"] else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
