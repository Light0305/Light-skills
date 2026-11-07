from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pypdfium2 as pdfium

from litsearch.pdf_assets import render_pdf_assets


class PdfAssetsTest(unittest.TestCase):
    def test_pdfium_renderer_is_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "one-page.pdf"
            doc = pdfium.PdfDocument.new()
            page = doc.new_page(width=200, height=200)
            page.close()
            doc.save(str(pdf_path))
            doc.close()

            article = Path(tmp) / "article"
            result = render_pdf_assets(pdf_path, article, dpi=72)

            self.assertEqual(result["status"], "ok")
            self.assertTrue(result.get("renderer", "").startswith("pypdfium2"))
            self.assertTrue((article / "pages" / "page_001.png").exists())
            manifest = json.loads((article / "pdf_assets.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["renderer"], result["renderer"])

    def test_corrupt_pdf_writes_unavailable_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "broken.pdf"
            pdf_path.write_bytes(b"not a pdf")

            article = Path(tmp) / "article"
            result = render_pdf_assets(pdf_path, article, dpi=72)

            self.assertEqual(result["status"], "unavailable")
            self.assertIn("pypdfium2", result["reason"])
            self.assertTrue((article / "pdf_assets.json").exists())

    def test_missing_renderers_reports_both(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "any.pdf"
            pdf_path.write_bytes(b"x")
            article = Path(tmp) / "article"
            with patch(
                "litsearch.pdf_assets._render_with_pdfium",
                side_effect=ImportError("no pdfium"),
            ), patch(
                "litsearch.pdf_assets._render_with_pymupdf",
                side_effect=ImportError("no pymupdf"),
            ):
                result = render_pdf_assets(pdf_path, article, dpi=72)

            self.assertEqual(result["status"], "unavailable")
            self.assertIn("not installed", result["reason"])
            self.assertTrue((article / "pdf_assets.json").exists())


if __name__ == "__main__":
    unittest.main()
