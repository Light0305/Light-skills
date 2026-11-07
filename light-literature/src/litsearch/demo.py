from __future__ import annotations

from pathlib import Path
from typing import Any

from .exports import export_all
from .io import ensure_dir, write_json, write_jsonl
from .models import CitationEdge, Paper, ScreeningRow
from .normalize import make_edge_id, make_paper_id, now_iso
from .query import default_plan
from .render import render_reports, verify_run
from .saturation import compute_saturation
from .screening import validate_screening, write_screening
from .scoring import score_papers


def _plan() -> dict[str, Any]:
    plan = default_plan(
        "Retrieval-augmented generation for scientific literature review",
        domain="cs",
        framework="TMDMB",
        languages=["en", "zh"],
    )
    plan["run"]["slug"] = "demo"
    plan["questions"] = [
        {
            "id": "Q1",
            "level": "answerable",
            "parent_id": "",
            "en": "Which retrieval methods are used to find evidence for scientific literature review?",
            "zh": "哪些检索方法被用于为科学文献综述寻找证据？",
            "operationalization": "Task: literature review; Method: retrieval / RAG; Data: paper corpora; Metric: recall, faithfulness; Setting: scientific literature.",
        },
        {
            "id": "Q2",
            "level": "answerable",
            "parent_id": "",
            "en": "How is citation faithfulness evaluated in RAG-based literature synthesis?",
            "zh": "在基于 RAG 的文献合成中，引用忠实度如何评估？",
            "operationalization": "Outcome: citation precision / support; Comparator: LLM-only; Data: annotated citation claims.",
        },
        {
            "id": "Q3",
            "level": "testable",
            "parent_id": "Q1",
            "en": "What evidence exists that multi-source retrieval improves coverage over a single database?",
            "zh": "有哪些证据表明多源检索比单一数据库提高覆盖度？",
            "operationalization": "Compare unique relevant papers retrieved by one vs. multiple sources; measure marginal yield and overlap.",
        },
    ]
    plan["concept_blocks"] = [
        {
            "id": "C1",
            "label": {"en": "retrieval / RAG", "zh": "检索 / RAG"},
            "required": True,
            "terms": [
                {"text": "retrieval-augmented generation", "lang": "en", "type": "free", "vocab": "none"},
                {"text": "RAG", "lang": "en", "type": "free", "vocab": "none"},
                {"text": "literature search", "lang": "en", "type": "free", "vocab": "none"},
                {"text": "citation retrieval", "lang": "en", "type": "free", "vocab": "none"},
            ],
        },
        {
            "id": "C2",
            "label": {"en": "scientific literature review", "zh": "科学文献综述"},
            "required": True,
            "terms": [
                {"text": "scientific literature review", "lang": "en", "type": "free", "vocab": "none"},
                {"text": "evidence synthesis", "lang": "en", "type": "free", "vocab": "none"},
                {"text": "literature review", "lang": "en", "type": "free", "vocab": "none"},
            ],
        },
    ]
    for lens in plan["lenses"]:
        lens["question_ids"] = ["Q1", "Q2", "Q3"]
        for leg in lens["query_legs"]:
            leg["concept_block_ids"] = ["C1", "C2"]
    plan["filters"]["year_from"] = 2018
    plan["filters"]["year_to"] = 2026
    plan["filters"]["languages"] = ["en", "zh"]
    return plan


