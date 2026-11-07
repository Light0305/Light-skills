"""Behavioral invariants on synthetic fixtures, not scientific validation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analysis_bridge as bridge
import paired_effect as paired


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def complete_plan(root, timing="retrospective"):
    plan = bridge.read(root / "analysis-plan.json")
    plan.update({k: "Synthetic known-answer fixture; no empirical claim" for k, v in plan.items() if v == ""})
    plan.update(timing=timing, sensitivity_branches=[])
    put(root / "analysis-plan.json", plan)
    bridge.freeze_plan(root)


def complete_analysis(root, input_id="S0001"):
    item = bridge.read(root / "analysis.json")
    item.update(status="complete", data_kind="synthetic_validation")
    item["findings"] = [{"finding_id": "F01", "claim_refs": [], "run_refs": [], "mode": "descriptive",
                         "validity": "usable", "validity_basis": "Synthetic exact-answer check",
                         "outcome": "support", "statement": "Known fixture only",
                         "evidence": [{"input_id": input_id, "locator": "CSV line 2, column a"}],
                         "estimates": [], "limitations": ["Synthetic validation only"]}]
    item["loop_decision"].update(route="stop", finding_ids=["F01"], reason="Known-answer fixture complete",
        target_question="Validate plumbing only", next_action="Stop fixture", predictions=[],
        budget={"status": "not_applicable", "limit": None, "basis": "No next experiment"},
        stop_rule="Stop after exact-answer check", reentry_condition="Implementation changes",
        execution_authorization="Local validation only; no research experiments")
    put(root / "analysis.json", item)
    (root / "analysis-report.md").write_text("Synthetic fixture validation; no research conclusion.\n", encoding="utf-8")
    return item


class BridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="light-anaysis-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.raw = self.base / "原始 data.csv"
        self.raw.write_text("unit_id,a,b\nu1,5,3\nu2,8,6\n", encoding="utf-8")
        self.work = self.base / "分析"
        bridge.ingest([], [self.raw], self.work)

    def finish(self):
        complete_plan(self.work)
        return complete_analysis(self.work)

    def test_intake_is_read_only_draft_and_hashes_selected_data(self):
        original = self.raw.read_bytes()
        result = bridge.verify(self.work)
        self.assertTrue(result["ok"], result)
        self.assertTrue(any("Draft" in w for w in result["warnings"]))
        self.assertEqual(original, self.raw.read_bytes())
        with self.assertRaises(ValueError):
            bridge.export_handoff(self.work)

    def test_no_overwrite_or_reimport(self):
        before = (self.work / "context.json").read_bytes()
        with self.assertRaises(ValueError):
            bridge.ingest([], [self.raw], self.work)
        self.assertEqual(before, (self.work / "context.json").read_bytes())

    def test_input_drift_blocks_analysis(self):
        self.raw.write_text("changed", encoding="utf-8")
        result = bridge.verify(self.work)
        self.assertFalse(result["ok"])
        self.assertIn("Input drift", result["errors"][0])

    def test_context_identity_cannot_silently_change(self):
        c = bridge.read(self.work / "context.json")
        c["warnings"] = []
        put(self.work / "context.json", c)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_analysis_identity_is_checked(self):
        a = bridge.read(self.work / "analysis.json")
        a["analysis_id"] = "A_other"
        put(self.work / "analysis.json", a)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_plan_freeze_not_prospectivity_and_plan_drift_detected(self):
        complete_plan(self.work)
        lock = bridge.read(self.work / "plan-lock.json")
        self.assertEqual(lock["timing_claim"], "retrospective")
        p = bridge.read(self.work / "analysis-plan.json")
        p["comparison"] = "A different comparison after seeing data"
        put(self.work / "analysis-plan.json", p)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_cannot_freeze_incomplete_plan_or_overwrite_lock(self):
        with self.assertRaises(ValueError):
            bridge.freeze_plan(self.work)
        complete_plan(self.work)
        with self.assertRaises(FileExistsError):
            bridge.freeze_plan(self.work)

    def test_retrospective_findings_cannot_be_relabeled_confirmation(self):
        item = self.finish()
        item["findings"][0]["mode"] = "confirmatory"
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_decisive_finding_needs_valid_data(self):
        item = self.finish()
        item["findings"][0]["validity"] = "compromised"
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_unknown_origin_and_missing_evidence_not_decisive(self):
        item = self.finish()
        item["data_kind"] = "unknown"
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])
        item["data_kind"] = "synthetic_validation"
        item["findings"][0]["evidence"] = []
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_findings_refs_and_decision_refs_are_checked(self):
        item = self.finish()
        for field, value in [("run_refs", ["EX99/R1"]), ("claim_refs", ["EX99/C1"])]:
            changed = copy.deepcopy(item)
            changed["findings"][0][field] = value
            put(self.work / "analysis.json", changed)
            self.assertFalse(bridge.verify(self.work)["ok"])
        item["loop_decision"]["finding_ids"] = ["F_absent"]
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_interval_semantics_and_counts_checked(self):
        item = self.finish()
        est = {"name": "mean difference", "value": 2, "unit": "fixture units", "n_independent": 2,
               "n_observations": 4, "interval": {"level": .95, "lower": 1, "upper": 3,
               "type": "confidence", "method": "fixture", "uncertainty_scope": "fixture only"}}
        item["findings"][0]["estimates"] = [est]
        put(self.work / "analysis.json", item)
        self.assertTrue(bridge.verify(self.work)["ok"])
        for key, value in [("n_independent", 5), ("n_independent", True), ("value", float("inf"))]:
            changed = copy.deepcopy(item)
            changed["findings"][0]["estimates"][0][key] = value
            put(self.work / "analysis.json", changed)
            self.assertFalse(bridge.verify(self.work)["ok"])
        item["findings"][0]["estimates"][0]["interval"]["lower"] = 10
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_next_research_route_needs_discriminating_predictions(self):
        item = self.finish()
        item["loop_decision"].update(route="light-design", predictions=[])
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])
        item["loop_decision"]["predictions"] = [{"result": "Precision can exclude meaningful improvement", "decision": "Stop this branch"}]
        put(self.work / "analysis.json", item)
        self.assertTrue(bridge.verify(self.work)["ok"])

    def test_complete_handoff_is_versioned_and_not_executed(self):
        self.finish()
        result = bridge.export_handoff(self.work)
        self.assertEqual(result["route"], "stop")
        h = bridge.read(self.work / "handoff.json")
        self.assertEqual(h["data_kind"], "synthetic_validation")
        self.assertEqual(h["trigger_findings"][0]["finding_id"], "F01")
        with self.assertRaises(FileExistsError):
            bridge.export_handoff(self.work)
        item = bridge.read(self.work / "analysis.json")
        item["history"].append({"change": "New interpretation"})
        put(self.work / "analysis.json", item)
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_parent_lineage_preserves_prior_decision(self):
        self.finish()
        next_work = self.base / "round2"
        bridge.ingest([], [self.raw], next_work, self.work / "analysis.json")
        a = bridge.read(next_work / "analysis.json")
        c = bridge.read(next_work / "context.json")
        self.assertEqual(a["round"], 2)
        self.assertEqual(a["parent_analysis_id"], c["parent"]["analysis_id"])
        self.assertEqual(c["parent"]["loop_decision"]["route"], "stop")

    def make_artifact(self):
        code = self.work / "code/check.py"
        code.parent.mkdir()
        code.write_text("print(2)\n", encoding="utf-8")
        artifact = self.work / "derived/summary.json"
        put(artifact, {"known": 2})
        bridge.register_artifact(self.work, "T01", "derived/summary.json", ["S0001"], ["code/check.py"], "python code/check.py", sys.version)
        return code, artifact

    def test_derived_provenance_and_code_drift(self):
        code, _ = self.make_artifact()
        self.assertTrue(bridge.verify(self.work)["ok"])
        code.write_text("print(999)\n", encoding="utf-8")
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_derived_numeric_drift(self):
        _, artifact = self.make_artifact()
        put(artifact, {"known": 999})
        self.assertFalse(bridge.verify(self.work)["ok"])

    def test_path_traversal_and_outputs_inside_skill_rejected(self):
        for relative in ("../escape.json", str(self.raw), "derived/../../escape"):
            with self.assertRaises(ValueError):
                bridge.inside(self.work, relative)
        with self.assertRaises(ValueError):
            bridge.ingest([], [self.raw], ROOT / "test-output-must-not-exist")

    def test_strict_json_duplicate_nonfinite_and_overflow(self):
        p = self.base / "bad.json"
        for value in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e400}'):
            p.write_text(value, encoding="utf-8")
            with self.assertRaises(ValueError):
                bridge.read(p)

    def test_cli_supports_unicode_paths(self):
        proc = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/analysis_bridge.py"),
            "verify", "--workspace", str(self.work)], capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["ok"])


class PairedTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="light-anaysis-pairs-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.csv = self.base / "pairs.csv"

    def run_compare(self, text, direction="higher"):
        self.csv.write_text(text, encoding="utf-8")
        return paired.compare(self.csv, direction, .95, 2000, 17,
                              "Independent paired synthetic units", "Synthetic-unit sampling only", "synthetic_validation")

    def test_known_constant_shift_and_degeneracy_warning(self):
        r = self.run_compare("unit_id,a,b\nu1,3,1\nu2,103,101\nu3,-3,-5\n")
        self.assertEqual(r["mean_improvement"], 2)
        self.assertEqual((r["interval"]["lower"], r["interval"]["upper"]), (2, 2))
        self.assertTrue(any("degenerate" in w for w in r["warnings"]))

    def test_direction_and_row_order_invariance(self):
        r = self.run_compare("unit_id,a,b\nu1,6,1\nu2,8,7\nu3,0,3\n")
        s = self.run_compare("unit_id,a,b\nu3,0,3\nu1,6,1\nu2,8,7\n")
        self.assertEqual(r["interval"], s["interval"])
        t = self.run_compare("unit_id,a,b\nu1,6,1\nu2,8,7\nu3,0,3\n", "lower")
        self.assertEqual(r["mean_improvement"], -t["mean_improvement"])
        self.assertAlmostEqual(r["interval"]["lower"], -t["interval"]["upper"])

    def test_rejects_missing_duplicate_single_nonfinite_and_irregular(self):
        for text in ["unit_id,a,b\nu1,1,\nu2,2,1\n", "unit_id,a,b\nu1,1,2\nu1,2,3\n",
                     "unit_id,a,b\nu1,1,2\n", "unit_id,a,b\nu1,NaN,2\nu2,1,2\n",
                     "unit_id,a,b\nu1,1,2,3\nu2,1,2\n", "unit_id,a,b\nu1,1,inf\nu2,1,2\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.run_compare(text)

    def test_identical_conditions_zero_is_a_real_value(self):
        r = self.run_compare("unit_id,a,b\nu1,0,0\nu2,4,4\n")
        self.assertEqual(r["mean_improvement"], 0)
        self.assertEqual(r["n_independent_pairs"], 2)

    def test_bootstrap_matches_exact_empirical_distribution_for_two_pairs(self):
        r = self.run_compare("unit_id,a,b\nu1,1,0\nu2,3,0\n")
        # Exact bootstrap means are 1,2,3 with probabilities .25,.5,.25.
        self.assertEqual(r["mean_improvement"], 2)
        self.assertEqual((r["interval"]["lower"], r["interval"]["upper"]), (1, 3))

    def test_cli_does_not_overwrite_or_drop_provenance(self):
        self.csv.write_text("unit_id,a,b\nu1,1,0\nu2,3,0\n", encoding="utf-8")
        out = self.base / "effect.json"
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/paired_effect.py"), "--input", str(self.csv),
                   "--out", str(out), "--direction", "higher", "--unit-definition", "Synthetic pairs",
                   "--uncertainty-scope", "Unit sampling only", "--data-kind", "synthetic_validation", "--resamples", "100"]
        first = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual(first.returncode, 0, first.stderr)
        before = out.read_bytes()
        second = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(before, out.read_bytes())
        result = bridge.read(out)
        self.assertEqual(result["input"]["sha256"], bridge.fingerprint(self.csv)["sha256"])


if __name__ == "__main__":
    unittest.main()
