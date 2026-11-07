from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io import read_csv, read_jsonl, write_csv, write_jsonl
from .models import DECISIONS, REASON_CODES, Paper, ScreeningRow
from .normalize import now_iso

FIELDS = [
    "paper_id",
    "title",
    "year",
    "venue",
    "doi",
    "evidence_depth",
    "decision",
    "reason_code",
    "reason_text",
    "question_ids",
    "scores",
    "confidence",
    "lens_tags",
    "notes",
    "screened_by",
    "screened_at",
]


def _hard_filter(paper: Paper, plan: dict[str, Any]) -> tuple[str, str] | None:
    filters = plan.get("filters") or {}
    yf, yt = filters.get("year_from"), filters.get("year_to")
    if paper.year:
        if yf and paper.year < int(yf):
            return "DATE_RANGE", f"Year {paper.year} is before {yf}"
        if yt and paper.year > int(yt):
            return "DATE_RANGE", f"Year {paper.year} is after {yt}"
    if filters.get("exclude_retracted", True) and paper.is_retracted:
        return "RETRACTED", "Retraction status is set"
    languages = {str(x).lower() for x in (filters.get("languages") or []) if x}
    if paper.language and languages and paper.language.lower()[:2] not in {x[:2] for x in languages}:
        return "LANGUAGE", f"Language {paper.language} is outside scope"
    if not paper.title.strip():
        return "NO_TITLE", "No title available"
    if paper.is_preprint and not filters.get("include_preprints", True):
        return "NOT_PEER_REVIEWED", "Preprint excluded by plan"
    return None


def prescreen(papers: list[Paper], plan: dict[str, Any], existing: list[ScreeningRow] | None = None) -> list[ScreeningRow]:
    existing = existing or []
    by_id = {row.paper_id: row for row in existing}
    question_ids = ",".join(str(q.get("id", "")) for q in plan.get("questions", []) if q.get("id"))
    rows: list[ScreeningRow] = []
    for paper in papers:
        if paper.paper_id in by_id:
            old = by_id[paper.paper_id]
            # Refresh metadata but preserve the agent's decision.
            old.title = paper.title
            old.year = paper.year
            old.venue = paper.venue
            old.doi = paper.doi
            old.evidence_depth = paper.evidence_depth
            rows.append(old)
            continue
        hard = _hard_filter(paper, plan)
        if hard:
            code, text = hard
            rows.append(
                ScreeningRow(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    year=paper.year,
                    venue=paper.venue,
                    doi=paper.doi,
                    evidence_depth=paper.evidence_depth,
                    decision="exclude",
                    reason_code=code,
                    reason_text=text,
                    question_ids=question_ids,
                    scores=json.dumps(paper.discovery_score, ensure_ascii=False),
                    confidence="high",
                    screened_by="rule",
                    screened_at=now_iso(),
                )
            )
        else:
            min_chars = int((plan.get("filters") or {}).get("min_abstract_chars") or 0)
            insufficient = bool(min_chars and len(paper.abstract) < min_chars)
            rows.append(
                ScreeningRow(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    year=paper.year,
                    venue=paper.venue,
                    doi=paper.doi,
                    evidence_depth=paper.evidence_depth,
                    decision="maybe",
                    reason_code="INSUFFICIENT_EVIDENCE" if insufficient else "PENDING_REVIEW",
                    reason_text=(f"Abstract shorter than {min_chars} characters; retrieve or review the source before deciding eligibility."
                                 if insufficient else "Rule prescreen passed; agent/ human review required."),
                    question_ids=question_ids,
                    scores=json.dumps(paper.discovery_score, ensure_ascii=False),
                    confidence="low",
                    screened_by="rule",
                    screened_at=now_iso(),
                )
            )
    return rows


def read_screening(run_dir: str | Path) -> list[ScreeningRow]:
    run_dir = Path(run_dir)
    jsonl = run_dir / "screening.jsonl"
    csv_path = run_dir / "screening.csv"
    # Both files are written by prescreen. The agent may edit either one, so use
    # the newer file rather than silently preferring JSONL.
    if jsonl.exists() and csv_path.exists():
        use_jsonl = jsonl.stat().st_mtime >= csv_path.stat().st_mtime
    else:
        use_jsonl = jsonl.exists()
    if use_jsonl:
        return [ScreeningRow.from_dict(x) for x in read_jsonl(jsonl)]
    if csv_path.exists():
        return [ScreeningRow.from_dict(x) for x in read_csv(csv_path)]
    return []


def write_screening(run_dir: str | Path, rows: list[ScreeningRow]) -> None:
    run_dir = Path(run_dir)
    write_jsonl(run_dir / "screening.jsonl", [r.to_dict() for r in rows])
    write_csv(run_dir / "screening.csv", [r.to_dict() for r in rows], fieldnames=FIELDS, bom=True)


def validate_screening(rows: list[ScreeningRow], paper_ids: set[str]) -> list[str]:
    errors = []
    for row in rows:
        if row.paper_id not in paper_ids:
            errors.append(f"unknown paper_id: {row.paper_id}")
        if row.decision not in DECISIONS:
            errors.append(f"{row.paper_id}: invalid decision {row.decision!r}")
        if row.reason_code not in REASON_CODES:
            errors.append(f"{row.paper_id}: invalid reason_code {row.reason_code!r}")
        if row.decision == "include" and row.reason_code == "PENDING_REVIEW":
            errors.append(f"{row.paper_id}: include requires a substantive reason_code")
        if row.decision == "include" and row.reason_code not in {"IN_SCOPE", "PENDING_REVIEW"}:
            errors.append(f"{row.paper_id}: include reason conflicts with eligibility: {row.reason_code}")
        if row.decision == "exclude" and row.reason_code in {"IN_SCOPE", "PENDING_REVIEW"}:
            errors.append(f"{row.paper_id}: exclude requires a substantive exclusion reason")
        if row.decision in {"include", "maybe"} and not row.reason_text.strip():
            errors.append(f"{row.paper_id}: include/maybe requires reason_text")
    return errors
