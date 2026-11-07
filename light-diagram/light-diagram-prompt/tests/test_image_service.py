"""Offline routing and real localhost HTTP tests, with synthetic image fixtures.

No external credentials, paid generation, or scientific image quality evaluation.
"""
import base64
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/image_service.py"
spec = importlib.util.spec_from_file_location("image_service", SCRIPT)
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
KEY = "synthetic-test-key-never-a-real-credential"


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


PNG = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b""))


@contextmanager
def mock_api(mode="base64"):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, code=200, mime="application/json"):
            raw = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append({"method": "POST", "body": body, "authorization": self.headers.get("Authorization"),
                          "user_agent": self.headers.get('User-Agent')})
            if mode == "error":
                return self.send({"error": "raw provider error echoed " + KEY}, 401)
            if mode == "redirect":
                self.send_response(307)
                self.send_header("Location", self.server.origin + "/redirect-target")
                self.end_headers()
                return
            if mode == "text":
                return self.send({"job_id": "not-an-image", "message": "queued"})
            if mode == "bad-image":
                return self.send({"data": [{"b64_json": base64.b64encode(b"not a PNG").decode()}]})
            if mode == "url":
                return self.send({"data": [{"url": self.server.origin + "/asset?signature=synthetic"}]})
            return self.send({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})

        def do_GET(self):
            calls.append({"method": "GET", "authorization": self.headers.get("Authorization"),
                          "user_agent": self.headers.get('User-Agent')})
            return self.send(PNG, mime="image/png")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.origin = f"http://127.0.0.1:{server.server_port}"
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server.origin + "/v1/images/generations", calls
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def config(url="https://image-service.example/v1/images/generations", **extra):
    return {"url": url, "api_key": KEY, "model": "fixture-image-model", **extra}


