"""Study-level 2x2 risk evidence; analysis is separate from drawing.

No pooling, tests, weighting, correction, or design/causal inference is implied.
The log-Wald approximation assumes independent binomial arms. Zero-event rows
remain in the output with arm risks, but have unavailable log-Wald RR intervals.
Sources/methods: metadat dat.bcg; metafor escalc(RR, add=0); NIST Wilson score CI.
"""
from __future__ import annotations

import math
from statistics import NormalDist
import numpy as np
import pandas as pd


def _real_array(values, field):
    """Reject complex/Boolean observations before any potentially lossy cast."""
    raw = np.asarray(values, dtype=object)
    if any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in raw.flat):
        raise ValueError(f"{field} require real numeric values, never complex or Boolean inputs")
    try:
        return np.asarray(values, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} require real numeric values") from exc


def _real_scalar(value, field):
    values = _real_array(value, field)
    if values.ndim != 0:
        raise ValueError(f"{field} require a real numeric scalar")
    return values.item()


def _identity(frame, id_col, label_col):
    if not isinstance(frame, pd.DataFrame) or frame.empty or id_col not in frame or label_col not in frame:
        raise ValueError("Nonempty data with explicit ID and label columns required")
    if frame.columns.duplicated().any():
        raise ValueError("Unique input column names required; resolve duplicate source fields explicitly")
    if frame[[id_col, label_col]].isna().any().any():
        raise ValueError("Study IDs and labels must not be missing")
    ids = frame[id_col].map(str)
    if ids.str.strip().eq("").any() or ids.duplicated().any():
        raise ValueError("Study IDs must be unique and nonempty")
    if frame[label_col].map(str).str.strip().eq("").any():
        raise ValueError("Study labels must be nonempty")
    return ids


def align_studies(frame, order, *, id_col="study_id", label_col="label"):
    """Reorder complete rows by unique IDs, never labels or position alone."""
    ids = _identity(frame, id_col, label_col)
    requested = list(map(str, order))
    if len(requested) != len(set(requested)) or set(requested) != set(ids):
        raise ValueError("Order must contain every study ID exactly once")
    result = frame.copy()
    result[id_col] = ids
    return result.set_index(id_col, drop=False).loc[requested].reset_index(drop=True)


def _counts(frame, columns):
    if len(columns) != 4 or len(set(columns)) != 4 or any(c not in frame for c in columns):
        raise ValueError("Four distinct observed count columns required")
    counts = _real_array(frame[list(columns)], "Counts")
    if (not np.isfinite(counts).all() or (counts < 0).any()
            or (counts != np.floor(counts)).any() or (counts > 2**52).any()):
        raise ValueError("Counts must be finite, nonnegative exact integers <= 2**52")
    if ((counts[:, 0] + counts[:, 1] <= 0).any()
            or (counts[:, 2] + counts[:, 3] <= 0).any()):
        raise ValueError("Every observed arm needs a positive denominator")
    return counts


def wilson_interval(events, total, *, confidence=0.95):
    """Two-sided uncorrected Wilson score CI for independent Bernoulli data."""
    confidence = _real_scalar(confidence, "Confidence")
    if not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Confidence must lie strictly between zero and one")
    events, total = np.broadcast_arrays(_real_array(events, "Events"), _real_array(total, "Totals"))
    if (not np.isfinite(events).all() or not np.isfinite(total).all()
            or (total <= 0).any() or (events < 0).any() or (events > total).any()
            or (events != np.floor(events)).any() or (total != np.floor(total)).any()):
        raise ValueError("Wilson intervals require integer 0 <= events <= total and total > 0")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = events / total
    den = 1 + z*z/total
    center = (p + z*z/(2*total))/den
    half = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total))/den
    # Exact boundaries protect zero/complete arms from roundoff at 0 and 1.
    return np.where(events == 0, 0., center-half), np.where(events == total, 1., center+half)


