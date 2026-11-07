from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.metrics import record_metrics, show_metrics
from light_crawl.models import TargetProfile
from light_crawl.state import CaseStore, LightCrawlError


class MetricsTests(unittest.TestCase):
    def test_record_computes_per_item_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(
                Path(tmp) / "cases",
                "metrics-case",
                TargetProfile(url="https://example.com/", authorized=True),
            )
            payload = record_metrics(
                store,
                items=100,
                requests=120,
                browser_seconds=50,
                tokens=4000,
                success_rate=0.95,
                drift_recovery=0.8,
                note="unit test",
            )
            self.assertEqual(payload["requests_per_item"], 1.2)
            self.assertEqual(payload["browser_seconds_per_item"], 0.5)
            self.assertEqual(payload["tokens_per_1k_items"], 40000.0)
            self.assertEqual(payload["metrics_note"], "unit test")
            self.assertEqual(show_metrics(store)["success_rate"], 0.95)
            self.assertEqual(len(store.evidence()), 1)

    def test_invalid_metrics_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(
                Path(tmp) / "cases",
                "metrics-invalid",
                TargetProfile(url="https://example.com/", authorized=True),
            )
            with self.assertRaises(LightCrawlError):
                record_metrics(
                    store,
                    items=0,
                    requests=1,
                    browser_seconds=0,
                    tokens=0,
                    success_rate=1.0,
                    drift_recovery=0.0,
                )
            with self.assertRaises(LightCrawlError):
                record_metrics(
                    store,
                    items=10,
                    requests=1,
                    browser_seconds=0,
                    tokens=0,
                    success_rate=1.5,
                    drift_recovery=0.0,
                )


if __name__ == "__main__":
    unittest.main()
