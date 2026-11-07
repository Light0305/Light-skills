"""Isolated synthetic source/version regressions; no scientific experiments."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

try:
    from . import test_design_bridge as fixtures
except ImportError:
    import test_design_bridge as fixtures


class SourceHandoffTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.BridgeTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.bridge = fixtures.bridge

    def bound_input(self):
        c = self.case
        source = c.root / "synthetic-source.md"
        source.write_text("Synthetic source v1; fixture only", encoding="utf-8")
        record = json.loads((c.upstream / "evidence.jsonl").read_text(encoding="utf-8"))
        record.update(source_file=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        (c.upstream / "evidence.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
        return source

    def test_selected_evidence_drift_is_detected_beyond_the_idea_index(self):
        c = self.case
        source = self.bound_input()
        out = c.root / "new-design"
        self.bridge.ingest(c.upstream, "I01", out)
        self.assertTrue(self.bridge.verify(out)["ok"])
        source.write_text("Synthetic replacement; fixture only", encoding="utf-8")
        self.assertFalse(self.bridge.verify(out)["ok"])

    def test_already_stale_evidence_cannot_be_frozen_as_current(self):
        c = self.case
        source = self.bound_input()
        source.write_text("Synthetic replacement before ingest", encoding="utf-8")
        out = c.root / "new-design"
        with self.assertRaisesRegex(ValueError, "[Ss]ource.*(drift|changed|differ)"):
            self.bridge.ingest(c.upstream, "I01", out)
        self.assertFalse(out.exists())

    def test_ambiguous_paper_identity_does_not_silently_keep_last(self):
        c = self.case
        fixtures.write(c.upstream / "context.json", {"papers": [
            {"paper_id": "P01", "title": "Synthetic first identity"},
            {"paper_id": "P01", "title": "Synthetic incompatible identity"},
        ]})
        with self.assertRaisesRegex(ValueError, "[Dd]uplicate|[Cc]onflicting"):
            self.bridge.ingest(c.upstream, "I01", c.root / "new-design")

    def test_duplicate_evidence_is_rejected_before_creating_output(self):
        c = self.case
        path = c.upstream / "evidence.jsonl"
        path.write_bytes(path.read_bytes() * 2)
        with self.assertRaisesRegex(ValueError, "[Dd]uplicate"):
            self.bridge.ingest(c.upstream, "I01", c.root / "new-design")

    def own_source(self, path, digest=None):
        c = self.case
        c.ready()
        c.plan["sources"] = [{"source_id": "S01", "title": "Synthetic design source", "path": str(path)}]
        if digest is not None:
            c.plan["sources"][0]["sha256"] = digest
        c.plan["evidence"] = [{"evidence_id": "ED01", "source_id": "S01", "statement": "Synthetic local premise",
                               "locator": "Fixture section", "access_level": "full_text", "verified": True}]
        c.plan["claims"][0]["evidence_ids"] = ["ED01"]

    def test_scoped_checked_fact_cannot_use_missing_local_source(self):
        self.own_source(self.case.root / "missing.md")
        self.assertFalse(self.case.check()["ok"])

    def test_local_design_evidence_source_bytes_are_checked(self):
        source = self.case.root / "own-source.md"
        source.write_text("Synthetic source", encoding="utf-8")
        self.own_source(source, hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(self.case.check()["ok"])
        source.write_text("Synthetic changed source", encoding="utf-8")
        self.assertFalse(self.case.check()["ok"])

    def test_ready_plan_needs_nonempty_human_handoff(self):
        c = self.case
        c.ready()
        (c.out / "plan.md").write_text("", encoding="utf-8")
        self.assertFalse(c.check()["ok"])

    def test_unselected_paper_does_not_block_selected_design(self):
        c = self.case
        context = self.bridge.read_json(c.upstream / "context.json")
        context["papers"].append({"paper_id": "P_unselected", "title": "Synthetic unrelated report",
                                  "pdf_sha256": "a" * 64, "assets": {"paper.pdf": str(c.root / "absent.pdf")}})
        fixtures.write(c.upstream / "context.json", context)
        result = self.bridge.ingest(c.upstream, "I01", c.root / "selected-design")
        self.assertTrue(result["ok"])

    def test_selected_pdf_identity_is_checked(self):
        c = self.case
        pdf = c.root / "synthetic.pdf"
        pdf.write_bytes(b"SYNTHETIC source bytes; not a scientific PDF")
        context = self.bridge.read_json(c.upstream / "context.json")
        context["papers"][0].update(pdf_sha256="a" * 64, assets={"paper.pdf": str(pdf)})
        fixtures.write(c.upstream / "context.json", context)
        with self.assertRaisesRegex(ValueError, "Source PDF bytes differ"):
            self.bridge.ingest(c.upstream, "I01", c.root / "selected-design")

    def test_future_unbound_source_does_not_block_current_pilot(self):
        c = self.case
        c.ready()
        c.plan["sources"] = [{"source_id": "S_future", "title": "Synthetic future source",
                               "path": str(c.root / "not-yet-supplied.md")}]
        result = c.check()
        self.assertTrue(result["ok"])
        self.assertTrue(any("S_future" in w for w in result["warnings"]))

    def test_scoped_local_evidence_needs_the_reviewed_hash(self):
        source = self.case.root / "source.md"
        source.write_text("Synthetic local premise", encoding="utf-8")
        self.own_source(source)
        result = self.case.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("reviewed source sha256" in e for e in result["errors"]))

    @unittest.skipUnless((fixtures.ROOT.parent / "light-experiment/scripts/experiment.py").is_file(),
                         "Native sibling execution source is unavailable")
    def test_native_execution_intake_freezes_the_actual_design(self):
        c = self.case
        c.ready()
        protocol = c.out / "protocols/fixture.md"
        protocol.parent.mkdir()
        protocol.write_text("Synthetic protocol; no experiment executed", encoding="utf-8")
        self.assertTrue(c.check()["ok"])
        before = (c.out / "design.json").read_bytes()
        launcher = fixtures.ROOT.parent / "light-experiment/scripts/experiment.py"
        out = c.root / "execution"
        result = subprocess.run([sys.executable, "-B", str(launcher), "init", "--design", str(c.out),
                                 "--out", str(out), "--max-runs", "1", "--max-wall-seconds", "1",
                                 "--budget-basis", "Synthetic initialization test; no execution"],
                                cwd=c.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((out / "inputs/design/design.json").read_bytes(), before)
        self.assertEqual((out / "inputs/design/protocols/fixture.md").read_bytes(), protocol.read_bytes())
        self.assertEqual((c.out / "design.json").read_bytes(), before)
        self.assertFalse((out / "runs").exists())


if __name__ == "__main__":
    unittest.main()
