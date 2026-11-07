from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .adapters import (
    ALL_SOURCES,
    DEFAULT_SOURCES,
    EXPERIMENTAL_SOURCES,
    OPTIONAL_SOURCES,
    SOURCE_CAPABILITIES,
)
from .pipeline import (
    compile_plan_file,
    init_plan,
    load_and_validate,
    print_status,
    run_citation_analyze,
    run_citation_expand,
    run_doctor,
    run_oa_enrich,
    run_pdf_fetch,
    run_report,
    run_saturation,
    run_screen_prescreen,
    run_screen_validate,
    run_search,
    run_status,
    run_verify,
)
from .literature import add_pdf, build_literature
from .library_check import verify_literature
from .query import PlanError, plan_warnings


def _parse_sources(value: str | None) -> list[str] | None:
    if not value:
        return None
    value = value.strip().lower()
    if value in {"all", "*"}:
        return [s for s in ALL_SOURCES if s != "opencitations"]
    if value in {"default", "fast", "keyless"}:
        return list(DEFAULT_SOURCES)
    if value == "optional":
        return list(OPTIONAL_SOURCES)
    if value == "experimental":
        return list(EXPERIMENTAL_SOURCES)
    return [x.strip() for x in value.split(",") if x.strip()]


def _parse_languages(value: str) -> list[str]:
    return ["en", "zh"] if value == "both" else [value]


