from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.models import Delivery, Lane, PageKind, ProbeResult, TargetProfile
from light_crawl.router import decide_route


class RouterTests(unittest.TestCase):
    def test_static_html_routes_l0(self) -> None:
        probe = ProbeResult(
            url="https://example.com/",
            status=200,
            content_type="text/html",
            page_kind=PageKind.STATIC_HTML.value,
            visible_text_chars=900,
        )
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=10))
        self.assertEqual(decision.lane, Lane.L0_STATIC.value)
        self.assertEqual(decision.delivery, Delivery.SINGLE.value)
        self.assertGreaterEqual(decision.confidence, 0.7)

    def test_json_routes_l0_api(self) -> None:
        probe = ProbeResult(
            url="https://example.com/api/items",
            status=200,
            content_type="application/json",
            page_kind=PageKind.JSON_API.value,
            api_candidates=["https://example.com/api/items"],
        )
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=10))
        self.assertEqual(decision.lane, Lane.L0_API.value)
        self.assertIn("JSON", " ".join(decision.reasons))

    def test_signed_signal_routes_l2(self) -> None:
        probe = ProbeResult(
            url="https://example.com/app",
            status=200,
            content_type="text/html",
            page_kind=PageKind.STATIC_HTML.value,
            visible_text_chars=500,
            api_candidates=["https://example.com/api/items?page=1"],
            signature_hints=["sign", "timestamp"],
        )
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=10))
        self.assertEqual(decision.lane, Lane.L2_SIGNED.value)

    def test_blocked_routes_l3(self) -> None:
        probe = ProbeResult(
            url="https://example.com/",
            status=403,
            page_kind=PageKind.BLOCKED.value,
            challenge=True,
            cloudflare=True,
        )
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=10))
        self.assertEqual(decision.lane, Lane.L3_BLOCKED.value)
        self.assertTrue(any("CAPTCHA" in item for item in decision.stop_conditions))

    def test_spa_routes_l1(self) -> None:
        probe = ProbeResult(
            url="https://example.com/app",
            status=200,
            content_type="text/html",
            page_kind=PageKind.SPA_SHELL.value,
            script_count=7,
            visible_text_chars=50,
        )
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=10))
        self.assertEqual(decision.lane, Lane.L1_DYNAMIC.value)

    def test_app_target_routes_l4(self) -> None:
        probe = ProbeResult(url="D:/sample/app.asar", status=0)
        decision = decide_route(
            probe,
            TargetProfile(url="D:/sample/app.asar", kind="asar", volume=10),
        )
        self.assertEqual(decision.lane, Lane.L4_APP.value)

    def test_volume_selects_spider_delivery(self) -> None:
        probe = ProbeResult(
            url="https://example.com/",
            status=200,
            page_kind=PageKind.STATIC_HTML.value,
            visible_text_chars=900,
        )
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=5000))
        self.assertEqual(decision.delivery, Delivery.SPIDER.value)
        self.assertTrue(any("threshold" in item for item in decision.reasons))

    def test_probe_error_routes_l1_with_low_confidence(self) -> None:
        probe = ProbeResult(url="https://example.com/", status=0, error="timed out")
        decision = decide_route(probe, TargetProfile(url=probe.url, volume=1))
        self.assertEqual(decision.lane, Lane.L1_DYNAMIC.value)
        self.assertLess(decision.confidence, 0.5)


if __name__ == "__main__":
    unittest.main()
