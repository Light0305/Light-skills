"""Optional source-package integration checks using native tools, synthetic inputs only."""
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_leader as fixtures

PACK = Path(__file__).resolve().parents[2]
leader = fixtures.leader


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root

    def cli(self, script, *args, expected=0):
        path = PACK / script
        if not path.is_file():
            self.skipTest("Optional sibling source not installed: " + script)
        process = subprocess.run([sys.executable, "-X", "utf8", str(path), *map(str, args)],
                                 capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        return json.loads(process.stdout) if process.stdout.strip() else {"error": process.stderr}

    def test_directory_manager_preserves_native_workflow_overview(self):
        script = "project-layout/scripts/project.py"
        self.cli(script, "init", "--root", self.root, "--name", "Synthetic integration project")
        self.cli(script, "register", "--root", self.root, "--kind", "workflow", "--title", "Current scope", "--path", "Workflow")
        before = (self.root / "Workflow/00-Workflow总览.md").read_bytes()
        self.cli(script, "refresh", "--root", self.root)
        self.assertEqual(before, (self.root / "Workflow/00-Workflow总览.md").read_bytes())
        result = self.cli(script, "check", "--root", self.root)
        self.assertTrue(result["ok"])

    def test_native_analysis_and_memory_share_actual_source_drift(self):
        target = self.root / "Analysis/AN-test"
        self.cli("light-analysis/scripts/analysis_bridge.py", "ingest", "--input", self.root / "inputs/source.csv", "--out", target)
        native = json.loads((target / "analysis.json").read_text(encoding="utf-8"))
        self.assertEqual(native["status"], "draft")
        self.fixture.apply(self.fixture.task(expected_outputs=["Analysis/AN-test/analysis.json"],
                           acceptance="Check only native draft identity; no scientific acceptance"), self.fixture.start())
        self.fixture.apply({"action": "transition", "id": "T0001", "status": "completed",
                            "reason": "Only intake task delivered", "evidence": [self.fixture.source("Analysis/AN-test/analysis.json")],
                            "verification": "Read native status=draft; scientific analysis is still pending"})
        self.cli("light-memory/scripts/memory.py", "init", "--project", self.root, "--name", "Synthetic integration")
        capture = {"schema_version": "1.0", "capture_id": "native-draft-test", "label": "Synthetic native draft observation",
                   "items": [{"kind": "fact", "scope": "analysis:test", "slot": "native.status", "text": "Synthetic intake is draft, not a completed scientific analysis",
                              "epistemic": "verified_observation", "sources": [{"kind": "file", "path": "Analysis/AN-test/analysis.json", "locator": "status"}]}], "changes": []}
        path = self.fixture.file("capture.json", json.dumps(capture))
        self.cli("light-memory/scripts/memory.py", "capture", "--project", self.root, "--spec", path)
        self.assertTrue(leader.report(self.root, "verify")["ok"])
        self.cli("light-memory/scripts/memory.py", "verify", "--project", self.root)
        native["integration_test_note"] = "Synthetic input changed after capture"
        self.fixture.file("Analysis/AN-test/analysis.json", json.dumps(native))
        self.assertFalse(leader.report(self.root, "verify")["ok"])
        memory = self.cli("light-memory/scripts/memory.py", "verify", "--project", self.root, expected=1)
        self.assertTrue(memory["integrity_ok"])
        self.assertTrue(memory["needs_review"])

    def test_directory_manager_allocates_one_empty_workflow_for_native_init(self):
        root = self.root / "new-project"
        script = "project-layout/scripts/project.py"
        self.cli(script, "init", "--root", root, "--name", "Synthetic new project")
        allocated = self.cli(script, "add", "--root", root, "--kind", "workflow", "--title", "Current work")
        self.assertEqual(allocated["record"]["key"], "WF-0001")
        self.assertEqual(list((root / "Workflow").iterdir()), [])
        leader.mutate(root, "init", self.fixture.init)
        self.assertEqual(leader.load(root)[0]["project_id"], json.loads((root / "project.json").read_text(encoding="utf-8"))["project_id"])
        self.cli(script, "add", "--root", root, "--kind", "workflow", "--title", "Duplicate", expected=2)
        self.cli(script, "check", "--root", root)

    def test_native_review_snapshot_does_not_follow_a_new_manuscript_version(self):
        manuscript = self.fixture.file("Write/PAPER-test/drafts/v01.md", "# Synthetic manuscript\nNo scientific claims.\n")
        packet = self.root / "Review/REV-test/packet"
        self.cli("light-review/scripts/review_packet.py", "freeze", "--out", packet, "--file", "manuscript=" + str(manuscript))
        before = (packet / "packet.json").read_bytes()
        self.fixture.file("Write/PAPER-test/drafts/v01.md", "Changed synthetic manuscript")
        self.cli("light-review/scripts/review_packet.py", "verify", "--packet", packet)
        self.assertEqual(before, (packet / "packet.json").read_bytes())

    def remember_fixture(self):
        self.cli("light-memory/scripts/memory.py", "init", "--project", self.root, "--name", "Synthetic recovery")
        capture = {"schema_version": "1.0", "capture_id": "remember-source", "label": "Synthetic source check",
                   "items": [{"kind": "constraint", "scope": "project", "slot": "sample.boundary",
                              "text": "One synthetic problem; repeated runs are not independent samples",
                              "epistemic": "verified_observation",
                              "sources": [{"kind": "file", "path": "inputs/source.csv", "locator": "Synthetic rows"}]}]}
        path = self.fixture.file("capture.json", json.dumps(capture))
        self.cli("light-memory/scripts/memory.py", "capture", "--project", self.root, "--spec", path)

    def test_resume_reads_memory_and_keeps_project_unchanged(self):
        self.remember_fixture()
        self.fixture.apply(self.fixture.task())
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        packet = self.cli("light-leader/scripts/leader.py", "resume", "--project", self.root, "--query", "synthetic")
        self.assertEqual(packet["memory"]["status"], "read")
        self.assertEqual(packet["memory"]["packet"]["items"][0]["slot"], "sample.boundary")
        self.assertEqual([r["id"] for r in packet["candidates"]], ["T0001"])
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_resume_surfaces_memory_drift_and_native_running_entry(self):
        self.remember_fixture()
        self.fixture.apply(self.fixture.task(), self.fixture.start())
        self.fixture.file("inputs/source.csv", "Changed after capture")
        packet = leader.resume(self.root)
        self.assertEqual(packet["memory"]["packet"]["items"], [])
        self.assertIn("source_drift", packet["memory"]["packet"]["needs_review"][0]["reasons"])
        self.assertEqual(packet["candidates"], [])
        self.assertEqual(packet["workflow"]["running"][0]["id"], "T0001")

    def test_resume_does_not_hide_broken_memory_or_create_it(self):
        packet = leader.resume(self.root)
        self.assertEqual(packet["memory"]["status"], "not_initialized")
        self.assertFalse((self.root / "Memory").exists())
        self.remember_fixture()
        self.fixture.file("Memory/events/EVT-000001.json", "{}")
        packet = leader.resume(self.root)
        self.assertEqual(packet["memory"]["status"], "read_failed")
        self.assertIsNotNone(packet["workflow"])

    def test_standalone_resume_accepts_explicit_memory_installation(self):
        self.remember_fixture()
        installation = tempfile.TemporaryDirectory(prefix="standalone-leader-")
        self.addCleanup(installation.cleanup)
        copy_root = Path(installation.name) / "light-leader"
        shutil.copytree(PACK / "light-leader/scripts", copy_root / "scripts")
        shutil.copytree(PACK / "light-leader/assets", copy_root / "assets")
        script = copy_root / "scripts/leader.py"
        args = [sys.executable, "-X", "utf8", "-B", str(script), "resume", "--project", str(self.root)]
        process = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["memory"]["status"], "reader_unavailable")
        process = subprocess.run(args + ["--memory-skill", str(PACK / "light-memory")], capture_output=True,
                                 text=True, encoding="utf-8", timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["memory"]["status"], "read")


if __name__ == "__main__":
    unittest.main()
