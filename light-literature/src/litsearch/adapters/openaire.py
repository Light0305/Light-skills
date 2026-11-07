from __future__ import annotations

import re
from typing import Any

from ..models import Paper
from ..normalize import make_paper_id, normalize_doi, now_iso
from .base import Adapter, SearchResult

BASE = "https://api.openaire.eu/graph/v2/researchProducts"


def _text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(_text(x) for x in value if x)
    if isinstance(value, dict):
        return str(value.get("value") or value.get("label") or "")
    return re.sub(r"<[^>]+>", " ", str(value or "")).strip()


def _language(code: str) -> str:
    mapping = {"eng": "en", "fre": "fr", "ger": "de", "chi": "zh", "spa": "es", "jpn": "ja"}
    code = (code or "").lower()
    return mapping.get(code, code[:2])


class OpenAIREAdapter(Adapter):
    name = "openaire"

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = {
            "search": query["query"],
            "type": "publication",
            "page": 1,
            "pageSize": limit,
        }
        params.update(query.get("params", {}))
        try:
            resp = self.client.get(BASE, params=params, ttl=86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        data = resp.data or {}
        if "results" not in data:
            return SearchResult(source=self.name, status="error", error=_text(data.get("message", "unexpected response")))
        results = data.get("results") or []
        papers = [self._parse(rec, query, rank) for rank, rec in enumerate(results)]
        papers = [p for p in papers if p is not None]
        return SearchResult(
            source=self.name,
            papers=papers,
            raw_count=int((data.get("header") or {}).get("numFound") or len(results)),
        )

    def _parse(self, rec: dict[str, Any], query: dict[str, Any], rank: int) -> Paper | None:
        title = _text(rec.get("mainTitle"))
        if not title:
            return None
        abstract = _text(rec.get("descriptions"))
        authors = []
        for author in rec.get("authors") or []:
            name = author.get("fullName") or " ".join(
                x for x in [author.get("name"), author.get("surname")] if x
            )
            if name:
                authors.append(name)
        doi = ""
        for pid in rec.get("pids") or []:
            if str(pid.get("scheme", "")).lower() == "doi":
                doi = normalize_doi(pid.get("value", ""))
                break
        if not doi:
            for original in rec.get("originalIds") or []:
                if str(original).lower().startswith("10."):
                    doi = normalize_doi(str(original))
                    break
        year = None
        date = str(rec.get("publicationDate") or "")
        if len(date) >= 4 and date[:4].isdigit():
            year = int(date[:4])
        container = rec.get("container") or {}
        venue = container.get("name") or rec.get("publisher") or ""
        url = f"https://doi.org/{doi}" if doi else f"https://explore.openaire.eu/search/publication?articleId={rec.get('id', '')}"
        language = _language((rec.get("language") or {}).get("code", ""))
        concepts = []
        for subject in rec.get("subjects") or []:
            value = ((subject.get("subject") or {}).get("value")) or ""
            if value:
                concepts.append(str(value))
        oa_status = _text(rec.get("bestAccessRight")) or _text(rec.get("openAccessColor"))
        record = self.source_record(query, rank, url)
        record["source_id"] = str(rec.get("id", ""))
        return Paper(
            paper_id=make_paper_id(doi=doi, title=title, year=year),
            title=title,
            abstract=abstract,
            authors=authors,
            year=year,
            venue=str(venue),
            type=str(rec.get("type", "") or ""),
            doi=doi,
            url=url,
            oa_status=oa_status,
            language=language,
            concepts=concepts,
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )
