#!/usr/bin/env python
"""A config-driven Scrapling spider for L0/L0_API targets.

Example:
    python generic_spider.py --config site.json --out items.jsonl

The site config is intentionally small:

{
  "name": "quotes",
  "start_urls": ["https://quotes.toscrape.com/"],
  "allowed_domains": ["quotes.toscrape.com"],
  "item_selector": "div.quote",
  "fields": {
    "text": {"selector": "span.text::text"},
    "author": {"selector": "small.author::text"},
    "tags": {"selector": "div.tags a.tag::text", "many": true}
  },
  "next_selector": "li.next a::attr(href)",
  "concurrency": 4,
  "robots_txt_obey": true,
  "max_pages": 10
}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from scrapling.spiders import Spider, Response
except ImportError as error:  # pragma: no cover - exercised only without Scrapling
    raise SystemExit(
        "Scrapling is not installed. Run: pip install -e \".[fetchers]\" && scrapling install"
    ) from error


class GenericSpider(Spider):
    """A finite, config-driven spider with a page budget and a checkpoint directory."""

    name = "light_crawl_generic"

    def __init__(
        self,
        config_path: str | Path,
        *,
        max_pages: int | None = None,
        crawldir: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.config_path = Path(config_path).resolve()
        self.config: dict[str, Any] = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.name = str(self.config.get("name") or self.name)
        self.start_urls = list(self.config.get("start_urls") or [])
        self.allowed_domains = list(self.config.get("allowed_domains") or [])
        self.concurrent_requests = int(self.config.get("concurrency", 4))
        self.robots_txt_obey = bool(self.config.get("robots_txt_obey", True))
        self.max_pages = int(max_pages if max_pages is not None else self.config.get("max_pages", 100))
        self.crawldir = str(crawldir) if crawldir else None
        self.item_selector = str(self.config["item_selector"])
        self.fields: dict[str, dict[str, Any]] = dict(self.config["fields"])
        self.next_selector = self.config.get("next_selector")
        self._seen_pages = 0

    @staticmethod
    def _extract(node: Any, spec: dict[str, Any]) -> Any:
        selector = str(spec["selector"])
        many = bool(spec.get("many", False))
        if many:
            values = node.css(selector).getall()
            cleaned = [value.strip() for value in values if value and value.strip()]
            return cleaned
        value = node.css(selector).get()
        if value is None:
            return spec.get("default")
        return value.strip()

    async def parse(self, response: Response):
        self._seen_pages += 1
        if self._seen_pages > self.max_pages:
            return

        for node in response.css(self.item_selector):
            item: dict[str, Any] = {}
            for field, spec in self.fields.items():
                item[field] = self._extract(node, spec)
            if any(value not in (None, "", []) for value in item.values()):
                yield item

        if not self.next_selector or self._seen_pages >= self.max_pages:
            return
        href = response.css(str(self.next_selector)).get()
        if href:
            yield response.follow(href, callback=self.parse)


def _export(result: Any, output: Path) -> None:
    suffix = output.suffix.lower()
    if suffix == ".jsonl":
        result.items.to_jsonl(str(output))
    elif suffix == ".json":
        result.items.to_json(str(output))
    elif suffix == ".csv":
        result.items.to_csv(str(output))
    elif suffix == ".xml":
        result.items.to_xml(str(output))
    else:
        raise SystemExit(f"Unsupported output suffix: {suffix}. Use .json, .jsonl, .csv or .xml.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Config-driven Scrapling spider.")
    parser.add_argument("--config", required=True, help="Path to site.json.")
    parser.add_argument("--out", required=True, help="Output file: .json, .jsonl, .csv or .xml.")
    parser.add_argument("--crawldir", default="", help="Checkpoint directory for pause/resume.")
    parser.add_argument("--max-pages", type=int, default=None, help="Override the site page budget.")
    parser.add_argument("--concurrency", type=int, default=None, help="Override the site concurrency.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    spider = GenericSpider(
        config_path,
        max_pages=args.max_pages,
        crawldir=args.crawldir or None,
    )
    if args.concurrency is not None:
        spider.concurrent_requests = max(1, args.concurrency)

    result = spider.start()
    output = Path(args.out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _export(result, output)
    print(f"items={len(result.items)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
