"""Workflow failure, recovery, scope and provenance checks on synthetic projects."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/leader.py"
spec = importlib.util.spec_from_file_location("leader", SCRIPT)
leader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(leader)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="light-leader-test-")
        self.root = Path(self.temp.name).resolve()
        self.file("inputs/source.csv", "synthetic test data\nx,y\n1,2\n")
        self.goal = {"goal": "Test a synthetic analysis handoff", "scope": "Local synthetic files only",
                     "success": ["Deliver an inspected report"], "stop_rule": "Stop after the report",
                     "authorization_basis": "Unit test fixture; no real research or external operations"}
        self.init = {"objective": self.goal}
        leader.mutate(self.root, "init", self.init)
        self.n = 0

    def tearDown(self):
        self.temp.cleanup()

    def file(self, relative, content="synthetic test report\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def source(self, relative="inputs/source.csv"):
        return {"path": relative, "locator": "Synthetic test file, complete content"}

    def task(self, key="T0001", **kwargs):
        value = {"action": "add", "id": key, "skill": "light-anaysis", "title": "Synthetic report",
                 "question": "Can the actual fixture be handed off?", "workspace": "Analysis/AN-test",
                 "inputs": [self.source()], "depends_on": [], "expected_outputs": [f"outputs/{key}.md"],
                 "acceptance": "Read the synthetic report and confirm the stated scope",
                 "stop_rule": "Stop after checking the report", "required": True,
                 "budget": {"status": "not_applicable", "basis": "Only tiny local test files"}}
        value.update(kwargs)
        return value

    def apply(self, *ops):
        self.n += 1
        revision = leader.load(self.root)[0]["revision"]
        return leader.mutate(self.root, "apply", {"request_id": f"test-{self.n}",
                            "expected_revision": revision, "operations": list(ops)})

    def start(self, key="T0001"):
        return {"action": "transition", "id": key, "status": "running", "reason": "Begin test work",
                "execution_ref": f"Local test workspace outputs/{key}.md; no external job"}

    def complete(self, key="T0001"):
        self.file(f"outputs/{key}.md")
        return {"action": "transition", "id": key, "status": "completed", "reason": "Report inspected",
                "evidence": [self.source(f"outputs/{key}.md")],
                "verification": "Read actual synthetic file; no scientific validity claim"}

    def test_start_complete_and_close(self):
        self.apply(self.task(), self.start())
        self.apply(self.complete(), {"action": "close", "status": "complete", "reason": "Scope delivered"})
        self.assertEqual(leader.report(self.root, "status")["objective"]["status"], "complete")

    def test_unknown_blocked_execution_cannot_be_hidden_by_replacement(self):
        self.apply(self.task(), self.start())
        self.apply({"action": "transition", "id": "T0001", "status": "blocked",
                    "reason": "Actual process state is unknown"})
        before = (self.root / "Workflow/workflow.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "[Rr]econcile"):
            self.apply(self.task("T0002", supersedes="T0001", reason="Retry"))
        self.assertEqual(before, (self.root / "Workflow/workflow.json").read_bytes())

    def test_unknown_blocked_execution_cannot_be_hidden_by_new_objective(self):
        self.apply(self.task(), self.start())
        self.apply({"action": "transition", "id": "T0001", "status": "blocked",
                    "reason": "Actual process state is unknown"})
        with self.assertRaisesRegex(ValueError, "[Rr]econcile"):
            self.apply({"action": "objective", "objective": self.goal, "reason": "New work"})
        result = leader.report(self.root, "status")
        self.assertEqual(result["recovery_required"][0]["id"], "T0001")
        self.assertEqual(result["recovery_required"][0]["execution_ref"], self.start()["execution_ref"])

    def test_reconciled_blocked_execution_can_be_replaced(self):
        self.apply(self.task(), self.start())
        self.apply({"action": "transition", "id": "T0001", "status": "blocked",
                    "reason": "Actual process state is unknown"})
        self.apply(self.task("T0002", supersedes="T0001", reason="Confirmed retry is needed",
                             reconciliation="Inspected native process: terminated with no reusable outputs"))
        self.apply(self.start("T0002"))
        self.assertEqual([t["id"] for t in leader.report(self.root, "status")["running"]], ["T0002"])
        self.assertEqual(leader.report(self.root, "status")["recovery_required"], [])

    def test_legacy_unreconciled_replacement_remains_visible_on_recovery(self):
        self.apply(self.task(), self.start())
        self.apply({"action": "transition", "id": "T0001", "status": "blocked", "reason": "Unknown native job"})
        data, state = leader.load(self.root)
        old = self.task("T0002", supersedes="T0001", reason="Legacy replacement without recovery")
        old["inputs"] = leader.refs(self.root, old["inputs"], bind=True)
        operation = leader.execute(self.root, state, old, bind=False)
        event = {"revision": data["revision"] + 1, "request_id": "legacy-operation",
                 "request_hash": leader.digest(old), "recorded_at": leader.now(), "operations": [operation]}
        event["event_hash"] = leader.digest(event)
        data["events"].append(event); data["revision"] += 1
        leader.atomic(self.root / "Workflow/workflow.json", leader.canonical(data))
        self.assertEqual(leader.report(self.root, "status")["recovery_required"][0]["id"], "T0001")
        with self.assertRaisesRegex(ValueError, "Reconcile"):
            self.apply({"action": "objective", "objective": self.goal, "reason": "Changed scope"})

    def test_bound_registry_cannot_disappear_without_review(self):
        self.file("project.json", json.dumps({"schema_version": "1.0", "layout_version": "1.0", "project_id": "PRJ_BOUND"}))
        (self.root / "Workflow/workflow.json").unlink()
        (self.root / "Workflow/00-Workflow总览.md").unlink()
        leader.mutate(self.root, "init", self.init)
        (self.root / "project.json").unlink()
        with self.assertRaisesRegex(ValueError, "registry is missing"):
            leader.report(self.root, "status")

    def test_dependency_prevents_premature_start(self):
        self.apply(self.task(), self.task("T0002", depends_on=["T0001"]))
        with self.assertRaisesRegex(ValueError, "need review"):
            self.apply(self.start("T0002"))
        self.assertEqual([x["id"] for x in leader.report(self.root, "next")["tasks"]], ["T0001"])

    def test_completed_dependency_releases_successor(self):
        self.apply(self.task(), self.task("T0002", depends_on=["T0001"]), self.start())
        self.apply(self.complete())
        self.assertEqual([x["id"] for x in leader.report(self.root, "next")["tasks"]], ["T0002"])

    def test_dependency_cannot_reference_self_or_future(self):
        for deps in (["T0001"], ["T0002"]):
            with self.assertRaises(ValueError):
                self.apply(self.task(depends_on=deps))

    def test_input_drift_blocks_start(self):
        self.apply(self.task())
        self.file("inputs/source.csv", "changed test data")
        self.assertFalse(leader.report(self.root, "verify")["ok"])
        with self.assertRaises(ValueError):
            self.apply(self.start())

    def test_input_drift_blocks_completion(self):
        self.apply(self.task(), self.start())
        self.file("inputs/source.csv", "changed during work")
        with self.assertRaises(ValueError):
            self.apply(self.complete())

    def test_changed_output_propagates_to_downstream(self):
        self.apply(self.task(), self.task("T0002", depends_on=["T0001"]), self.start())
        self.apply(self.complete())
        self.file("outputs/T0001.md", "new unreviewed report")
        result = leader.report(self.root, "next")
        self.assertFalse(result["tasks"])
        reasons = {x["id"]: x["reasons"] for x in result["needs_review"]}
        self.assertIn("dependency_unusable: T0001", reasons["T0002"])

    def test_missing_source_detected_read_only(self):
        self.apply(self.task())
        (self.root / "inputs/source.csv").unlink()
        before = (self.root / "Workflow/workflow.json").read_bytes()
        self.assertFalse(leader.report(self.root, "verify")["ok"])
        self.assertEqual(before, (self.root / "Workflow/workflow.json").read_bytes())

    def test_completion_needs_real_outputs_and_verification(self):
        self.apply(self.task(), self.start())
        op = self.complete()
        for field, value in [("evidence", []), ("verification", "")]:
            broken = dict(op, **{field: value})
            with self.assertRaises(ValueError):
                self.apply(broken)
        self.apply(op)

    def test_completion_must_cover_promised_output(self):
        self.apply(self.task(), self.start())
        op = self.complete()
        self.file("other.md")
        op["evidence"] = [self.source("other.md")]
        with self.assertRaises(ValueError):
            self.apply(op)

    def test_no_direct_pending_to_complete(self):
        self.apply(self.task())
        with self.assertRaises(ValueError):
            self.apply(self.complete())

    def test_atomic_batch_rejection(self):
        before = (self.root / "Workflow/workflow.json").read_bytes()
        with self.assertRaises(ValueError):
            self.apply(self.task(), self.task("T0002", depends_on=["MISSING"]))
        self.assertEqual(before, (self.root / "Workflow/workflow.json").read_bytes())

    def test_revision_rejects_stale_writer(self):
        self.apply(self.task())
        with self.assertRaisesRegex(ValueError, "Stale revision"):
            leader.mutate(self.root, "apply", {"request_id": "old", "expected_revision": 0,
                                                "operations": [self.start()]})

    def test_request_replay_is_idempotent(self):
        value = {"request_id": "one", "expected_revision": 0, "operations": [self.task()]}
        leader.mutate(self.root, "apply", value)
        result = leader.mutate(self.root, "apply", value)
        self.assertTrue(result["idempotent"])
        self.assertEqual(result["revision"], 1)
        value["operations"][0]["title"] = "different"
        with self.assertRaisesRegex(ValueError, "different content"):
            leader.mutate(self.root, "apply", value)

    def test_dry_run_does_not_write_or_create_workspaces(self):
        before = (self.root / "Workflow/workflow.json").read_bytes()
        leader.mutate(self.root, "apply", {"request_id": "dry", "expected_revision": 0,
                                           "operations": [self.task()]}, True)
        self.assertEqual(before, (self.root / "Workflow/workflow.json").read_bytes())
        self.assertFalse((self.root / "Analysis").exists())
        (self.root / "Workflow/workflow.json").unlink()
        (self.root / "Workflow/00-Workflow总览.md").unlink()
        (self.root / "Workflow").rmdir()
        leader.mutate(self.root, "init", self.init, True)
        self.assertFalse((self.root / "Workflow").exists())

    def test_lock_prevents_simultaneous_writes(self):
        self.file("Workflow/.write.lock", "test writer")
        with self.assertRaisesRegex(ValueError, "lock exists"):
            self.apply(self.task())

    def test_view_failure_does_not_hide_committed_work(self):
        self.file("Workflow/00-Workflow总览.md", "handwritten content")
        result = self.apply(self.task())
        self.assertIn("view_warning", result)
        self.assertEqual(leader.load(self.root)[0]["revision"], 1)
        self.assertEqual((self.root / "Workflow/00-Workflow总览.md").read_text(), "handwritten content")

    def test_atomic_replace_failure_preserves_previous_state(self):
        before = (self.root / "Workflow/workflow.json").read_bytes()
        with patch.object(leader.os, "replace", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.apply(self.task())
        self.assertEqual(before, (self.root / "Workflow/workflow.json").read_bytes())
        self.assertFalse((self.root / "Workflow/.write.lock").exists())

    def test_path_escape_private_config_and_self_evidence_rejected(self):
        for relative in ("../outside", "C:/outside", "a\\b", ".", ".env", "Workflow/workflow.json"):
            with self.assertRaises(ValueError, msg=relative):
                self.apply(self.task(inputs=[self.source(relative)]))

    def test_junction_evidence_is_rejected_on_windows(self):
        if os.name != "nt":
            self.skipTest("Windows junction check")
        link = self.root / "linked"
        result = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 "New-Item -ItemType Junction -Path '" + str(link) + "' -Target '" + str(self.root / "inputs") + "' | Out-Null"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            with self.assertRaises(ValueError):
                self.apply(self.task(inputs=[self.source("linked/source.csv")]))
        finally:
            os.rmdir(link)

    def test_project_identity_mismatch(self):
        self.file("project.json", json.dumps({"schema_version": "1.0", "layout_version": "1.0", "project_id": "PRJ_A"}))
        (self.root / "Workflow/workflow.json").unlink()
        (self.root / "Workflow/00-Workflow总览.md").unlink()
        leader.mutate(self.root, "init", self.init)
        self.file("project.json", json.dumps({"schema_version": "1.0", "layout_version": "1.0", "project_id": "PRJ_B"}))
        with self.assertRaisesRegex(ValueError, "another project"):
            leader.load(self.root)

    def test_project_can_be_relocated(self):
        self.apply(self.task(), self.start())
        self.apply(self.complete())
        with tempfile.TemporaryDirectory() as other:
            moved = Path(other) / "moved"
            shutil.copytree(self.root, moved)
            self.assertTrue(leader.report(moved, "verify")["ok"])

    def test_running_work_is_reported_and_not_restarted(self):
        self.apply(self.task(), self.start())
        result = leader.report(self.root, "next")
        self.assertFalse(result["tasks"])
        self.assertEqual(result["running"][0]["id"], "T0001")
        with self.assertRaises(ValueError):
            self.apply(self.start())

    def test_blocked_work_needs_reconciliation_before_resume(self):
        self.apply(self.task(), self.start(), {"action": "transition", "id": "T0001", "status": "blocked", "reason": "Job status unknown"})
        op = {"action": "transition", "id": "T0001", "status": "pending", "reason": "Resume test"}
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.apply(op)
        op["reconciliation"] = "Confirmed no process launched; same inputs retained"
        self.apply(op)

    def test_running_cancel_needs_actual_reconciliation(self):
        self.apply(self.task(), self.start())
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.apply({"action": "transition", "id": "T0001", "status": "cancelled", "reason": "Stop"})

    def test_hold_does_not_cancel_running_job_and_allows_reconciliation(self):
        self.apply(self.task(), self.start(), {"action": "close", "status": "hold", "reason": "User paused new work"})
        self.assertTrue(leader.report(self.root, "status")["running"])
        self.apply(self.complete())
        self.assertEqual(leader.load(self.root)[1]["tasks"]["T0001"]["status"], "completed")

    def test_required_cancelled_work_does_not_count_as_delivered(self):
        self.apply(self.task(), {"action": "transition", "id": "T0001", "status": "cancelled", "reason": "Test cancellation"})
        with self.assertRaisesRegex(ValueError, "Required work remains"):
            self.apply({"action": "close", "status": "complete", "reason": "Claim delivery"})

    def test_no_empty_objective_completion(self):
        with self.assertRaises(ValueError):
            self.apply({"action": "close", "status": "complete", "reason": "Empty plan"})

    def test_retry_has_new_identity_and_preserves_required_work(self):
        self.apply(self.task(), self.start(), {"action": "transition", "id": "T0001", "status": "failed", "reason": "Synthetic failure; no process alive"})
        with self.assertRaises(ValueError):
            self.apply(self.start())
        with self.assertRaisesRegex(ValueError, "required responsibility"):
            self.apply(self.task("T0002", supersedes="T0001", reason="retry", required=False))
        self.apply(self.task("T0002", supersedes="T0001", reason="retry"), self.start("T0002"))
        self.apply(self.complete("T0002"), {"action": "close", "status": "complete", "reason": "Replacement delivered"})
        self.assertEqual(leader.load(self.root)[1]["tasks"]["T0001"]["status"], "failed")

    def test_superseded_result_is_not_reusable_by_old_dependents(self):
        self.apply(self.task(), self.task("T0002", depends_on=["T0001"]), self.start())
        self.apply(self.complete())
        self.apply(self.task("T0003", supersedes="T0001", reason="Different interpretation requires new report"))
        self.assertIn("dependency_unusable: T0001", leader.assessment(self.root, leader.load(self.root)[1])["T0002"])

    def test_unknown_budget_blocks_paid_execution_but_not_diagnosis(self):
        self.apply(self.task(budget={"status": "unknown", "basis": "Compute limit not supplied"}),
                   self.task("T0002", required=False))
        self.assertEqual([x["id"] for x in leader.report(self.root, "next")["tasks"]], ["T0002"])
        with self.assertRaisesRegex(ValueError, "budget"):
            self.apply(self.start())

    def test_bounded_budget_needs_actual_limits(self):
        with self.assertRaises(ValueError):
            self.apply(self.task(budget={"status": "bounded", "basis": "Test allocation"}))

    def test_objective_change_retains_history_and_current_scope(self):
        self.apply(self.task())
        goal = dict(self.goal, goal="Different user deliverable")
        self.apply({"action": "objective", "objective": goal, "reason": "User changed request"})
        result = leader.report(self.root, "next")
        self.assertFalse(result["tasks"])
        self.assertEqual(result["objective"]["id"], "OBJ-0002")
        self.assertIn("T0001", leader.load(self.root)[1]["tasks"])

    def test_new_objective_and_closure_can_share_one_atomic_batch(self):
        completion = self.complete()
        self.apply({"action": "objective", "objective": self.goal, "reason": "New bounded scope"},
                   self.task(), self.start(), completion,
                   {"action": "close", "status": "complete", "reason": "All new work accepted"})
        data, state = leader.load(self.root)
        self.assertEqual(state["objective"]["status"], "complete")
        self.assertEqual(data["events"][0]["operations"][0]["objective"]["status"], "active")

    def test_objective_change_requires_running_work_reconciled(self):
        self.apply(self.task(), self.start())
        with self.assertRaises(ValueError):
            self.apply({"action": "objective", "objective": self.goal, "reason": "Change scope"})

    def test_event_corruption_is_detected(self):
        self.apply(self.task())
        path = self.root / "Workflow/workflow.json"
        value = leader.read(path)
        value["events"][0]["operations"][0]["title"] = "tampered"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "event changed"):
            leader.load(self.root)

    def test_json_duplicate_keys_and_nonfinite_numbers_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":1e999}'):
            path = self.file("invalid.json", raw)
            with self.assertRaises(ValueError):
                leader.read(path)

    def test_source_package_cannot_be_used_as_research_project(self):
        with self.assertRaises(ValueError):
            leader.project_root(SCRIPT.parents[2])

    def test_standalone_copy_runs_without_siblings(self):
        with tempfile.TemporaryDirectory() as parent:
            skill = Path(parent) / "installed/light-leader"
            shutil.copytree(SCRIPT.parent, skill / "scripts")
            shutil.copytree(SCRIPT.parents[1] / "assets", skill / "assets")
            project = Path(parent) / "research"
            project.mkdir()
            value = project / "objective.json"
            value.write_text(json.dumps(self.init), encoding="utf-8")
            process = subprocess.run([sys.executable, str(skill / "scripts/leader.py"), "init", "--project", str(project), "--spec", str(value)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertTrue((project / "Workflow/workflow.json").is_file())


if __name__ == "__main__":
    unittest.main()
