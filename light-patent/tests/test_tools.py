"""Observable support, reference, export and non-overwrite invariants."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_case import audit_case, claim_text, read_case, valid_omml
from export_case import export_case
from init_case import init_case

FIXTURE = ROOT / "tests" / "fixtures"


class SupportChecks(unittest.TestCase):
    def setUp(self):
        self.data = read_case(FIXTURE / "case.json")

    def codes(self, profile="application"):
        return {x["code"] for x in audit_case(self.data, FIXTURE, profile) if x["severity"] == "ERROR"}

    def test_supported_fixture_and_honest_search_warning(self):
        findings = audit_case(self.data, FIXTURE, "application")
        self.assertFalse(self.codes())
        self.assertIn("SEARCH_LIMIT", {x["code"] for x in findings})

    def test_unsupported_dependent_limitation_is_blocked(self):
        self.data["features"][2]["support"] = "needs-confirmation"
        self.assertIn("UNSUPPORTED_CLAIM", self.codes())

    def test_missing_source_and_empty_locator_are_blocked(self):
        ref = self.data["features"][0]["source_refs"][0]
        ref.update(source_id="missing", locator="")
        self.assertTrue({"SOURCE_REF", "LOCATOR"} <= self.codes())

    def test_unread_material_cannot_support_claim(self):
        self.data["sources"][0]["reviewed"] = False
        self.assertIn("UNREAD_SUPPORT", self.codes())

    def test_source_fingerprint_mismatch_requires_review(self):
        self.data["sources"][0]["sha256"] = "0" * 64
        self.assertIn("SOURCE_CHANGED", self.codes())

    def test_heading_is_not_substantive_specification_support(self):
        self.data["claims"][0]["limitations"][0]["spec_ids"] = ["H001"]
        self.assertIn("SPEC_SUPPORT", self.codes())

    def test_entailed_requires_necessity_rationale(self):
        self.data["features"][0]["support"] = "entailed"
        self.assertIn("ENTAILMENT", self.codes())

    def test_filed_case_rejects_new_material_as_original_basis(self):
        self.data["stage"] = "filed"
        self.assertIn("MISSING_SUPPORT", self.codes())
        for f in self.data["features"]:
            f["original_refs"] = deepcopy(f["source_refs"])
        self.assertIn("ORIGINAL_BASIS", self.codes())
        self.data["sources"][0]["role"] = "original-application"
        self.assertFalse(self.codes())

    def test_dependency_graph_no_forward_reference(self):
        self.data["claims"][1]["depends_on"] = [3]
        self.assertIn("DEPENDENCY", self.codes())

    def test_multiple_dependency_and_single_dependency_distinction(self):
        second = self.data["claims"][1]
        third = deepcopy(second)
        third.update(number=3, depends_on=[1, 2])
        fourth = deepcopy(second)
        fourth.update(number=4, depends_on=[3])
        self.data["claims"] += [third, fourth]
        self.assertFalse(self.codes(), "单项引用多项从属应允许")
        fourth["depends_on"] = [1, 3]
        self.assertIn("MULTIPLE_BASE", self.codes())
        fourth["depends_on"] = [1, 2]
        fourth["dependency_mode"] = "all"
        self.assertIn("MULTIPLE_MODE", self.codes())

    def test_utility_model_rejects_method_and_missing_drawings(self):
        self.data["patent_type"] = "utility-model"
        self.assertTrue({"UTILITY_SUBJECT", "UTILITY_FIGURES"} <= self.codes())

    def test_claim_and_spec_placeholder_blocked_but_disclosure_can_be_incomplete(self):
        self.data["claims"][0]["limitations"][0]["text"] = "[待确认]"
        self.assertIn("PLACEHOLDER", self.codes())
        self.data["documents"]["disclosure"][1]["text"] += "；待补充测试条件。"
        self.assertFalse(self.codes("disclosure"))

    def test_missing_drawing_and_bad_abstract_selection(self):
        self.data["figures"] = [{"id":"G001", "title":"图1 流程图", "path":"absent.png"}]
        self.assertTrue({"FIGURE_FILE", "ABSTRACT_FIGURE", "FIGURE_UNUSED"} <= self.codes())

    def test_empty_documents_and_bad_shape_return_findings(self):
        self.data["documents"]["specification"] = []
        self.assertIn("EMPTY_DOCUMENT", self.codes())
        self.assertEqual(audit_case([], FIXTURE)[0]["code"], "TYPE")
        self.data["features"] = [5]
        self.assertIn("TYPE", self.codes())

    def test_malformed_json_field_types_are_reported_without_crashing(self):
        scenarios = [
            lambda d: d.update(stage=[], patent_type={}),
            lambda d: d["features"][0].update(support=[]),
            lambda d: d["claims"][0].update(category=[], kind=[]),
            lambda d: d["documents"].update(abstract=None),
            lambda d: d["documents"]["specification"][0].update(type=[]),
            lambda d: d.update(sources=None, features=None, claims=None),
        ]
        for mutate in scenarios:
            with self.subTest(mutation=mutate):
                data = read_case(FIXTURE / "case.json")
                mutate(data)
                self.assertTrue(any(f["severity"] == "ERROR" for f in audit_case(data, FIXTURE)))

    def test_explicit_open_blocker_stops_formal_export(self):
        self.data["questions"] = [{"id":"Q1", "severity":"blocking", "text":"核心机制尚缺"}]
        self.assertIn("OPEN_BLOCKER", self.codes())
        self.assertFalse(self.codes("disclosure"))

    def test_omml_validation_rejects_non_math_and_entity_declarations(self):
        self.assertFalse(valid_omml("<root>not math</root>"))
        self.assertFalse(valid_omml('<!DOCTYPE foo [<!ENTITY a "x">]><foo>&a;</foo>'))

    def test_cli_exit_status_has_distinct_input_and_structural_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "case.json"
            path.write_text("{broken", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/audit_case.py"), str(path)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            path.write_text("{}", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/audit_case.py"), str(path)], capture_output=True)
            self.assertEqual(result.returncode, 2)


class ExportChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.case = self.base / "case.json"
        self.data = read_case(FIXTURE / "case.json")
        self.data["sources"][0]["path"] = str(FIXTURE / "inventor-note.txt")
        self.save()

    def save(self):
        self.case.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")

    def test_initialization_never_overwrites_material(self):
        dest = self.base / "new-case"
        init_case(dest, "测试案件")
        initial = (dest / "case.json").read_bytes()
        with self.assertRaises(ValueError):
            init_case(dest, "另一个案件")
        self.assertEqual(initial, (dest / "case.json").read_bytes())

    def test_markdown_package_has_separate_clean_files_and_support(self):
        out = export_case(self.case, self.base / "md", fmt="md")
        self.assertTrue((out / "02_权利要求书.md").is_file())
        self.assertTrue((out / "03_说明书.md").is_file())
        self.assertTrue((out / "支持表.md").is_file())
        self.assertNotIn("F001", (out / "02_权利要求书.md").read_text(encoding="utf-8"))
        self.assertIn(self.data["title"], (out / "03_说明书.md").read_text(encoding="utf-8"))
        manifest = read_case(out / "交付清单.json")
        self.assertEqual(manifest["visual_review"], "not-performed")
        self.assertTrue(manifest["files"])

    def test_output_directory_is_not_replaced(self):
        out = self.base / "delivered"
        out.mkdir()
        marker = out / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            export_case(self.case, out, fmt="md")
        self.assertEqual(marker.read_text(), "keep")

    def test_unsupported_claim_prevents_creating_package(self):
        self.data["features"][1]["support"] = "unsupported"
        self.save()
        out = self.base / "bad"
        with self.assertRaises(ValueError):
            export_case(self.case, out, fmt="md")
        self.assertFalse(out.exists())

    @unittest.skipUnless(importlib.util.find_spec("docx"), "optional python-docx not installed")
    def test_figures_are_copied_and_embedded_in_separate_sheets(self):
        def chunk(tag, content):
            return struct.pack("!I", len(content)) + tag + content + struct.pack("!I", zlib.crc32(tag + content))
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", 2, 2, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\xff\xff" * 2) * 2)) + chunk(b"IEND", b"")
        (self.base / "drawing.png").write_bytes(png)
        self.data["figures"] = [{"id":"G001", "title":"图1 测试图件", "path":"drawing.png"}]
        self.data["abstract_figure_id"] = "G001"
        self.data["documents"]["specification"].append({"id":"I001", "type":"image", "figure_id":"G001"})
        self.save()
        out = export_case(self.case, self.base / "drawings", fmt="both")
        self.assertEqual((out / "figures/figure-1.png").read_bytes(), png)
        for name in ("05_说明书附图.docx", "06_摘要附图.docx"):
            with zipfile.ZipFile(out / name) as archive:
                self.assertTrue(any(n.startswith("word/media/") for n in archive.namelist()))

    @unittest.skipUnless(importlib.util.find_spec("docx"), "optional python-docx not installed")
    def test_word_has_native_math_and_no_support_ids_in_formal_body(self):
        omml = '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:sSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:oMath>'
        self.assertTrue(valid_omml(omml))
        self.data["documents"]["specification"].append({"id":"E1", "type":"equation", "latex":"x^2", "omml":omml})
        self.save()
        out = export_case(self.case, self.base / "word", fmt="both")
        with zipfile.ZipFile(out / "03_说明书.docx") as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("m:sSup", xml)
        self.assertNotIn("F001", xml)
        with zipfile.ZipFile(out / "02_权利要求书.docx") as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("权利要求1", xml)

    @unittest.skipUnless(importlib.util.find_spec("docx"), "optional python-docx not installed")
    def test_latex_only_is_not_silently_delivered_as_editable_word_math(self):
        self.data["documents"]["specification"].append({"id":"E1", "type":"equation", "latex":"x^2"})
        self.save()
        with self.assertRaisesRegex(ValueError, "OMML"):
            export_case(self.case, self.base / "word", fmt="docx")
        self.assertFalse((self.base / "word").exists())
        self.assertTrue(export_case(self.case, self.base / "md", fmt="md").exists())


if __name__ == "__main__":
    unittest.main()
