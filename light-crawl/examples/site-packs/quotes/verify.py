#!/usr/bin/env python
"""Offline regression check for the quotes site pack."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scrapling.parser import Selector
except ImportError as error:  # pragma: no cover - only without Scrapling
    raise SystemExit(
        "Scrapling is required for this check. Run: pip install -e \".[fetchers]\""
    ) from error

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "response.html"


def main() -> int:
    if not FIXTURE.exists():
        print(f"FAIL missing fixture: {FIXTURE}", file=sys.stderr)
        return 1
    page = Selector(FIXTURE.read_text(encoding="utf-8"))
    quotes = page.css("div.quote")
    if len(quotes) != 10:
        print(f"FAIL expected 10 quotes, got {len(quotes)}", file=sys.stderr)
        return 1
    first = quotes[0]
    text = first.css("span.text::text").get()
    author = first.css("small.author::text").get()
    tags = first.css("div.tags a.tag::text").getall()
    if not text or not author or len(tags) != 4:
        print(f"FAIL first item incomplete: text={text!r} author={author!r} tags={tags!r}", file=sys.stderr)
        return 1
    print(f"PASS quotes={len(quotes)} first_author={author} first_tags={len(tags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
