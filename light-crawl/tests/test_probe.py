from __future__ import annotations

import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.models import PageKind
from light_crawl.probe import probe_target


STATIC_HTML = """<!doctype html>
<html lang="en">
<head><title>Static catalogue</title></head>
<body>
  <h1>Items</h1>
  <p>This is a server-rendered page with enough visible text to be classified as static HTML.
  It also links to a JSON endpoint that the router should notice.</p>
  <a href="/api/items">items api</a>
  <script src="/app.js"></script>
</body>
</html>
"""

SPA_HTML = """<!doctype html>
<html><head><title>App</title></head>
<body><div id="root"></div><script src="/app.js"></script></body></html>
"""

THIN_JS_HTML = """<!doctype html>
<html><head><title>JS catalogue</title></head>
<body><h1>Quotes</h1><p>Loading...</p>
<script>
const payload = """ + ("x" * 1200) + """;
document.querySelector('#items').innerHTML = payload;
</script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/static":
            body = STATIC_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/json":
            body = b'{"items": [{"id": 1}, {"id": 2}]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/thin-js":
            body = THIN_JS_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/spa":
            body = SPA_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/blocked":
            body = b"<html><body>Just a moment... cf-chl</body></html>"
            self.send_response(403)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_static_html(self) -> None:
        result = probe_target(f"{self.base}/static", timeout=5)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.page_kind, PageKind.STATIC_HTML.value)
        self.assertEqual(result.title, "Static catalogue")
        self.assertTrue(any("/api/items" in item for item in result.api_candidates))

    def test_json_api(self) -> None:
        result = probe_target(f"{self.base}/json", timeout=5)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.page_kind, PageKind.JSON_API.value)
        self.assertIn("application/json", result.content_type)

    def test_spa_shell(self) -> None:
        result = probe_target(f"{self.base}/spa", timeout=5)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.page_kind, PageKind.SPA_SHELL.value)
        self.assertGreaterEqual(result.script_count, 1)

    def test_thin_inline_script_is_spa(self) -> None:
        result = probe_target(f"{self.base}/thin-js", timeout=5)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.page_kind, PageKind.SPA_SHELL.value)
        self.assertGreaterEqual(result.inline_script_bytes, 1000)

    def test_blocked(self) -> None:
        result = probe_target(f"{self.base}/blocked", timeout=5)
        self.assertEqual(result.status, 403)
        self.assertEqual(result.page_kind, PageKind.BLOCKED.value)
        self.assertTrue(result.challenge)

    def test_network_error_is_reported(self) -> None:
        result = probe_target("http://127.0.0.1:1/nope", timeout=2)
        self.assertEqual(result.status, 0)
        self.assertTrue(result.error)


if __name__ == "__main__":
    unittest.main()
