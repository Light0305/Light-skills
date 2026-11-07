from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io import write_csv, write_json
from .models import Paper, ScreeningRow


def _bibtex_escape(text: str) -> str:
    return re.sub(r"([{}%&#_$])", r"\\\1", text or "")


def _bibtex_key(paper: Paper, used: set[str]) -> str:
    author = (paper.authors[0].split()[-1] if paper.authors else "anon").lower()
    author = re.sub(r"[^a-z0-9]", "", author) or "anon"
    year = paper.year or "nd"
    word = re.sub(r"[^a-z0-9]", "", (paper.title.split()[0] if paper.title else "paper").lower()) or "paper"
    base = f"{author}{year}{word}"
    key = base
    i = 2
    while key in used:
        key = f"{base}{i}"
        i += 1
    used.add(key)
    return key


def export_all(run_dir: str | Path, papers: list[Paper], rows: list[ScreeningRow]) -> dict[str, str]:
    run_dir = Path(run_dir)
    exports = run_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    paper_rows = []
    used: set[str] = set()
    bib_entries = []
    for paper in papers:
        key = _bibtex_key(paper, used)
        paper_rows.append(
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "authors": "; ".join(paper.authors),
                "year": paper.year or "",
                "venue": paper.venue,
                "doi": paper.doi,
                "arxiv_id": paper.arxiv_id,
                "pmid": paper.pmid,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "pdf_path": paper.pdf_path,
                "pdf_status": paper.pdf_status,
                "pdf_source": paper.pdf_source,
                "oa_status": paper.oa_status,
                "license": paper.license,
                "cited_by_count": paper.cited_by_count,
                "evidence_depth": paper.evidence_depth,
                "discovery_score": paper.discovery_score.get("total", 0),
            }
        )
        fields = [
            "@article{" + key + ",",
            f"  title = {{{_bibtex_escape(paper.title)}}},",
        ]
        if paper.authors:
            fields.append(f"  author = {{{_bibtex_escape(' and '.join(paper.authors))}}},")
        if paper.year:
            fields.append(f"  year = {{{paper.year}}},")
        if paper.venue:
            fields.append(f"  journal = {{{_bibtex_escape(paper.venue)}}},")
        if paper.doi:
            fields.append(f"  doi = {{{paper.doi}}},")
        if paper.url:
            fields.append(f"  url = {{{paper.url}}},")
        if paper.pdf_path:
            fields.append(f"  file = {{{paper.pdf_path}}},")
        fields.append("}")
        bib_entries.append("\n".join(fields))
    write_csv(exports / "papers.csv", paper_rows, bom=True)
    write_json(exports / "papers.json", [p.to_dict() for p in papers])
    (exports / "references.bib").write_text("\n\n".join(bib_entries) + "\n", encoding="utf-8")
    write_csv(exports / "screening.csv", [r.to_dict() for r in rows], bom=True)
    return {
        "papers_csv": str(exports / "papers.csv"),
        "papers_json": str(exports / "papers.json"),
        "bibtex": str(exports / "references.bib"),
        "screening_csv": str(exports / "screening.csv"),
    }
