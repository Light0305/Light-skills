from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from .adapters import ALL_SOURCES, DEFAULT_SOURCES, DOMAIN_BUNDLES, OPTIONAL_SOURCES
from .config import Config


class PlanError(ValueError):
    pass


FRAMEWORKS = {
    "PICO": ["population", "intervention", "comparison", "outcome"],
    "PICOS": ["population", "intervention", "comparison", "outcome", "study_design"],
    "PECO": ["population", "exposure", "comparison", "outcome"],
    "SPIDER": ["sample", "phenomenon_of_interest", "design", "evaluation", "research_type"],
    "TMDMB": ["task", "method", "dataset", "metric", "baseline"],
    "CUSTOM": ["concept_1", "concept_2", "concept_3"],
}

DOMAIN_FRAMEWORK = {
    "cs": "TMDMB",
    "biomed": "PICO",
    "social": "SPIDER",
    "general": "CUSTOM",
}

SORT_VARIANTS = {
    "europepmc": ["relevance", "recent", "cited"],
    "pubmed": ["relevance", "recent"],
    "arxiv": ["relevance", "recent"],
    "crossref": ["relevance", "recent", "cited"],
    "openaire": ["relevance", "recent", "cited"],
    "doaj": ["relevance"],
    "dblp": ["relevance"],
    "openalex": ["relevance", "recent", "cited"],
    "semantic_scholar": ["relevance"],
}

# Per-run query caps for sources with tight or fragile limits.
SOURCE_QUERY_CAPS = {
    "openaire": 2,      # anonymous ~60 req/hour
    "doaj": 1,          # upstream 502s on some networks
    "dblp": 2,          # Anubis challenge on some networks
    "openalex": 6,      # keyless daily budget
    "semantic_scholar": 3,
}

SYNONYMS = {
    "retrieval augmented generation": ["RAG", "retrieval-augmented generation"],
    "large language model": ["LLM", "large language models"],
    "literature review": ["evidence synthesis", "research synthesis"],
    "scientific literature": ["scholarly literature", "academic literature"],
    "ai agent": ["LLM agent", "autonomous agent"],
    "citation": ["reference", "bibliographic"],
    "snowball": ["citation chasing", "backward snowballing", "forward snowballing"],
}


def _has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in str(text or ""))


def _has_latin(text: str) -> bool:
    return any(("a" <= ch.lower() <= "z") for ch in str(text or ""))