def analyze_2x2(frame, *, id_col="study_id", label_col="label",
                counts=("tpos", "tneg", "cpos", "cneg"), confidence=0.95):
    """Return all observed rows, denominators, arm risks, and study RR CIs.

    counts = (numerator events, numerator non-events, comparator events,
    comparator non-events). RR is risk_numerator/risk_comparator, not odds ratio.
    With either event count zero, RR/logRR/CI are unavailable, status explicit;
    no constant is added. Non-event zeros are supported without adjustment.
    Source columns cannot use the derived-output namespace: explicitly rename
    colliding source fields before analysis so IDs and observations are retained.
    """
    ids = _identity(frame, id_col, label_col)
    derived = {"n_numerator", "n_comparator", "log_rr", "variance_log_rr",
               "rr", "rr_low", "rr_high", "rr_status"}
    derived.update("risk_"+arm+suffix for arm in ("numerator", "comparator")
                   for suffix in ("", "_low", "_high"))
    collisions = derived.intersection(frame.columns)
    if collisions:
        raise ValueError("Input columns collide with derived output names: " +
                         ", ".join(sorted(collisions)) +
                         "; explicitly rename the source fields before analysis")
    values = _counts(frame, counts)
    a, b, c, d = values.T
    result = frame.copy().reset_index(drop=True)
    result[id_col] = ids.to_numpy()
    n1, n0 = a+b, c+d
    result["n_numerator"], result["n_comparator"] = n1.astype(np.int64), n0.astype(np.int64)
    for arm, events, total in [("numerator", a, n1), ("comparator", c, n0)]:
        lo, hi = wilson_interval(events, total, confidence=confidence)
        result["risk_"+arm] = events/total
        result["risk_"+arm+"_low"], result["risk_"+arm+"_high"] = lo, hi
    valid = (a > 0) & (c > 0)
    z = NormalDist().inv_cdf((1+confidence)/2)
    log_rr, variance = np.full(len(frame), np.nan), np.full(len(frame), np.nan)
    log_rr[valid] = np.log((a[valid]/n1[valid])/(c[valid]/n0[valid]))
    variance[valid] = (1/a[valid]-1/n1[valid]) + (1/c[valid]-1/n0[valid])
    result["log_rr"], result["variance_log_rr"] = log_rr, variance
    result["rr"] = np.exp(log_rr)
    result["rr_low"], result["rr_high"] = np.exp(log_rr-z*np.sqrt(variance)), np.exp(log_rr+z*np.sqrt(variance))
    result["rr_status"] = np.where(valid, "estimable_log_wald", "unavailable_zero_events")
    result.attrs["methods"] = {"confidence": confidence, "effect": "risk ratio: numerator/comparator",
        "rr_interval": "two-sided log-Wald; independent binomial arms",
        "risk_interval": "two-sided Wilson score; uncorrected",
        "zero_cells": "no continuity correction; either zero-event arm leaves RR unavailable",
        "pooling": "none", "weights": "none", "independent_units": "studies, not arms"}
    return result


def validate_effects(frame, *, effect_scale, reference, id_col="study_id", label_col="label",
                     estimate="rr", lower="rr_low", upper="rr_high", status="rr_status"):
    """Validate explicit RR scale/baseline and interval semantics before drawing."""
    _identity(frame, id_col, label_col)
    expected = {"ratio": 1., "log_ratio": 0.}
    reference = _real_scalar(reference, "Reference")
    if effect_scale not in expected or not math.isfinite(reference) or reference != expected[effect_scale]:
        raise ValueError("RR requires ratio/reference=1 or log_ratio/reference=0")
    if any(c not in frame for c in [estimate, lower, upper]):
        raise ValueError("Effect estimate and both CI columns required")
    a = _real_array(frame[[estimate, lower, upper]], "Effect estimates and CI bounds")
    finite = np.isfinite(a)
    available = finite.all(axis=1)
    absent = np.isnan(a).all(axis=1)
    if not (available | absent).all():
        raise ValueError("Observed effects need finite complete CI bounds")
    if absent.any() and (status not in frame or not frame.loc[absent, status].eq("unavailable_zero_events").all()):
        raise ValueError("Unavailable effects need an explicit zero-event status")
    if ((a[available, 1] > a[available, 0]).any() or (a[available, 2] < a[available, 0]).any()):
        raise ValueError("CI must bracket its estimate")
    if effect_scale == "ratio" and (a[available] <= 0).any():
        raise ValueError("Ratio estimates and bounds must be strictly positive")
    if status in frame and not frame.loc[available, status].eq("estimable_log_wald").all():
        raise ValueError("Observed effects contradict declared availability")
    return available


