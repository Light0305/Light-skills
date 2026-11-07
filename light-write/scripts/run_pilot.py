"""Reproducible, fixed-context CLI writing pilot. Model calls require local Codex login.

This is a development evaluation, not automatic skill-discovery or expert validation.
No network service or API key is configured by this script. Raw CLI logs are retained.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "evaluations" / "2026-10-27-pilot"
COMMON = """Complete the manuscript task using only the supplied research material.
Follow the attached writing guidance, subject to the explicit manuscript request.
All guidance files needed for this fixed-context test are attached; do not open files,
invoke skills, use tools, browse, run commands, delegate, or edit any files.
Do not discuss this test or emit routing announcements. Return only the deliverable
and any short, materially necessary author note permitted by the request.
"""


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_cases():
    return [json.loads(x) for x in (BUNDLE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def snapshot(label, paths):
    entries = []
    for source, rel in paths:
        dest = BUNDLE / "snapshots" / label / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        entries.append({"path": dest.relative_to(BUNDLE).as_posix(), "sha256": digest(dest.read_bytes())})
    entries.sort(key=lambda x: x["path"])
    return {"id": digest(json.dumps(entries, sort_keys=True).encode()), "files": entries}


def prepare():
    if (BUNDLE / "registration.json").exists():
        raise SystemExit("Registration already exists; use a new bundle rather than overwriting frozen inputs.")
    upstream = Path.home() / ".codex" / "skills"
    paths = [(ROOT / "SKILL.md", "SKILL.md")]
    paths += [(p, p.relative_to(ROOT).as_posix()) for folder in ("references", "modules") for p in (ROOT / folder).rglob("*") if p.is_file()]
    light = snapshot("light-before", paths)
    upstream_paths = [(p, p.relative_to(upstream).as_posix()) for folder in ("nature-writing", "nature-polishing", "nature-shared") for p in (upstream / folder).rglob("*") if p.suffix in {".md", ".yaml"}]
    up = snapshot("upstream", upstream_paths)
    cli = shutil.which("codex.cmd") or shutil.which("codex")
    version = subprocess.run([cli, "--version"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
    dump(BUNDLE / "registration.json", {
        "registered_at": now(), "design": "fixed-context development pilot; manually routed supplied guidance; no automatic skill-discovery test",
        "arms": ["light-write", "upstream"], "cases": len(load_cases()), "repetitions": 1,
        "cli": version, "model_requested": "CLI default with --ignore-user-config", "model_effective": None,
        "settings": {"effort": "medium", "sandbox": "read-only", "ephemeral": True, "ignore_user_config": True},
        "system_instructions": "Host-provided CLI instructions not fully exposed; shared across arms. Fresh process per case/arm.",
        "tool_policy": "Prompt forbids tool calls; retain events and flag any observed use; no external source verification.",
        "review": "Two fresh model-assisted blinded reviews per pair, batches of seven; same CLI defaults. No human domain reviewers.",
        "thresholds": {"serious_errors_target": 0, "scores": "0-4 per dimension; no universal aggregate ranking", "hard_constraints": "required language, paragraph/sentence count, word range where stated; recorded separately"},
        "limitations": ["Synthetic development cases, one repetition, same underlying provider/model family for writing and review", "Model identity and full inherited system context not observable; do not claim exact model reproduction", "Snapshots identify installed local upstream files, not a verified upstream Git commit", "No paid API setup; consumes existing Codex access", "Any tuned cases become regression cases, not held-out improvement evidence"],
        "common_prompt": COMMON, "snapshots": {"light-before": light, "upstream": up},
    })


def guidance(case, arm, phase):
    if arm == "light-write":
        base = BUNDLE / "snapshots" / ("light-" + phase)
        names = ["SKILL.md", "references/integrity-and-evidence.md", "references/module-routing.md", "references/article-types.md", "references/sections.md", f"references/{'drafting' if case['task']=='draft' else 'polishing'}.md", "modules/catalog.json", f"modules/fields/{case['domain']}.md"]
        if phase != "before":
            names += ["references/argument-and-prose.md"]
        if case.get("allocation"):
            names += ["references/results-allocation.md"]
    else:
        base = BUNDLE / "snapshots" / "upstream"
        name = "nature-writing" if case["task"] == "draft" else "nature-polishing"
        manifest = (base / name / "manifest.yaml").read_text(encoding="utf-8")
        core = manifest.split("always_load:", 1)[1].split("axes:", 1)[0]
        names = [f"{name}/SKILL.md", f"{name}/manifest.yaml"]
        names += [(Path(name) / x).as_posix() for x in re.findall(r"^\s*-\s*([^#\s]+)", core, re.M)]
        # Resolve ../nature-shared without allowing paths outside the frozen bundle.
        names = [os.path.normpath(x).replace("\\", "/") for x in names]
        section = case["section"]
        if name == "nature-writing":
            section = {"results": "experiments", "methods": "method"}.get(section, section)
            names += [f"{name}/static/fragments/task/manuscript.md"]
        names += [f"{name}/static/fragments/{axis}/{value}.md" for axis, value in [("paper_type", case["upstream_type"]), ("section", section), ("language", "zh-to-en" if case["language"] == "zh" else "en"), ("journal", "generic")]]
        if case["section"] == "discussion":
            names += ["nature-shared/core/discussion-argument-language.md"]
        if case["section"] == "results" or case.get("allocation"):
            names += ["nature-shared/core/main-text-discipline.md"]
        if name == "nature-writing":
            ref = {"intro": "introduction", "abstract": "abstract", "methods": "method", "results": "experiments", "conclusion": "conclusion"}.get(case["section"])
            if ref:
                names += [f"{name}/references/{ref}.md"]
        else:
            names += [f"{name}/references/style-guardrails.md", f"{name}/references/section-moves.md"]
    files, blocks = [], []
    for name in dict.fromkeys(names):
        p = base / name
        data = p.read_bytes()  # Missing dependencies fail loudly.
        files.append({"path": p.relative_to(BUNDLE).as_posix(), "sha256": digest(data)})
        blocks.append(f"<guidance path={json.dumps(name)}>\n{data.decode('utf-8')}\n</guidance>")
    return "\n".join(blocks), files


def invoke(prompt, folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "input.txt").write_text(prompt, encoding="utf-8")
    cli = shutil.which("codex.cmd") or shutil.which("codex")
    args = [cli, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check", "--json", "-s", "read-only", "-c", 'model_reasoning_effort="medium"', "-"]
    # Empty CWD avoids project guidance/AGENTS. Shared host user instructions may still apply.
    cwd = BUNDLE / "empty-cwd"
    cwd.mkdir(exist_ok=True)
    start = now()
    t = time.monotonic()
    try:
        result = subprocess.run(args, input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=cwd, timeout=480)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or b""
        stderr = e.stderr or b""
        stdout = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
        code = -1
    (folder / "events.jsonl").write_text(stdout, encoding="utf-8")
    (folder / "stderr.txt").write_text(stderr, encoding="utf-8")
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    messages = [e["item"]["text"] for e in events if e.get("type") == "item.completed" and e.get("item", {}).get("type") == "agent_message"]
    tool_events = [e for e in events if e.get("type", "").startswith("item.") and e.get("item", {}).get("type") not in {None, "agent_message", "reasoning"}]
    output = "\n\n".join(messages)
    (folder / "output.md").write_text(output, encoding="utf-8")
    usage = next((e.get("usage") for e in reversed(events) if e.get("type") == "turn.completed"), None)
    errors = [e.get("message") or e.get("error", {}).get("message", "") for e in events if e.get("type") in {"error", "turn.failed"}]
    limit_hit = any("usage limit" in message.lower() for message in errors)
    meta = {"started_at": start, "elapsed_seconds": round(time.monotonic()-t, 2), "exit_code": code, "usage": usage, "observed_tool_events": tool_events, "completed": code == 0 and bool(output.strip()) and any(e.get("type") == "turn.completed" for e in events), "errors": errors, "usage_limit": limit_hit}
    dump(folder / "execution.json", meta)
    return output, meta


def generate(phase, workers, ids, retry_errors=False):
    cases = [c for c in load_cases() if not ids or c["id"] in ids]
    tasks = [(case, arm) for case in cases for arm in (["light-write", "upstream"] if phase == "before" else ["light-write"])]
    random.Random(2710).shuffle(tasks)
    registration = json.loads((BUNDLE / "registration.json").read_text(encoding="utf-8"))
    stop = threading.Event()

    def job(task):
        case, arm = task
        folder = BUNDLE / phase / case["id"] / arm
        attempt_suffix = ""
        if folder.exists() and any(folder.iterdir()):
            if not retry_errors:
                return f"SKIP existing attempt {phase}/{case['id']}/{arm}"
            if completed_output(folder) is not None:
                return f"SKIP completed retry {phase}/{case['id']}/{arm}"
            numbers = [int(p.name[6:]) for p in folder.glob("retry-*")
                       if p.is_dir() and p.name[6:].isdigit()]
            attempt_suffix = f"-retry-{max(numbers, default=0)+1:03d}"
            folder = folder / attempt_suffix.lstrip("-")
        if stop.is_set():
            return f"NOT ATTEMPTED after usage-limit response: {phase}/{case['id']}/{arm}"
        context, files = guidance(case, arm, phase)
        user_input = json.dumps({"source_facts": case["source_facts"], "request": case["request"]}, ensure_ascii=False, indent=2)
        prompt = COMMON + "\n" + context + "\n<manuscript_task>\n" + user_input + "\n</manuscript_task>"
        output, meta = invoke(prompt, folder)
        if meta.get("usage_limit"):
            stop.set()
        label = "upstream" if arm == "upstream" else "light-" + phase
        snap = registration["snapshots"].get(label)
        if snap is None:
            snap = json.loads((BUNDLE / f"{phase}-snapshot.json").read_text(encoding="utf-8"))
        record = {"schema_version": "1.0", "run_id": f"{phase}-{case['id']}-{arm}", "case_id": case["id"], "case_sha256": digest(json.dumps(case, ensure_ascii=False, sort_keys=True).encode()), "arm": arm, "repetition": 1, "started_at": meta["started_at"], "status": "completed" if meta["completed"] else "error", "model": {"provider": "Codex CLI authenticated provider", "requested": "CLI default (--ignore-user-config)", "effective": None}, "configuration": {"harness": registration["cli"] + " fixed-context pilot", "settings": registration["settings"], "system_instructions": registration["system_instructions"], "tool_policy": registration["tool_policy"]}, "skill_snapshot": snap["id"], "loaded_files": files, "input": prompt, "output": output, "stop_reason": "turn.completed" if meta["completed"] else "unknown/error; inspect events", "tool_evidence": ["Guidance preloaded verbatim in input; no dynamic file-loading test.", f"Observed tool events: {len(meta['observed_tool_events'])}; inspect events.jsonl"], "blind_id": "assigned in review packet", "reviews": []}
        record["run_id"] += attempt_suffix
        if meta.get("usage_limit"):
            record["stop_reason"] = "usage_limit; no writing output generated"
        dump(folder / "record.json", record)
        return f"{'OK' if meta['completed'] else 'ERROR'} {phase}/{case['id']}/{arm} {meta['elapsed_seconds']}s"

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(job, tasks):
            print(result, flush=True)


def completed_output(folder):
    """Select the latest completed attempt only if its retained text matches.

    Later failed attempts do not erase a success. A damaged later completed
    attempt must not silently fall back to older prose. Never repair records.
    """
    retries = sorted(folder.glob("retry-*/record.json"),
                     key=lambda p: int(p.parent.name[6:]) if p.parent.name[6:].isdigit() else -1)
    records = [folder / "record.json", *retries]
    selected = None
    try:
        for path in records:
            if not path.exists():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                return None
            if record.get("status") == "completed":
                selected = (path.parent / "output.md", record.get("output"))
        if selected is None:
            return None
        output, expected = selected
        if not isinstance(expected, str) or not expected.strip():
            return None
        return output if output.read_text(encoding="utf-8") == expected else None
    except (OSError, ValueError, UnicodeError):
        return None


def review(phase, workers, ids):
    cases = [c for c in load_cases() if not ids or c["id"] in ids]
    packet_dir = BUNDLE / {"before": "reviews", "after": "retests", "after2": "retests-2"}[phase]
    packet_dir.mkdir(exist_ok=True)
    jobs = []
    for reviewer in range(1, 3):
        for batch in range(2):
            packet, key = [], {}
            for index, case in enumerate(cases[batch*7:(batch+1)*7]):
                variants = []
                previous = "before" if phase == "after" else "after"
                arms = [("before", "light-write"), ("before", "upstream")] if phase == "before" else [(previous, "light-write"), (phase, "light-write")]
                random.Random(2700 + reviewer*100 + index).shuffle(arms)
                for j, (p, arm) in enumerate(arms):
                    out = completed_output(BUNDLE / p / case["id"] / arm)
                    if out is None:
                        continue
                    blind = f"Q{reviewer}{batch}{index}{j}"
                    key[blind] = {"phase": p, "arm": arm, "case_id": case["id"], "output_path": out.relative_to(BUNDLE).as_posix()}
                    variants.append({"blind_id": blind, "text": out.read_text(encoding="utf-8")})
                if len(variants) == 2:
                    packet.append({"case_id": case["id"], "source_facts": case["source_facts"], "request": case["request"], "rubric": case["rubric"], "variants": variants})
            if packet:
                folder = packet_dir / f"reviewer-{reviewer}-batch-{batch+1}"
                if not (folder / "packet.json").exists():
                    dump(folder / "blind-key.json", key)
                    dump(folder / "packet.json", packet)
                else:
                    # Preserve the exact already-frozen blinded order on reruns.
                    packet = json.loads((folder / "packet.json").read_text(encoding="utf-8"))
                jobs.append((folder, packet))
    prompt = """You are a model-assisted scholarly writing reviewer, not a human field expert. Rate each anonymized response against the supplied facts, task, and rubric. You do not know the writing system. Do not use tools, files, external sources, or skills. Do not infer that a polished voice proves scientific quality. A defensible new interpretation or proposed future experiment is allowed if clearly framed and supported; invented completed studies are not. Material numerical facts, mathematical quantifiers, causal scope, narrator/author attribution, and counterevidence matter. Judge the complete deliverable; literal number preservation is not mandatory for a discussion if the request permits synthesis and no numerical meaning is changed. Judge word limits on the requested prose only, excluding permitted notes. Reward substantive synthesis and argumentative force as well as appropriate uncertainty. Do not require experimental proof for interpretive scholarship.
