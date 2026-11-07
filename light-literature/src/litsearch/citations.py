from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import get_adapter
from .config import Config
from .dedupe import _strong_keys
from .io import read_json, read_jsonl, write_json, write_jsonl
from .models import CitationEdge, Paper
from .normalize import make_edge_id, make_paper_id, normalize_doi, now_iso
from .screening import prescreen, read_screening, write_screening
from .scoring import score_papers

CITATION_LIMIT = 20


def _seed_pool(
    papers: list[Paper],
    rows: list[dict[str, Any]],
    limit: int,
    seed_ids: list[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[Paper]:
    by_id = {p.paper_id: p for p in papers}
    if seed_ids:
        return [by_id[pid] for pid in seed_ids if pid in by_id][:limit]
    included = [by_id[r["paper_id"]] for r in rows if r.get("decision") == "include" and r["paper_id"] in by_id]
    maybe = [by_id[r["paper_id"]] for r in rows if r.get("decision") == "maybe" and r["paper_id"] in by_id]
    pool = included + maybe
    if not pool:
        pool = list(papers)
    exclude_ids = exclude_ids or set()
    # Prefer seeds not already used in an earlier round; fall back to used seeds
    # only if there are not enough new candidates.
    fresh = [p for p in pool if p.paper_id not in exclude_ids]
    used = [p for p in pool if p.paper_id in exclude_ids]
    pool = fresh + used

    def quality(p: Paper) -> tuple:
        row = next((r for r in rows if r.get("paper_id") == p.paper_id), {})
        return (
            1 if row.get("decision") == "include" else 0,
            1 if (p.pmid or p.pmcid) else 0,
            0 if p.is_preprint else 1,
            1 if p.cited_by_count >= 5 else 0,
            1 if p.doi else 0,
            p.discovery_score.get("total", 0),
        )

    # Keep fresh and used seeds in separate priority tiers. A plain sort over
    # fresh + used would let a high-quality used seed jump ahead again.
    pool = sorted(fresh, key=quality, reverse=True) + sorted(used, key=quality, reverse=True)
    seen = set()
    out = []
    for p in pool:
        if p.paper_id not in seen and (p.doi or p.pmid or p.pmcid or p.openalex_id or p.s2_id):
            seen.add(p.paper_id)
            out.append(p)
    return out[:limit]


def _merge_new(existing: list[Paper], new_papers: list[Paper]) -> tuple[list[Paper], dict[str, str]]:
    """Merge new records into existing by strong identifiers. Keep existing IDs stable."""
    by_key: dict[str, list[Paper]] = {}
    for paper in existing:
        for key in _strong_keys(paper):
            by_key.setdefault(key, []).append(paper)
    id_map: dict[str, str] = {}
    for new in new_papers:
        target = None
        keys = _strong_keys(new)
        # A shared work/preprint identifier does not erase a distinct report DOI.
        for key in keys:
            matches = [p for p in by_key.get(key, [])
                       if not (normalize_doi(p.doi) and normalize_doi(new.doi)
                               and normalize_doi(p.doi) != normalize_doi(new.doi))]
            if len(matches) == 1:
                target = matches[0]
                break
        if target is None:
            existing.append(new)
            for key in _strong_keys(new):
                by_key.setdefault(key, []).append(new)
            continue
        # Keep target.paper_id; enrich fields.
        target.abstract = max(target.abstract, new.abstract, key=len)
        target.authors = max(target.authors, new.authors, key=len)
        target.cited_by_count = max(target.cited_by_count, new.cited_by_count)
        target.is_retracted = target.is_retracted or new.is_retracted
        target.is_preprint = target.is_preprint and new.is_preprint
        target.pdf_url = target.pdf_url or new.pdf_url
        target.url = target.url or new.url
        target.venue = target.venue or new.venue
        target.year = target.year or new.year
        target.doi = target.doi or new.doi
        target.pmid = target.pmid or new.pmid
        target.pmcid = target.pmcid or new.pmcid
        target.arxiv_id = target.arxiv_id or new.arxiv_id
        target.openalex_id = target.openalex_id or new.openalex_id
        target.s2_id = target.s2_id or new.s2_id
        for key in _strong_keys(target):
            if not any(p is target for p in by_key.get(key, [])):
                by_key.setdefault(key, []).append(target)
        target.evidence_depth = max(
            [target.evidence_depth, new.evidence_depth],
            key=lambda d: {"metadata_only": 0, "abstract": 1, "full_text_link": 2}.get(d, 0),
        )
        seen = {(r.get("source"), r.get("source_id"), r.get("query_id")) for r in target.source_records}
        for rec in new.source_records:
            key = (rec.get("source"), rec.get("source_id"), rec.get("query_id"))
            if key not in seen:
                target.source_records.append(rec)
                seen.add(key)
        id_map[new.paper_id] = target.paper_id
    return existing, id_map


def expand_citations(
    run_dir: str | Path,
    plan: dict[str, Any],
    config: Config,
    *,
    round_no: int = 1,
    seed_count: int | None = None,
    sources: list[str] | None = None,
    directions: list[str] | None = None,
    seed_paper_ids: list[str] | None = None,
) -> dict[str, Any]:
    from .http import HttpClient
    from .screening import read_screening as _read

    run_dir = Path(run_dir)
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    rows = [r.to_dict() for r in _read(run_dir)]
    seed_count = seed_count or int((plan.get("budgets") or {}).get("max_citation_seeds", 10))
    sources = sources or ["europepmc", "opencitations"]
    directions = directions or ["forward", "backward"]
    seed_log_path = run_dir / "citation_seeds.json"
    used_seeds = set(read_json(seed_log_path, []) or [])
    seeds = _seed_pool(papers, rows, seed_count, seed_paper_ids, used_seeds)
    client = HttpClient(config)

    new_papers: list[Paper] = []
    edges: list[CitationEdge] = [
        CitationEdge.from_dict(x) for x in read_jsonl(run_dir / "citation_edges.jsonl")
    ]
    existing_edge_count = len(edges)
    log_path = run_dir / "search_log.json"
    search_log = read_json(log_path, {}) or {}
    source_runs = search_log.setdefault("source_runs", [])
    event_time = now_iso()

    for seed in seeds:
        for source in sources:
            try:
                adapter = get_adapter(source, client, config)
            except ValueError:
                continue
            for direction in directions:
                result = adapter.citations(seed, direction, CITATION_LIMIT)
                for p in result.papers:
                    p.source_records.append(
                        {
                            "source": source,
                            "source_id": "",
                            "query_id": f"cite:{seed.paper_id}:{direction}",
                            "leg_id": "citation",
                            "lens_id": "citation",
                            "round": round_no,
                            "rank": 0,
                            "retrieved_at": event_time,
                            "url": "",
                        }
                    )
                new_papers.extend(result.papers)
                edges.extend(result.edges)
                source_runs.append(
                    {
                        "source": source,
                        "query_id": f"cite:{seed.paper_id}:{direction}",
                        "status": result.status,
                        "fetched": len(result.papers),
                        "error": result.error,
                        "retrieved_at": event_time,
                    }
                )

    # Process every fetched identity so edges from all providers get an alias.
    previous_unique = len(papers)
    existing, id_map = _merge_new(papers, new_papers)
    added = len(existing) - previous_unique

    # Remap edge targets that were merged into existing papers. Only new edges
    # belong to this round; existing edges keep their original round.
    for edge in edges[existing_edge_count:]:
        edge.source_paper_id = id_map.get(edge.source_paper_id, edge.source_paper_id)
        edge.target_paper_id = id_map.get(edge.target_paper_id, edge.target_paper_id)
        edge.edge_id = make_edge_id(edge.source_paper_id, edge.target_paper_id, edge.direction, edge.provider)
        edge.round = round_no

    # Deduplicate edges.
    edge_seen = set()
    unique_edges = []
    for edge in edges:
        if edge.edge_id in edge_seen:
            continue
        edge_seen.add(edge.edge_id)
        unique_edges.append(edge)

    existing = score_papers(existing, plan)
    new_rows = prescreen(existing, plan, read_screening(run_dir))
    write_jsonl(run_dir / "papers.jsonl", [p.to_dict() for p in existing])
    write_jsonl(run_dir / "citation_edges.jsonl", [e.to_dict() for e in unique_edges])
    write_screening(run_dir, new_rows)

    search_log["source_runs"] = source_runs
    totals = search_log.setdefault("totals", {})
    previous_identified = int(totals.get("identified") or 0)
    totals["identified"] = previous_identified + len(new_papers)
    totals["unique"] = len(existing)
    totals["duplicates_removed"] = max(0, totals["identified"] - len(existing))
    totals["citation_added"] = added
    search_log.setdefault("prisma_s", {})["citation_searching"] = "performed"
    search_log.setdefault("events", []).append(
        {
            "type": "citation_expansion",
            "timestamp": event_time,
            "detail": {
                "round": round_no,
                "seeds": len(seeds),
                "new_papers": added,
                "records_fetched": len(new_papers),
                "edges": len(unique_edges),
            },
        }
    )
    write_json(seed_log_path, sorted(used_seeds | {p.paper_id for p in seeds}))
    write_json(log_path, search_log)
    from .prisma import build_prisma_s_audit

    build_prisma_s_audit(run_dir)

    return {
        "seeds": len(seeds),
        "new_papers": added,
        "records_fetched": len(new_papers),
        "edges": len(unique_edges),
        "merged_into_existing": len(id_map),
    }
