#!/usr/bin/env python3
"""Bounded local computational runs and provenance. Python 3.10+, standard library.

This records observable execution; it does not certify scientific validity, complete
dependency capture, trusted timestamps, authorization, or remote job completion.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
READY = {"ready_for_pilot", "ready_for_execution"}
KINDS = {"smoke", "baseline", "pilot", "experiment", "confirmation", "diagnostic"}
ENV_KEYS = {"CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "OMP_NUM_THREADS",
            "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "PYTHONHASHSEED",
            "CUBLAS_WORKSPACE_CONFIG", "JAX_ENABLE_X64", "JAX_PLATFORMS"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value, label="ID"):
    require(isinstance(value, str) and ID.fullmatch(value), f"Invalid {label}: {value!r}")
    return value


def text_value(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def positive(value):
    return number(value) and value > 0


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path):
    def invalid(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=no_duplicates, parse_constant=invalid)


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def digest(path):
    path = Path(path)
    require(path.is_file(), f"Missing regular file: {path}")
    before = path.stat()
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
            size += len(chunk)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            f"File changed while hashing: {path}")
    return {"bytes": size, "sha256": sha.hexdigest()}


def inside(root, relative):
    require(text_value(relative), "A relative file path is required")
    relative = relative.replace("\\", "/")
    require(not relative.startswith("/") and ":" not in relative
            and all(p not in ("", ".", "..") for p in relative.split("/")),
            f"Unsafe relative path: {relative}")
    root = Path(root).resolve()
    path = root.joinpath(*relative.split("/"))
    require(path.resolve().is_relative_to(root), f"Path escapes root: {relative}")
    return path


def is_link(path):
    return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 1024)


def files_under(root):
    root = Path(root).resolve()
    for parent, directories, names in os.walk(root, followlinks=False):
        for name in sorted(directories + names):
            path = Path(parent) / name
            require(not is_link(path), f"Links/reparse points are not archived: {path}")
            require(path.resolve().is_relative_to(root), f"File escapes archive: {path}")
        for name in sorted(names):
            path = Path(parent) / name
            require(path.is_file(), f"Not a regular file: {path}")
            yield path


def record_file(root, path):
    return {"path": Path(path).relative_to(root).as_posix(), **digest(path)}


def copy_frozen(source, destination):
    original = digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Path(source).open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    require(digest(destination) == original == digest(source),
            f"Input changed while snapshotting: {source}")
    return original


@contextmanager
def locked(workspace):
    lock = workspace / ".operation.lock"
    try:
        with lock.open("x", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "created_at": now()}, stream)
    except FileExistsError as exc:
        raise ValueError("Workspace is locked. Check the recorded process before recovering a stale lock.") from exc
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def event(workspace, kind, payload, occurred_at=None):
    event_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_") + uuid.uuid4().hex[:12]
    item = {"schema_version": "1.0", "event_id": event_id, "event_type": kind,
            "occurred_at": occurred_at, "recorded_at": now(), "payload": payload}
    write_new(workspace / "events" / (event_id + ".json"), item)
    return event_id


def table(plan, field, key):
    rows = plan.get(field)
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows),
            f"design.{field} must be an object array")
    result = {}
    for row in rows:
        identity = identifier(row.get(key), key)
        require(identity not in result, f"Duplicate {key}: {identity}")
        result[identity] = row
    return result


def handoff(plan, context, scope, ready=False):
    require(isinstance(plan, dict) and isinstance(context, dict), "Design/context must be objects")
    require(plan.get("schema_version") == context.get("schema_version") == "1.0",
            "Supported design/context schema_version: 1.0")
    identifier(plan.get("design_id"), "design_id")
    require(type(plan.get("version")) is int and plan["version"] > 0, "Invalid design version")
    selection, idea = plan.get("selection", {}), context.get("idea", {})
    require(isinstance(selection, dict) and isinstance(idea, dict), "Missing design/idea identity")
    identifier(selection.get("idea_id"), "idea_id")
    require(type(selection.get("idea_version")) is int and selection["idea_version"] > 0,
            "Invalid idea version")
    require(type(idea.get("version")) is int and idea["version"] > 0, "Invalid context idea version")
    require((selection["idea_id"], selection["idea_version"]) == (idea.get("idea_id"), idea.get("version")),
            "Design selection does not match context idea/version")
    require(isinstance(scope, list) and len(scope) == len(set(scope)), "Invalid execution scope")
    experiments = table(plan, "experiments", "experiment_id")
    tasks = table(plan, "tasks", "task_id")
    for item in scope:
        identifier(item, "experiment_id")
        require(item in experiments, f"Unknown scoped experiment: {item}")
    for task in tasks.values():
        require(task.get("experiment_id") in experiments, "Task references unknown experiment")
        deps = task.get("depends_on")
        require(isinstance(deps, list) and all(isinstance(d, str) and d in tasks for d in deps),
                f"Invalid dependencies: {task['task_id']}")
    visiting, visited = set(), set()

    def walk(task_id):
        require(task_id not in visiting, "Task dependency cycle")
        if task_id not in visited:
            visiting.add(task_id)
            for dep in tasks[task_id]["depends_on"]:
                walk(dep)
            visiting.remove(task_id)
            visited.add(task_id)
    for task_id in tasks:
        walk(task_id)
    if ready:
        require(plan.get("status") in READY, "Design is not ready; preparation/implementation may continue")
        allowed = plan.get("execution_scope")
        require(isinstance(allowed, list) and scope and set(scope) <= set(allowed) <= set(experiments),
                "Campaign exceeds design execution_scope or is empty")
        if plan["status"] == "ready_for_execution":
            require(set(allowed) == set(experiments), "Full execution status must cover all experiments")
        elif plan["status"] == "ready_for_pilot":
            require(all(experiments[e].get("stage") == "pilot" for e in allowed),
                    "Pilot-ready scope includes non-pilot experiment")
        resources, gates = table(plan, "resources", "resource_id"), table(plan, "gates", "gate_id")
        for exp_id in scope:
            exp = experiments[exp_id]
            for key, lookup, accepted in (("resource_ids", resources, {"available"}),
                                           ("gate_ids", gates, {"confirmed", "not_applicable"})):
                refs = exp.get(key)
                require(isinstance(refs, list) and all(isinstance(r, str) and r in lookup for r in refs),
                        f"Invalid {key} in {exp_id}")
                require(all(lookup[r].get("status") in accepted for r in refs),
                        f"Unresolved {key} in {exp_id}")
            sample = exp.get("sample_size", {})
            require(isinstance(sample, dict) and sample.get("status") in {"justified", "not_applicable"},
                    f"Unresolved sample/information basis: {exp_id}")
            require(text_value(sample.get("basis")), f"Missing sample/information basis: {exp_id}")
            if sample["status"] == "justified":
                require(type(sample.get("n")) is int and sample["n"] > 0, f"Invalid sample size: {exp_id}")
            for task in tasks.values():
                if task["experiment_id"] == exp_id:
                    require(all(tasks[d]["experiment_id"] in scope for d in task["depends_on"]),
                            f"Task dependency outside campaign scope: {task['task_id']}")
    return experiments, tasks


def init(design, out, max_runs, max_wall_seconds, budget_basis, scope=None):
    design, out = Path(design).resolve(), Path(out).resolve()
    require(not (design == out or design in out.parents or out in design.parents),
            "Design and execution directories must be separate and non-overlapping")
    require(out != ROOT and ROOT not in out.parents, "Research outputs cannot live inside the skill")
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())),
            "Output must be new or empty; existing campaign will not be overwritten")
    require(type(max_runs) is int and max_runs > 0 and positive(max_wall_seconds), "Positive limits required")
    require(text_value(budget_basis), "Explain the budget basis")
    plan, context = read(design / "design.json"), read(design / "context.json")
    scope = plan.get("execution_scope", []) if scope is None else scope
    handoff(plan, context, scope)
    paths = [design / name for name in ("context.json", "design.json", "plan.md")]
    if (design / "protocols").exists():
        require(not is_link(design / "protocols"), "Protocol directory cannot be a link")
        paths.extend(files_under(design / "protocols"))
    for path in paths:
        require(path.is_file() and not is_link(path), f"Missing or linked handoff file: {path}")
    out.mkdir(parents=True, exist_ok=True)
    records, originals = [], []
    for path in paths:
        destination = out / "inputs" / "design" / path.relative_to(design)
        info = copy_frozen(path, destination)
        records.append(record_file(out, destination))
        originals.append({"path": str(path), **info})
    campaign = {"schema_version": "1.0", "campaign_id": "EX_" + uuid.uuid4().hex[:12],
                "created_at": now(), "design_id": plan["design_id"], "design_version": plan["version"],
                "selection": plan["selection"], "execution_scope": scope,
                "budget": {"max_runs": max_runs, "max_wall_seconds": max_wall_seconds,
                           "basis": budget_basis}}
    write_new(out / "campaign.json", campaign)
    records.append(record_file(out, out / "campaign.json"))
    write_new(out / "upstream.json", {"schema_version": "1.0", "source": str(design),
              "records": records, "originals": originals,
              "boundary": "Frozen files only; original drift is reported, not silently imported"})
    event(out, "campaign_created", {"campaign_id": campaign["campaign_id"]}, campaign["created_at"])
    return {"ok": True, "workspace": str(out), "design_status": plan.get("status"),
            "execution_scope": scope, "budget": campaign["budget"]}


def check_records(root, records):
    errors = []
    require(isinstance(records, list), "Fingerprint records must be an array")
    paths = set()
    for item in records:
        require(isinstance(item, dict), "Invalid fingerprint record")
        path = inside(root, item.get("path"))
        require(item["path"] not in paths, "Duplicate fingerprint path")
        paths.add(item["path"])
        try:
            if digest(path) != {k: item[k] for k in ("bytes", "sha256")}:
                errors.append(f"Fingerprint drift: {path}")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    return errors


def workspace_state(workspace):
    workspace = Path(workspace).resolve()
    upstream = read(workspace / "upstream.json")
    require(upstream.get("schema_version") == "1.0", "Unsupported upstream snapshot")
    errors = check_records(workspace, upstream.get("records"))
    require(not errors, "; ".join(errors))
    campaign = read(workspace / "campaign.json")
    require(campaign.get("schema_version") == "1.0", "Unsupported campaign")
    plan = read(workspace / "inputs/design/design.json")
    context = read(workspace / "inputs/design/context.json")
    require((campaign.get("design_id"), campaign.get("design_version"), campaign.get("selection")) ==
            (plan.get("design_id"), plan.get("version"), plan.get("selection")), "Campaign identity drift")
    return workspace, upstream, campaign, plan, context


def run_dir(workspace, run_id):
    return inside(workspace, "runs/" + identifier(run_id, "run_id"))


def git_info(cwd):
    def query(args):
        try:
            p = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=10)
            return p.stdout.strip() if p.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    return {"head": query(["rev-parse", "HEAD"]),
            "status": query(["status", "--porcelain=v1", "--untracked-files=normal"]),
            "boundary": "HEAD/status are context; snapshot every relevant dirty/untracked code/config file"}


def effective_env(overrides):
    return {key: overrides.get(key, os.environ.get(key)) for key in sorted(ENV_KEYS)}


def execution_ready(workspace, plan, context, scope):
    tables = handoff(plan, context, scope, ready=True)
    require(text_value((workspace / "inputs/design/plan.md").read_text(encoding="utf-8-sig")),
            "A nonempty frozen plan.md is required before preparing or starting execution")
    return tables


def prepare(workspace, spec_path):
    workspace, _, campaign, plan, context = workspace_state(workspace)
    with locked(workspace):
        _, tasks = execution_ready(workspace, plan, context, campaign["execution_scope"])
        spec = read(spec_path)
        require(isinstance(spec, dict) and spec.get("schema_version") == "1.0", "Run spec schema_version: 1.0")
        folder = run_dir(workspace, spec.get("run_id"))
        require(not folder.exists(), "Run ID already exists; use a new ID for every attempt")
        require(spec.get("experiment_id") in campaign["execution_scope"], "Experiment outside execution scope")
        task_id = spec.get("task_id")
        require(isinstance(task_id, str) and task_id in tasks and
                tasks[task_id]["experiment_id"] == spec["experiment_id"], "Task/experiment mismatch")
        require(spec.get("kind") in KINDS and text_value(spec.get("purpose")), "Run kind/purpose required")
        require(isinstance(spec.get("unit"), dict) and spec["unit"], "Explicit unit/repetition identity required")
        require(isinstance(spec.get("parameters"), dict), "Resolved parameters must be an object")
        require(positive(spec.get("timeout_seconds")), "Positive finite run timeout required")
        require(isinstance(spec.get("provenance"), dict) and
                all(text_value(spec["provenance"].get(k)) for k in ("environment", "hardware", "determinism")),
                "Environment, hardware and determinism provenance required; state actual unknowns")
        parent = spec.get("parent_run_id")
        if parent is not None:
            previous = read(run_dir(workspace, parent) / "spec.json")
            require(previous["experiment_id"] == spec["experiment_id"], "Parent experiment mismatch")
        deps = spec.setdefault("depends_on_runs", [])
        require(isinstance(deps, list) and all(isinstance(x, str) for x in deps), "Invalid depends_on_runs")
        for dep in deps:
            run_dir(workspace, dep)  # Validate ID now; acceptance is rechecked at launch.
        require(text_value(spec.get("cwd")), "Working directory required")
        cwd = Path(spec["cwd"]).resolve()
        require(cwd.is_dir(), "Working directory does not exist")
        argv = spec.get("argv")
        require(isinstance(argv, list) and argv and all(text_value(a) and "\0" not in a for a in argv),
                "Command must be a nonempty argv array without NUL characters")
        candidate = Path(argv[0])
        executable = (cwd / candidate).resolve() if (cwd / candidate).is_file() else shutil.which(argv[0])
        require(executable is not None and Path(executable).is_file(), "Executable cannot be found")
        executable = Path(executable).resolve()
        require(executable.suffix.lower() not in {".cmd", ".bat"}, "Use an explicit interpreter for scripts")
        overrides = spec.setdefault("environment", {})
        require(isinstance(overrides, dict) and set(overrides) <= ENV_KEYS
                and all(isinstance(v, str) and "\0" not in v for v in overrides.values()),
                "Only documented non-secret numerical environment overrides are supported")
        inputs = spec.get("inputs")
        require(isinstance(inputs, list) and inputs and all(isinstance(i, dict) for i in inputs),
                "Input files must include the actual code/config/environment/data dependencies")
        require(any(i.get("role") == "code" for i in inputs), "At least one code/binary input is required")
        input_paths = []
        seen = set()
        for item in inputs:
            require(text_value(item.get("path")) and text_value(item.get("role"))
                    and type(item.get("snapshot")) is bool, "Input path/role/snapshot required")
            path = (cwd / item["path"]).resolve()
            require(path.is_file() and path not in seen, f"Missing or duplicate input: {path}")
            require(not path.is_relative_to(folder), "A run cannot consume its own not-yet-produced outputs")
            seen.add(path)
            input_paths.append((item, path))
        outputs = spec.get("expected_outputs")
        require(isinstance(outputs, list) and outputs, "Declare at least one expected raw output")
        output_names = set()
        for item in outputs:
            require(isinstance(item, dict), "Output specification must be an object")
            path = inside(folder / "outputs", item.get("path"))
            key = os.path.normcase(str(path))
            require(key not in output_names, "Duplicate expected output")
            output_names.add(key)
            require(type(item.get("required")) is bool and text_value(item.get("role")),
                    "Expected output role/required flag required")
            require(type(item.get("min_bytes", 1)) is int and item.get("min_bytes", 1) >= 0,
                    "Output min_bytes must be a nonnegative integer")
        require(any(item["required"] and item.get("min_bytes", 1) > 0 for item in outputs),
                "At least one required nonempty raw output must be declared")
        folder.mkdir(parents=True)
        spec["cwd"] = str(cwd)
        spec["argv"] = [str(executable), *argv[1:]]
        frozen_inputs = []
        for index, (item, path) in enumerate(input_paths):
            item["path"] = str(path)
            data = {"source": str(path), "role": item["role"], "snapshot": None, **digest(path)}
            if item["snapshot"]:
                destination = folder / "snapshots" / f"{index:04d}" / path.name
                copy_frozen(path, destination)
                data["snapshot"] = destination.relative_to(folder).as_posix()
            frozen_inputs.append(data)
        if executable not in seen:
            frozen_inputs.append({"source": str(executable), "role": "executable", "snapshot": None,
                                  **digest(executable)})
        write_new(folder / "spec.json", spec)
        write_new(folder / "input-manifest.json", {"schema_version": "1.0", "inputs": frozen_inputs})
        write_new(folder / "environment.json", {"recorded_at": now(), "numerical_env": effective_env(overrides),
                  "git": git_info(cwd), "runner_python": sys.version, "runner_executable": sys.executable,
                  "declared_provenance": spec["provenance"],
                  "boundary": "Runner Python is not necessarily the experiment runtime; no full environment dump"})
        write_new(folder / "prepared.json", {"schema_version": "1.0", "prepared_at": now(),
                  "campaign": digest(workspace / "campaign.json"),
                  "records": [record_file(folder, p) for p in files_under(folder)]})
        event(workspace, "run_prepared", {"run_id": spec["run_id"], "experiment_id": spec["experiment_id"]}, now())
        return {"ok": True, "run_id": spec["run_id"], "state": "prepared", "command": spec["argv"]}


def check_prepared(workspace, folder):
    prep = read(folder / "prepared.json")
    errors = check_records(folder, prep.get("records"))
    require(not errors, "; ".join(errors))
    require(digest(workspace / "campaign.json") == prep.get("campaign"), "Prepared campaign drift")


def input_drift(folder):
    changes = []
    for item in read(folder / "input-manifest.json")["inputs"]:
        try:
            if digest(Path(item["source"])) != {k: item[k] for k in ("bytes", "sha256")}:
                changes.append("Input drift: " + item["source"])
        except (OSError, ValueError) as exc:
            changes.append(str(exc))
    return changes


def budget_state(workspace):
    started, consumed, unresolved = 0, 0.0, []
    for path in sorted((workspace / "events").glob("*.json")):
        item = read(path)
        if item.get("event_type") == "run_started":
            run_id = identifier(item["payload"].get("run_id"), "recorded attempt")
            require((run_dir(workspace, run_id) / "started.json").is_file(),
                    "Missing recorded attempt: " + run_id)
    for folder in sorted((workspace / "runs").glob("*")) if (workspace / "runs").exists() else []:
        require(folder.is_dir() and not is_link(folder), "Invalid run directory")
        require((folder / "started.json").is_file() or not any(
            (folder / name).exists() for name in ("result.json", "manifest.json")),
            "Missing start record for completed attempt: " + folder.name)
        if (folder / "started.json").exists():
            started += 1
            if (folder / "result.json").exists():
                result = read(folder / "result.json")
                manifest = read(folder / "manifest.json")
                key_records = [r for r in manifest["records"] if r["path"] in {"started.json", "result.json"}]
                require({r["path"] for r in key_records} == {"started.json", "result.json"}, "Unsealed budget records")
                errors = check_records(folder, key_records)
                require(not errors, "; ".join(errors))
                require(number(result.get("wall_seconds")) and result["wall_seconds"] >= 0, "Invalid duration")
                consumed += result["wall_seconds"]
                if not result.get("termination_confirmed", False):
                    unresolved.append(folder.name)
            else:
                unresolved.append(folder.name)
    return {"attempts": started, "wall_seconds": consumed, "unresolved": unresolved}


def terminate_tree(process):
    errors = []
    if os.name == "nt":
        try:
            p = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=15)
            if p.returncode != 0:
                errors.append("taskkill did not confirm descendant termination")
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            errors.append(str(exc))
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        errors.append("Root process is still running")
    return not errors, errors


def output_checks(folder, spec):
    checks = []
    for item in spec["expected_outputs"]:
        try:
            path = inside(folder / "outputs", item["path"])
            exists = path.is_file() and not is_link(path)
            size = path.stat().st_size if exists else None
            ok = (exists and size >= item.get("min_bytes", 1)) or (not exists and not item["required"])
            checks.append({**item, "exists": exists, "bytes": size, "ok": ok})
        except (OSError, ValueError) as exc:
            checks.append({**item, "ok": False, "error": str(exc)})
    return checks


def run_inventory(folder, hash_files=True):
    records, unarchived = [], []
    for parent, directories, names in os.walk(folder, followlinks=False):
        parent = Path(parent)
        kept = []
        for name in sorted(directories):
            path = parent / name
            if path == folder / "assessments":
                continue
            if is_link(path):
                unarchived.append(path.relative_to(folder).as_posix())
            else:
                kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            path = parent / name
            if path == folder / "manifest.json":
                continue
            if is_link(path) or not path.is_file():
                unarchived.append(path.relative_to(folder).as_posix())
            else:
                records.append(record_file(folder, path) if hash_files else {
                    "path": path.relative_to(folder).as_posix()})
    return records, unarchived


def seal(folder):
    records, unarchived = run_inventory(folder)
    write_new(folder / "manifest.json", {"schema_version": "1.0", "sealed_at": now(),
              "records": records, "unarchived_links_or_special_files": unarchived})


def assessment_history(folder):
    directory = folder / "assessments"
    require(not directory.exists() or not is_link(directory), "Linked assessments directory")
    paths = sorted((folder / "assessments").glob("*.json"))
    history, previous = [], None
    for path in paths:
        require(path.is_file() and not is_link(path), "Invalid assessment receipt")
        receipt = read(path)
        require(hashlib.sha256(canonical(receipt["assessment"])).hexdigest() == receipt["sha256"],
                "Assessment content drift")
        require(receipt["assessment"].get("run_id") == folder.name, "Assessment binding mismatch")
        require(receipt.get("supersedes") == previous, "Assessment correction chain is broken")
        history.append((path, receipt))
        previous = path.name
    present = {path.stem for path in paths}
    for path in sorted((folder.parents[1] / "events").glob("*.json")):
        item = read(path)
        if item.get("event_type") == "run_assessed" and item.get("payload", {}).get("run_id") == folder.name:
            require(item["payload"].get("assessment_id") in present,
                    "Missing recorded assessment; do not fall back to an older QC decision")
    return history


def latest_assessment(folder):
    history = assessment_history(folder)
    return history[-1][1]["assessment"] if history else None


def check_archive(folder):
    manifest = read(folder / "manifest.json")
    records, unarchived = run_inventory(folder)
    expected = {r["path"]: r for r in manifest["records"]}
    require(len(expected) == len(manifest["records"]), "Duplicate sealed record path")
    actual = {r["path"]: r for r in records}
    require(set(expected) == set(actual), "Untracked/removed sealed run files")
    require(expected == actual, "Fingerprint drift in sealed run: " + folder.name)
    require(not unarchived and not manifest.get("unarchived_links_or_special_files"),
            "Run contains unarchived links/special files")


def accepted_prerequisite(workspace, run_id, visiting=None):
    visiting = set() if visiting is None else visiting
    require(run_id not in visiting, "Run prerequisite cycle")
    visiting.add(run_id)
    folder = run_dir(workspace, run_id)
    check_prepared(workspace, folder)
    check_archive(folder)
    spec, result = read(folder / "spec.json"), read(folder / "result.json")
    history = assessment_history(folder)
    require(spec.get("run_id") == result.get("run_id") == run_id, "Prerequisite identity mismatch")
    require(result.get("process_status") == "succeeded" and result.get("artifacts_ok")
            and not result.get("input_drift_after") and result.get("termination_confirmed")
            and history and history[-1][1]["assessment"].get("qc_status") == "passed",
            f"Unaccepted prerequisite: {run_id}")
    for dep in spec.get("depends_on_runs", []):
        accepted_prerequisite(workspace, dep, visiting)
    visiting.remove(run_id)
    receipt_path = history[-1][0]
    return {"run_id": run_id, "result": digest(folder / "result.json"),
            "assessment_file": receipt_path.relative_to(folder).as_posix(),
            "assessment": digest(receipt_path)}


def check_run_dependencies(workspace, folder):
    spec = read(folder / "spec.json")
    return [accepted_prerequisite(workspace, dep) for dep in spec.get("depends_on_runs", [])]


def run(workspace, run_id):
    workspace, _, campaign, plan, context = workspace_state(workspace)
    with locked(workspace):
        execution_ready(workspace, plan, context, campaign["execution_scope"])
        folder = run_dir(workspace, run_id)
        check_prepared(workspace, folder)
        require(not (folder / "started.json").exists(), "Attempt already started; never rerun the same ID")
        spec = read(folder / "spec.json")
        require(spec["run_id"] == run_id, "Run ID drift")
        drift = input_drift(folder)
        require(not drift, "; ".join(drift))
        require(read(folder / "environment.json")["numerical_env"] == effective_env(spec["environment"]),
                "Numerical environment changed after preparation")
        dependencies = check_run_dependencies(workspace, folder)
        spent = budget_state(workspace)
        require(not spent["unresolved"], "An earlier attempt has unknown/live termination; inspect and recover it first")
        limits = campaign["budget"]
        require(spent["attempts"] < limits["max_runs"], "Campaign run budget exhausted")
        remaining = limits["max_wall_seconds"] - spent["wall_seconds"]
        require(remaining > 0, "Campaign process-wall budget exhausted")
        timeout = min(spec["timeout_seconds"], remaining)
        outputs = folder / "outputs"
        require(not outputs.exists(), "Output directory must not pre-exist; stale outputs are refused")
        outputs.mkdir()
        command = [a.replace("{output}", str(outputs)) for a in spec["argv"]]
        started_at = now()
        write_new(folder / "started.json", {"started_at": started_at, "runner_pid": os.getpid(),
                  "command": command, "effective_timeout_seconds": timeout,
                  "attempt_index": spent["attempts"] + 1, "dependencies": dependencies})
        event(workspace, "run_started", {"run_id": run_id, "command": command}, started_at)
        environment = os.environ.copy()
        environment.update(spec["environment"])
        environment["LIGHT_EXPERIMENT_OUT"] = str(outputs)
        before = time.monotonic()
        process, code, status, errors, stopped = None, None, "start_failed", [], True
        try:
            with (folder / "stdout.log").open("xb") as stdout, (folder / "stderr.log").open("xb") as stderr:
                options = {"start_new_session": True} if os.name != "nt" else {
                    "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                process = subprocess.Popen(command, cwd=spec["cwd"], env=environment,
                                           stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                           shell=False, **options)
                write_new(folder / "process.json", {"pid": process.pid, "recorded_at": now()})
                try:
                    code = process.wait(timeout=timeout)
                    status = "succeeded" if code == 0 else "failed"
                except subprocess.TimeoutExpired:
                    status = "timed_out"
                    stopped, errors = terminate_tree(process)
                    code = process.returncode
                except KeyboardInterrupt:
                    status = "interrupted"
                    stopped, errors = terminate_tree(process)
                    code = process.returncode
        except OSError as exc:
            errors.append(str(exc))
            if process is not None:
                stopped, termination_errors = terminate_tree(process)
                errors.extend(termination_errors)
                code = process.returncode
        elapsed = time.monotonic() - before
        checks = output_checks(folder, spec)
        _, unarchived = run_inventory(folder, hash_files=False)
        if unarchived:
            errors.append("Output links/special files are not archived: " + ", ".join(unarchived))
        after_drift = input_drift(folder)
        result = {"schema_version": "1.0", "run_id": run_id, "recorded_by": "local_runner",
                  "process_status": status, "returncode": code, "started_at": started_at,
                  "ended_at": now(), "wall_seconds": elapsed, "termination_confirmed": stopped,
                  "output_checks": checks, "artifacts_ok": all(c["ok"] for c in checks) and not unarchived,
                  "input_drift_after": after_drift, "errors": errors,
                  "scientific_outcome": "not_evaluated"}
        write_new(folder / "result.json", result)
        seal(folder)
        event(workspace, "run_finished", {"run_id": run_id, "process_status": status,
              "artifacts_ok": result["artifacts_ok"]}, result["ended_at"])
        return {"ok": status == "succeeded" and result["artifacts_ok"] and not after_drift,
                **result, "budget": budget_state(workspace)}


def assess(workspace, run_id, assessment_path):
    workspace, _, _, plan, _ = workspace_state(workspace)
    with locked(workspace):
        folder = run_dir(workspace, run_id)
        result = read(folder / "result.json")
        check_archive(folder)
        history = assessment_history(folder)
        assessment = read(assessment_path)
        require(isinstance(assessment, dict) and assessment.get("schema_version") == "1.0"
                and assessment.get("run_id") == run_id, "Assessment identity mismatch")
        require(assessment.get("qc_status") in {"pending", "passed", "failed", "unknown"}, "Invalid QC status")
        require(assessment.get("outcome") in {"support", "falsify", "inconclusive", "not_evaluated"}, "Invalid outcome")
        require(all(text_value(assessment.get(k)) for k in ("assessor", "qc_basis", "next_action")),
                "Assessment requires assessor, QC basis and next action")
        claims = table(plan, "claims", "claim_id")
        ids = assessment.get("claim_ids")
        require(isinstance(ids, list) and all(isinstance(i, str) and i in claims for i in ids), "Unknown claim IDs")
        run_spec = read(folder / "spec.json")
        experiments = table(plan, "experiments", "experiment_id")
        require(set(ids) <= set(experiments[run_spec["experiment_id"]].get("claim_ids", [])),
                "Assessment claims are outside the bound experiment")
        if assessment["qc_status"] == "passed":
            require(result["process_status"] == "succeeded" and result["artifacts_ok"]
                    and not result["input_drift_after"] and result["termination_confirmed"],
                    "Failed/incomplete/drifting run cannot pass QC")
            check_run_dependencies(workspace, folder)
        if assessment["outcome"] in {"support", "falsify"}:
            require(assessment["qc_status"] == "passed" and ids, "Scientific outcome requires passed QC and claims")
        metrics = assessment.get("metrics")
        require(isinstance(metrics, list), "metrics must be an array")
        for metric in metrics:
            require(isinstance(metric, dict) and text_value(metric.get("name"))
                    and text_value(metric.get("unit")) and text_value(metric.get("locator")),
                    "Metric needs name/unit/locator")
            require(metric.get("value") is None or number(metric.get("value")), "Metric must be finite or null")
            artifact = inside(folder, metric.get("artifact"))
            require(artifact.is_file(), "Metric artifact is missing")
            artifact_name = artifact.relative_to(folder).as_posix()
            sealed_paths = {r["path"] for r in read(folder / "manifest.json")["records"]}
            require(artifact_name in sealed_paths and (artifact_name.startswith("outputs/")
                    or artifact_name in {"stdout.log", "stderr.log"}),
                    "Metric must reference sealed raw outputs/logs, not configuration or assessment files")
            require(result["process_status"] == "succeeded" or metric["value"] is None,
                    "Failed process metrics must be null; diagnostic partial values belong in raw logs/notes")
        if assessment["outcome"] in {"support", "falsify"}:
            require(metrics and any(m["value"] is not None for m in metrics), "Outcome needs measured evidence")
        for field in ("deviations", "limitations"):
            require(isinstance(assessment.get(field), list), f"{field} must be an array")
        assessment_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_") + uuid.uuid4().hex[:8]
        receipt = {"recorded_at": now(), "supersedes": history[-1][0].name if history else None,
                   "assessment": assessment, "sha256": hashlib.sha256(canonical(assessment)).hexdigest(),
                   "boundary": "Locator existence checked; numerical extraction and scientific inference require review"}
        write_new(folder / "assessments" / (assessment_id + ".json"), receipt)
        event(workspace, "run_assessed", {"run_id": run_id, "assessment_id": assessment_id,
              "qc_status": assessment["qc_status"], "outcome": assessment["outcome"]}, now())
        return {"ok": True, "assessment_id": assessment_id, "qc_status": assessment["qc_status"],
                "outcome": assessment["outcome"]}


def note(workspace, note_path):
    workspace, *_ = workspace_state(workspace)
    with locked(workspace):
        item = read(note_path)
        require(isinstance(item, dict), "Note must be an object")
        require(all(text_value(item.get(k)) for k in ("actor", "observation", "event_type")), "Note needs actor/type/observation")
        occurred = item.get("occurred_at")
        if occurred is not None:
            parsed = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
            require(parsed.utcoffset() is not None, "Event time needs a timezone offset")
        require(isinstance(item.get("evidence_refs"), list), "Note needs evidence_refs, which may be empty for an explicit unknown")
        if item.get("run_id") is not None:
            require((run_dir(workspace, item["run_id"]) / "spec.json").exists(), "Unknown note run_id")
        return {"ok": True, "event_id": event(workspace, item["event_type"], item, occurred)}


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Access denied/unknown: conservatively alive.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def recover(workspace, run_id, reason):
    workspace, *_ = workspace_state(workspace)
    require(text_value(reason), "Recovery needs the evidence/reason for confirmed process termination")
    with locked(workspace):
        folder = run_dir(workspace, run_id)
        started = read(folder / "started.json")
        require(not (folder / "result.json").exists(), "Run already has a result; preserve it and record corrections with note")
        pids = [started.get("runner_pid")]
        if (folder / "process.json").exists():
            pids.append(read(folder / "process.json").get("pid"))
        require(not any(pid_alive(p) for p in pids), "Recorded runner/child PID still exists; do not duplicate or recover live work")
        duration = max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(started["started_at"])).total_seconds())
        checks = output_checks(folder, read(folder / "spec.json"))
        result = {"schema_version": "1.0", "run_id": run_id, "recorded_by": "operator_recovery",
                  "process_status": "interrupted", "returncode": None, "started_at": started["started_at"],
                  "ended_at": None, "recorded_at": now(), "wall_seconds": duration,
                  "duration_basis": "Conservative upper bound until recovery, not measured process runtime",
                  "termination_confirmed": True, "output_checks": checks, "artifacts_ok": False,
                  "input_drift_after": input_drift(folder), "errors": [reason],
                  "scientific_outcome": "not_evaluated"}
        write_new(folder / "result.json", result)
        seal(folder)
        event(workspace, "run_recovered", {"run_id": run_id, "reason": reason}, None)
        return {"ok": True, "run_id": run_id, "state": "interrupted", "budget": budget_state(workspace)}


def verify(workspace):
    errors, warnings, counts = [], [], {"prepared": 0, "attempted": 0, "assessed": 0}
    try:
        workspace, upstream, campaign, plan, context = workspace_state(workspace)
        handoff(plan, context, campaign["execution_scope"])
        if plan.get("status") not in READY:
            warnings.append("Imported design is not execution-ready")
        else:
            execution_ready(workspace, plan, context, campaign["execution_scope"])
        for item in upstream["originals"]:
            try:
                if digest(item["path"]) != {k: item[k] for k in ("bytes", "sha256")}:
                    warnings.append("Upstream original changed; frozen copy retained: " + item["path"])
            except (OSError, ValueError):
                warnings.append("Upstream original unavailable; frozen copy retained: " + item["path"])
        if (workspace / ".operation.lock").exists():
            warnings.append("Workspace operation lock exists; verification is a point-in-time view")
        folders = sorted((workspace / "runs").glob("*")) if (workspace / "runs").exists() else []
        for folder in folders:
            try:
                identifier(folder.name, "run directory")
                require(folder.is_dir() and not is_link(folder), "Invalid run directory")
                check_prepared(workspace, folder)
                counts["prepared"] += 1
                spec = read(folder / "spec.json")
                require(spec["run_id"] == folder.name and spec["experiment_id"] in campaign["execution_scope"], "Run binding mismatch")
                if (folder / "started.json").exists():
                    counts["attempted"] += 1
                    if not (folder / "result.json").exists():
                        warnings.append("Live or interrupted attempt, not complete: " + folder.name)
                    else:
                        result = read(folder / "result.json")
                        require(result["run_id"] == folder.name, "Result binding mismatch")
                        check_archive(folder)
                        try:
                            current_dependencies = check_run_dependencies(workspace, folder)
                            bound_dependencies = read(folder / "started.json").get("dependencies")
                            if current_dependencies and bound_dependencies != current_dependencies:
                                warnings.append("Prerequisite QC binding changed or was not captured; review: " + folder.name)
                        except (OSError, ValueError, KeyError, TypeError) as exc:
                            errors.append(f"{folder.name}: Invalid prerequisite: {exc}")
                        if result["process_status"] != "succeeded" or not result["artifacts_ok"]:
                            warnings.append("Retained unsuccessful/incomplete attempt: " + folder.name)
                        if result["input_drift_after"]:
                            errors.append("Input changed during execution: " + folder.name)
                        assessment = latest_assessment(folder)
                        if not assessment:
                            warnings.append("Scientific QC/interpretation pending: " + folder.name)
                        elif assessment.get("qc_status") != "passed":
                            warnings.append(f"QC not passed ({assessment.get('qc_status')}): {folder.name}")
                else:
                    warnings.append("Prepared, not executed: " + folder.name)
                    errors.extend(input_drift(folder))
                counts["assessed"] += len(assessment_history(folder))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{folder.name}: {exc}")
        spent = budget_state(workspace)
        if spent["unresolved"]:
            warnings.append("Inspect unknown/live process termination: " + ", ".join(spent["unresolved"]))
        for path in sorted((workspace / "events").glob("*.json")):
            item = read(path)
            require(item.get("event_id") == path.stem and item.get("recorded_at"), "Invalid event identity")
        return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": counts, "budget": spent,
                "boundary": "Integrity/relationships only; warnings and successful exit are not scientific acceptance"}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
        return {"ok": False, "errors": errors, "warnings": warnings, "counts": counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init", help="Freeze a design and create a bounded campaign; never launches work")
    p.add_argument("--design", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-runs", type=int, required=True)
    p.add_argument("--max-wall-seconds", type=float, required=True)
    p.add_argument("--budget-basis", required=True)
    p.add_argument("--experiment-id", action="append", dest="scope")
    for name in ("prepare", "run", "assess", "note", "recover", "verify"):
        p = commands.add_parser(name)
        p.add_argument("--workspace", type=Path, required=True)
        if name == "prepare":
            p.add_argument("--spec", type=Path, required=True)
        if name in {"run", "assess", "recover"}:
            p.add_argument("--run-id", required=True)
        if name in {"assess", "note"}:
            p.add_argument("--file", type=Path, required=True)
        if name == "recover":
            p.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = init(args.design, args.out, args.max_runs, args.max_wall_seconds, args.budget_basis, args.scope)
        elif args.command == "prepare":
            result = prepare(args.workspace, args.spec)
        elif args.command == "run":
            result = run(args.workspace, args.run_id)
        elif args.command == "assess":
            result = assess(args.workspace, args.run_id, args.file)
        elif args.command == "note":
            result = note(args.workspace, args.file)
        elif args.command == "recover":
            result = recover(args.workspace, args.run_id, args.reason)
        else:
            result = verify(args.workspace)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
