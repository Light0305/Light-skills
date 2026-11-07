#!/usr/bin/env python
"""A local Cloudflare-style challenge fixture used by the L3 benchmark case.

`/` always returns a 403 challenge. `/js-challenge` is a browser-solvable
challenge: it sets a cookie and redirects to `/ok`, so the browser capture path
can be tested end to end without pretending to solve real Cloudflare.
"""

from __future__ import annotations

import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


CHALLENGE = b"""<!doctype html>
<html><head><title>Just a moment...</title></head>
<body>Just a moment... Enable JavaScript and cookies to continue. cf-chl</body>
</html>"""

JS_CHALLENGE = b"""<!doctype html>
<html><head><title>Checking your browser...</title></head>
<body>
<script>
  document.cookie = "lc_passed=1; path=/";
  window.location.href = "/ok";
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: bytes, content_type: str, challenge: bool = False) -> None:
        self.send_response(status)
        self.send_header("Server", "cloudflare")
        self.send_header("CF-Ray", "8f00local")
        if challenge:
            self.send_header("CF-Mitigated", "challenge")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send(403, CHALLENGE, "text/html; charset=utf-8", challenge=True)
            return
        if self.path == "/js-challenge":
            self._send(200, JS_CHALLENGE, "text/html; charset=utf-8")
            return
        if self.path == "/ok":
            self._send(200, b"ok", "text/plain; charset=utf-8")
            return
        if self.path == "/robots.txt":
            self._send(200, b"User-agent: *\nAllow: /\n", "text/plain; charset=utf-8")
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
    parser = argparse.ArgumentParser(description="Local Cloudflare-style challenge fixture.")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    server, thread, base = start_server(args.port)
    print(f"cloudflare_app listening on {base}")
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        stop_server(server, thread)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
