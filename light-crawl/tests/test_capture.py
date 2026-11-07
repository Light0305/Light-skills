from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.capture import capture_target
from light_crawl.models import PageKind, Phase, ProbeResult, TargetProfile
from light_crawl.state import CaseStore
from light_crawl.utils import write_json


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        body = b"<html><body><h1>Captured</h1><p>fixture body</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Set-Cookie", "secret=should-not-be-saved")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.url = f"http://{host}:{port}/page"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_capture_saves_fixtures_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(
                Path(tmp) / "cases",
                "capture-case",
                TargetProfile(url=self.url, authorized=True),
            )
            write_json(
                store.probe_file,
                ProbeResult(
                    url=self.url,
                    status=200,
                    page_kind=PageKind.STATIC_HTML.value,
                    visible_text_chars=100,
                ).to_dict(),
            )
            store.advance(Phase.PROBED, "probe")

            result = capture_target(store, timeout=5)
            self.assertEqual(result.status, 200)
            self.assertTrue(result.body_path.exists())
            self.assertTrue(result.meta_path.exists())
            self.assertTrue(result.request_path.exists())
            self.assertIn(b"Captured", result.body_path.read_bytes())
            self.assertEqual(store.state.phase, Phase.CAPTURED.value)
            self.assertGreaterEqual(len(store.evidence()), 1)

            meta = result.meta_path.read_text(encoding="utf-8")
            self.assertNotIn("secret=should-not-be-saved", meta)
            request = result.request_path.read_text(encoding="utf-8")
            self.assertNotIn("secret=should-not-be-saved", request)
            self.assertIn('"cookies": {}', request)

    def test_capture_requires_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(
                Path(tmp) / "cases",
                "no-probe",
                TargetProfile(url=self.url, authorized=True),
            )
            with self.assertRaises(Exception):
                capture_target(store, timeout=5)

    def test_actual_http_truncation_is_in_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(Path(tmp), 'limited', TargetProfile(url=self.url, authorized=True))
            write_json(store.probe_file, ProbeResult(url=self.url, status=200).to_dict())
            result = capture_target(store, timeout=5, max_bytes=12)
            self.assertEqual(len(result.body), 12)
            self.assertTrue(result.truncated)
            import json
            self.assertTrue(json.loads(result.meta_path.read_text(encoding='utf-8'))['truncated'])


if __name__ == "__main__":
    unittest.main()
