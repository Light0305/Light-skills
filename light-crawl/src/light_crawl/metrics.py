"""Record actual run metrics on a case."""

from __future__ import annotations

from typing import Any

from .state import CaseStore, LightCrawlError
from .utils import utc_now


METRIC_KEYS = (
    "items",
    "requests",
    "browser_seconds",
    "tokens",
    "success_rate",
    "drift_recovery_rate",
    "requests_per_item",
    "browser_seconds_per_item",
    "tokens_per_1k_items",
    "metrics_recorded_at",
    "metrics_note",
)


def record_metrics(
    store: CaseStore,
    *,
    items: int,
    requests: int,
    browser_seconds: float,
    tokens: int,
    success_rate: float,
    drift_recovery: float,
    note: str = "",
) -> dict[str, Any]:
    if items <= 0:
        raise LightCrawlError("items must be greater than zero to compute per-item metrics.")
    if requests < 0 or browser_seconds < 0 or tokens < 0:
        raise LightCrawlError("requests, browser_seconds and tokens must be non-negative.")
    if not 0 <= success_rate <= 1:
        raise LightCrawlError("success_rate must be between 0 and 1.")
    if not 0 <= drift_recovery <= 1:
        raise LightCrawlError("drift_recovery must be between 0 and 1.")

    metrics = {
        "items": int(items),
        "requests": int(requests),
        "browser_seconds": float(browser_seconds),
        "tokens": int(tokens),
        "success_rate": round(float(success_rate), 4),
        "drift_recovery_rate": round(float(drift_recovery), 4),
        "requests_per_item": round(requests / items, 4),
        "browser_seconds_per_item": round(browser_seconds / items, 4),
        "tokens_per_1k_items": round(tokens / items * 1000, 1),
        "metrics_recorded_at": utc_now(),
        "metrics_note": note,
    }
    store.state.metrics.update(metrics)
    store.save()
    store.add_evidence(
        phase=store.state.phase,
        source="light-crawl metrics",
        action="record run metrics",
        observation=(
            f"items={items}; requests={requests}; browser_seconds={browser_seconds}; "
            f"tokens={tokens}; success_rate={success_rate}; drift_recovery={drift_recovery}"
        ),
        inference="per-item cost and quality metrics recorded for the benchmark",
        confidence="high",
    )
    return metrics


def show_metrics(store: CaseStore) -> dict[str, Any]:
    return {key: store.state.metrics[key] for key in METRIC_KEYS if key in store.state.metrics}
