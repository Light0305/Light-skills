#!/usr/bin/env python
"""End-to-end check for the signed-local pack.

Starts the local signed fixture, proves the unsigned request is rejected, then
uses this pack's `repro/sign.py` to reproduce a valid request.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for entry in (str(ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from benchmarks.fixtures.signed_app.server import start_server, stop_server
from repro.sign import build_url


def fetch(url: str) -> tuple[int, bytes]:
    try:
        with urlopen(url, timeout=5) as response:
            return int(getattr(response, "status", 0) or 0), response.read()
    except HTTPError as error:
        return int(error.code or 0), error.read()


def main() -> int:
    server, thread, base = start_server()
    try:
        unsigned_status, _ = fetch(base + "/api/orders?page=1")
        signed_status, body = fetch(build_url(base))
        payload = json.loads(body.decode("utf-8")) if signed_status == 200 else {}
        orders = payload.get("orders", [])
        passed = unsigned_status == 403 and signed_status == 200 and len(orders) == 2
        print(
            f"{'PASS' if passed else 'FAIL'} unsigned={unsigned_status} "
            f"signed={signed_status} orders={len(orders)}"
        )
        return 0 if passed else 1
    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    raise SystemExit(main())
