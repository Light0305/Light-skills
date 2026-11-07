#!/usr/bin/env python
"""A local cookie/session login fixture used by the L1 login pack.

GET /login      -> a small form
POST /login     -> sets `session=demo-session` and redirects to /private
GET /private    -> 200 JSON only when the cookie is present, otherwise 401
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


LOGIN_PAGE = b"""<!doctype html>
<html><head><title>Demo login</title></head>
<body>
  <main>
    <h1>Demo login</h1>
    <p>This local fixture uses a cookie-backed session. A client must POST the demo
    credentials, keep the cookie, and then request the private endpoint.</p>
    <form method="post" action="/login">
      <label>Username <input name="username" value="demo"></label>
      <label>Password <input name="password" type="password" value="demo"></label>
      <button type="submit">Sign in</button>
    </form>
  </main>
</body></html>
"""

PRIVATE = {
    "ok": True,
    "user": "demo",
    "orders": [
        {"id": "A-100", "total": 42.5},
        {"id": "A-101", "total": 18.0},
    ],
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: bytes, content_type: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/robots.txt":
            self._send(200, b"User-agent: *\nAllow: /\n", "text/plain; charset=utf-8")
            return
        if self.path == "/login":
            self._send(200, LOGIN_PAGE, "text/html; charset=utf-8")
            return
        if self.path == "/private":
            cookie = self.headers.get("Cookie", "")
            if "session=demo-session" in cookie:
                self._send(200, json.dumps(PRIVATE).encode("utf-8"), "application/json")
            else:
                self._send(401, b'{"error": "login required"}', "application/json")
            return
        if self.path == "/":
            self._send(200, LOGIN_PAGE, "text/html; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/login":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(body)
        username = (form.get("username") or [""])[0]
        password = (form.get("password") or [""])[0]
        if username != "demo" or password != "demo":
            self._send(401, b'{"error": "bad credentials"}', "application/json")
            return
        self._send(
            302,
            b"",
            "text/plain; charset=utf-8",
            {"Location": "/private", "Set-Cookie": "session=demo-session; Path=/; HttpOnly"},
        )

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
    parser = argparse.ArgumentParser(description="Local cookie/session login fixture.")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    server, thread, base = start_server(args.port)
    print(f"login_app listening on {base}")
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        stop_server(server, thread)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
