"""Routing benchmark and cost-metric aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import ProbeResult, TargetProfile
from .router import decide_route
from .state import LightCrawlError
from .utils import ensure_dir, read_json, utc_now, write_json


@dataclass
class BenchmarkCase:
    slug: str
    path: Path
    target: TargetProfile
    probe: ProbeResult
    expected: dict[str, Any]
    metrics: dict[str, Any]
    measured: dict[str, Any]
    source_case: str = ""
    notes: str = ""


@dataclass
class BenchmarkResult:
    slug: str
    expected_lane: str
    actual_lane: str
    expected_delivery: str
    actual_delivery: str
    min_confidence: float
    actual_confidence: float
    passed: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    measured: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


def load_case(path: Path) -> BenchmarkCase:
    data = read_json(path / "case.json")
    probe_data = read_json(path / "probe.json")
    if not data or not probe_data:
        raise LightCrawlError(f"Benchmark case needs case.json and probe.json: {path}")
    target = TargetProfile.from_dict(data.get("target", {}) or {})
    expected = dict(data.get("expected", {}) or {})
    if not expected.get("lane") or not expected.get("delivery"):
        raise LightCrawlError(f"Benchmark expected.lane/delivery missing: {path}")
    measured_data = read_json(path / "measured.json", default={}) or {}
    return BenchmarkCase(
        slug=str(data.get("slug") or path.name),
        path=path,
        target=target,
        probe=ProbeResult.from_dict(probe_data),
        expected=expected,
        metrics=dict(data.get("metrics", {}) or {}),
        measured=dict(measured_data),
        source_case=str(data.get("source_case", "") or ""),
        notes=str(data.get("notes", "")),
    )


def load_cases(root: Path) -> list[BenchmarkCase]:
    root = Path(root)
    if not root.exists():
        raise LightCrawlError(f"Benchmark cases directory not found: {root}")
    cases = [load_case(path) for path in sorted(root.iterdir()) if path.is_dir()]
    if not cases:
        raise LightCrawlError(f"No benchmark cases found under: {root}")
    return cases


def _source_metrics(case: BenchmarkCase, source_root: Path) -> dict[str, Any]:
    """Read actual metrics from a standard case, if it still exists locally."""

    if not case.source_case:
        return {}
    candidates = [
        Path(case.source_case),
        Path(source_root) / case.source_case,
    ]
    for candidate in candidates:
        case_file = candidate / "case.json" if candidate.is_dir() else candidate
        if not case_file.exists():
            continue
        data = read_json(case_file, default={}) or {}
        metrics = data.get("metrics", {}) or {}
        if metrics:
            return dict(metrics)
    return {}


def run_benchmark(cases_root: Path, source_root: Path = Path("cases")) -> dict[str, Any]:
    cases = load_cases(cases_root)
    results: list[BenchmarkResult] = []
    source_measured = 0
    for case in cases:
        decision = decide_route(case.probe, case.target)
        measured = dict(case.measured)
        actual = _source_metrics(case, source_root)
        if actual:
            measured.update(actual)
            source_measured += 1
        expected_lane = str(case.expected["lane"])
        expected_delivery = str(case.expected["delivery"])
        min_confidence = float(case.expected.get("min_confidence", 0.0) or 0.0)
        passed = (
            decision.lane == expected_lane
            and decision.delivery == expected_delivery
            and decision.confidence >= min_confidence
        )
        results.append(
            BenchmarkResult(
                slug=case.slug,
                expected_lane=expected_lane,
                actual_lane=decision.lane,
                expected_delivery=expected_delivery,
                actual_delivery=decision.delivery,
                min_confidence=min_confidence,
                actual_confidence=decision.confidence,
                passed=passed,
                reasons=decision.reasons,
                metrics=case.metrics,
                measured=measured,
                notes=case.notes,
            )
        )

    total = len(results)
    passed_count = sum(1 for result in results if result.passed)
    metric_names = (
        "success_rate",
        "requests_per_item",
        "browser_seconds_per_item",
        "tokens_per_1k_items",
        "drift_recovery_rate",
    )
    averages: dict[str, float | None] = {}
    measured_averages: dict[str, float | None] = {}
    for name in metric_names:
        values = [
            float(result.metrics[name])
            for result in results
            if result.metrics.get(name) is not None
        ]
        averages[name] = round(sum(values) / len(values), 4) if values else None

        measured_values = [
            float(result.measured[name])
            for result in results
            if result.measured.get(name) is not None
        ]
        measured_averages[name] = (
            round(sum(measured_values) / len(measured_values), 4) if measured_values else None
        )

    return {
        "generated_at": utc_now(),
        "cases_root": str(Path(cases_root).resolve()),
        "total": total,
        "passed": passed_count,
        "accuracy": round(passed_count / total, 4) if total else 0.0,
        "averages": averages,
        "measured_averages": measured_averages,
        "measured_from_source_cases": source_measured,
        "results": [
            {
                "slug": result.slug,
                "expected_lane": result.expected_lane,
                "actual_lane": result.actual_lane,
                "expected_delivery": result.expected_delivery,
                "actual_delivery": result.actual_delivery,
                "min_confidence": result.min_confidence,
                "actual_confidence": round(result.actual_confidence, 3),
                "passed": result.passed,
                "reasons": result.reasons,
                "metrics": result.metrics,
                "measured": result.measured,
                "notes": result.notes,
            }
            for result in results
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# light-crawl benchmark",
        "",
        f"> Generated at {summary['generated_at']}",
        f"> Cases: {summary['total']} · Routing accuracy: {summary['passed']}/{summary['total']} "
        f"({summary['accuracy'] * 100:.1f}%)",
        "",
        "## Routing",
        "",
        "| Case | Expected | Actual | Pass | Confidence |",
        "|---|---|---|---|---|",
    ]
    for result in summary["results"]:
        mark = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"| {result['slug']} | {result['expected_lane']} / {result['expected_delivery']} | "
            f"{result['actual_lane']} / {result['actual_delivery']} | {mark} | "
            f"{result['actual_confidence']:.2f} |"
        )
    def metric_table(key: str) -> list[str]:
        rows = [
            "| Case | Success | Req/item | Browser s/item | Tokens/1k | Drift recovery |",
            "|---|---|---|---|---|---|",
        ]
        for result in summary["results"]:
            metrics = result[key]
            if not metrics:
                rows.append(f"| {result['slug']} | - | - | - | - | - |")
                continue
            def value(name: str) -> str:
                raw = metrics.get(name)
                return "-" if raw is None else str(raw)
            rows.append(
                f"| {result['slug']} | {value('success_rate')} | {value('requests_per_item')} | "
                f"{value('browser_seconds_per_item')} | {value('tokens_per_1k_items')} | "
                f"{value('drift_recovery_rate')} |"
            )
        return rows

    lines.extend(
        [
            "",
            "## Reference metrics (budgets)",
            "",
            "These are target budgets attached to the case; a null/absent value is shown as `-`,",
            "not as zero.",
            "",
            *metric_table("metrics"),
            "",
            "## Measured metrics",
            "",
            "Only cases with a `measured.json` file are populated. A dash means the value was",
            "not measured, not that it was zero.",
            "",
            *metric_table("measured"),
            "",
            "## Aggregates",
            "",
            "### Budget",
            "",
            "| Metric | Average |",
            "|---|---|",
        ]
    )
    for name, value in summary["averages"].items():
        lines.append(f"| {name} | {'-' if value is None else value} |")
    lines.extend(
        [
            "",
            "### Measured",
            "",
            "| Metric | Average |",
            "|---|---|",
        ]
    )
    for name, value in summary["measured_averages"].items():
        lines.append(f"| {name} | {'-' if value is None else value} |")
    lines.append("")
    return "\n".join(lines)


def write_benchmark(summary: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir = ensure_dir(Path(out_dir))
    json_path = out_dir / "results.json"
    report_path = out_dir / "report.md"
    write_json(json_path, summary)
    report_path.write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    return json_path, report_path
