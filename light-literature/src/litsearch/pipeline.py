from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .adapters import (
    ALL_SOURCES,
    DEFAULT_SOURCES,
    EXPERIMENTAL_SOURCES,
    OPTIONAL_SOURCES,
    SOURCE_CAPABILITIES,
    get_adapter,
    requires_key,
)
from .config import Config, load_config
from .citations import expand_citations
from .citation_analysis import analyze_citations
from .coverage import build_coverage
from .dedupe import dedupe_papers
from .exports import export_all
from .http import HttpClient
from .health import health_weights, load_health, update_health
from .io import ensure_dir, read_json, read_jsonl, write_json, write_jsonl
from .models import Paper
from .normalize import now_iso
from .pdf import fetch_pdfs
from .prisma import build_prisma_s_audit
from .query import compile_plan, default_plan, validate_plan
from .render import build_report_data, render_reports, verify_run
from .saturation import compute_saturation
from .screening import prescreen, read_screening, validate_screening, write_screening
from .scoring import score_papers, select_stratified


def init_plan(
    direction: str,
    *,
    direction_en: str | None = None,
    domain: str = "general",
    framework: str | None = None,
    languages: list[str] | None = None,
    out: str | Path,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    plan = default_plan(
        direction,
        direction_en=direction_en,
        domain=domain,
        framework=framework,
        languages=languages,
        year_from=year_from,
        year_to=year_to,
    )
    write_json(out, plan)
    return plan


def load_and_validate(plan_path: str | Path, *, strict: bool = False) -> dict[str, Any]:
    plan = read_json(plan_path)
    if plan is None:
        raise FileNotFoundError(f"Plan not found: {plan_path}")
    validate_plan(plan, strict=strict)
    return plan


def compile_plan_file(
    plan_path: str | Path,
    *,
    out: str | Path,
    sources: list[str] | None = None,
    enable_optional: bool = False,
    config: Config | None = None,
) -> dict[str, Any]:
    plan = load_and_validate(plan_path)
    config = config or load_config()
    compiled = compile_plan(plan, config, sources=sources, enable_optional=enable_optional)
    write_json(out, compiled)
    return compiled


def run_search(
    plan_path: str | Path,
    run_dir: str | Path,
    *,
    sources: list[str] | None = None,
    max_per_source: int | None = None,
    enable_optional: bool = False,
    config: Config | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    plan = load_and_validate(plan_path)
    run_dir = ensure_dir(run_dir)
    write_json(run_dir / "query_plan.json", plan)
    compiled = compile_plan(plan, config, sources=sources, enable_optional=enable_optional)
    write_json(run_dir / "compiled_queries.json", compiled)

    queries = compiled["queries"]
    source_counts = Counter(q["source"] for q in queries)
    max_per_source = int(max_per_source or (plan.get("budgets") or {}).get("max_per_source", 80))
    client = HttpClient(config)
    started = now_iso()
    source_runs: list[dict[str, Any]] = []
    all_papers: list[Paper] = []
    source_ok = 0
    source_failed = 0

    for query in queries:
        source = query["source"]
        per_query = max(5, min(50, max_per_source // max(1, source_counts[source])))
        if requires_key(source, config):
            result_status = "auth_required"
            result_error = f"{source} requires an API key; skipped in keyless mode."
            result_papers: list[Paper] = []
        else:
            try:
                adapter = get_adapter(source, client, config)
                result = adapter.search(query, per_query)
            except Exception as exc:  # noqa: BLE001
                result_status = "error"
                result_error = str(exc)
                result_papers = []
            else:
                result_status = result.status
                result_error = result.error
                result_papers = result.papers
        if result_status in {"ok", "empty"}:
            source_ok += 1
        else:
            source_failed += 1
        for paper in result_papers:
            paper.source_records.append(
                {
                    "source": source,
                    "source_id": "",
                    "query_id": query["query_id"],
                    "leg_id": query.get("leg_id", ""),
                    "lens_id": query.get("lens_id", ""),
                    "rank": len(paper.source_records),
                    "retrieved_at": now_iso(),
                    "url": paper.url,
                }
            )
        all_papers.extend(result_papers)
        source_runs.append(
            {
                "source": source,
                "query_id": query["query_id"],
                "leg_id": query.get("leg_id", ""),
                "lens_id": query.get("lens_id", ""),
                "sort": query.get("sort", ""),
                "query": query.get("query", ""),
                "status": result_status,
                "fetched": len(result_papers),
                "error": result_error,
                "retrieved_at": now_iso(),
            }
        )

    deduped, merge_log = dedupe_papers(all_papers)
    health_state = update_health(config.cache_dir, source_runs)
    health = health_weights(health_state)
    deduped = score_papers(deduped, plan, source_health=health)
    max_total = int((plan.get("budgets") or {}).get("max_total_candidates", 400))
    if len(deduped) > max_total:
        deduped = select_stratified(deduped, max_total)
    rows = prescreen(deduped, plan)

    write_jsonl(run_dir / "papers.jsonl", [p.to_dict() for p in deduped])
    write_json(run_dir / "merge_log.json", merge_log)
    write_screening(run_dir, rows)

    identified = sum(int(r.get("fetched", 0) or 0) for r in source_runs)
    search_log = {
        "schema_version": "1.0",
        "run_id": run_dir.name,
        "plan_hash": compiled.get("plan_hash", ""),
        "started_at": started,
        "finished_at": now_iso(),
        "source_runs": source_runs,
        "events": [
            {
                "type": "search",
                "timestamp": now_iso(),
                "detail": {
                    "queries": len(queries),
                    "raw_records": len(all_papers),
                    "unique_records": len(deduped),
                },
            }
        ],
        "totals": {
            "identified": identified,
            "unique": len(deduped),
            "duplicates_removed": merge_log.get("duplicates_removed", 0),
        },
        "source_health": health_state,
        "partial": source_failed > 0,
        "degraded_sources": sorted(
            {r["source"] for r in source_runs if r.get("status") not in {"ok", "empty"}}
        ),
        "coverage": build_coverage(source_runs, deduped),
        "prisma_s": {
            "database_search": "performed",
            "citation_searching": "pending",
            "search_strategy_reporting": "compiled_queries.json",
            "limits": "recorded",
        },
    }
    write_json(run_dir / "search_log.json", search_log)
    write_json(
        run_dir / "run.json",
        {
            "run_id": run_dir.name,
            "plan_hash": compiled.get("plan_hash", ""),
            "created_at": started,
            "sources": compiled.get("sources", []),
            "queries": len(queries),
        },
    )
    if not all_papers and source_failed and not source_ok:
        build_prisma_s_audit(run_dir)
        raise RuntimeError("All enabled sources failed; see search_log.json for details")
    build_prisma_s_audit(run_dir)
    return {
        "run_dir": str(run_dir),
        "queries": len(queries),
        "raw_records": len(all_papers),
        "unique_records": len(deduped),
        "screening_rows": len(rows),
        "source_runs": len(source_runs),
        "queries_ok": source_ok,
        "queries_failed": source_failed,
        "partial": source_failed > 0,
        "degraded_sources": sorted(
            {r["source"] for r in source_runs if r.get("status") not in {"ok", "empty"}}
        ),
    }


def run_screen_prescreen(run_dir: str | Path, *, new_only: bool = False) -> dict[str, Any]:
    run_dir = Path(run_dir)
    plan = read_json(run_dir / "query_plan.json", {}) or {}
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    existing = read_screening(run_dir)
    rows = prescreen(papers, plan, existing)
    write_screening(run_dir, rows)
    return {"screening_rows": len(rows), "new_only": new_only}


def run_screen_validate(run_dir: str | Path) -> list[str]:
    run_dir = Path(run_dir)
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    rows = read_screening(run_dir)
    return validate_screening(rows, {p.paper_id for p in papers})


def run_citation_expand(
    run_dir: str | Path,
    *,
    round_no: int = 1,
    seeds: int | None = None,
    sources: list[str] | None = None,
    directions: list[str] | None = None,
    seed_paper_ids: list[str] | None = None,
    config: Config | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    run_dir = Path(run_dir)
    plan = read_json(run_dir / "query_plan.json", {}) or {}
    return expand_citations(
        run_dir,
        plan,
        config,
        round_no=round_no,
        seed_count=seeds,
        sources=sources,
        directions=directions,
        seed_paper_ids=seed_paper_ids,
    )


def run_citation_analyze(run_dir: str | Path) -> dict[str, Any]:
    return analyze_citations(run_dir)


def run_saturation(run_dir: str | Path) -> dict[str, Any]:
    return compute_saturation(run_dir)


def run_oa_enrich(
    run_dir: str | Path,
    *,
    limit: int = 20,
    config: Config | None = None,
) -> dict[str, Any]:
    """Fill OA PDF links via Unpaywall. Email only; no registration."""
    config = config or load_config()
    run_dir = Path(run_dir)
    if not config.unpaywall_email:
        return {
            "status": "skipped",
            "reason": "Set LITSEARCH_MAILTO or UNPAYWALL_EMAIL to use Unpaywall.",
            "checked": 0,
            "updated": 0,
        }
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    candidates = [p for p in papers if p.doi and not p.pdf_url]
    candidates.sort(key=lambda p: p.discovery_score.get("total", 0), reverse=True)
    client = HttpClient(config)
    adapter = get_adapter("unpaywall", client, config)
    checked = 0
    updated = 0
    errors = 0
    for paper in candidates[:limit]:
        try:
            data = adapter.enrich(paper)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            errors += 1
            continue
        checked += 1
        if not data:
            continue
        if data.get("pdf_url"):
            paper.pdf_url = data["pdf_url"]
        if data.get("oa_status"):
            paper.oa_status = data["oa_status"]
        if data.get("license"):
            paper.license = data["license"]
        if data.get("is_oa"):
            updated += 1
    write_jsonl(run_dir / "papers.jsonl", [p.to_dict() for p in papers])
    summary = {
        "status": "ok",
        "checked": checked,
        "updated": updated,
        "errors": errors,
        "limit": limit,
        "candidates_with_doi": len(candidates),
    }
    write_json(run_dir / "oa_enrich.json", summary)
    return summary


def run_pdf_fetch(
    run_dir: str | Path,
    *,
    limit: int = 20,
    out_dir: str | Path | None = None,
    config: Config | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    return fetch_pdfs(run_dir, limit=limit, out_dir=out_dir, config=config)


def run_doctor(config: Config | None = None) -> dict[str, Any]:
    config = config or load_config()
    pdf_renderers: list[str] = []
    try:
        import pypdfium2 as pdfium

        version = getattr(getattr(pdfium, "version", None), "PYPDFIUM_INFO", "")
        pdf_renderers.append(f"pypdfium2 {version}".strip())
    except Exception:  # noqa: BLE001
        pass
    try:
        import fitz  # PyMuPDF (optional fallback)

        version = getattr(fitz, "VersionBind", "") or getattr(fitz, "__version__", "")
        pdf_renderers.append(f"PyMuPDF {version}".strip())
    except Exception:  # noqa: BLE001
        pass
    return {
        "config": {
            "mailto": bool(config.mailto),
            "openalex_key": bool(config.openalex_api_key),
            "s2_key": bool(config.s2_api_key),
            "ncbi_key": bool(config.ncbi_api_key),
            "unpaywall_email": bool(config.unpaywall_email),
        },
        "keyless_default_sources": DEFAULT_SOURCES,
        "optional_keyed_sources": OPTIONAL_SOURCES,
        "experimental_sources": EXPERIMENTAL_SOURCES,
        "all_search_sources": ALL_SOURCES,
        "capabilities": SOURCE_CAPABILITIES,
        "source_health": load_health(config.cache_dir),
        "pdf_renderer": pdf_renderers[0] if pdf_renderers else "",
        "pdf_renderers": pdf_renderers,
        "notes": [
            "Default mode requires no registration.",
            "OpenAlex works keyless with a small daily budget; a free key helps heavy use.",
            "Semantic Scholar is skipped unless S2_API_KEY is set.",
            "Host-model reading: pypdfium2 is installed by default; PyMuPDF is an optional fallback (`pip install \"litsearch[pdf]\"`).",
            "DOAJ and DBLP are experimental: upstream may return 502 or a bot challenge.",
            "Unpaywall needs only an email (LITSEARCH_MAILTO or UNPAYWALL_EMAIL).",
        ],
    }


def run_report(run_dir: str | Path, *, lang: str = "both") -> dict[str, str]:
    paths = render_reports(run_dir, lang=lang)
    papers = [Paper.from_dict(x) for x in read_jsonl(Path(run_dir) / "papers.jsonl")]
    rows = read_screening(run_dir)
    export_all(run_dir, papers, rows)
    return paths


def run_verify(run_dir: str | Path, *, strict: bool = False) -> list[str]:
    return verify_run(run_dir, strict=strict)


def run_status(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    data = build_report_data(run_dir)
    return {
        "run_dir": str(run_dir),
        "counts": data["counts"],
        "source_runs": len(data.get("search_log", {}).get("source_runs", []) or []),
        "edges": len(data.get("edges", [])),
        "saturation": data.get("saturation", {}),
    }


def print_status(status: dict[str, Any]) -> str:
    lines = [f"Run: {status['run_dir']}"]
    for key, value in status["counts"].items():
        lines.append(f"  {key}: {value}")
    lines.append(f"  source_runs: {status['source_runs']}")
    lines.append(f"  citation_edges: {status['edges']}")
    sat = status.get("saturation") or {}
    if sat:
        lines.append(f"  saturation: {sat.get('stopping_reason', '')}")
    return "\n".join(lines)
