from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.live_check import main as live_check


class LiveFixtureTests(unittest.TestCase):
    def test_signed_and_cloudflare_fixtures(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = live_check(["--json"])
        self.assertEqual(code, 0)
        checks = json.loads(stdout.getvalue())
        self.assertEqual(len(checks), 2)
        self.assertTrue(all(check["passed"] for check in checks))
        self.assertEqual({check["actual"] for check in checks}, {"L2_SIGNED", "L3_BLOCKED"})


if __name__ == "__main__":
    unittest.main()
