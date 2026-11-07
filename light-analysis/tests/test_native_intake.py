"""Native-format fixtures are synthetic records, not actual experiment claims."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

from test_analysis import bridge, put, complete_plan, complete_analysis


def native_fixture(root, status="succeeded", run_id="R001", result=True):
    design = {"schema_version": "1.0", "design_id": "D01", "version": 3,
              "selection": {"idea_id": "I01", "idea_version": 2},
              "claims": [{"claim_id": "C01", "statement": "Synthetic fixture"}],
              "experiments": [{"experiment_id": "X01", "claim_ids": ["C01"]}]}
    put(root / "campaign.json", {"schema_version": "1.0", "campaign_id": "EX_fixture_" + root.name,
        "design_id": "D01", "design_version": 3, "selection": design["selection"], "execution_scope": ["X01"]})
    put(root / "inputs/design/design.json", design)
    put(root / f"runs/{run_id}/spec.json", {"schema_version": "1.0", "run_id": run_id,
        "experiment_id": "X01", "task_id": "T01", "kind": "pilot", "unit": {"unit_id": "U01"}})
    if result:
        put(root / f"runs/{run_id}/result.json", {"schema_version": "1.0", "run_id": run_id,
            "process_status": status, "returncode": 0 if status == "succeeded" else 7,
            "artifacts_ok": status == "succeeded", "input_drift_after": []})
    raw = root / f"runs/{run_id}/outputs/raw.json"
    put(raw, {"synthetic_validation": True, "value": 14})
    return raw


class NativeIntakeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="light-analysis-native-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.execution, self.work = self.base / "execution", self.base / "analysis"

    def test_native_identity_and_selected_raw_only(self):
        raw = native_fixture(self.execution)
        bridge.ingest([self.execution], [], self.work)
        c = bridge.read(self.work / "context.json")
        e = c["executions"][0]
        self.assertEqual((e["design_id"], e["design_version"]), ("D01", 3))
        self.assertEqual(e["selection"], {"idea_id": "I01", "idea_version": 2})
        self.assertNotIn(str(raw), [r["path"] for r in c["inputs"]])
        self.assertEqual(e["runs"][0]["run_ref"], "EX01/R001")

    def test_failed_run_not_automatically_scientific_falsification(self):
        raw = native_fixture(self.execution, status="failed")
        bridge.ingest([self.execution], [raw], self.work)
        complete_plan(self.work)
        c = bridge.read(self.work / "context.json")
        rid = next(x["input_id"] for x in c["inputs"] if x["path"] == str(raw))
        a = complete_analysis(self.work, rid)
        a["findings"][0].update(run_refs=["EX01/R001"], claim_refs=["EX01/C01"], outcome="falsify")
        put(self.work / "analysis.json", a)
        self.assertFalse(bridge.verify(self.work)["ok"])
        a["findings"][0].update(outcome="not_evaluated", validity="compromised")
        put(self.work / "analysis.json", a)
        self.assertTrue(bridge.verify(self.work)["ok"])

    def test_task_defined_failure_outcome_requires_explicit_basis(self):
        raw = native_fixture(self.execution, status="timed_out")
        bridge.ingest([self.execution], [raw], self.work)
        complete_plan(self.work)
        context = bridge.read(self.work / 'context.json')
        raw_id = next(r['input_id'] for r in context['inputs'] if r['path'] == str(raw))
        a = complete_analysis(self.work, raw_id)
        a["findings"][0].update(run_refs=["EX01/R001"], failure_outcome_basis="Synthetic benchmark protocol defines timeout as an unsolved task, not a zero-valued accuracy measure")
        put(self.work / "analysis.json", a)
        self.assertTrue(bridge.verify(self.work)["ok"])

    def test_running_or_interrupted_does_not_become_success(self):
        native_fixture(self.execution, result=False)
        put(self.execution / "runs/R001/started.json", {"run_id": "R001"})
        bridge.ingest([self.execution], [], self.work)
        c = bridge.read(self.work / "context.json")
        self.assertEqual(c["executions"][0]["runs"][0]["process_status"], "running_or_interrupted")

    def test_latest_assessment_receipt_is_unwrapped_and_retained(self):
        native_fixture(self.execution)
        for name, status in [("20260101", "failed"), ("20260102", "passed")]:
            put(self.execution / f"runs/R001/assessments/{name}.json",
                {"assessment": {"qc_status": status, "outcome": "inconclusive"}, "supersedes": None})
        bridge.ingest([self.execution], [], self.work)
        c = bridge.read(self.work / "context.json")
        self.assertEqual(c["executions"][0]["runs"][0]["qc_status"], "passed")
        self.assertEqual(len([i for i in c["inputs"] if i["role"] == "run_assessment"]), 2)

    def test_frozen_metadata_remains_valid_with_drift_warning(self):
        native_fixture(self.execution)
        bridge.ingest([self.execution], [], self.work)
        p = bridge.read(self.execution / "inputs/design/design.json")
        p["version"] = 4
        put(self.execution / "inputs/design/design.json", p)
        r = bridge.verify(self.work)
        self.assertTrue(r["ok"], r)
        self.assertTrue(any("metadata changed" in w for w in r["warnings"]))

    def test_multiple_campaign_run_ids_are_namespaced(self):
        native_fixture(self.execution)
        other = self.base / "another"
        native_fixture(other)
        bridge.ingest([self.execution, other], [], self.work)
        c = bridge.read(self.work / "context.json")
        refs = [r["run_ref"] for e in c["executions"] for r in e["runs"]]
        self.assertEqual(refs, ["EX01/R001", "EX02/R001"])

    def test_identity_mismatch_rejected_before_creation(self):
        native_fixture(self.execution)
        c = bridge.read(self.execution / "campaign.json")
        c["design_version"] = 999
        put(self.execution / "campaign.json", c)
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [], self.work)
        self.assertFalse(self.work.exists())


if __name__ == "__main__":
    unittest.main()
