"""Synthetic fixtures only: tests never use real applicant facts or credentials."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import copyright_case as cc
import render_materials as renderer


def review_selection(case, include=None):
    selection = cc.read_json(case / "selection.json")
    selection.update(scope_reviewed=True, scope_note="Synthetic fixture: complete program reviewed", skipped_review="Synthetic fixture: excluded directories are not program scope")
    for item in selection["files"]:
        item["decision"] = "include" if include is None or item["path"] in include else "exclude"
        item["reason"] = "Synthetic fixture program" if item["decision"] == "include" else "Not part of this fixture program"
    cc.write_json(case / "selection.json", selection)


def complete_facts(case):
    facts = cc.read_json(case / "case.json")
    facts.update(delivery_profile="legacy", software_name="合成测试数据处理软件", version="V0.7", owners=["合成测试主体（非真实申请人）"], owner_type="测试主体",
                 development_mode="独立开发", rights_acquisition="原始取得", rights_scope="全部权利",
                 completed_on="2024-01-01", publication_status="未发表", languages=["Python"],
                 purpose="用于测试材料工具的读入与统计流程。", industry="测试", main_functions="读取数值并计算合计，将结果输出到文件。", technical_features="使用逐行读入和明确的数值校验。")
    facts["environments"] = {k: "合成测试环境；不代表真实申请事实" for k in facts["environments"]}
    facts["reviews"] = {"facts_confirmed": True, "confirmation_basis": "Synthetic test fixture, no real applicant",
                         "rights_basis": "Fixture authored for this test", "third_party_review": "No third-party implementation in fixture",
                         "source_ending_review": "Fixture ends at its final statement", "visual_review": "Synthetic fixture automated checks; real cases still require visual review"}
    facts["features"] = [{"id": "F01", "name": "计算合计", "status": "implemented", "evidence": [{"path": "main.py", "lines": [1, 1]}], "manual_heading": "计算合计"}]
    cc.write_json(case / "case.json", facts)
    manual = {"document_type": "设计说明书", "sections": [{"heading": "计算合计", "level": 1, "blocks": [
        {"type": "paragraph", "text": "程序读取已校验的数值序列，依次累加后返回合计。此处为材料工具的合成测试样例。"},
        {"type": "table", "headers": ["输入", "输出"], "rows": [["数值序列", "合计数值"]]},
        {"type": "code", "text": "python main.py"},
    ]}]}
    cc.write_json(case / "manual.json", manual)
    return facts


class CaseFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="light-copyright-test-")
        self.base = Path(self.tmp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.case = self.base / "materials"
        cc.init_case(self.project, self.case)

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, name="main.py", text="result = sum([1, 2, 3])\n"):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def prepare(self, lines=1):
        self.source(text="\n".join(f"value_{i} = {i}" for i in range(lines)) + "\n")
        cc.scan_case(self.case)
        review_selection(self.case)


class CaseTest(CaseFixture):
    def test_init_preserves_existing_facts(self):
        facts = cc.read_json(self.case / "case.json")
        facts["software_name"] = "保留用户编辑"
        cc.write_json(self.case / "case.json", facts)
        cc.init_case(self.project, self.case)
        self.assertEqual(cc.read_json(self.case / "case.json")["software_name"], "保留用户编辑")

    def test_empty_project_is_not_success(self):
        cc.scan_case(self.case)
        review_selection(self.case)
        with self.assertRaises(cc.CaseError):
            cc.extract_case(self.case)

    def test_page_boundaries_and_no_duplicate_source(self):
        for count in (1, 49, 50, 51, 2950, 2951, 3000, 3001, 3501):
            with self.subTest(count=count):
                self.source(text="\n".join(f"value_{i} = {i}" for i in range(count)) + "\n")
                cc.scan_case(self.case)
                selection = cc.read_json(self.case / "selection.json")
                inv = cc.read_json(self.case / "inventory.json")
                selection["snapshot_sha256"] = inv["snapshot_sha256"]
                selection["files"] = [{"path": f["path"], "sha256": f["sha256"]} for f in inv["files"]]
                cc.write_json(self.case / "selection.json", selection)
                review_selection(self.case)
                cc.extract_case(self.case)
                data = cc.verify_pages(self.case)
                expected_full = (count + 49) // 50
                self.assertEqual(data["complete_pages"], expected_full)
                self.assertEqual(data["submitted_pages"], min(60, expected_full))
                locations = [(r["path"], r["line"]) for p in data["pages"] for r in p["lines"]]
                self.assertEqual(len(locations), len(set(locations)))
                self.assertEqual(locations[0][1], 1)
                self.assertEqual(locations[-1][1], count)
                for p in data["pages"][:-1]:
                    self.assertEqual(len(p["lines"]), 50)
                if expected_full > 60:
                    self.assertEqual(data["pages"][30]["source_page"], expected_full - 29)

    def test_whitespace_comments_and_original_lines_are_preserved(self):
        self.source(text='# Copyright: upstream name retained\n\ndef run():\n    url = "http://example.invalid"\n    return url\n')
        cc.scan_case(self.case)
        review_selection(self.case)
        cc.extract_case(self.case)
        page = cc.read_json(self.case / "source-pages.json")["pages"][0]
        self.assertEqual([r["line"] for r in page["lines"]], [1, 3, 4, 5])
        self.assertEqual(page["lines"][2]["text"], '    url = "http://example.invalid"')
        self.assertIn("Copyright", page["lines"][0]["text"])

    def test_notebook_code_cells_only(self):
        notebook = {"cells": [{"cell_type": "markdown", "source": ["Not code"]},
                              {"cell_type": "code", "source": ["x = 1\n", "\n", "y = x + 2\n"], "outputs": [{"text": "not program"}]},
                              {"cell_type": "code", "source": "print(y)\n"}]}
        cc.write_json(self.project / "analysis.ipynb", notebook)
        cc.scan_case(self.case)
        review_selection(self.case)
        cc.extract_case(self.case)
        data = cc.read_json(self.case / "source-pages.json")
        self.assertEqual(data["raw_source_lines"], 4)
        self.assertEqual(data["nonblank_source_lines"], 3)
        self.assertEqual([(r["cell_index"], r["line"]) for r in data["pages"][0]["lines"]], [(2, 1), (2, 3), (3, 1)])

    def test_unknown_source_and_chinese_encoding_are_not_lost(self):
        (self.project / "process.custom").write_bytes('处理结果 = 1\n'.encode("gb18030"))
        cc.scan_case(self.case)
        inv = cc.read_json(self.case / "inventory.json")
        self.assertEqual(inv["files"][0]["category"], "review")
        review_selection(self.case)
        cc.extract_case(self.case)
        self.assertIn("处理结果", cc.read_json(self.case / "source-pages.json")["pages"][0]["lines"][0]["text"])

    def test_output_directory_inside_project_is_excluded(self):
        inner = self.project / "custom-materials"
        cc.init_case(self.project, inner)
        self.source()
        cc.scan_case(inner)
        inv = cc.read_json(inner / "inventory.json")
        self.assertEqual([f["path"] for f in inv["files"]], ["main.py"])

    def test_new_file_invalidates_snapshot(self):
        self.prepare()
        cc.extract_case(self.case)
        self.source("new.py", "new_logic = 2\n")
        with self.assertRaises(cc.CaseError):
            cc.verify_pages(self.case)

    def test_changed_file_invalidates_snapshot(self):
        self.prepare()
        self.source(text="changed = 2\n")
        with self.assertRaises(cc.CaseError):
            cc.extract_case(self.case)

    def test_missing_decision_blocks_incomplete_scope(self):
        self.prepare()
        data = cc.read_json(self.case / "selection.json")
        data["files"] = []
        cc.write_json(self.case / "selection.json", data)
        with self.assertRaises(cc.CaseError):
            cc.extract_case(self.case)

    def test_source_page_tampering_is_detected(self):
        self.prepare()
        cc.extract_case(self.case)
        data = cc.read_json(self.case / "source-pages.json")
        data["pages"][0]["lines"][0]["text"] = "fabricated = 1"
        cc.write_json(self.case / "source-pages.json", data)
        with self.assertRaises(cc.CaseError):
            cc.verify_pages(self.case)

    def test_secrets_fail_without_export_or_value_in_report(self):
        fake = "unit_test_fake_secret_123456"
        self.source(text=f'api_key = "{fake}"\n')
        cc.scan_case(self.case)
        review_selection(self.case)
        with self.assertRaises(cc.CaseError) as error:
            cc.extract_case(self.case)
        self.assertNotIn(fake, str(error.exception))
        self.assertNotIn(fake, (self.case / "secret-findings.json").read_text(encoding="utf-8"))
        self.assertFalse((self.case / "source-pages.json").exists())

    def test_allowlist_is_bound_to_exact_location_and_reason(self):
        self.source(text='password = "fixture_not_a_real_password"\n')
        cc.scan_case(self.case)
        review_selection(self.case)
        data = cc.read_json(self.case / "selection.json")
        data["secret_allowlist"] = [{"path": "main.py", "line": 1, "cell_index": None, "rule": "credential_literal", "reason": "Explicit synthetic fixture value"}]
        cc.write_json(self.case / "selection.json", data)
        cc.extract_case(self.case)
        self.assertEqual(cc.verify_pages(self.case)["submitted_pages"], 1)

    def test_path_escape_is_rejected(self):
        for value in ("../outside.py", str(self.project / "main.py")):
            with self.subTest(value=value), self.assertRaises(cc.CaseError):
                cc.contained(self.project, value)

    def test_symlink_to_outside_is_not_followed(self):
        outside = self.base / "outside.py"
        outside.write_text("outside = 9", encoding="utf-8")
        try:
            (self.project / "link.py").symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable in this Windows environment")
        cc.scan_case(self.case)
        self.assertFalse(cc.read_json(self.case / "inventory.json")["files"])
        with self.assertRaises(cc.CaseError):
            cc.contained(self.project, "link.py")


HAS_RENDER = all(importlib.util.find_spec(m) for m in ("reportlab", "docx", "pypdf", "PIL"))


@unittest.skipUnless(HAS_RENDER, "Optional document libraries not installed")
class RenderTest(CaseFixture):
    def setUp(self):
        super().setUp()
        try:
            self.font, self.font_path = renderer.load_pdf_font()
        except cc.CaseError:
            self.skipTest("No supported local Chinese font; core tests still run")

    def ready(self, count=3):
        self.prepare(count)
        complete_facts(self.case)
        cc.extract_case(self.case)
        for kind in ("application", "code", "manual"):
            renderer.render(self.case, kind, ["docx", "pdf"])

    def test_real_docx_pdf_and_worksheet_end_to_end(self):
        self.ready()
        report = cc.audit_case(self.case)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["status"], "local_review_ready")
        self.assertFalse(report["portal_ready"])
        self.assertTrue(report["warnings"])
        self.assertEqual(len(renderer.release(self.case, "code")), 2)
        self.assertEqual(cc.audit_case(self.case)["errors"], [])

    def test_front_and_back_render_has_exact_60_pdf_pages(self):
        self.prepare(3501)
        complete_facts(self.case)
        cc.extract_case(self.case)
        paths = renderer.render(self.case, "code", ["docx", "pdf"])
        from pypdf import PdfReader
        pdf = PdfReader(next(p for p in paths if p.suffix == ".pdf"))
        self.assertEqual(len(pdf.pages), 60)
        self.assertIn("value_0", pdf.pages[0].extract_text())
        self.assertIn("value_3500", pdf.pages[-1].extract_text())
        self.assertNotIn("value_1500 =", "\n".join(p.extract_text() for p in pdf.pages))

    def test_long_lines_fail_instead_of_truncating(self):
        self.source(text='payload = "' + "x" * 800 + '"\n')
        cc.scan_case(self.case)
        review_selection(self.case)
        complete_facts(self.case)
        cc.extract_case(self.case)
        with self.assertRaises(cc.CaseError):
            renderer.render(self.case, "code", ["pdf"])
        self.assertFalse((self.case / "deliverables.json").exists())

    def test_fact_change_invalidates_existing_outputs(self):
        self.ready()
        facts = cc.read_json(self.case / "case.json")
        facts["version"] = "V0.8"
        cc.write_json(self.case / "case.json", facts)
        report = cc.audit_case(self.case)
        self.assertTrue(report["errors"])
        with self.assertRaises(cc.CaseError):
            renderer.release(self.case, "manual")

    def test_manual_only_request_does_not_require_full_registration(self):
        self.source()
        complete_facts(self.case)
        facts = cc.read_json(self.case / "case.json")
        for key in ("owners", "owner_type", "completed_on", "development_mode", "rights_acquisition", "rights_scope", "publication_status"):
            facts[key] = None
        facts["reviews"]["facts_confirmed"] = False
        cc.write_json(self.case / "case.json", facts)
        renderer.render(self.case, "manual", ["pdf"])
        self.assertEqual(cc.audit_case(self.case, ["manual"])["errors"], [])
        self.assertEqual(len(renderer.release(self.case, "manual")), 1)

    def test_new_version_can_release_while_old_release_is_archived(self):
        self.ready()
        old_paths = renderer.release(self.case, "code")
        facts = cc.read_json(self.case / "case.json")
        facts["version"] = "V0.8"
        cc.write_json(self.case / "case.json", facts)
        cc.extract_case(self.case)
        renderer.render(self.case, "code", ["docx", "pdf"])
        new_paths = renderer.release(self.case, "code")
        self.assertTrue(all(p.is_file() for p in new_paths))
        self.assertTrue(all(not p.exists() for p in old_paths))
        self.assertTrue(any("V0.7" in p.name for p in (self.case / "历史资料").iterdir()))

    def test_unsupported_glyph_is_reported_instead_of_replaced(self):
        with self.assertRaises(cc.CaseError):
            renderer.check_glyphs("not covered: \U0010ffff", self.font)

    def test_user_edit_is_preserved_before_regeneration(self):
        self.ready()
        manifest = cc.read_json(self.case / "deliverables.json")
        artifact = next(a for a in manifest["artifacts"] if a["kind"] == "application")
        path = self.case / artifact["path"]
        modified = path.read_bytes() + "用户编辑\n".encode("utf-8")
        path.write_bytes(modified)
        self.assertTrue(cc.audit_case(self.case)["errors"])
        renderer.render(self.case, "application", [])
        self.assertIn(modified, [p.read_bytes() for p in (self.case / "历史资料").iterdir()])

    def test_placeholder_blocks_release_but_not_drafts(self):
        self.ready()
        manual = cc.read_json(self.case / "manual.json")
        manual["sections"][0]["blocks"][0]["text"] = "【待补图：命令行输出】"
        cc.write_json(self.case / "manual.json", manual)
        renderer.render(self.case, "manual", ["pdf"])
        self.assertTrue(cc.audit_case(self.case)["errors"])
        with self.assertRaises(cc.CaseError):
            renderer.release(self.case, "manual")

    def test_image_input_hash_and_real_file_are_checked(self):
        self.prepare()
        complete_facts(self.case)
        cc.extract_case(self.case)
        from PIL import Image
        image_path = self.case / "screenshots" / "synthetic.png"
        image_path.parent.mkdir()
        Image.new("RGB", (300, 150), "white").save(image_path)
        manual = cc.read_json(self.case / "manual.json")
        manual["sections"][0]["blocks"].append({"type": "image", "path": "screenshots/synthetic.png", "caption": "合成测试图（不是软件运行截图）", "provenance": "Test-created image only"})
        cc.write_json(self.case / "manual.json", manual)
        for kind in ("application", "code", "manual"):
            renderer.render(self.case, kind, ["docx", "pdf"])
        self.assertEqual(cc.audit_case(self.case)["errors"], [])
        Image.new("RGB", (300, 150), "black").save(image_path)
        self.assertTrue(cc.audit_case(self.case)["errors"])


if __name__ == "__main__":
    unittest.main()
