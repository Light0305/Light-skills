"""Reported-data redesigns of two figures4papers benchmarks (CC BY-NC 4.0).

Run: python assets/examples/benchmark.py --out <output-directory>
Inputs are bundled JSON snapshots with source hashes; no reference repo needed.
"""
from pathlib import Path
import argparse
import csv
import json
import sys
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from editorial import (figure_style, canvas, axes_mm, text_mm, panel_heading,
                       estimate_column, component_matrix, scientific_heatmap)
from project_style import role, current_project
from publication import save_figure, write_json


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def method_comparison(data):
    fig = canvas((180, 130)); axes = []
    limits = [(.45, .96), (.10, .82), (.10, .62)]
    ticks = [[.5, .7, .9], [.2, .4, .6, .8], [.2, .4, .6]]
    for row, (key, title, top, height) in enumerate([
        ("data_comparison_IEDB", "IEDB", 14, 43),
        ("data_comparison_Cancer", "Cancer", 76, 47),
    ]):
        table = data[key]; values = np.array(table["mean"]); errors = np.array(table["std"])
        panel_heading(fig, "ab"[row], title, 3, top-11)
        colors = [role('baseline')]*len(table["methods"])
        colors[-1] = role('primary')
        for j, metric in enumerate(table["metrics"]):
            x = 42 + 47*j
            ax = axes_mm(fig, x, top, 37, height, label=f"{row}-{j}")
            estimate_column(ax, values[:, j], table["methods"], lower=values[:, j]-errors[:, j],
                            upper=values[:, j]+errors[:, j], colors=colors, highlight=len(values)-1,
                            limits=limits[j], ticks=ticks[j], show_labels=j == 0, guide_rows=False)
            ax.set_title(metric, fontsize=7.5, pad=6, fontweight="bold")
            axes.append(ax)
    return fig, axes, {"panel_ids": [f"{r}-{c}" for r in range(2) for c in range(3)],
                       "row_groups": [[f"{r}-{c}" for c in range(3)] for r in range(2)],
                       "column_groups": [[f"0-{c}", f"1-{c}"] for c in range(3)]}


def ablation(data):
    fig = canvas((180, 126)); axes = []
    text_mm(fig, 3, 2, "a", fontsize=9, fontweight="bold")
    table = data["data_ablation_IEDB"]
    values, errors = np.array(table["mean"]), np.array(table["std"])
    included = np.array([[int(bit) for bit in row] for row in table["ablations"]])
    names = [f"V{i+1:02}" for i in range(len(values)-1)] + ["Full"]
    ax = axes_mm(fig, 17, 18, 46, 48, label="components")
    component_matrix(ax, included, row_labels=names,
                     column_labels=["S", "Q", "B", "M", "T"], highlight=11)
    axes.append(ax)
    text_mm(fig, 17, 4, "Components", fontsize=7.5)
    for j, (metric, lim, ticks) in enumerate(zip(table["metrics"],
            [(.75, .91), (.40, .74), (.38, .54)], [[.75, .80, .85, .90], [.4, .5, .6, .7], [.4, .45, .5]])):
        ax = axes_mm(fig, 75+35*j, 18, 27, 48, label=f"ablation-{j}")
        estimate_column(ax, values[:, j], names, lower=values[:, j]-errors[:, j],
                        upper=values[:, j]+errors[:, j], highlight=11,
                        colors=[role('baseline')]*11+[role('primary')], limits=lim, ticks=ticks, show_labels=False,guide_rows=False)
        ax.set_title(metric, fontsize=7.5, fontweight="bold", pad=6)
        axes.append(ax)
    table = data["data_ablation_Cancer"]
    values, errors = np.array(table["mean"]), np.array(table["std"])
    coefficients = np.array(table["coeffs"], dtype=float)
    for j, metric in enumerate(table["metrics"]):
        x = 17+60*j
        panel_heading(fig, "bcd"[j], metric, x-14, 80)
        ax = axes_mm(fig, x, 89, 37, 23, label=f"sensitivity-{j}")
        for flag, color, marker in [(0, role('baseline'), "o"), (1, role('primary'), "D")]:
            mask = coefficients[:, 0] == flag
            xx, yy, ee = coefficients[mask, 1], values[mask, j], errors[mask, j]
            ax.errorbar(xx, yy, yerr=ee, color=color, marker=marker, markersize=2.5,
                        linewidth=.85, elinewidth=.65, capsize=1.5,
                        label="With transfer" if flag else "Without transfer")
        ax.set_xscale("symlog", linthresh=.001, linscale=.8)
        ax.set_xticks([0, .001, .01, .1], ["0", ".001", ".01", ".1"])
        ax.tick_params(labelsize=6.5)
        ax.yaxis.set_major_locator(plt.MaxNLocator(3))
        axes.append(ax)
    axes[-1].legend(loc="upper center", bbox_to_anchor=(-.58, 1.75), ncols=2, fontsize=6.7)
    text_mm(fig, 90, 121, "Contrastive coefficient", ha="center", fontsize=7)
    return fig, axes, {"panel_ids": ["components", *[f"ablation-{i}" for i in range(3)], *[f"sensitivity-{i}" for i in range(3)]],
        "row_groups": [[f"ablation-{i}" for i in range(3)], [f"sensitivity-{i}" for i in range(3)]],
        "column_groups": []}


