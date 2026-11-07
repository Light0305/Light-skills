"""Render a case report from the artifact bus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Phase
from .state import CaseStore, load_probe, load_route
from .utils import human_bytes, truncate, utc_now
from .validation import checked_receipt


def _cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _status_line(store: CaseStore) -> str:
    phase_index = list(Phase).index(Phase(store.state.phase))
    if phase_index >= list(Phase).index(Phase.VERIFIED):
        try:
            receipt = checked_receipt(store.directory)
        except (ValueError, OSError, TypeError, KeyError) as error:
            return f'Not currently verified: {error}'
        if receipt is None:
            return 'Phase marked VERIFIED or later, but no executed check receipt exists. Structural checks alone do not prove a replay or live sample passed.'
        return 'Selected controlled check passed against the recorded code and fixtures. Live coverage, completeness and scientific suitability require separate evidence.'
    if phase_index >= list(Phase).index(Phase.BUILT):
        return "Built, but not yet verified. Do not treat the spider as production-ready."
    if phase_index >= list(Phase).index(Phase.REPRODUCED):
        return "Signature or request replay reproduced locally; the spider is not built yet."
    return "Not verified. This case is still in discovery."


def _probe_section(store: CaseStore) -> str:
    try:
        probe = load_probe(store)
    except Exception:
        return "No probe yet. Run `light-crawl probe <case>`."
    rows = [
        ("Status", probe.status),
        ("Final URL", probe.final_url or probe.url),
        ("Content type", probe.content_type or "unknown"),
        ("Page kind", probe.page_kind),
        ("Visible text", f"{probe.visible_text_chars} chars"),
        ("Scripts", probe.script_count),
        ("Inline script bytes", probe.inline_script_bytes),
        ("Forms", probe.form_count),
        ("Cloudflare headers", "yes" if probe.cloudflare else "no"),
        ("Challenge markers", "yes" if probe.challenge else "no"),
        ("CAPTCHA markers", "yes" if probe.captcha else "no"),
        ("Elapsed", f"{probe.elapsed_ms} ms"),
        ("Bytes read", human_bytes(probe.bytes_read)),
    ]
    table = "\n".join(f"| {_cell(key)} | {_cell(value)} |" for key, value in rows)
    apis = "\n".join(f"- `{item}`" for item in probe.api_candidates) or "- none detected"
    hints = ", ".join(probe.signature_hints) or "none"
    return f"""| Field | Value |
|---|---|
{table}

**API candidates**

{apis}

**Signature hints:** {hints}

**Body preview**

> {truncate(probe.body_preview, 500)}
"""


def _route_section(store: CaseStore) -> str:
    try:
        route = load_route(store)
    except Exception:
        return "No route yet. Run `light-crawl route <case>`."
    reasons = "\n".join(f"- {item}" for item in route.reasons) or "- none"
    actions = "\n".join(f"{index}. {item}" for index, item in enumerate(route.next_actions, 1)) or "1. Continue with the selected lane."
    tools = "\n".join(f"- `{item}`" for item in route.tools) or "- none"
    stops = "\n".join(f"- {item}" for item in route.stop_conditions) or "- none"
    return f"""- **Lane:** `{route.lane}`
- **Delivery:** `{route.delivery}`
- **Confidence:** `{route.confidence:.2f}`

**Why this route**

{reasons}

**Next actions**

{actions}

**Tools**

{tools}

**Stop conditions**

{stops}
"""


def _evidence_section(store: CaseStore) -> str:
    entries = store.evidence()
    if not entries:
        return "No evidence recorded yet. Use `light-crawl evidence ...` after each meaningful observation."
    lines = [
        "| ID | Phase | Source | Observation | Inference | Confidence | Artifact |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in entries:
        lines.append(
            "| {id} | {phase} | {source} | {observation} | {inference} | {confidence} | {artifact} |".format(
                id=_cell(entry.get("evidence_id")),
                phase=_cell(entry.get("phase")),
                source=_cell(entry.get("source")),
                observation=_cell(truncate(entry.get("observation", ""), 500)),
                inference=_cell(truncate(entry.get("inference", ""), 500)),
                confidence=_cell(entry.get("confidence", "")),
                artifact=_cell(entry.get("artifact", "")),
            )
        )
    return "\n".join(lines)


def _artifacts_section(store: CaseStore) -> str:
    if not store.state.artifacts:
        return "No artifacts recorded."
    lines = ["| Path | Label | Size | SHA-256 |", "|---|---|---|---|"]
    for path, meta in sorted(store.state.artifacts.items()):
        digest = str(meta.get("sha256", ""))[:16]
        lines.append(
            f"| `{_cell(path)}` | {_cell(meta.get('label', ''))} | {human_bytes(meta.get('bytes', 0))} | `{digest}` |"
        )
    return "\n".join(lines)


def _metrics_section(store: CaseStore) -> str:
    if not store.state.metrics:
        return "No metrics recorded."
    lines = ["| Metric | Value |", "|---|---|"]
    for key, value in sorted(store.state.metrics.items()):
        lines.append(f"| {_cell(key)} | {_cell(value)} |")
    return "\n".join(lines)


def render_report(store: CaseStore) -> str:
    route = None
    try:
        route = load_route(store)
    except Exception:
        pass

    next_actions = "\n".join(f"{i}. {item}" for i, item in enumerate(route.next_actions, 1)) if route else (
        "1. Confirm authorization in `scope.md`.\n"
        "2. Run `light-crawl probe <case>`.\n"
        "3. Run `light-crawl route <case>`."
    )

    blockers = "\n".join(f"- {item}" for item in store.state.blockers) or "- none recorded"
    limitations = [
        "The HTTP probe does not execute JavaScript; a JS shell may be classified as dynamic, not wrong.",
        "A route is a hypothesis with a confidence score, not a finding.",
        "An observation is not an inference. Inferences are marked separately in the evidence ledger.",
        "A built spider is not a production spider until it passes fixture and live verification.",
        "The report never proves authorization, robots compliance, or Terms of Service compliance.",
    ]
    if store.target.demo:
        limitations.append("This is an offline demo case with synthetic probe data; it does not contact a live target.")

    return f"""# light-crawl report — {store.state.slug}

> Generated at {utc_now()} by `light-crawl report`.
> Phase: **{store.state.phase}** · Lane: **{store.state.lane or "unrouted"}** · Delivery: **{store.state.delivery or "unknown"}**

## 1. Status

{_status_line(store)}

## 2. Target

| Field | Value |
|---|---|
| URL | `{_cell(store.target.url)}` |
| Kind | `{_cell(store.target.kind)}` |
| Volume | {_cell(store.target.volume)} |
| Auth | `{_cell(store.target.auth)}` |
| Geography | `{_cell(store.target.geo or "unspecified")}` |
| Authorized | {_cell(store.target.authorized)} |
| Demo | {_cell(store.target.demo)} |

## 3. Probe

{_probe_section(store)}

## 4. Route

{_route_section(store)}

## 5. Evidence ledger

{_evidence_section(store)}

## 6. Artifacts

{_artifacts_section(store)}

## 7. Metrics

{_metrics_section(store)}

## 8. Blockers

{blockers}

## 9. Next actions

{next_actions}

## 10. Limitations and unknowns

{chr(10).join(f"- {item}" for item in limitations)}
"""


def write_report(store: CaseStore) -> Path:
    store.reports_dir.mkdir(parents=True, exist_ok=True)
    store.report_file.write_text(render_report(store), encoding="utf-8", newline="\n")
    return store.report_file
