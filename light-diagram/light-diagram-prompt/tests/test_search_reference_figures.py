from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "search_reference_figures.py"


class ReferenceSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="light-diagram-")
        self.root = Path(self.temp.name)
        self.corpus = self.root / "中文 Some papers' diagram" / "gallery" / "aaai" / "final"
        self.corpus.mkdir(parents=True)
        (self.corpus / "paper-robot.jpg").write_bytes(b"not-an-image-but-discoverable")
        (self.corpus / "paper-cell.jpg").write_bytes(b"not-an-image-but-discoverable")
        self.metadata = self.root / "figures.json"
        self.metadata.write_text(json.dumps([
            {"id": "robot-1", "image": "images/aaai/final/paper-robot.jpg", "title": "Robot Framework", "pattern": "framework", "venue": "aaai", "year": 2025, "paper": "https://example.test/robot"},
            {"id": "cell-1", "image": "images/aaai/final/paper-cell.jpg", "title": "Cell Mechanism", "pattern": "conceptual", "venue": "aaai", "year": 2024},
        ]), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )

    def test_text_search_maps_metadata_across_images_prefix(self) -> None:
        result = self.run_cli(self.corpus.parents[2], "--query", "robot", "--pattern", "framework", "--metadata", self.metadata, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["text_match_only"])
        self.assertEqual(len(payload["results"]), 1)
        record = payload["results"][0]["metadata"]
        self.assertEqual(record["id"], "robot-1")
        self.assertEqual(record["paper"], "https://example.test/robot")

    def test_pattern_filters_unmatched_records(self) -> None:
        result = self.run_cli(self.corpus.parents[2], "--pattern", "framework", "--metadata", self.metadata, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual([Path(row["path"]).name for row in payload["results"]], ["paper-robot.jpg"])

    def test_utf8_path_prints_without_console_encoding_error(self) -> None:
        result = self.run_cli(self.corpus.parents[2], "--limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Some papers' diagram", result.stdout)

    def test_single_image_root_keeps_metadata_lookup(self) -> None:
        image = self.corpus / "paper-robot.jpg"
        result = self.run_cli(image, "--pattern", "framework", "--metadata", self.metadata, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["results"][0]["metadata"]["id"], "robot-1")

    def test_contact_sheet_created_and_existing_file_is_not_overwritten(self) -> None:
        output = self.root / "sheet.png"
        result = self.run_cli(self.corpus.parents[2], "--query", "robot", "--metadata", self.metadata, "--contact-sheet", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        original = output.read_bytes()
        blocked = self.run_cli(self.corpus.parents[2], "--query", "robot", "--metadata", self.metadata, "--contact-sheet", output)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_empty_corpus_returns_empty_results(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        result = self.run_cli(empty, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"], [])

    def test_absent_metadata_and_no_matching_keywords(self) -> None:
        result = self.run_cli(self.corpus, "--query", "no-such-topic-xyz", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"], [])
        result = self.run_cli(self.corpus, "--limit", "1", "--json")
        self.assertEqual(len(json.loads(result.stdout)["results"]), 1)

    def test_duplicate_basenames_use_full_metadata_paths(self) -> None:
        other = self.corpus.parents[1] / "icml" / "final"
        other.mkdir(parents=True)
        (other / "paper-robot.jpg").write_bytes(b"another image")
        rows = json.loads(self.metadata.read_text(encoding="utf-8"))
        rows.append({"id": "other-robot", "image": "images/icml/final/paper-robot.jpg", "title": "Robot elsewhere"})
        self.metadata.write_text(json.dumps(rows), encoding="utf-8")
        result = self.run_cli(self.corpus.parents[2], "--query", "robot", "--metadata", self.metadata, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        found = {Path(row["path"]).parent.parent.name: row["metadata"]["id"] for row in json.loads(result.stdout)["results"]}
        self.assertEqual(found, {"aaai": "robot-1", "icml": "other-robot"})

    def test_missing_pillow_still_returns_text_candidates(self) -> None:
        # -S suppresses site-packages, including Pillow, without uninstalling it.
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(SCRIPT), str(self.corpus),
             "--json", "--contact-sheet", str(self.root / "no-pillow.png")],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["results"]), 2)
        self.assertIsNone(payload["contact_sheet"])
        self.assertIn("Pillow", result.stderr)

    def test_missing_input_and_help(self) -> None:
        result = self.run_cli(self.root / "missing")
        self.assertNotEqual(result.returncode, 0)
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bad_metadata_and_bad_limit_fail_cleanly(self) -> None:
        bad = self.root / "bad.json"
        bad.write_text("{bad", encoding="utf-8")
        result = self.run_cli(self.corpus, "--metadata", bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read metadata", result.stderr)
        result = self.run_cli(self.corpus, "--limit", "0")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