def _print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="litsearch",
        description="Bilingual, reproducible literature discovery from a research direction.",
    )
    parser.add_argument("--version", action="version", version=f"litsearch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # plan
    plan = sub.add_parser("plan", help="Create, validate, or compile a query plan.")
    plan_sub = plan.add_subparsers(dest="plan_command", required=True)
    p_init = plan_sub.add_parser("init", help="Write a query-plan skeleton.")
    p_init.add_argument("--direction", required=True)
    p_init.add_argument("--direction-en", default=None, help="English canonical direction (recommended for Chinese input).")
    p_init.add_argument("--domain", default="general", choices=["cs", "biomed", "social", "general"])
    p_init.add_argument("--framework", default=None)
    p_init.add_argument("--lang", default="en", choices=["en", "zh", "both"])
    p_init.add_argument("--out", required=True)
    p_init.add_argument("--year-from", type=int, default=None)
    p_init.add_argument("--year-to", type=int, default=None)

    p_val = plan_sub.add_parser("validate", help="Validate a query plan.")
    p_val.add_argument("--plan", required=True)
    p_val.add_argument("--strict", action="store_true")

    p_comp = plan_sub.add_parser("compile", help="Compile source-specific queries.")
    p_comp.add_argument("--plan", required=True)
    p_comp.add_argument("--out", required=True)
    p_comp.add_argument("--sources", default=None)
    p_comp.add_argument("--enable-optional", action="store_true")

    # search
    search = sub.add_parser("search", help="Run multi-source retrieval.")
    search.add_argument("--plan", required=True)
    search.add_argument("--run", required=True)
    search.add_argument("--sources", default=None)
    search.add_argument("--max-per-source", type=int, default=None)
    search.add_argument("--enable-optional", action="store_true")

    # screening
    screen = sub.add_parser("screen", help="Prescreen or validate screening decisions.")
    screen_sub = screen.add_subparsers(dest="screen_command", required=True)
    s_pre = screen_sub.add_parser("prescreen", help="Apply deterministic hard filters.")
    s_pre.add_argument("--run", required=True)
    s_pre.add_argument("--new-only", action="store_true")
    s_val = screen_sub.add_parser("validate", help="Validate screening.csv / screening.jsonl.")
    s_val.add_argument("--run", required=True)

    # citations
    citations = sub.add_parser("citations", help="Citation expansion.")
    cit_sub = citations.add_subparsers(dest="citation_command", required=True)
    c_exp = cit_sub.add_parser("expand", help="Expand backward/forward citations from seeds.")
    c_exp.add_argument("--run", required=True)
    c_exp.add_argument("--round", type=int, default=1)
    c_exp.add_argument("--seeds", type=int, default=None)
    c_exp.add_argument("--sources", default="europepmc,opencitations")
    c_exp.add_argument("--directions", default="forward,backward")
    c_exp.add_argument("--seed-paper-ids", default=None, help="Comma-separated internal paper IDs.")
    c_an = cit_sub.add_parser("analyze", help="Build co-citation and bridge analysis.")
    c_an.add_argument("--run", required=True)

    # metrics
    metrics = sub.add_parser("metrics", help="Compute run metrics.")
    met_sub = metrics.add_subparsers(dest="metrics_command", required=True)
    m_sat = met_sub.add_parser("saturation", help="Compute the saturation record.")
    m_sat.add_argument("--run", required=True)

    # open-access enrichment
    oa = sub.add_parser("oa", help="Open-access enrichment via Unpaywall.")
    oa_sub = oa.add_subparsers(dest="oa_command", required=True)
    oa_enrich = oa_sub.add_parser("enrich", help="Fill PDF links for DOI-bearing papers.")
    oa_enrich.add_argument("--run", required=True)
    oa_enrich.add_argument("--limit", type=int, default=20)

    pdf = sub.add_parser("pdf", help="Download open-access PDFs.")
    pdf_sub = pdf.add_subparsers(dest="pdf_command", required=True)
    pdf_fetch = pdf_sub.add_parser("fetch", help="Fetch verified OA PDFs for a run.")
    pdf_fetch.add_argument("--run", required=True)
    pdf_fetch.add_argument("--limit", type=int, default=20)
    pdf_fetch.add_argument("--out", default=None)

    literature = sub.add_parser("literature", help="Build Literature/<paper>/ folders for host-model reading.")
    lit_sub = literature.add_subparsers(dest="literature_command", required=True)
    lit_verify = lit_sub.add_parser("verify", help="Check library index and recorded PDF identity without writes.")
    lit_verify.add_argument("--out", required=True)
    lit_build = lit_sub.add_parser("build", help="Create per-paper folders, prepare PDFs for host-model reading.")
    lit_build.add_argument("--run", required=True)
    lit_build.add_argument("--out", required=True)
    lit_build.add_argument("--status", default="include", help="Comma-separated screening decisions.")
    lit_build.add_argument("--paper-ids", default=None, help="Comma-separated internal paper IDs.")
    lit_build.add_argument("--include-maybe", action="store_true")
    lit_build.add_argument("--limit", type=int, default=None)
    lit_build.add_argument("--fetch-pdfs", action="store_true")

    lit_add = lit_sub.add_parser("add", help="Import a user-supplied PDF and run Phase 2.")
    lit_add.add_argument("--pdf", required=True)
    lit_add.add_argument("--out", required=True)
    lit_add.add_argument("--title", default=None)
    lit_add.add_argument("--authors", default=None, help="Comma-separated authors.")
    lit_add.add_argument("--year", type=int, default=None)
    lit_add.add_argument("--doi", default="")

    for command in (lit_build, lit_add):
        command.add_argument("--dry-run", action="store_true", help="Preview selection and page counts without writing output or fetching PDFs.")
        command.add_argument("--force-prepare", action="store_true", help="Refresh page assets and reading tasks; preserve model-authored files.")

    # report
    report = sub.add_parser("report", help="Render bilingual Markdown reports and exports.")
    report.add_argument("--run", required=True)
    report.add_argument("--lang", default="both", choices=["en", "zh", "both"])
    report.add_argument("--formats", default="md,csv,json,bibtex")

    # verify / status / demo
    verify = sub.add_parser("verify", help="Check run integrity and PRISMA arithmetic.")
    verify.add_argument("--run", required=True)
    verify.add_argument("--strict", action="store_true")

    status = sub.add_parser("status", help="Print run status.")
    status.add_argument("--run", required=True)

    doctor = sub.add_parser("doctor", help="Show keyless/key configuration status.")
    doctor.add_argument("--json", action="store_true")

    demo = sub.add_parser("demo", help="Create an offline synthetic run.")
    demo.add_argument("--offline", action="store_true", default=True)
    demo.add_argument("--out", default="runs/demo")
    demo.add_argument("--lang", default="both", choices=["en", "zh", "both"])

    sources = sub.add_parser("sources", help="List available sources.")
    sources.add_argument("--json", action="store_true")

    return parser


def _reconfigure_stdio() -> None:
    """Make Chinese paths/titles printable on Windows legacy consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def main(argv: list[str] | None = None) -> int:
    _reconfigure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            if args.plan_command == "init":
                plan = init_plan(
                    args.direction,
                    direction_en=args.direction_en,
                    domain=args.domain,
                    framework=args.framework,
                    languages=_parse_languages(args.lang),
                    out=args.out,
                    year_from=args.year_from,
                    year_to=args.year_to,
                )
                print(f"Wrote {args.out}")
                for warning in plan_warnings(plan):
                    print(f"Warning: {warning}", file=sys.stderr)
                _print({"questions": len(plan["questions"]), "concept_blocks": len(plan["concept_blocks"])})
                return 0
            if args.plan_command == "validate":
                plan = load_and_validate(args.plan, strict=args.strict)
                print(f"Plan OK: {args.plan}")
                for warning in plan_warnings(plan):
                    print(f"Warning: {warning}", file=sys.stderr)
                _print({"questions": len(plan["questions"]), "concept_blocks": len(plan["concept_blocks"])})
                return 0
            if args.plan_command == "compile":
                compiled = compile_plan_file(
                    args.plan,
                    out=args.out,
                    sources=_parse_sources(args.sources),
                    enable_optional=args.enable_optional,
                )
                print(f"Wrote {args.out}")
                _print(
                    {
                        "sources": compiled["sources"],
                        "queries": len(compiled["queries"]),
                        "dropped": len(compiled["dropped"]),
                    }
                )
                return 0

        if args.command == "search":
            result = run_search(
                args.plan,
                args.run,
                sources=_parse_sources(args.sources),
                max_per_source=args.max_per_source,
                enable_optional=args.enable_optional,
            )
            _print(result)
            return 0

        if args.command == "screen":
            if args.screen_command == "prescreen":
                _print(run_screen_prescreen(args.run, new_only=args.new_only))
                return 0
            if args.screen_command == "validate":
                errors = run_screen_validate(args.run)
                if errors:
                    print("Screening validation failed:", file=sys.stderr)
                    for error in errors:
                        print(f"- {error}", file=sys.stderr)
                    return 1
                print("Screening OK")
                return 0

        if args.command == "citations":
            if args.citation_command == "expand":
                result = run_citation_expand(
                    args.run,
                    round_no=args.round,
                    seeds=args.seeds,
                    sources=[x.strip() for x in args.sources.split(",") if x.strip()],
                    directions=[x.strip() for x in args.directions.split(",") if x.strip()],
                    seed_paper_ids=[x.strip() for x in (args.seed_paper_ids or "").split(",") if x.strip()],
                )
                _print(result)
                return 0
            if args.citation_command == "analyze":
                _print(run_citation_analyze(args.run))
                return 0

        if args.command == "metrics":
            if args.metrics_command == "saturation":
                _print(run_saturation(args.run))
                return 0

        if args.command == "oa":
            if args.oa_command == "enrich":
                _print(run_oa_enrich(args.run, limit=args.limit))
                return 0

        if args.command == "pdf":
            if args.pdf_command == "fetch":
                _print(run_pdf_fetch(args.run, limit=args.limit, out_dir=args.out))
                return 0

        if args.command == "literature":
            if args.literature_command == "verify":
                result = verify_literature(args.out)
                _print(result)
                return 0 if result["ok"] else 1
            if args.literature_command == "build":
                statuses = {x.strip() for x in args.status.split(",") if x.strip()}
                if args.include_maybe:
                    statuses.add("maybe")
                result = build_literature(
                    args.run,
                    args.out,
                    statuses=statuses,
                    paper_ids={x.strip() for x in (args.paper_ids or "").split(",") if x.strip()} or None,
                    limit=args.limit,
                    fetch_pdf=args.fetch_pdfs,
                    dry_run=args.dry_run,
                    force_prepare=args.force_prepare,
                )
                _print({k: v for k, v in result.items() if k != "entries"})
                return 0
            if args.literature_command == "add":
                result = add_pdf(
                    args.pdf,
                    args.out,
                    title=args.title,
                    authors=args.authors,
                    year=args.year,
                    doi=args.doi,
                    dry_run=args.dry_run,
                    force_prepare=args.force_prepare,
                )
                _print({k: v for k, v in result.items() if k != "entries"})
                return 0

        if args.command == "doctor":
            result = run_doctor()
            if args.json:
                _print(result)
            else:
                print("litsearch doctor")
                for key, value in result["config"].items():
                    print(f"  {key}: {'set' if value else 'missing'}")
                print(f"  pdf_renderer: {result.get('pdf_renderer') or 'missing (read PDF directly or install pypdfium2 Pillow)'}")
                print("  default/keyless:", ", ".join(result["keyless_default_sources"]))
                print("  optional keyed:", ", ".join(result["optional_keyed_sources"]))
                print("  experimental:", ", ".join(result["experimental_sources"]))
                print("  notes:")
                for note in result["notes"]:
                    print(f"    - {note}")
                health = result.get("source_health", {}) or {}
                if health:
                    print("  health:")
                    for source, record in sorted(health.items()):
                        print(f"    - {source}: {record.get('score', '?')} ({record.get('last_status', '')})")
            return 0

        if args.command == "report":
            paths = run_report(args.run, lang=args.lang)
            _print(paths)
            return 0

        if args.command == "verify":
            errors = run_verify(args.run, strict=args.strict)
            if errors:
                print("Verification failed:", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print("Run OK")
            return 0

        if args.command == "status":
            print(print_status(run_status(args.run)))
            return 0

        if args.command == "demo":
            from .demo import run_demo

            result = run_demo(args.out, offline=True, lang=args.lang)
            _print(result)
            return 0

        if args.command == "sources":
            if args.json:
                _print(
                    {
                        "default_keyless": DEFAULT_SOURCES,
                        "optional_keyed": OPTIONAL_SOURCES,
                        "experimental": EXPERIMENTAL_SOURCES,
                        "all_search": [s for s in ALL_SOURCES if s != "opencitations"],
                        "capabilities": SOURCE_CAPABILITIES,
                    }
                )
            else:
                print("default/keyless:", ", ".join(DEFAULT_SOURCES))
                print("optional keyed:", ", ".join(OPTIONAL_SOURCES))
                print("experimental:", ", ".join(EXPERIMENTAL_SOURCES))
                print("all search:", ", ".join(s for s in ALL_SOURCES if s != "opencitations"))
            return 0

    except PlanError as exc:
        print(f"Plan error:\n{exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 2
