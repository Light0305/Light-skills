from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Any

from .models import Paper
from .normalize import (
    make_paper_id,
    normalize_arxiv,
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    normalize_person,
    title_key,
)


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _author_keys(paper: Paper) -> set[str]:
    out = set()
    for author in paper.authors:
        parts = normalize_person(author).split()
        # A surname/initial alone cannot establish bibliographic identity.
        if len(parts) >= 2 or any("一" <= ch <= "鿿" for ch in "".join(parts)):
            out.add(" ".join(sorted(parts)))
    return out


def _author_overlap(a: Paper, b: Paper) -> float:
    sa, sb = _author_keys(a), _author_keys(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa), len(sb))


def _strong_keys(paper: Paper) -> list[str]:
    keys = []
    if paper.doi:
        keys.append("doi:" + normalize_doi(paper.doi))
    if paper.pmid:
        keys.append("pmid:" + normalize_pmid(paper.pmid))
    if paper.pmcid:
        keys.append("pmcid:" + normalize_pmcid(paper.pmcid))
    if paper.arxiv_id:
        keys.append("arxiv:" + normalize_arxiv(paper.arxiv_id))
    if paper.openalex_id:
        keys.append("openalex:" + paper.openalex_id)
    if paper.s2_id:
        keys.append("s2:" + paper.s2_id)
    return keys


def _merge_field(target: Paper, source: Paper, field: str) -> None:
    current = getattr(target, field)
    incoming = getattr(source, field)
    if not current and incoming:
        setattr(target, field, incoming)


def _merge_group(group: list[Paper], cluster_id: str) -> tuple[Paper, dict[str, Any]]:
    def preference(p: Paper) -> tuple:
        return (
            1 if not p.is_preprint else 0,
            1 if p.doi else 0,
            1 if p.abstract else 0,
            len(p.authors),
            p.cited_by_count,
        )

    ordered = sorted(group, key=preference, reverse=True)
    base = ordered[0]
    merged = Paper.from_dict(base.to_dict())
    merged.abstract = max((p.abstract for p in ordered), key=len, default="")
    merged.authors = max((p.authors for p in ordered), key=len, default=[])
    merged.cited_by_count = max((p.cited_by_count for p in ordered), default=0)
    merged.is_retracted = any(p.is_retracted for p in ordered)
    merged.is_preprint = all(p.is_preprint for p in ordered)
    merged.evidence_depth = _best_depth([p.evidence_depth for p in ordered])
    merged.referenced_works = sorted({x for p in ordered for x in p.referenced_works})
    merged.related_works = sorted({x for p in ordered for x in p.related_works})
    merged.concepts = sorted({x for p in ordered for x in p.concepts if x})

    for p in ordered[1:]:
        for field in (
            "title",
            "year",
            "venue",
            "type",
            "doi",
            "arxiv_id",
            "pmid",
            "pmcid",
            "openalex_id",
            "s2_id",
            "url",
            "pdf_url",
            "language",
        ):
            _merge_field(merged, p, field)

    records = []
    seen = set()
    for p in ordered:
        for rec in p.source_records:
            key = (rec.get("source"), rec.get("source_id"), rec.get("query_id"))
            if key not in seen:
                seen.add(key)
                records.append(rec)
    merged.source_records = records

    versions = []
    version_seen = set()
    for p in ordered:
        for version in p.versions:
            signature = (version.get("paper_id"), version.get("doi"), version.get("arxiv_id"))
            if signature not in version_seen:
                version_seen.add(signature)
                versions.append(version)
    for p in ordered:
        if p.paper_id != base.paper_id:
            versions.append(
                {
                    "paper_id": p.paper_id,
                    "doi": p.doi,
                    "arxiv_id": p.arxiv_id,
                    "pmid": p.pmid,
                    "venue": p.venue,
                    "year": p.year,
                    "source_records": p.source_records,
                }
            )
    merged.versions = versions

    new_id = make_paper_id(
        doi=merged.doi,
        pmid=merged.pmid,
        pmcid=merged.pmcid,
        arxiv_id=merged.arxiv_id,
        openalex_id=merged.openalex_id,
        s2_id=merged.s2_id,
        title=merged.title,
        year=merged.year,
    )
    merged.paper_id = new_id
    # Ensure edge targets from members still resolve through versions.
    reasons = []
    dois = {normalize_doi(p.doi) for p in ordered if p.doi}
    if len(dois) == 1:
        reasons.append("same DOI")
    if any(p.is_preprint for p in ordered) and any(not p.is_preprint for p in ordered):
        reasons.append("preprint/published version")
    if len(ordered) > 1:
        reasons.append("title/identifier cluster")
    possible_duplicate = len(dois) > 1 and not (
        any(p.is_preprint for p in ordered) and any(not p.is_preprint for p in ordered)
    )
    log = {
        "cluster_id": cluster_id,
        "retained_paper_id": new_id,
        "member_paper_ids": [p.paper_id for p in ordered],
        "member_titles": [p.title for p in ordered],
        "merge_reasons": reasons,
        "possible_duplicate": possible_duplicate,
    }
    return merged, log


def _best_depth(depths: list[str]) -> str:
    order = {"metadata_only": 0, "abstract": 1, "full_text_link": 2}
    return max(depths or ["metadata_only"], key=lambda d: order.get(d, 0))


