#!/usr/bin/env python
"""Reproduce the local signed-API fixture end to end.

The sequence is the L2 contract in miniature:

1. unsigned request -> 403;
2. compute page/ts/nonce/sign;
3. signed request -> 200 with orders.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.fixtures.signed_app.server import expected_sign, start_server, stop_server


def fetch(url: str, timeout: int = 5) -> tuple[int, bytes]:
    try:
        with urlopen(url, timeout=timeout) as response:
            return int(getattr(response, "status", 0) or 0), response.read()
    except HTTPError as error:
        return int(error.code or 0), error.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the local signed-API fixture.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    server, thread, base = start_server()
    try:
        unsigned_status, _ = fetch(base + "/api/orders?page=1")
        page = "1"
        ts = str(int(time.time() * 1000))
        nonce = secrets.token_hex(8)
        signature = expected_sign(page, ts, nonce)
        query = urlencode({"page": page, "ts": ts, "nonce": nonce, "sign": signature})
        signed_status, body = fetch(base + "/api/orders?" + query)
        payload = json.loads(body.decode("utf-8")) if signed_status == 200 else {}
        orders = payload.get("orders", [])
        passed = unsigned_status == 403 and signed_status == 200 and len(orders) == 2
        result = {
            "unsigned_status": unsigned_status,
            "signed_status": signed_status,
            "orders": len(orders),
            "signature": signature,
            "passed": passed,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"unsigned: {unsigned_status} (expected 403)")
            print(f"signed:   {signed_status} (expected 200)")
            print(f"orders:   {len(orders)}")
            print(f"result:   {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1
    except (URLError, OSError) as error:
        print(f"signed repro failed: {error}", file=sys.stderr)
        return 1
    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    raise SystemExit(main())
