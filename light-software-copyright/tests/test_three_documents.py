"""Behavior of the three-document delivery, not reference business content."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
import zipfile

from test_pipeline import CaseFixture, HAS_RENDER, cc, complete_facts, renderer

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@unittest.skipUnless(HAS_RENDER, "Optional rendering libraries unavailable")
class ThreeDocumentTest(CaseFixture):
    def setup_documents(self, lines=3):
        self.prepare(lines)
        facts = complete_facts(self.case)
        facts["delivery_profile"] = "three-documents"
        facts["features"][0]["function_heading"] = "合计功能"
        # These three documents do not invent administrative facts.
        facts["owners"] = []
        facts["owner_type"] = None
        facts["reviews"]["facts_confirmed"] = False
        cc.write_json(self.case / "case.json", facts)
        functions = {"document_type": "功能说明", "sections": [{
            "heading": "合计功能", "level": 1, "blocks": [
                {"type": "paragraph", "text": "显示真实数值序列的合计结果。此为独立功能说明的合成测试内容。"},
                {"type": "steps", "items": ["准备已校验的数值。", "执行程序并读取合计结果。"]},
            ]}]}
        cc.write_json(self.case / "functions.json", functions)
        cc.extract_case(self.case)

    def xml(self, path, part="word/document.xml"):
        with zipfile.ZipFile(path) as z:
            return ET.fromstring(z.read(part))

    def test_new_case_defaults_to_three_documents_without_private_facts(self):
        facts = cc.read_json(self.case / "case.json")
        self.assertEqual(facts["delivery_profile"], "three-documents")
        self.assertIsNone(facts["software_name"])
        self.assertEqual(facts["owners"], [])

    def test_default_cli_creates_exactly_three_distinct_docx(self):
        self.setup_documents()
        result = subprocess.run([sys.executable, "-B", str(Path(renderer.__file__)),
                                 "--case", str(self.case)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = [Path(p) for p in json.loads(result.stdout)["paths"]]
        title = cc.title_for(cc.read_json(self.case / "case.json"))
        self.assertEqual({p.name for p in paths}, {title+"_"+s+".docx" for s in ("功能说明","软件代码","软件说明书")})
        self.assertEqual(len(list((self.case / "草稿").iterdir())), 3)
        from docx import Document
        ftext = "\n".join(p.text for p in Document(paths[0]).paragraphs)
        mtext = "\n".join(p.text for p in Document(paths[2]).paragraphs)
        self.assertIn("独立功能说明", ftext)
        self.assertNotIn("独立功能说明", mtext)
        self.assertEqual(cc.audit_case(self.case)["errors"], [])
        self.assertFalse(cc.audit_case(self.case)["portal_ready"])

    def test_native_styles_list_cover_and_page_field(self):
        self.setup_documents(51)
        functions, code, manual = renderer.render(self.case, "bundle", ["docx"])
        fx = self.xml(functions)
        self.assertEqual(len(fx.findall(".//w:numPr", NS)), 2)
        styles = self.xml(functions, "word/styles.xml")
        for style_id in ("Title", "Heading1", "Heading2", "Heading3"):
            h = styles.find(f".//w:style[@w:styleId='{style_id}']/w:rPr", NS)
            self.assertEqual(h.find("w:color", NS).get("{"+NS["w"]+"}val"), "000000")
        sect = fx.find(".//w:sectPr", NS)
        self.assertAlmostEqual(int(sect.find("w:pgMar",NS).get("{"+NS["w"]+"}left")) / 1440 * 25.4, 25, delta=.05)
        mx = self.xml(manual)
        self.assertEqual(len(mx.findall(".//w:pageBreakBefore", NS)), 1)
        cx = self.xml(code)
        self.assertEqual(len(cx.findall(".//w:body/w:p", NS)), 51)
        self.assertEqual(len(cx.findall(".//w:pageBreakBefore", NS)), 1)
        header = self.xml(code, "word/header1.xml")
        self.assertEqual(header.find(".//w:fldSimple", NS).get("{"+NS["w"]+"}instr"), "PAGE")
        from docx import Document
        expected = [r["text"] for p in cc.verify_pages(self.case)["pages"] for r in p["lines"]]
        self.assertEqual([p.text for p in Document(code).paragraphs], expected)

    def test_functions_change_leaves_code_and_manual_current(self):
        self.setup_documents()
        renderer.render(self.case, "bundle", ["docx"])
        doc = cc.read_json(self.case / "functions.json")
        doc["sections"][0]["blocks"][0]["text"] += " 新的功能表述。"
        cc.write_json(self.case / "functions.json", doc)
        self.assertTrue(cc.audit_case(self.case, ["functions"])["errors"])
        self.assertEqual(cc.audit_case(self.case, ["code"])["errors"], [])
        self.assertEqual(cc.audit_case(self.case, ["manual"])["errors"], [])

    def test_source_changes_invalidate_document_evidence_without_optional_hash(self):
        self.setup_documents()
        renderer.render(self.case, "bundle", ["docx"])
        self.source(text="changed = 7\n")
        for kind in ("manual", "functions"):
            self.assertTrue(any("Stale project evidence" in e for e in cc.audit_case(self.case, [kind])["errors"]))

    def test_bad_last_document_does_not_publish_half_bundle(self):
        self.setup_documents()
        doc = cc.read_json(self.case / "manual.json")
        doc["sections"][0]["blocks"].append({"type":"image","path":"missing.png","caption":"图件","provenance":"不存在的测试图"})
        cc.write_json(self.case / "manual.json", doc)
        with self.assertRaises((OSError, cc.CaseError)):
            renderer.render(self.case, "bundle", ["docx"])
        self.assertFalse((self.case / "deliverables.json").exists())
        self.assertFalse((self.case / "草稿").exists())

    def test_bundle_release_has_only_three_docx_and_does_not_overwrite(self):
        self.setup_documents()
        renderer.render(self.case, "bundle", ["docx"])
        paths = renderer.release_bundle(self.case)
        self.assertEqual({p.suffix for p in paths}, {".docx"})
        self.assertEqual(len(list(paths[0].parent.iterdir())), 3)
        original = {p:p.read_bytes() for p in paths}
        with self.assertRaises(cc.CaseError):
            renderer.release_bundle(self.case)
        self.assertEqual(original, {p:p.read_bytes() for p in paths})
        self.assertEqual(cc.audit_case(self.case)["errors"], [])
        manifest = cc.read_json(self.case / "deliverables.json")
        released = [a for a in manifest["artifacts"] if a.get("release")]
        self.assertTrue(all("project_inputs" in a for a in released))

    def test_single_release_keeps_source_binding(self):
        self.setup_documents()
        renderer.render(self.case, "manual", ["docx"])
        paths = renderer.release(self.case, "manual")
        self.source(text="modified = 9\n")
        report = cc.audit_case(self.case, ["manual"])
        self.assertTrue(any(str(paths[0].relative_to(self.case)).replace("\\","/") in e and "Stale project evidence" in e for e in report["errors"]))

    def test_existing_draft_user_edits_are_preserved(self):
        self.setup_documents()
        paths = renderer.render(self.case, "bundle", ["docx"])
        edited = paths[0].read_bytes() + b"user edit"
        paths[0].write_bytes(edited)
        with self.assertRaises(cc.CaseError):
            renderer.release_bundle(self.case)
        renderer.render(self.case, "functions", ["docx"])
        self.assertIn(edited, [p.read_bytes() for p in (self.case / "历史资料").iterdir()])

    def test_each_document_needs_its_own_feature_anchor(self):
        self.setup_documents()
        renderer.render(self.case, "bundle", ["docx"])
        f = cc.read_json(self.case / "case.json")
        f["features"][0]["function_heading"] = "并不存在的功能"
        cc.write_json(self.case / "case.json", f)
        self.assertTrue(any("Feature missing from functions" in e for e in cc.audit_case(self.case, ["functions"])["errors"]))

    def test_invalid_steps_are_not_silently_rendered_as_character_list(self):
        self.setup_documents()
        doc = cc.read_json(self.case / "functions.json")
        doc["sections"][0]["blocks"] = [{"type":"steps","items":"错误的字符串"}]
        cc.write_json(self.case / "functions.json", doc)
        with self.assertRaises(cc.CaseError):
            renderer.render(self.case, "functions", ["docx"])

    def test_layout_changes_need_explicit_review(self):
        self.setup_documents()
        renderer.render(self.case, "bundle", ["docx"])
        profile = cc.read_json(self.case / "layout-profile.json")
        profile["body"]["size_pt"] = 40
        cc.write_json(self.case / "layout-profile.json", profile)
        with self.assertRaises(cc.CaseError):
            renderer.render(self.case, "bundle", ["docx"])

    def test_docx_short_code_works_without_optional_pdf_library(self):
        self.setup_documents()
        with patch.object(renderer, "load_pdf_font", side_effect=ImportError("No PDF library")):
            paths = renderer.render(self.case, "bundle", ["docx"])
        self.assertEqual(len(paths), 3)
        self.assertEqual(cc.audit_case(self.case)["errors"], [])

    def test_unmeasured_wide_cjk_line_is_rejected(self):
        self.setup_documents()
        self.source(text="# " + "测" * 100 + "\n")
        cc.scan_case(self.case)
        inventory = cc.read_json(self.case/"inventory.json")
        selection = cc.read_json(self.case/"selection.json")
        selection["snapshot_sha256"] = inventory["snapshot_sha256"]
        selection["files"] = [{"path":f["path"],"sha256":f["sha256"]} for f in inventory["files"]]
        cc.write_json(self.case/"selection.json",selection)
        from test_pipeline import review_selection
        review_selection(self.case)
        cc.extract_case(self.case)
        with patch.object(renderer, "load_pdf_font", side_effect=ImportError("No PDF library")):
            with self.assertRaises(cc.CaseError):
                renderer.render(self.case, "code", ["docx"])

    def test_reference_docx_long_line_is_not_silently_clipped(self):
        self.setup_documents()
        self.source(text='value = "' + "x"*800 + '"\n')
        cc.scan_case(self.case)
        inventory = cc.read_json(self.case/"inventory.json")
        selection = cc.read_json(self.case/"selection.json")
        selection["snapshot_sha256"] = inventory["snapshot_sha256"]
        selection["files"] = [{"path":f["path"],"sha256":f["sha256"]} for f in inventory["files"]]
        cc.write_json(self.case/"selection.json",selection)
        from test_pipeline import review_selection
        review_selection(self.case)
        cc.extract_case(self.case)
        with self.assertRaises(cc.CaseError):
            renderer.render(self.case, "code", ["docx"])
        self.assertFalse((self.case/"deliverables.json").exists())


if __name__ == "__main__":
    unittest.main()
