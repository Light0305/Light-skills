from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from ..models import CitationEdge, Paper
from ..normalize import authors_from_string, make_edge_id, make_paper_id, normalize_doi, now_iso
from .base import Adapter, CitationResult, SearchResult, first

BASE = "https://api.crossref.org/works"
SELECT = "DOI,title,author,issued,container-title,abstract,is-referenced-by-count,type,URL,link,subject"


def _strip_jats(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


class CrossrefAdapter(Adapter):
    name = "crossref"

    def _params(self, *, collection: bool = False) -> dict[str, Any]:
        # Crossref permits select on collection routes, not /works/{doi}.
        params: dict[str, Any] = {"select": SELECT} if collection else {}
        if self.config.mailto:
            params["mailto"] = self.config.mailto
        return params

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = self._params(collection=True)
        params.update(
            {
                "query.bibliographic": query["query"],
                "rows": limit,
            }
        )
        for key in ("filter", "sort", "order"):
            if query.get("params", {}).get(key):
                params[key] = query["params"][key]
        try:
            resp = self.client.get(BASE, params=params, ttl=86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        items = (((resp.data or {}).get("message") or {}).get("items")) or []
        papers = [self._parse(item, query, rank) for rank, item in enumerate(items)]
        papers = [p for p in papers if p is not None]
        return SearchResult(source=self.name, papers=papers, raw_count=len(items))

    def _parse(self, item: dict[str, Any], query: dict[str, Any] | None = None, rank: int = 0) -> Paper | None:
        doi = normalize_doi(item.get("DOI", ""))
        title = _strip_jats(first(item.get("title")) or "")
        if not title and not doi:
            return None
        abstract = _strip_jats(item.get("abstract", ""))
        authors = []
        for author in item.get("author", []) or []:
            name = " ".join(x for x in [author.get("given", ""), author.get("family", "")] if x).strip()
            if name:
                authors.append(name)
        year = None
        for key in ("issued", "published"):
            parts = (item.get(key) or {}).get("date-parts") or []
            if parts and parts[0] and parts[0][0]:
                try:
                    year = int(parts[0][0])
                except (TypeError, ValueError):
                    year = None
                if year:
                    break
        venue = first(item.get("container-title")) or ""
        pdf_url = ""
        for link in item.get("link", []) or []:
            if "pdf" in str(link.get("content-type", "")).lower():
                pdf_url = link.get("URL", "")
                break
        record = self.source_record(query or {}, rank, item.get("URL", ""))
        record["source_id"] = doi
        return Paper(
            paper_id=make_paper_id(doi=doi, title=title, year=year),
            title=title or f"[Unresolved] {doi}",
            abstract=abstract,
            authors=authors,
            year=year,
            venue=venue,
            type=str(item.get("type", "") or ""),
            doi=doi,
            url=item.get("URL", ""),
            pdf_url=pdf_url,
            cited_by_count=int(item.get("is-referenced-by-count") or 0),
            is_preprint=str(item.get("type", "")).lower() == "posted-content",
            language=str(item.get("language", "") or ""),
            concepts=[str(x) for x in (item.get("subject") or [])],
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )

    def get_by_doi(self, doi: str) -> Paper | None:
        doi = normalize_doi(doi)
        if not doi:
            return None
        url = f"{BASE}/{quote(doi, safe='')}"
        try:
            resp = self.client.get(url, params=self._params(), ttl=7 * 86400)
        except Exception:  # noqa: BLE001
            return None
        message = (resp.data or {}).get("message") or {}
        return self._parse(message)

    def citations(self, paper: Paper, direction: str, limit: int) -> CitationResult:
        if direction == "forward" or not paper.doi:
            return CitationResult(source=self.name, status="skipped", error="Crossref has no forward citation endpoint")
        url = f"{BASE}/{quote(paper.doi, safe='')}"
        try:
            resp = self.client.get(url, params=self._params(), ttl=7 * 86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return CitationResult(source=self.name, status=status, error=str(exc))
        message = (resp.data or {}).get("message") or {}
        edges: list[CitationEdge] = []
        papers: list[Paper] = []
        for rank, ref in enumerate((message.get("reference") or [])[:limit]):
            target = self._parse_reference(ref, rank)
            if target is None:
                continue
            papers.append(target)
            edges.append(
                CitationEdge(
                    edge_id=make_edge_id(paper.paper_id, target.paper_id, direction, self.name),
                    source_paper_id=paper.paper_id,
                    target_paper_id=target.paper_id,
                    direction=direction,
                    relation="reference",
                    provider=self.name,
                    provider_edge_id=str(ref.get("key", "")),
                    provenance_url=url,
                    retrieved_at=now_iso(),
                )
            )
        return CitationResult(source=self.name, edges=edges, papers=papers)

    def _parse_reference(self, ref: dict[str, Any], rank: int) -> Paper | None:
        doi = normalize_doi(ref.get("DOI", ""))
        title = _strip_jats(ref.get("article-title", "") or ref.get("unstructured", "") or "")
        year = ref.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        if not title and not doi:
            return None
        return Paper(
            paper_id=make_paper_id(doi=doi, title=title, year=year),
            title=title or f"[Unresolved] {doi}",
            authors=authors_from_string(ref.get("author", "")),
            year=year,
            venue=ref.get("journal-title", "") or "",
            doi=doi,
            evidence_depth="metadata_only",
            created_at=now_iso(),
        )
