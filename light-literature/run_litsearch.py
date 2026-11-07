#!/usr/bin/env python3
"""Zero-install launcher for litsearch.

Run `python litsearch.py --help` from the repository root without installing.
After `pip install -e .`, the `litsearch` command is also available.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from litsearch.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
