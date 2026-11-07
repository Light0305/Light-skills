from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.models import Phase, TargetProfile
from light_crawl.state import CaseStore, LightCrawlError


class StateTests(unittest.TestCase):
    def test_create_advance_evidence_and_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cases"
            target = TargetProfile(
                url="https://example.com/",
                kind="web",
                volume=50,
                authorized=True,
                notes="unit test",
            )
            store = CaseStore.create(root, "My Case!", target)
            self.assertEqual(store.directory.name, "my-case")
            self.assertTrue((store.directory / "scope.md").exists())
            self.assertTrue((store.directory / "target.json").exists())
            self.assertEqual(store.state.phase, Phase.INTAKE.value)

            store.advance(Phase.PROBED, "probe done")
            entry = store.add_evidence(
                phase=Phase.PROBED.value,
                source="test",
                action="probe",
                observation="status=200",
                inference="static page",
                confidence="high",
            )
            self.assertEqual(entry.evidence_id, "E0001")
            artifact = store.directory / "sample.txt"
            artifact.write_text("hello", encoding="utf-8")
            relative = store.add_artifact(artifact, "sample")
            self.assertTrue((store.directory / relative).exists())
            self.assertEqual(len(store.state.artifacts[relative]["sha256"]), 64)

            reloaded = CaseStore.load(store.directory)
            self.assertEqual(reloaded.state.phase, Phase.PROBED.value)
            self.assertEqual(len(reloaded.evidence()), 1)
            self.assertEqual(reloaded.state.target["url"], target.url)

    def test_backwards_transition_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cases"
            store = CaseStore.create(root, "case", TargetProfile(url="https://example.com/"))
            store.advance(Phase.ROUTED, "routed")
            with self.assertRaises(LightCrawlError):
                store.advance(Phase.PROBED, "back")

    def test_resolve_by_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cases"
            store = CaseStore.create(root, "slug-case", TargetProfile(url="https://example.com/"))
            resolved = CaseStore.resolve("slug-case", root)
            self.assertEqual(resolved.directory.resolve(), store.directory.resolve())

    def test_missing_case_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LightCrawlError):
                CaseStore.resolve("missing", Path(tmp) / "cases")


if __name__ == "__main__":
    unittest.main()
