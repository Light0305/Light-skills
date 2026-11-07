from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .normalize import now_iso

STATUS_SCORE = {
    "ok": 1.0,
    "empty": 0.75,
    "rate_limited": 0.1,
    "blocked": 0.0,
    "auth_required": 0.0,
    "error": 0.0,
    "skipped": 0.0,
}


def _path(cache_dir: str | Path) -> Path:
    return Path(cache_dir) / "source_health.json"


def load_health(cache_dir: str | Path) -> dict[str, dict[str, Any]]:
    data = read_json(_path(cache_dir), {}) or {}
    return data.get("sources", {}) or {}


def update_health(
    cache_dir: str | Path,
    source_runs: list[dict[str, Any]],
    *,
    alpha: float = 0.3,
) -> dict[str, dict[str, Any]]:
    """Update a persistent EWMA health score per source.

    The score is a reliability signal, not a quality judgment. It is used to
    down-weight a source's agreement contribution when it is blocked or flaky.
    """
    state = load_health(cache_dir)
    grouped: dict[str, list[str]] = defaultdict(list)
    for run in source_runs:
        source = str(run.get("source", ""))
        status = str(run.get("status", ""))
        if source:
            grouped[source].append(status)
    for source, statuses in grouped.items():
        run_score = 100.0 * sum(STATUS_SCORE.get(s, 0.0) for s in statuses) / max(1, len(statuses))
        previous = state.get(source, {}).get("score")
        score = run_score if previous is None else alpha * run_score + (1 - alpha) * float(previous)
        state[source] = {
            "score": round(score, 1),
            "runs": int(state.get(source, {}).get("runs", 0)) + len(statuses),
            "last_status": statuses[-1] if statuses else "",
            "updated_at": now_iso(),
        }
    try:
        write_json(_path(cache_dir), {"sources": state, "updated_at": now_iso()})
    except OSError:
        pass
    return state


def health_weights(state: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {source: float(record.get("score", 50.0)) / 100.0 for source, record in state.items()}
