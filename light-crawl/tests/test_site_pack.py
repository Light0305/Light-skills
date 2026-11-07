from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "examples" / "site-packs" / "quotes"


class SitePackTests(unittest.TestCase):
    def test_quotes_pack_verify_script(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(PACK / "verify.py")],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS", completed.stdout)
        self.assertTrue((PACK / "site.json").exists())
        self.assertTrue((PACK / "fixtures" / "response.html").exists())

    def test_github_api_pack_verify_script(self) -> None:
        pack = ROOT / "examples" / "site-packs" / "github-api"
        completed = subprocess.run(
            [sys.executable, str(pack / "verify.py")],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS", completed.stdout)
        self.assertTrue((pack / "fixtures" / "response.json").exists())

    def test_signed_local_pack_verify_script(self) -> None:
        pack = ROOT / "examples" / "site-packs" / "signed-local"
        completed = subprocess.run(
            [sys.executable, str(pack / "verify.py")],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS unsigned=403 signed=200 orders=2", completed.stdout)

    def test_login_local_pack_verify_script(self) -> None:
        pack = ROOT / "examples" / "site-packs" / "login-local"
        completed = subprocess.run(
            [sys.executable, str(pack / "verify.py")],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS before=401 login=200 private=200", completed.stdout)


if __name__ == "__main__":
    unittest.main()
