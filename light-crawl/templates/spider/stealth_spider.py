#!/usr/bin/env python
"""A config-driven Scrapling spider backed by a stealth browser session.

Use this for L1_DYNAMIC/L3_BLOCKED targets where the page needs JavaScript or a
real browser. Keep the page budget small while exploring.

    python stealth_spider.py --config site.json --out items.jsonl --max-pages 3

The config is the same shape as `generic_spider.py`, plus:

    "wait_selector": "main",
    "solve_cloudflare": false,
    "headless": true,
    "real_chrome": "auto (system Chrome if present, otherwise bundled)"
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from scrapling.fetchers import AsyncStealthySession
    from scrapling.spiders import Spider, Response
except ImportError as error:  # pragma: no cover - exercised only without Scrapling
    raise SystemExit(
        "Scrapling is not installed. Run: pip install -e \".[fetchers]\" && scrapling install"
    ) from error

try:
    from light_crawl.sessions import SessionBroker, SessionConflict
    from light_crawl.utils import system_chrome_path
except ImportError:  # pragma: no cover - template can be copied outside the package
    SessionBroker = None
    SessionConflict = Exception

    def system_chrome_path():
        return None


class StealthSpider(Spider):
    name = "light_crawl_stealth"

    def __init__(
        self,
        config_path: str | Path,
        *,
        max_pages: int | None = None,
        crawldir: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        self.config_path = Path(config_path).resolve()
        self.config: dict[str, Any] = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.name = str(self.config.get("name") or self.name)
        self.start_urls = list(self.config.get("start_urls") or [])
        self.allowed_domains = list(self.config.get("allowed_domains") or [])
        self.concurrent_requests = int(self.config.get("concurrency", 2))
        self.robots_txt_obey = bool(self.config.get("robots_txt_obey", True))
        self.max_pages = int(max_pages if max_pages is not None else self.config.get("max_pages", 10))
        self.item_selector = str(self.config["item_selector"])
        self.fields: dict[str, dict[str, Any]] = dict(self.config["fields"])
        self.next_selector = self.config.get("next_selector")
        self.wait_selector = str(self.config.get("wait_selector") or "body")
        self.headless = bool(self.config.get("headless", True))
        self.solve_cloudflare = bool(self.config.get("solve_cloudflare", False))
        self.real_chrome = bool(
            self.config.get("real_chrome", system_chrome_path() is not None)
        )
        self._seen_pages = 0
        super().__init__(crawldir=crawldir, **kwargs)

    def configure_sessions(self, manager: Any) -> None:
        manager.add(
            "stealth",
            AsyncStealthySession(
                headless=self.headless,
                solve_cloudflare=self.solve_cloudflare,
                real_chrome=self.real_chrome,
                record_requests=True,
            ),
            default=True,
            lazy=True,
        )

    @staticmethod
    def _extract(node: Any, spec: dict[str, Any]) -> Any:
        selector = str(spec["selector"])
        if bool(spec.get("many", False)):
            values = node.css(selector).getall()
            return [value.strip() for value in values if value and value.strip()]
        value = node.css(selector).get()
        if value is None:
            return spec.get("default")
        return value.strip()

    async def parse(self, response: Response):
        self._seen_pages += 1
        if self._seen_pages > self.max_pages:
            return
        for node in response.css(self.item_selector):
            item = {field: self._extract(node, spec) for field, spec in self.fields.items()}
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
    else:
        raise SystemExit(f"Unsupported output suffix: {suffix}. Use .json, .jsonl or .csv.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Config-driven Scrapling stealth spider.")
    parser.add_argument("--config", required=True, help="Path to site.json.")
    parser.add_argument("--out", required=True, help="Output file: .json, .jsonl or .csv.")
    parser.add_argument("--crawldir", default="", help="Checkpoint directory for pause/resume.")
    parser.add_argument("--max-pages", type=int, default=None, help="Override the page budget.")
    parser.add_argument("--headed", action="store_true", help="Run the browser visibly.")
    parser.add_argument("--solve-cloudflare", action="store_true", help="Enable the Cloudflare solver.")
    parser.add_argument(
        "--bundled-browser",
        action="store_true",
        help="Use Scrapling's downloaded browser instead of the installed Google Chrome.",
    )
    parser.add_argument("--lock-profile", default="", help="Acquire this browser profile before launching.")
    parser.add_argument("--owner", default="", help="Session owner label for the lock.")
    parser.add_argument("--lock-ttl", type=int, default=3600, help="Lock TTL in seconds.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    spider = StealthSpider(
        config_path,
        max_pages=args.max_pages,
        crawldir=args.crawldir or None,
    )
    if args.headed:
        spider.headless = False
    if args.solve_cloudflare:
        spider.solve_cloudflare = True
    if args.bundled_browser:
        spider.real_chrome = False

    broker = None
    lock = None
    if args.lock_profile:
        if SessionBroker is None:
            raise SystemExit("light-crawl is not installed; cannot acquire a profile lock.")
        broker = SessionBroker(Path(".light-crawl/sessions"))
        owner = args.owner or f"stealth-spider-{os.getpid()}"
        try:
            lock = broker.acquire(
                args.lock_profile,
                owner,
                ttl_seconds=max(60, args.lock_ttl),
                metadata={"script": "templates/spider/stealth_spider.py"},
            )
        except SessionConflict as error:
            raise SystemExit(f"Profile lock conflict: {error}") from error
        print(f"profile_lock={lock.profile} owner={lock.owner}")

    try:
        result = spider.start()
        output = Path(args.out).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        _export(result, output)
        print(f"items={len(result.items)} output={output}")
        return 0
    finally:
        if broker is not None and lock is not None:
            try:
                broker.release(lock.profile, lock.owner)
            except SessionConflict:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
