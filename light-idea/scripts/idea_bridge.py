#!/usr/bin/env python3
"""Local-only literature handoff and referential checks; never scientific scoring."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4


ASSETS = ("meta.json", "paper.md", "paper.pdf", "source_map.json", "note.md",
          "note.en.md", "paper.zh.md", "translation_notes.md")
RUN_FILES = ("query_plan.json", "synthesis.json", "search_log.json", "saturation.json",
             "citation_edges.jsonl", "citation_analysis.json")
STATUSES = {"candidate", "shortlisted", "recommended", "hold", "rejected", "archived"}
NOVELTY = {"unsearched", "inconclusive", "overlap_found", "differentiated_within_scope"}
INTENTS = {"duplicate", "mechanism", "adjacent", "skeptic", "citation"}
CLAIM_TYPES = {"empirical", "causal", "theoretical", "methodological", "qualitative", "resource"}
KINDS = {"author_claim", "observation", "limitation", "method", "counterevidence"}
DESIGN_FIELDS = ("prediction", "rival_explanation", "test", "baseline", "metric",
                 "success", "falsifier", "negative_result_value", "first_step", "budget", "failure_modes")
RESEARCH_FIELDS = ("question", "hypothesis", "claim_type", "scope", "prior_art")
TEST_FIELDS = ("prediction", "rival_explanation", "test", "baseline", "metric", "success", "falsifier")


class InputError(ValueError):
    """An actionable input or filesystem problem."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read JSON {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise InputError(f"{path}:{number}: expected a JSON object")
            rows.append(value)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read JSONL {path}: {exc}") from exc
    return rows


