from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..models import Paper
from ..normalize import make_paper_id, normalize_arxiv, normalize_doi, now_iso
from .base import Adapter, SearchResult

BASE = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return " ".join("".join(el.itertext()).split())


class ArxivAdapter(Adapter):
    name = "arxiv"

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = {
            "search_query": query["query"],
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate" if query.get("sort") == "recent" else "relevance",
            "sortOrder": "descending",
        }
        try:
            resp = self.client.get(BASE, params=params, parse="text", ttl=86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        try:
            root = ET.fromstring(resp.data)
        except ET.ParseError as exc:
            return SearchResult(source=self.name, status="error", error=f"XML parse error: {exc}")
        entries = root.findall("a:entry", NS)
        papers = []
        for rank, entry in enumerate(entries):
            paper = self._parse(entry, query, rank)
            if paper is not None:
                papers.append(paper)
        return SearchResult(source=self.name, papers=papers, raw_count=len(entries))

    def _parse(self, entry: ET.Element, query: dict[str, Any], rank: int) -> Paper | None:
        url = _text(entry.find("a:id", NS))
        arxiv_id = normalize_arxiv(url)
        title = _text(entry.find("a:title", NS))
        if not title:
            return None
        abstract = _text(entry.find("a:summary", NS))
        published = _text(entry.find("a:published", NS))
        year = None
        if len(published) >= 4 and published[:4].isdigit():
            year = int(published[:4])
        authors = [_text(a.find("a:name", NS)) for a in entry.findall("a:author", NS)]
        doi = normalize_doi(_text(entry.find("arxiv:doi", NS)))
        journal_ref = _text(entry.find("arxiv:journal_ref", NS))
        categories = [c.get("term", "") for c in entry.findall("a:category", NS) if c.get("term")]
        pdf_url = ""
        for link in entry.findall("a:link", NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break
        source_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else url
        record = self.source_record(query, rank, source_url)
        record["source_id"] = arxiv_id
        return Paper(
            paper_id=make_paper_id(doi=doi, arxiv_id=arxiv_id, title=title, year=year),
            title=title,
            abstract=abstract,
            authors=[a for a in authors if a],
            year=year,
            venue=journal_ref or "arXiv",
            type="preprint",
            doi=doi,
            arxiv_id=arxiv_id,
            url=source_url,
            pdf_url=pdf_url,
            is_preprint=True,
            language="en",
            concepts=categories,
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )
