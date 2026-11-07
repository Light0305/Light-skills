from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    type: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pmid: str = ""
    pmcid: str = ""
    openalex_id: str = ""
    s2_id: str = ""
    url: str = ""
    pdf_url: str = ""
    pdf_path: str = ""
    pdf_status: str = ""
    pdf_source: str = ""
    pdf_sha256: str = ""
    oa_status: str = ""
    license: str = ""
    cited_by_count: int = 0
    is_retracted: bool = False
    is_preprint: bool = False
    language: str = ""
    concepts: list[str] = field(default_factory=list)
    referenced_works: list[str] = field(default_factory=list)
    related_works: list[str] = field(default_factory=list)
    source_records: list[dict[str, Any]] = field(default_factory=list)
    evidence_depth: str = "metadata_only"
    discovery_score: dict[str, Any] = field(default_factory=dict)
    versions: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Paper":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class CitationEdge:
    edge_id: str
    source_paper_id: str
    target_paper_id: str
    direction: str  # backward | forward
    relation: str  # reference | citation
    provider: str
    provider_edge_id: str = ""
    intent: str = ""
    context: str = ""
    round: int = 1
    confidence: str = "confirmed"
    provenance_url: str = ""
    retrieved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CitationEdge":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class ScreeningRow:
    paper_id: str
    title: str = ""
    year: int | None = None
    venue: str = ""
    doi: str = ""
    evidence_depth: str = "metadata_only"
    decision: str = "maybe"  # include | exclude | maybe
    reason_code: str = "PENDING_REVIEW"
    reason_text: str = ""
    question_ids: str = ""
    scores: str = ""
    confidence: str = "low"
    lens_tags: str = ""
    notes: str = ""
    screened_by: str = "rule"
    screened_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScreeningRow":
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in data.items() if k in allowed}
        if "year" in clean and isinstance(clean["year"], str):
            try:
                clean["year"] = int(clean["year"]) if clean["year"].strip() else None
            except ValueError:
                clean["year"] = None
        return cls(**clean)


DECISIONS = {"include", "exclude", "maybe"}

REASON_CODES = {
    "PENDING_REVIEW",
    "IN_SCOPE",
    "OUT_OF_SCOPE",
    "WRONG_POPULATION",
    "WRONG_DESIGN",
    "NO_PRIMARY_DATA",
    "NOT_PEER_REVIEWED",
    "DUPLICATE_VERSION",
    "LANGUAGE",
    "DATE_RANGE",
    "RETRACTED",
    "LOW_RELEVANCE",
    "INSUFFICIENT_EVIDENCE",
    "UNABLE_TO_VERIFY",
    "BUDGET_LIMIT",
    "NO_TITLE",
}
