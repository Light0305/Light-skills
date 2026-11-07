from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pypdfium2 as pdfium

from litsearch.cli import main
from litsearch.io import read_json, write_json, write_jsonl
from litsearch.literature import add_pdf, article_folder_name, build_literature
from litsearch.models import Paper, ScreeningRow
from litsearch.normalize import make_paper_id


def make_pdf(path: Path, pages: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument.new()
    try:
        for _ in range(pages):
            page = doc.new_page(width=100, height=100)
            page.close()
        doc.save(str(path))
    finally:
        doc.close()


class LiteratureTests(unittest.TestCase):
    def _run(self, root: Path, with_pdf: bool = True) -> tuple[Path, Paper]:
        run = root / "run"
        run.mkdir()
        paper = Paper(paper_id=make_paper_id(title="A study", year=2024),
                      title="A study", authors=["Alice Smith"], year=2024)
        write_jsonl(run / "papers.jsonl", [paper.to_dict()])
        write_jsonl(run / "screening.jsonl", [ScreeningRow(
            paper_id=paper.paper_id, decision="include", reason_code="IN_SCOPE",
        ).to_dict()])
        if with_pdf:
            make_pdf(run / "pdfs" / f"{paper.paper_id}.pdf")
        return run, paper

    def test_folder_name_sanitizes_and_deduplicates(self) -> None:
        p = Paper(paper_id="test", title="A/B: Test?", authors=["Alice Smith"], year=2024)
        name = article_folder_name(p, set())
        self.assertEqual(name, "2024_smith_A-B-Test")
        self.assertTrue(article_folder_name(p, {name}).endswith("_2"))

    def test_default_build_prepares_pages_and_pending_host_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, _ = self._run(root)
            result = build_literature(run, root / "Literature")
            entry = result["entries"][0]
            folder = root / "Literature" / entry["folder"]
            self.assertEqual(entry["parse_method"], "host_model")
            self.assertEqual(entry["parse_status"], "model_parse_required")
            self.assertEqual(entry["assets_status"], "ok")
            self.assertEqual(result["pages_estimated"], 2)
            self.assertEqual(len(list((folder / "pages").glob("*.png"))), 2)
            self.assertTrue((folder / "MODEL_PARSE.md").is_file())
            self.assertTrue((folder / "AGENT_TASKS.md").is_file())
            self.assertFalse((folder / "paper.md").exists())
            self.assertEqual(read_json(root / "Literature" / "manifest.json")["selected"], 1)

    def test_dry_run_does_not_write_or_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, _ = self._run(root)
            with patch("litsearch.literature.render_pdf_assets") as render, patch("litsearch.literature.fetch_pdfs") as fetch:
                result = build_literature(run, root / "Literature", dry_run=True, fetch_pdf=True)
            render.assert_not_called()
            fetch.assert_not_called()
            self.assertEqual(result["pages_estimated"], 2)
            self.assertFalse((root / "Literature").exists())

    def test_add_pdf_dry_run_leaves_output_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "paper.pdf")
            add_pdf(root / "paper.pdf", root / "Literature", dry_run=True)
            self.assertFalse((root / "Literature").exists())

    def test_add_pdf_records_provenance_in_meta_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "paper.pdf")
            result = add_pdf(root / "paper.pdf", root / "Literature", title="Local paper")
            meta = read_json(Path(result["folder"]) / "meta.json")
            self.assertEqual(meta["source"], "user_pdf")
            self.assertEqual(meta["original_pdf"], str((root / "paper.pdf").resolve()))
            self.assertEqual(read_json(root / "Literature" / "manifest.json")["entries"][0], meta)

    def test_repeated_import_preserves_host_work_and_other_index_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "paper.pdf")
            out = root / "Literature"
            first = add_pdf(root / "paper.pdf", out, title="First paper")
            folder = Path(first["folder"])
            (folder / "paper.md").write_text("Original transcription", encoding="utf-8")
            (folder / "note.md").write_text("My note", encoding="utf-8")
            add_pdf(root / "paper.pdf", out, title="Second paper")
            with patch("litsearch.literature.render_pdf_assets") as render:
                repeat = add_pdf(root / "paper.pdf", out, title="First paper")
            render.assert_not_called()
            self.assertEqual(repeat["folder"], first["folder"])
            self.assertEqual(repeat["parse_already_present"], 1)
            self.assertEqual((folder / "note.md").read_text(encoding="utf-8"), "My note")
            index = (out / "README.md").read_text(encoding="utf-8")
            self.assertIn("First paper", index)
            self.assertIn("Second paper", index)
            self.assertEqual(len(list(out.glob("*/meta.json"))), 2)

    def test_force_prepare_refreshes_assets_without_rewriting_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, _ = self._run(root)
            out = root / "Literature"
            result = build_literature(run, out)
            folder = out / result["entries"][0]["folder"]
            (folder / "paper.md").write_text("Keep this", encoding="utf-8")
            with patch("litsearch.literature.render_pdf_assets", return_value={"status": "ok"}) as render:
                build_literature(run, out, force_prepare=True)
            render.assert_called_once()
            self.assertEqual((folder / "paper.md").read_text(encoding="utf-8"), "Keep this")

    def test_missing_pdf_keeps_honest_status_and_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, _ = self._run(root, with_pdf=False)
            out = root / "Literature"
            result = build_literature(run, out)
            entry = result["entries"][0]
            folder = out / entry["folder"]
            self.assertEqual(entry["parse_status"], "pdf_missing")
            self.assertTrue((folder / "AGENT_TASKS.md").exists())
            self.assertFalse((folder / "MODEL_PARSE.md").exists())

    def test_renderer_failure_does_not_claim_transcription(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, _ = self._run(root)
            with patch("litsearch.literature.render_pdf_assets", return_value={"status": "unavailable", "reason": "test"}):
                result = build_literature(run, root / "Literature")
            self.assertEqual(result["entries"][0]["assets_status"], "unavailable")
            self.assertEqual(result["model_parse_required"], 1)

    def test_rebuild_preserves_annotations_and_reuses_local_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, paper = self._run(root)
            out = root / "Literature"
            result = build_literature(run, out)
            folder = out / result["entries"][0]["folder"]
            meta = read_json(folder / "meta.json")
            meta.update({"acquisition": [{"status": "user_supplied"}], "doc2x_status": "ok"})
            write_json(folder / "meta.json", meta)
            (run / "pdfs" / f"{paper.paper_id}.pdf").unlink()
            result = build_literature(run, out)
            self.assertEqual(result["pdf_present"], 1)
            self.assertTrue((folder / "paper.pdf").exists())
            self.assertEqual(result["entries"][0]["acquisition"], meta["acquisition"])
            self.assertNotIn("doc2x_status", result["entries"][0])

    def test_cli_add_runs_default_host_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "paper.pdf")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["literature", "add", "--pdf", str(root / "paper.pdf"), "--out", str(root / "Literature")])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["model_parse_required"], 1)

    def test_manifest_retains_all_papers_after_partial_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "paper.pdf")
            out = root / "Literature"
            add_pdf(root / "paper.pdf", out, title="Synthetic first report")
            add_pdf(root / "paper.pdf", out, title="Synthetic second report")
            manifest = read_json(out / "manifest.json")
            self.assertEqual(len(manifest["entries"]), 2)
            self.assertEqual(manifest["selected"], 1)
            self.assertEqual(manifest["library_total"], 2)

    def test_different_pdf_cannot_silently_replace_read_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "first.pdf", pages=1)
            make_pdf(root / "revised.pdf", pages=2)
            out = root / "Literature"
            first = add_pdf(root / "first.pdf", out, title="Synthetic versioned report", doi="10.9999/versioned")
            folder = Path(first["folder"])
            original = (folder / "paper.pdf").read_bytes()
            (folder / "note.md").write_text("Synthetic note based on the first PDF", encoding="utf-8")
            before = (out / "manifest.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "PDF.*differ|different PDF"):
                add_pdf(root / "revised.pdf", out, title="Synthetic versioned report", doi="10.9999/versioned")
            self.assertEqual((folder / "paper.pdf").read_bytes(), original)
            self.assertEqual((out / "manifest.json").read_bytes(), before)

    def test_pdf_identity_is_recorded_for_later_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "paper.pdf")
            result = add_pdf(root / "paper.pdf", root / "Literature", title="Synthetic source identity")
            self.assertRegex(result["entries"][0]["pdf_sha256"], r"^[0-9a-f]{64}$")

    def test_missing_old_pdf_does_not_allow_a_different_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pdf(root / "first.pdf", pages=1)
            make_pdf(root / "revised.pdf", pages=2)
            out = root / "Literature"
            first = add_pdf(root / "first.pdf", out, title="Synthetic lost source", doi="10.9999/lost")
            folder = Path(first["folder"])
            (folder / "paper.pdf").unlink()
            (folder / "note.md").write_text("Synthetic old-version note", encoding="utf-8")
            before = (out / "manifest.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "PDF.*differ"):
                add_pdf(root / "revised.pdf", out, title="Synthetic lost source", doi="10.9999/lost")
            self.assertFalse((folder / "paper.pdf").exists())
            self.assertEqual((out / "manifest.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
