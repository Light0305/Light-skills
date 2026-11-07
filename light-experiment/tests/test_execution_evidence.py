"""Synthetic regressions for measured evidence, corrections and consumed runs."""
from pathlib import Path
import json
import subprocess
import sys
import unittest

import test_experiment as fixtures

tool = fixtures.tool


class ExecutionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.ExperimentTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.workspace = self.case.workspace
        self.folder = self.workspace / "runs/R001"

    def execute(self):
        self.case.prepare()
        return tool.run(self.workspace, "R001")

    def accepted_pair(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment())
        spec = self.case.make_spec("R002")
        spec["depends_on_runs"] = ["R001"]
        self.case.prepare("R002", spec=spec)
        tool.run(self.workspace, "R002")

    def test_optional_outputs_alone_cannot_define_a_scientific_run(self):
        spec = self.case.make_spec()
        spec["expected_outputs"][0]["required"] = False
        with self.assertRaisesRegex(ValueError, "required.*nonempty"):
            self.case.prepare(spec=spec)
        self.assertFalse(self.folder.exists())

    def test_required_empty_marker_is_not_a_raw_product(self):
        spec = self.case.make_spec()
        spec["expected_outputs"][0]["min_bytes"] = 0
        with self.assertRaisesRegex(ValueError, "required.*nonempty"):
            self.case.prepare(spec=spec)

    def test_configuration_cannot_be_cited_as_measured_evidence(self):
        self.execute()
        path = self.case.assessment()
        item = tool.read(path)
        item["metrics"][0]["artifact"] = "spec.json"
        fixtures.write(path, item)
        with self.assertRaisesRegex(ValueError, "sealed.*raw"):
            tool.assess(self.workspace, "R001", path)

    def test_unsealed_assessment_attachment_cannot_support_an_outcome(self):
        self.execute()
        attachment = self.folder / "assessments/late.txt"
        attachment.parent.mkdir()
        attachment.write_text("14", encoding="utf-8")
        path = self.case.assessment()
        item = tool.read(path)
        item["metrics"][0]["artifact"] = "assessments/late.txt"
        fixtures.write(path, item)
        with self.assertRaisesRegex(ValueError, "sealed.*raw"):
            tool.assess(self.workspace, "R001", path)

    def test_missing_start_record_cannot_reduce_spent_budget(self):
        self.execute()
        (self.folder / "started.json").unlink()
        self.case.prepare("R002")
        with self.assertRaisesRegex(ValueError, "Missing.*attempt"):
            tool.run(self.workspace, "R002")
        self.assertFalse((self.workspace / "runs/R002/started.json").exists())

    def test_missing_run_directory_cannot_erase_a_recorded_attempt(self):
        self.execute()
        retained = self.case.base / "retained-R001"
        self.assertTrue(retained.resolve().is_relative_to(self.case.base.resolve()))
        self.folder.rename(retained)
        with self.assertRaisesRegex(ValueError, "Missing.*attempt"):
            tool.budget_state(self.workspace)

    def test_older_assessment_drift_blocks_further_correction(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment())
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="inconclusive"))
        first = sorted((self.folder / "assessments").glob("*.json"))[0]
        item = tool.read(first)
        item["assessment"]["qc_basis"] = "Unexpected edit of an earlier assessment"
        fixtures.write(first, item)
        with self.assertRaisesRegex(ValueError, "Assessment content drift"):
            tool.assess(self.workspace, "R001", self.case.assessment())
        self.assertEqual(len(list((self.folder / "assessments").glob("*.json"))), 2)

    def test_broken_assessment_correction_chain_is_reported(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment())
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="inconclusive"))
        latest = sorted((self.folder / "assessments").glob("*.json"))[-1]
        item = tool.read(latest)
        item["supersedes"] = "absent.json"
        fixtures.write(latest, item)
        report = tool.verify(self.workspace)
        self.assertFalse(report["ok"], report)
        self.assertTrue(any("Assessment correction chain" in e for e in report["errors"]))

    def test_revoked_prerequisite_requires_review_of_consumed_results(self):
        self.accepted_pair()
        original = (self.workspace / "runs/R002/result.json").read_bytes()
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="inconclusive", qc="failed"))
        report = tool.verify(self.workspace)
        self.assertFalse(report["ok"], report)
        self.assertTrue(any("prerequisite" in e.lower() for e in report["errors"]))
        with self.assertRaisesRegex(ValueError, "prerequisite"):
            tool.assess(self.workspace, "R002", self.case.assessment("R002"))
        self.assertEqual((self.workspace / "runs/R002/result.json").read_bytes(), original)

    def test_unexecuted_input_drift_is_visible_to_verification(self):
        self.case.prepare()
        self.case.config.write_text("{}", encoding="utf-8")
        report = tool.verify(self.workspace)
        self.assertFalse(report["ok"], report)
        self.assertTrue(any("Input drift" in e for e in report["errors"]))
        self.assertEqual(report["budget"]["attempts"], 0)

    def test_empty_frozen_plan_cannot_authorize_preparation(self):
        (self.case.design / "plan.md").write_text(" \n", encoding="utf-8")
        self.case.workspace = self.case.base / "empty-plan-campaign"
        tool.init(self.case.design, self.case.workspace, 2, 30, "Synthetic limited test")
        with self.assertRaisesRegex(ValueError, "nonempty.*plan.md"):
            self.case.prepare()
        self.assertFalse((self.case.workspace / "runs").exists())

    def test_optional_diagnostic_output_can_accompany_required_raw_data(self):
        spec = self.case.make_spec()
        spec["expected_outputs"].append({"path": "optional.txt", "role": "diagnostic",
                                          "required": False, "min_bytes": 0})
        self.case.prepare(spec=spec)
        result = tool.run(self.workspace, "R001")
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["output_checks"][-1]["exists"])

    def test_later_live_code_edits_do_not_rewrite_a_completed_run(self):
        self.execute()
        original = (self.folder / "snapshots/0000/worker.py").read_bytes()
        self.case.worker.write_text("# Later work for another attempt", encoding="utf-8")
        report = tool.verify(self.workspace)
        self.assertTrue(report["ok"], report)
        self.assertEqual((self.folder / "snapshots/0000/worker.py").read_bytes(), original)

    def test_valid_scientific_negative_can_be_a_prerequisite(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="falsify"))
        spec = self.case.make_spec("R002")
        spec["depends_on_runs"] = ["R001"]
        self.case.prepare("R002", spec=spec)
        self.assertTrue(tool.run(self.workspace, "R002")["ok"])

    def test_dependency_receipt_is_bound_and_reapproval_requires_review(self):
        self.accepted_pair()
        start = tool.read(self.workspace / "runs/R002/started.json")
        bound = start["dependencies"][0]
        self.assertEqual(bound["run_id"], "R001")
        self.assertEqual(bound["result"], tool.digest(self.folder / "result.json"))
        self.assertEqual(bound["assessment"], tool.digest(self.folder / bound["assessment_file"]))
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="inconclusive"))
        report = tool.verify(self.workspace)
        self.assertTrue(report["ok"], report)
        self.assertTrue(any("QC binding changed" in w and "R002" in w for w in report["warnings"]))

    def test_deleted_latest_assessment_cannot_restore_an_older_pass(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment())
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="inconclusive", qc="failed"))
        sorted((self.folder / "assessments").glob("*.json"))[-1].unlink()
        with self.assertRaisesRegex(ValueError, "Missing recorded assessment"):
            tool.latest_assessment(self.folder)
        self.assertFalse(tool.verify(self.workspace)["ok"])

    def test_sealed_stdout_is_a_valid_raw_metric_source(self):
        self.execute()
        path = self.case.assessment(outcome="not_evaluated", qc="pending", value=None)
        item = tool.read(path)
        item["metrics"][0].update(artifact="stdout.log", locator="Unparsed raw log; no inferred value")
        fixtures.write(path, item)
        self.assertTrue(tool.assess(self.workspace, "R001", path)["ok"])

    def test_existing_pending_qc_stays_visible_in_verification(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="not_evaluated", qc="pending"))
        report = tool.verify(self.workspace)
        self.assertTrue(report["ok"], report)
        self.assertTrue(any("QC not passed (pending)" in w for w in report["warnings"]))

    def test_revocation_propagates_through_transitive_prerequisites(self):
        self.accepted_pair()
        tool.assess(self.workspace, "R002", self.case.assessment("R002"))
        spec = self.case.make_spec("R003")
        spec["depends_on_runs"] = ["R002"]
        self.case.prepare("R003", spec=spec)
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="inconclusive", qc="failed"))
        with self.assertRaisesRegex(ValueError, "Unaccepted prerequisite: R001"):
            tool.run(self.workspace, "R003")
        self.assertEqual(tool.budget_state(self.workspace)["attempts"], 2)

    def test_actual_analysis_intake_retains_identity_qc_and_raw_input(self):
        self.execute()
        tool.assess(self.workspace, "R001", self.case.assessment(outcome="falsify"))
        self.assertTrue(tool.verify(self.workspace)["ok"])
        out = self.case.base / "analysis"
        bridge = fixtures.ROOT.parent / "light-anaysis/scripts/analysis_bridge.py"
        raw = self.folder / "outputs/raw.json"
        before = raw.read_bytes()
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(bridge), "ingest",
                                 "--execution", str(self.workspace), "--input", str(raw), "--out", str(out)],
                                capture_output=True, text=True, encoding="utf-8", timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
        context = tool.read(out / "context.json")
        execution = context["executions"][0]
        self.assertEqual((execution["design_id"], execution["design_version"]), ("D01", 3))
        self.assertEqual(execution["selection"], {"idea_id": "I01", "idea_version": 2})
        self.assertEqual(execution["runs"][0]["qc_status"], "passed")
        self.assertEqual(execution["runs"][0]["upstream_outcome"], "falsify")
        source = next(row for row in context["inputs"] if row["path"] == str(raw))
        self.assertEqual(source["sha256"], tool.digest(raw)["sha256"])
        self.assertEqual(raw.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
