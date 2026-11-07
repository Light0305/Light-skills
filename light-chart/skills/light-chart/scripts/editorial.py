"""Physical-size composition and evidence encodings for scientific figures.

Design synthesis: nature-figure evidence architecture, FigMirror compactness /
hairline calibration, and figures4papers benchmark layouts. See notices.
These are composable primitives, not a required layout or statistical pipeline.
"""
from __future__ import annotations

from contextlib import contextmanager
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm, to_rgb
from project_style import project_context, colormap, role, current_project

INK = "#252B32"
MUTED = "#66717D"
BASELINE = "#8B99A6"
BLUE = "#226D8D"
TEAL = "#288C83"
WARM = "#CA7259"
PALE = "#EAF2F5"


@contextmanager
def figure_style(*, font=None, size=None, project=None, lang='en'):
    """Local rc context; final point sizes, not slide-scale sizes."""
    with project_context(project, lang=lang):
        size = current_project()['typography']['base_pt'] if size is None else size
        minimum = current_project()['typography']['minimum_pt']
        if size < minimum:
            raise ValueError('Figure base size is smaller than project minimum')
        family = [font] if font else mpl.rcParams['font.family']
        with mpl.rc_context({
        "font.family": family,
        "font.size": size, "text.color": role('ink'), "axes.labelcolor": role('ink'),
        "axes.edgecolor": role('muted'), "axes.linewidth": .6,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": role('muted'), "ytick.color": role('muted'),
        "xtick.labelcolor": role('ink'), "ytick.labelcolor": role('ink'),
        "xtick.labelsize": size, "ytick.labelsize": size,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "xtick.major.width": .6, "ytick.major.width": .6,
        "xtick.major.pad": 2.5, "ytick.major.pad": 3,
        "legend.frameon": False, "legend.fontsize": size,
        "legend.handlelength": 1.4, "legend.handletextpad": .45,
        "legend.columnspacing": 1, "legend.borderaxespad": 0,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.facecolor": "white", "figure.facecolor": "white",
    }):
            yield


def canvas(size_mm):
    size = np.asarray(size_mm, float)
    if size.shape != (2,) or not np.isfinite(size).all() or (size <= 0).any():
        raise ValueError("size_mm must be two positive finite dimensions")
    return plt.figure(figsize=size / 25.4)


def axes_mm(fig, left, top, width, height, **kwargs):
    """Place a plotting rectangle in mm from the top-left of a fixed page."""
    fw, fh = fig.get_size_inches() * 25.4
    rect = np.asarray([left, top, width, height], float)
    if not np.isfinite(rect).all() or min(width, height) <= 0:
        raise ValueError("invalid axes rectangle")
    if left < 0 or top < 0 or left + width > fw + 1e-8 or top + height > fh + 1e-8:
        raise ValueError("axes rectangle extends outside the page")
    return fig.add_axes([left/fw, 1-(top+height)/fh, width/fw, height/fh], **kwargs)


def text_mm(fig, x, y, text, **kwargs):
    fw, fh = fig.get_size_inches() * 25.4
    if 'fontsize' in kwargs:
        kwargs['fontsize']=max(kwargs['fontsize'],current_project()['typography']['minimum_pt'])
    return fig.text(x/fw, 1-y/fh, text, **{"va": "top", **kwargs})


def panel_heading(fig, letter, title, x, y, *, subtitle=None):
    text_mm(fig, x, y, letter, fontsize=9, fontweight="bold")
    text_mm(fig, x+5, y+.15, title, fontsize=8, fontweight="bold")
    if subtitle:
        text_mm(fig, x+5, y+4.2, subtitle, fontsize=6.8, color=role('muted'))


