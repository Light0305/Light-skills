#!/usr/bin/env python
"""A minimal JSON-API spider for the GitHub repository endpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from scrapling.fetchers import Fetcher
except ImportError as error:  # pragma: no cover - only without Scrapling
    raise SystemExit(
        "Scrapling is required. Run: pip install -e \".[fetchers]\""
    ) from error


def resolve(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch one JSON API and export one item.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--crawldir", default="")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    page = Fetcher.get(str(config["url"]), stealthy_headers=True)
    if int(getattr(page, "status", 0) or 0) >= 400:
        print(f"request failed with status {getattr(page, 'status', 0)}", file=sys.stderr)
        return 1
    data = page.json()
    item = {field: resolve(data, path) for field, path in config["fields"].items()}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"items=1 output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
