"""Command-line interface for light-crawl."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import js_reverse, rea, scrapling
from .benchmark import run_benchmark, write_benchmark
from .capture import capture_target
from .doctor import format_checks, run_doctor
from .learn import learn_case
from .metrics import record_metrics, show_metrics
from .migrate import migrate_site_pack
from .models import Lane, PageKind, Phase, PHASE_ORDER, ProbeResult, TargetProfile
from .probe import probe_target
from .report import write_report
from .router import decide_route
from .sessions import SessionBroker, SessionConflict
from .site import check_site_pack, default_output, list_site_packs, read_site_pack_info, run_site_pack
from .state import CaseStore, LightCrawlError, load_probe
from .utils import ensure_dir, write_json
from .verify import format_report, verify_case
from .validation import run_check
from .dataset import check_dataset, export_dataset


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _case(args: argparse.Namespace) -> CaseStore:
    return CaseStore.resolve(args.case, Path(args.case_root))


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_site_root() -> Path:
    for candidate in (Path("examples/site-packs"), _skill_root() / "examples" / "site-packs"):
        if candidate.exists():
            return candidate
    return Path("examples/site-packs")


def _default_benchmark_root() -> Path:
    for candidate in (Path("benchmarks/cases"), _skill_root() / "benchmarks" / "cases"):
        if candidate.exists():
            return candidate
    return Path("benchmarks/cases")


def _resolve_pack(value: str) -> Path:
    candidate = Path(value)
    if candidate.exists():
        return candidate
    fallback = _skill_root() / value
    return fallback if fallback.exists() else candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="light-crawl",
        description="Probe → route → reverse → rebuild → crawl → verify → learn.",
    )
    parser.add_argument("--version", action="version", version=f"light-crawl {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    dataset = sub.add_parser('dataset', help='Export/check an explicit research-data handoff without copying large data.')
    actions = dataset.add_subparsers(dest='dataset_action', required=True)
    export = actions.add_parser('export')
    export.add_argument('case')
    export.add_argument('--case-root', default='cases')
    export.add_argument('--spec', required=True)
    export.add_argument('--out', required=True)
    check = actions.add_parser('check')
    check.add_argument('manifest')

    doctor = sub.add_parser("doctor", help="Check Python, Scrapling, js-reverse, REA and browser readiness.")
    doctor.add_argument("--json", action="store_true", help="Machine-readable output.")
    doctor.add_argument("--strict", action="store_true", help="Exit non-zero on warnings as well as failures.")

    new_case = sub.add_parser("new-case", help="Create a case with scope, target and artifact directories.")
    new_case.add_argument("slug", help="Short case name.")
    new_case.add_argument("--target", required=True, help="Entry URL or local artifact path.")
    new_case.add_argument("--kind", default="web", help="web, app, electron, asar, apk, har, saz, native, ...")
    new_case.add_argument("--volume", type=int, default=1, help="Expected items/pages; >=1000 selects spider delivery.")
    new_case.add_argument("--auth", default="none", help="none, cookie, bearer, login, ...")
    new_case.add_argument("--geo", default="", help="Required geography or locale.")
    new_case.add_argument("--authorized", action="store_true", help="Confirm authorization is on file.")
    new_case.add_argument("--notes", default="", help="Free-form scope notes.")
    new_case.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    new_case.add_argument("--force", action="store_true", help="Replace an existing case.")
    new_case.add_argument("--json", action="store_true", help="Machine-readable output.")

    probe = sub.add_parser("probe", help="Run a cheap HTTP probe and classify the response.")
    probe.add_argument("case", help="Case directory or slug.")
    probe.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    probe.add_argument("--header", action="append", default=[], help="Extra request header KEY=VALUE.")
    probe.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    probe.add_argument("--json", action="store_true", help="Machine-readable output.")

    capture = sub.add_parser("capture", help="Save a raw HTTP response into fixtures/ and evidence.")
    capture.add_argument("case", help="Case directory or slug.")
    capture.add_argument("--timeout", type=int, default=20, help="HTTP/browser timeout in seconds.")
    capture.add_argument("--max-bytes", type=int, default=10_000_000, help="Maximum body bytes to save.")
    capture.add_argument("--header", action="append", default=[], help="Extra request header KEY=VALUE.")
    capture.add_argument("--engine", choices=["http", "scrapling"], default="http", help="Capture engine.")
    capture.add_argument("--headed", action="store_true", help="Show the browser when using scrapling.")
    capture.add_argument("--solve-cloudflare", action="store_true", help="Enable Scrapling's Cloudflare solver.")
    capture.add_argument("--wait-selector", default="", help="Wait for this selector in scrapling mode.")
    capture.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    capture.add_argument("--json", action="store_true", help="Machine-readable output.")

    route = sub.add_parser("route", help="Choose L0-L4 and delivery mode from the probe.")
    route.add_argument("case", help="Case directory or slug.")
    route.add_argument("--lane", default="", help="Manual lane override: L0_STATIC, L0_API, L1_DYNAMIC, L2_SIGNED, L3_BLOCKED, L4_APP.")
    route.add_argument("--delivery", default="", choices=["", "single", "spider"], help="Manual delivery override.")
    route.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    route.add_argument("--json", action="store_true", help="Machine-readable output.")

    status = sub.add_parser("status", help="Show the current case state.")
    status.add_argument("case", help="Case directory or slug.")
    status.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    status.add_argument("--json", action="store_true", help="Machine-readable output.")

    evidence = sub.add_parser("evidence", help="Append an observation to the evidence ledger.")
    evidence.add_argument("case", help="Case directory or slug.")
    evidence.add_argument("--phase", default="", help="Phase label; defaults to the current phase.")
    evidence.add_argument("--source", required=True, help="Tool or person that produced the observation.")
    evidence.add_argument("--action", required=True, help="What was done.")
    evidence.add_argument("--observation", required=True, help="What was observed.")
    evidence.add_argument("--inference", default="", help="What it may mean; keep separate from observation.")
    evidence.add_argument("--confidence", default="medium", choices=["low", "medium", "high"], help="Confidence in the inference.")
    evidence.add_argument("--artifact", default="", help="Path or label of the supporting artifact.")
    evidence.add_argument("--artifact-file", default="", help="Copy this file into artifacts/ and reference it.")
    evidence.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    evidence.add_argument("--json", action="store_true", help="Machine-readable output.")

    advance = sub.add_parser("advance", help="Move a case forward through the phase state machine.")
    advance.add_argument("case", help="Case directory or slug.")
    advance.add_argument("phase", choices=[phase.value for phase in Phase], help="Target phase.")
    advance.add_argument("--note", default="", help="Why the phase changed.")
    advance.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    advance.add_argument("--json", action="store_true", help="Machine-readable output.")

    verify = sub.add_parser("verify", help="Offline-check a case contract, fixtures, hashes and secrets.")
    verify.add_argument("case", help="Case directory or slug.")
    verify.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    verify.add_argument("--json", action="store_true", help="Machine-readable output.")
    verify.add_argument('--run-check', help='Explicitly execute a trusted local Python check under repro/, spider/ or fixtures/.')
    verify.add_argument('--timeout', type=int, default=60, help='Selected check timeout in seconds.')

    report = sub.add_parser("report", help="Render reports/report.md from the case artifacts.")
    report.add_argument("case", help="Case directory or slug.")
    report.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    report.add_argument("--json", action="store_true", help="Machine-readable output.")

    learn = sub.add_parser("learn", help="Promote the case into a reusable site pack.")
    learn.add_argument("case", help="Case directory or slug.")
    learn.add_argument("--domain", default="", help="Domain for the site pack; inferred from the target URL by default.")
    learn.add_argument("--sites-root", default="sites", help="Directory that holds site packs.")
    learn.add_argument("--force", action="store_true", help="Replace an existing site pack.")
    learn.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    learn.add_argument("--json", action="store_true", help="Machine-readable output.")

    site = sub.add_parser("site", help="Inspect or run tracked site packs.")
    site_sub = site.add_subparsers(dest="site_action", required=True)
    site_list = site_sub.add_parser("list", help="List site packs under a root.")
    site_list.add_argument("--root", default="", help="Site-pack root; defaults to the skill's examples/site-packs.")
    site_list.add_argument("--stale-days", type=int, default=30, help="Mark packs unverified for more than N days.")
    site_list.add_argument("--json", action="store_true", help="Machine-readable output.")
    site_show = site_sub.add_parser("show", help="Show one site pack.")
    site_show.add_argument("pack", help="Site-pack directory.")
    site_show.add_argument("--json", action="store_true", help="Machine-readable output.")
    site_check = site_sub.add_parser("check", help="Run a pack's offline verifier.")
    site_check.add_argument("pack", help="Site-pack directory.")
    site_check.add_argument("--write", action="store_true", help="Update last_verified_at on success.")
    site_check.add_argument("--timeout", type=int, default=120, help="Verifier timeout in seconds.")
    site_check.add_argument("--json", action="store_true", help="Machine-readable output.")
    site_migrate = site_sub.add_parser("migrate", help="Migrate site.json to the current schema.")
    site_migrate.add_argument("pack", nargs="?", default="", help="Site-pack directory.")
    site_migrate.add_argument("--all", action="store_true", help="Migrate every pack under --root.")
    site_migrate.add_argument("--root", default="", help="Site-pack root for --all; defaults to the skill's examples/site-packs.")
    site_migrate.add_argument("--write", action="store_true", help="Write migrated site.json files.")
    site_migrate.add_argument("--json", action="store_true", help="Machine-readable output.")
    site_run = site_sub.add_parser("run", help="Run the pack's spider and offline verifier.")
    site_run.add_argument("pack", help="Site-pack directory, e.g. examples/site-packs/quotes.")
    site_run.add_argument("--out", default="", help="Output file; defaults under runs/.")
    site_run.add_argument("--max-pages", type=int, default=None, help="Override the spider page budget.")
    site_run.add_argument("--crawldir", default="", help="Checkpoint directory for pause/resume.")
    site_run.add_argument("--skip-verify", action="store_true", help="Do not run the pack's verify.py.")
    site_run.add_argument("--timeout", type=int, default=300, help="Spider timeout in seconds.")
    site_run.add_argument("--json", action="store_true", help="Machine-readable output.")

    metrics = sub.add_parser("metrics", help="Record or show actual run metrics for a case.")
    metrics_sub = metrics.add_subparsers(dest="metrics_action", required=True)
    metrics_record = metrics_sub.add_parser("record", help="Record items, requests, browser time, tokens and quality.")
    metrics_record.add_argument("case", help="Case directory or slug.")
    metrics_record.add_argument("--items", type=int, required=True, help="Items produced by the run.")
    metrics_record.add_argument("--requests", type=int, default=0, help="HTTP requests used.")
    metrics_record.add_argument("--browser-seconds", type=float, default=0.0, help="Browser wall time used.")
    metrics_record.add_argument("--tokens", type=int, default=0, help="Agent/model tokens used.")
    metrics_record.add_argument("--success-rate", type=float, required=True, help="0..1 field/extraction success rate.")
    metrics_record.add_argument("--drift-recovery", type=float, default=0.0, help="0..1 drift recovery rate.")
    metrics_record.add_argument("--note", default="", help="Run label or context.")
    metrics_record.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    metrics_record.add_argument("--json", action="store_true", help="Machine-readable output.")
    metrics_show = metrics_sub.add_parser("show", help="Show recorded metrics.")
    metrics_show.add_argument("case", help="Case directory or slug.")
    metrics_show.add_argument("--case-root", default="cases", help="Directory that holds cases.")
    metrics_show.add_argument("--json", action="store_true", help="Machine-readable output.")

    session = sub.add_parser("session", help="Inspect or claim a browser-profile lock.")
    session_sub = session.add_subparsers(dest="session_action", required=True)
    session_status = session_sub.add_parser("status", help="Show one profile or all profile locks.")
    session_status.add_argument("profile", nargs="?", default="", help="Profile name; omit to list all.")
    session_status.add_argument("--root", default=".light-crawl/sessions", help="Lock directory.")
    session_status.add_argument("--json", action="store_true", help="Machine-readable output.")
    session_acquire = session_sub.add_parser("acquire", help="Claim a profile for this owner.")
    session_acquire.add_argument("profile", help="Profile name, e.g. js-reverse-default.")
    session_acquire.add_argument("--owner", required=True, help="Owner label, e.g. case-id or agent session.")
    session_acquire.add_argument("--ttl", type=int, default=3600, help="Lease seconds (minimum 60).")
    session_acquire.add_argument("--note", default="", help="Why this profile is owned.")
    session_acquire.add_argument("--force", action="store_true", help="Take over an active lock. Use deliberately.")
    session_acquire.add_argument("--root", default=".light-crawl/sessions", help="Lock directory.")
    session_acquire.add_argument("--json", action="store_true", help="Machine-readable output.")
    session_release = session_sub.add_parser("release", help="Release a profile owned by this owner.")
    session_release.add_argument("profile", help="Profile name.")
    session_release.add_argument("--owner", required=True, help="Owner label that holds the lock.")
    session_release.add_argument("--root", default=".light-crawl/sessions", help="Lock directory.")
    session_release.add_argument("--json", action="store_true", help="Machine-readable output.")
    session_cleanup = session_sub.add_parser("cleanup", help="Remove expired profile locks.")
    session_cleanup.add_argument("--root", default=".light-crawl/sessions", help="Lock directory.")
    session_cleanup.add_argument("--json", action="store_true", help="Machine-readable output.")

    adapters = sub.add_parser("adapters", help="Show the status of Scrapling, js-reverse and REA.")
    adapters.add_argument("--json", action="store_true", help="Machine-readable output.")

    benchmark = sub.add_parser("benchmark", help="Run the routing benchmark and aggregate cost metrics.")
    benchmark.add_argument("--cases", default="", help="Benchmark cases directory; defaults to the skill's benchmarks/cases.")
    benchmark.add_argument("--source-cases", default="cases", help="Standard case directory for measured metrics.")
    benchmark.add_argument("--out", default="benchmarks/results", help="Output directory for results.json and report.md.")
    benchmark.add_argument("--json", action="store_true", help="Machine-readable output.")

    demo = sub.add_parser("demo", help="Create an offline demo case and report with synthetic data.")
    demo.add_argument("--out", default="runs/demo", help="Demo case directory.")
    demo.add_argument("--force", action="store_true", help="Replace an existing demo.")
    demo.add_argument("--json", action="store_true", help="Machine-readable output.")

    return parser


def _cmd_doctor(args: argparse.Namespace) -> int:
    checks = run_doctor()
    if args.json:
        print(_json([check.to_dict() for check in checks]))
    else:
        print(format_checks(checks))
    failures = any(check.status == "fail" for check in checks)
    warnings = any(check.status == "warn" for check in checks)
    return 1 if failures or (args.strict and warnings) else 0


def _cmd_new_case(args: argparse.Namespace) -> int:
    target = TargetProfile(
        url=args.target,
        kind=args.kind,
        volume=max(1, args.volume),
        auth=args.auth,
        geo=args.geo,
        authorized=args.authorized,
        notes=args.notes,
    )
    store = CaseStore.create(Path(args.case_root), args.slug, target, force=args.force)
    payload = store.summary()
    if args.json:
        print(_json(payload))
    else:
        print(f"Created case: {store.directory.resolve()}")
        print(f"  phase: {store.state.phase}")
        print(f"  next:  light-crawl probe {store.directory}")
        if not args.authorized:
            print("  WARNING: scope.md says authorization is not confirmed. Do not send traffic yet.")
    return 0


def _parse_headers(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        if "=" in value:
            key, raw = value.split("=", 1)
        elif ":" in value:
            key, raw = value.split(":", 1)
        else:
            raise LightCrawlError(f"Header must be KEY=VALUE or KEY: VALUE: {value}")
        key = key.strip()
        if not key:
            raise LightCrawlError(f"Header has an empty name: {value}")
        headers[key] = raw.strip()
    return headers


def _cmd_probe(args: argparse.Namespace) -> int:
    store = _case(args)
    if not store.target.authorized:
        raise LightCrawlError('Confirm the authorized/public-data scope before sending traffic')
    headers = _parse_headers(args.header)
    result = probe_target(store.target.url, timeout=max(1, args.timeout), headers=headers)
    write_json(store.probe_file, result.to_dict())
    if PHASE_ORDER.index(Phase(store.state.phase)) < PHASE_ORDER.index(Phase.PROBED):
        store.advance(Phase.PROBED, f"HTTP probe completed with status {result.status or 'error'}")
    artifact = store.add_artifact(store.probe_file, 'probe')
    store.add_evidence(
        phase=store.state.phase,
        source="light-crawl probe",
        action=f"GET {store.target.url}",
        observation=(
            f"status={result.status}; kind={result.page_kind}; title={result.title!r}; "
            f"scripts={result.script_count}; text={result.visible_text_chars}; "
            f"api_candidates={len(result.api_candidates)}; hints={','.join(result.signature_hints) or 'none'}"
        ),
        inference="initial acquisition lane hypothesis" if not result.error else "probe failed; investigate network or protection",
        confidence="medium" if not result.error else "low",
        artifact=artifact,
    )
    if result.error:
        store.add_blocker(f"probe error: {result.error}")
    if args.json:
        print(_json({"case": store.summary(), "probe": result.to_dict()}))
    else:
        print(f"Probe: {store.target.url}")
        print(f"  status:        {result.status or 'error'}")
        print(f"  page kind:     {result.page_kind}")
        print(f"  title:         {result.title or '(none)'}")
        print(f"  scripts:       {result.script_count}")
        print(f"  text chars:    {result.visible_text_chars}")
        print(f"  API candidates:{len(result.api_candidates)}")
        for candidate in result.api_candidates[:5]:
            print(f"    - {candidate}")
        if result.signature_hints:
            print(f"  hints:         {', '.join(result.signature_hints)}")
        if result.error:
            print(f"  error:         {result.error}")
        print(f"  next:          light-crawl route {store.directory}")
    return 0 if not result.error else 1


def _cmd_capture(args: argparse.Namespace) -> int:
    store = _case(args)
    headers = _parse_headers(args.header)
    result = capture_target(
        store,
        timeout=max(1, args.timeout),
        max_bytes=max(1024, args.max_bytes),
        extra_headers=headers,
        engine=args.engine,
        headed=args.headed,
        solve_cloudflare=args.solve_cloudflare,
        wait_selector=args.wait_selector,
    )
    if args.json:
        print(_json({"case": store.summary(), "capture": result.to_dict()}))
    else:
        print(f"Captured: {result.url}")
        print(f"  status:  {result.status}")
        print(f"  bytes:   {len(result.body)}")
        print(f"  fixture: {result.body_path.relative_to(store.directory)}")
        print(f"  meta:    {result.meta_path.relative_to(store.directory)}")
    return 0


def _cmd_route(args: argparse.Namespace) -> int:
    store = _case(args)
    probe = load_probe(store)
    decision = decide_route(probe, store.target)
    if args.lane:
        valid_lanes = {lane.value for lane in Lane}
        if args.lane not in valid_lanes:
            raise LightCrawlError(f"Unknown lane: {args.lane}")
        decision.lane = args.lane
        decision.confidence = 1.0
        decision.reasons.append("manual lane override by the operator")
    if args.delivery:
        decision.delivery = args.delivery
        decision.reasons.append("manual delivery override by the operator")
    write_json(store.route_file, decision.to_dict())
    artifact = store.add_artifact(store.route_file, 'route')
    store.advance(
        Phase.ROUTED if PHASE_ORDER.index(Phase(store.state.phase)) < PHASE_ORDER.index(Phase.ROUTED) else store.state.phase,
        f"routed to {decision.lane} ({decision.delivery}, confidence {decision.confidence:.2f})",
        lane=decision.lane,
        delivery=decision.delivery,
    )
    store.add_evidence(
        phase=store.state.phase,
        source="light-crawl router",
        action="decide acquisition lane",
        observation=f"lane={decision.lane}; delivery={decision.delivery}; confidence={decision.confidence:.2f}",
        inference="; ".join(decision.reasons),
        confidence="high" if decision.confidence >= 0.8 else "medium",
        artifact=artifact,
    )
    if args.json:
        print(_json({"case": store.summary(), "route": decision.to_dict()}))
    else:
        print(f"Route: {decision.lane} · delivery={decision.delivery} · confidence={decision.confidence:.2f}")
        for reason in decision.reasons:
            print(f"  - {reason}")
        print("Next actions:")
        for index, action in enumerate(decision.next_actions, 1):
            print(f"  {index}. {action}")
        print(f"Next: light-crawl report {store.directory}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    store = _case(args)
    payload = store.summary()
    payload["has_probe"] = store.probe_file.exists()
    payload["has_route"] = store.route_file.exists()
    payload["has_report"] = store.report_file.exists()
    if args.json:
        print(_json(payload))
        return 0
    print(f"Case:       {payload['case_id']}")
    print(f"Directory:  {payload['directory']}")
    print(f"Phase:      {payload['phase']}")
    print(f"Lane:       {payload['lane'] or '-'}")
    print(f"Delivery:   {payload['delivery'] or '-'}")
    print(f"Evidence:   {payload['evidence_count']}")
    print(f"Artifacts:  {payload['artifacts']}")
    print(f"Probe:      {'yes' if payload['has_probe'] else 'no'}")
    print(f"Route:      {'yes' if payload['has_route'] else 'no'}")
    print(f"Report:     {'yes' if payload['has_report'] else 'no'}")
    if payload["blockers"]:
        print("Blockers:")
        for blocker in payload["blockers"]:
            print(f"  - {blocker}")
    return 0


def _cmd_evidence(args: argparse.Namespace) -> int:
    store = _case(args)
    artifact = args.artifact
    if args.artifact_file:
        artifact = store.add_artifact(Path(args.artifact_file), label=args.artifact or Path(args.artifact_file).name)
    entry = store.add_evidence(
        phase=args.phase or store.state.phase,
        source=args.source,
        action=args.action,
        observation=args.observation,
        inference=args.inference,
        confidence=args.confidence,
        artifact=artifact,
    )
    if args.json:
        print(_json(entry.to_dict()))
    else:
        print(f"Evidence {entry.evidence_id} recorded.")
    return 0


def _cmd_advance(args: argparse.Namespace) -> int:
    store = _case(args)
    store.advance(Phase(args.phase), args.note or f"advanced to {args.phase}")
    if args.json:
        print(_json(store.summary()))
    else:
        print(f"Phase: {store.state.phase}")
        print(f"Case:  {store.directory.resolve()}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    store = _case(args)
    if args.run_check:
        run_check(store, args.run_check, args.timeout)
    report = verify_case(store.directory)
    if args.json:
        print(_json(report.to_dict()))
    else:
        print(format_report(report))
    return 0 if report.ok else 1


def _cmd_report(args: argparse.Namespace) -> int:
    store = _case(args)
    path = write_report(store)
    if args.json:
        print(_json({"report": str(path.resolve()), "case": store.summary()}))
    else:
        print(f"Report written: {path.resolve()}")
    return 0


def _cmd_learn(args: argparse.Namespace) -> int:
    store = _case(args)
    path = learn_case(
        store,
        Path(args.sites_root),
        domain=args.domain or None,
        force=args.force,
    )
    if args.json:
        print(_json({"site_pack": str(path.resolve()), "case": store.summary()}))
    else:
        print(f"Site pack: {path.resolve()}")
    return 0


def _cmd_site(args: argparse.Namespace) -> int:
    if args.site_action == "list":
        root = Path(args.root) if args.root else _default_site_root()
        packs = list_site_packs(root, stale_days=args.stale_days)
        if args.json:
            print(_json([pack.to_dict() for pack in packs]))
        else:
            for pack in packs:
                expected = "-" if pack.expected_items is None else pack.expected_items
                state = "STALE" if pack.stale else "ok"
                verified = pack.last_verified_at[:10] if pack.last_verified_at else "never"
                print(
                    f"{pack.domain:<24} {pack.lane:<12} s{pack.schema_version} v{pack.version} items={expected:<4} "
                    f"verified={verified:<10} {state:<5} "
                    f"spider={'yes' if pack.has_spider else 'no':<3} "
                    f"verify={'yes' if pack.has_verify else 'no':<3} {pack.path}"
                )
        return 0

    if args.site_action == "show":
        info = read_site_pack_info(_resolve_pack(args.pack))
        if args.json:
            print(_json(info.to_dict()))
        else:
            for key, value in info.to_dict().items():
                print(f"{key}: {value}")
        return 0

    if args.site_action == "migrate":
        if args.all:
            root = Path(args.root) if args.root else _default_site_root()
            packs = [pack.path for pack in list_site_packs(root)]
        elif args.pack:
            packs = [_resolve_pack(args.pack)]
        else:
            raise LightCrawlError("Pass a pack path or --all.")
        results = [migrate_site_pack(pack, write=args.write) for pack in packs]
        if args.json:
            print(_json(results))
        else:
            for result in results:
                state = "changed" if result["changed"] else "current"
                wrote = "written" if result["wrote"] else "dry-run"
                print(f"{result['pack']}  {state}  {wrote}")
        return 0

    if args.site_action == "check":
        result = check_site_pack(_resolve_pack(args.pack), write=args.write, timeout=args.timeout)
        if args.json:
            print(_json(result))
        else:
            print(f"Pack:   {result['pack']}")
            print(f"Result: {'PASS' if result['passed'] else 'FAIL'}")
            print(f"Time:   {result['elapsed_ms']} ms")
            if result["wrote_timestamp"]:
                print("Updated: last_verified_at")
            if not result["passed"]:
                print(result["stderr_tail"])
        return 0 if result["passed"] else 1

    if args.site_action != "run":
        raise LightCrawlError(f"Unknown site action: {args.site_action}")
    pack = _resolve_pack(args.pack)
    output = Path(args.out) if args.out else default_output(pack)
    result = run_site_pack(
        pack,
        output=output,
        max_pages=args.max_pages,
        crawldir=Path(args.crawldir) if args.crawldir else None,
        verify=not args.skip_verify,
        timeout=args.timeout,
    )
    if args.json:
        print(_json(result.to_dict()))
    else:
        print(f"Pack:   {result.pack}")
        print(f"Output: {result.output}")
        print(f"Items:  {result.items}")
        print(f"Verify: {result.verify_returncode if result.verify_returncode is not None else 'skipped'}")
        if not result.passed and result.stderr.strip():
            print(f"Stderr: {result.stderr.strip()[-1000:]}")
        print(f"Result: {'PASS' if result.passed else 'FAIL'}")
    return 0 if result.passed else 1


def _cmd_metrics(args: argparse.Namespace) -> int:
    store = _case(args)
    if args.metrics_action == "record":
        payload = record_metrics(
            store,
            items=args.items,
            requests=args.requests,
            browser_seconds=args.browser_seconds,
            tokens=args.tokens,
            success_rate=args.success_rate,
            drift_recovery=args.drift_recovery,
            note=args.note,
        )
        if args.json:
            print(_json(payload))
        else:
            print(f"Metrics recorded for {store.state.slug}")
            for key, value in payload.items():
                print(f"  {key}: {value}")
        return 0
    if args.metrics_action == "show":
        payload = show_metrics(store)
        if args.json:
            print(_json(payload))
        elif not payload:
            print("No metrics recorded.")
        else:
            for key, value in payload.items():
                print(f"{key}: {value}")
        return 0
    raise LightCrawlError(f"Unknown metrics action: {args.metrics_action}")


def _cmd_session(args: argparse.Namespace) -> int:
    broker = SessionBroker(Path(args.root))
    action = args.session_action

    if action == "status":
        if args.profile:
            payload = broker.status(args.profile)
            if args.json:
                print(_json(payload))
            else:
                print(f"Profile: {payload['profile']}")
                print(f"  owned:  {payload['owned']}")
                print(f"  active: {payload.get('active', False)}")
                if payload["owned"]:
                    print(f"  owner:  {payload['owner']}")
                    print(f"  pid:    {payload['pid']}")
                    print(f"  until:  {payload['expires_at']:.0f}")
            return 0
        locks = broker.list()
        payload = [lock.to_dict() | {"expired": lock.expired} for lock in locks]
        if args.json:
            print(_json(payload))
        elif not payload:
            print("No profile locks.")
        else:
            for lock in locks:
                state = "stale" if lock.expired else "active"
                print(f"{lock.profile:<28} {state:<7} owner={lock.owner} pid={lock.pid}")
        return 0

    if action == "acquire":
        try:
            lock = broker.acquire(
                args.profile,
                args.owner,
                ttl_seconds=max(60, args.ttl),
                metadata={"note": args.note} if args.note else {},
                force=args.force,
            )
        except SessionConflict as error:
            print(f"light-crawl: {error}", file=sys.stderr)
            return 3
        payload = lock.to_dict() | {"expired": lock.expired}
        if args.json:
            print(_json(payload))
        else:
            print(f"Acquired profile: {lock.profile}")
            print(f"  owner: {lock.owner}")
            print(f"  until: {lock.expires_at:.0f}")
        return 0

    if action == "release":
        try:
            released = broker.release(args.profile, args.owner)
        except SessionConflict as error:
            print(f"light-crawl: {error}", file=sys.stderr)
            return 3
        payload = {"profile": args.profile, "released": released}
        if args.json:
            print(_json(payload))
        else:
            print(f"Released: {args.profile}" if released else f"No lock: {args.profile}")
        return 0

    if action == "cleanup":
        removed = broker.cleanup()
        if args.json:
            print(_json({"removed": removed}))
        else:
            print(f"Removed {len(removed)} expired lock(s).")
        return 0

    raise LightCrawlError(f"Unknown session action: {action}")


def _cmd_adapters(args: argparse.Namespace) -> int:
    payload = {
        "scrapling": {
            "available": scrapling.available(),
            "path": scrapling.find_cli(),
            "version": scrapling.version(),
            "install": scrapling.install_hint(),
        },
        "js_reverse": {
            "available": js_reverse.available(),
            "path": js_reverse.find_binary(),
            "version": js_reverse.version(),
            "configured_in": js_reverse.configured_in(),
            "tools": len(js_reverse.TOOL_NAMES),
            "install": js_reverse.install_hint(),
        },
        "rea": {
            "available": rea.available(),
            "path": rea.find_cli(),
            "wrapper": str(rea.wrapper_path()),
            "wrapper_available": rea.wrapper_available(),
            "skill": str(rea.skill_path()),
            "skill_installed": rea.skill_path().exists(),
            "configured_in": rea.configured_in(),
            "install": rea.install_hint(),
        },
    }
    if args.json:
        print(_json(payload))
        return 0
    for name, item in payload.items():
        marker = "ok" if item.get("available") else "warn"
        print(f"[{marker}] {name}")
        for key, value in item.items():
            if key == "available":
                continue
            print(f"    {key}: {value}")
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    cases_root = Path(args.cases) if args.cases else _default_benchmark_root()
    summary = run_benchmark(cases_root, Path(args.source_cases))
    json_path, report_path = write_benchmark(summary, Path(args.out))
    if args.json:
        print(_json(summary))
    else:
        print(f"Routing accuracy: {summary['passed']}/{summary['total']} ({summary['accuracy'] * 100:.1f}%)")
        for result in summary["results"]:
            mark = "PASS" if result["passed"] else "FAIL"
            print(
                f"  [{mark}] {result['slug']:<24} "
                f"{result['actual_lane']:<12} confidence={result['actual_confidence']:.2f}"
            )
        print(f"Results: {json_path.resolve()}")
        print(f"Report:  {report_path.resolve()}")
    return 0 if summary["passed"] == summary["total"] else 1


def _cmd_demo(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if out.exists() and not args.force:
        raise LightCrawlError(f"Demo already exists: {out}. Use --force to replace it.")
    if out.exists():
        shutil.rmtree(out)
    ensure_dir(out.parent)
    target = TargetProfile(
        url="https://example.com/demo",
        kind="web",
        volume=250,
        authorized=True,
        notes="OFFLINE DEMO — synthetic data, no live request.",
        demo=True,
    )
    store = CaseStore.create(out.parent, out.name, target, force=True)
    probe = ProbeResult(
        url=target.url,
        final_url=target.url,
        status=200,
        content_type="text/html; charset=utf-8",
        elapsed_ms=42,
        bytes_read=28400,
        title="Example demo catalogue",
        lang="en",
        page_kind=PageKind.STATIC_HTML.value,
        script_count=3,
        inline_script_bytes=1800,
        form_count=1,
        visible_text_chars=1200,
        api_candidates=["https://example.com/api/items?page=1"],
        signature_hints=[],
        body_preview="Synthetic demo page with a server-rendered catalogue and a JSON API candidate.",
    )
    write_json(store.probe_file, probe.to_dict())
    store.advance(Phase.PROBED, "offline demo probe")
    store.add_evidence(
        phase=Phase.PROBED.value,
        source="demo",
        action="synthetic probe",
        observation="status=200; static_html; 1200 text chars; one API candidate",
        inference="L0 is plausible, but the demo does not prove a live site",
        confidence="low",
        artifact=str(store.probe_file),
    )
    decision = decide_route(probe, target)
    write_json(store.route_file, decision.to_dict())
    store.advance(Phase.ROUTED, "offline demo route", lane=decision.lane, delivery=decision.delivery)
    store.add_evidence(
        phase=Phase.ROUTED.value,
        source="demo",
        action="synthetic route",
        observation=f"lane={decision.lane}; delivery={decision.delivery}",
        inference="demo only",
        confidence="low",
        artifact=str(store.route_file),
    )
    report_path = write_report(store)
    if args.json:
        print(_json({"case": store.summary(), "report": str(report_path.resolve())}))
    else:
        print(f"Demo case: {store.directory.resolve()}")
        print(f"Report:    {report_path.resolve()}")
        print("Note: synthetic data; this is a contract demo, not a live crawl.")
    return 0


def _utf8_stdio() -> None:
    """Keep help and reports readable on Windows consoles with legacy code pages."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == 'dataset':
            result = (export_dataset(_case(args), Path(args.spec), Path(args.out))
                if args.dataset_action == 'export' else check_dataset(Path(args.manifest)))
            print(_json(result))
            return 0 if result['ok'] else 1
        if args.command == "doctor":
            return _cmd_doctor(args)
        if args.command == "new-case":
            return _cmd_new_case(args)
        if args.command == "probe":
            return _cmd_probe(args)
        if args.command == "capture":
            return _cmd_capture(args)
        if args.command == "route":
            return _cmd_route(args)
        if args.command == "status":
            return _cmd_status(args)
        if args.command == "evidence":
            return _cmd_evidence(args)
        if args.command == "advance":
            return _cmd_advance(args)
        if args.command == "verify":
            return _cmd_verify(args)
        if args.command == "report":
            return _cmd_report(args)
        if args.command == "learn":
            return _cmd_learn(args)
        if args.command == "site":
            return _cmd_site(args)
        if args.command == "metrics":
            return _cmd_metrics(args)
        if args.command == "session":
            return _cmd_session(args)
        if args.command == "adapters":
            return _cmd_adapters(args)
        if args.command == "benchmark":
            return _cmd_benchmark(args)
        if args.command == "demo":
            return _cmd_demo(args)
        parser.error(f"Unknown command: {args.command}")
    except LightCrawlError as error:
        print(f"light-crawl: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("light-crawl: interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