def forest_panel(ax, frame, *, effect_scale, reference, order=None,
                 id_col="study_id", label_col="label", estimate="rr", lower="rr_low", upper="rr_high",
                 color="#243D4D", limits=None, show_labels=True):
    """Validated RR point/CI column, reusing editorial.estimate_column."""
    from editorial import estimate_column
    ordered = align_studies(frame, frame[id_col] if order is None else order, id_col=id_col, label_col=label_col)
    valid = validate_effects(ordered, effect_scale=effect_scale, reference=reference,
        id_col=id_col, label_col=label_col, estimate=estimate, lower=lower, upper=upper)
    all_bounds = ordered.loc[valid, [lower, upper]].to_numpy(float).ravel()
    ax.set_xscale("log" if effect_scale == "ratio" else "linear")
    if limits is None:
        all_bounds = np.r_[all_bounds, reference]
        if effect_scale == "ratio":
            limits = [all_bounds.min()/1.18, all_bounds.max()*1.18]
        else:
            margin = max(float(np.ptp(all_bounds))*.06, .1)
            limits = [all_bounds.min()-margin, all_bounds.max()+margin]
    limits = _real_array(limits, "Effect limits")
    if (len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]
            or not limits[0] <= reference <= limits[1]
            or (effect_scale == "ratio" and limits[0] <= 0)):
        raise ValueError("Limits must include the RR reference on the declared scale")
    estimate_column(ax, ordered[estimate], ordered[label_col].map(str),
        lower=ordered[lower], upper=ordered[upper], colors=[color]*len(ordered),
        show_labels=show_labels, limits=limits, guide_rows=False)
    ax.axvline(reference, color="#79838A", linestyle=(0, (3, 3)), lw=.7, zorder=0)
    return ordered


def arm_risk_panel(ax, frame, *, risk_scale, order=None, id_col="study_id", label_col="label",
                   arm_labels=("Numerator", "Comparator"), colors=("#0072B2", "#B65323"), limits=None):
    """Two offset arm risks on the same study rows, with explicit risk scale.

    Input fractions are converted to percent for display. Log display requires
    strictly positive CI bounds; choose linear for retained zero-event arms.
    """
    if risk_scale not in {"linear", "log"}:
        raise ValueError("Risk scale must be explicitly linear or log")
    if len(arm_labels) != 2 or len(set(arm_labels)) != 2 or len(colors) != 2:
        raise ValueError("Two distinct arm identities and colors required")
    ordered = align_studies(frame, frame[id_col] if order is None else order, id_col=id_col, label_col=label_col)
    bounds = []
    for arm in ["numerator", "comparator"]:
        cols = ["risk_"+arm, "risk_"+arm+"_low", "risk_"+arm+"_high"]
        if any(c not in ordered for c in cols):
            raise ValueError("Observed arm risks and both CI bounds required")
        a = _real_array(ordered[cols], "Arm risks and CI bounds")
        if (not np.isfinite(a).all() or (a < 0).any() or (a > 1).any()
                or (a[:, 1] > a[:, 0]).any() or (a[:, 2] < a[:, 0]).any()):
            raise ValueError("Arm risks require finite, bracketed intervals within [0,1]")
        if risk_scale == "log" and (a <= 0).any():
            raise ValueError("Zero risk/bound cannot be hidden on a log axis; use linear")
        bounds.extend(a[:, 1:].ravel()*100)
    if limits is None:
        limits = [min(bounds)/1.3, max(bounds)*1.3] if risk_scale == "log" else [0., min(100., max(bounds)*1.08)]
    limits = _real_array(limits, "Risk limits")
    if (len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]
            or min(bounds) < limits[0] or max(bounds) > limits[1]
            or (risk_scale == "log" and limits[0] <= 0)):
        raise ValueError("Risk limits must preserve every CI on the declared scale")
    ax.set_xscale(risk_scale)
    y = np.arange(len(ordered))
    for arm, offset, label, color, marker, fill in zip(
            ["numerator", "comparator"], [-.15, .15], arm_labels, colors, ["o", "s"], [True, False]):
        v = ordered["risk_"+arm].to_numpy()*100
        lo, hi = ordered["risk_"+arm+"_low"].to_numpy()*100, ordered["risk_"+arm+"_high"].to_numpy()*100
        ax.errorbar(v, y+offset, xerr=[v-lo, hi-v], fmt=marker, color=color, ecolor=color,
            mfc=color if fill else "white", mec=color, mew=.75, ms=3.2,
            elinewidth=.85, capsize=1.5, capthick=.7, label=label, zorder=3)
    ax.set_xlim(limits)
    ax.set_ylim(len(ordered)-.5, -.5)
    ax.set_yticks(y, [])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    return ordered