def plan_warnings(plan: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for block in plan.get("concept_blocks", []) or []:
        texts = [str(t.get("text", "")).strip() for t in block.get("terms", []) if str(t.get("text", "")).strip()]
        if texts and all(_has_cjk(t) and not _has_latin(t) for t in texts):
            warnings.append(
                f"concept_block {block.get('id', '?')} is Chinese-only; English-indexed "
                "sources (OpenAlex, Crossref, Europe PMC, OpenAIRE) will underperform. "
                "Add English equivalents or use `plan init --direction-en`."
            )
    return warnings


def _direction_blocks(direction: str) -> list[dict[str, Any]]:
    text = " ".join(direction.split())
    parts: list[str] = []
    for sep in (" for ", " and ", " in ", " of "):
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            break
    if not parts:
        parts = [text]
    if len(parts) == 1 and "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
    parts = parts[:3]
    blocks = []
    for idx, part in enumerate(parts, 1):
        terms = [part]
        if "-" in part:
            terms.append(part.replace("-", " "))
        elif " " in part:
            terms.append(part.replace(" ", "-"))
        low = part.lower()
        for key, syns in SYNONYMS.items():
            if key in low or key.replace(" ", "-") in low:
                terms.extend(syns)
        seen = set()
        unique_terms = []
        for term in terms:
            key = term.lower()
            if term and key not in seen:
                seen.add(key)
                unique_terms.append(term)
        blocks.append(
            {
                "id": f"C{idx}",
                "label": {"en": part, "zh": part},
                "required": True,
                "terms": [
                    {"text": term, "lang": "en", "type": "free", "vocab": "none"}
                    for term in unique_terms
                ],
            }
        )
    return blocks


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def default_plan(
    direction: str,
    *,
    direction_en: str | None = None,
    domain: str = "general",
    framework: str | None = None,
    languages: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    now = datetime.now()
    domain = domain if domain in DOMAIN_FRAMEWORK else "general"
    framework = framework or DOMAIN_FRAMEWORK[domain]
    framework = framework.upper() if framework.upper() in FRAMEWORKS else "CUSTOM"
    languages = languages or ["en"]
    year_from = year_from or (now.year - 10)
    year_to = year_to or now.year
    direction_zh = direction.strip()
    direction_en = (direction_en or "").strip() or direction_zh
    if not direction_zh:
        direction_zh = direction_en
    short = direction_en if len(direction_en) <= 120 else direction_en[:117].rsplit(" ", 1)[0] + "..."
    short_zh = direction_zh if len(direction_zh) <= 120 else direction_zh[:117].rsplit(" ", 1)[0] + "..."
    blocks = _direction_blocks(direction_en)
    block_ids = [b["id"] for b in blocks]

    plan: dict[str, Any] = {
        "schema_version": "1.0",
        "run": {"slug": "litsearch-run", "languages": languages},
        "direction": {"en": direction_en, "zh": direction_zh},
        "domain": domain,
        "review_type": "semi_systematic",
        "framework": {"name": framework, "fields": {k: "" for k in FRAMEWORKS[framework]}},
        "grand_challenge": {
            "en": f"What is the current state of knowledge on: {short}?",
            "zh": f"关于“{short_zh}”的当前研究现状是什么？",
        },
        "questions": [
            {
                "id": "Q1",
                "level": "answerable",
                "parent_id": "",
                "en": f"What do we know about {short}?",
                "zh": f"关于“{short_zh}”我们已知什么？",
                "operationalization": "TODO: population/context, intervention/exposure/task, comparator, outcome/metric, data setting.",
            }
        ],
        "concept_blocks": blocks,
        "lenses": [
            {
                "id": "foundation_frontier",
                "name": {"en": "Foundations & frontier", "zh": "基础与前沿"},
                "enabled": True,
                "weight": 1.0,
                "question_ids": ["Q1"],
                "query_legs": [
                    {
                        "leg_id": "L1",
                        "concept_block_ids": block_ids,
                        "terms_override": [],
                        "sort_variants": ["relevance", "recent"],
                        "source_overrides": {},
                    }
                ],
            },
            {
                "id": "skeptic_method",
                "name": {"en": "Skeptic & methodologist", "zh": "批判与方法"},
                "enabled": True,
                "weight": 1.0,
                "question_ids": ["Q1"],
                "query_legs": [
                    {
                        "leg_id": "L2",
                        "concept_block_ids": block_ids,
                        "terms_override": [],
                        "sort_variants": ["relevance", "recent"],
                        "source_overrides": {},
                    }
                ],
            },
            {
                "id": "practitioner",
                "name": {"en": "Practitioner & adjacent field", "zh": "实践与邻近领域"},
                "enabled": True,
                "weight": 1.0,
                "question_ids": ["Q1"],
                "query_legs": [
                    {
                        "leg_id": "L3",
                        "concept_block_ids": block_ids,
                        "terms_override": [],
                        "sort_variants": ["relevance", "recent"],
                        "source_overrides": {},
                    }
                ],
            },
        ],
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "languages": languages,
            "types": [],
            "exclude_retracted": True,
            "include_preprints": True,
            "min_abstract_chars": 0,
        },
        "source_policy": {
            "enabled": DOMAIN_BUNDLES.get(domain, DEFAULT_SOURCES),
            "optional": OPTIONAL_SOURCES,
            "weights": {},
            "allow_keyless_optional": False,
        },
        "budgets": {
            "max_per_source": 80,
            "max_total_candidates": 400,
            "max_requests_per_source": 9,
            "citation_rounds": 1,
            "max_citation_seeds": 10,
            "time_budget_seconds": 600,
        },
        "screening": {
            "include_criteria": [
                "Directly addresses at least one listed question.",
                "Reports primary evidence, a method, a benchmark, or a substantive critique.",
            ],
            "exclude_criteria": [
                "Editorial, comment, erratum, or non-research news.",
                "Outside the stated population/context/date/language scope.",
            ],
            "rubric_weights": {},
        },
        "outputs": {
            "languages": languages,
            "formats": ["md", "csv", "json", "bibtex"],
            "run_root": "runs",
        },
    }
    return plan


def validate_plan(plan: dict[str, Any], *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        raise PlanError("Plan must be a JSON object")
    if plan.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    direction = plan.get("direction") or {}
    if not (direction.get("en") or direction.get("zh")):
        errors.append("direction.en or direction.zh is required")
    if plan.get("domain") not in {"cs", "biomed", "social", "general"}:
        errors.append("domain must be cs, biomed, social, or general")
    framework = plan.get("framework") or {}
    if framework.get("name") not in FRAMEWORKS:
        errors.append(f"framework.name must be one of {sorted(FRAMEWORKS)}")
    questions = plan.get("questions") or []
    if not questions:
        errors.append("at least one question is required")
    for q in questions:
        if not q.get("id"):
            errors.append("each question needs an id")
        if not (q.get("en") or q.get("zh")):
            errors.append(f"question {q.get('id', '?')} needs en or zh text")
    blocks = plan.get("concept_blocks") or []
    if not blocks:
        errors.append("at least one concept_block is required")
    for b in blocks:
        if not b.get("id"):
            errors.append("each concept_block needs an id")
        terms = b.get("terms") or []
        if not any(str(t.get("text", "")).strip() for t in terms):
            errors.append(f"concept_block {b.get('id', '?')} has no terms")
    lenses = plan.get("lenses") or []
    if not lenses:
        errors.append("at least one lens is required")
    for lens in lenses:
        if not lens.get("id"):
            errors.append("each lens needs an id")
        for leg in lens.get("query_legs") or []:
            if not leg.get("leg_id"):
                errors.append(f"lens {lens.get('id', '?')} has a leg without leg_id")
            for block_id in leg.get("concept_block_ids") or []:
                if block_id not in {b.get("id") for b in blocks}:
                    errors.append(f"leg {leg.get('leg_id', '?')} references unknown concept block {block_id}")
    filters = plan.get("filters") or {}
    if filters.get("year_from") and filters.get("year_to"):
        if int(filters["year_from"]) > int(filters["year_to"]):
            errors.append("filters.year_from must be <= filters.year_to")
    policy = plan.get("source_policy") or {}
    for source in policy.get("enabled", []) + policy.get("optional", []):
        if source not in ALL_SOURCES:
            errors.append(f"unknown source: {source}")
    budgets = plan.get("budgets") or {}
    if int(budgets.get("max_per_source", 0)) <= 0:
        errors.append("budgets.max_per_source must be positive")

    if strict:
        if len(questions) < 3:
            errors.append("strict: at least 3 questions are required")
        for q in questions:
            if len(str(q.get("operationalization", "")).strip()) < 20:
                errors.append(f"strict: question {q.get('id', '?')} needs an operationalization")
        if len(blocks) < 2:
            errors.append("strict: at least 2 concept blocks are required")
        generic = {"review", "systematic review", "study", "paper", "analysis", "method", "research", "literature"}
        for b in blocks:
            terms = {str(t.get("text", "")).strip().lower() for t in b.get("terms", []) if str(t.get("text", "")).strip()}
            if terms and terms <= generic:
                errors.append(f"strict: concept_block {b.get('id', '?')} contains only generic terms")
        for warning in plan_warnings(plan):
            errors.append("strict: " + warning)
        if len(lenses) < 3:
            errors.append("strict: at least 3 lenses are required")
        criteria = plan.get("screening") or {}
        if not criteria.get("include_criteria") or not criteria.get("exclude_criteria"):
            errors.append("strict: screening include/exclude criteria are required")

    if errors:
        raise PlanError("\n".join(f"- {e}" for e in errors))
    return []


def plan_terms(plan: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for block in plan.get("concept_blocks", []):
        for term in block.get("terms", []):
            text = str(term.get("text", "")).strip()
            if text:
                terms.append(text)
    seen = set()
    out = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            out.append(term)
    return out


def _quote(term: str) -> str:
    term = " ".join(str(term).split())
    return f'"{term}"'


def _block_terms(block: dict[str, Any]) -> list[str]:
    return [str(t.get("text", "")).strip() for t in block.get("terms", []) if str(t.get("text", "")).strip()]


def _block_expression(block: dict[str, Any], source: str) -> str:
    terms = _block_terms(block)
    if not terms:
        return ""
    if source == "europepmc":
        return "(" + " OR ".join(f"TITLE_ABS:{_quote(t)}" for t in terms) + ")"
    if source == "pubmed":
        parts = []
        for t in terms:
            parts.append(f"{_quote(t)}[tiab]")
        return "(" + " OR ".join(parts) + ")"
    if source == "arxiv":
        return "(" + " OR ".join(f"all:{_quote(t)}" for t in terms) + ")"
    if source == "crossref":
        return " ".join(terms)
    if source == "openaire":
        # OpenAIRE rejects queries with more than 4 logical operators. Keep at
        # most two deduplicated terms per block; compile_plan also caps blocks.
        unique: list[str] = []
        seen: set[str] = set()
        for term in terms:
            key = term.lower().replace("-", " ")
            if key not in seen:
                seen.add(key)
                unique.append(term)
        return "(" + " OR ".join(_quote(t) for t in unique[:2]) + ")"
    if source in {"doaj", "dblp"}:
        return "(" + " OR ".join(_quote(t) for t in terms) + ")"
    if source == "openalex":
        return "(" + " OR ".join(_quote(t) for t in terms) + ")"
    if source == "semantic_scholar":
        return " ".join(terms)
    return " ".join(terms)


def _extend_with_override(expr: str, override: list[str], source: str) -> str:
    # OpenAIRE has a hard 4-operator limit; overrides would exceed it.
    if source == "openaire":
        return expr
    override = [str(t).strip() for t in override if str(t).strip()]
    if not override:
        return expr
    if source == "crossref" or source == "semantic_scholar":
        return " ".join([expr] + override)
    if source == "europepmc":
        extra = "(" + " OR ".join(f"TITLE_ABS:{_quote(t)}" for t in override) + ")"
    elif source == "pubmed":
        extra = "(" + " OR ".join(f"{_quote(t)}[tiab]" for t in override) + ")"
    elif source == "arxiv":
        extra = "(" + " OR ".join(f"all:{_quote(t)}" for t in override) + ")"
    elif source in {"openaire", "doaj", "dblp"}:
        extra = "(" + " OR ".join(_quote(t) for t in override) + ")"
    else:
        extra = "(" + " OR ".join(_quote(t) for t in override) + ")"
    return f"{expr} AND {extra}"


def _date_filter(plan: dict[str, Any], source: str) -> str:
    filters = plan.get("filters") or {}
    yf, yt = filters.get("year_from"), filters.get("year_to")
    if not yf or not yt:
        return ""
    if source == "europepmc":
        return f" AND (PUB_YEAR:[{yf} TO {yt}])"
    if source == "pubmed":
        return f' AND ("{yf}"[dp] : "{yt}"[dp])'
    if source == "arxiv":
        return f" AND submittedDate:[{yf}01010000 TO {yt}12312359]"
    return ""


def _crossref_params(plan: dict[str, Any], sort: str) -> dict[str, Any]:
    filters = plan.get("filters") or {}
    parts = []
    if filters.get("year_from"):
        parts.append(f"from-pub-date:{filters['year_from']}-01-01")
    if filters.get("year_to"):
        parts.append(f"until-pub-date:{filters['year_to']}-12-31")
    types = filters.get("types") or []
    if types:
        parts.append("type:" + "|".join(types))
    params: dict[str, Any] = {"filter": ",".join(parts)} if parts else {}
    if sort == "recent":
        params.update({"sort": "published", "order": "desc"})
    elif sort == "cited":
        params.update({"sort": "is-referenced-by-count", "order": "desc"})
    else:
        params.update({"sort": "relevance", "order": "desc"})
    return params


def _openalex_params(plan: dict[str, Any], sort: str) -> dict[str, Any]:
    filters = plan.get("filters") or {}
    parts = []
    if filters.get("year_from"):
        parts.append(f"from_publication_date:{filters['year_from']}-01-01")
    if filters.get("year_to"):
        parts.append(f"to_publication_date:{filters['year_to']}-12-31")
    if filters.get("types"):
        parts.append("type:" + "|".join(filters["types"]))
    params: dict[str, Any] = {"filter": ",".join(parts)} if parts else {}
    if sort == "recent":
        params["sort"] = "publication_date:desc"
    elif sort == "cited":
        params["sort"] = "cited_by_count:desc"
    else:
        params["sort"] = "relevance_score:desc"
    return params


def _openaire_params(plan: dict[str, Any], sort: str) -> dict[str, Any]:
    filters = plan.get("filters") or {}
    params: dict[str, Any] = {"type": "publication"}
    if filters.get("year_from"):
        params["fromPublicationDate"] = f"{filters['year_from']}-01-01"
    if filters.get("year_to"):
        params["toPublicationDate"] = f"{filters['year_to']}-12-31"
    if sort == "recent":
        params["sortBy"] = "publicationDate DESC"
    elif sort == "cited":
        params["sortBy"] = "citationCount DESC"
    else:
        params["sortBy"] = "relevance DESC"
    return params


def _doaj_params(plan: dict[str, Any], sort: str) -> dict[str, Any]:
    return {}


def _dblp_params(plan: dict[str, Any], sort: str) -> dict[str, Any]:
    return {}


def _s2_params(plan: dict[str, Any]) -> dict[str, Any]:
    filters = plan.get("filters") or {}
    yf, yt = filters.get("year_from"), filters.get("year_to")
    if yf and yt:
        return {"year": f"{yf}-{yt}"}
    return {}


def compile_plan(
    plan: dict[str, Any],
    config: Config,
    *,
    sources: list[str] | None = None,
    enable_optional: bool = False,
) -> dict[str, Any]:
    validate_plan(plan)
    policy = plan.get("source_policy") or {}
    enabled = list(sources or policy.get("enabled") or DEFAULT_SOURCES)
    if enable_optional:
        for s in policy.get("optional", []) or OPTIONAL_SOURCES:
            if s == "semantic_scholar" and not config.s2_api_key:
                continue
            if s not in enabled:
                enabled.append(s)
    enabled = [s for s in enabled if s in ALL_SOURCES]

    blocks = {b["id"]: b for b in plan.get("concept_blocks", [])}
    queries: list[dict[str, Any]] = []
    for lens in plan.get("lenses", []):
        if not lens.get("enabled", True):
            continue
        for leg in lens.get("query_legs", []):
            selected_blocks = [blocks[b] for b in leg.get("concept_block_ids", []) if b in blocks]
            if not selected_blocks:
                continue
            for source in enabled:
                override = leg.get("source_overrides", {}).get(source, {}).get("terms_override", leg.get("terms_override", []))
                blocks_for_source = selected_blocks[:2] if source == "openaire" else selected_blocks
                expr = " AND ".join(filter(None, [_block_expression(b, source) for b in blocks_for_source]))
                expr = _extend_with_override(expr, override, source)
                if not expr:
                    continue
                expr += _date_filter(plan, source)
                variants = leg.get("sort_variants") or SORT_VARIANTS.get(source, ["relevance"])
                variants = [v for v in variants if v in SORT_VARIANTS.get(source, ["relevance"])]
                if not variants:
                    variants = ["relevance"]
                for sort in variants:
                    params: dict[str, Any] = {}
                    if source == "crossref":
                        params.update(_crossref_params(plan, sort))
                    elif source == "openalex":
                        params.update(_openalex_params(plan, sort))
                    elif source == "openaire":
                        params.update(_openaire_params(plan, sort))
                    elif source == "doaj":
                        params.update(_doaj_params(plan, sort))
                    elif source == "dblp":
                        params.update(_dblp_params(plan, sort))
                    elif source == "semantic_scholar":
                        params.update(_s2_params(plan))
                    query_id = "q_" + _hash(f"{source}|{lens['id']}|{leg['leg_id']}|{sort}|{expr}")
                    queries.append(
                        {
                            "query_id": query_id,
                            "source": source,
                            "lens_id": lens["id"],
                            "leg_id": leg["leg_id"],
                            "query": expr,
                            "sort": sort,
                            "params": params,
                            "filters": plan.get("filters", {}),
                        }
                    )

    # Deduplicate identical source/query/sort combinations.
    seen = set()
    unique = []
    for q in queries:
        key = (q["source"], q["query"], q["sort"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(q)

    # Per-source budget: keep relevance first, then recent, then cited.
    priority = {"relevance": 0, "recent": 1, "cited": 2}
    limited: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    per_source: dict[str, int] = {}
    base_limit = int((plan.get("budgets") or {}).get("max_requests_per_source", 9))
    for q in sorted(unique, key=lambda x: (priority.get(x["sort"], 9), x["source"])):
        cap = min(base_limit, SOURCE_QUERY_CAPS.get(q["source"], base_limit))
        if per_source.get(q["source"], 0) >= cap:
            dropped.append(q)
            continue
        per_source[q["source"]] = per_source.get(q["source"], 0) + 1
        limited.append(q)

    return {
        "schema_version": "1.0",
        "plan_hash": _hash(str(plan)),
        "sources": enabled,
        "queries": sorted(limited, key=lambda x: (x["source"], priority.get(x["sort"], 9), x["query_id"])),
        "dropped": dropped,
        "budget_per_source": base_limit,
    }
