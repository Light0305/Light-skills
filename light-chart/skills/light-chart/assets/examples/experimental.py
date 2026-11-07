"""Six-panel evidence figure, using explicitly simulated subject-level data.

No files from a reference repository are required. Data and the figure legend
are written alongside outputs. This demonstrates composition, not biology.
"""
from pathlib import Path
import argparse
import sys
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from editorial import (figure_style, canvas, axes_mm, text_mm, panel_heading,
    estimate_column, scientific_heatmap, raw_groups, interval_trajectory,
    INK, MUTED, BLUE, WARM, BASELINE)
from publication import save_figure, write_json

GROUPS = ["Reference", "Vehicle", "Treatment"]
COLORS = ["#71828B", WARM, BLUE]


def simulate(seed=2741):
    rng = np.random.default_rng(seed)
    n = 18
    time = np.array([0, 3, 7, 14, 21, 28.])
    curves = [[88, 89, 88, 90, 89, 90], [24, 25, 26, 29, 32, 35], [24, 30, 42, 61, 74, 82]]
    subjects = []
    dose = np.array([0, .03, .1, .3, 1, 3, 10.])
    for group, curve in enumerate(curves):
        for index in range(n):
            latent = rng.normal(0, 5)
            trajectory = np.clip(np.array(curve) + latent + rng.normal(0, 2.5, len(time)), 0, 100)
            viability = np.clip([88, 37, 76][group]+latent*.85+rng.normal(0, 7), 0, 100)
            migration = np.clip([78, 53, 55][group]+latent*.4+rng.normal(0, 11), 0, 100)
            integrity = np.clip([89, 48, 66][group]+latent*.6+rng.normal(0, 7), 0, 100)
            modules = np.array([[.1, .1, .2, .0, .2, .1], [1.5, 1.3, 1.2, .9, -1.1, -.7], [.5, .2, .4, .6, .5, .7]][group]) + rng.normal(0, .4, 6)
            stress = np.clip(viability - [62, 32, 71][group]*dose/(dose+.7) + rng.normal(0, 2.2, len(dose)), 0, 100)
            subjects.append({"id": f"G{group+1}-{index+1:02}", "group": GROUPS[group],
                "trajectory": trajectory.tolist(), "viability": float(viability),
                "migration": float(migration), "integrity": float(integrity),
                "modules": modules.tolist(), "stress": stress.tolist()})
    return {"kind": "SIMULATED_DATA", "seed": seed, "time_days": time.tolist(),
            "dose": dose.tolist(), "subjects": subjects}


def bootstrap_mean(values, rng):
    values = np.asarray(values)
    boot = values[rng.integers(0, len(values), (2000, len(values)))].mean(axis=1)
    lo, hi = np.quantile(boot, [.025, .975], axis=0)
    return values.mean(axis=0), lo, hi


