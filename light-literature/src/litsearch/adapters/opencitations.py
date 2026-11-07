from __future__ import annotations

import re
from typing import Any

from ..models import CitationEdge, Paper
from ..normalize import make_edge_id, make_paper_id, normalize_doi, now_iso
from .base import Adapter, CitationResult

BASE = "https://api.opencitations.net/index/v2"


def _extract_doi(value: str) -> str:
    match = re.search(r"doi:([^\s;]+)", value or "", flags=re.I)
    return normalize_doi(match.group(1)) if match else ""


def _extract_openalex(value: str) -> str:
    match = re.search(r"openalex:(W\d+)", value or "", flags=re.I)
    return match.group(1) if match else ""


class OpenCitationsAdapter(Adapter):
    name = "opencitations"

    def citations(self, paper: Paper, direction: str, limit: int) -> CitationResult:
        if not paper.doi:
            return CitationResult(source=self.name, status="skipped", error="no DOI")
        endpoint = "citations" if direction == "forward" else "references"
        url = f"{BASE}/{endpoint}/doi:{paper.doi}"
        try:
            resp = self.client.get(url, ttl=7 * 86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return CitationResult(source=self.name, status=status, error=str(exc))
        rows = resp.data or []
        if not isinstance(rows, list):
            return CitationResult(source=self.name, status="error", error="unexpected response")
        edges: list[CitationEdge] = []
        papers: list[Paper] = []
        for row in rows[:limit]:
            other = row.get("citing") if direction == "forward" else row.get("cited")
            doi = _extract_doi(str(other or ""))
            openalex_id = _extract_openalex(str(other or ""))
            if not doi and not openalex_id:
                continue
            target = Paper(
                paper_id=make_paper_id(doi=doi, openalex_id=openalex_id),
                title=f"[Unresolved] {doi or openalex_id}",
                doi=doi,
                openalex_id=openalex_id,
                evidence_depth="metadata_only",
                created_at=now_iso(),
            )
            papers.append(target)
            edges.append(
                CitationEdge(
                    edge_id=make_edge_id(paper.paper_id, target.paper_id, direction, self.name),
                    source_paper_id=paper.paper_id,
                    target_paper_id=target.paper_id,
                    direction=direction,
                    relation="citation" if direction == "forward" else "reference",
                    provider=self.name,
                    provider_edge_id=str(row.get("oci", "")),
                    provenance_url=url,
                    retrieved_at=now_iso(),
                )
            )
        return CitationResult(source=self.name, edges=edges, papers=papers)
