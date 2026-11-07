from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.site import runtime_python


class SiteRuntimeTests(unittest.TestCase):
    def test_prefers_runtime_home_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            windows_python = Path(tmp) / "venv" / "Scripts" / "python.exe"
            posix_python = Path(tmp) / "venv" / "bin" / "python"
            for candidate in (windows_python, posix_python):
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text("", encoding="utf-8")
            expected = windows_python if os.name == "nt" else posix_python
            with patch.dict(os.environ, {"LIGHT_CRAWL_HOME": tmp}, clear=False):
                self.assertEqual(runtime_python(), str(expected))

    def test_falls_back_to_current_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LIGHT_CRAWL_HOME": tmp}, clear=False):
                self.assertEqual(runtime_python(), sys.executable)


if __name__ == "__main__":
    unittest.main()
