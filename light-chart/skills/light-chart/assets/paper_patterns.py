"""Adapted figures4papers patterns; see THIRD_PARTY_NOTICES.md (CC BY-NC 4.0).

Functions consume caller data, do not run tests, and do not write files.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from project_style import colors_for, colormap

COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]


def comparison_bars(methods, metrics, values, errors=None, *, colors=None, size_mm=(180, 85)):
    values = np.asarray(values, dtype=float)
    if values.shape != (len(methods), len(metrics)) or not np.isfinite(values).all():
        raise ValueError("values must be a finite methods-by-metrics matrix")
    if errors is not None:
        errors = np.asarray(errors, dtype=float)
        if errors.shape != values.shape or not np.isfinite(errors).all() or (errors < 0).any():
            raise ValueError("errors must be finite, non-negative and match values")
    colors = list(colors) if colors is not None else colors_for(methods)
    if len(methods) > len(colors):
        raise ValueError("provide one distinguishable color per method")
    fig, all_axes = plt.subplots(1, len(metrics) + 1, figsize=np.asarray(size_mm)/25.4,
                                 layout="constrained", gridspec_kw={"width_ratios": [1]*len(metrics)+[0.8]})
    axes = list(np.atleast_1d(all_axes))
    for index, metric in enumerate(metrics):
        ax = axes[index]
        ax.bar(np.arange(len(methods)), values[:, index],
               yerr=errors[:, index] if errors is not None else None,
               color=colors[:len(methods)], capsize=2, error_kw={"linewidth": 0.8})
        ax.set(xticks=[], ylabel=str(metric))
    handles = [Line2D([], [], marker="s", linestyle="none", color=color, label=label)
               for color, label in zip(colors, methods)]
    axes[-1].legend(handles=handles, loc="center left", frameon=False)
    axes[-1].set_axis_off()
    return fig, axes[:-1]


def trend_lines(x, values, labels, lower=None, upper=None, *, colors=None, size_mm=(150, 95)):
    for vector in [x, values, *([lower, upper] if lower is not None and upper is not None else [])]:
        raw = np.asarray(vector, dtype=object)
        if np.iscomplexobj(raw) or any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in raw.flat):
            raise ValueError("Trajectory arrays require real numeric observations, not complex or Boolean values")
    x, values = np.asarray(x, dtype=float), np.asarray(values, dtype=float)
    if x.ndim != 1 or len(np.unique(x)) != len(x) or not np.isfinite(x).all():
        raise ValueError("x must contain unique finite continuous coordinates")
    if values.shape != (len(labels), len(x)) or not np.isfinite(values).all():
        raise ValueError("values must be a finite series-by-x matrix")
    if (lower is None) != (upper is None):
        raise ValueError("provide both interval bounds")
    if lower is not None:
        lower, upper = np.asarray(lower, float), np.asarray(upper, float)
        if lower.shape != values.shape or upper.shape != values.shape or not np.isfinite(lower).all() or not np.isfinite(upper).all() or (lower > values).any() or (upper < values).any():
            raise ValueError("finite interval bounds must bracket each value")
    colors = list(colors) if colors is not None else colors_for(labels)
    if len(labels) > len(colors):
        raise ValueError("provide a distinguishable color per series")
    order = np.argsort(x, kind="stable")
    fig, ax = plt.subplots(figsize=np.asarray(size_mm)/25.4, layout="constrained")
    for index, label in enumerate(labels):
        ax.plot(x[order], values[index, order], color=colors[index], marker=["o", "s", "^", "D"][index % 4],
                linestyle=["-", "--", "-.", ":"][index % 4], label=label, linewidth=1.3, markersize=4)
        if lower is not None:
            ax.fill_between(x[order], lower[index, order], upper[index, order], color=colors[index], alpha=0.12)
    return fig, ax


def annotated_heatmap(values, row_labels, column_labels, *, label="Value", cmap=None, size_mm=(150, 100)):
    values = np.asarray(values, dtype=float)
    if values.shape != (len(row_labels), len(column_labels)) or np.isinf(values).any():
        raise ValueError("matrix shape must match labels; only NaN is allowed for missing cells")
    palette = plt.get_cmap(cmap).copy() if cmap else colormap()
    palette = palette.with_extremes(bad="#EEEEEE")
    fig, ax = plt.subplots(figsize=np.asarray(size_mm)/25.4, layout="constrained")
    image = ax.imshow(np.ma.masked_invalid(values), cmap=palette, aspect="auto")
    fig.colorbar(image, ax=ax, label=label, shrink=0.85, pad=0.04)
    ax.set(xticks=np.arange(len(column_labels)), yticks=np.arange(len(row_labels)),
           xticklabels=list(column_labels), yticklabels=list(row_labels))
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            text = "NA" if np.isnan(value) else f"{value:g}"
            color = "white" if np.isfinite(value) and image.norm(value) > 0.6 else "#222222"
            ax.text(column, row, text, ha="center", va="center", color=color, fontsize=8)
    return fig, ax
