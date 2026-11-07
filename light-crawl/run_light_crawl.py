#!/usr/bin/env python
"""Run light-crawl from a source checkout without installing the package."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from light_crawl.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