class RoutingTests(unittest.TestCase):
    def test_available_host_precedes_custom(self):
        self.assertEqual(service.select_route(config(), "yes")["selected"], "builtin")

    def test_custom_when_host_absent(self):
        self.assertEqual(service.select_route(config(), "no")["selected"], "custom")

    def test_prompt_only_without_capabilities(self):
        self.assertEqual(service.select_route({}, "no")["selected"], "prompt_only")

    def test_explicit_prompt_only_overrides_both(self):
        self.assertEqual(service.select_route(config(), "yes", "prompt_only")["selected"], "prompt_only")

    def test_explicit_custom_overrides_host(self):
        self.assertEqual(service.select_route(config(), "yes", "custom")["selected"], "custom")

    def test_unknown_host_requires_discovery(self):
        self.assertEqual(service.select_route(config(), "unknown")["selected"], "discovery_required")

    def test_incomplete_config_delivers_prompt(self):
        self.assertEqual(service.select_route({"model": "a"}, "no")["reason"], "custom_configuration_incomplete")

    def test_base_url_construction(self):
        c = config()
        del c["url"]
        c["base_url"] = "https://example.com/custom/v1/"
        self.assertEqual(service.custom_settings(c)["url"], "https://example.com/custom/v1/images/generations")

    def test_env_key_precedes_literal(self):
        with patch.dict(os.environ, {"FIXTURE_IMAGE_KEY": "fixture-environment-key"}):
            settings = service.custom_settings(config(api_key_env="FIXTURE_IMAGE_KEY"))
        self.assertEqual(settings["headers"]["Authorization"], "Bearer fixture-environment-key")

    def test_service_origin_is_completed_to_image_endpoint(self):
        self.assertEqual(service.custom_settings(config(url='https://example.com/'))['url'],
                         'https://example.com/v1/images/generations')

    def test_v1_url_prefix_is_completed_to_image_endpoint(self):
        self.assertEqual(service.custom_settings(config(url='https://example.com/v1/'))['url'],
                         'https://example.com/v1/images/generations')

    def test_explicit_custom_endpoint_path_is_preserved(self):
        self.assertEqual(service.custom_settings(config(url='https://example.com/custom/generate'))['url'],
                         'https://example.com/custom/generate')

    def test_base_url_origin_uses_v1(self):
        c=config();del c['url'];c['base_url']='https://example.com'
        self.assertEqual(service.custom_settings(c)['url'], 'https://example.com/v1/images/generations')

    def test_unsupported_protocol_does_not_claim_compatibility(self):
        with self.assertRaises(service.ServiceError):
            service.custom_settings(config(api_style="arbitrary-vendor"))

    def test_params_cannot_replace_published_prompt(self):
        with self.assertRaises(service.ServiceError):
            service.custom_settings(config(params={"prompt": "replace the delivered prompt"}))

    def test_remote_insecure_url_rejected(self):
        with self.assertRaises(service.ServiceError):
            service.custom_settings(config(url="http://remote.example/images"))


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.prompt = self.base / "提示词-v1.txt"
        self.prompt.write_text("Draw a scientific schematic. 图中文字仅为 A 和 B。", encoding="utf-8")

    def run_cli(self, *args):
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args,
                                 "--prompt", str(self.prompt)], capture_output=True, text=True, encoding="utf-8")
        events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        self.assertNotIn(KEY, result.stdout + result.stderr)
        return result, events

    def local_config(self, url):
        path = self.base / "image-config.json"
        path.write_text(json.dumps(config(url)), encoding="utf-8")
        return path

    def test_actual_base64_http_and_exact_prompt(self):
        with mock_api() as (url, calls):
            result = service.generate_custom(config(url, params={"size": "1536x1024"}), self.prompt, self.base / "new")
        self.assertEqual(result["status"], "generated")
        self.assertEqual(result["review_status"], "not_run")
        self.assertEqual(result["calls_this_run"], 1)
        self.assertEqual(calls[0]["body"]["prompt"], self.prompt.read_text("utf-8"))
        self.assertEqual(calls[0]["body"]["model"], "fixture-image-model")
        self.assertEqual(calls[0]["body"]["size"], "1536x1024")
        self.assertNotIn("response_format", calls[0]["body"])
        self.assertEqual(calls[0]['user_agent'], service.USER_AGENT)
        self.assertEqual(Path(result["images"][0]["path"]).read_bytes(), PNG)
        self.assertEqual(result["executed_prompt"]["sha256"], hashlib.sha256(self.prompt.read_bytes()).hexdigest())
        self.assertNotIn(KEY, json.dumps(result))

    def test_url_download_has_no_api_auth(self):
        with mock_api("url") as (url, calls):
            result = service.generate_custom(config(url), self.prompt, self.base / "url")
        self.assertEqual(result["status"], "generated")
        self.assertEqual([c["method"] for c in calls], ["POST", "GET"])
        self.assertEqual(calls[0]["authorization"], "Bearer " + KEY)
        self.assertIsNone(calls[1]["authorization"])
        self.assertEqual(calls[1]['user_agent'], service.USER_AGENT)

    def test_failure_is_recorded_without_retry_or_key_echo(self):
        with mock_api("error") as (url, calls):
            result, events = self.run_cli("generate", "--host-available", "no", "--config", str(self.local_config(url)),
                                          "--output-dir", str(self.base / "failure"), "--prompt-published")
        self.assertEqual(result.returncode, 2)
        last = events[-1]
        self.assertEqual(last["status"], "failed")
        self.assertEqual(last["calls_this_run"], 1)
        self.assertEqual(len(calls), 1)
        self.assertIn("401", last["error"])
        self.assertNotIn(KEY, (self.base / "failure/generation.json").read_text())

    def test_queued_job_is_not_success(self):
        with mock_api("text") as (url, calls):
            result = service.generate_custom(config(url), self.prompt, self.base / "job")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["images"], [])

    def test_nonimage_bytes_are_not_success(self):
        with mock_api("bad-image") as (url, calls):
            result = service.generate_custom(config(url), self.prompt, self.base / "bad")
        self.assertEqual(result["status"], "failed")

    def test_redirect_does_not_resend_auth_or_post(self):
        with mock_api("redirect") as (url, calls):
            result = service.generate_custom(config(url), self.prompt, self.base / "redirect")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(calls), 1)

    def test_changed_prompt_requires_republication(self):
        old = hashlib.sha256(self.prompt.read_bytes()).hexdigest()
        self.prompt.write_text("Changed prompt", encoding="utf-8")
        with self.assertRaises(service.ServiceError):
            service.generate_custom(config(), self.prompt, self.base / "changed", old)
        self.assertFalse((self.base / "changed").exists())

    def test_existing_output_is_preserved(self):
        output = self.base / "existing"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("Keep me")
        with self.assertRaises(FileExistsError):
            service.generate_custom(config(), self.prompt, output)
        self.assertEqual(marker.read_text(), "Keep me")

    def test_plan_has_zero_http_calls(self):
        with mock_api() as (url, calls):
            result, events = self.run_cli("plan", "--host-available", "no", "--config", str(self.local_config(url)))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(events[0]["event"], "prompt_ready")
        self.assertEqual(events[-1]["selected"], "custom")
        self.assertEqual(calls, [])

    def test_cli_refuses_call_without_prompt_publication(self):
        with mock_api() as (url, calls):
            result, events = self.run_cli("generate", "--host-available", "no", "--config", str(self.local_config(url)),
                                          "--output-dir", str(self.base / "unpublished"))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])
        self.assertFalse((self.base / "unpublished").exists())

    def test_cli_custom_generates_and_keeps_prompt_link(self):
        with mock_api() as (url, calls):
            result, events = self.run_cli("generate", "--host-available", "no", "--config", str(self.local_config(url)),
                                          "--output-dir", str(self.base / "cli"), "--prompt-published")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(events[0]["event"], "prompt_ready")
        self.assertEqual(events[0]["prompt"]["sha256"], events[-1]["published_prompt"]["sha256"])
        self.assertEqual(events[-1]["status"], "generated")

    def test_prompt_only_ignores_unreadable_config(self):
        result, events = self.run_cli("generate", "--provider", "prompt_only", "--config", str(self.base / "missing.json"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(events[-1]["selected"], "prompt_only")

    def test_broken_custom_config_does_not_block_available_host(self):
        result, events = self.run_cli("plan", "--host-available", "yes", "--config", str(self.base / "missing.json"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(events[-1]["selected"], "builtin")


if __name__ == "__main__":
    unittest.main()
