#!/usr/bin/env python
"""Log into the local fixture and reuse the cookie through a Scrapling session."""

from __future__ import annotations

try:
    from scrapling.fetchers import FetcherSession
except ImportError as error:  # pragma: no cover - only without Scrapling
    raise SystemExit(
        "Scrapling is required. Run: pip install -e \".[fetchers]\""
    ) from error


def login_and_fetch(base: str):
    with FetcherSession(impersonate="chrome", stealthy_headers=True) as session:
        login = session.post(
            base.rstrip("/") + "/login",
            data={"username": "demo", "password": "demo"},
        )
        private = session.get(base.rstrip("/") + "/private")
        return login, private


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Log into the local fixture.")
    parser.add_argument("--base", default="http://127.0.0.1:8767")
    args = parser.parse_args()
    login, private = login_and_fetch(args.base)
    print(f"login_status={login.status} private_status={private.status}")
    print(private.text[:500])
