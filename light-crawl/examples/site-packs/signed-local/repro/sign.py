#!/usr/bin/env python
"""Reproduce the demo signed request.

This mirrors the local fixture server's algorithm:

    base64("page|ts|nonce:demo-secret")

It is deliberately simple; the point is the L2 reproduction shape, not crypto.
"""

from __future__ import annotations

import base64
import secrets
import time
from urllib.parse import urlencode

SECRET = "demo-secret"


def expected_sign(page: str, ts: str, nonce: str) -> str:
    payload = f"{page}|{ts}|{nonce}:{SECRET}"
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


def build_query(page: str = "1", *, ts: str | None = None, nonce: str | None = None) -> dict[str, str]:
    timestamp = ts or str(int(time.time() * 1000))
    nonce_value = nonce or secrets.token_hex(8)
    return {
        "page": page,
        "ts": timestamp,
        "nonce": nonce_value,
        "sign": expected_sign(page, timestamp, nonce_value),
    }


def build_url(base: str, page: str = "1", **kwargs: str) -> str:
    query = urlencode(build_query(page, **kwargs))
    return f"{base.rstrip('/')}/api/orders?{query}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Print a signed demo URL.")
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    print(build_url(args.base))