def build(data):
    fig = canvas((180, 177)); axes = []; rng = np.random.default_rng(612)
    subsets = [[row for row in data["subjects"] if row["group"] == name] for name in GROUPS]
    panel_heading(fig, "a", "Recovery over time", 3, 4)
    text_mm(fig, 177, 11, "SIMULATED DATA", fontsize=6.2, color=MUTED, ha="right")
    ax = axes_mm(fig, 17, 17, 88, 40, label="a")
    for group, rows in enumerate(subsets):
        mean, lo, hi = bootstrap_mean([row["trajectory"] for row in rows], rng)
        interval_trajectory(ax, data["time_days"], mean, lo, hi,
            color=COLORS[group], label=GROUPS[group], marker=["o", "s", "D"][group],
            linestyle=["--", "-", "-"][group])
    ax.set(xlabel="Time (days)", ylabel="Recovery score", xlim=(-1, 29), ylim=(0, 100),
           xticks=data["time_days"], yticks=[0, 25, 50, 75, 100])
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.19), ncols=3, fontsize=6.7)
    axes.append(ax)

    panel_heading(fig, "b", "Endpoint variation", 114, 4)
    ax = axes_mm(fig, 128, 17, 47, 40, label="b")
    raw_groups(ax, [[row["trajectory"][-1] for row in rows] for rows in subsets],
               ["Ref.", "Veh.", "Treat."], COLORS, point_size=8)
    ax.set(ylabel="Day 28 recovery", ylim=(0, 100), yticks=[0, 25, 50, 75, 100])
    axes.append(ax)

    panel_heading(fig, "c", "Response under stress", 3, 75)
    ax = axes_mm(fig, 17, 86, 43, 27, label="c")
    for group in [1, 2]:
        mean, lo, hi = bootstrap_mean([row["stress"] for row in subsets[group]], rng)
        interval_trajectory(ax, data["dose"], mean, lo, hi, color=COLORS[group],
                            marker=["o", "s", "D"][group])
    ax.set_xscale("symlog", linthresh=.03, linscale=.7)
    ax.set(xlabel="Stressor (a.u.)", ylabel="Viability (%)", ylim=(0, 100), yticks=[0, 50, 100])
    ax.set_xticks([0, .1, 1, 10], ["0", ".1", "1", "10"])
    axes.append(ax)

    panel_heading(fig, "d", "Functional effects", 76, 75)
    ax = axes_mm(fig, 116, 86, 59, 27, label="d")
    fields = ["recovery", "viability", "migration", "integrity"]
    estimates, lower, upper = [], [], []
    for field in fields:
        values = [np.array([row["trajectory"][-1] if field == "recovery" else row[field] for row in rows]) for rows in subsets[1:]]
        boot = [v[rng.integers(0, len(v), (2000, len(v)))].mean(axis=1) for v in values]
        estimates.append(values[1].mean()-values[0].mean())
        lo, hi = np.quantile(boot[1]-boot[0], [.025, .975]); lower.append(lo); upper.append(hi)
    estimate_column(ax, estimates, [x.title() for x in fields], lower=lower, upper=upper,
                    colors=[BLUE]*4, limits=(-15, 65), ticks=[0, 20, 40, 60], guide_rows=False)
    ax.axvline(0, color=MUTED, linewidth=.6, linestyle=(0, (3, 3)), zorder=1)
    ax.set_xlabel("Treatment − vehicle (points)")
    axes.append(ax)

    panel_heading(fig, "e", "Sample-level molecular modules", 3, 129)
    values = np.array([row["modules"] for row in data["subjects"]]).T
    z = (values-values.mean(axis=1, keepdims=True))/values.std(axis=1, keepdims=True, ddof=1)
    ax = axes_mm(fig, 25, 142, 80, 23, label="e")
    image = scientific_heatmap(ax, z,
        ["Inflamm.", "IFN", "Stress", "ECM", "Repair", "Metabol."], [""]*54,
        limits=(-3.5, 3.5), center=0, annotate=False, col_breaks=[18, 36])
    ax.set_xticks([])
    for index, (name, color) in enumerate(zip(GROUPS, COLORS)):
        left = 25+index*80/3
        text_mm(fig, left+80/6, 137.5, name, ha="center", color=color, fontsize=6.3)
    cbax = axes_mm(fig, 49, 169, 30, 1.7)
    bar = fig.colorbar(image, cax=cbax, orientation="horizontal", ticks=[-3, 0, 3])
    bar.outline.set_visible(False); bar.ax.tick_params(labelsize=6, pad=1, length=1.5)
    text_mm(fig, 82, 169, "Row z score", fontsize=6.2, color=MUTED)
    axes.append(ax)

    panel_heading(fig, "f", "Orthogonal readout", 114, 129)
    ax = axes_mm(fig, 128, 142, 47, 23, label="f")
    for index, rows in enumerate(subsets):
        ax.scatter([row["viability"] for row in rows], [row["trajectory"][-1] for row in rows],
                   s=9, color=COLORS[index], marker=["o", "s", "D"][index],
                   edgecolor="white", linewidth=.35, alpha=.8)
    ax.set(xlabel="Tissue viability (%)", ylabel="Recovery score", xlim=(10, 100), ylim=(10, 100),
           xticks=[25, 50, 75, 100], yticks=[25, 50, 75, 100])
    axes.append(ax)
    return fig, axes, {"panel_ids": list("abcdef"), "row_groups": [],
                      "column_groups": [["b", "f"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    data = simulate(); write_json(args.out/"04_simulated_source_data.json", data)
    with figure_style():
        fig, axes, alignment = build(data)
        report = save_figure(fig, args.out/"04_experimental_evidence", axes=axes, dpi=450,
                             alignment_options=alignment)
        report["design_review"] = {"status": "pending", "layout_rationale": "a is the primary longitudinal panel; e shows individual samples; b/f share the right-column plotting rectangle. c/d have distinct roles and intentional widths."}
        report["data_kind"] = "SIMULATED_DATA"
        write_json(args.out/"04_experimental_evidence.qa.json", report)
        print(report["automated_status"]); plt.close(fig)
        if report["automated_status"] in {"FAIL", "NOT_AUDITABLE"}:
            raise RuntimeError("Inspect 04_experimental_evidence.qa.json before using this output")
    (args.out/"04_experimental_legend.md").write_text(
        "# SIMULATED DATA — design demonstration only\n\n"
        "All 54 subjects (18 per group) and every measurement were generated with seed 2741. "
        "No observed biological findings are represented.\n\n"
        "a: group means with 95% percentile bootstrap intervals over subjects (2,000 draws). "
        "Time intervals remain 0, 3, 7, 14, 21 and 28 days. b: every subject's day-28 value; "
        "boxes: median and quartiles; whiskers: 1.5 IQR; all observations, including outliers, remain visible. "
        "c: the same subject-level simulated stress assay, group means and subject-bootstrap intervals; "
        "symlog x retains zero and measured doses. d: unpaired treatment-minus-vehicle mean differences "
        "with 95% independent-group percentile bootstrap intervals (2,000 draws). "
        "All outcomes use 0–100 scales; migration's interval crosses zero and is retained. "
        "No p values or significance symbols are added. e: six simulated module scores, standardized "
        "within rows over all 54 subjects using sample SD; original group/subject order, no clustering, "
        "no per-group rescaling. f: the same 54 subjects' orthogonal tissue readout and day-28 score, "
        "with no pooled regression that could conceal group confounding.\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