def dedupe_papers(papers: list[Paper]) -> tuple[list[Paper], dict[str, Any]]:
    if not papers:
        return [], {"clusters": [], "duplicates_removed": 0, "possible_duplicates": [],
                    "possible_duplicates_omitted": 0}
    uf = UnionFind(len(papers))
    key_map: dict[str, list[int]] = defaultdict(list)
    doi_sets = [{normalize_doi(p.doi)} if normalize_doi(p.doi) else set() for p in papers]
    possible: list[dict[str, Any]] = []
    possible_count = 0

    def candidate(a: int, b: int, reason: str) -> None:
        nonlocal possible_count
        possible_count += 1
        if len(possible) < 200:
            possible.append({"paper_ids": [papers[a].paper_id, papers[b].paper_id],
                             "_indexes": [a, b],
                             "reason": reason, "action": "retain separately; inspect source identity"})

    def unite(a: int, b: int, reason: str) -> bool:
        ra, rb = uf.find(a), uf.find(b)
        if ra == rb:
            return True
        if doi_sets[ra] and doi_sets[rb] and doi_sets[ra] != doi_sets[rb]:
            candidate(a, b, "Conflicting DOIs despite " + reason)
            return False
        identifiers = doi_sets[ra] | doi_sets[rb]
        uf.union(a, b)
        doi_sets[uf.find(a)] = identifiers
        return True

    for i, paper in enumerate(papers):
        for key in _strong_keys(paper):
            for prior in key_map[key]:
                unite(i, prior, key)
            key_map[key].append(i)

    # Weak matches need full author evidence, an exact year and a useful title.
    by_title: dict[str, list[int]] = defaultdict(list)
    for i, paper in enumerate(papers):
        tk = title_key(paper.title)
        if tk:
            by_title[tk].append(i)
    for indexes in by_title.values():
        title_dois = {normalize_doi(papers[i].doi) for i in indexes if normalize_doi(papers[i].doi)}
        for a_pos in range(len(indexes)):
            for b_pos in range(a_pos + 1, len(indexes)):
                a, b = papers[indexes[a_pos]], papers[indexes[b_pos]]
                ai, bi = indexes[a_pos], indexes[b_pos]
                if uf.find(ai) == uf.find(bi):
                    continue
                if len(title_dois) > 1:
                    candidate(ai, bi, "Same title has multiple DOI identities; versions need separate evidence")
                    continue
                overlap = _author_overlap(a, b)
                title = title_key(a.title)
                informative_title = len(title.split()) >= 3 or sum("一" <= ch <= "鿿" for ch in title) >= 6
                if not (a.year and b.year and a.year == b.year and overlap >= 0.5 and informative_title):
                    candidate(ai, bi, "Title alone lacks matching full authors, year or a distinctive title")
                    continue
                unite(ai, bi, "matching title, year and full author names")

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(papers)):
        groups[uf.find(i)].append(i)

    merged_papers: list[Paper] = []
    clusters: list[dict[str, Any]] = []
    by_root: dict[int, Paper] = {}
    cluster_outputs = []
    for cluster_idx, indexes in enumerate(groups.values()):
        group = [papers[i] for i in indexes]
        if len(group) == 1:
            copied = Paper.from_dict(group[0].to_dict())
            merged_papers.append(copied)
            by_root[uf.find(indexes[0])] = copied
            continue
        merged, log = _merge_group(group, f"c{cluster_idx + 1}")
        merged_papers.append(merged)
        clusters.append(log)
        by_root[uf.find(indexes[0])] = merged
        cluster_outputs.append((log, merged))

    # Sparse providers derive IDs from title/year. Keeping uncertain records
    # separate must not leave duplicate IDs that corrupt screening and edges.
    by_id: dict[str, list[Paper]] = defaultdict(list)
    for paper in merged_papers:
        by_id[paper.paper_id].append(paper)
    collisions = []
    for original_id, records in by_id.items():
        if len(records) < 2:
            continue
        seen: dict[str, int] = defaultdict(int)
        for paper in records:
            content = {field: getattr(paper, field) for field in (
                "title", "authors", "year", "venue", "doi", "pmid", "pmcid", "arxiv_id",
                "openalex_id", "s2_id", "url", "abstract")}
            fingerprint = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]
            seen[fingerprint] += 1
            paper.paper_id = f"{original_id}_r{fingerprint}_{seen[fingerprint]}"
        collisions.append({"original_paper_id": original_id,
                           "assigned_paper_ids": sorted(p.paper_id for p in records),
                           "reason": "Unconfirmed distinct records shared a sparse title/year-derived identity"})
    for log, paper in cluster_outputs:
        log["retained_paper_id"] = paper.paper_id
    # Resolve candidate locators after any sparse-ID disambiguation.
    for item in possible:
        indexes = item.pop("_indexes")
        item["paper_ids"] = [by_root[uf.find(i)].paper_id for i in indexes]

    # Recompute IDs and sort for determinism.
    merged_papers.sort(key=lambda p: (p.year or 0, p.title.lower()), reverse=True)
    return merged_papers, {
        "clusters": clusters,
        "duplicates_removed": len(papers) - len(merged_papers),
        "possible_duplicates": possible,
        "possible_duplicates_omitted": possible_count - len(possible),
        "id_collisions": collisions,
    }
