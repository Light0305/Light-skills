from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..models import Paper
from ..normalize import normalize_doi
from .base import Adapter, SearchResult

BASE = "https://api.unpaywall.org/v2"


class UnpaywallAdapter(Adapter):
    """DOI lookup for open-access PDF locations. Not a search source."""

    name = "unpaywall"

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        return SearchResult(
            source=self.name,
            status="skipped",
            error="Unpaywall is a DOI lookup, not a search source.",
        )

    def enrich(self, paper: Paper) -> dict[str, Any]:
        if not paper.doi or not self.config.unpaywall_email:
            return {}
        url = f"{BASE}/{quote(normalize_doi(paper.doi), safe='')}"
        try:
            resp = self.client.get(
                url,
                params={"email": self.config.unpaywall_email},
                ttl=7 * 86400,
            )
        except Exception:  # noqa: BLE001
            return {}
        data = resp.data or {}
        locations = data.get("oa_locations") or []
        ordered = sorted(
            locations,
            key=lambda x: 0 if str(x.get("host_type", "")).lower() == "repository" else 1,
        )
        pdf_urls = [str(x.get("url_for_pdf")) for x in ordered if x.get("url_for_pdf")]
        best = data.get("best_oa_location") or {}
        if not best:
            best = next((x for x in ordered if x.get("url_for_pdf")), {}) or (ordered[0] if ordered else {})
        return {
            "is_oa": bool(data.get("is_oa")),
            "oa_status": str(data.get("oa_status", "") or ""),
            "pdf_url": str(best.get("url_for_pdf") or best.get("url") or ""),
            "pdf_urls": list(dict.fromkeys(pdf_urls)),
            "license": str(best.get("license", "") or ""),
            "url": str(best.get("url", "") or ""),
        }

    def get_by_doi(self, doi: str) -> Paper | None:
        return None
