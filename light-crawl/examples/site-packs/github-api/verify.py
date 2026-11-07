#!/usr/bin/env python
"""Offline regression check for the GitHub API pack."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "response.json"

REQUIRED = ("full_name", "stargazers_count", "forks_count", "open_issues_count", "html_url")


def main() -> int:
    if not FIXTURE.exists():
        print(f"FAIL missing fixture: {FIXTURE}", file=sys.stderr)
        return 1
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED if data.get(key) is None]
    if missing:
        print(f"FAIL missing fields: {missing}", file=sys.stderr)
        return 1
    if data["full_name"] != "python/cpython":
        print(f"FAIL unexpected full_name: {data['full_name']}", file=sys.stderr)
        return 1
    if not isinstance(data["stargazers_count"], int) or data["stargazers_count"] <= 0:
        print(f"FAIL unexpected stars: {data['stargazers_count']!r}", file=sys.stderr)
        return 1
    print(
        f"PASS full_name={data['full_name']} stars={data['stargazers_count']} "
        f"forks={data['forks_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
