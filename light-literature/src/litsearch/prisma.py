from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, read_jsonl, write_json
from .normalize import now_iso


def build_prisma_s_audit(run_dir: str | Path) -> dict[str, Any]:
    """Build a PRISMA-S-informed 16-item search-reporting audit.

    This is not a claim of PRISMA-S compliance. It records what the run did,
    what was implicit, and what was skipped.
    """
    run_dir = Path(run_dir)
    plan = read_json(run_dir / "query_plan.json", {}) or {}
    compiled = read_json(run_dir / "compiled_queries.json", {}) or {}
    search_log = read_json(run_dir / "search_log.json", {}) or {}
    merge_log = read_json(run_dir / "merge_log.json", {}) or {}
    edges = read_jsonl(run_dir / "citation_edges.jsonl")
    filters = plan.get("filters", {}) or {}
    sources = compiled.get("sources") or (plan.get("source_policy") or {}).get("enabled", [])
    source_runs = search_log.get("source_runs", []) or []
    run_date = str(search_log.get("started_at") or now_iso())
    identified = int((search_log.get("totals") or {}).get("identified") or 0)

    items = [
        {
            "item": 1,
            "label": "Database name",
            "status": "performed",
            "detail": ", ".join(sources) if sources else "none",
        },
        {
            "item": 2,
            "label": "Multi-database searching",
            "status": "implicit",
            "detail": "Independent API searches; no single platform bundled multiple databases.",
        },
        {
            "item": 3,
            "label": "Study registries",
            "status": "skipped",
            "detail": "Clinical trial/study registries were not searched.",
        },
        {
            "item": 4,
            "label": "Online resources and browsing",
            "status": "skipped",
            "detail": "No hand browsing, tables of contents, or conference websites.",
        },
        {
            "item": 5,
            "label": "Citation searching",
            "status": "performed" if edges else "pending",
            "detail": f"{len(edges)} citation edges recorded." if edges else "No citation expansion run yet.",
        },
        {
            "item": 6,
            "label": "Contacts",
            "status": "skipped",
            "detail": "No authors, experts, or manufacturers were contacted.",
        },
        {
            "item": 7,
            "label": "Other methods",
            "status": "not_applicable",
            "detail": "No additional search methods.",
        },
        {
            "item": 8,
            "label": "Full search strategies",
            "status": "performed",
            "detail": "compiled_queries.json contains the exact per-source queries.",
        },
        {
            "item": 9,
            "label": "Limits and restrictions",
            "status": "performed",
            "detail": (
                f"years {filters.get('year_from', '?')}–{filters.get('year_to', '?')}; "
                f"languages {', '.join(filters.get('languages', [])) or 'n/a'}; "
                f"preprints {'allowed' if filters.get('include_preprints', True) else 'excluded'}"
            ),
        },
        {
            "item": 10,
            "label": "Search filters",
            "status": "implicit",
            "detail": "Concept blocks and controlled-vocabulary terms; no published search filter was applied.",
        },
        {
            "item": 11,
            "label": "Prior work",
            "status": "skipped",
            "detail": "Strategies were generated for this run, not adapted from a prior review.",
        },
        {
            "item": 12,
            "label": "Updates",
            "status": "skipped",
            "detail": "Single run; no rerun or alerting schedule.",
        },
        {
            "item": 13,
            "label": "Dates of searches",
            "status": "performed",
            "detail": run_date,
        },
        {
            "item": 14,
            "label": "Peer review",
            "status": "skipped",
            "detail": "No PRESS-style peer review of the search strategy.",
        },
        {
            "item": 15,
            "label": "Total records",
            "status": "performed",
            "detail": f"{identified} records identified across {len(source_runs)} source runs.",
        },
        {
            "item": 16,
            "label": "Deduplication",
            "status": "performed",
            "detail": f"merge_log.json; {merge_log.get('duplicates_removed', 0)} duplicates removed.",
        },
    ]
    data = {
        "schema_version": "1.0",
        "standard": "PRISMA-S-informed (not a compliance claim)",
        "generated_at": now_iso(),
        "items": items,
        "source_health": search_log.get("source_health", {}),
        "coverage": search_log.get("coverage", {}),
    }
    write_json(run_dir / "prisma_s_audit.json", data)
    return data
