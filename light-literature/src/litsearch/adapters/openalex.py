from __future__ import annotations

from typing import Any

from ..models import CitationEdge, Paper
from ..normalize import authors_from_string, make_edge_id, make_paper_id, normalize_doi, now_iso
from .base import Adapter, CitationResult, SearchResult

BASE = "https://api.openalex.org/works"
SELECT = (
    "id,doi,title,display_name,publication_year,publication_date,authorships,"
    "primary_location,best_oa_location,cited_by_count,type,open_access,"
    "referenced_works,related_works,abstract_inverted_index,language,is_retracted,primary_topic"
)


def _inverted_to_text(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in inverted.items():
        for idx in indexes:
            positions.append((idx, word))
    return " ".join(word for _, word in sorted(positions))


def _openalex_id(value: str) -> str:
    return str(value or "").rstrip("/").split("/")[-1]


class OpenAlexAdapter(Adapter):
    name = "openalex"

    def _base_params(self, limit: int) -> dict[str, Any]:
        params: dict[str, Any] = {"per-page": limit, "select": SELECT}
        if self.config.mailto:
            params["mailto"] = self.config.mailto
        if self.config.openalex_api_key:
            params["api_key"] = self.config.openalex_api_key
        return params

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = self._base_params(limit)
        params["search"] = query["query"]
        for key in ("filter", "sort"):
            if query.get("params", {}).get(key):
                params[key] = query["params"][key]
        try:
            resp = self.client.get(BASE, params=params, ttl=86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else (
                "auth_required" if getattr(exc, "status", None) in {401, 403} else "error"
            )
            return SearchResult(source=self.name, status=status, error=str(exc))
        results = ((resp.data or {}).get("results")) or []
        papers = [self._parse(item, query, rank) for rank, item in enumerate(results)]
        papers = [p for p in papers if p is not None]
        return SearchResult(source=self.name, papers=papers, raw_count=len(results))

    def _parse(self, item: dict[str, Any], query: dict[str, Any] | None = None, rank: int = 0) -> Paper | None:
        openalex_id = _openalex_id(item.get("id", ""))
        title = str(item.get("display_name") or item.get("title") or "").strip()
        doi = normalize_doi(item.get("doi", ""))
        if not title and not doi and not openalex_id:
            return None
        abstract = _inverted_to_text(item.get("abstract_inverted_index"))
        authors = [
            str(((a.get("author") or {}).get("display_name")) or "")
            for a in item.get("authorships", []) or []
        ]
        authors = [a for a in authors if a]
        year = item.get("publication_year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        venue = ((item.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        pdf_url = (
            (item.get("best_oa_location") or {}).get("pdf_url")
            or (item.get("primary_location") or {}).get("pdf_url")
            or ""
        )
        url = (
            (item.get("primary_location") or {}).get("landing_page_url")
            or (f"https://doi.org/{doi}" if doi else "")
            or (f"https://openalex.org/{openalex_id}" if openalex_id else "")
        )
        refs = [_openalex_id(x) for x in (item.get("referenced_works") or [])]
        related = [_openalex_id(x) for x in (item.get("related_works") or [])]
        concepts = []
        topic = item.get("primary_topic") or {}
        if topic.get("display_name"):
            concepts.append(topic["display_name"])
        record = self.source_record(query or {}, rank, url)
        record["source_id"] = openalex_id
        return Paper(
            paper_id=make_paper_id(doi=doi, openalex_id=openalex_id, title=title, year=year),
            title=title or f"[Unresolved] {doi or openalex_id}",
            abstract=abstract,
            authors=authors,
            year=year,
            venue=str(venue),
            type=str(item.get("type", "") or ""),
            doi=doi,
            openalex_id=openalex_id,
            url=url,
            pdf_url=pdf_url,
            cited_by_count=int(item.get("cited_by_count") or 0),
            is_retracted=bool(item.get("is_retracted")),
            is_preprint=str(item.get("type", "")).lower() in {"preprint", "posted-content"},
            language=str(item.get("language", "") or ""),
            concepts=concepts,
            referenced_works=refs,
            related_works=related,
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )

    def citations(self, paper: Paper, direction: str, limit: int) -> CitationResult:
        if not paper.openalex_id:
            return CitationResult(source=self.name, status="skipped", error="no OpenAlex ID")
        if direction == "forward":
            params = self._base_params(limit)
            params["filter"] = f"cites:{paper.openalex_id}"
            url = BASE
            try:
                resp = self.client.get(url, params=params, ttl=7 * 86400)
            except Exception as exc:  # noqa: BLE001
                status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
                return CitationResult(source=self.name, status=status, error=str(exc))
            results = ((resp.data or {}).get("results")) or []
            papers = [self._parse(item) for item in results]
            papers = [p for p in papers if p is not None]
        else:
            refs = paper.referenced_works[:limit]
            if not refs:
                return CitationResult(source=self.name, status="skipped", error="no referenced_works")
            params = self._base_params(limit)
            params["filter"] = "openalex:" + "|".join(refs)
            try:
                resp = self.client.get(BASE, params=params, ttl=7 * 86400)
            except Exception as exc:  # noqa: BLE001
                status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
                return CitationResult(source=self.name, status=status, error=str(exc))
            results = ((resp.data or {}).get("results")) or []
            papers = [self._parse(item) for item in results]
            papers = [p for p in papers if p is not None]
            found = {p.openalex_id for p in papers}
            for ref in refs:
                if ref not in found:
                    papers.append(
                        Paper(
                            paper_id=make_paper_id(openalex_id=ref),
                            title=f"[Unresolved] OpenAlex {ref}",
                            openalex_id=ref,
                            evidence_depth="metadata_only",
                            created_at=now_iso(),
                        )
                    )
        edges: list[CitationEdge] = []
        for target in papers:
            edges.append(
                CitationEdge(
                    edge_id=make_edge_id(paper.paper_id, target.paper_id, direction, self.name),
                    source_paper_id=paper.paper_id,
                    target_paper_id=target.paper_id,
                    direction=direction,
                    relation="citation" if direction == "forward" else "reference",
                    provider=self.name,
                    provenance_url=f"{BASE}?filter={'cites:' + paper.openalex_id if direction == 'forward' else 'openalex:' + '|'.join(paper.referenced_works[:limit])}",
                    retrieved_at=now_iso(),
                )
            )
        return CitationResult(source=self.name, edges=edges, papers=papers)
