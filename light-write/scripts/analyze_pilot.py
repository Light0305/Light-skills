"""Audit retained pilot artifacts and summarize mechanical checks and model reviews."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import statistics
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "evaluations/2026-10-27-pilot"
spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def audit():
    cases = {c["id"]: c for c in map(json.loads, (BUNDLE / "cases.jsonl").read_text(encoding="utf-8").splitlines())}
    schema = json.loads((ROOT / "schemas/run.schema.json").read_text(encoding="utf-8"))
    mechanical = []
    records = [p for phase in ("before", "after", "after2") for p in (BUNDLE / phase).rglob("record.json")]
    run_ids = set()
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["run_id"] not in run_ids, record["run_id"]
        run_ids.add(record["run_id"])
        validator.check_run(record, schema, set(cases), BUNDLE)
        for item in record["loaded_files"]:
            p = validator.local_file(BUNDLE, item["path"])
            assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"], item
        case = cases[record["case_id"]]
        assert record["case_sha256"] == hashlib.sha256(json.dumps(case, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        source_prompt = (path.parent / "input.txt").read_text(encoding="utf-8")
        assert record["input"] == source_prompt
        for item in record["loaded_files"]:
            guide = (BUNDLE / item["path"]).read_text(encoding="utf-8")
            assert guide in source_prompt, (record["run_id"], item["path"])
        assert record["output"] == (path.parent / "output.md").read_text(encoding="utf-8")
        prose = re.split(r"\n\s*(?:\*\*)?(?:Author[’']?s? note|Note|作者说明|说明)\b", record["output"], flags=re.I)[0].strip()
        # Ignore optional prose label; keep paragraph breaks for requested paragraph count.
        prose = re.sub(r"\A(?:\*\*)?(?:Results|Discussion|Draft|Conclusion)(?:\*\*)?:?\s*\n", "", prose)
        if case["language"] == "zh":
            count = len(re.findall(r"[\u3400-\u9fff]", prose))
            limits = (180, 260)
            unit = "Han characters"
        else:
            # Published measurement convention: whitespace-delimited tokens incl. math.
            count = len(prose.split())
            match = re.search(r"(\d+)[–-](\d+)[- ](?:word|English words)", case["request"])
            if not match:
                match = re.search(r"(\d+)[–-](\d+) English words", case["request"])
            limits = tuple(map(int, match.groups())) if match else None
            unit = "whitespace tokens"
        execution = json.loads((path.parent / "execution.json").read_text(encoding="utf-8"))
        paragraphs = [p for p in re.split(r"\n\s*\n", prose) if p.strip()]
        completed = record["status"] == "completed"
        events = (path.parent / "events.jsonl").read_text(encoding="utf-8")
        mechanical.append({"run_id": record["run_id"], "case_id": case["id"], "phase": path.relative_to(BUNDLE).parts[0], "arm": record["arm"], "status": record["status"], "count": count if completed else None, "count_unit": unit, "length_range": limits, "length_ok": (limits is None or limits[0] <= count <= limits[1]) if completed else None, "paragraphs": len(paragraphs) if completed else None, "usage_limit": "usage limit" in events.lower(), "tool_events": len(execution["observed_tool_events"]), "elapsed_seconds": execution["elapsed_seconds"], "usage": execution["usage"]})
    (BUNDLE / "mechanical.json").write_text(json.dumps(mechanical, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    summary = {"record_count": len(records), "hashes_and_run_contracts": "passed", "length_measurement": "English: whitespace tokens incl. math; Chinese: Han characters, excludes digits/punctuation; optional notes excluded by label heuristic", "groups": {}}
    for phase, arm in sorted({(r["phase"], r["arm"]) for r in mechanical}):
        group = [r for r in mechanical if r["phase"] == phase and r["arm"] == arm]
        input_tokens = [r["usage"]["input_tokens"] for r in group if r["usage"]]
        summary["groups"][f"{phase}/{arm}"] = {"count": len(group), "completed": sum(r["status"] == "completed" for r in group), "usage_limit_failures": sum(r["usage_limit"] for r in group), "length_misses": [r["case_id"] for r in group if r["length_ok"] is False], "tool_events": sum(r["tool_events"] for r in group), "mean_input_tokens": round(statistics.mean(input_tokens)) if input_tokens else None, "mean_elapsed_seconds": round(statistics.mean(r["elapsed_seconds"] for r in group), 1)}
    reviews, preferences, normalizations = [], [], []
    for category in ("reviews", "retests", "retests-2"):
        for ratings in (BUNDLE / category).glob("*/ratings.json"):
            key = json.loads((ratings.parent / "blind-key.json").read_text(encoding="utf-8"))
            packet = json.loads((ratings.parent / "packet.json").read_text(encoding="utf-8"))
            active = {v["blind_id"] for item in packet for v in item["variants"]}
            for item in packet:
                case = cases[item["case_id"]]
                assert item["source_facts"] == case["source_facts"]
                assert item["request"] == case["request"]
                assert item["rubric"] == case["rubric"]
                for variant in item["variants"]:
                    entry = key[variant["blind_id"]]
                    # Old keys predate output_path; their recordings remain intact.
                    location = entry.get("output_path", f"{entry['phase']}/{entry['case_id']}/{entry['arm']}/output.md")
                    output_path = validator.local_file(BUNDLE, location)
                    generation = json.loads((output_path.parent / "record.json").read_text(encoding="utf-8"))
                    assert generation["status"] == "completed", location
                    assert variant["text"] == output_path.read_text(encoding="utf-8"), location
            value = json.loads(ratings.read_text(encoding="utf-8"))
            assert {r["blind_id"] for r in value["reviews"]} == active, ratings
            assert len(value["reviews"]) == len(active), ratings
            for r in value["reviews"]:
                r = dict(r)
                r["scores"] = dict(r["scores"])
                if "domain_approprpriateness" in r["scores"]:
                    assert "domain_appropriateness" not in r["scores"]
                    r["scores"]["domain_appropriateness"] = r["scores"].pop("domain_approprpriateness")
                    normalizations.append({"file": ratings.relative_to(BUNDLE).as_posix(), "blind_id": r["blind_id"], "operation": "normalize misspelled domain_approprpriateness key; numerical value unchanged; raw ratings retained"})
                assert r["case_id"] == key[r["blind_id"]]["case_id"]
                assert set(r["scores"]) == {"factual_fidelity", "evidence_calibration", "task_completion", "argument_quality", "domain_appropriateness", "language_quality", "gap_handling"}
                assert all(v is None or (isinstance(v, int) and 0 <= v <= 4) for v in r["scores"].values())
                reviews.append({**r, **key[r["blind_id"]], "reviewer": ratings.parent.name, "review_type": "model-assisted", "comparison": category})
            for r in value["pairwise"]:
                selected = r["preferred"]
                assert selected == "tie" or key[selected]["case_id"] == r["case_id"]
                preferences.append({**r, "selected": "tie" if selected == "tie" else key[selected], "reviewer": ratings.parent.name, "comparison": category})
    for name, value in (("decoded-reviews.json", reviews), ("decoded-preferences.json", preferences), ("summary.json", summary), ("review-normalizations.json", normalizations)):
        (BUNDLE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    aggregates = {"review_type": "model-assisted; two fresh review calls per pair; no human experts", "score_groups": {}, "preference_groups": {}}
    grouped = defaultdict(list)
    for r in reviews:
        grouped[(r["comparison"], r["phase"], r["arm"])].append(r)
    for key, rows in grouped.items():
        dimensions = sorted({d for r in rows for d in r["scores"]})
        means = {}
        for d in dimensions:
            values = [r["scores"].get(d) for r in rows if r["scores"].get(d) is not None]
            means[d] = round(statistics.mean(values), 3) if values else None
        aggregates["score_groups"]["/".join(key)] = {"review_rows": len(rows), "serious_error_annotations": sum(len(r["serious_failures"]) for r in rows), "mean_scores": means}
    for comparison in ("reviews", "retests", "retests-2"):
        for domain in sorted({c["domain"] for c in cases.values()}):
            counts = defaultdict(int)
            for p in preferences:
                if p["comparison"] != comparison or cases[p["case_id"]]["domain"] != domain:
                    continue
                selected = p["selected"]
                counts["tie" if selected == "tie" else selected["arm"] if comparison == "reviews" else selected["phase"]] += 1
            if counts:
                aggregates["preference_groups"][f"{comparison}/{domain}"] = dict(counts)
    (BUNDLE / "aggregates.json").write_text(json.dumps(aggregates, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Model-assisted review rows: {len(reviews)}; pairwise judgments: {len(preferences)}")


if __name__ == "__main__":
    audit()
