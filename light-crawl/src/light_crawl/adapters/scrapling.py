"""Scrapling discovery and command contracts."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def find_cli() -> str | None:
    found = shutil.which("scrapling")
    if found:
        return found
    for name in ("scrapling.exe", "scrapling"):
        candidate = Path(sys.executable).with_name(name)
        if candidate.exists():
            return str(candidate)
    return None


def version() -> str:
    cli = find_cli()
    if not cli:
        return ""
    try:
        completed = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=15, check=False)
        lines = (completed.stdout or completed.stderr or "").strip().splitlines()
        return lines[0] if lines else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def available() -> bool:
    return find_cli() is not None


def install_hint() -> str:
    return 'pip install -e ".[fetchers]" && scrapling install'


def command_examples(url: str) -> list[str]:
    return [
        f'scrapling extract get "{url}" page.md --ai-targeted',
        f'scrapling extract fetch "{url}" page.md --ai-targeted --wait-selector "body"',
        f'scrapling shell',
    ]


def fetcher_contract() -> str:
    return (
        "L0 uses Fetcher/FetcherSession. L1/L3 use StealthyFetcher/StealthySession with "
        "record_requests=True so the JSON API can be discovered before parsing DOM. "
        "L5 uses Spider with crawldir, AutoThrottle and proxy rotation."
    )
