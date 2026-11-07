from __future__ import annotations

import logging
import hashlib
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from .config import Config, load_config
from .io import read_json, read_jsonl, write_json, write_jsonl
from .models import Paper, ScreeningRow
from .normalize import make_paper_id, now_iso, surname
from .pdf_assets import estimate_pages, render_pdf_assets
from .pdf import fetch_pdfs
from .screening import read_screening


def _slug(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"[^\w一-鿿]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-_ ")
    return text[:max_len].rstrip("-_ ") or "Untitled"


def article_folder_name(paper: Paper, used: set[str] | None = None) -> str:
    used = used or set()
    year = paper.year or "nd"
    author = surname(paper.authors[0]) if paper.authors else "Unknown"
    author = _slug(author, 24) or "Unknown"
    title = _slug(paper.title, 54)
    base = f"{year}_{author}_{title}"
    name = base
    i = 2
    while name in used:
        name = f"{base}_{i}"
        i += 1
    return name


def _decision(rows: list[Any], paper_id: str) -> str:
    for row in rows:
        if row.paper_id == paper_id:
            return row.decision
    return ""


def _pdf_source(paper: Paper, run_dir: Path, manifest: dict[str, dict[str, Any]]) -> Path | None:
    candidates = []
    if paper.pdf_path:
        candidates.append(Path(paper.pdf_path))
    item = manifest.get(paper.paper_id) or {}
    if item.get("path"):
        candidates.append(Path(item["path"]))
    candidates.append(run_dir / "pdfs" / f"{paper.paper_id}.pdf")
    for path in candidates:
        if path.is_file():
            return path.resolve()
    return None


def extract_pdf_metadata(pdf_path: str | Path) -> dict[str, Any]:
    """Best-effort title/author from PDF metadata; publication year stays unknown."""
    path = Path(pdf_path)
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            logger = logging.getLogger(module_name)
            old_level = logger.level
            logger.setLevel(logging.ERROR)
            try:
                meta = module.PdfReader(str(path)).metadata or {}
                title = str(getattr(meta, "title", "") or "").strip()
                author = str(getattr(meta, "author", "") or "").strip()
                # PDF creation time is not a publication date. The host supplies
                # a verified year explicitly or leaves bibliographic year unknown.
                return {"title": title, "author": author, "year": None}
            finally:
                logger.setLevel(old_level)
        except Exception:  # noqa: BLE001
            continue
    return {"title": "", "author": "", "year": None}


