from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "site-packs" / "login-local"))

from repro.session import DPAPI_MAGIC, load_state, protect_bytes, save_state, unprotect_bytes


class LoginEncryptionTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "DPAPI is Windows-only")
    def test_dpapi_roundtrip_and_no_plaintext(self) -> None:
        raw = b'{"cookies":{"session":"demo-session"}}'
        encrypted = protect_bytes(raw)
        self.assertNotIn(b"demo-session", encrypted)
        self.assertEqual(unprotect_bytes(encrypted), raw)

    def test_save_and_load_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.state"
            save_state(path, {"host": "127.0.0.1", "cookies": {"session": "demo-session"}})
            raw = path.read_bytes()
            self.assertNotIn(b"demo-session", raw)
            self.assertEqual(load_state(path)["cookies"]["session"], "demo-session")
            if os.name == "nt":
                self.assertTrue(raw.startswith(DPAPI_MAGIC))

    def test_forced_plain_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.json"
            save_state(
                path,
                {"host": "127.0.0.1", "cookies": {"session": "demo-session"}},
                protection="plain",
            )
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(DPAPI_MAGIC))
            self.assertIn(b'"protection": "plain-0600"', raw)
            self.assertEqual(load_state(path)["cookies"]["session"], "demo-session")


if __name__ == "__main__":
    unittest.main()
