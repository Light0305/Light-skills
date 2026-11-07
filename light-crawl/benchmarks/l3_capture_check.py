#!/usr/bin/env python
"""Check browser capture against the local challenge fixture.

The fixture's `/js-challenge` sets a cookie and redirects to `/ok`. The browser
engine must follow that flow and save the final body. This proves the browser
capture path, not real Cloudflare solving.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.fixtures.cloudflare_app.server import start_server, stop_server
from light_crawl.capture import capture_target
from light_crawl.models import PageKind, ProbeResult, TargetProfile
from light_crawl.probe import probe_target
from light_crawl.state import CaseStore
from light_crawl.utils import write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Browser-capture the local JS challenge fixture.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    server, thread, base = start_server()
    try:
        url = base + "/js-challenge"
        probe = probe_target(url, timeout=5)
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(
                Path(tmp) / "cases",
                "l3-capture-check",
                TargetProfile(url=url, volume=1, authorized=True),
            )
            write_json(store.probe_file, probe.to_dict())
            result = capture_target(store, engine="scrapling", timeout=30, wait_selector="body")
            body = result.body.decode("utf-8", errors="replace")
            passed = result.status == 200 and result.engine == "scrapling-stealth" and "ok" in body
            payload = {
                "url": url,
                "probe_kind": probe.page_kind,
                "capture_status": result.status,
                "engine": result.engine,
                "bytes": len(result.body),
                "final_url": result.final_url,
                "passed": passed,
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"probe kind:     {probe.page_kind}")
                print(f"capture status: {result.status}")
                print(f"engine:         {result.engine}")
                print(f"final url:      {result.final_url}")
                print(f"result:         {'PASS' if passed else 'FAIL'}")
            return 0 if passed else 1
    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    raise SystemExit(main())