def _copy_pdf(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dest.resolve():
        return
    shutil.copy2(src, dest)


def _pdf_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_library_index(out_dir: Path, summary: dict[str, Any]) -> None:
    """The manifest indexes the whole library; selection counters describe this batch."""
    entries = [read_json(p, {}) for p in sorted(out_dir.glob("*/meta.json"))]
    entries = [entry for entry in entries if entry]
    summary["library_total"] = len(entries)
    _write_index(out_dir, entries)
    write_json(out_dir / "manifest.json", {
        **summary, "entries": entries,
        "selected_paper_ids": [entry["paper_id"] for entry in summary["entries"]],
    })


def _write_article_tasks(article_dir: Path, meta: dict[str, Any]) -> None:
    templates = Path(__file__).resolve().parents[2] / "templates"
    text = f"""# Agent tasks for this paper

- **Title:** {meta['title']}
- **DOI:** {meta.get('doi', '')}
- **Parse status:** {meta['parse_status']}
- **Prompt directory:** `{templates}`

## 1. Source-grounded reading

If the PDF is missing, obtain a lawful copy first; keep the missing status until
it is available. Otherwise follow `MODEL_PARSE.md` when present and the prompt
`parse_pdf_model.md`. Read every PDF page; produce `paper.md`, `source_map.json`,
and `model_parse_notes.md`. Reuse existing full text, but check its source anchors
against the PDF before translating or taking notes. Do not replace it with a summary.

## 2. Translation and optional bilingual reader

Follow `translate_paper.md` to write the full Chinese `paper.zh.md` and terminology
ledger `translation_notes.md`. Preserve source IDs, equations, tables, captions,
image links and reference numbers. If requested, write aligned English/Chinese
blocks to `reader.bilingual.md` using those same IDs.

## 3. Evidence-anchored note

Follow `paper_note.md` and `templates/paper-note-template.zh.md` to write Chinese
`note.md` (optional English: `note.en.md`). Establish an evidence inventory and
claim-evidence matrix first. Reconstruct the research problem, design choices,
load-bearing components, key equations and evidence limits. Separate author
claims, analyst inferences, external facts and hypotheses. External facts require
verified sources; missing evidence stays explicitly unassessable.

## 4. Refresh the index

Re-run the same literature command after host-model work to refresh metadata and
the index; completed text, translation and notes are reused. Scripts prepare assets;
they do not call a language model or claim that model-authored files are complete.
"""
    (article_dir / "AGENT_TASKS.md").write_text(text, encoding="utf-8")


def _write_model_parse(article_dir: Path, paper: Paper) -> dict[str, Any]:
    assets = render_pdf_assets(article_dir / "paper.pdf", article_dir)
    asset_note = ""
    if assets.get("status") in {"ok", "partial"}:
        asset_note = (
            f"Page PNGs: `pages/` ({len(assets.get('pages', []))} pages). "
            f"Extracted images: `images/` ({len(assets.get('images', []))} images). "
            "Read the page PNGs with a multimodal model; use `pdf_assets.json` as the index."
        )
    else:
        asset_note = (
            "Page rendering was unavailable; read `paper.pdf` directly with the "
            "host model's PDF reader. Record the reason in `model_parse_notes.md`."
        )
    text = f"""# Model-parse task

Prepare or verify `paper.md` against the PDF `paper.pdf`. Preserve completed
model-authored files; asset refresh alone does not require rewriting them.

Use the host model (must be **multimodal**) to read the PDF page by page and write
`paper.md` following `templates/prompts/parse_pdf_model.md`.

{asset_note}

## Requirements

- Read **every page**; do not summarize or skip sections.
- Preserve headings, paragraphs, equations (LaTeX), tables, figure captions, and
  references.
- Use page anchors such as `<!-- page: 3 -->` so the note can cite pages later.
- Use `pages/page_XXX.png` for visual reading and `images/page_XXX_img_Y.*` for
  figure/table crops where possible; if an image cannot be extracted, say `image
  missing` and keep the caption.
- Run a second completeness pass: section count, equations, tables, figures,
  references; fix omissions.
- Write `model_parse_notes.md` with OCR uncertainty and missing assets.
- Do not invent text that is not in the PDF.

## Title

{paper.title}

## After parsing

Write `paper.zh.md` (translation) and `note.md` (Chinese note) using the usual
contracts.
"""
    (article_dir / "MODEL_PARSE.md").write_text(text, encoding="utf-8")
    return assets


def _write_index(out_dir: Path, entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Literature",
        "",
        "Generated by litsearch. Folders hold source PDFs and host-model reading tasks;",
        "text, translations and notes appear after the host model completes them.",
        "",
        "| Folder | Title | Year | DOI | PDF | Parse | Translation | Note |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for entry in sorted(entries, key=lambda x: (x.get("year") or 0, x.get("title", "")), reverse=True):
        folder = entry["folder"]
        lines.append(
            f"| [{folder}]({folder}/) | {str(entry.get('title', '')).replace('|', '/')[:80]} | "
            f"{entry.get('year', '')} | {entry.get('doi', '')} | "
            f"{entry.get('pdf_status', '')} | {entry.get('parse_status', '')} | "
            f"{entry.get('translation_status', '')} | {entry.get('note_status', '')} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_pdf(
    pdf_path: str | Path,
    out_dir: str | Path,
    *,
    title: str | None = None,
    authors: list[str] | str | None = None,
    year: int | None = None,
    doi: str = "",
    dry_run: bool = False,
    force_prepare: bool = False,
    config: Config | None = None,
) -> dict[str, Any]:
    """Import a user-supplied PDF and prepare host-model reading tasks."""
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")
    config = config or load_config()
    meta = extract_pdf_metadata(pdf)
    title = (title or meta.get("title") or pdf.stem).strip()
    if isinstance(authors, str):
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
    elif authors:
        author_list = [str(a).strip() for a in authors if str(a).strip()]
    else:
        raw = str(meta.get("author") or "")
        author_list = [a.strip() for a in re.split(r"[;,]", raw) if a.strip()] or ["Unknown"]
    year = year or meta.get("year")
    paper = Paper(
        paper_id=make_paper_id(doi=doi, title=title, year=year),
        title=title,
        authors=author_list,
        year=year,
        doi=doi or "",
        type="article",
        url="",
        evidence_depth="metadata_only",
        created_at=now_iso(),
    )
    with tempfile.TemporaryDirectory(prefix="litsearch-import-") as tmp:
        run = Path(tmp)
        pdf_copy = run / "pdfs" / f"{paper.paper_id}.pdf"
        pdf_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, pdf_copy)
        write_jsonl(run / "papers.jsonl", [paper.to_dict()])
        write_jsonl(
            run / "screening.jsonl",
            [
                ScreeningRow(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    year=paper.year,
                    decision="include",
                    reason_code="IN_SCOPE",
                    reason_text="User-supplied PDF import.",
                ).to_dict()
            ],
        )
        write_json(
            run / "pdf_manifest.json",
            {"items": [{"paper_id": paper.paper_id, "status": "user_pdf", "path": str(pdf_copy)}]},
        )
        result = build_literature(
            run,
            out_dir,
            statuses={"include"},
            paper_ids={paper.paper_id},
            dry_run=dry_run,
            force_prepare=force_prepare,
            config=config,
        )
    if dry_run:
        return result
    for entry in result.get("entries", []):
        if entry.get("paper_id") == paper.paper_id:
            folder = Path(out_dir) / entry["folder"]
            meta_path = folder / "meta.json"
            data = read_json(meta_path, {}) or {}
            data["source"] = "user_pdf"
            data["original_pdf"] = str(pdf.resolve())
            write_json(meta_path, data)
            entry["source"] = "user_pdf"
            entry["original_pdf"] = str(pdf.resolve())
            result["folder"] = str(folder)
    _save_library_index(Path(out_dir), result)
    return result


def build_literature(
    run_dir: str | Path,
    out_dir: str | Path,
    *,
    statuses: set[str] | None = None,
    paper_ids: set[str] | None = None,
    limit: int | None = None,
    fetch_pdf: bool = False,
    dry_run: bool = False,
    force_prepare: bool = False,
    config: Config | None = None,
) -> dict[str, Any]:
    """Prepare per-paper assets and host-model tasks; never call a model API."""
    config = config or load_config()
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    statuses = statuses or {"include"}
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    rows = read_screening(run_dir)
    if fetch_pdf and not dry_run:
        fetch_pdfs(run_dir, limit=limit or 50, config=config)
    manifest = {
        item.get("paper_id"): item
        for item in (read_json(run_dir / "pdf_manifest.json", {}) or {}).get("items", [])
    }
    selected = [
        p for p in papers
        if _decision(rows, p.paper_id) in statuses
        and (not paper_ids or p.paper_id in paper_ids)
    ]
    selected.sort(key=lambda p: (
        bool(_pdf_source(p, run_dir, manifest)), p.discovery_score.get("total", 0)
    ), reverse=True)
    if limit is not None:
        selected = selected[:limit]

    # Keep folder identities stable across partial builds and imports.
    existing = {}
    used = {p.name for p in out_dir.iterdir() if p.is_dir()} if out_dir.exists() else set()
    for path in out_dir.glob("*/meta.json"):
        data = read_json(path, {}) or {}
        if data.get("paper_id"):
            if data["paper_id"] in existing:
                raise ValueError("Duplicate paper_id in existing library: " + data["paper_id"])
            existing[data["paper_id"]] = (path.parent, data)
    # Check the entire selection before replacing any library source or metadata.
    for paper in selected:
        previous = existing.get(paper.paper_id)
        if not previous:
            continue
        folder, old = previous
        incoming = _pdf_source(paper, run_dir, manifest)
        current = folder / "paper.pdf"
        expected = old.get("pdf_sha256")
        if current.is_file() and incoming and _pdf_digest(current) != _pdf_digest(incoming):
            raise ValueError(f"A different PDF already exists for {paper.paper_id}; preserve the old source and reading files and handle replacement as an explicit versioned migration")
        if expected and current.is_file() and _pdf_digest(current) != expected:
            raise ValueError(f"Recorded PDF and current bytes differ for {paper.paper_id}; review the source change before refreshing reading metadata")
        if expected and incoming and _pdf_digest(incoming) != expected:
            raise ValueError(f"Recorded PDF and incoming bytes differ for {paper.paper_id}; preserve the source version even when the old local PDF is missing")
    entries: list[dict[str, Any]] = []
    for paper in selected:
        previous = existing.get(paper.paper_id)
        folder = previous[0].name if previous else article_folder_name(paper, used)
        used.add(folder)
        article_dir = out_dir / folder
        old = previous[1] if previous else {}
        src_pdf = _pdf_source(paper, run_dir, manifest)
        if src_pdf is None and (article_dir / "paper.pdf").is_file():
            src_pdf = article_dir / "paper.pdf"
        pdf_status = "present" if src_pdf else "missing"
        pages = estimate_pages(src_pdf) if src_pdf else 0
        parse_status = "pdf_missing"
        assets = read_json(article_dir / "pdf_assets.json", {}) or {}
        if src_pdf:
            has_text = (article_dir / "paper.md").is_file() and (article_dir / "paper.md").stat().st_size > 0
            parse_status = "already_present" if has_text else "model_parse_required"
            if not dry_run:
                article_dir.mkdir(parents=True, exist_ok=True)
                _copy_pdf(src_pdf, article_dir / "paper.pdf")
                if force_prepare or not has_text:
                    assets = _write_model_parse(article_dir, paper)
        meta = {
            # Preserve provenance and user annotations; replace obsolete parser fields.
            **{k: v for k, v in old.items() if not k.startswith("doc2x_")},
            "paper_id": paper.paper_id,
            "folder": folder,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
            "doi": paper.doi,
            "arxiv_id": paper.arxiv_id,
            "url": paper.url,
            "decision": _decision(rows, paper.paper_id),
            "pdf_status": pdf_status,
            "pdf_sha256": _pdf_digest(src_pdf) if src_pdf else old.get("pdf_sha256", ""),
            "parse_method": "host_model",
            "pages_estimated": pages,
            "parse_status": parse_status,
            "assets_status": assets.get("status", "not_prepared"),
            "source_map_status": "present" if (article_dir / "source_map.json").is_file() else "missing",
            "translation_status": "present" if (article_dir / "paper.zh.md").is_file() else "missing",
            "note_status": "present" if (article_dir / "note.md").is_file() else "missing",
            "created_at": old.get("created_at") or now_iso(),
            "updated_at": now_iso(),
        }
        if not dry_run:
            article_dir.mkdir(parents=True, exist_ok=True)
            write_json(article_dir / "meta.json", meta)
            _write_article_tasks(article_dir, meta)
        entries.append(meta)

    summary = {
        "out_dir": str(out_dir),
        "parse_method": "host_model",
        "dry_run": dry_run,
        "pages_estimated": sum(e["pages_estimated"] for e in entries),
        "selected": len(selected),
        "pdf_present": sum(e["pdf_status"] == "present" for e in entries),
        "parse_already_present": sum(e["parse_status"] == "already_present" for e in entries),
        "model_parse_required": sum(e["parse_status"] == "model_parse_required" for e in entries),
        "translation_present": sum(e["translation_status"] == "present" for e in entries),
        "note_present": sum(e["note_status"] == "present" for e in entries),
        "entries": entries,
    }
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        _save_library_index(out_dir, summary)
    return summary
