from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from .models import Paper
from .normalize import tokenize
from .query import plan_terms

HALF_LIFE = {"cs": 4, "biomed": 6, "social": 8, "general": 8}


def _contains(text: str, term: str) -> bool:
    text = text.lower()
    term = term.lower()
    if not term:
        return False
    if term in text:
        return True
    tokens = tokenize(text)
    term_tokens = tokenize(term)
    return bool(term_tokens) and term_tokens.issubset(tokens)


def _relevance(paper: Paper, terms: list[str]) -> float:
    if not terms:
        return 0.0
    title = paper.title or ""
    abstract = paper.abstract or ""
    concepts = " ".join(paper.concepts)
    hits = 0.0
    total = 0.0
    for term in terms:
        total += 3.0
        if _contains(title, term):
            hits += 3.0
        elif _contains(concepts, term):
            hits += 1.5
        elif _contains(abstract, term):
            hits += 1.0
    return min(1.0, hits / total) if total else 0.0


def _bm25_scores(papers: list[Paper], terms: list[str]) -> list[float]:
    """Lightweight BM25 over title/abstract/concepts. No embeddings, no keys."""
    if not papers or not terms:
        return [0.0] * len(papers)
    query_tokens = tokenize(" ".join(terms))
    if not query_tokens:
        return [0.0] * len(papers)
    docs: list[set[str]] = []
    for paper in papers:
        docs.append(tokenize(f"{paper.title} {paper.abstract} {' '.join(paper.concepts)}"))
    n_docs = len(docs)
    avg_len = sum(len(d) for d in docs) / max(1, n_docs)
    df: dict[str, int] = {}
    for doc in docs:
        for token in doc:
            df[token] = df.get(token, 0) + 1
    idf = {
        token: math.log(1 + (n_docs - df.get(token, 0) + 0.5) / (df.get(token, 0) + 0.5))
        for token in query_tokens
    }
    k1, b = 1.5, 0.75
    scores: list[float] = []
    for doc in docs:
        dl = len(doc)
        score = 0.0
        for token in query_tokens:
            if token not in doc:
                continue
            tf = 1.0
            score += idf.get(token, 0.0) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(1.0, avg_len)))
        scores.append(score)
    max_score = max(scores) if scores else 0.0
    return [s / max_score if max_score > 0 else 0.0 for s in scores]


def _recency(paper: Paper, domain: str, current_year: int) -> float:
    if not paper.year:
        return 0.5
    age = max(0, current_year - paper.year)
    half_life = HALF_LIFE.get(domain, 8)
    value = math.exp(-math.log(2) * age / half_life)
    return max(0.2, min(1.0, value))


def _citation_impact(paper: Paper, current_year: int) -> float:
    age = max(1, current_year - (paper.year or current_year) + 1)
    cites_per_year = paper.cited_by_count / age
    return min(1.0, math.log1p(cites_per_year) / math.log1p(20))


def _source_agreement(paper: Paper, health: dict[str, float] | None) -> float:
    sources = {r.get("source") for r in paper.source_records if r.get("source")}
    ranks = [int(r.get("rank", 100)) for r in paper.source_records if str(r.get("rank", "")).isdigit()]
    best_rank = min(ranks) if ranks else 100
    if health:
        weighted = sum(max(0.0, min(1.0, health.get(s, 0.5))) for s in sources)
    else:
        weighted = 0.5 * len(sources)
    coverage = min(1.0, weighted / 2.0)
    rank_score = 1 - math.log1p(best_rank) / math.log1p(100)
    return 0.7 * coverage + 0.3 * rank_score


def _evidence(paper: Paper) -> float:
    return {"full_text_link": 1.0, "abstract": 0.6, "metadata_only": 0.2}.get(paper.evidence_depth, 0.2)


def _metadata(paper: Paper) -> float:
    checks = [
        bool(paper.doi or paper.pmid or paper.arxiv_id or paper.openalex_id or paper.s2_id),
        bool(paper.authors),
        bool(paper.venue),
        bool(paper.year),
        bool(paper.type),
        bool(paper.abstract),
        bool(paper.url),
    ]
    return sum(checks) / len(checks)


def _stratum(paper: Paper, current_year: int, p75: float) -> str:
    age = current_year - (paper.year or current_year)
    cpy = paper.cited_by_count / max(1, age + 1)
    if age <= 2:
        return "recent"
    if age <= 5 and paper.cited_by_count <= 2:
        return "emerging"
    if cpy >= p75 and age >= 3:
        return "high_impact"
    return "established"