def _papers(plan: dict[str, Any]) -> list[Paper]:
    rows = [
        ("Retrieval-Augmented Generation for Scientific Literature Review", 2024, 120, "RAG combines a retriever with a generator to ground literature review claims in retrieved evidence."),
        ("Multi-Source Literature Search for Evidence Synthesis", 2023, 90, "A multi-source search pipeline improves coverage and reduces single-database bias in evidence synthesis."),
        ("Citation Faithfulness in LLM-Based Literature Review", 2025, 40, "We evaluate citation precision and support in LLM-generated literature reviews and find frequent misattribution."),
        ("A Benchmark for Retrieval-Augmented Literature Discovery", 2026, 12, "We introduce a benchmark for literature discovery with recall, coverage, and citation faithfulness metrics."),
        ("Snowballing and Database Search: A Comparative Study", 2021, 75, "Backward and forward snowballing add unique studies but do not fully compensate for database search."),
        ("Search Strategy Errors in Systematic Reviews", 2020, 60, "Missing synonyms, controlled vocabulary, and Boolean errors reduce recall in systematic review searches."),
        ("Semantic Search for Scholarly Documents", 2022, 55, "Dense retrieval improves semantic matching but can miss exact terminology and recent papers."),
        ("OpenAlex and Semantic Scholar for Citation Graph Construction", 2024, 25, "We compare citation coverage and metadata quality across open scholarly graphs."),
        ("A Survey of Retrieval-Augmented Generation", 2023, 300, "This survey organizes RAG methods, retrieval strategies, and evaluation metrics."),
        ("Negative Results in Retrieval Evaluation", 2022, 8, "We report negative results for a retrieval reranker that fails to improve literature search."),
        ("PRISMA-Informed Search Reporting for AI-Assisted Reviews", 2026, 5, "We propose a reproducible reporting template for AI-assisted literature searches."),
        ("Terminology Drift in Interdisciplinary Literature Search", 2019, 30, "Terminology changes across fields and time; query expansion must account for drift."),
    ]
    papers = []
    for i, (title, year, cites, abstract) in enumerate(rows, 1):
        doi = f"10.5555/demo.{i}"
        papers.append(
            Paper(
                paper_id=make_paper_id(doi=doi, title=title, year=year),
                title=title,
                abstract=abstract,
                authors=[f"Demo Author {chr(64 + ((i - 1) % 6) + 1)}"],
                year=year,
                venue="Demo Conference on Literature Search",
                type="article",
                doi=doi,
                url=f"https://example.org/demo/{i}",
                cited_by_count=cites,
                language="en",
                concepts=["retrieval", "literature review", "RAG"],
                source_records=[
                    {
                        "source": "demo",
                        "source_id": f"demo-{i}",
                        "query_id": "demo-query",
                        "leg_id": "L1",
                        "lens_id": "foundation_frontier",
                        "rank": i,
                        "retrieved_at": now_iso(),
                        "url": f"https://example.org/demo/{i}",
                    }
                ],
                evidence_depth="abstract",
                created_at=now_iso(),
            )
        )
    return score_papers(papers, plan)


def _screening(papers: list[Paper]) -> list[ScreeningRow]:
    decisions = ["include"] * 6 + ["maybe"] * 3 + ["exclude"] * 3
    codes = ["OUT_OF_SCOPE"] * 3
    rows = []
    for i, (paper, decision) in enumerate(zip(papers, decisions)):
        if decision == "include":
            code = "IN_SCOPE"
            text = "Demo decision: directly relevant to the question and evidence matrix."
        elif decision == "maybe":
            code = "INSUFFICIENT_EVIDENCE"
            text = "Demo decision: potentially relevant but evidence is insufficient."
        else:
            code = "OUT_OF_SCOPE"
            text = "Demo decision: topic is outside the scoped questions."
        rows.append(
            ScreeningRow(
                paper_id=paper.paper_id,
                title=paper.title,
                year=paper.year,
                venue=paper.venue,
                doi=paper.doi,
                evidence_depth=paper.evidence_depth,
                decision=decision,
                reason_code=code,
                reason_text=text,
                question_ids="Q1,Q2,Q3",
                scores=str(paper.discovery_score.get("total", 0)),
                confidence="high" if decision == "include" else "medium",
                screened_by="demo",
                screened_at=now_iso(),
            )
        )
    return rows


def _edges(papers: list[Paper]) -> list[CitationEdge]:
    edges = []
    for i, j in [(0, 6), (1, 7), (2, 8), (3, 9)]:
        source, target = papers[i], papers[j]
        edges.append(
            CitationEdge(
                edge_id=make_edge_id(source.paper_id, target.paper_id, "forward", "demo"),
                source_paper_id=source.paper_id,
                target_paper_id=target.paper_id,
                direction="forward",
                relation="citation",
                provider="demo",
                provider_edge_id=f"demo-edge-{i}",
                round=1,
                provenance_url="https://example.org/demo-graph",
                retrieved_at=now_iso(),
            )
        )
    return edges


