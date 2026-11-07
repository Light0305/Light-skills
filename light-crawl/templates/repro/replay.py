#!/usr/bin/env python
"""Replay a captured request without a browser.

The request fixture is deliberately small and secret-free:

{
  "method": "GET",
  "url": "https://example.com/api/items",
  "headers": {"accept": "application/json"},
  "params": {"page": "1"},
  "json": null,
  "data": null,
  "cookies": {}
}

Usage:
    python replay.py --request request.json
    python replay.py --request request.json --out response.json
    python replay.py --request request.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


def load_request(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit("Request fixture must be a JSON object.")
    if not data.get("url"):
        raise SystemExit("Request fixture must contain a non-empty `url`.")
    return data


def build_request(fixture: dict) -> Request:
    method = str(fixture.get("method") or "GET").upper()
    parsed = urlparse(str(fixture["url"]))
    query = parsed.query
    params = fixture.get("params") or {}
    if params:
        extra = urlencode(params, doseq=True)
        query = f"{query}&{extra}" if query else extra
    url = urlunparse(parsed._replace(query=query))

    headers = {str(key): str(value) for key, value in (fixture.get("headers") or {}).items()}
    cookies = fixture.get("cookies") or {}
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers["Cookie"] = cookie_header

    body: bytes | None = None
    if fixture.get("json") is not None:
        body = json.dumps(fixture["json"], ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif fixture.get("data") is not None:
        if isinstance(fixture["data"], dict):
            body = urlencode(fixture["data"], doseq=True).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = str(fixture["data"]).encode("utf-8")

    return Request(url, data=body, headers=headers, method=method)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a captured HTTP request.")
    parser.add_argument("--request", required=True, help="Path to request.json.")
    parser.add_argument("--out", default="", help="Write the response body to this file.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print the prepared request and exit.")
    parser.add_argument("--show-headers", action="store_true", help="Print response headers.")
    args = parser.parse_args(argv)

    fixture = load_request(Path(args.request))
    request = build_request(fixture)

    if args.dry_run:
        print(f"{request.get_method()} {request.full_url}")
        for key, value in request.header_items():
            if key.lower() in {"cookie", "authorization"}:
                value = "<redacted>"
            print(f"{key}: {value}")
        if request.data:
            preview = request.data[:1000].decode("utf-8", errors="replace")
            print(f"body: {preview}")
        return 0

    started = time.perf_counter()
    try:
        with urlopen(request, timeout=args.timeout) as response:
            raw = response.read()
            elapsed = (time.perf_counter() - started) * 1000
            status = int(getattr(response, "status", 0) or 0)
            headers = dict(response.headers)
            content_type = headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
    except HTTPError as error:
        raw = error.read()
        elapsed = (time.perf_counter() - started) * 1000
        status = int(error.code or 0)
        headers = dict(error.headers)
        content_type = headers.get("Content-Type", "")
        text = raw.decode("utf-8", errors="replace")
    except (URLError, TimeoutError, OSError) as error:
        print(f"replay failed: {error}", file=sys.stderr)
        return 1

    print(f"status={status} elapsed_ms={elapsed:.0f} bytes={len(raw)} content_type={content_type}")
    if args.show_headers:
        for key, value in headers.items():
            if key.lower() in {"set-cookie"}:
                value = "<redacted>"
            print(f"{key}: {value}")
    print(text[:2000])

    if args.out:
        Path(args.out).write_bytes(raw)
        print(f"wrote {Path(args.out).resolve()}")
    return 0 if status < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