def estimate_column(ax, values, labels, *, lower=None, upper=None,
                    colors=None, highlight=None, limits=None, ticks=None,
                    show_labels=True, guide_rows=True):
    """One aligned dot/interval column; bounds must be supplied, never inferred.

    NaN estimates create an explicit NA row; bounds for an observed estimate must
    be finite and bracket it. The caller decides ordering, estimand and error type.
    """
    values = np.asarray(values, float)
    if values.shape != (len(labels),) or np.isinf(values).any() or len(labels) == 0:
        raise ValueError("values must match labels and contain no infinity")
    if (lower is None) != (upper is None):
        raise ValueError("provide both bounds or neither")
    valid = np.isfinite(values)
    if lower is not None:
        lower, upper = np.asarray(lower, float), np.asarray(upper, float)
        if lower.shape != values.shape or upper.shape != values.shape:
            raise ValueError("interval dimensions must match estimates")
        if not np.isfinite(lower[valid]).all() or not np.isfinite(upper[valid]).all():
            raise ValueError("observed estimates require finite interval bounds")
        if (lower[valid] > values[valid]).any() or (upper[valid] < values[valid]).any():
            raise ValueError("intervals must bracket estimates")
    colors = list(colors) if colors is not None else [role('baseline')]*len(labels)
    if len(colors) != len(labels):
        raise ValueError("one color is required per row")
    if highlight is not None and (not isinstance(highlight, (int, np.integer)) or not 0 <= highlight < len(labels)):
        raise ValueError("highlight must identify an existing row")
    for index, (value, color) in enumerate(zip(values, colors)):
        if index == highlight:
            ax.axhspan(index-.44, index+.44, color=role('pale'), linewidth=0, zorder=0)
        elif guide_rows:
            ax.axhline(index, color="#E5E9ED", linewidth=.35, zorder=0)
        if np.isfinite(value):
            err = None if lower is None else [[value-lower[index]], [upper[index]-value]]
            ax.errorbar(value, index, xerr=err, fmt="D" if index == highlight else "o",
                        markersize=3.6 if index == highlight else 3.0,
                        color=color, ecolor=color, elinewidth=.85,
                        capsize=1.8, capthick=.7, markeredgewidth=.5, zorder=3)
        else:
            ax.text(.5, index, "NA", transform=ax.get_yaxis_transform(),
                    ha="center", va="center", fontsize=max(6.5,current_project()['typography']['minimum_pt']), color=role('muted'))
    ax.set_ylim(len(labels)-.5, -.5)
    ax.set_yticks(np.arange(len(labels)), labels if show_labels else [])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    if limits is not None:
        if len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]:
            raise ValueError("invalid limits")
        # Refuse to silently hide supplied intervals or values.
        all_values = values[valid] if lower is None else np.r_[lower[valid], upper[valid]]
        if ((all_values < limits[0]) | (all_values > limits[1])).any():
            raise ValueError("limits would clip supplied evidence")
        ax.set_xlim(limits)
    if ticks is not None:
        ax.set_xticks(ticks)
    for index, tick in enumerate(ax.get_yticklabels()):
        tick.set_color(role('ink'))
        if index == highlight:
            tick.set_color(colors[index]); tick.set_fontweight("bold")
    return ax


