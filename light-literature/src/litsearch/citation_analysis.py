from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from .io import read_jsonl, write_json
from .models import Paper


def _paper_title(by_id: dict[str, Paper], pid: str) -> str:
    paper = by_id.get(pid)
    return paper.title if paper else ""


def analyze_citations(run_dir: str | Path) -> dict[str, Any]:
    """Co-citation and bridge analysis over existing citation edges.

    Backward edges: seed -> referenced paper. A reference cited by multiple seeds
    is a co-citation candidate.
    Forward edges: seed -> citing paper. A paper citing multiple seeds is a bridge.
    No new API calls; uses citation_edges.jsonl.
    """
    run_dir = Path(run_dir)
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    edges = read_jsonl(run_dir / "citation_edges.jsonl")
    by_id = {p.paper_id: p for p in papers}
    forward: dict[str, set[str]] = defaultdict(set)
    backward: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source = str(edge.get("source_paper_id", ""))
        target = str(edge.get("target_paper_id", ""))
        if not source or not target:
            continue
        if edge.get("direction") == "forward":
            forward[source].add(target)
        else:
            backward[source].add(target)

    def invert(graph: dict[str, set[str]]) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for source, targets in graph.items():
            for target in targets:
                out[target].add(source)
        return out

    co_cited = []
    for target, sources in invert(backward).items():
        if len(sources) >= 2:
            co_cited.append(
                {
                    "paper_id": target,
                    "title": _paper_title(by_id, target),
                    "seed_ids": sorted(sources),
                    "count": len(sources),
                }
            )
    bridges = []
    for target, sources in invert(forward).items():
        if len(sources) >= 2:
            bridges.append(
                {
                    "paper_id": target,
                    "title": _paper_title(by_id, target),
                    "seed_ids": sorted(sources),
                    "count": len(sources),
                }
            )
    co_cited.sort(key=lambda x: (-x["count"], x["paper_id"]))
    bridges.sort(key=lambda x: (-x["count"], x["paper_id"]))

    seeds = sorted(set(forward) | set(backward))
    pairs = []
    for a, b in combinations(seeds[:20], 2):
        common_cites = forward.get(a, set()) & forward.get(b, set())
        common_refs = backward.get(a, set()) & backward.get(b, set())
        if common_cites or common_refs:
            pairs.append(
                {
                    "seed_a": a,
                    "seed_b": b,
                    "common_citations": sorted(common_cites),
                    "common_references": sorted(common_refs),
                }
            )
    data = {
        "schema_version": "1.0",
        "seed_count": len(seeds),
        "edge_count": len(edges),
        "co_cited": co_cited[:50],
        "bridges": bridges[:50],
        "seed_pairs": pairs[:50],
    }
    write_json(run_dir / "citation_analysis.json", data)
    return data
