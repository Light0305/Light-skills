"""Synthetic structural regression tests; these do not validate scientific quality."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("design_bridge", ROOT / "scripts/design_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream, self.out = self.root / "想法", self.root / "方案"
        self.upstream.mkdir()
        self.original = {
            "schema_version": "1.0", "topic": "Synthetic assay feasibility",
            "constraints": {"time": "one day"},
            "ideas": [{"idea_id": "I01", "version": 2, "status": "shortlisted",
                       "question": "Can the acquisition pipeline retain raw measurements?",
                       "basis_evidence_ids": ["E01"], "prior_art": [],
                       "design": {"test": "A bounded technical pilot"}}]}
        write(self.upstream / "ideas.json", self.original)
        write(self.upstream / "context.json", {"papers": [{"paper_id": "P01", "title": "Synthetic fixture"}]})
        (self.upstream / "evidence.jsonl").write_text(json.dumps({
            "evidence_id": "E01", "paper_id": "P01", "statement": "Synthetic premise only",
            "verified": True, "access_level": "full_text", "locator": "Fixture section"}) + "\n", encoding="utf-8")
        (self.upstream / "decision.md").write_text("Synthetic data; no real experiment was run.", encoding="utf-8")
        self.before = {p.name: p.read_bytes() for p in self.upstream.iterdir()}
        bridge.ingest(self.upstream, "I01", self.out)
        self.plan = bridge.read_json(self.out / "design.json")

    def check(self, plan=None):
        write(self.out / "design.json", self.plan if plan is None else plan)
        return bridge.verify(self.out)

    def ready(self):
        p = self.plan
        p["status"] = "ready_for_pilot"
        p["objective"] = "Check traceable acquisition, without testing a scientific effect"
        p["claims"] = [{"claim_id": "C01", "statement": "The planned acquisition is feasible",
                        "prediction": "Each slot yields a recoverable raw record",
                        "rival": "Data are dropped or irreversibly aggregated",
                        "scope": "Synthetic instrument fixture only", "evidence_ids": ["E01"]}]
        p["resources"] = [{"resource_id": "R01", "name": "Mock acquisition fixture",
                           "status": "available", "specification": "In-memory synthetic fixture",
                           "locator": "tests/test_design_bridge.py", "basis": "Constructed in the test"}]
        p["gates"] = [{"gate_id": "G01", "description": "Fixture availability",
                       "status": "confirmed", "basis": "Created locally during setUp"}]
        p["experiments"] = [{
            "experiment_id": "X01", "name": "Acquisition pilot", "stage": "pilot",
            "purpose": "Decide whether an acquisition implementation is ready for further work",
            "claim_ids": ["C01"], "resource_ids": ["R01"], "gate_ids": ["G01"],
            "design": "Technical feasibility check; no efficacy inference",
            "units": {"allocation": "Mock capture slot", "independent": "Mock capture session",
                      "observation": "Raw record within a session"},
            "conditions": ["Known synthetic input"], "allocation": "No comparative allocation needed",
            "procedure": "Build a mock acquisition function according to task T01",
            "measurement": {"primary": "Raw-record retention", "operationalization": "Presence of every generated ID",
                            "timepoint": "Immediately after mock capture", "qc": "All fixture IDs must be preserved"},
            "sample_size": {"n": 4, "n_definition": "Four mock capture sessions in total",
                            "status": "justified", "method": "Bounded workflow check",
                            "basis": "Four named fixture paths; no statistical power claim"},
            "analysis": "Compare generated and retained IDs; not a statistical efficacy test",
            "decisions": {"support": "If every raw ID survives, proceed to instrumentation planning",
                          "falsify": "Any dropped ID defeats workflow feasibility in this fixture",
                          "inconclusive": "Fixture crash is a technical failure; inspect the log",
                          "stop": "Stop at four sessions; diagnose failures before redesign"}}]
        p["tasks"] = [{"task_id": "T01", "experiment_id": "X01", "depends_on": [],
                       "inputs": ["Mock ID list in fixture"], "action": "Implement a bounded mock capture preserving IDs",
                       "outputs": ["Mock raw-record list"], "acceptance": "Generated IDs equal retained IDs",
                       "owner": "Fixture implementer", "effort": "Four mock calls; no external cost"}]
        p["execution_scope"] = ["X01"]
        p["budget"] = {"summary": "Four mock calls", "basis": "Bounded fixture", "limit": "Four calls"}
        p["review"] = {"strongest_objection": "Mock behavior may not match the instrument",
                       "response": "Limit the inference to the fixture", "residual_risk": "Real instrumentation remains untested"}
        return p

    def test_ingest_preserves_identity_sources_and_bytes(self):
        ctx = bridge.read_json(self.out / "context.json")
        self.assertEqual(ctx["idea"], self.original["ideas"][0])
        self.assertEqual(self.plan["selection"], {"idea_id": "I01", "idea_version": 2})
        self.assertEqual(ctx["papers"][0]["paper_id"], "P01")
        self.assertEqual(ctx["evidence"][0]["evidence_id"], "E01")
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.upstream.iterdir()})
        self.assertEqual(self.plan["status"], "draft")
        self.assertTrue(self.check()["ok"])

    def test_refuses_overwrite_without_changing_existing_output(self):
        before = (self.out / "design.json").read_bytes()
        with self.assertRaises(ValueError):
            bridge.ingest(self.upstream, "I01", self.out)
        self.assertEqual(before, (self.out / "design.json").read_bytes())

    def test_refuses_upstream_overlap_and_unsafe_id(self):
        for output in (self.upstream, self.upstream / "nested", self.root):
            with self.subTest(output=output), self.assertRaises(ValueError):
                bridge.ingest(self.upstream, "I01", output)
        with self.assertRaises(ValueError):
            bridge.ingest(self.upstream, "../I01", self.root / "other")

    def test_input_drift_is_detected(self):
        (self.upstream / "decision.md").write_text("Changed after import", encoding="utf-8")
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("drift" in e for e in result["errors"]))

    def test_missing_input_is_detected(self):
        (self.upstream / "context.json").unlink()
        self.assertTrue(any("missing" in e for e in self.check()["errors"]))

    def test_version_change_and_boolean_version_fail(self):
        for version in (1, True):
            self.plan["selection"]["idea_version"] = version
            self.assertFalse(self.check()["ok"])

    def test_valid_pilot_with_future_unresolved_phase(self):
        self.ready()
        future = copy.deepcopy(self.plan["experiments"][0])
        future.update(experiment_id="X02", stage="confirmatory", resource_ids=["R02"], gate_ids=["G02"])
        future["sample_size"]["status"] = "pending"
        future["sample_size"]["n"] = None
        self.plan["resources"].append({"resource_id": "R02", "name": "Future samples", "status": "unknown"})
        self.plan["gates"].append({"gate_id": "G02", "description": "Future access", "status": "unknown"})
        self.plan["experiments"].append(future)
        self.assertTrue(self.check()["ok"])
        self.plan["status"] = "ready_for_execution"
        self.assertFalse(self.check()["ok"])

    def test_unknown_and_duplicate_references_fail(self):
        for field, bad in (("claim_ids", ["C404"]), ("resource_ids", ["R404"]),
                           ("gate_ids", ["G404"]), ("claim_ids", ["C01", "C01"])):
            with self.subTest(field=field):
                self.ready()
                self.plan["experiments"][0][field] = bad
                self.assertFalse(self.check()["ok"])

    def test_unavailable_resource_or_unknown_gate_blocks_scoped_execution(self):
        for table in ("resources", "gates"):
            with self.subTest(table=table):
                self.ready()
                self.plan[table][0]["status"] = "unknown"
                self.assertFalse(self.check()["ok"])

    def test_sample_size_is_not_invented_by_import_and_pending_blocks_ready(self):
        self.assertEqual(self.plan["experiments"], [])
        self.ready()
        self.plan["experiments"][0]["sample_size"].update(n=None, status="pending")
        self.assertFalse(self.check()["ok"])
        for invalid in (True, -3, 3.5):
            self.plan["experiments"][0]["sample_size"].update(n=invalid, status="justified")
            self.assertFalse(self.check()["ok"])

    def test_dependency_cycles_and_unknown_tasks_fail(self):
        self.ready()
        for deps in (["T01"], ["T404"]):
            self.plan["tasks"][0]["depends_on"] = deps
            self.assertFalse(self.check()["ok"])
        self.plan["tasks"][0]["depends_on"] = ["T02"]
        second = copy.deepcopy(self.plan["tasks"][0])
        second.update(task_id="T02", depends_on=["T01"])
        self.plan["tasks"].append(second)
        self.assertTrue(any("cycle" in e for e in self.check()["errors"]))

    def test_dependency_on_experiment_outside_scope_fails(self):
        self.ready()
        exp = copy.deepcopy(self.plan["experiments"][0])
        exp.update(experiment_id="X02", stage="confirmatory")
        self.plan["experiments"].append(exp)
        task = copy.deepcopy(self.plan["tasks"][0])
        task.update(task_id="T02", experiment_id="X02")
        self.plan["tasks"].append(task)
        self.plan["tasks"][0]["depends_on"] = ["T02"]
        self.assertTrue(any("outside execution_scope" in e for e in self.check()["errors"]))

    def test_ready_state_requires_decisions_tasks_and_review(self):
        for field in ("support", "falsify", "inconclusive", "stop"):
            self.ready()
            self.plan["experiments"][0]["decisions"][field] = ""
            self.assertFalse(self.check()["ok"])
        self.ready()
        self.plan["tasks"] = []
        self.assertFalse(self.check()["ok"])
        self.ready()
        self.plan["review"]["residual_risk"] = ""
        self.assertFalse(self.check()["ok"])

    def test_evidence_collision_and_missing_source_fail(self):
        self.ready()
        self.plan["evidence"] = [{"evidence_id": "E01", "source_id": "S404",
                                  "statement": "Fixture", "locator": "Fixture",
                                  "access_level": "full_text", "verified": True}]
        result = self.check()
        self.assertTrue(any("collide" in e for e in result["errors"]))
        self.assertTrue(any("S404" in e for e in result["errors"]))

    def test_full_execution_covers_all_claims(self):
        self.ready()
        self.plan["status"] = "ready_for_execution"
        self.assertTrue(self.check()["ok"])
        extra = copy.deepcopy(self.plan["claims"][0])
        extra["claim_id"] = "C02"
        self.plan["claims"].append(extra)
        self.assertFalse(self.check()["ok"])

    def test_theory_information_rationale_need_not_be_numeric(self):
        self.ready()
        self.plan["experiments"][0]["sample_size"].update(
            status="not_applicable", n=None, method="Proof obligation", n_definition="Not a sampling claim",
            basis="Finite lemma obligations and counterexample scope are stated in the protocol")
        self.assertTrue(self.check()["ok"])

    def test_malformed_nested_values_return_errors(self):
        for table in ("experiments", "tasks", "claims", "resources", "gates", "sources", "evidence"):
            self.ready()
            self.plan[table] = [None, "bad", 4]
            self.assertFalse(self.check()["ok"])
        self.ready()
        self.plan["status"] = []
        self.assertFalse(self.check()["ok"])
        self.ready()
        self.plan["experiments"][0]["units"] = []
        self.assertFalse(self.check()["ok"])

    def test_standalone_mode_is_supported_without_claiming_upstream_review(self):
        ctx = {"schema_version": "1.0", "mode": "standalone", "idea": {"idea_id": "I01", "version": 2},
               "evidence": [], "input_files": [], "warnings": []}
        write(self.out / "context.json", ctx)
        result = self.check()
        self.assertTrue(result["ok"])
        self.assertTrue(any("Standalone" in w for w in result["warnings"]))

    def test_cli_exit_codes(self):
        command = [sys.executable, str(ROOT / "scripts/design_bridge.py"), "verify", "--workspace", str(self.out)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.plan["selection"]["idea_version"] = 999
        write(self.out / "design.json", self.plan)
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        (self.out / "design.json").write_text("bad JSON", encoding="utf-8")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
