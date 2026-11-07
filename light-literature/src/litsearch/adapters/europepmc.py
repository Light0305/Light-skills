from __future__ import annotations

import re
from typing import Any

from ..models import CitationEdge, Paper
from ..normalize import (
    authors_from_string,
    make_edge_id,
    make_paper_id,
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    now_iso,
)
from .base import Adapter, CitationResult, SearchResult, as_list, first

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


class EuropePMCAdapter(Adapter):
    name = "europepmc"

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = {
            "query": query["query"],
            "format": "json",
            "pageSize": limit,
            "resultType": "core",
        }
        if query.get("sort") == "recent":
            params["sort"] = "P_PDATE_D desc"
        elif query.get("sort") == "cited":
            params["sort"] = "CITED desc"
        url = f"{BASE}/search"
        try:
            resp = self.client.get(url, params=params, ttl=86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        data = resp.data or {}
        records = (data.get("resultList") or {}).get("result") or []
        papers = [self._parse(rec, query, rank) for rank, rec in enumerate(records)]
        papers = [p for p in papers if p is not None]
        return SearchResult(source=self.name, papers=papers, raw_count=len(records))

    def _parse(self, rec: dict[str, Any], query: dict[str, Any], rank: int) -> Paper | None:
        title = _strip_tags(rec.get("title", ""))
        if not title:
            return None
        abstract = _strip_tags(rec.get("abstractText", ""))
        source = str(rec.get("source", ""))
        source_id = str(rec.get("id", ""))
        pmid = normalize_pmid(rec.get("pmid") or (source_id if source == "MED" else ""))
        pmcid = normalize_pmcid(rec.get("pmcid") or (source_id if source == "PMC" else ""))
        doi = normalize_doi(rec.get("doi", ""))
        pub_types = [str(x) for x in as_list((rec.get("pubTypeList") or {}).get("pubType"))]
        is_retracted = any("retract" in p.lower() for p in pub_types)
        is_preprint = source == "PPR" or any("preprint" in p.lower() for p in pub_types)
        journal = (
            ((rec.get("journalInfo") or {}).get("journal") or {}).get("title")
            or rec.get("journalTitle")
            or (rec.get("bookOrReportDetails") or {}).get("publisher")
            or ""
        )
        year = rec.get("pubYear")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        pdf_url = ""
        for item in as_list((rec.get("fullTextUrlList") or {}).get("fullTextUrl")):
            if str(item.get("documentStyle", "")).lower() == "pdf":
                pdf_url = item.get("url", "")
                break
        url = f"https://europepmc.org/article/{source}/{source_id}" if source and source_id else ""
        record = self.source_record(query, rank, url)
        record["source_id"] = source_id
        paper = Paper(
            paper_id=make_paper_id(doi=doi, pmid=pmid, pmcid=pmcid, title=title, year=year),
            title=title,
            abstract=abstract,
            authors=authors_from_string(rec.get("authorString", "")),
            year=year,
            venue=journal,
            type=first(pub_types) or "article",
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            url=url,
            pdf_url=pdf_url,
            cited_by_count=int(rec.get("citedByCount") or 0),
            is_retracted=is_retracted,
            is_preprint=is_preprint,
            language=str(rec.get("language", "") or ""),
            concepts=[],
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )
        return paper

    def citations(self, paper: Paper, direction: str, limit: int) -> CitationResult:
        if paper.pmid:
            source, ident = "MED", paper.pmid
        elif paper.pmcid:
            source, ident = "PMC", paper.pmcid
        else:
            return CitationResult(source=self.name, status="skipped", error="no PMID/PMCID")
        endpoint = "citations" if direction == "forward" else "references"
        url = f"{BASE}/{source}/{ident}/{endpoint}"
        try:
            resp = self.client.get(url, params={"format": "json", "pageSize": limit}, ttl=7 * 86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return CitationResult(source=self.name, status=status, error=str(exc))
        data = resp.data or {}
        if direction == "forward":
            rows = (data.get("citationList") or {}).get("citation") or []
        else:
            rows = (data.get("referenceList") or {}).get("reference") or []
        edges: list[CitationEdge] = []
        papers: list[Paper] = []
        for row in rows:
            target = self._parse_citation(row)
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
                    provider_edge_id=str(row.get("id", "")),
                    provenance_url=url,
                    retrieved_at=now_iso(),
                )
            )
        return CitationResult(source=self.name, edges=edges, papers=papers)

    def _parse_citation(self, row: dict[str, Any]) -> Paper | None:
        title = _strip_tags(row.get("title", ""))
        source = str(row.get("source", ""))
        ident = str(row.get("id", ""))
        pmid = normalize_pmid(ident if source == "MED" else row.get("pmid", ""))
        pmcid = normalize_pmcid(ident if source == "PMC" else row.get("pmcid", ""))
        doi = normalize_doi(row.get("doi", ""))
        if not title and not doi and not pmid and not pmcid:
            return None
        year = row.get("pubYear")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        url = f"https://europepmc.org/article/{source}/{ident}" if source and ident else ""
        return Paper(
            paper_id=make_paper_id(doi=doi, pmid=pmid, pmcid=pmcid, title=title, year=year),
            title=title or f"[Unresolved] {doi or pmid or pmcid}",
            authors=authors_from_string(row.get("authorString", "")),
            year=year,
            venue=row.get("journalAbbreviation", "") or "",
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            url=url,
            evidence_depth="metadata_only",
            created_at=now_iso(),
        )
