from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.models import Phase, TargetProfile
from light_crawl.state import CaseStore
from light_crawl.verify import verify_case


class VerifyTests(unittest.TestCase):
    def _case(self, root: Path) -> CaseStore:
        store = CaseStore.create(
            root / "cases",
            "verify-case",
            TargetProfile(url="https://example.com/", authorized=True),
        )
        store.advance(Phase.VERIFIED, "fixtures and sample passed")
        (store.spider_dir / "spider.py").write_text("print('ok')\n", encoding="utf-8")
        (store.repro_dir / "sign.py").write_text("print('ok')\n", encoding="utf-8")
        (store.fixtures_dir / "request.json").write_text('{"url": "https://example.com/"}', encoding="utf-8")
        store.reports_dir.mkdir(exist_ok=True)
        (store.reports_dir / "report.md").write_text("# report\n", encoding="utf-8")
        return store

    def test_verified_case_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._case(Path(tmp))
            report = verify_case(store.directory)
            self.assertTrue(report.ok, [finding.message for finding in report.failures])
            self.assertGreaterEqual(len(report.warnings), 1)

    def test_tampered_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._case(Path(tmp))
            artifact = store.directory / "artifact.txt"
            artifact.write_text("original", encoding="utf-8")
            relative = store.add_artifact(artifact, "artifact")
            (store.directory / relative).write_text("tampered", encoding="utf-8")
            report = verify_case(store.directory)
            self.assertFalse(report.ok)
            self.assertTrue(any("hash" in finding.code for finding in report.failures))

    def test_verified_without_fixture_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore.create(
                Path(tmp) / "cases",
                "no-fixture",
                TargetProfile(url="https://example.com/", authorized=True),
            )
            store.advance(Phase.VERIFIED, "too early")
            (store.spider_dir / "spider.py").write_text("print('ok')\n", encoding="utf-8")
            report = verify_case(store.directory)
            self.assertFalse(report.ok)
            self.assertTrue(any("fixtures" in finding.code for finding in report.failures))

    def test_secret_fixture_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._case(Path(tmp))
            (store.fixtures_dir / "request.json").write_text(
                '{"url": "https://example.com/", "token": "live-secret"}',
                encoding="utf-8",
            )
            report = verify_case(store.directory)
            self.assertTrue(report.ok)
            self.assertTrue(any("fixture_secret" == finding.code for finding in report.warnings))


if __name__ == "__main__":
    unittest.main()
