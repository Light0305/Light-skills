from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, read_jsonl, write_json
from .models import Paper
from .screening import read_screening


def compute_saturation(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    rows = [r.to_dict() for r in read_screening(run_dir)]
    edges = read_jsonl(run_dir / "citation_edges.jsonl")
    search_log = read_json(run_dir / "search_log.json", {}) or {}
    coverage = search_log.get("coverage", {}) or {}
    row_by_id = {r["paper_id"]: r for r in rows}

    first_round: dict[str, int] = {}
    for paper in papers:
        rounds = []
        for record in paper.source_records:
            if record.get("round") is not None and str(record.get("query_id", "")).startswith("cite:"):
                try:
                    rounds.append(int(record["round"]))
                except (TypeError, ValueError):
                    continue
        first_round[paper.paper_id] = min(rounds) if rounds else 0

    edge_rounds = sorted({int(e.get("round", 1)) for e in edges})
    rounds_data: list[dict[str, Any]] = []
    cumulative_included = 0
    cumulative_maybe = 0
    for round_no in edge_rounds:
        ids = {paper.paper_id for paper in papers if first_round.get(paper.paper_id) == round_no}
        new_included = sum(1 for pid in ids if row_by_id.get(pid, {}).get("decision") == "include")
        new_maybe = sum(1 for pid in ids if row_by_id.get(pid, {}).get("decision") == "maybe")
        previous_included = cumulative_included
        cumulative_included += new_included
        cumulative_maybe += new_maybe
        marginal = (new_included / len(ids)) if ids else 0.0
        threshold = max(3, 0.02 * max(1, previous_included))
        # Without any included papers, inclusion-based yield is meaningless.
        # Fall back to a raw new-unique threshold and keep the result provisional.
        if cumulative_included > 0:
            low_yield = new_included < threshold and marginal < 0.05
        else:
            low_yield = len(ids) < 3
        rounds_data.append(
            {
                "round": round_no,
                "new_unique": len(ids),
                "new_included": new_included,
                "new_maybe": new_maybe,
                "marginal_relevance_rate": round(marginal, 4),
                "cumulative_included": cumulative_included,
                "low_yield": low_yield,
            }
        )

    saturated = False
    screening_ready = cumulative_included > 0
    if len(rounds_data) >= 2 and screening_ready:
        saturated = all(row["low_yield"] for row in rounds_data[-2:])
    if not rounds_data:
        stopping_reason = "no_citation_round"
    elif saturated:
        stopping_reason = "two_consecutive_low_yield"
    elif len(rounds_data) == 1:
        stopping_reason = "one_round_only"
    elif not screening_ready:
        stopping_reason = "no_included_screening"
    else:
        stopping_reason = "max_rounds_or_budget"

    data = {
        "rounds": rounds_data,
        "coverage": coverage,
        "query_count": coverage.get("query_count", 0),
        "coverage_plateau": bool(coverage.get("coverage_plateau", False)),
        "mean_rediscovery_rate": coverage.get("mean_rediscovery_rate", 0.0),
        "screening_ready": screening_ready,
        "saturated": saturated,
        "provisional": not saturated,
        "stopping_reason": stopping_reason,
        "cumulative_included": cumulative_included,
        "cumulative_maybe": cumulative_maybe,
    }
    write_json(run_dir / "saturation.json", data)
    return data
