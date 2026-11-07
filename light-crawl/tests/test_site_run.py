from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.site import run_site_pack


SPIDER = """import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("--config")
parser.add_argument("--out")
parser.add_argument("--max-pages", type=int, default=None)
args = parser.parse_args()
Path(args.out).write_text(
    json.dumps({"id": 1}) + "\\n" + json.dumps({"id": 2}) + "\\n",
    encoding="utf-8",
)
"""

VERIFY = """import sys
sys.exit(0)
"""


class SiteRunTests(unittest.TestCase):
    def _pack(self, root: Path, expected: int = 2) -> Path:
        pack = root / "pack"
        (pack / "spider").mkdir(parents=True)
        (pack / "site.json").write_text(
            json.dumps({"domain": "local", "run": {"expected_items": expected}}),
            encoding="utf-8",
        )
        (pack / "spider" / "site.json").write_text("{}", encoding="utf-8")
        (pack / "spider" / "spider.py").write_text(SPIDER, encoding="utf-8")
        (pack / "verify.py").write_text(VERIFY, encoding="utf-8")
        return pack

    def test_run_site_pack_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = self._pack(root)
            result = run_site_pack(pack, output=root / "out.jsonl")
            self.assertTrue(result.passed, result.stderr)
            self.assertEqual(result.items, 2)
            self.assertEqual(result.verify_returncode, 0)

    def test_expected_count_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = self._pack(root, expected=3)
            result = run_site_pack(pack, output=root / "out.jsonl")
            self.assertFalse(result.passed)
            self.assertEqual(result.items, 2)
            self.assertEqual(result.expected_items, 3)

    def test_missing_pack_files_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "empty"
            pack.mkdir()
            with self.assertRaises(Exception):
                run_site_pack(pack, output=root / "out.jsonl")


if __name__ == "__main__":
    unittest.main()
