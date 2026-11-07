from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.benchmark import load_cases, run_benchmark, write_benchmark
from light_crawl.state import LightCrawlError


class BenchmarkTests(unittest.TestCase):
    def test_builtin_cases_pass(self) -> None:
        summary = run_benchmark(ROOT / "benchmarks" / "cases")
        self.assertEqual(summary["total"], 5)
        self.assertEqual(summary["passed"], 5)
        self.assertEqual(summary["accuracy"], 1.0)
        for result in summary["results"]:
            self.assertTrue(result["passed"], result["slug"])
        self.assertIsNotNone(summary["averages"]["success_rate"])
        self.assertEqual(summary["measured_averages"]["success_rate"], 1.0)
        by_slug = {result["slug"]: result for result in summary["results"]}
        self.assertEqual(by_slug["static_quotes"]["measured"]["items"], 10)
        self.assertFalse(by_slug["cloudflare"]["measured"])

    def test_load_cases_rejects_missing_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LightCrawlError):
                load_cases(Path(tmp) / "missing")

    def test_source_case_metrics_override_measured_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = root / "bench" / "source_metrics"
            cases.mkdir(parents=True)
            case_data = {
                "slug": "source_metrics",
                "source_case": "actual-case",
                "target": {
                    "url": "https://quotes.toscrape.com/",
                    "kind": "web",
                    "volume": 10,
                    "authorized": True,
                },
                "expected": {"lane": "L0_STATIC", "delivery": "single", "min_confidence": 0.7},
                "metrics": {"success_rate": 0.5},
            }
            (cases / "case.json").write_text(json.dumps(case_data), encoding="utf-8")
            (cases / "probe.json").write_text(
                (ROOT / "benchmarks" / "cases" / "static_quotes" / "probe.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            source = root / "cases" / "actual-case"
            source.mkdir(parents=True)
            (source / "case.json").write_text(
                json.dumps({"metrics": {"items": 7, "success_rate": 0.99}}),
                encoding="utf-8",
            )
            summary = run_benchmark(root / "bench", root / "cases")
            self.assertEqual(summary["measured_from_source_cases"], 1)
            self.assertEqual(summary["results"][0]["measured"]["items"], 7)
            self.assertEqual(summary["measured_averages"]["success_rate"], 0.99)

    def test_write_benchmark_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_benchmark(ROOT / "benchmarks" / "cases")
            json_path, report_path = write_benchmark(summary, Path(tmp))
            self.assertTrue(json_path.exists())
            self.assertTrue(report_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Routing accuracy: 5/5", report)
            self.assertIn("signed_api", report)


if __name__ == "__main__":
    unittest.main()
