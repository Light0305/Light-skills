"""Allow `python -m light_crawl` to behave like the `light-crawl` command."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
