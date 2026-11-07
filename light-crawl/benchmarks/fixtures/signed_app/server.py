#!/usr/bin/env python
"""A local signed-API fixture used by the L2 benchmark case.

The signature is deliberately simple and local:

    sign = base64("page|ts|nonce:demo-secret")

It is not production crypto. Its purpose is to give the L2 lane a deterministic
end-to-end reproduction target: unsigned request -> 403, reproduced signature ->
200.
"""

from __future__ import annotations

import argparse
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


SECRET = "demo-secret"
MAX_TS_SKEW_MS = 60 * 60 * 1000


def expected_sign(page: str, ts: str, nonce: str) -> str:
    payload = f"{page}|{ts}|{nonce}:{SECRET}"
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Signed Orders</title></head>
<body>
  <main>
    <h1>Signed Orders</h1>
    <p>This fixture page demonstrates an order-list API that requires a signature, a timestamp
    and a nonce. The signature is intentionally simple and local.</p>
    <p>The browser code below builds the request. A real target would use a stronger secret and
    an obfuscated signer; the routing and reproduction signals are the same.</p>
    <ul id="orders"></ul>
  </main>
  <script>
    const nonce = () => Math.random().toString(16).slice(2);
    const sign = (page, ts, n) => btoa(`${page}|${ts}|${n}:demo-secret`);
    const load = async () => {
      const page = "1";
      const ts = String(Date.now());
      const n = nonce();
      const signature = sign(page, ts, n);
      const url = `/api/orders?page=${page}&ts=${ts}&nonce=${n}&sign=${encodeURIComponent(signature)}`;
      const response = await fetch(url);
      const data = await response.json();
      document.querySelector("#orders").textContent = JSON.stringify(data);
    };
    load();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/robots.txt":
            self._send(200, b"User-agent: *\nAllow: /\n", "text/plain; charset=utf-8")
            return
        if parsed.path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/orders":
            query = parse_qs(parsed.query)
            page = (query.get("page") or [""])[0]
            ts = (query.get("ts") or [""])[0]
            nonce = (query.get("nonce") or [""])[0]
            supplied = (query.get("sign") or [""])[0]
            if not page or not ts or not nonce or not supplied:
                self._send(403, b'{"error": "missing signature fields"}', "application/json")
                return
            try:
                ts_value = int(ts)
            except ValueError:
                self._send(403, b'{"error": "invalid timestamp"}', "application/json")
                return
            if abs(int(time.time() * 1000) - ts_value) > MAX_TS_SKEW_MS:
                self._send(403, b'{"error": "stale timestamp"}', "application/json")
                return
            if supplied != expected_sign(page, ts, nonce):
                self._send(403, b'{"error": "bad signature"}', "application/json")
                return
            payload = {
                "page": int(page),
                "orders": [
                    {"id": "A-100", "total": 42.5},
                    {"id": "A-101", "total": 18.0},
                ],
            }
            self._send(200, json.dumps(payload).encode("utf-8"), "application/json")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        return


def start_server(port: int = 0):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, actual_port = server.server_address[:2]
    return server, thread, f"http://{host}:{actual_port}"


def stop_server(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local signed-API fixture server.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server, thread, base = start_server(args.port)
    print(f"signed_app listening on {base}")
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        stop_server(server, thread)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
