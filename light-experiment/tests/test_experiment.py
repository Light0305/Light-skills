"""Synthetic process/integrity regressions; no scientific efficacy claims."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("experiment", ROOT / "scripts/experiment.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def make_design(folder):
    folder.mkdir(parents=True)
    context = {"schema_version": "1.0", "mode": "standalone",
               "idea": {"idea_id": "I01", "version": 2}, "input_files": [], "evidence": [], "papers": []}
    plan = {
        "schema_version": "1.0", "design_id": "D01", "version": 3,
        "selection": {"idea_id": "I01", "idea_version": 2}, "status": "ready_for_pilot",
        "objective": "Synthetic known-answer calculation and evidence retention; no scientific claim",
        "constraints": {"compute": "local standard library only"},
        "claims": [{"claim_id": "C01", "statement": "The fixture returns the sum of squares of 1,2,3",
                    "prediction": "Raw result equals 14", "rival": "Broken path, arithmetic or missing output",
                    "scope": "Synthetic fixture only", "evidence_ids": []}],
        "sources": [], "evidence": [],
        "resources": [{"resource_id": "RS01", "name": "Local deterministic fixture", "status": "available",
                       "specification": "Python standard library", "locator": str(__file__),
                       "basis": "Fixture constructed by setUp, not an external research resource"}],
        "gates": [{"gate_id": "G01", "description": "Local fixture is present", "status": "confirmed",
                   "basis": "Written by the test"}],
        "experiments": [{
            "experiment_id": "X01", "name": "Known-answer pilot", "stage": "pilot", "claim_ids": ["C01"],
            "resource_ids": ["RS01"], "gate_ids": ["G01"], "purpose": "Check code-to-raw-output trace",
            "design": "Deterministic known-answer synthetic test",
            "units": {"allocation": "No allocation: deterministic fixture", "independent": "One calculation",
                      "observation": "Three input numbers in a single calculation"},
            "conditions": ["Known input [1,2,3]"], "allocation": "Not randomized; deterministic technical test",
            "procedure": "Run the local worker with frozen config; inspect raw JSON",
            "measurement": {"primary": "Sum of squares", "operationalization": "Integer sum, dimensionless",
                            "timepoint": "At process exit", "qc": "Three inputs; raw JSON contains 14"},
            "sample_size": {"n": 1, "n_definition": "One deterministic fixture, not an efficacy sample",
                            "method": "Known-answer verification", "basis": "Exact answer 1+4+9=14",
                            "status": "justified"},
            "analysis": "Exact equality to 14, no statistical inference",
            "decisions": {"support": "Fixture passes if answer and evidence are retained",
                          "falsify": "Wrong exact answer defeats this implementation",
                          "inconclusive": "A crash does not establish arithmetic validity",
                          "stop": "Stop within the local campaign budget"}}],
        "tasks": [{"task_id": "T01", "experiment_id": "X01", "depends_on": [], "inputs": ["Local config"],
                   "action": "Run deterministic fixture", "outputs": ["raw.json"], "acceptance": "Answer is 14",
                   "owner": "Test harness", "effort": "One short CPU process, no external service"}],
        "execution_scope": ["X01"], "budget": {"summary": "Short synthetic processes", "basis": "Test harness",
                                                 "limit": "Per-test campaign limits"},
        "review": {"strongest_objection": "Toy test does not validate real research",
                   "response": "Only assess process and recording invariants", "residual_risk": "Real workloads untested"},
        "history": []}
    write(folder / "context.json", context)
    write(folder / "design.json", plan)
    (folder / "plan.md").write_text("Synthetic arithmetic and provenance test only.", encoding="utf-8")
    (folder / "protocols").mkdir()
    (folder / "protocols/check.txt").write_text("Expected answer: 14", encoding="utf-8")
    return plan


WORKER = '''import json, os, pathlib, subprocess, sys, time
cfg_path = pathlib.Path(sys.argv[1])
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
out = pathlib.Path(os.environ["LIGHT_EXPERIMENT_OUT"])
sys.stdout.buffer.write("原始日志\\n".encode("utf-8")); sys.stdout.flush()
print("diagnostic stderr", file=sys.stderr, flush=True)
if cfg["mode"] == "fail":
    (out/"partial.txt").write_text("partial evidence", encoding="utf-8")
    raise SystemExit(7)
if cfg["mode"] == "timeout":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    (out/"child.json").write_text(json.dumps({"pid":child.pid}))
    time.sleep(120)
if cfg["mode"] == "sleep": time.sleep(2)
if cfg["mode"] == "mutate": cfg_path.write_text("{}", encoding="utf-8")
if cfg["mode"] != "missing":
    (out/"raw.json").write_text(json.dumps({"sum_squares":sum(v*v for v in cfg["values"]),
                                          "values":cfg["values"], "args":sys.argv[2:]}),encoding="utf-8")
    (out/"manifest.json").write_text("Output also named manifest; must be fingerprinted",encoding="utf-8")
'''


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="light-experiment-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.design = self.base / "上游设计"
        self.source = self.base / "计算 project"
        self.source.mkdir()
        self.worker = self.source / "worker.py"
        self.worker.write_text(WORKER, encoding="utf-8")
        self.config = self.source / "config.json"
        write(self.config, {"mode": "ok", "values": [1, 2, 3]})
        self.plan = make_design(self.design)
        self.workspace = self.base / "执行 records"
        self.before = {p.relative_to(self.design).as_posix(): p.read_bytes() for p in self.design.rglob("*") if p.is_file()}
        tool.init(self.design, self.workspace, 8, 60, "Synthetic bounded validation")

    def make_spec(self, run_id="R001", mode="ok", timeout=15):
        write(self.config, {"mode": mode, "values": [1, 2, 3]})
        return {"schema_version": "1.0", "run_id": run_id, "experiment_id": "X01", "task_id": "T01",
                "kind": "smoke", "purpose": "Known-answer synthetic check", "parent_run_id": None,
                "unit": {"unit_id": "U01", "seed": None}, "parameters": {"values": [1, 2, 3]},
                "argv": [sys.executable, str(self.worker), str(self.config)], "cwd": str(self.source),
                "timeout_seconds": timeout, "environment": {},
                "provenance": {"environment": "This Python standard library", "hardware": "Local test CPU",
                               "determinism": "Exact integer arithmetic, no random seed needed"},
                "inputs": [{"path": str(self.worker), "role": "code", "snapshot": True},
                           {"path": str(self.config), "role": "config", "snapshot": True}],
                "expected_outputs": [{"path": "raw.json", "role": "raw", "required": True, "min_bytes": 1}]}

    def prepare(self, run_id="R001", mode="ok", timeout=15, spec=None):
        spec = self.make_spec(run_id, mode, timeout) if spec is None else spec
        path = self.base / (run_id + "-spec.json")
        write(path, spec)
        return tool.prepare(self.workspace, path)

    def assessment(self, run_id="R001", outcome="support", qc="passed", value=14):
        item = {"schema_version": "1.0", "run_id": run_id, "assessor": "Synthetic test harness",
                "qc_status": qc, "qc_basis": "Known-answer check, not scientific evidence",
                "outcome": outcome, "claim_ids": ["C01"],
                "metrics": [{"name": "sum_squares", "value": value, "unit": "dimensionless",
                             "artifact": "outputs/raw.json", "locator": "JSON $.sum_squares"}],
                "deviations": [], "limitations": ["Synthetic test only"], "next_action": "Stop synthetic pilot"}
        path = self.base / "assessment.json"
        write(path, item)
        return path

    def test_frozen_handoff_preserves_identity_bytes_and_protocols(self):
        campaign = tool.read(self.workspace / "campaign.json")
        self.assertEqual((campaign["design_id"], campaign["design_version"]), ("D01", 3))
        self.assertEqual(campaign["selection"], {"idea_id": "I01", "idea_version": 2})
        self.assertEqual(self.before, {p.relative_to(self.design).as_posix(): p.read_bytes() for p in self.design.rglob("*") if p.is_file()})
        self.assertEqual((self.workspace / "inputs/design/protocols/check.txt").read_text(), "Expected answer: 14")
        self.assertTrue(tool.verify(self.workspace)["ok"])

    def test_upstream_can_evolve_without_silent_reimport(self):
        self.plan["version"] = 4
        write(self.design / "design.json", self.plan)
        result = tool.verify(self.workspace)
        self.assertTrue(result["ok"])
        self.assertTrue(any("Upstream original changed" in w for w in result["warnings"]))
        self.assertEqual(tool.read(self.workspace / "inputs/design/design.json")["version"], 3)

    def test_local_snapshot_and_budget_drift_are_errors(self):
        for target in ["campaign.json", "inputs/design/plan.md"]:
            with self.subTest(target=target):
                path = self.workspace / target
                before = path.read_bytes()
                path.write_bytes(before + b" ")
                self.assertFalse(tool.verify(self.workspace)["ok"])
                path.write_bytes(before)

    def test_refuses_overwrite_overlap_and_skill_outputs(self):
        for out in [self.workspace, self.design, self.design / "nested", self.base, ROOT / "data-test"]:
            with self.subTest(out=out), self.assertRaises(ValueError):
                tool.init(self.design, out, 2, 5, "Fixture")
        self.assertEqual(tool.read(self.workspace / "campaign.json")["budget"]["max_runs"], 8)

    def test_draft_import_does_not_authorize_launch(self):
        self.plan["status"] = "draft"
        write(self.design / "design.json", self.plan)
        alternate = self.base / "draft-execution"
        tool.init(self.design, alternate, 2, 5, "Fixture")
        self.workspace = alternate
        with self.assertRaisesRegex(ValueError, "not ready"):
            self.prepare()

    def test_identity_scope_resource_gate_and_cycle_checks(self):
        context = tool.read(self.design / "context.json")
        variants = []
        p = copy.deepcopy(self.plan); p["selection"]["idea_version"] = 5; variants.append(p)
        p = copy.deepcopy(self.plan); p["version"] = True; variants.append(p)
        p = copy.deepcopy(self.plan); p["resources"][0]["status"] = "unknown"; variants.append(p)
        p = copy.deepcopy(self.plan); p["gates"][0]["status"] = "blocked"; variants.append(p)
        p = copy.deepcopy(self.plan); p["tasks"][0]["depends_on"] = ["T01"]; variants.append(p)
        p = copy.deepcopy(self.plan); p["experiments"][0]["stage"] = "confirmatory"; variants.append(p)
        for index, plan in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                tool.handoff(plan, context, ["X01"], ready=True)
        with self.assertRaises(ValueError):
            tool.handoff(self.plan, context, ["X404"], ready=True)

    def test_unresolved_future_phase_does_not_block_scoped_pilot(self):
        p = copy.deepcopy(self.plan)
        future = copy.deepcopy(p["experiments"][0])
        future.update(experiment_id="X02", stage="confirmatory", resource_ids=["RS02"])
        future["sample_size"]["status"] = "pending"
        p["experiments"].append(future)
        p["resources"].append({"resource_id": "RS02", "status": "unknown"})
        tool.handoff(p, tool.read(self.design / "context.json"), ["X01"], ready=True)

    def test_prepare_does_not_run_and_refuses_reused_id(self):
        self.prepare()
        folder = self.workspace / "runs/R001"
        self.assertFalse((folder / "started.json").exists())
        self.assertFalse((folder / "outputs").exists())
        with self.assertRaises(ValueError):
            self.prepare()

    def test_input_drift_blocks_launch_without_spending_budget(self):
        self.prepare()
        self.worker.write_text(WORKER + "\n# modified", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Input drift"):
            tool.run(self.workspace, "R001")
        self.assertEqual(tool.budget_state(self.workspace)["attempts"], 0)

    def test_spec_tampering_blocks_launch(self):
        self.prepare()
        path = self.workspace / "runs/R001/spec.json"
        value = tool.read(path); value["argv"] = [sys.executable, "-c", "print('different')"]
        write(path, value)
        with self.assertRaisesRegex(ValueError, "Fingerprint drift"):
            tool.run(self.workspace, "R001")

    def test_output_traversal_bad_ids_bad_timeout_and_secret_env_refused(self):
        for key, value in [("run_id", "../escape"), ("timeout_seconds", True),
                           ("timeout_seconds", float("inf")), ("environment", {"API_KEY": "do-not-record"})]:
            spec = self.make_spec(); spec[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.prepare(spec=spec)
        for name in ["../escape", "..\\escape", "/outside", "C:\\outside", "x/../../escape"]:
            spec = self.make_spec(); spec["expected_outputs"][0]["path"] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.prepare(spec=spec)

    def test_success_retains_raw_bytes_outputs_and_pending_qc(self):
        self.prepare()
        result = tool.run(self.workspace, "R001")
        self.assertTrue(result["ok"])
        self.assertEqual(result["returncode"], 0)
        folder = self.workspace / "runs/R001"
        self.assertEqual((folder / "stdout.log").read_bytes(), "原始日志\n".encode("utf-8"))
        self.assertIn(b"diagnostic stderr", (folder / "stderr.log").read_bytes())
        self.assertEqual(tool.read(folder / "outputs/raw.json")["sum_squares"], 14)
        self.assertIn("outputs/manifest.json", {x["path"] for x in tool.read(folder / "manifest.json")["records"]})
        check = tool.verify(self.workspace)
        self.assertTrue(check["ok"])
        self.assertTrue(any("QC/interpretation pending" in w for w in check["warnings"]))
        with self.assertRaises(ValueError):
            tool.run(self.workspace, "R001")

    def test_zero_exit_with_missing_outputs_is_not_success(self):
        self.prepare(mode="missing")
        result = tool.run(self.workspace, "R001")
        self.assertFalse(result["ok"])
        self.assertEqual(result["process_status"], "succeeded")
        self.assertFalse(result["artifacts_ok"])
        self.assertTrue(tool.verify(self.workspace)["ok"])

    def test_crash_keeps_partial_output_and_real_exit_code(self):
        self.prepare(mode="fail")
        result = tool.run(self.workspace, "R001")
        self.assertFalse(result["ok"])
        self.assertEqual((result["process_status"], result["returncode"]), ("failed", 7))
        self.assertTrue((self.workspace / "runs/R001/outputs/partial.txt").exists())
        self.assertEqual(result["budget"]["attempts"], 1)

    def test_timeout_stops_process_tree_and_retains_evidence(self):
        self.prepare(mode="timeout", timeout=1.5)
        result = tool.run(self.workspace, "R001")
        self.assertEqual(result["process_status"], "timed_out")
        self.assertTrue(result["termination_confirmed"], result)
        child = tool.read(self.workspace / "runs/R001/outputs/child.json")
        self.assertFalse(tool.pid_alive(child["pid"]))
        self.assertTrue(tool.verify(self.workspace)["ok"])

    def test_campaign_count_limit_includes_failures(self):
        alternative = self.base / "limited"
        tool.init(self.design, alternative, 1, 15, "One allowed attempt")
        self.workspace = alternative
        self.prepare(mode="fail"); tool.run(self.workspace, "R001")
        self.prepare("R002")
        with self.assertRaisesRegex(ValueError, "run budget exhausted"):
            tool.run(self.workspace, "R002")

    def test_remaining_wall_budget_caps_larger_run_timeout(self):
        alternative = self.base / "wall-limited"
        tool.init(self.design, alternative, 3, 0.15, "Short timeout test")
        self.workspace = alternative
        self.prepare(mode="sleep", timeout=30)
        result = tool.run(self.workspace, "R001")
        self.assertEqual(result["process_status"], "timed_out")
        started = tool.read(self.workspace / "runs/R001/started.json")
        self.assertLessEqual(started["effective_timeout_seconds"], 0.15)
        self.prepare("R002")
        with self.assertRaisesRegex(ValueError, "wall budget exhausted"):
            tool.run(self.workspace, "R002")

    def test_input_mutation_during_run_is_recorded_as_invalid(self):
        self.prepare(mode="mutate")
        result = tool.run(self.workspace, "R001")
        self.assertFalse(result["ok"])
        self.assertTrue(result["input_drift_after"])
        self.assertFalse(tool.verify(self.workspace)["ok"])

    def test_output_tampering_and_untracked_files_detected(self):
        self.prepare(); tool.run(self.workspace, "R001")
        folder = self.workspace / "runs/R001"
        (folder / "outputs/raw.json").write_text("{}")
        self.assertFalse(tool.verify(self.workspace)["ok"])
        (folder / "outputs/new.txt").write_text("untracked")
        self.assertTrue(any("Untracked" in e for e in tool.verify(self.workspace)["errors"]))

    def test_stale_output_dir_is_refused(self):
        self.prepare()
        output = self.workspace / "runs/R001/outputs"
        output.mkdir(); (output / "raw.json").write_text("old result")
        with self.assertRaisesRegex(ValueError, "pre-exist"):
            tool.run(self.workspace, "R001")

    def test_changed_numeric_environment_blocks_without_spending_attempt(self):
        self.prepare()
        previous = os.environ.get("OMP_NUM_THREADS")
        os.environ["OMP_NUM_THREADS"] = "999"
        try:
            with self.assertRaisesRegex(ValueError, "Numerical environment changed"):
                tool.run(self.workspace, "R001")
        finally:
            if previous is None:
                os.environ.pop("OMP_NUM_THREADS", None)
            else:
                os.environ["OMP_NUM_THREADS"] = previous
        self.assertEqual(tool.budget_state(self.workspace)["attempts"], 0)

    def test_corrupt_budget_record_cannot_enable_more_compute(self):
        self.prepare(); tool.run(self.workspace, "R001")
        path = self.workspace / "runs/R001/result.json"
        changed = tool.read(path); changed["wall_seconds"] = 0; write(path, changed)
        self.prepare("R002")
        with self.assertRaisesRegex(ValueError, "Fingerprint drift"):
            tool.run(self.workspace, "R002")

    def test_dependency_artifact_changes_prevent_launch(self):
        self.prepare(); tool.run(self.workspace, "R001")
        tool.assess(self.workspace, "R001", self.assessment())
        (self.workspace / "runs/R001/outputs/raw.json").write_text("modified")
        spec = self.make_spec("R002"); spec["depends_on_runs"] = ["R001"]
        self.prepare("R002", spec=spec)
        with self.assertRaisesRegex(ValueError, "Fingerprint drift"):
            tool.run(self.workspace, "R002")

    def test_assessment_and_correction_preserve_history(self):
        self.prepare(); tool.run(self.workspace, "R001")
        first = tool.assess(self.workspace, "R001", self.assessment())
        second = tool.assess(self.workspace, "R001", self.assessment(outcome="inconclusive"))
        paths = sorted((self.workspace / "runs/R001/assessments").glob("*.json"))
        self.assertEqual(len(paths), 2)
        self.assertEqual(tool.read(paths[-1])["supersedes"], first["assessment_id"] + ".json")
        self.assertNotEqual(first["assessment_id"], second["assessment_id"])
        self.assertTrue(tool.verify(self.workspace)["ok"])

    def test_failed_or_incomplete_run_cannot_pass_qc(self):
        self.prepare(mode="missing"); tool.run(self.workspace, "R001")
        with self.assertRaisesRegex(ValueError, "cannot pass QC"):
            tool.assess(self.workspace, "R001", self.assessment())

    def test_metric_locator_must_exist_and_values_must_be_finite(self):
        self.prepare(); tool.run(self.workspace, "R001")
        path = self.assessment()
        item = tool.read(path); item["metrics"][0]["artifact"] = "outputs/absent.json"; write(path, item)
        with self.assertRaisesRegex(ValueError, "artifact is missing"):
            tool.assess(self.workspace, "R001", path)
        path = self.assessment(value=float("nan"))
        with self.assertRaises(ValueError):
            tool.assess(self.workspace, "R001", path)

    def test_prerequisite_needs_explicit_passed_qc(self):
        self.prepare(); tool.run(self.workspace, "R001")
        spec = self.make_spec("R002"); spec["depends_on_runs"] = ["R001"]
        self.prepare("R002", spec=spec)
        with self.assertRaisesRegex(ValueError, "Unaccepted prerequisite"):
            tool.run(self.workspace, "R002")
        tool.assess(self.workspace, "R001", self.assessment())
        self.assertTrue(tool.run(self.workspace, "R002")["ok"])

    def test_append_notes_keep_unknown_occurrence_time(self):
        path = self.base / "note.json"
        write(path, {"event_type": "observation", "occurred_at": None, "actor": "Test operator",
                     "observation": "Retrospective fixture note", "evidence_refs": [], "retrospective": True})
        first = tool.note(self.workspace, path); second = tool.note(self.workspace, path)
        self.assertNotEqual(first["event_id"], second["event_id"])
        saved = tool.read(self.workspace / "events" / (first["event_id"] + ".json"))
        self.assertIsNone(saved["occurred_at"])
        self.assertTrue(saved["recorded_at"].endswith("+00:00"))

    def test_command_args_are_literal_without_shell_interpretation(self):
        spec = self.make_spec()
        literal = "literal & echo not-a-command; $(also-literal)"
        spec["argv"].append(literal)
        self.prepare(spec=spec); tool.run(self.workspace, "R001")
        raw = tool.read(self.workspace / "runs/R001/outputs/raw.json")
        self.assertEqual(raw["args"], [literal])

    def test_stale_lock_blocks_mutations(self):
        (self.workspace / ".operation.lock").write_text("manual lock")
        with self.assertRaisesRegex(ValueError, "locked"):
            self.prepare()

    def test_duplicate_json_and_nonfinite_constants_rejected(self):
        path = self.base / "bad.json"
        for content in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}']:
            path.write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                tool.read(path)

    def test_interrupted_attempt_blocks_then_recovers_without_fabricated_end(self):
        self.prepare()
        folder = self.workspace / "runs/R001"
        write(folder / "started.json", {"started_at": tool.now(), "runner_pid": 2147483000})
        (folder / "outputs").mkdir()
        self.prepare("R002")
        with self.assertRaisesRegex(ValueError, "unknown/live"):
            tool.run(self.workspace, "R002")
        result = tool.recover(self.workspace, "R001", "Synthetic absent PID; no real experiment was started")
        self.assertTrue(result["ok"])
        recovered = tool.read(folder / "result.json")
        self.assertIsNone(recovered["ended_at"])
        self.assertEqual(recovered["recorded_by"], "operator_recovery")
        self.assertTrue(tool.run(self.workspace, "R002")["ok"])

    def test_recovery_refuses_live_runner(self):
        self.prepare()
        write(self.workspace / "runs/R001/started.json", {"started_at": tool.now(), "runner_pid": os.getpid()})
        with self.assertRaisesRegex(ValueError, "still exists"):
            tool.recover(self.workspace, "R001", "Should fail: test process is alive")

    def test_cli_roundtrip_and_exit_status(self):
        self.prepare()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/experiment.py"), "run",
                                 "--workspace", str(self.workspace), "--run-id", "R001"],
                                capture_output=True, encoding="utf-8", timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
        duplicate = subprocess.run([sys.executable, str(ROOT / "scripts/experiment.py"), "run",
                                    "--workspace", str(self.workspace), "--run-id", "R001"],
                                   capture_output=True, encoding="utf-8", timeout=10)
        self.assertEqual(duplicate.returncode, 2)


if __name__ == "__main__":
    unittest.main()
