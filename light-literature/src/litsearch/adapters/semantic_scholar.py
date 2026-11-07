from __future__ import annotations

from typing import Any

from ..models import CitationEdge, Paper
from ..normalize import make_edge_id, make_paper_id, normalize_arxiv, normalize_doi, normalize_pmid, now_iso
from .base import Adapter, CitationResult, SearchResult

BASE = "https://api.semanticscholar.org/graph/v1"
SEARCH_FIELDS = (
    "paperId,title,abstract,year,authors,venue,citationCount,externalIds,"
    "openAccessPdf,fieldsOfStudy,publicationTypes,tldr"
)
CITE_FIELDS = (
    "contexts,intents,isInfluential,"
    "citingPaper.paperId,citingPaper.title,citingPaper.abstract,citingPaper.year,"
    "citingPaper.authors,citingPaper.venue,citingPaper.citationCount,"
    "citingPaper.externalIds,citingPaper.openAccessPdf"
)
REF_FIELDS = (
    "contexts,intents,isInfluential,"
    "citedPaper.paperId,citedPaper.title,citedPaper.abstract,citedPaper.year,"
    "citedPaper.authors,citedPaper.venue,citedPaper.citationCount,"
    "citedPaper.externalIds,citedPaper.openAccessPdf"
)


class SemanticScholarAdapter(Adapter):
    name = "semantic_scholar"

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.config.s2_api_key} if self.config.s2_api_key else {}

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = {"query": query["query"], "limit": limit, "fields": SEARCH_FIELDS}
        params.update(query.get("params", {}))
        try:
            resp = self.client.get(
                f"{BASE}/paper/search",
                params=params,
                headers=self._headers(),
                ttl=86400,
            )
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else (
                "auth_required" if getattr(exc, "status", None) in {401, 403} else "error"
            )
            return SearchResult(source=self.name, status=status, error=str(exc))
        data = (resp.data or {}).get("data") or []
        papers = [self._parse(item, query, rank) for rank, item in enumerate(data)]
        papers = [p for p in papers if p is not None]
        return SearchResult(source=self.name, papers=papers, raw_count=len(data))

    def _parse(self, item: dict[str, Any], query: dict[str, Any] | None = None, rank: int = 0) -> Paper | None:
        ext = item.get("externalIds") or {}
        doi = normalize_doi(ext.get("DOI", ""))
        arxiv_id = normalize_arxiv(ext.get("ArXiv", ""))
        pmid = normalize_pmid(ext.get("PubMed", ""))
        s2_id = str(item.get("paperId", "") or "")
        title = str(item.get("title", "") or "").strip()
        if not title and not doi and not s2_id:
            return None
        abstract = str(item.get("abstract", "") or "")
        if not abstract and isinstance(item.get("tldr"), dict):
            abstract = str(item["tldr"].get("text", "") or "")
        year = item.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        authors = [str((a or {}).get("name", "")) for a in (item.get("authors") or [])]
        authors = [a for a in authors if a]
        url = f"https://www.semanticscholar.org/paper/{s2_id}" if s2_id else ""
        record = self.source_record(query or {}, rank, url)
        record["source_id"] = s2_id
        return Paper(
            paper_id=make_paper_id(doi=doi, pmid=pmid, arxiv_id=arxiv_id, s2_id=s2_id, title=title, year=year),
            title=title or f"[Unresolved] {doi or s2_id}",
            abstract=abstract,
            authors=authors,
            year=year,
            venue=str(item.get("venue", "") or ""),
            type="article",
            doi=doi,
            arxiv_id=arxiv_id,
            pmid=pmid,
            s2_id=s2_id,
            url=url,
            pdf_url=str(((item.get("openAccessPdf") or {}).get("url")) or ""),
            cited_by_count=int(item.get("citationCount") or 0),
            is_preprint=bool(arxiv_id and not doi),
            concepts=[str(x) for x in (item.get("fieldsOfStudy") or [])],
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )

    def citations(self, paper: Paper, direction: str, limit: int) -> CitationResult:
        if not paper.s2_id:
            return CitationResult(source=self.name, status="skipped", error="no Semantic Scholar ID")
        endpoint = "citations" if direction == "forward" else "references"
        fields = CITE_FIELDS if direction == "forward" else REF_FIELDS
        try:
            resp = self.client.get(
                f"{BASE}/paper/{paper.s2_id}/{endpoint}",
                params={"fields": fields, "limit": limit},
                headers=self._headers(),
                ttl=7 * 86400,
            )
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return CitationResult(source=self.name, status=status, error=str(exc))
        rows = (resp.data or {}).get("data") or []
        edges: list[CitationEdge] = []
        papers: list[Paper] = []
        key = "citingPaper" if direction == "forward" else "citedPaper"
        for row in rows:
            target_data = row.get(key) or {}
            target = self._parse(target_data)
            if target is None:
                continue
            papers.append(target)
            edges.append(
                CitationEdge(
                    edge_id=make_edge_id(paper.paper_id, target.paper_id, direction, self.name),
                    source_paper_id=paper.paper_id,
                    target_paper_id=target.paper_id,
                    direction=direction,
                    relation="citation" if direction == "forward" else "reference",
                    provider=self.name,
                    provider_edge_id=str(target.s2_id),
                    intent="|".join(str(x) for x in (row.get("intents") or [])),
                    context=" | ".join(str(x) for x in (row.get("contexts") or [])),
                    confidence="confirmed",
                    provenance_url=f"{BASE}/paper/{paper.s2_id}/{endpoint}",
                    retrieved_at=now_iso(),
                )
            )
        return CitationResult(source=self.name, edges=edges, papers=papers)
