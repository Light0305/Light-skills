from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import Config
from ..http import HttpClient
from ..models import CitationEdge, Paper
from ..normalize import now_iso


@dataclass
class SearchResult:
    source: str
    papers: list[Paper] = field(default_factory=list)
    raw_count: int = 0
    status: str = "ok"  # ok | empty | rate_limited | auth_required | blocked | error | skipped
    error: str = ""


@dataclass
class CitationResult:
    source: str
    edges: list[CitationEdge] = field(default_factory=list)
    papers: list[Paper] = field(default_factory=list)
    status: str = "ok"
    error: str = ""


class Adapter:
    name = "base"

    def __init__(self, client: HttpClient, config: Config) -> None:
        self.client = client
        self.config = config

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        raise NotImplementedError

    def citations(self, paper: Paper, direction: str, limit: int) -> CitationResult:
        return CitationResult(source=self.name, status="skipped", error="not supported")

    def get_by_doi(self, doi: str) -> Paper | None:
        return None

    def source_record(self, query: dict[str, Any], rank: int, url: str) -> dict[str, Any]:
        return {
            "source": self.name,
            "source_id": "",
            "query_id": query.get("query_id", ""),
            "leg_id": query.get("leg_id", ""),
            "lens_id": query.get("lens_id", ""),
            "rank": rank,
            "retrieved_at": now_iso(),
            "url": url,
        }


def first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
