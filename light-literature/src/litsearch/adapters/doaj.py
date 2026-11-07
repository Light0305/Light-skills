from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from ..models import Paper
from ..normalize import make_paper_id, normalize_doi, now_iso
from .base import Adapter, SearchResult

BASE = "https://doaj.org/api/v3/search/articles"


def _text(value: Any) -> str:
    return re.sub(r"<[^>]+>", " ", str(value or "")).strip()


class DOAJAdapter(Adapter):
    name = "doaj"

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        url = f"{BASE}/{quote(query['query'], safe='')}"
        try:
            resp = self.client.get(
                url,
                params={"pageSize": min(limit, 100), "page": 1},
                ttl=86400,
                timeout=10,
                retries=1,
            )
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        data = resp.data or {}
        results = data.get("results") or []
        if not isinstance(results, list):
            return SearchResult(source=self.name, status="error", error=str(data)[:200])
        papers = [self._parse(item, query, rank) for rank, item in enumerate(results)]
        papers = [p for p in papers if p is not None]
        return SearchResult(source=self.name, papers=papers, raw_count=len(results))

    def _parse(self, item: dict[str, Any], query: dict[str, Any], rank: int) -> Paper | None:
        bib = item.get("bibjson") or {}
        title = _text(bib.get("title"))
        if not title:
            return None
        abstract = _text(bib.get("abstract"))
        authors = [a.get("name", "") for a in (bib.get("author") or []) if a.get("name")]
        year = bib.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        doi = ""
        for ident in bib.get("identifier") or []:
            if str(ident.get("type", "")).lower() == "doi":
                doi = normalize_doi(ident.get("id", ""))
                break
        pdf_url = ""
        for link in bib.get("link") or []:
            if str(link.get("type", "")).lower() in {"fulltext", "pdf"}:
                pdf_url = link.get("url", "")
                break
        url = pdf_url or (f"https://doi.org/{doi}" if doi else "")
        journal = (bib.get("journal") or {}).get("title") or ""
        language = ""
        langs = bib.get("language") or []
        if isinstance(langs, list) and langs:
            language = str(langs[0])
        elif isinstance(langs, str):
            language = langs
        concepts = [str(x) for x in (bib.get("keywords") or [])]
        record = self.source_record(query, rank, url)
        record["source_id"] = str(item.get("id", ""))
        return Paper(
            paper_id=make_paper_id(doi=doi, title=title, year=year),
            title=title,
            abstract=abstract,
            authors=authors,
            year=year,
            venue=str(journal),
            type="article",
            doi=doi,
            url=url,
            pdf_url=pdf_url,
            language=language,
            concepts=concepts,
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )
