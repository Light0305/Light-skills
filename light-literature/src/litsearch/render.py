from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .i18n import LABELS
from .io import read_json, read_jsonl
from .models import Paper, ScreeningRow
from .screening import read_screening, validate_screening
from .scoring import select_stratified

TOKEN_RE = re.compile(r"\[\[(p_[0-9a-f]{12})\]\]")


def _loc(value: Any, lang: str) -> str:
    if isinstance(value, dict):
        text = value.get(lang)
        if text:
            return str(text)
        fallback = value.get("en") or value.get("zh") or ""
        if lang == "zh" and fallback:
            return str(fallback) + " [zh missing]"
        return str(fallback)
    return str(value or "")


def _resolve(text: Any, by_id: dict[str, Paper], order: list[str], lang: str = "en") -> str:
    text = _loc(text, lang)
    if not text:
        return ""

    def repl(match: re.Match[str]) -> str:
        pid = match.group(1)
        if pid not in by_id:
            raise ValueError(f"synthesis references unknown paper_id: {pid}")
        if pid not in order:
            order.append(pid)
        return f"[{order.index(pid) + 1}]"

    return TOKEN_RE.sub(repl, text)


def _ref_numbers(ids: list[str], by_id: dict[str, Paper], order: list[str]) -> str:
    refs = []
    for pid in ids or []:
        if pid not in by_id:
            raise ValueError(f"synthesis references unknown paper_id: {pid}")
        if pid not in order:
            order.append(pid)
        refs.append(f"[{order.index(pid) + 1}]")
    return " ".join(refs)


def _fmt_authors(paper: Paper, limit: int = 3) -> str:
    if not paper.authors:
        return "Unknown"
    names = paper.authors[:limit]
    text = ", ".join(names)
    if len(paper.authors) > limit:
        text += " et al."
    return text


def _fmt_paper_link(paper: Paper) -> str:
    title = (paper.title or "").replace("|", "\\|")
    if paper.doi:
        return f"[{title}](https://doi.org/{paper.doi})"
    if paper.arxiv_id:
        return f"[{title}](https://arxiv.org/abs/{paper.arxiv_id})"
    if paper.pmid:
        return f"[{title}](https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/)"
    if paper.url:
        return f"[{title}]({paper.url})"
    return title


def _paper_ref(paper: Paper) -> str:
    authors = _fmt_authors(paper, 6)
    venue = f" {paper.venue}." if paper.venue else ""
    year = f" {paper.year}." if paper.year else ""
    ids = []
    if paper.doi:
        ids.append(f"doi:{paper.doi}")
    if paper.arxiv_id:
        ids.append(f"arXiv:{paper.arxiv_id}")
    if paper.pmid:
        ids.append(f"PMID:{paper.pmid}")
    suffix = f" {'; '.join(ids)}." if ids else ""
    return f"{authors}. {paper.title}.{venue}{year}{suffix}".strip()


def _default_reading_path(papers: list[Paper], rows_by_id: dict[str, dict[str, Any]], current_year: int) -> list[dict[str, Any]]:
    tiers = {
        "foundation": [],
        "core": [],
        "method": [],
        "frontier": [],
        "contrarian": [],
        "adjacent": [],
    }
    used: set[str] = set()

    def add(tier: str, paper: Paper) -> None:
        if paper.paper_id in used:
            return
        used.add(paper.paper_id)
        tiers[tier].append(paper.paper_id)

    for paper in sorted(papers, key=lambda p: p.discovery_score.get("total", 0), reverse=True):
        row = rows_by_id.get(paper.paper_id, {})
        text = f"{paper.title} {paper.abstract}".lower()
        if paper.year and current_year - paper.year >= 5 and paper.cited_by_count >= 50:
            add("foundation", paper)
        elif row.get("decision") == "include":
            add("core", paper)
        elif any(k in text for k in ("method", "benchmark", "evaluation", "dataset")):
            add("method", paper)
        elif paper.year and current_year - paper.year <= 2:
            add("frontier", paper)
        elif any(k in text for k in ("critique", "limitation", "failure", "negative", "retract")):
            add("contrarian", paper)
        elif row.get("decision") == "maybe":
            add("adjacent", paper)
        else:
            add("adjacent", paper)
    return [
        {"tier": tier, "paper_ids": ids, "rationale": {"en": "", "zh": ""}}
        for tier, ids in tiers.items()
        if ids
    ]


def build_report_data(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    plan = read_json(run_dir / "query_plan.json", {}) or {}
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    rows = read_screening(run_dir)
    edges = read_jsonl(run_dir / "citation_edges.jsonl")
    saturation = read_json(run_dir / "saturation.json", {}) or {}
    search_log = read_json(run_dir / "search_log.json", {}) or {}
    merge_log = read_json(run_dir / "merge_log.json", {}) or {}
    synthesis = read_json(run_dir / "synthesis.json", None)
    compiled = read_json(run_dir / "compiled_queries.json", {}) or {}
    prisma_audit = read_json(run_dir / "prisma_s_audit.json", {}) or {}
    citation_analysis = read_json(run_dir / "citation_analysis.json", {}) or {}

    by_id = {p.paper_id: p for p in papers}
    rows_by_id = {r.paper_id: r.to_dict() for r in rows}
    paper_ids = set(by_id)
    if synthesis:
        errors = validate_synthesis(synthesis, paper_ids)
        if errors:
            raise ValueError("Invalid synthesis.json:\n" + "\n".join(f"- {e}" for e in errors))

    included = [r for r in rows if r.decision == "include"]
    maybe = [r for r in rows if r.decision == "maybe"]
    excluded = [r for r in rows if r.decision == "exclude"]
    source_runs = search_log.get("source_runs", []) or []
    identified = int((search_log.get("totals") or {}).get("identified") or sum(int(r.get("fetched", 0) or 0) for r in source_runs))
    unique = len(papers)
    duplicates = int(merge_log.get("duplicates_removed") or max(0, identified - unique))
    citation_targets = {e.get("target_paper_id") for e in edges}
    citation_added = len({x for x in citation_targets if x in paper_ids})

    counts = {
        "identified": identified,
        "unique": unique,
        "duplicates_removed": duplicates,
        "screened": len(rows),
        "included": len(included),
        "excluded": len(excluded),
        "maybe": len(maybe),
        "citation_added": citation_added,
    }

    pool = [by_id[r.paper_id] for r in included + maybe if r.paper_id in by_id]
    if not pool:
        pool = list(papers)
    pool.sort(key=lambda p: p.discovery_score.get("total", 0), reverse=True)
    top = select_stratified(pool, 20)

    current_year = datetime.now().year
    if synthesis and synthesis.get("reading_path"):
        reading_path = synthesis["reading_path"]
    else:
        reading_path = _default_reading_path(papers, rows_by_id, current_year)

    ref_order: list[str] = []
    summary_en = _resolve((synthesis or {}).get("summary"), by_id, ref_order, "en")
    summary_zh = _resolve((synthesis or {}).get("summary"), by_id, ref_order, "zh")
    if not summary_en and not summary_zh:
        summary_en = LABELS["en"]["no_summary"]
        summary_zh = LABELS["zh"]["no_summary"]

    question_answers = []
    for item in (synthesis or {}).get("question_answers", []) or []:
        question_answers.append(
            {
                "question_id": item.get("question_id", ""),
                "en": _resolve(item.get("answer"), by_id, ref_order, "en"),
                "zh": _resolve(item.get("answer"), by_id, ref_order, "zh"),
                "paper_ids": item.get("paper_ids", []),
            }
        )

    gaps = []
    for gap in (synthesis or {}).get("gaps", []) or []:
        evidence_ids = gap.get("evidence_paper_ids", []) or []
        gaps.append(
            {
                "gap_id": gap.get("gap_id", ""),
                "type": gap.get("type", ""),
                "en": _resolve(gap.get("statement"), by_id, ref_order, "en"),
                "zh": _resolve(gap.get("statement"), by_id, ref_order, "zh"),
                "evidence_paper_ids": evidence_ids,
                "evidence_refs": _ref_numbers(evidence_ids, by_id, ref_order),
                "confidence": gap.get("confidence", "low"),
                "evidence_types": gap.get("evidence_types", []),
            }
        )

    idea_cards = []
    for idea in (synthesis or {}).get("idea_cards", []) or []:
        prior_art = idea.get("closest_prior_art", []) or []
        idea_cards.append(
            {
                "idea_id": idea.get("idea_id", ""),
                "title_en": _loc(idea.get("title"), "en"),
                "title_zh": _loc(idea.get("title"), "zh"),
                "prior_art": prior_art,
                "prior_art_refs": _ref_numbers(prior_art, by_id, ref_order),
                "delta_en": _resolve(idea.get("delta"), by_id, ref_order, "en"),
                "delta_zh": _resolve(idea.get("delta"), by_id, ref_order, "zh"),
                "feasibility_en": _resolve(idea.get("feasibility"), by_id, ref_order, "en"),
                "feasibility_zh": _resolve(idea.get("feasibility"), by_id, ref_order, "zh"),
                "experiment_en": _resolve(idea.get("discriminating_experiment"), by_id, ref_order, "en"),
                "experiment_zh": _resolve(idea.get("discriminating_experiment"), by_id, ref_order, "zh"),
            }
        )

    limitations = (synthesis or {}).get("limitations")
    if not limitations:
        limitations = {
            "en": "This is a PRISMA-informed title/abstract search, not a PRISMA-compliant systematic review. Only one citation round is complete. Coverage is bounded by the listed sources, dates, and languages.",
            "zh": "这是 PRISMA-informed 的标题/摘要检索，不是 PRISMA-compliant 系统综述；只完成一轮引用扩展。覆盖范围受所列数据源、时间和语言限制。",
        }

    references = [by_id[pid] for pid in ref_order if pid in by_id]
    for paper in top:
        if paper.paper_id not in ref_order:
            ref_order.append(paper.paper_id)
            references.append(paper)
    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "plan": plan,
        "papers": papers,
        "rows": [r.to_dict() for r in rows],
        "rows_by_id": rows_by_id,
        "edges": edges,
        "saturation": saturation,
        "search_log": search_log,
        "merge_log": merge_log,
        "compiled": compiled,
        "prisma_audit": prisma_audit,
        "citation_analysis": citation_analysis,
        "synthesis": synthesis,
        "counts": counts,
        "top": top,
        "source_health": search_log.get("source_health", {}) or {},
        "strata": dict(Counter(p.discovery_score.get("stratum", "established") for p in papers)),
        "reading_path": reading_path,
        "question_answers": question_answers,
        "summary_en": summary_en,
        "summary_zh": summary_zh,
        "gaps": gaps,
        "idea_cards": idea_cards,
        "limitations": limitations,
        "references": references,
        "ref_order": ref_order,
    }


