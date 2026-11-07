"""Offline harness regression checks: these tests never call a model."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot", ROOT / "scripts/run_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotHarnessTests(unittest.TestCase):
    def test_failed_empty_output_cannot_be_reviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            pilot.dump(folder / "record.json", {"status": "error"})
            (folder / "output.md").write_text("", encoding="utf-8")
            self.assertIsNone(pilot.completed_output(folder))

    def test_completed_retry_selected_without_erasing_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            pilot.dump(folder / "record.json", {"status": "error"})
            retry = folder / "retry-001"
            pilot.dump(retry / "record.json", {"status": "completed", "output": "A real output."})
            (retry / "output.md").write_text("A real output.", encoding="utf-8")
            self.assertEqual(pilot.completed_output(folder), retry / "output.md")
            self.assertEqual(json.loads((folder / "record.json").read_text())["status"], "error")

    def test_completed_missing_empty_or_changed_output_cannot_be_reviewed(self):
        for text in (None, "", "   ", "Changed prose"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                pilot.dump(folder / "record.json", {"status": "completed", "output": "Original prose"})
                if text is not None:
                    (folder / "output.md").write_text(text, encoding="utf-8")
                self.assertIsNone(pilot.completed_output(folder))

    def test_damaged_later_completed_attempt_cannot_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            pilot.dump(folder / "record.json", {"status": "completed", "output": "Original"})
            (folder / "output.md").write_text("Original", encoding="utf-8")
            pilot.dump(folder / "retry-001/record.json", {"status": "error"})
            self.assertEqual(pilot.completed_output(folder), folder / "output.md")
            pilot.dump(folder / "retry-002/record.json", {"status": "completed", "output": "New"})
            self.assertIsNone(pilot.completed_output(folder))

    def test_bad_record_is_not_rated(self):
        for raw in ("[]", "{"):
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory); (folder / "record.json").write_text(raw, encoding="utf-8")
                self.assertIsNone(pilot.completed_output(folder))

    def set_up_bundle(self, root):
        cases = [{"id": f"case-{index}", "task": "draft", "domain": "computing",
                  "source_facts": ["Synthetic observation."], "request": "Write one sentence.",
                  "rubric": ["EVALUATOR_ONLY_SECRET"]} for index in range(3)]
        pilot.dump(root / "registration.json", {
            "cli": "offline-test", "settings": {}, "system_instructions": "shared",
            "tool_policy": "none", "snapshots": {"light-after2": {"id": "frozen-test"}},
        })
        return cases

    def test_usage_limit_stops_new_jobs_and_failed_attempt_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = self.set_up_bundle(root)

            def limit(prompt, folder):
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "input.txt").write_text(prompt, encoding="utf-8")
                self.assertNotIn("EVALUATOR_ONLY_SECRET", prompt)
                return "", {"completed": False, "started_at": "2026-10-27", "observed_tool_events": [],
                            "usage_limit": True, "elapsed_seconds": 0}

            with patch.object(pilot, "BUNDLE", root), patch.object(pilot, "load_cases", return_value=cases), \
                    patch.object(pilot, "guidance", return_value=("guidance", [])), \
                    patch.object(pilot, "invoke", side_effect=limit) as invoke:
                pilot.generate("after2", 1, [], False)
                self.assertEqual(invoke.call_count, 1)
                records = list(root.rglob("record.json"))
                self.assertEqual(len(records), 1)
                self.assertEqual(json.loads(records[0].read_text())["stop_reason"],
                                 "usage_limit; no writing output generated")

    def test_explicit_retry_keeps_original_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = self.set_up_bundle(root)[0]
            original = root / "after2" / case["id"] / "light-write" / "record.json"
            pilot.dump(original, {"status": "error", "original": True})
            before = original.read_bytes()

            def success(prompt, folder):
                folder.mkdir(parents=True, exist_ok=True)
                return "A result.", {"completed": True, "started_at": "2026-10-27",
                                     "observed_tool_events": [], "elapsed_seconds": 0}

            with patch.object(pilot, "BUNDLE", root), patch.object(pilot, "load_cases", return_value=[case]), \
                    patch.object(pilot, "guidance", return_value=("guidance", [])), \
                    patch.object(pilot, "invoke", side_effect=success):
                pilot.generate("after2", 1, [], True)
            self.assertEqual(original.read_bytes(), before)
            retry = original.parent / "retry-001" / "record.json"
            record = json.loads(retry.read_text())
            self.assertEqual(record["status"], "completed")
            self.assertTrue(record["run_id"].endswith("retry-001"))

    def test_interrupted_attempt_without_record_is_preserved_and_requires_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); case = self.set_up_bundle(root)[0]
            folder = root / "after2" / case["id"] / "light-write"
            folder.mkdir(parents=True); (folder / "input.txt").write_text("Interrupted input", encoding="utf-8")
            (folder / "retry-003").mkdir()
            def success(prompt, attempt):
                attempt.mkdir(parents=True, exist_ok=True)
                (attempt / "output.md").write_text("New prose", encoding="utf-8")
                return "New prose", {"completed": True, "started_at": "2026-11-06",
                    "observed_tool_events": [], "elapsed_seconds": 0}
            with patch.object(pilot, "BUNDLE", root), patch.object(pilot, "load_cases", return_value=[case]), \
                    patch.object(pilot, "guidance", return_value=("guidance", [])), \
                    patch.object(pilot, "invoke", side_effect=success) as invoke:
                pilot.generate("after2", 1, [], False)
                invoke.assert_not_called()
                pilot.generate("after2", 1, [], True)
            self.assertEqual((folder / "input.txt").read_text(encoding="utf-8"), "Interrupted input")
            self.assertTrue((folder / "retry-004/record.json").is_file())


if __name__ == "__main__":
    unittest.main()