def _synthesis(papers: list[Paper]) -> dict[str, Any]:
    p = [x.paper_id for x in papers]
    return {
        "schema_version": "1.0",
        "summary": {
            "en": f"This offline demo shows the report contract, not a real literature finding. The candidate set contains {len(papers)} synthetic records; six are included, three are pending, and three are excluded. The central themes are retrieval for literature review [[{p[0]}]], multi-source coverage [[{p[1]}]], and citation faithfulness [[{p[2]}]]. This is not a completeness claim.",
            "zh": f"这是一个离线 demo，用于展示报告契约，不是真实文献结论。候选集包含 {len(papers)} 条合成记录，其中 6 条纳入、3 条待定、3 条排除。核心主题是面向文献综述的检索 [[{p[0]}]]、多源覆盖 [[{p[1]}]] 和引用忠实度 [[{p[2]}]]。这不等同于检索完整。",
        },
        "question_answers": [
            {
                "question_id": "Q1",
                "answer": {
                    "en": f"The demo corpus frames retrieval as a grounding step [[{p[0]}]] and compares database search with snowballing [[{p[4]}]].",
                    "zh": f"Demo 语料把检索视为证据落地步骤 [[{p[0]}]]，并比较数据库检索与滚雪球 [[{p[4]}]]。",
                },
                "paper_ids": [p[0], p[4]],
            },
            {
                "question_id": "Q2",
                "answer": {
                    "en": f"Citation faithfulness is treated as a precision/support problem [[{p[2]}]] and a benchmark target [[{p[3]}]].",
                    "zh": f"引用忠实度被视为精确率/支持度问题 [[{p[2]}]]，也是基准评测目标 [[{p[3]}]]。",
                },
                "paper_ids": [p[2], p[3]],
            },
            {
                "question_id": "Q3",
                "answer": {
                    "en": f"Multi-source evidence is suggestive but the demo records are synthetic [[{p[1]}]].",
                    "zh": f"多源检索的证据只是示意性的，demo 记录为合成数据 [[{p[1]}]]。",
                },
                "paper_ids": [p[1]],
            },
        ],
        "reading_path": [
            {
                "tier": "foundation",
                "paper_ids": [p[8], p[4], p[5]],
                "rationale": {
                    "en": "Start with the survey and the two methodological comparisons to understand the design space.",
                    "zh": "先读综述和两篇方法比较，建立设计空间。",
                },
            },
            {
                "tier": "core",
                "paper_ids": [p[0], p[1], p[2], p[3]],
                "rationale": {
                    "en": "These directly address retrieval, coverage, and citation faithfulness.",
                    "zh": "这些文献直接对应检索、覆盖度和引用忠实度。",
                },
            },
            {
                "tier": "contrarian",
                "paper_ids": [p[9], p[11]],
                "rationale": {
                    "en": "Read the negative result and terminology-drift paper to avoid overgeneralizing.",
                    "zh": "阅读负结果和术语漂移论文，避免过度推广。",
                },
            },
        ],
        "gaps": [
            {
                "gap_id": "G1",
                "type": "method",
                "statement": {
                    "en": f"The demo corpus lacks a head-to-head comparison of multi-source retrieval and citation snowballing under the same recall budget [[{p[1]}]] [[{p[4]}]].",
                    "zh": f"Demo 语料缺少在同一召回预算下对多源检索与引用滚雪球的正面对比 [[{p[1]}]] [[{p[4]}]]。",
                },
                "evidence_paper_ids": [p[1], p[4]],
                "confidence": "medium",
                "evidence_types": ["author_limitation", "missing_link"],
            }
        ],
        "idea_cards": [
            {
                "idea_id": "I1",
                "title": {
                    "en": "Budget-matched comparison of search and snowballing",
                    "zh": "等预算下的检索与滚雪球对比",
                },
                "closest_prior_art": [p[1], p[4]],
                "delta": {
                    "en": "Hold recall budget constant and measure marginal unique relevant papers per method.",
                    "zh": "固定召回预算，测量每种方法带来的边际唯一相关文献。",
                },
                "feasibility": {
                    "en": "Feasible with OpenAlex/Europe PMC and a pre-registered seed set; no proprietary data required.",
                    "zh": "可用 OpenAlex/Europe PMC 和预注册 seed set 完成，不需要专有数据。",
                },
                "discriminating_experiment": {
                    "en": "If snowballing adds no unique relevant papers beyond multi-source search at equal budget, the hypothesis is falsified.",
                    "zh": "如果在等预算下滚雪球没有带来额外唯一相关文献，则假设被证伪。",
                },
            }
        ],
        "limitations": {
            "en": "Offline demo: all records are synthetic and must not be cited as real papers. The demo exercises the report contract, not retrieval quality.",
            "zh": "离线 demo：所有记录均为合成数据，不能当作真实论文引用。demo 验证的是报告契约，不是检索质量。",
        },
    }


