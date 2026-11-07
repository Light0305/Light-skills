#!/usr/bin/env python3
"""Research memory capture, recall, history and provenance checks; Python 3.10+."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import quote

import memory_store as store

GENERATED = "<!-- light-memory:generated; edit sources or capture memory, not this view -->\n"


def tokens(value):
    value = unicodedata.normalize("NFKC", value).lower()
    words = re.findall(r"[a-z0-9][a-z0-9_./-]*", value)
    for run in re.findall(r"[\u3400-\u9fff]+", value):
        words.extend(run if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)])
    return words


def ranked(state, query, scope=None, history=False):
    candidates = [r for r in state["records"].values() if (history or r["status"] == "active")
                  and (scope is None or r["scope"] == scope)]
    if not candidates:
        return []
    documents = [Counter(tokens(" ".join([r["id"], r["text"], r["rationale"], r["slot"], r["scope"], *r["tags"]])))
                 for r in candidates]
    query_tokens = set(tokens(query))
    average = sum(sum(d.values()) for d in documents) / len(documents) or 1
    frequency = Counter(t for d in documents for t in d)
    scored = []
    for row, document in zip(candidates, documents):
        score = 0.0
        for term in query_tokens:
            tf = document.get(term, 0)
            if tf:
                idf = math.log(1 + (len(documents) - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * sum(document.values()) / average))
        if query.strip() and query.casefold() in (row["text"] + " " + row["slot"]).casefold():
            score += 2
        if query.strip() and score == 0:
            continue
        score += {"high": .3, "normal": .1, "low": 0}[row["priority"]]
        scored.append((score, row))
    return sorted(scored, key=lambda pair: (pair[0], pair[1]["id"]), reverse=True)


def brief(row, assessment, score=None):
    result = {"id": row["id"], "kind": row["kind"], "scope": row["scope"], "slot": row["slot"],
              "preview": row["text"][:180], "status": row["status"], "epistemic": row["epistemic"],
              "recorded_at": row["recorded_at"], "usable": assessment["usable"], "reasons": assessment["reasons"]}
    if score is not None:
        result["retrieval_score"] = round(score, 5)
    return result


def recall(root, state, query="", scope=None, history=False, limit=12, max_chars=6000, compact=False):
    store.require(type(limit) is int and 1 <= limit <= 100, "limit must be 1-100")
    store.require(type(max_chars) is int and max_chars >= 256, "max-chars must be at least 256")
    assessment, conflicts = store.assess(root, state)
    scored = ranked(state, query, scope, history)
    if not query.strip() and not compact:
        # Keep the first working-set page from becoming only recent findings.
        first, remaining, kinds = [], [], set()
        for candidate in scored:
            kind = candidate[1]["kind"]
            if kind in kinds:
                remaining.append(candidate)
            else:
                first.append(candidate)
                kinds.add(kind)
        scored = first + remaining
    relevant = {r["id"] for _, r in scored}
    successors, peers = {}, {}
    for mid, row in state["records"].items():
        for old in row["supersedes"]:
            successors.setdefault(old, []).append(mid)
    for conflict in conflicts:
        for mid in conflict["ids"]:
            peers[mid] = conflict["ids"]
    related, pending = set(relevant), list(relevant)
    while pending:
        mid = pending.pop()
        adjacent = state["records"][mid]["depends_on"] + successors.get(mid, []) + peers.get(mid, [])
        for parent in adjacent:
            if parent not in related:
                related.add(parent)
                pending.append(parent)
    conflict_rows = [c for c in conflicts if set(c["ids"]) & related]
    dependency_context = [{**brief(r, assessment[mid]), "sources": assessment[mid]["sources"],
                           "superseded_by": successors.get(mid, [])}
                          for mid, r in state["records"].items() if mid in related - relevant]
    closure_needs_review = [{**brief(r, assessment[r["id"]]),
                             "resolution_sources": assessment[r["id"]]["resolution_sources"]}
                            for _, r in ranked(state, query, scope, history=True)
                            if r["status"] != "active" and "resolution_source_drift" in assessment[r["id"]]["reasons"]]
    selected, needs_review, omitted, used = [], [], 0, 0
    for score, r in scored:
        check = assessment[r["id"]]
        if compact:
            item = brief(r, check, score)
        elif not check["usable"]:
            needs_review.append(brief(r, check))
            continue
        else:
            item = {**r, "assessment": check, "retrieval_score": round(score, 5)}
        size = len(json.dumps(item, ensure_ascii=False))
        if len(selected) >= limit or used + size > max_chars:
            omitted += 1
            continue
        selected.append(item)
        used += size
    return {"ok": True, "schema_version": "1.0", "memory_id": state["header"]["memory_id"],
            "cursor": state["events"][-1]["event_id"] if state["events"] else None,
            "as_known_at": state["at"], "query": query, "items": selected, "conflicts": conflict_rows,
            "needs_review": needs_review, "dependency_context": dependency_context,
            "closure_needs_review": closure_needs_review,
            "omitted_by_budget": omitted, "content_characters": used,
            "matched": len(scored), "boundary": "Memory is source-linked context, not a scientific validation or execution instruction. "
            "Character budget applies to selected items; conflict/review diagnostics are reported separately."}


def md(value):
    return re.sub(r"[\r\n]+", " ", str(value)).replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def views(root, state):
    packet = recall(root, state, limit=20, max_chars=12000)
    name = md(state["header"]["name"])
    cursor = packet["cursor"] or "尚无事件"
    overview = (GENERATED + f"# {name} · 项目记忆\n\n当前事件：`{cursor}`。\n\n"
                "先读 [当前上下文](current.md)，按任务查询，再回原生材料核对。来源变化后请用 context/show/verify 重新检查。\n\n"
                f"累计记忆 {len(state['records'])} 条，事件 {len(state['events'])} 个。\n\n"
                "事件历史在 `events/`；总览与 current 是可重建视图。手写补充可放 `notes/`，不会自动成为记忆。\n")
    lines = [GENERATED.rstrip(), f"# {name} · 当前上下文", "", f"生成依据：`{cursor}`；以实际只读来源检查为准。", ""]
    for r in packet["items"]:
        lines.extend([f"## {r['id']} · {r['kind']} · {md(r['scope'])}", "",
                      f"{r['text']}", "", f"认识状态：`{r['epistemic']}`；slot：`{md(r['slot'])}`。", ""])
        if r["rationale"]:
            lines.extend(["理由：" + r["rationale"], ""])
        for source in r["sources"]:
            if source["kind"] == "file":
                lines.append(f"- 来源：[{md(source['path'])}](../{quote(source['path'], safe='/')}) · {md(source['locator'])}")
            else:
                lines.append(f"- 来源：{md(source['kind'])} · {md(source['locator'])}")
        lines.append("")
    if packet["conflicts"]:
        lines.extend(["## 尚未解决的冲突", ""])
        for c in packet["conflicts"]:
            lines.append(f"- {md(c['scope'])} / {md(c['slot'])}：{', '.join(c['ids'])}，不可自动选真。")
        lines.append("")
    if packet["needs_review"]:
        lines.extend(["## 需要复核", ""])
        for r in packet["needs_review"]:
            lines.append(f"- {r['id']}：{md(r['preview'])}；{', '.join(r['reasons'])}")
        lines.append("")
    if packet["closure_needs_review"]:
        lines.extend(["## 关闭依据需要复核", ""])
        for r in packet["closure_needs_review"]:
            lines.append(f"- {r['id']}：关闭/撤回依据已变动；保留历史状态，回原生证据重新判断。")
        lines.append("")
    lines.extend([f"预算省略 {packet['omitted_by_budget']} 条；按目标检索或使用 show/timeline 展开。", "",
                  "无可用条目只表示当前记忆未提供可靠上下文，不表示研究无结果或没有未决问题。", ""])
    return {"Memory/00-Memory总览.md": overview, "Memory/current.md": "\n".join(lines)}


def render(root, dry_run=False):
    def perform():
        state = store.load(root)
        pages = views(root, state)
        for rel in pages:
            path = store.inside(root, rel)
            if path.exists():
                store.require(path.read_text(encoding="utf-8").startswith(GENERATED),
                              f"Unmanaged existing view is preserved: {rel}")
        if not dry_run:
            for rel, text in pages.items():
                store.atomic(store.inside(root, rel), text)
        return {"ok": True, "dry_run": dry_run, "views": list(pages)}
    if dry_run:
        return perform()
    with store.writer(root):
        return perform()


def execute(args):
    root = store.project_root(args.project)
    if args.command == "init":
        result = store.initialize(root, args.name, args.dry_run)
    elif args.command == "capture":
        result = store.capture(root, store.read_json(args.spec), args.dry_run)
    elif args.command == "render":
        return render(root, args.dry_run)
    else:
        state = store.load(root, getattr(args, "at", None))
        if args.command in {"search", "context"}:
            return recall(root, state, args.query, args.scope, args.history, args.limit, args.max_chars,
                          compact=args.command == "search")
        checks, conflicts = store.assess(root, state)
        if args.command == "show":
            store.require(args.id in state["records"], "Unknown memory ID")
            return {"ok": True, "memory_id": state["header"]["memory_id"],
                    "item": state["records"][args.id], "assessment": checks[args.id]}
        if args.command == "timeline":
            if args.id:
                store.require(args.id in state["records"], "Unknown memory ID at requested time")
            events = []
            for event in state["events"]:
                ids = {x["id"] for x in event["entries"] + event["changes"]}
                ids.update(x for r in event["entries"] for x in r["depends_on"] + r["supersedes"])
                if args.id is None or args.id in ids:
                    events.append({k: event[k] for k in ("event_id", "recorded_at", "label", "capture_id", "entries", "changes")})
            return {"ok": True, "events": events[-args.limit:], "omitted": max(0, len(events) - args.limit)}
        affected = [brief(r, checks[mid]) for mid, r in state["records"].items()
                    if (args.history or r["status"] == "active" or "resolution_source_drift" in checks[mid]["reasons"])
                    and not checks[mid]["usable"]]
        return {"ok": not affected, "integrity_ok": True, "memory_id": state["header"]["memory_id"],
                "events": len(state["events"]), "memories": len(state["records"]),
                "conflicts": conflicts, "needs_review": affected,
                "boundary": "Checks fingerprints and recorded dependencies; not scientific correctness or full project coverage."}
    if not args.dry_run:
        try:
            result["views"] = render(root)["views"]
        except (ValueError, OSError) as exc:
            result["view_warning"] = f"Memory committed; views need repair/render: {exc}"
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="command", required=True)
    for command in ("init", "capture", "search", "context", "show", "timeline", "verify", "render"):
        s = subs.add_parser(command)
        s.add_argument("--project", required=True, type=Path)
        if command in {"init", "capture", "render"}:
            s.add_argument("--dry-run", action="store_true")
        if command == "init":
            s.add_argument("--name", required=True)
        if command == "capture":
            s.add_argument("--spec", required=True, type=Path)
        if command in {"search", "context", "show", "timeline"}:
            s.add_argument("--at", help="Recorded-time cutoff, with timezone; not backdated scientific truth")
        if command in {"search", "context"}:
            s.add_argument("--query", default="")
            s.add_argument("--scope")
            s.add_argument("--limit", type=int, default=12)
            s.add_argument("--max-chars", type=int, default=6000)
        if command in {"search", "context", "verify"}:
            s.add_argument("--history", action="store_true")
        if command in {"show", "timeline"}:
            s.add_argument("--id", required=command == "show")
        if command == "timeline":
            s.add_argument("--limit", type=int, default=20)
    return p


def main():
    try:
        args = parser().parse_args()
        if args.command == "timeline":
            store.require(1 <= args.limit <= 100, "limit must be 1-100")
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