def validate_synthesis(synthesis: dict[str, Any], paper_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(synthesis, dict):
        return ["synthesis must be a JSON object"]
    if synthesis.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    summary = synthesis.get("summary") or {}
    if not (isinstance(summary, dict) and (summary.get("en") or summary.get("zh"))):
        errors.append("summary.en or summary.zh is required")

    def check_ids(ids: Any, where: str) -> None:
        for pid in ids or []:
            if pid not in paper_ids:
                errors.append(f"{where}: unknown paper_id {pid}")

    for i, item in enumerate(synthesis.get("question_answers", []) or []):
        check_ids(item.get("paper_ids"), f"question_answers[{i}]")
    for i, tier in enumerate(synthesis.get("reading_path", []) or []):
        check_ids(tier.get("paper_ids"), f"reading_path[{i}]")
    for i, gap in enumerate(synthesis.get("gaps", []) or []):
        check_ids(gap.get("evidence_paper_ids"), f"gaps[{i}]")
    for i, idea in enumerate(synthesis.get("idea_cards", []) or []):
        check_ids(idea.get("closest_prior_art"), f"idea_cards[{i}]")
    return errors


def _render_protocol(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    lines = [f"## {L['protocol']}", ""]
    plan = data["plan"]
    filters = plan.get("filters", {})
    policy = plan.get("source_policy", {})
    actual_sources = data.get("compiled", {}).get("sources") or policy.get("enabled", [])
    lines.append(f"- {L['sources']}: {', '.join(actual_sources) or 'n/a'}")
    lines.append(
        f"- {L['filters']}: year {filters.get('year_from', '?')}–{filters.get('year_to', '?')}; "
        f"languages {', '.join(filters.get('languages', [])) or 'n/a'}; "
        f"preprints {'allowed' if filters.get('include_preprints', True) else 'excluded'}"
    )
    queries = data.get("compiled", {}).get("queries", []) or []
    if queries:
        lines.append(f"- {L['queries']}: {len(queries)} compiled")
        lines.append("")
        lines.append("| # | Source | Lens | Sort | Query |")
        lines.append("|---:|---|---|---|---|")
        for i, q in enumerate(queries[:20], 1):
            query = str(q.get("query", "")).replace("|", "\\|")
            lines.append(f"| {i} | {q.get('source')} | {q.get('lens_id')} | {q.get('sort')} | `{query}` |")
        if len(queries) > 20:
            lines.append(f"| … | | | | {len(queries) - 20} more in compiled_queries.json |")
    lines.append("")
    return lines


def _render_prisma(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    c = data["counts"]
    lines = [f"## {L['prisma']}", "", "| Stage | Count |", "|---|---:|"]
    for key in ("identified", "duplicates_removed", "unique", "screened", "excluded", "included", "maybe", "citation_added"):
        label = {
            "identified": L["identified"],
            "duplicates_removed": L["duplicates"],
            "unique": "Unique records" if L is LABELS["en"] else "唯一记录",
            "screened": L["screened"],
            "excluded": L["excluded"],
            "included": L["included"],
            "maybe": L["maybe"],
            "citation_added": L["citation_added"],
        }[key]
        lines.append(f"| {label} | {c.get(key, 0)} |")
    lines.append("")
    return lines


def _render_evidence(data: dict[str, Any], L: dict[str, str], lang: str) -> list[str]:
    lines = [f"## {L['evidence']}", ""]
    if not data["top"]:
        lines.append("No candidates." if lang == "en" else "没有候选文献。")
        lines.append("")
        return lines
    lines.append(f"| # | {L['paper']} | {L['year']} | {L['venue']} | {L['score']} | {L['evidence_depth']} | {L['decision']} | ID |")
    lines.append("|---:|---|---:|---|---:|---|---|---|")
    for i, paper in enumerate(data["top"], 1):
        row = data["rows_by_id"].get(paper.paper_id, {})
        title = _fmt_paper_link(paper)
        venue = (paper.venue or "").replace("|", "\\|")
        doi = f"doi:{paper.doi}" if paper.doi else (f"arXiv:{paper.arxiv_id}" if paper.arxiv_id else "")
        lines.append(
            f"| {i} | {title} | {paper.year or ''} | {venue} | "
            f"{paper.discovery_score.get('total', 0)} | {paper.evidence_depth} | {row.get('decision', '')} | {doi} |"
        )
    lines.append("")
    return lines


def _render_reading(data: dict[str, Any], L: dict[str, str], lang: str) -> list[str]:
    lines = [f"## {L['reading']}", ""]
    tiers = data.get("reading_path", [])
    if not tiers:
        lines.append("No reading path." if lang == "en" else "没有阅读路径。")
        lines.append("")
        return lines
    by_id = {p.paper_id: p for p in data["papers"]}
    for tier in tiers:
        name = tier.get("tier", "")
        label = L.get(name, name)
        ids = [pid for pid in tier.get("paper_ids", []) if pid in by_id]
        if not ids:
            continue
        lines.append(f"### {label}")
        rationale = _loc(tier.get("rationale"), lang)
        if rationale:
            lines.append(rationale)
            lines.append("")
        for pid in ids:
            paper = by_id[pid]
            lines.append(f"- {_fmt_paper_link(paper)} ({paper.year or 'n.d.'})")
        lines.append("")
    return lines


def _render_gaps(data: dict[str, Any], L: dict[str, str], lang: str) -> list[str]:
    lines = [f"## {L['gaps']}", ""]
    if not data["gaps"]:
        lines.append(L["no_gaps"])
        lines.append("")
        return lines
    for gap in data["gaps"]:
        statement = gap.get(lang) or gap.get("en") or gap.get("zh") or ""
        lines.append(f"### {gap.get('gap_id', '')} — {gap.get('type', '')}")
        lines.append(statement)
        if gap.get("evidence_paper_ids"):
            lines.append(f"- {L['evidence_types']}: {', '.join(gap['evidence_types'])}")
            lines.append(f"- {L['confidence']}: {gap.get('confidence', '')}")
            lines.append(f"- {L['references']}: {gap.get('evidence_refs', '')}")
        lines.append("")
    return lines


def _render_ideas(data: dict[str, Any], L: dict[str, str], lang: str) -> list[str]:
    lines = [f"## {L['ideas']}", ""]
    if not data["idea_cards"]:
        lines.append(L["no_ideas"])
        lines.append("")
        return lines
    for idea in data["idea_cards"]:
        title = idea.get(f"title_{lang}") or idea.get("title_en") or ""
        lines.append(f"### {idea.get('idea_id', '')} — {title}")
        if idea.get("prior_art"):
            lines.append(f"- {L['prior_art']}: {idea.get('prior_art_refs', '')}")
        for key, label in (("delta", L["delta"]), ("feasibility", L["feasibility"]), ("experiment", L["experiment"])):
            text = idea.get(f"{key}_{lang}") or idea.get(f"{key}_en") or ""
            if text:
                lines.append(f"- {label}: {text}")
        lines.append("")
    return lines


def _render_citation_analysis(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    analysis = data.get("citation_analysis", {}) or {}
    co_cited = (analysis.get("co_cited") or [])[:10]
    bridges = (analysis.get("bridges") or [])[:10]
    if not co_cited and not bridges:
        return []
    lines = [f"## {L['citation_graph']}", ""]
    if co_cited:
        lines.extend([f"### {L['co_cited']}", "", "| Paper | Seeds | Count |", "|---|---|---:|"])
        for row in co_cited:
            title = (row.get("title") or row.get("paper_id", ""))[:90].replace("|", "\\|")
            lines.append(f"| {title} | {', '.join(row.get('seed_ids', [])[:3])} | {row.get('count', 0)} |")
        lines.append("")
    if bridges:
        lines.extend([f"### {L['bridges']}", "", "| Paper | Seeds | Count |", "|---|---|---:|"])
        for row in bridges:
            title = (row.get("title") or row.get("paper_id", ""))[:90].replace("|", "\\|")
            lines.append(f"| {title} | {', '.join(row.get('seed_ids', [])[:3])} | {row.get('count', 0)} |")
        lines.append("")
    return lines


def _render_sources(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    lines = [f"## {L['source_status']}", ""]
    runs = data.get("search_log", {}).get("source_runs", []) or []
    if not runs:
        lines.append("No source runs recorded." if L is LABELS["en"] else "没有数据源运行记录。")
        lines.append("")
        return lines
    health = data.get("source_health", {}) or {}
    agg: dict[str, dict[str, int]] = {}
    for run in runs:
        source = str(run.get("source", ""))
        status = str(run.get("status", ""))
        agg.setdefault(source, {})
        agg[source][status] = agg[source].get(status, 0) + 1
    lines.append("| Source | Status | Runs | Health |")
    lines.append("|---|---|---:|---:|")
    for source, statuses in sorted(agg.items()):
        score = (health.get(source) or {}).get("score", "")
        for status, count in sorted(statuses.items()):
            lines.append(f"| {source} | {status} | {count} | {score} |")
    lines.append("")
    return lines


def _render_coverage(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    coverage = (data.get("saturation", {}) or {}).get("coverage", {}) or {}
    curve = (coverage.get("curve") or [])[-10:]
    if not curve:
        return []
    lines = ["### Coverage curve", "", "| Query | Source | Retrieved | New unique | Cumulative | Rediscovery |", "|---|---|---:|---:|---:|---:|"]
    for row in curve:
        lines.append(
            f"| {row.get('query_id', '')[:14]} | {row.get('source', '')} | {row.get('retrieved', 0)} | "
            f"{row.get('new_unique', 0)} | {row.get('cumulative_unique', 0)} | {row.get('rediscovery_rate', 0)} |"
        )
    lines.append("")
    if coverage.get("coverage_plateau"):
        lines.append("Plateau detected on the last queries. This is a heuristic; it is not a completeness proof.")
    else:
        lines.append("No plateau detected. Coverage is still growing or the query budget ended.")
    lines.append("")
    return lines


def _render_strata(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    strata = data.get("strata", {}) or {}
    if not strata:
        return []
    lines = ["### Citation / recency strata", "", "| Stratum | Papers |", "|---|---:|"]
    for key in ("high_impact", "recent", "emerging", "established"):
        if key in strata:
            lines.append(f"| {key} | {strata[key]} |")
    lines.append("")
    return lines


def _render_prisma_audit(data: dict[str, Any], L: dict[str, str]) -> list[str]:
    items = (data.get("prisma_audit", {}) or {}).get("items", []) or []
    if not items:
        return []
    lines = ["### PRISMA-S-informed audit", "", "| # | Item | Status | Detail |", "|---:|---|---|---|"]
    for item in items:
        detail = str(item.get("detail", "")).replace("|", "\\|")
        lines.append(f"| {item.get('item', '')} | {item.get('label', '')} | {item.get('status', '')} | {detail} |")
    lines.append("")
    return lines


def render_markdown(data: dict[str, Any], lang: str) -> str:
    L = LABELS[lang]
    plan = data["plan"]
    direction = _loc(plan.get("direction"), lang)
    lines: list[str] = []
    lines.append(f"# {L['report_title']}: {direction}")
    lines.append("")
    lines.append(f"- {L['run']}: `{data['run_id']}`")
    lines.append(f"- {L['date']}: {data['date']}")
    lines.append(f"- {L['direction']}: {direction}")
    lines.append("")

    lines.append(f"## {L['summary']}")
    lines.append(data["summary_en"] if lang == "en" else data["summary_zh"])
    lines.append("")

    if data["question_answers"]:
        lines.append(f"### {L['questions']}")
        for item in data["question_answers"]:
            answer = item.get(lang) or item.get("en") or item.get("zh") or ""
            lines.append(f"- **{item.get('question_id', '')}**: {answer}")
        lines.append("")

    lines.append(f"## {L['brief']}")
    lines.append(f"### {L['grand_challenge']}")
    lines.append(_loc(plan.get("grand_challenge"), lang))
    lines.append("")
    lines.append(f"### {L['questions']}")
    for q in plan.get("questions", []):
        text = _loc(q, lang)
        lines.append(f"- **{q.get('id', '')}** ({q.get('level', '')}): {text}")
        if q.get("operationalization"):
            lines.append(f"  - Operationalization: {q['operationalization']}")
    lines.append("")
    lines.append(f"### {L['framework']}: {plan.get('framework', {}).get('name', '')}")
    fields = plan.get("framework", {}).get("fields", {})
    if fields:
        lines.append(", ".join(f"{k}={v or '—'}" for k, v in fields.items()))
        lines.append("")
    lines.append(f"### {L['concepts']}")
    for block in plan.get("concept_blocks", []):
        terms = ", ".join(t.get("text", "") for t in block.get("terms", []) if t.get("text"))
        lines.append(f"- **{_loc(block.get('label'), lang)}**: {terms}")
    lines.append("")
    lines.append(f"### {L['criteria']}")
    for item in (plan.get("screening", {}) or {}).get("include_criteria", []):
        lines.append(f"- Include: {item}")
    for item in (plan.get("screening", {}) or {}).get("exclude_criteria", []):
        lines.append(f"- Exclude: {item}")
    lines.append("")

    lines.extend(_render_protocol(data, L))
    lines.extend(_render_prisma(data, L))
    lines.extend(_render_coverage(data, L))
    lines.extend(_render_evidence(data, L, lang))
    lines.extend(_render_strata(data, L))
    lines.extend(_render_reading(data, L, lang))
    lines.extend(_render_citation_analysis(data, L))
    lines.extend(_render_gaps(data, L, lang))
    lines.extend(_render_ideas(data, L, lang))

    lines.append(f"## {L['limitations']}")
    lines.append(_loc(data["limitations"], lang))
    lines.append("")
    lines.append(L["provisional"])
    lines.append("")
    sat = data.get("saturation", {})
    if sat:
        lines.append(f"- stopping_reason: {sat.get('stopping_reason', '')}")
        for r in sat.get("rounds", []) or []:
            lines.append(
                f"- round {r.get('round')}: new_unique={r.get('new_unique')}, "
                f"new_included={r.get('new_included')}, "
                f"marginal_relevance_rate={r.get('marginal_relevance_rate')}"
            )
        lines.append("")
    lines.extend(_render_sources(data, L))

    lines.append(f"## {L['references']}")
    for i, paper in enumerate(data.get("references", []), 1):
        lines.append(f"{i}. {_paper_ref(paper)}")
    lines.append("")
    lines.append(f"## {L['appendix']}")
    lines.extend(_render_prisma_audit(data, L))
    lines.append(f"- {L['reproduction']}: `python litsearch.py search --plan {data['run_dir']}/query_plan.json --run {data['run_dir']}`")
    lines.append(f"- {L['language_note']}")
    lines.append("")
    return "\n".join(lines)


def render_reports(run_dir: str | Path, lang: str = "both") -> dict[str, str]:
    run_dir = Path(run_dir)
    data = build_report_data(run_dir)
    paths: dict[str, str] = {}
    if lang in {"en", "both"}:
        en = render_markdown(data, "en")
        (run_dir / "report.en.md").write_text(en, encoding="utf-8")
        paths["en"] = str(run_dir / "report.en.md")
    if lang in {"zh", "both"}:
        zh = render_markdown(data, "zh")
        (run_dir / "report.zh.md").write_text(zh, encoding="utf-8")
        paths["zh"] = str(run_dir / "report.zh.md")
    if lang == "both":
        en = (run_dir / "report.en.md").read_text(encoding="utf-8")
        zh = (run_dir / "report.zh.md").read_text(encoding="utf-8")
        bilingual = "# Bilingual report / 双语报告\n\n" + en + "\n\n---\n\n" + zh
        (run_dir / "report.bilingual.md").write_text(bilingual, encoding="utf-8")
        (run_dir / "report.md").write_text(bilingual, encoding="utf-8")
        paths["bilingual"] = str(run_dir / "report.bilingual.md")
    elif lang == "en":
        (run_dir / "report.md").write_text((run_dir / "report.en.md").read_text(encoding="utf-8"), encoding="utf-8")
    elif lang == "zh":
        (run_dir / "report.md").write_text((run_dir / "report.zh.md").read_text(encoding="utf-8"), encoding="utf-8")
    return paths


def verify_run(run_dir: str | Path, *, strict: bool = False) -> list[str]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    try:
        data = build_report_data(run_dir)
    except ValueError as exc:
        return [str(exc)]
    if strict:
        for name in ("report.en.md", "report.zh.md"):
            if not (run_dir / name).exists():
                errors.append(f"strict: missing {name}; run `report --lang both` first")
    c = data["counts"]
    if c["screened"] != c["included"] + c["excluded"] + c["maybe"]:
        errors.append(
            f"PRISMA counts do not balance: screened={c['screened']} != "
            f"included+excluded+maybe={c['included'] + c['excluded'] + c['maybe']}"
        )
    if c["identified"] < c["unique"]:
        errors.append(f"identified={c['identified']} < unique={c['unique']}")
    paper_ids = {p.paper_id for p in data["papers"]}
    for row in data["rows"]:
        if row.get("paper_id") not in paper_ids:
            errors.append(f"screening row references unknown paper: {row.get('paper_id')}")
    errors.extend(validate_screening([ScreeningRow.from_dict(r) for r in data["rows"]], paper_ids))
    for edge in data["edges"]:
        if edge.get("target_paper_id") not in paper_ids:
            errors.append(f"citation edge target missing from papers: {edge.get('target_paper_id')}")
    for name in ("report.en.md", "report.zh.md"):
        path = run_dir / name
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if "[[p_" in text:
                errors.append(f"{name}: unresolved citation token")
            if "[zh missing]" in text:
                errors.append(f"{name}: missing Chinese synthesis text")
    return errors
