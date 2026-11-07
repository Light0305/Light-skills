"""Synthetic regression fixtures for source/version recovery, never research evidence."""
import json
import os
from pathlib import Path
import unittest
import subprocess
import sys

try:
    from . import test_bridge as fixtures
except ImportError:
    import test_bridge as fixtures


class RevisionRegressions(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.BridgeCase()
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.bridge = fixtures.bridge

    def test_latest_csv_decision_is_used(self):
        c = self.case
        fixtures.save(c.run / "screening.jsonl", [
            {"paper_id": "p_one", "decision": "exclude", "reason_code": "OUT_OF_SCOPE"},
            {"paper_id": "p_two", "decision": "include", "reason_code": "IN_SCOPE"},
        ], jsonl=True)
        os.utime(c.run / "screening.jsonl", ns=(1_000_000_000, 1_000_000_000))
        # The existing CSV is newer and says p_one=maybe, p_two=exclude.
        c.ingest()
        context = self.bridge.read_json(c.out / "context.json")
        self.assertEqual([p["paper_id"] for p in context["papers"]], ["p_one"])
        self.assertEqual(context["papers"][0]["decision"], "maybe")

    def test_equal_time_conflicting_screening_requires_resolution(self):
        c = self.case
        fixtures.save(c.run / "screening.jsonl", [
            {"paper_id": "p_one", "decision": "exclude", "reason_code": "OUT_OF_SCOPE"},
        ], jsonl=True)
        stamp = 1_000_000_000
        for name in ("screening.csv", "screening.jsonl"):
            os.utime(c.run / name, ns=(stamp, stamp))
        with self.assertRaisesRegex(self.bridge.InputError, "screening.*conflict|Conflicting screening"):
            c.ingest()

    def test_incomplete_library_manifest_is_not_silently_accepted(self):
        c = self.case
        manifest = self.bridge.read_json(c.lit / "manifest.json")
        manifest["entries"] = manifest["entries"][:1]
        fixtures.save(c.lit / "manifest.json", manifest)
        with self.assertRaisesRegex(self.bridge.InputError, "[Mm]anifest.*(incomplete|index|cover)"):
            self.bridge.ingest(c.lit, None, c.out)

    def test_selected_pdf_is_compared_with_recorded_library_hash(self):
        c = self.case
        article = c.lit / "synthetic-1"
        pdf = article / "paper.pdf"
        pdf.write_bytes(b"SYNTHETIC original source bytes; not a real PDF")
        meta = self.bridge.read_json(article / "meta.json")
        meta["pdf_sha256"] = self.bridge.sha256(pdf)
        fixtures.save(article / "meta.json", meta)
        pdf.write_bytes(b"SYNTHETIC replaced source bytes; not a real PDF")
        with self.assertRaisesRegex(self.bridge.InputError, "PDF.*(changed|differ)"):
            c.ingest()

    def test_force_does_not_erase_evidence_source_drift(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        source = Path(evidence[0]["source_file"])
        evidence[0]["source_sha256"] = self.bridge.sha256(source)
        c.write_bundle(doc, evidence, searches)
        source.write_text("SYNTHETIC replacement; old anchor is no longer valid", encoding="utf-8")
        c.ingest(force=True)
        self.assertFalse(self.bridge.verify(c.out)["ok"])

    def test_force_archives_the_previous_input_context(self):
        c = self.case
        c.workspace()
        before = (c.out / "context.json").read_bytes()
        (c.lit / "synthetic-1" / "paper.md").write_text("SYNTHETIC revised source", encoding="utf-8")
        c.ingest(force=True)
        context = self.bridge.read_json(c.out / "context.json")
        history = context.get("context_history", [])
        self.assertTrue(history)
        self.assertEqual(Path(history[-1]["path"]).read_bytes(), before)

    def test_changed_question_cannot_reuse_old_searches_without_a_version_bump(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        doc["ideas"][0]["question"] = "SYNTHETIC different scientific question"
        c.write_bundle(doc, evidence, searches)
        self.assertFalse(self.bridge.verify(c.out)["ok"])

    def test_known_other_papers_file_cannot_substitute_for_named_evidence(self):
        c = self.case
        doc, evidence, searches = c.workspace()
        fixtures.save(c.out / "external_papers.jsonl", [{
            "paper_id": "ext_other", "title": "SYNTHETIC other report",
            "url": "https://fixture.invalid/other", "retrieved_at": "2026-11-06",
        }], jsonl=True)
        evidence[0]["paper_id"] = "ext_other"
        doc["ideas"][0]["prior_art"] = []
        c.write_bundle(doc, evidence, searches)
        self.assertFalse(self.bridge.verify(c.out)["ok"])

    def test_editorial_title_change_preserves_search_binding(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        doc["ideas"][0]["title"] = "SYNTHETIC clearer title; same scientific content"
        c.write_bundle(doc, evidence, searches)
        self.assertTrue(self.bridge.verify(c.out)["ok"])

    def test_refreshing_searches_for_a_real_revision_allows_review(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        idea = doc["ideas"][0]
        idea.update(version=2, question="SYNTHETIC revised question")
        idea["history"] = [{"version": 2, "previous_version": 1, "reason": "Synthetic revision fixture"}]
        for row in searches:
            row["idea_versions"]["I01"] = 2
            row["idea_fingerprints"] = {"I01": self.bridge.idea_fingerprint(idea)}
        c.write_bundle(doc, evidence, searches)
        self.assertTrue(self.bridge.verify(c.out)["ok"])

    def test_legacy_unbound_records_remain_readable_as_hold(self):
        c = self.case
        doc, evidence, searches = c.workspace()
        evidence[0].pop("source_sha256")
        for row in searches:
            row.pop("idea_fingerprints")
        c.write_bundle(doc, evidence, searches)
        result = self.bridge.verify(c.out)
        self.assertTrue(result["ok"])
        self.assertTrue(any("source hash is unrecorded" in w for w in result["warnings"]))

    def test_legacy_unbound_sources_cannot_silently_support_recommendation(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        evidence[0].pop("source_sha256")
        for row in searches:
            row.pop("idea_fingerprints")
        c.write_bundle(doc, evidence, searches)
        result = self.bridge.verify(c.out)
        self.assertFalse(result["ok"])
        self.assertTrue(any("reviewed source_sha256" in e for e in result["errors"]))
        self.assertTrue(any("idea_fingerprints" in e for e in result["errors"]))

    def test_fingerprints_command_is_read_only(self):
        c = self.case
        c.workspace()
        before = {p: p.read_bytes() for p in c.out.rglob("*") if p.is_file()}
        result = subprocess.run([sys.executable, "-B", str(fixtures.ROOT / "scripts/idea_bridge.py"),
                                 "fingerprint", "--workspace", str(c.out)],
                                cwd=c.base, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(json.loads(result.stdout)["ideas"]["I01"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(before, {p: p.read_bytes() for p in c.out.rglob("*") if p.is_file()})

    def test_unindexed_local_evidence_source_drift_is_detected(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        source = c.base / "separately_supplied_excerpt.md"
        source.write_text("SYNTHETIC source excerpt from the named report", encoding="utf-8")
        evidence[0].update(source_file=str(source.resolve()), source_sha256=self.bridge.sha256(source))
        c.write_bundle(doc, evidence, searches)
        self.assertTrue(self.bridge.verify(c.out)["ok"])
        source.write_text("SYNTHETIC changed excerpt", encoding="utf-8")
        self.assertFalse(self.bridge.verify(c.out)["ok"])

    def test_equal_time_equivalent_screening_is_accepted(self):
        import csv
        c = self.case
        with (c.run / "screening.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        fixtures.save(c.run / "screening.jsonl", rows, jsonl=True)
        for name in ("screening.csv", "screening.jsonl"):
            os.utime(c.run / name, ns=(1_000_000_000, 1_000_000_000))
        c.ingest()
        self.assertEqual(len(self.bridge.read_json(c.out / "context.json")["papers"]), 1)

    def test_forged_evidence_hash_reports_error_without_crashing(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        evidence[0]["source_sha256"] = []
        c.write_bundle(doc, evidence, searches)
        result = self.bridge.verify(c.out)
        self.assertFalse(result["ok"])
        self.assertTrue(any("source_sha256" in e for e in result["errors"]))

    def test_unchanged_refresh_keeps_valid_recommendation_and_checks_archive(self):
        c = self.case
        c.workspace(recommended=True)
        c.ingest(force=True)
        self.assertTrue(self.bridge.verify(c.out)["ok"])
        history = self.bridge.read_json(c.out / "context.json")["context_history"]
        Path(history[-1]["path"]).write_text("SYNTHETIC changed archive", encoding="utf-8")
        result = self.bridge.verify(c.out)
        self.assertFalse(result["ok"])
        self.assertTrue(any("context archive" in e for e in result["errors"]))

    def test_empty_file_cannot_be_checked_source_evidence(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        source = c.base / "empty-source.md"
        source.write_bytes(b"")
        evidence[0].update(source_file=str(source), source_sha256=self.bridge.sha256(source))
        c.write_bundle(doc, evidence, searches)
        result = self.bridge.verify(c.out)
        self.assertFalse(result["ok"])
        self.assertTrue(any("source_file is empty" in e for e in result["errors"]))

    @unittest.skipUnless((fixtures.ROOT.parent / "light-design/scripts/design_bridge.py").is_file(),
                         "Native sibling Design source is not installed")
    def test_native_design_intake_preserves_selected_revision_and_evidence(self):
        c = self.case
        doc, evidence, searches = c.workspace(recommended=True)
        self.assertTrue(self.bridge.verify(c.out)["ok"])
        out = c.base / "Design/PROT-0001_synthetic/v01"
        launcher = fixtures.ROOT.parent / "light-design/scripts/design_bridge.py"
        result = subprocess.run([sys.executable, "-B", str(launcher), "ingest", "--ideas", str(c.out),
                                 "--idea-id", "I01", "--out", str(out)],
                                cwd=c.base, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        returned = json.loads(result.stdout)
        self.assertEqual(returned["status"], "draft")
        context = json.loads((out / "context.json").read_text(encoding="utf-8"))
        self.assertEqual(context["idea"]["version"], doc["ideas"][0]["version"])
        self.assertEqual(context["evidence"][0]["source_sha256"], evidence[0]["source_sha256"])
        self.assertEqual(context["novelty_log"][0]["idea_fingerprints"], searches[0]["idea_fingerprints"])


if __name__ == "__main__":
    unittest.main()
