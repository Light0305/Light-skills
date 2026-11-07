from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.l3_capture_check import main as l3_capture_check


class L3CaptureTests(unittest.TestCase):
    def test_browser_capture_follows_js_challenge(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = l3_capture_check(["--json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["capture_status"], 200)
        self.assertEqual(payload["engine"], "scrapling-stealth")


if __name__ == "__main__":
    unittest.main()
