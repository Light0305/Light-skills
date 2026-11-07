#!/usr/bin/env python3
"""Optional research-directory registry. Standard library, no research execution."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import unicodedata
import uuid
from urllib.parse import quote

LAYOUT_ROOT = Path(__file__).resolve().parents[1]
KINDS = json.loads((LAYOUT_ROOT / "assets/layout.json").read_text(encoding="utf-8"))["kinds"]
STATES = {"planned", "active", "complete", "hold", "archived"}
START, END = "<!-- light-project:navigation:start -->", "<!-- light-project:navigation:end -->"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(title):
    title = unicodedata.normalize("NFKC", title).strip()
    require(title, "任务标题不能为空")
    return re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "-", title)[:48].rstrip(". ") or "未命名"


def inside(root, relative):
    require(isinstance(relative, str) and relative, "路径必须是项目内相对路径")
    p = PurePosixPath(relative)
    require(not p.is_absolute() and ".." not in p.parts and "\\" not in relative
            and not re.search(r"[:\x00-\x1f]", relative), f"无效相对路径：{relative}")
    path = root.joinpath(*p.parts)
    require(path.resolve().is_relative_to(root), f"路径越出项目：{relative}")
    # Includes Windows junctions, including those pointing inside the project.
    for item in (path, *path.parents):
        if item == root:
            break
        require(not linked(item),
                f"登记及受管路径不能经过链接：{item}")
    return path


def linked(path):
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def validate(root, data, check_paths=True):
    require(isinstance(data, dict) and data.get("schema_version") == "1.0"
            and data.get("layout_version") == "1.0", "不是受支持的 Light 项目登记文件；不接管同名文件")
    require(isinstance(data.get("name"), str) and data["name"].strip(), "缺少项目名称")
    records = data.get("artifacts")
    require(isinstance(records, list), "artifacts 必须为列表")
    by_key, paths, ids = {}, set(), {}
    for r in records:
        require(isinstance(r, dict) and r.get("kind") in KINDS, "未知记录类型")
        kind = KINDS[r["kind"]]
        require(isinstance(r.get("artifact_id"), str)
                and re.fullmatch(re.escape(kind["prefix"]) + r"-\d{4,}", r["artifact_id"]), "无效归档编号")
        version = r.get("version")
        require((isinstance(version, str) and re.fullmatch(r"v\d{2,}", version)
                 and int(version[1:]) > 0) if kind.get("versioned") else version is None, "无效版本")
        key = r["artifact_id"] + ("@" + version if version else "")
        require(r.get("key") == key and key not in by_key, "key 无效或重复")
        require(r["artifact_id"] not in ids or (kind.get("versioned") and ids[r["artifact_id"]] == r["kind"]),
                "归档编号重复")
        require(r.get("status") in STATES and isinstance(r.get("title"), str) and r["title"].strip(),
                "状态或标题无效")
        path = inside(root, r.get("path"))
        normalized = path.relative_to(root).as_posix().casefold()
        require(normalized not in paths, "重复登记路径（不区分大小写）")
        require(not check_paths or path.is_dir(), f"登记目录不存在：{r['path']}")
        require(isinstance(r.get("upstream"), list) and all(isinstance(x, str) for x in r["upstream"])
                and len(set(r["upstream"])) == len(r["upstream"]), "upstream 无效或重复")
        by_key[key], ids[r["artifact_id"]] = r, r["kind"]
        paths.add(normalized)
    require(sum(r["kind"] == "literature" for r in records) <= 1, "一个项目只登记一个主文献库")
    require(sum(r["kind"] == "memory" for r in records) <= 1, "一个项目只登记一个 Memory 入口")
    require(sum(r["kind"] == "workflow" for r in records) <= 1, "一个项目只登记一个 Workflow 入口")
    require(sum(r["kind"] == "write" for r in records) <= 1,
            "一个项目只登记一篇核心论文；草稿、转投和返修放同一论文工作区")
    for key, r in by_key.items():
        require(all(x in by_key and x != key for x in r["upstream"]), f"未知或自身上游：{key}")
        prior = r.get("supersedes")
        if prior is not None:
            require(prior in by_key and prior != key, f"未知前版：{key}")
            old = by_key[prior]
            require(old["artifact_id"] == r["artifact_id"] and r["version"] is not None
                    and int(old["version"][1:]) < int(r["version"][1:]), "修订版本关系无效")
    visited, active = set(), set()

    def visit(key):
        require(key not in active, "上游或修订关系存在环")
        if key in visited:
            return
        active.add(key)
        r = by_key[key]
        for parent in r["upstream"] + ([r["supersedes"]] if r.get("supersedes") else []):
            visit(parent)
        active.remove(key)
        visited.add(key)

    for key in by_key:
        visit(key)
    return by_key


def read_project(root):
    return json.loads(inside(root, "project.json").read_text(encoding="utf-8-sig"))


def escape(text):
    return re.sub(r"[\r\n]+", " ", text).replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def navigation(data, area=None):
    rows = ["| 归档记录 | 类型 | 状态 | 输入 / 前版 |", "|---|---|---|---|"]
    for r in data["artifacts"]:
        k = KINDS[r["kind"]]
        if area and k["area"] != area:
            continue
        prefix = "../" if area else ""
        path = prefix + quote(r["path"], safe="/") + "/"
        refs = r["upstream"] + (["前版 " + r["supersedes"]] if r.get("supersedes") else [])
        rows.append(f"| [{r['key']} · {escape(r['title'])}]({path}) | {k['label']} | {r['status']} | {'、'.join(refs) or '—'} |")
    return "\n".join(rows) + "\n\n归档状态仅表示任务整理进度；科学判断以各任务原生记录为准。\n"


def managed_text(path, content, initial):
    old = exact_text(path) if path.exists() else initial
    require(old.count(START) == old.count(END) and old.count(START) <= 1,
            f"导航标记损坏，请保留正文并修复：{path}")
    block = START + "\n" + content + END
    if START in old:
        start, end = old.index(START), old.index(END)
        require(start < end, f"导航标记顺序错误：{path}")
        return old[:start] + block + old[end + len(END):]
    return old + ("\n" if old.endswith("\n") else "\n\n") + block + "\n"


def exact_text(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def prepare_navigation(root, data):
    pages = {}
    readme = inside(root, "README.md")
    initial = f"# {data['name']}\n\n研究问题：待记录。\n\n当前工作与下一步：待记录。\n\n主要结论与依据：尚未记录。\n"
    pages[readme] = managed_text(readme, navigation(data), initial)
    areas = dict.fromkeys(KINDS[r["kind"]]["area"] for r in data["artifacts"])
    for area in areas:
        if any(k["area"] == area and k.get("native_overview") for k in KINDS.values()):
            continue
        path = inside(root, f"{area}/00-{area}总览.md")
        pages[path] = managed_text(path, navigation(data, area), f"# {area} 总览\n")
    return pages


def atomic_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".light-project-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def writer(root):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".light-project.lock"
    with lock.open("x", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), "created_at": now()}))
    try:
        yield
    finally:
        lock.unlink()


def new_record(data, kind, title, path=None, upstream=None):
    rule = KINDS[kind]
    number = 1 + max((int(r["artifact_id"].split("-")[-1]) for r in data["artifacts"]
                      if KINDS[r["kind"]]["prefix"] == rule["prefix"]), default=0)
    artifact_id = f"{rule['prefix']}-{number:04d}"
    version = "v01" if rule.get("versioned") else None
    if path is None:
        parts = [rule["area"]]
        if rule.get("subdir"):
            parts.append(rule["subdir"])
        if not rule.get("fixed"):
            parts.append(artifact_id + "_" + slug(title))
        if version:
            parts.append(version)
        path = "/".join(parts)
    return {"key": artifact_id + ("@" + version if version else ""), "artifact_id": artifact_id,
            "kind": kind, "title": title.strip(), "path": path, "version": version,
            "status": "planned", "upstream": upstream or [], "supersedes": None, "created_at": now()}


def operation(root, args):
    command = args.command
    created, record = None, None
    if command == "init":
        require(not (root / "project.json").exists(), "project.json 已存在，未覆盖；已有项目使用 refresh/register")
        require(args.name.strip(), "项目名称不能为空")
        data = {"schema_version": "1.0", "layout_version": "1.0", "project_id": "PRJ_" + uuid.uuid4().hex[:12],
                "name": args.name.strip(), "created_at": now(), "artifacts": []}
    else:
        data = read_project(root)
        by_key = validate(root, data)
        if command in {"add", "register"}:
            slug(args.title)
            path = args.path if command == "register" else None
            record = new_record(data, args.kind, args.title, path, args.upstream)
            if command == "register":
                location = inside(root, path)
                require(location != root and location.is_dir(), "只能登记已存在的项目内子目录")
                record["path"] = location.relative_to(root).as_posix()
                record["status"] = args.status
            else:
                created = inside(root, record["path"])
                require(not created.exists(), "任务目录已存在；使用 register 原地登记，不自动接管")
            data["artifacts"].append(record)
        elif command in {"revise", "update"}:
            require(args.key in by_key, f"未登记的 key：{args.key}")
            old = by_key[args.key]
            if command == "revise":
                require(KINDS[old["kind"]].get("versioned"), "仅设计使用版本目录；其他任务新建一轮并引用上游")
                number = max(int(r["version"][1:]) for r in data["artifacts"]
                             if r["artifact_id"] == old["artifact_id"]) + 1
                version = f"v{number:02d}"
                base = PurePosixPath(old["path"]).parent if PurePosixPath(old["path"]).name == old["version"] else (
                    PurePosixPath("Design") / (old["artifact_id"] + "_" + slug(old["title"])))
                record = {**old, "key": old["artifact_id"] + "@" + version, "version": version,
                          "path": (base / version).as_posix(), "status": "planned",
                          "supersedes": old["key"], "created_at": now()}
                data["artifacts"].append(record)
                created = inside(root, record["path"])
                require(not created.exists(), "新版本目录已存在，未覆盖")
            else:
                if args.status:
                    old["status"] = args.status
                if args.upstream is not None:
                    old["upstream"] = args.upstream
                record = old
    validate(root, data, check_paths=False)
    pages = prepare_navigation(root, data)  # Preflight before creating task directories.
    if not args.dry_run:
        if created:
            created.mkdir(parents=True, exist_ok=False)
        atomic_text(inside(root, "project.json"), json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        for path, text in pages.items():
            atomic_text(path, text)
    return {"ok": True, "dry_run": args.dry_run, "root": str(root), "record": record,
            "workspace": str(root / record["path"]) if record else None}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("init", "add", "register", "revise", "update", "refresh", "check"):
        s = sub.add_parser(name)
        s.add_argument("--root", type=Path, required=True)
        if name != "check":
            s.add_argument("--dry-run", action="store_true")
        if name == "init":
            s.add_argument("--name", required=True)
        if name in {"add", "register"}:
            s.add_argument("--kind", choices=KINDS, required=True)
            s.add_argument("--title", required=True)
            s.add_argument("--upstream", action="append", default=[])
        if name == "register":
            s.add_argument("--path", required=True)
        if name in {"revise", "update"}:
            s.add_argument("--key", required=True)
        if name in {"register", "update"}:
            s.add_argument("--status", choices=sorted(STATES), default="planned" if name == "register" else None)
        if name == "update":
            s.add_argument("--upstream", action="append", default=None)
    return p


def run(args):
    root = args.root.expanduser().resolve()
    pack = LAYOUT_ROOT.parent
    require(root != pack and pack not in root.parents, "真实研究项目请放在技能源码集合之外")
    require(not root.exists() or root.is_dir(), "项目根路径不是目录")
    require(not any((ancestor / "SKILL.md").is_file() for ancestor in (root, *root.parents)),
            "研究项目不能放在已安装 skill 内")
    if args.command == "check":
        data = read_project(root)
        validate(root, data)
        pages = prepare_navigation(root, data)
        stale = [str(p) for p, content in pages.items() if not p.exists() or exact_text(p) != content]
        return {"ok": not stale, "artifacts": len(data["artifacts"]), "stale_navigation": stale,
                "boundary": "只检查登记、路径和导航；不验证科学结论或专业记录"}
    if args.dry_run:
        return operation(root, args)
    if args.command != "init":
        require(root.is_dir(), "项目根目录不存在，请先 init")
    with writer(root):
        return operation(root, args)


def main():
    try:
        result = run(parser().parse_args())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
