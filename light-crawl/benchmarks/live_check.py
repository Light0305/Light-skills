#!/usr/bin/env python
"""Probe the local signed/Cloudflare fixture servers and check their routes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.fixtures.cloudflare_app.server import start_server as start_cloudflare
from benchmarks.fixtures.cloudflare_app.server import stop_server as stop_cloudflare
from benchmarks.fixtures.signed_app.server import start_server as start_signed
from benchmarks.fixtures.signed_app.server import stop_server as stop_signed
from light_crawl.models import TargetProfile
from light_crawl.probe import probe_target
from light_crawl.router import decide_route


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live-check local benchmark fixtures.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    checks = []
    signed_server, signed_thread, signed_base = start_signed()
    cloudflare_server, cloudflare_thread, cloudflare_base = start_cloudflare()
    try:
        cases = [
            ("signed_app", signed_base + "/", "L2_SIGNED"),
            ("cloudflare_app", cloudflare_base + "/", "L3_BLOCKED"),
        ]
        for name, url, expected in cases:
            probe = probe_target(url, timeout=5)
            target = TargetProfile(url=url, volume=10, authorized=True)
            decision = decide_route(probe, target)
            passed = decision.lane == expected
            checks.append(
                {
                    "name": name,
                    "url": url,
                    "page_kind": probe.page_kind,
                    "expected": expected,
                    "actual": decision.lane,
                    "passed": passed,
                    "confidence": decision.confidence,
                }
            )
    finally:
        stop_signed(signed_server, signed_thread)
        stop_cloudflare(cloudflare_server, cloudflare_thread)

    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        for check in checks:
            mark = "PASS" if check["passed"] else "FAIL"
            print(
                f"[{mark}] {check['name']:<16} page_kind={check['page_kind']:<10} "
                f"expected={check['expected']:<12} actual={check['actual']}"
            )
    return 0 if all(check["passed"] for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
