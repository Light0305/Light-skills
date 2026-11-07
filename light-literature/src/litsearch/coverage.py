from __future__ import annotations

from typing import Any

from .models import Paper


def build_coverage(
    source_runs: list[dict[str, Any]],
    papers: list[Paper],
    *,
    plateau_window: int = 3,
) -> dict[str, Any]:
    """Estimate coverage from rediscovery across independent query legs.

    This is a heuristic, not a completeness proof. A high rediscovery rate means
    later queries mostly re-find papers already seen; it does not mean the
    literature is exhausted.
    """
    query_ids: list[str] = []
    source_by_query: dict[str, str] = {}
    for run in source_runs:
        qid = str(run.get("query_id", ""))
        if qid and run.get("status") in {"ok", "empty"} and qid not in source_by_query:
            query_ids.append(qid)
            source_by_query[qid] = str(run.get("source", ""))
    if not query_ids:
        return {
            "query_count": 0,
            "curve": [],
            "coverage_plateau": False,
            "mean_rediscovery_rate": 0.0,
        }

    query_to_ids: dict[str, set[str]] = {qid: set() for qid in query_ids}
    for paper in papers:
        for record in paper.source_records:
            qid = str(record.get("query_id", ""))
            if qid in query_to_ids:
                query_to_ids[qid].add(paper.paper_id)

    cumulative: set[str] = set()
    curve: list[dict[str, Any]] = []
    for qid in query_ids:
        ids = query_to_ids.get(qid, set())
        new = ids - cumulative
        retrieved = len(ids)
        rediscovery = 1 - (len(new) / retrieved) if retrieved else 0.0
        cumulative |= ids
        curve.append(
            {
                "query_id": qid,
                "source": source_by_query.get(qid, ""),
                "retrieved": retrieved,
                "new_unique": len(new),
                "cumulative_unique": len(cumulative),
                "rediscovery_rate": round(rediscovery, 4),
            }
        )

    recent = curve[-plateau_window:]
    plateau = bool(recent) and all(
        row["new_unique"] < max(3, 0.02 * max(1, row["cumulative_unique"]))
        and row["rediscovery_rate"] >= 0.8
        for row in recent
    )
    mean_rediscovery = sum(row["rediscovery_rate"] for row in curve) / len(curve)
    return {
        "query_count": len(curve),
        "curve": curve,
        "coverage_plateau": plateau,
        "mean_rediscovery_rate": round(mean_rediscovery, 4),
    }