def run_demo(out: str | Path, *, offline: bool = True, lang: str = "both") -> dict[str, Any]:
    run_dir = ensure_dir(out)
    plan = _plan()
    papers = _papers(plan)
    rows = _screening(papers)
    edges = _edges(papers)
    write_json(run_dir / "query_plan.json", plan)
    write_jsonl(run_dir / "papers.jsonl", [p.to_dict() for p in papers])
    write_screening(run_dir, rows)
    write_jsonl(run_dir / "citation_edges.jsonl", [e.to_dict() for e in edges])
    write_json(
        run_dir / "merge_log.json",
        {"clusters": [], "duplicates_removed": 17},
    )
    write_json(
        run_dir / "search_log.json",
        {
            "schema_version": "1.0",
            "run_id": run_dir.name,
            "plan_hash": "demo",
            "started_at": now_iso(),
            "finished_at": now_iso(),
            "source_runs": [
                {"source": "demo", "query_id": "demo-q1", "status": "ok", "fetched": 10},
                {"source": "demo", "query_id": "demo-q2", "status": "ok", "fetched": 8},
                {"source": "demo", "query_id": "demo-q3", "status": "ok", "fetched": 6},
                {"source": "demo", "query_id": "demo-q4", "status": "ok", "fetched": 5},
            ],
            "events": [{"type": "demo", "timestamp": now_iso(), "detail": {"offline": offline}}],
            "totals": {"identified": 29, "unique": len(papers), "duplicates_removed": 17},
            "prisma_s": {
                "database_search": "demo",
                "citation_searching": "demo",
                "search_strategy_reporting": "demo",
                "limits": "demo",
            },
        },
    )
    write_json(
        run_dir / "compiled_queries.json",
        {
            "schema_version": "1.0",
            "plan_hash": "demo",
            "sources": ["demo"],
            "queries": [
                {
                    "query_id": "demo-q1",
                    "source": "demo",
                    "lens_id": "foundation_frontier",
                    "leg_id": "L1",
                    "sort": "relevance",
                    "query": '(retrieval-augmented generation OR RAG) AND (scientific literature review OR evidence synthesis)',
                    "params": {},
                }
            ],
            "dropped": [],
        },
    )
    write_json(run_dir / "synthesis.json", _synthesis(papers))
    compute_saturation(run_dir)
    paths = render_reports(run_dir, lang=lang)
    export_all(run_dir, papers, rows)
    screening_errors = validate_screening(rows, {p.paper_id for p in papers})
    if screening_errors:
        raise RuntimeError("Demo screening validation failed:\n" + "\n".join(f"- {e}" for e in screening_errors))
    errors = verify_run(run_dir)
    if errors:
        raise RuntimeError("Demo verification failed:\n" + "\n".join(f"- {e}" for e in errors))
    return {"run_dir": str(run_dir), "papers": len(papers), "reports": paths, "verified": True}
