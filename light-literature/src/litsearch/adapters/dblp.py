from __future__ import annotations

import html
import json
import re
from typing import Any

from ..models import Paper
from ..normalize import make_paper_id, normalize_doi, now_iso
from .base import Adapter, SearchResult

BASE = "https://dblp.org/search/publ/api"


def _text(value: Any) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).strip()


class DBLPAdapter(Adapter):
    name = "dblp"

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        try:
            resp = self.client.get(
                BASE,
                params={"q": query["query"], "format": "json", "h": min(limit, 1000), "f": 0},
                parse="text",
                ttl=86400,
                timeout=10,
                retries=1,
            )
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        text = resp.data or ""
        if "Making sure you're not a bot" in text or text.lstrip().lower().startswith("<!doctype html"):
            return SearchResult(
                source=self.name,
                status="blocked",
                error="DBLP is serving an Anubis bot challenge; use the DBLP dump or a browser.",
            )
        try:
            data = json.loads(text)
        except ValueError:
            return SearchResult(source=self.name, status="error", error="DBLP returned non-JSON")
        hits = (((data.get("result") or {}).get("hits") or {}).get("hit")) or []
        if isinstance(hits, dict):
            hits = [hits]
        papers = [self._parse(hit.get("info") or {}, query, rank) for rank, hit in enumerate(hits)]
        papers = [p for p in papers if p is not None]
        return SearchResult(source=self.name, papers=papers, raw_count=len(hits))

    def _parse(self, info: dict[str, Any], query: dict[str, Any], rank: int) -> Paper | None:
        title = _text(info.get("title"))
        if not title:
            return None
        authors_raw = (info.get("authors") or {}).get("author") or []
        if isinstance(authors_raw, dict):
            authors_raw = [authors_raw]
        authors = []
        for author in authors_raw:
            if isinstance(author, dict):
                authors.append(_text(author.get("text")))
            else:
                authors.append(_text(author))
        year = info.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        doi = normalize_doi(info.get("doi", ""))
        url = info.get("ee") or (f"https://doi.org/{doi}" if doi else info.get("url", ""))
        record = self.source_record(query, rank, url)
        record["source_id"] = str(info.get("key", ""))
        return Paper(
            paper_id=make_paper_id(doi=doi, title=title, year=year),
            title=title,
            authors=authors,
            year=year,
            venue=_text(info.get("venue")),
            type=_text(info.get("type")) or "article",
            doi=doi,
            url=url,
            source_records=[record],
            evidence_depth="metadata_only",
            created_at=now_iso(),
        )