Return ONLY JSON: {"reviews":[{"case_id":"...","blind_id":"...","serious_failures":[{"category":"fabrication|fact_drift|overclaim|hidden_counterevidence|scope_violation","quote":"exact output excerpt","reason":"..."}],"scores":{"factual_fidelity":0,"evidence_calibration":0,"task_completion":0,"argument_quality":0,"domain_appropriateness":0,"language_quality":0,"gap_handling":null},"rationale":"specific strengths and weaknesses with short exact excerpts","suggested_repair":"..."}],"pairwise":[{"case_id":"...","preferred":"blind ID or tie","reason":"..."}]}. Score applicable dimensions 0-4 (4 excellent, 3 minor edits, 2 substantial edits, 1 poor, 0 unusable); gap_handling may be null. Do not give a single overall score. All annotations must be based on provided evidence.\n"""

    def job(item):
        folder, packet = item
        if (folder / "ratings.json").exists():
            return f"SKIP {folder.name}"
        output, meta = invoke(prompt + json.dumps(packet, ensure_ascii=False), folder)
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", output.strip())
        try:
            value = json.loads(clean)
            dump(folder / "ratings.json", value)
            return f"OK {phase} {folder.name} {len(value.get('reviews', []))} reviews"
        except json.JSONDecodeError:
            return f"ERROR {folder}: non-JSON review retained"

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(job, jobs):
            print(result, flush=True)


def after_snapshot(phase):
    if phase == "before":
        raise SystemExit("Use prepare for the initial snapshot")
    if (BUNDLE / f"{phase}-snapshot.json").exists():
        raise SystemExit("Frozen snapshot already exists; choose a new phase")
    paths = [(ROOT / "SKILL.md", "SKILL.md")]
    paths += [(p, p.relative_to(ROOT).as_posix()) for folder in ("references", "modules") for p in (ROOT / folder).rglob("*") if p.is_file()]
    dump(BUNDLE / f"{phase}-snapshot.json", snapshot("light-" + phase, paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "generate", "review", "snapshot-after"])
    parser.add_argument("--phase", choices=["before", "after", "after2"], default="before")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--retry-errors", action="store_true", help="Keep the failed attempt and create a new retry directory; consumes Codex allowance")
    args = parser.parse_args()
    if args.action == "prepare": prepare()
    elif args.action == "generate": generate(args.phase, args.workers, args.cases, args.retry_errors)
    elif args.action == "review": review(args.phase, args.workers, args.cases)
    else: after_snapshot(args.phase)


if __name__ == "__main__":
    main()
