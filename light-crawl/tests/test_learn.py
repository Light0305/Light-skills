from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.learn import learn_case
from light_crawl.models import Phase, TargetProfile
from light_crawl.state import CaseStore, LightCrawlError
from light_crawl.validation import run_check


class LearnTests(unittest.TestCase):
    def _case(self, root: Path) -> CaseStore:
        store = CaseStore.create(
            root / "cases",
            "shop-example",
            TargetProfile(url="https://www.example.com/products", authorized=True),
        )
        (store.spider_dir / "site.json").write_text('{"name": "example"}', encoding="utf-8")
        (store.repro_dir / "sign.py").write_text("print('ok')\n", encoding="utf-8")
        store.fixtures_dir.mkdir(exist_ok=True)
        (store.fixtures_dir / "request.json").write_text('{"url": "https://www.example.com/api"}', encoding="utf-8")
        store.advance(Phase.VERIFIED, "fixtures passed")
        run_check(store, 'repro/sign.py')
        return store

    def test_learn_copies_reusable_parts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = self._case(root)
            pack = learn_case(store, root / "sites")
            self.assertTrue((pack / "site.json").exists())
            self.assertTrue((pack / "README.md").exists())
            self.assertTrue((pack / "spider" / "site.json").exists())
            self.assertTrue((pack / "repro" / "sign.py").exists())
            self.assertTrue((pack / "fixtures" / "request.json").exists())
            self.assertEqual(store.state.phase, Phase.LEARNED.value)

    def test_learn_without_code_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = CaseStore.create(root / "cases", "empty", TargetProfile(url="https://example.com"))
            with self.assertRaises(LightCrawlError):
                learn_case(store, root / "sites")

    def test_learn_requires_verified_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = self._case(root)
            store.state.phase = Phase.BUILT.value
            with self.assertRaises(LightCrawlError):
                learn_case(store, root / "sites")

    def test_learn_force_replaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = self._case(root)
            first = learn_case(store, root / "sites")
            (first / "stale.txt").write_text("stale", encoding="utf-8")
            second = learn_case(store, root / "sites", force=True)
            self.assertFalse((second / "stale.txt").exists())


if __name__ == "__main__":
    unittest.main()