def score_paper(
    paper: Paper,
    terms: list[str],
    domain: str,
    current_year: int,
    *,
    bm25: float = 0.0,
    source_health: dict[str, float] | None = None,
    p75: float = 0.0,
) -> dict[str, Any]:
    lexical = _relevance(paper, terms)
    relevance = 0.6 * lexical + 0.4 * max(0.0, min(1.0, bm25))
    recency = _recency(paper, domain, current_year)
    impact = _citation_impact(paper, current_year)
    agreement = _source_agreement(paper, source_health)
    evidence = _evidence(paper)
    metadata = _metadata(paper)

    components = {
        "relevance": round(35 * relevance, 2),
        "recency": round(20 * recency, 2),
        "citation_impact": round(15 * impact, 2),
        "source_agreement": round(10 * agreement, 2),
        "evidence_depth": round(10 * evidence, 2),
        "metadata_completeness": round(10 * metadata, 2),
    }
    penalties: list[str] = []
    penalty = 0.0
    if paper.is_retracted:
        penalty += 50
        penalties.append("retracted:-50")
    if paper.is_preprint:
        penalty += 2
        penalties.append("preprint:-2")
    if not paper.abstract:
        penalty += 5
        penalties.append("no_abstract:-5")

    bonus = 0.0
    age = current_year - (paper.year or current_year)
    if 0 <= age <= 2 and relevance >= 0.5:
        bonus += 5
        penalties.append("frontier_bonus:+5")

    total = max(0.0, min(100.0, sum(components.values()) - penalty + bonus))
    return {
        "total": round(total, 2),
        "components": components,
        "penalties": penalties,
        "stratum": _stratum(paper, current_year, p75),
        "explanation": (
            f"lexical={lexical:.2f}; bm25={bm25:.2f}; recency={recency:.2f}; "
            f"impact={impact:.2f}; agreement={agreement:.2f}"
        ),
    }


def score_papers(
    papers: list[Paper],
    plan: dict[str, Any],
    current_year: int | None = None,
    source_health: dict[str, float] | None = None,
) -> list[Paper]:
    current_year = current_year or datetime.now().year
    terms = plan_terms(plan)
    domain = str(plan.get("domain", "general"))
    bm25 = _bm25_scores(papers, terms)
    cpy_values = []
    for paper in papers:
        age = max(1, current_year - (paper.year or current_year) + 1)
        cpy_values.append(paper.cited_by_count / age)
    if cpy_values:
        ordered = sorted(cpy_values)
        p75 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.75))]
    else:
        p75 = 0.0
    for paper, bm25_score in zip(papers, bm25):
        paper.discovery_score = score_paper(
            paper,
            terms,
            domain,
            current_year,
            bm25=bm25_score,
            source_health=source_health,
            p75=p75,
        )
    return papers


def select_stratified(papers: list[Paper], n: int) -> list[Paper]:
    """Round-robin strata so a high-citation list does not bury recent work."""
    groups: dict[str, list[Paper]] = {}
    for paper in sorted(papers, key=lambda p: p.discovery_score.get("total", 0), reverse=True):
        stratum = paper.discovery_score.get("stratum", "established")
        groups.setdefault(stratum, []).append(paper)
    order = ["high_impact", "recent", "emerging", "established"]
    selected: list[Paper] = []
    used: set[str] = set()
    while len(selected) < n and any(groups.get(k) for k in order):
        for key in order:
            if groups.get(key):
                paper = groups[key].pop(0)
                if paper.paper_id not in used:
                    used.add(paper.paper_id)
                    selected.append(paper)
                    if len(selected) >= n:
                        break
    for paper in sorted(papers, key=lambda p: p.discovery_score.get("total", 0), reverse=True):
        if len(selected) >= n:
            break
        if paper.paper_id not in used:
            selected.append(paper)
            used.add(paper.paper_id)
    return selected


def select_diverse(papers: list[Paper], n: int) -> list[Paper]:
    """MMR-like selection with author/venue caps."""
    candidates = sorted(papers, key=lambda p: p.discovery_score.get("total", 0), reverse=True)
    selected: list[Paper] = []
    author_counts: dict[str, int] = {}
    venue_counts: dict[str, int] = {}
    for paper in candidates:
        if len(selected) >= n:
            break
        first_author = paper.authors[0].split()[-1].lower() if paper.authors else ""
        venue = paper.venue.lower()
        if first_author and author_counts.get(first_author, 0) >= 2:
            continue
        if venue and venue_counts.get(venue, 0) >= 3:
            continue
        if selected:
            max_overlap = 0.0
            tokens = tokenize(paper.title)
            for chosen in selected:
                other = tokenize(chosen.title)
                if tokens and other:
                    overlap = len(tokens & other) / len(tokens | other)
                    max_overlap = max(max_overlap, overlap)
            if max_overlap > 0.9:
                continue
        selected.append(paper)
        if first_author:
            author_counts[first_author] = author_counts.get(first_author, 0) + 1
        if venue:
            venue_counts[venue] = venue_counts.get(venue, 0) + 1
    return selected