def rna_matrix(data):
    fig = canvas((180, 105))
    rows = data["methods"]
    columns = ["+", "−"]*3
    delta = np.stack([data[f"results_{domain}_delta_{direction}"] for domain in ["openvaccine", "zebrafish", "ribosome"] for direction in ["pos", "neg"]], axis=1)
    pct = np.stack([data[f"results_{domain}_pct_{direction}"] for domain in ["openvaccine", "zebrafish", "ribosome"] for direction in ["pos", "neg"]], axis=1)
    axes = []
    for j, (letter, title, values, limits, center, fmt) in enumerate([
            ("a", "Prediction change", delta, (-3, 3), 0, ".2f"),
            ("b", "Target fraction (%)", pct, (0, 100), None, ".1f")]):
        left = 52+65*j
        panel_heading(fig, letter, title, left-1, 3)
        ax = axes_mm(fig, left, 20, 59, 71, label=letter)
        image = scientific_heatmap(ax, values, rows, columns, limits=limits, center=center,
                    fmt=fmt, row_breaks=[4, 8, 12], col_breaks=[2, 4], highlight_row=12,annotate=False)
        if j:
            ax.set_yticklabels([])
        for k, group in enumerate(["OpenVaccine", "Zebrafish", "Ribosome"]):
            text_mm(fig, left+(k+.5)*59/3, 11, group, ha="center", fontsize=max(6.4,current_project()['typography']['minimum_pt']), color=role('muted'))
        color_ax = axes_mm(fig, left+8, 96, 43, 2)
        bar = fig.colorbar(image, cax=color_ax, orientation="horizontal")
        bar.outline.set_visible(False)
        bar.set_ticks([-3, 0, 3] if center is not None else [0, 50, 100])
        bar.ax.tick_params(labelsize=6.5, length=2, pad=2)
        axes.append(ax)
    return fig, axes, {"panel_ids": ["a", "b"], "row_groups": [["a", "b"]], "column_groups": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--project", type=Path)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    # Export all source numbers separately; dense matrices need not print every
    # value inside a figure to remain inspectable and reproducible.
    for source in ['immunostruct.json', 'rnagenscape.json']:
        write_json(args.out/source, read(source))
    rna=read('rnagenscape.json')
    with (args.out/'03_structured_heatmap_values.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['method','domain','target_direction','prediction_change','target_fraction_pct'])
        for i,method in enumerate(rna['methods']):
            for domain in ['openvaccine','zebrafish','ribosome']:
                for direction in ['pos','neg']:
                    writer.writerow([method,domain,direction,rna[f'results_{domain}_delta_{direction}'][i],
                                     rna[f'results_{domain}_pct_{direction}'][i]])
    with figure_style(project=args.project):
        for name, builder, source in [("01_method_comparison", method_comparison, "immunostruct.json"),
                ("02_component_ablation", ablation, "immunostruct.json"),
                ("03_structured_heatmap", rna_matrix, "rnagenscape.json")]:
            fig, axes, alignment = builder(read(source))
            report = save_figure(fig, args.out/name, axes=axes, dpi=450, alignment_options=alignment)
            report["data_source"] = read(source)["_provenance"]
            report["design_review"] = {"status": "pending", "basis": "technical checks do not judge editorial quality"}
            write_json(args.out/f"{name}.qa.json", report)
            print(name, report["automated_status"])
            plt.close(fig)
            if report["automated_status"] in {"FAIL", "NOT_AUDITABLE"}:
                raise RuntimeError(f"Inspect {name}.qa.json before using this output")
    (args.out/"figure_legends.md").write_text(
        "# Reported-data redesigns\n\n"
        "Source: Chen Liu et al., supplied figures4papers snapshot (CC BY-NC 4.0). "
        "These reproduce repository-reported aggregates, not independently verified experimental data.\n\n"
        "**01. Method comparison.** All nine IEDB and ten Cancer methods are shown in source order. "
        "Point estimates and symmetric errors reproduce the source mean and std arrays. "
        "AUROC and AUPRC use literal std entries; Mean PPVn errors were already divided by √5 in the source. "
        "The snapshot does not specify independent sampling units or justify reinterpreting these as confidence intervals. "
        "ImmunoStruct is highlighted for navigation; Cancer AUROC ties BigMHC-IM at 0.771, not a unique win.\n\n"
        "**02. Component ablation.** All 12 IEDB variants are retained. V01–V11 and Full follow source ordering; "
        "Filled circles mean included and open circles excluded in each 5-bit design. "
        "S = Structure; Q = Sequence; B = Bchems (source term); M = MMA; T = Transfer Learning. "
        "Bottom panels retain all eight coefficient conditions, both source boolean flags and all three metrics. "
        "The flag is labeled with/without transfer, inferred from source plotting labels for indices 6, 4 and 0; "
        "the coefficient is similarly interpreted as contrastive weight. Confirm these mappings with the data owner for research reuse. "
        "The symlog coefficient axis retains zero and actual nonzero coordinates. Error conventions match 01.\n\n"
        "**03. RNA optimization.** Every one of the 13 supplied methods and six tasks is retained. "
        "Signed prediction changes use a common zero-centered scale; target-direction fractions use a common 0–100% scale. "
        "The + and − columns indicate desired directions, not test significance. "
        "Separators follow method families in the source order. No uncertainty or tests are inferred. "
        "Exact source values are in 03_structured_heatmap_values.csv and rnagenscape.json; "
        "cell numbers are omitted from the image to reduce duplicate visual encoding.\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