def object_at(path: Path) -> dict:
    value = read_json(path)
    if not isinstance(value, dict):
        raise InputError(f"{path}: expected a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def idea_fingerprint(idea: dict) -> str:
    """Bind a search to scientific content, excluding title/status/editorial fields."""
    content = {key: idea.get(key) for key in RESEARCH_FIELDS}
    if isinstance(idea.get("prior_art"), list):
        content["prior_art"] = sorted(
            [{key: item.get(key) for key in ("paper_id", "overlap", "delta")}
             if isinstance(item, dict) else item for item in idea["prior_art"]],
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    design = idea.get("design")
    content["design"] = {key: design.get(key) for key in TEST_FIELDS} if isinstance(design, dict) else design
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def fingerprints(workspace: Path) -> dict:
    """Read-only helper; attaching the output to a log is not a search."""
    doc = object_at(workspace / "ideas.json")
    ideas = doc.get("ideas")
    if not isinstance(ideas, list) or any(not isinstance(x, dict) for x in ideas):
        raise InputError("ideas must be an array of objects")
    result = {}
    for idea in ideas:
        iid = require_id(idea, "idea_id", "ideas")
        if iid in result or type(idea.get("version")) is not int or idea["version"] < 1:
            raise InputError(f"Duplicate idea_id or invalid version: {iid}")
        result[iid] = {"version": idea["version"], "sha256": idea_fingerprint(idea)}
    return {"ok": True, "ideas": result,
            "boundary": "Content identifiers only; no search, novelty assessment or scientific review was performed."}


def doi_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).casefold()


def choice(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False


def require_id(record: dict, field: str, location: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise InputError(f"{location}: invalid or missing {field}")
    return value


def contained(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise InputError(f"Literature folder escapes input root: {relative!r}")
    return target


def atomic_text(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def ingest(literature: Path | None, run: Path | None, out: Path,
           paper_ids: set[str] | None = None, include_excluded: bool = False,
           force: bool = False) -> dict:
    if not literature and not run:
        raise InputError("Provide --literature or --run (or both).")
    literature = literature.resolve() if literature else None
    run = run.resolve() if run else None
    if literature and (literature / "Literature").is_dir() and not (literature / "manifest.json").is_file():
        literature = literature / "Literature"
    for root in (literature, run):
        if root and not root.is_dir():
            raise InputError(f"Input directory does not exist: {root}")
    out = out.resolve()
    if any(root and out.is_relative_to(root) for root in (literature, run)):
        raise InputError("Output must be outside the input Literature and run directories.")
    targets = [out / "context.json", out / "reading_queue.md"]
    if not force and any(p.exists() for p in targets):
        raise InputError("Output index already exists. Choose a new directory or use --force.")

    warnings: list[str] = []
    papers: dict[str, dict] = {}
    fingerprints: dict[str, dict] = {}
    upstream: dict = {}

    def remember(path: Path) -> None:
        if path.is_file():
            fingerprints[str(path.resolve())] = {
                "path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)}

    def merge(record: dict, origin: str) -> dict:
        pid = require_id(record, "paper_id", origin)
        if not isinstance(record.get("title"), str) or not record["title"].strip():
            raise InputError(f"{origin}: paper {pid} has no title")
        if pid not in papers:
            papers[pid] = {**record, "assets": {}, "origins": [origin], "reading_status": "not_assessed"}
        else:
            current = papers[pid]
            left, right = doi_key(current.get("doi")), doi_key(record.get("doi"))
            if left and right and left != right:
                raise InputError(f"Conflicting DOI for the same paper_id {pid}: {left} versus {right}")
            for field, value in record.items():
                if field in {"assets", "origins", "reading_status", "screening"}:
                    continue
                if field == "source_records" and isinstance(value, list) and isinstance(current.get(field), list):
                    signatures = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in current[field]}
                    for item in value:
                        signature = json.dumps(item, sort_keys=True, ensure_ascii=False)
                        if signature not in signatures:
                            current[field].append(item)
                            signatures.add(signature)
                    continue
                if current.get(field) in (None, "", [], {}):
                    current[field] = value
                elif field in {"title", "year", "doi", "decision"} and value not in (None, "", [], {}) and current[field] != value:
                    warnings.append(f"{pid}: conflicting {field}; kept first value; inspect {origin}")
            if record.get("is_retracted") is True:
                current["is_retracted"] = True
            current["origins"].append(origin)
        return papers[pid]

    if run:
        paper_file = run / "papers.jsonl"
        if paper_file.is_file():
            records = read_jsonl(paper_file)
        else:
            paper_file = run / "exports" / "papers.json"
            if not paper_file.is_file():
                raise InputError(f"No papers.jsonl or exports/papers.json in {run}")
            records = read_json(paper_file)
            if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
                raise InputError(f"{paper_file}: expected an array of paper objects")
        remember(paper_file)
        seen: dict[str, dict] = {}
        for number, record in enumerate(records, 1):
            pid = require_id(record, "paper_id", str(paper_file))
            if pid in seen:
                previous = seen[pid]
                same_title = " ".join(previous.get("title", "").split()).casefold() == " ".join(str(record.get("title", "")).split()).casefold()
                same_doi = bool(doi_key(previous.get("doi"))) and doi_key(previous.get("doi")) == doi_key(record.get("doi"))
                if not same_title and not same_doi:
                    raise InputError(f"Ambiguous repeated paper_id {pid} in {paper_file}; conflicting identity")
                warnings.append(f"Repeated paper_id {pid}: merged compatible records and preserved distinct source_records")
            seen[pid] = record
            merge(record, f"{paper_file}:record-{number}")

        screening_files = [p for p in (run / "screening.jsonl", run / "screening.csv") if p.is_file()]

        def read_screens(path: Path) -> list[dict]:
            if path.suffix == ".jsonl":
                return read_jsonl(path)
            with path.open(encoding="utf-8-sig", newline="") as stream:
                return list(csv.DictReader(stream))

        if screening_files:
            screening_files.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
            screen_file = screening_files[0]
            screens = read_screens(screen_file)
            if len(screening_files) == 2 and screen_file.stat().st_mtime_ns == screening_files[1].stat().st_mtime_ns:
                fields = ("paper_id", "decision", "reason_code", "reason_text", "screened_by")
                def decisions(records):
                    return sorted({tuple(str(row.get(k) or "").strip() for k in fields) for row in records})
                if decisions(screens) != decisions(read_screens(screening_files[1])):
                    raise InputError("Conflicting screening files have equal timestamps; resolve which decisions to use")
            for path in screening_files:
                remember(path)
            upstream["screening_source"] = str(screen_file)
        else:
            screen_file = run / "screening.jsonl"
            screens = []
            warnings.append("No screening file; imported papers have not been screened by this tool.")
        screen_seen: dict[str, dict] = {}
        for screen in screens:
            pid = require_id(screen, "paper_id", str(screen_file))
            if pid in screen_seen:
                if screen_seen[pid] == screen:
                    warnings.append(f"Repeated identical screening record for {pid}: retained once")
                    continue
                raise InputError(f"Conflicting screening records for {pid}; inspect the upstream decisions")
            screen_seen[pid] = screen
            if pid not in papers:
                warnings.append(f"Screening record without a paper: {pid}")
                continue
            papers[pid]["screening"] = screen
            if screen.get("decision"):
                papers[pid]["decision"] = screen["decision"]
        for filename in RUN_FILES:
            path = run / filename
            if path.is_file():
                remember(path)
                if filename in {"query_plan.json", "synthesis.json"}:
                    value = object_at(path)
                    upstream[filename.removesuffix(".json")] = value
                else:
                    upstream.setdefault("coverage_files", {})[filename] = str(path)

    if literature:
        manifest = literature / "manifest.json"
        if manifest.is_file():
            remember(manifest)
            entries = object_at(manifest).get("entries")
            if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
                raise InputError(f"{manifest}: entries must be an array of objects")
            indexed_folders = set()
            indexed_ids = set()
            for entry in entries:
                folder_name = entry.get("folder")
                pid = require_id(entry, "paper_id", str(manifest))
                if not isinstance(folder_name, str) or not folder_name:
                    raise InputError("A Literature entry has no folder")
                folder = contained(literature, folder_name)
                if pid in indexed_ids or folder in indexed_folders:
                    raise InputError("Manifest must index each article identity and folder exactly once")
                indexed_ids.add(pid)
                indexed_folders.add(folder)
                if not folder.is_dir():
                    raise InputError(f"Manifest indexes a missing article directory: {folder}")
            actual_folders = {p.parent.resolve() for p in literature.glob("*/meta.json")}
            if not actual_folders.issubset(indexed_folders):
                raise InputError("Manifest is incomplete: it does not index every article; refresh the library index before intake")
        elif (literature / "meta.json").is_file():
            entries = [{**object_at(literature / "meta.json"), "folder": "."}]
        else:
            entries = [{**object_at(p), "folder": p.parent.name} for p in sorted(literature.glob("*/meta.json"))]
        if not entries:
            raise InputError(f"No manifest entries or meta.json records in {literature}")
        for entry in entries:
            folder_name = entry.get("folder")
            if not isinstance(folder_name, str) or not folder_name:
                raise InputError("A Literature entry has no folder")
            folder = contained(literature, folder_name)
            meta_path = folder / "meta.json"
            meta = object_at(meta_path) if meta_path.is_file() else {}
            if meta.get("paper_id") and entry.get("paper_id") and meta["paper_id"] != entry["paper_id"]:
                raise InputError(f"Paper identity differs between manifest and {meta_path}")
            if doi_key(entry.get("doi")) and doi_key(meta.get("doi")) and doi_key(entry["doi"]) != doi_key(meta["doi"]):
                raise InputError(f"DOI differs between manifest and {meta_path}")
            if any(meta.get(k) not in (None, "") and entry.get(k) not in (None, "") and meta[k] != entry[k] for k in ("title", "year")):
                warnings.append(f"{entry.get('paper_id')}: manifest/meta title or year differs; meta value retained")
            record = {**entry, **meta}
            paper = merge(record, str(meta_path if meta else manifest))
            for filename in ASSETS:
                path = folder / filename
                if path.is_file():
                    asset = path.resolve()
                    if not asset.is_relative_to(literature):
                        raise InputError(f"Literature asset escapes input root: {path}")
                    old = paper["assets"].get(filename)
                    if old and old != str(asset):
                        raise InputError(f"{paper['paper_id']}: multiple {filename} assets; select one upstream folder")
                    paper["assets"][filename] = str(asset)

    if paper_ids:
        missing = paper_ids - papers.keys()
        if missing:
            raise InputError("Requested paper IDs not found: " + ", ".join(sorted(missing)))
    selected = []
    for pid, paper in papers.items():
        if paper_ids and pid not in paper_ids:
            continue
        if paper.get("decision") == "exclude" and not include_excluded:
            if paper_ids:
                raise InputError(f"Requested {pid} is excluded; inspect its reason or use --include-excluded.")
            continue
        paper["reading_status"] = "not_assessed"
        screen = paper.get("screening", {})
        if not screen or screen.get("screened_by") == "rule" or screen.get("reason_code") == "PENDING_REVIEW":
            warnings.append(f"{pid}: human/host screening not established; preserve the original decision")
        if paper.get("is_retracted") is True:
            warnings.append(f"{pid}: marked retracted upstream; do not use as reliable supporting evidence")
        for asset in paper["assets"].values():
            remember(Path(asset))
        pdf = paper["assets"].get("paper.pdf")
        expected_pdf = paper.get("pdf_sha256")
        if expected_pdf:
            if not isinstance(expected_pdf, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_pdf):
                raise InputError(f"{pid}: invalid recorded PDF fingerprint")
            if not pdf or sha256(Path(pdf)) != expected_pdf:
                raise InputError(f"{pid}: recorded PDF is missing or bytes differ; review the Literature source version before intake")
        elif pdf:
            warnings.append(f"{pid}: PDF baseline is unrecorded; intake fingerprints current bytes only, not historical reading consistency")
        selected.append(paper)
    if not selected:
        raise InputError("No papers remain after selection; check scope and screening decisions.")

    doi_groups: dict[str, list[str]] = {}
    for paper in selected:
        if key := doi_key(paper.get("doi")):
            doi_groups.setdefault(key, []).append(paper["paper_id"])
    for key, ids in doi_groups.items():
        if len(ids) > 1:
            warnings.append(f"Same DOI has multiple IDs ({key}): {', '.join(ids)}; not independent evidence")
    gaps = upstream.get("synthesis", {}).get("gaps", [])
    if not isinstance(gaps, list):
        raise InputError("Upstream synthesis.gaps must be an array")
    for gap in gaps:
        if isinstance(gap, dict):
            gap_ids = gap.get("evidence_paper_ids", [])
            if not isinstance(gap_ids, list) or any(not isinstance(pid, str) for pid in gap_ids):
                raise InputError("Upstream gap.evidence_paper_ids must be an array of IDs")
            absent = set(gap_ids) - {p["paper_id"] for p in selected}
            if absent:
                warnings.append(f"Upstream gap {gap.get('gap_id')}: references outside selected corpus: {sorted(absent)}")
    context = {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "source_roots": {"literature": str(literature) if literature else None, "run": str(run) if run else None},
        "papers": selected, "input_files": list(fingerprints.values()), "upstream": upstream,
        "warnings": list(dict.fromkeys(warnings)),
        "counts": {"papers": len(selected), "input_files": len(fingerprints)},
    }
    if targets[0].is_file():
        previous = object_at(targets[0])
        history = previous.get("context_history", [])
        if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
            raise InputError("Previous context_history must be an array of objects")
        digest = sha256(targets[0])
        archive = out / "context-history" / (digest + ".json")
        if archive.exists() and sha256(archive) != digest:
            raise InputError(f"Previous context archive differs from recorded identity: {archive}")
        context["context_history"] = [*history, {"path": str(archive), "sha256": digest}]
    queue = ["# 文献阅读队列", "", "导入只建立可用性索引；以下材料均未由导入器阅读或科学审查。", ""]
    for paper in selected:
        title = paper["title"].replace("\n", " ").replace("\r", " ")
        queue.extend([f"## {paper['paper_id']} · {title}", "",
                      f"筛选状态：{paper.get('decision', 'unknown')}；本轮阅读状态：not_assessed", ""])
        if paper.get("doi"):
            queue.append(f"DOI：{paper['doi']}")
        for name, path in paper["assets"].items():
            queue.append(f"- [{name}](<{Path(path).as_posix()}>)")
        if not paper["assets"]:
            queue.append("- 无本地全文/笔记资产；从摘要或已核对的来源开始。")
        queue.append("")
    queue.extend(["## 导入提示", "", *[f"- {w}" for w in context["warnings"]], ""])
    out.mkdir(parents=True, exist_ok=True)
    if targets[0].is_file():
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            # Preserve exact bytes, including a possible legacy BOM.
            with archive.open("xb") as stream:
                stream.write(targets[0].read_bytes())
    atomic_text(targets[0], json.dumps(context, ensure_ascii=False, indent=2) + "\n")
    atomic_text(targets[1], "\n".join(queue))
    return {"ok": True, "out": str(out), "counts": context["counts"], "warnings": context["warnings"]}


def verify(workspace: Path) -> dict:
    workspace = workspace.resolve()
    context = object_at(workspace / "context.json")
    document = object_at(workspace / "ideas.json")
    errors: list[str] = []
    warnings: list[str] = []

    def rows(value: Any, label: str) -> list[dict]:
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            errors.append(f"{label}: expected an array of objects")
            return []
        return value

    def text_field(record: dict, field: str, label: str) -> bool:
        if not isinstance(record.get(field), str) or not record[field].strip():
            errors.append(f"{label}: {field} must be a non-empty string")
            return False
        return True

    def id_list(value: Any, label: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(i, str) or not i for i in value):
            errors.append(f"{label}: expected an array of non-empty IDs")
            return []
        if len(set(value)) != len(value):
            errors.append(f"{label}: duplicate IDs")
        return value

    def index(records: list[dict], key: str, label: str) -> dict[str, dict]:
        result = {}
        for record in records:
            try:
                identifier = require_id(record, key, label)
            except InputError as exc:
                errors.append(str(exc))
                continue
            if identifier in result:
                errors.append(f"{label}: duplicate {key} {identifier}")
            result[identifier] = record
        return result

    def refs(identifiers: list[str], target: dict, label: str) -> None:
        for identifier in identifiers:
            if identifier not in target:
                errors.append(f"{label}: unknown ID {identifier}")

    def obj(value: Any, label: str) -> dict:
        if not isinstance(value, dict):
            errors.append(f"{label}: expected an object")
            return {}
        return value

    def optional_jsonl(name: str) -> list[dict]:
        path = workspace / name
        return read_jsonl(path) if path.is_file() else []

    for name, value in (("context", context), ("ideas", document)):
        if value.get("schema_version") != "1.0":
            errors.append(f"{name}: schema_version must be 1.0")
    text_field(document, "topic", "ideas")
    obj(document.get("constraints"), "constraints")
    papers = index(rows(context.get("papers"), "context.papers"), "paper_id", "context.papers")
    external = index(optional_jsonl("external_papers.jsonl"), "paper_id", "external_papers")
    for pid, paper in external.items():
        if pid in papers:
            errors.append(f"external_papers: paper_id already exists upstream: {pid}")
        text_field(paper, "title", pid)
        text_field(paper, "retrieved_at", pid)
        if not http_url(paper.get("url")):
            errors.append(f"{pid}: external paper requires a source http(s) URL")
        if "example.org" in str(paper.get("url", "")):
            errors.append(f"{pid}: replace the illustrative example.org source")
    papers.update(external)
    evidence = index(optional_jsonl("evidence.jsonl"), "evidence_id", "evidence")
    searches = index(optional_jsonl("novelty_log.jsonl"), "search_id", "novelty_log")
    ideas = index(rows(document.get("ideas"), "ideas.ideas"), "idea_id", "ideas")

    for item in rows(context.get("input_files"), "context.input_files"):
        if not text_field(item, "path", "input_files") or not text_field(item, "sha256", "input_files"):
            continue
        path = Path(item["path"])
        if not path.is_absolute():
            errors.append(f"Input fingerprint path must be absolute: {path}")
        elif not path.is_file():
            errors.append(f"Input file missing since ingest: {path}")
        elif sha256(path) != item["sha256"]:
            errors.append(f"Input changed since ingest; re-read affected evidence: {path}")

    for item in rows(context.get("context_history", []), "context.context_history"):
        if not text_field(item, "path", "context_history") or not text_field(item, "sha256", "context_history"):
            continue
        path = Path(item["path"])
        if not path.is_absolute() or not path.is_file() or sha256(path) != item["sha256"]:
            errors.append(f"Previous context archive missing or changed: {path}")

    known_assets: dict[str, set[str]] = {}
    for pid, paper in papers.items():
        assets = paper.get("assets", {})
        if not isinstance(assets, dict):
            errors.append(f"{pid}: assets must be an object")
            continue
        for value in assets.values():
            if isinstance(value, str) and Path(value).is_absolute():
                known_assets.setdefault(str(Path(value).resolve()), set()).add(pid)

    for eid, entry in evidence.items():
        refs([entry.get("paper_id")] if isinstance(entry.get("paper_id"), str) else ["<missing paper_id>"], papers, eid)
        for field in ("statement", "locator"):
            text_field(entry, field, eid)
        if not choice(entry.get("access_level"), {"metadata", "abstract", "full_text"}):
            errors.append(f"{eid}: invalid access_level")
        if not choice(entry.get("kind"), KINDS):
            errors.append(f"{eid}: invalid kind")
        if not isinstance(entry.get("verified"), bool):
            errors.append(f"{eid}: verified must be boolean")
        elif not entry["verified"]:
            warnings.append(f"{eid}: evidence is not checked")
        source_file, source_url = entry.get("source_file"), entry.get("source_url")
        if source_file:
            if not isinstance(source_file, str):
                errors.append(f"{eid}: source_file must be a string")
            elif not Path(source_file).is_absolute() or not Path(source_file).is_file():
                errors.append(f"{eid}: source_file must be an existing absolute file")
            elif Path(source_file).stat().st_size == 0:
                errors.append(f"{eid}: source_file is empty; it cannot establish checked source evidence")
            else:
                owners = known_assets.get(str(Path(source_file).resolve()), set())
                if owners and (not isinstance(entry.get("paper_id"), str) or entry["paper_id"] not in owners):
                    errors.append(f"{eid}: source_file belongs to a different paper: {sorted(owners)}")
                expected = entry.get("source_sha256")
                if expected is None:
                    warnings.append(f"{eid}: source hash is unrecorded; bind the actually reviewed source before recommendation")
                elif not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                    errors.append(f"{eid}: source_sha256 must be a lowercase SHA-256 digest")
                elif sha256(Path(source_file)) != expected:
                    errors.append(f"{eid}: evidence source changed since review; re-read the affected evidence")
        if source_url and not http_url(source_url):
            errors.append(f"{eid}: source_url must be an http(s) URL")
        if not source_file and not source_url:
            errors.append(f"{eid}: source_file or source_url is required")
        elif not source_file and source_url:
            warnings.append(f"{eid}: remote source content is not fetched or fingerprint-checked by this verifier")

    search_members: dict[str, list[str]] = {}
    for sid, entry in searches.items():
        for field in ("date", "source", "query", "screened_summary", "limitations"):
            text_field(entry, field, sid)
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("date", ""))):
                raise ValueError("not ISO date")
            date.fromisoformat(entry["date"])
        except (ValueError, TypeError):
            errors.append(f"{sid}: date must be a real YYYY-MM-DD date")
        if not choice(entry.get("intent"), INTENTS):
            errors.append(f"{sid}: invalid search intent")
        if not choice(entry.get("status"), {"ok", "failed", "blocked", "not_run"}):
            errors.append(f"{sid}: invalid search status")
        refs(id_list(entry.get("result_paper_ids"), f"{sid}.result_paper_ids"), papers, sid)
        idea_refs = id_list(entry.get("idea_ids"), f"{sid}.idea_ids")
        search_members[sid] = idea_refs
        refs(idea_refs, ideas, sid)
        versions = obj(entry.get("idea_versions"), f"{sid}.idea_versions")
        for iid in idea_refs:
            if type(versions.get(iid)) is not int or versions[iid] < 1:
                errors.append(f"{sid}: missing positive integer version for {iid}")

    for iid, idea in ideas.items():
        for field in ("title", "question", "rationale"):
            text_field(idea, field, iid)
        if not choice(idea.get("status"), STATUSES):
            errors.append(f"{iid}: invalid status")
        if type(idea.get("version")) is not int or idea["version"] < 1:
            errors.append(f"{iid}: version must be a positive integer")
        basis = id_list(idea.get("basis_evidence_ids"), f"{iid}.basis_evidence_ids")
        refs(basis, evidence, iid)
        novelty = obj(idea.get("novelty"), f"{iid}.novelty")
        if not choice(novelty.get("status"), NOVELTY):
            errors.append(f"{iid}: invalid novelty status")
        search_ids = id_list(novelty.get("search_ids"), f"{iid}.novelty.search_ids")
        refs(search_ids, searches, iid)
        current_searches = []
        for sid in search_ids:
            entry = searches.get(sid, {})
            if entry and iid not in search_members.get(sid, []):
                errors.append(f"{iid}: search {sid} does not refer to this idea")
            bindings = entry.get("idea_fingerprints", {})
            if not isinstance(bindings, dict):
                errors.append(f"{sid}: idea_fingerprints must be an object")
                bindings = {}
            if (entry.get("status") == "ok" and isinstance(entry.get("idea_versions"), dict)
                    and entry["idea_versions"].get(iid) == idea.get("version")
                    and bindings.get(iid) == idea_fingerprint(idea)):
                current_searches.append(entry)
        prior = rows(idea.get("prior_art", []), f"{iid}.prior_art")
        full_text_prior = False
        for comparison in prior:
            pid = comparison.get("paper_id")
            refs([pid] if isinstance(pid, str) else ["<missing prior paper_id>"], papers, iid)
            for field in ("overlap", "delta"):
                text_field(comparison, field, iid + ".prior_art")
            eids = id_list(comparison.get("evidence_ids"), f"{iid}.prior_art.evidence_ids")
            refs(eids, evidence, iid)
            if idea.get("status") == "recommended" and not eids:
                errors.append(f"{iid}: each recommended prior-art comparison needs its own checked evidence")
            for eid in eids:
                item = evidence.get(eid, {})
                if idea.get("status") == "recommended" and item.get("verified") is not True:
                    errors.append(f"{iid}: prior-art evidence {eid} is not checked")
                if idea.get("status") == "recommended" and item.get("source_file") and not item.get("source_sha256"):
                    errors.append(f"{iid}: prior-art evidence {eid} needs the reviewed source_sha256")
                if item and item.get("paper_id") != pid:
                    errors.append(f"{iid}: prior-art evidence {eid} belongs to a different paper")
                if item.get("paper_id") == pid and item.get("access_level") == "full_text" and item.get("verified") is True:
                    full_text_prior = True
        if choice(idea.get("status"), {"hold", "rejected", "archived"}):
            text_field(idea, "decision_reason", iid)
        if idea.get("status") != "recommended":
            continue
        for field in ("hypothesis", "decision_reason"):
            text_field(idea, field, iid)
        if not choice(idea.get("claim_type"), CLAIM_TYPES):
            errors.append(f"{iid}: invalid or missing claim_type")
        if not basis:
            errors.append(f"{iid}: recommendation needs checked basis evidence")
        for eid in basis:
            item = evidence.get(eid, {})
            if item.get("verified") is not True:
                errors.append(f"{iid}: basis evidence {eid} is not checked")
            if item.get("source_file") and not item.get("source_sha256"):
                errors.append(f"{iid}: basis evidence {eid} needs the reviewed source_sha256")
            source_id = item.get("paper_id")
            if isinstance(source_id, str) and papers.get(source_id, {}).get("is_retracted") is True:
                errors.append(f"{iid}: retracted paper used as supporting evidence")
        if not prior or not full_text_prior:
            errors.append(f"{iid}: recommendation needs checked full-text closest-prior-art evidence")
        if novelty.get("status") != "differentiated_within_scope":
            errors.append(f"{iid}: recommendation has no bounded novelty differentiation")
        for field in ("conclusion", "limitations"):
            text_field(novelty, field, iid + ".novelty")
        intents = {entry.get("intent") for entry in current_searches if isinstance(entry.get("intent"), str)}
        queries = {str(entry.get("query", "")).strip().casefold() for entry in current_searches}
        if "duplicate" not in intents or len(intents) < 2 or len(queries) < 2:
            errors.append(f"{iid}: recommendation needs current-version successful duplicate and distinct-concept searches bound to this idea content; inspect idea_fingerprints")
        design = obj(idea.get("design"), f"{iid}.design")
        for field in DESIGN_FIELDS:
            text_field(design, field, iid + ".design")
        gates = obj(idea.get("gates"), f"{iid}.gates")
        for field in ("data_access", "resource_fit"):
            if gates.get(field) != "confirmed":
                errors.append(f"{iid}: recommended pilot requires confirmed {field}")
            text_field(gates, field + "_basis", iid + ".gates")
        review = obj(idea.get("review"), f"{iid}.review")
        for field in ("strongest_objection", "response", "residual_risk"):
            text_field(review, field, iid + ".review")

    for record in [document, *evidence.values(), *searches.values()]:
        for pid in re.findall(r"\[\[([A-Za-z][A-Za-z0-9_-]*)\]\]", json.dumps(record, ensure_ascii=False)):
            if pid not in papers:
                errors.append(f"Citation token refers to unknown paper: {pid}")
    for path in [workspace / "decision.md", *sorted((workspace / "cards").glob("*.md"))]:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8-sig")
        for pid in re.findall(r"\[\[([A-Za-z][A-Za-z0-9_-]*)\]\]", content):
            if pid not in papers:
                errors.append(f"{path.name}: citation token refers to unknown paper: {pid}")
    if not ideas:
        warnings.append("No idea records; no recommendation is being checked.")
    warnings.append("Structural checks cannot certify scientific truth, novelty, or feasibility.")
    return {"ok": not errors, "errors": list(dict.fromkeys(errors)), "warnings": warnings,
            "counts": {"papers": len(papers), "ideas": len(ideas), "evidence": len(evidence), "searches": len(searches)}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    load = sub.add_parser("ingest", help="Index a light-literature run and/or Literature directory, read-only")
    load.add_argument("--literature", type=Path)
    load.add_argument("--run", type=Path)
    load.add_argument("--out", type=Path, required=True)
    load.add_argument("--paper-ids", help="Comma-separated existing paper IDs")
    load.add_argument("--include-excluded", action="store_true")
    load.add_argument("--force", action="store_true", help="Replace context.json and reading_queue.md only")
    check = sub.add_parser("verify", help="Check workspace structure, references, recommendation gates and input drift")
    check.add_argument("--workspace", type=Path, required=True)
    identify = sub.add_parser("fingerprint", help="Read current scientific content identifiers; does not perform novelty searches")
    identify.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            ids = {s.strip() for s in args.paper_ids.split(",") if s.strip()} if args.paper_ids else None
            if args.paper_ids is not None and not ids:
                raise InputError("--paper-ids must name at least one existing paper ID.")
            result = ingest(args.literature, args.run, args.out, ids, args.include_excluded, args.force)
        elif args.command == "fingerprint":
            result = fingerprints(args.workspace)
        else:
            result = verify(args.workspace)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except (InputError, OSError, UnicodeError, csv.Error) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
