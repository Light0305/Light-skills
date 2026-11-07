#!/usr/bin/env python
"""Compatibility wrapper for the package-level case verifier.

Prefer `light-crawl verify <case>`. This script keeps the old invocation working
from a source checkout:

    python templates/verify/verify_case.py --case cases/my-case
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from light_crawl.verify import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