def component_matrix(ax, included, *, row_labels=None, column_labels=None, highlight=None):
    """Explicit boolean design, open = absent, filled = present."""
    included = np.asarray(included)
    if included.ndim != 2 or not np.isin(included, [0, 1]).all():
        raise ValueError("included must be a boolean / 0–1 design matrix")
    nr, nc = included.shape
    if row_labels is not None and len(row_labels) != nr:
        raise ValueError("row labels do not match design")
    if column_labels is not None and len(column_labels) != nc:
        raise ValueError("column labels do not match design")
    for row in range(nr):
        if row == highlight:
            ax.axhspan(row-.44, row+.44, color=role('pale'), linewidth=0, zorder=0)
        for col in range(nc):
            present = bool(included[row, col])
            ax.plot(col, row, "o", markersize=3.0,
                    markerfacecolor=(role('primary') if row == highlight else role('muted')) if present else "white",
                    markeredgecolor=role('primary') if row == highlight else role('baseline'), markeredgewidth=.6)
    ax.set(xlim=(-.5, nc-.5), ylim=(nr-.5, -.5),
           xticks=np.arange(nc), xticklabels=column_labels or [str(i+1) for i in range(nc)],
           yticks=np.arange(nr), yticklabels=row_labels or [])
    ax.xaxis.tick_top()
    ax.tick_params(length=0, pad=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return ax


def scientific_heatmap(ax, values, rows, columns, *, limits, center=None,
                       cmap=None, fmt=".2f", row_breaks=(), col_breaks=(),
                       highlight_row=None, annotate=True):
    """Grouped matrix with a scientific scale and luminance-aware annotations.

    No clustering, row sorting, normalization or missing-value imputation occurs.
    Returns the mappable; caller allocates the colorbar rectangle explicitly.
    """
    values = np.asarray(values, float)
    if values.shape != (len(rows), len(columns)) or np.isinf(values).any():
        raise ValueError("matrix must match labels; only NaN may denote missingness")
    lo, hi = limits
    if not np.isfinite([lo, hi]).all() or lo >= hi:
        raise ValueError("limits must be finite and increasing")
    if center is not None and not lo < center < hi:
        raise ValueError("center must lie strictly within limits")
    observed = values[np.isfinite(values)]
    if ((observed < lo) | (observed > hi)).any():
        raise ValueError("limits would saturate supplied values; choose an explicit wider scale")
    if cmap is None:
        cmap = colormap(diverging=center is not None)
    cmap = (mpl.colormaps[cmap] if isinstance(cmap, str) else cmap).copy()
    cmap = cmap.with_extremes(bad=role('missing'))
    norm = Normalize(lo, hi) if center is None else TwoSlopeNorm(center, lo, hi)
    image = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
    ax.set(xticks=np.arange(len(columns)), xticklabels=columns,
           yticks=np.arange(len(rows)), yticklabels=rows)
    ax.xaxis.tick_top()
    ax.tick_params(length=0, pad=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if annotate:
        for (row, col), value in np.ndenumerate(values):
            rgb = np.asarray(to_rgb(cmap(norm(value)))) if np.isfinite(value) else np.array([1, 1, 1])
            linear = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
            luminance = float(linear @ [.2126, .7152, .0722])
            # Pick the higher-contrast endpoint, including mid-tone cells where
            # white annotations can look elegant but become hard to read.
            color = "white" if 1.05/(luminance+.05) > (luminance+.05)/.05 else "black"
            ax.text(col, row, "NA" if not np.isfinite(value) else format(value, fmt),
                    ha="center", va="center", fontsize=max(7,current_project()['typography']['minimum_pt']), color=color,
                    fontweight="bold" if row == highlight_row else "normal")
    for edge in row_breaks:
        ax.axhline(edge-.5, color="white", linewidth=2)
    for edge in col_breaks:
        ax.axvline(edge-.5, color="white", linewidth=2)
    if highlight_row is not None:
        if not 0 <= highlight_row < len(rows):
            raise ValueError("highlight row out of range")
        tick = ax.get_yticklabels()[highlight_row]
        tick.set_fontweight("bold"); tick.set_color(role('primary'))
    return image


def raw_groups(ax, groups, labels, colors, *, seed=0, point_size=9):
    """All observations plus quartiles/median; no kernel-smoothed tiny samples.

    Deterministic horizontal jitter changes positions only along the categorical
    axis. Box whiskers use 1.5 IQR; outliers remain visible among the raw points.
    """
    if not len(groups) == len(labels) == len(colors):
        raise ValueError("groups, labels and colors must have equal lengths")
    arrays = [np.asarray(group, float) for group in groups]
    if any(x.ndim != 1 or len(x) == 0 or not np.isfinite(x).all() for x in arrays):
        raise ValueError("groups must be nonempty finite vectors; handle missingness explicitly")
    rng = np.random.default_rng(seed)
    for index, (values, color) in enumerate(zip(arrays, colors)):
        ax.boxplot([values], positions=[index], widths=.48, patch_artist=True,
            showfliers=False, manage_ticks=False,
            boxprops={"facecolor": "white", "edgecolor": color, "linewidth": .8},
            whiskerprops={"color": color, "linewidth": .7},
            capprops={"color": color, "linewidth": .7},
            medianprops={"color": color, "linewidth": 1.2}, zorder=2)
        xx = index + rng.uniform(-.16, .16, len(values))
        ax.scatter(xx, values, s=point_size, facecolor=color, edgecolor="white",
                   linewidth=.3, alpha=.75, zorder=3)
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.set_xlim(-.55, len(labels)-.45)
    return ax


def interval_trajectory(ax, x, mean, lower, upper, *, color, label=None,
                        marker="o", linestyle="-"):
    """Draw supplied estimates at their actual x coordinates, without fitting."""
    for vector in (x, mean, lower, upper):
        raw = np.asarray(vector, dtype=object)
        if np.iscomplexobj(raw) or any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in raw.flat):
            raise ValueError("Trajectory arrays require real numeric observations, not complex or Boolean values")
    x, mean, lower, upper = [np.asarray(v, float) for v in (x, mean, lower, upper)]
    if any(v.ndim != 1 or v.shape != x.shape or not np.isfinite(v).all() for v in [x, mean, lower, upper]):
        raise ValueError("x and all interval arrays must be matching finite vectors")
    if len(np.unique(x)) != len(x) or (lower > mean).any() or (upper < mean).any():
        raise ValueError("x must be unique and intervals must bracket means")
    order = np.argsort(x, kind="stable")
    ax.fill_between(x[order], lower[order], upper[order], color=color, alpha=.13, linewidth=0)
    return ax.plot(x[order], mean[order], color=color, label=label, marker=marker,
                   linestyle=linestyle, markersize=2.6, linewidth=1.1)[0]
