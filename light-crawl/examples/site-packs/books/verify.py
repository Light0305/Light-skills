#!/usr/bin/env python
"""Offline regression check for the books site pack."""

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
    books = page.css("article.product_pod")
    if len(books) != 20:
        print(f"FAIL expected 20 books on page 1, got {len(books)}", file=sys.stderr)
        return 1
    first = books[0]
    title = first.css("h3 a::attr(title)").get()
    price = first.css("p.price_color::text").get()
    next_href = page.css("li.next a::attr(href)").get()
    if not title or not price or not next_href:
        print(
            f"FAIL incomplete first page: title={title!r} price={price!r} next={next_href!r}",
            file=sys.stderr,
        )
        return 1
    print(f"PASS books={len(books)} first_title={title!r} next={next_href}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
