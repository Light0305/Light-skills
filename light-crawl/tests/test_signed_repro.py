from __future__ import annotations

import base64
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.signed_repro import main as signed_repro
from benchmarks.fixtures.signed_app.server import expected_sign


class SignedReproTests(unittest.TestCase):
    def test_signature_is_deterministic(self) -> None:
        raw = base64.b64decode(expected_sign("1", "1700000000000", "abc"))
        self.assertEqual(raw.decode("utf-8"), "1|1700000000000|abc:demo-secret")

    def test_reproduction_sequence_passes(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = signed_repro([])
        self.assertEqual(code, 0)
        self.assertIn("PASS", stdout.getvalue())
        self.assertIn("signed:   200", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
