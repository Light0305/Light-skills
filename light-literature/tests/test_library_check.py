"""Source drift and real downstream intake on isolated synthetic PDF libraries."""
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from litsearch.cli import main
from litsearch.io import read_json, write_json
from litsearch.library_check import verify_literature
from litsearch.literature import add_pdf, extract_pdf_metadata
try:
    from .test_literature import make_pdf
except ImportError:
    from test_literature import make_pdf


class LibraryCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="litsearch-library-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "Literature"
        make_pdf(self.root / "paper.pdf")
        result = add_pdf(self.root / "paper.pdf", self.out, title="Synthetic report one")
        self.article = Path(result["folder"])

    def test_consistent_prepared_library_does_not_claim_reading_completion(self):
        result = verify_literature(self.out)
        self.assertTrue(result["ok"])
        self.assertEqual(result["entries"][0]["artifacts"]["note.md"], "missing_or_empty")

    def test_changed_pdf_invalidates_reading_context_without_writes(self):
        before = (self.out / "manifest.json").read_bytes()
        make_pdf(self.article / "paper.pdf", pages=3)
        result = verify_literature(self.out)
        self.assertFalse(result["ok"])
        self.assertTrue(result["integrity_ok"])
        self.assertTrue(result["needs_review"])
        self.assertEqual(before, (self.out / "manifest.json").read_bytes())

    def test_partial_manifest_is_detected(self):
        add_pdf(self.root / "paper.pdf", self.out, title="Synthetic report two")
        manifest = read_json(self.out / "manifest.json")
        manifest["entries"] = manifest["entries"][:1]
        write_json(self.out / "manifest.json", manifest)
        self.assertFalse(verify_literature(self.out)["integrity_ok"])

    def test_removed_pdf_is_detected(self):
        (self.article / "paper.pdf").unlink()
        self.assertFalse(verify_literature(self.out)["integrity_ok"])

    def test_empty_note_is_not_present_reading_work(self):
        (self.article / "note.md").write_text("", encoding="utf-8")
        meta = read_json(self.article / "meta.json")
        meta["note_status"] = "present"
        write_json(self.article / "meta.json", meta)
        self.assertTrue(verify_literature(self.out)["needs_review"])

    def test_cli_returns_review_status_for_source_drift(self):
        make_pdf(self.article / "paper.pdf", pages=2)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["literature", "verify", "--out", str(self.out)])
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(stdout.getvalue())["needs_review"])

    def test_existing_untracked_pdf_does_not_gain_a_verified_history(self):
        meta = read_json(self.article / "meta.json")
        meta.pop("pdf_sha256")
        write_json(self.article / "meta.json", meta)
        self.assertTrue(verify_literature(self.out)["needs_review"])

    def test_pdf_creation_date_is_not_used_as_publication_year(self):
        metadata = types.SimpleNamespace(title="Synthetic metadata", author="Fixture Author",
                                         creation_date=datetime(2026, 1, 1, tzinfo=timezone.utc))
        fake = types.SimpleNamespace(PdfReader=lambda _: types.SimpleNamespace(metadata=metadata))
        with patch.dict(sys.modules, {"pypdf": fake}):
            self.assertIsNone(extract_pdf_metadata(self.root / "paper.pdf")["year"])

    def test_native_idea_intake_sees_the_entire_incremental_library(self):
        script = Path(__file__).resolve().parents[2] / "light-idea/scripts/idea_bridge.py"
        if not script.is_file():
            self.skipTest("Optional sibling source not installed")
        add_pdf(self.root / "paper.pdf", self.out, title="Synthetic report two")
        target = self.root / "Idea/IDEA-test"
        process = subprocess.run([sys.executable, "-X", "utf8", "-B", str(script), "ingest", "--literature", str(self.out), "--out", str(target)],
                                 capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        context = read_json(target / "context.json")
        self.assertEqual(len(context["papers"]), 2)


if __name__ == "__main__":
    unittest.main()
