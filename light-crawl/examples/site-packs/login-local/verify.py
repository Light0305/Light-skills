#!/usr/bin/env python
"""End-to-end cookie/session check for the login-local pack."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for entry in (str(ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from benchmarks.fixtures.login_app.server import start_server, stop_server
from repro.session import DPAPI_MAGIC, fetch_with_state, load_state, login_and_save


def unauthenticated_status(url: str) -> int:
    try:
        with urlopen(url, timeout=5) as response:
            return int(getattr(response, "status", 0) or 0)
    except HTTPError as error:
        return int(error.code or 0)


def main() -> int:
    server, thread, base = start_server()
    try:
        before = unauthenticated_status(base + "/private")
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "session.dpapi"
            login, private = login_and_save(base, state_path)
            restored = fetch_with_state(base, state_path)
            raw = state_path.read_bytes()
            state = load_state(state_path)
            encrypted = raw.startswith(DPAPI_MAGIC)
            plaintext_absent = b"demo-session" not in raw
            force_plain = os.environ.get("LIGHT_CRAWL_FORCE_PLAIN") == "1"
            expect_dpapi = os.name == "nt" and not force_plain
            mode = state_path.stat().st_mode & 0o777
            mode_ok = (mode == 0o600) or os.name == "nt"
            protection = "dpapi" if encrypted else str(state.get("protection") or "none")
            if expect_dpapi:
                protection_ok = encrypted and plaintext_absent
            else:
                protection_ok = (
                    not encrypted
                    and protection == "plain-0600"
                    and mode_ok
                )
            try:
                payload = restored.json()
            except Exception:
                payload = {}
            passed = (
                before == 401
                and int(getattr(login, "status", 0) or 0) == 200
                and int(getattr(private, "status", 0) or 0) == 200
                and int(getattr(restored, "status", 0) or 0) == 200
                and payload.get("user") == "demo"
                and len(payload.get("orders", [])) == 2
                and "demo-session" in state.get("cookies", {}).values()
                and protection_ok
            )
            print(
                f"{'PASS' if passed else 'FAIL'} before={before} "
                f"login={getattr(login, 'status', 0)} private={getattr(private, 'status', 0)} "
                f"restored={getattr(restored, 'status', 0)} user={payload.get('user')!r} "
                f"orders={len(payload.get('orders', []))} protection={protection} mode={oct(mode)}"
            )
            return 0 if passed else 1
    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    raise SystemExit(main())
