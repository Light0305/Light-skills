#!/usr/bin/env python3
"""Mean paired improvement with an iid-pair percentile bootstrap (stdlib).

The caller must establish independent units and legitimate pairing. No p-value,
equivalence conclusion or scientific decision is generated.
"""
import argparse
import csv
import math
from pathlib import Path
import random
import statistics
import sys

from analysis_bridge import fingerprint, plain_file, require, write_new


def quantile(values, q):
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    weight = position - low
    return values[low] * (1 - weight) + values[high] * weight


def finite_mean(values):
    try:
        return statistics.fmean(values)
    except OverflowError:
        # Exact-ratio fallback avoids overflow of an otherwise finite mean.
        return statistics.mean(values)


def compare(path, direction, confidence, resamples, seed, unit_definition, uncertainty_scope, data_kind):
    require(direction in {"higher", "lower"}, "Choose higher or lower")
    require(math.isfinite(confidence) and 0 < confidence < 1, "Confidence must be between 0 and 1")
    require(type(resamples) is int and resamples >= 100, "At least 100 bootstrap draws; this is computational, not a sample-size guarantee")
    require(unit_definition.strip() and uncertainty_scope.strip(), "Define units and uncertainty scope")
    require(data_kind in {"measured", "simulation", "synthetic_validation", "illustrative", "unknown"}, "Invalid data kind")
    path = plain_file(path)
    original = fingerprint(path)
    rows = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ["unit_id", "a", "b"], "CSV header must be exactly unit_id,a,b")
        for line, row in enumerate(reader, 2):
            require(None not in row and all(isinstance(v, str) and v.strip() for v in row.values()), f"Incomplete/irregular pair at CSV line {line}")
            key = row["unit_id"].strip()
            require(key not in rows, f"Duplicate independent-unit ID at CSV line {line}")
            a, b = float(row["a"]), float(row["b"])
            require(math.isfinite(a) and math.isfinite(b), f"Non-finite pair at CSV line {line}")
            difference = a - b if direction == "higher" else b - a
            require(math.isfinite(difference), "Pair difference overflow")
            rows[key] = difference
    require(fingerprint(path) == original, "Input changed during analysis")
    differences = [rows[k] for k in sorted(rows)]
    n = len(differences)
    require(n >= 2, "Need at least two complete independent pairs; this does not establish adequate precision")
    rng = random.Random(seed)
    draws = sorted(finite_mean(rng.choices(differences, k=n)) for _ in range(resamples))
    alpha = 1 - confidence
    lower, upper = quantile(draws, alpha / 2), quantile(draws, 1 - alpha / 2)
    require(all(math.isfinite(v) for v in (lower, upper)), "Bootstrap estimate overflow")
    warnings = ["Caller asserts independent pairs; script does not verify scientific independence or pairing.",
                "Percentile bootstrap may have poor coverage for small, skewed, discrete or heavy-tailed samples.",
                "Resampling repetitions do not increase independent N; no p-value or equivalence claim computed."]
    if min(differences) == max(differences):
        warnings.append("Constant observed differences: degenerate bootstrap interval does not establish zero population uncertainty.")
    return {"schema_version": "1.0", "data_kind": data_kind,
            "input": {"path": str(path), **original}, "n_independent_pairs": n,
            "unit_definition": unit_definition, "improvement_definition": "a-b" if direction == "higher" else "b-a",
            "mean_improvement": finite_mean(differences), "sd_differences": statistics.stdev(differences),
            "interval": {"level": confidence, "lower": lower, "upper": upper,
                         "type": "confidence", "method": "iid paired-unit percentile bootstrap; linear quantiles",
                         "uncertainty_scope": uncertainty_scope},
            "resamples": resamples, "seed": seed, "python": sys.version, "warnings": warnings}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--direction", choices=["higher", "lower"], required=True)
    p.add_argument("--unit-definition", required=True)
    p.add_argument("--uncertainty-scope", required=True)
    p.add_argument("--data-kind", choices=["measured", "simulation", "synthetic_validation", "illustrative", "unknown"], required=True)
    p.add_argument("--confidence", type=float, default=0.95)
    p.add_argument("--resamples", type=int, default=10000)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    try:
        out = Path(args.out).resolve()
        require(not out.exists(), "Output exists; choose a new derived file")
        result = compare(args.input, args.direction, args.confidence, args.resamples, args.seed,
                         args.unit_definition, args.uncertainty_scope, args.data_kind)
        write_new(out, result)
        print(f"Saved paired effect: {out}")
        return 0
    except (ValueError, OSError, OverflowError, statistics.StatisticsError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
