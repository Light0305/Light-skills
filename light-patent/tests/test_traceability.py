"""Source roles and read-only delivery freshness checks."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_tools import FIXTURE, ROOT, audit_case, export_case, read_case
from export_case import verify_export


class SourceRoleTest(unittest.TestCase):
    def setUp(self):
        self.data = read_case(FIXTURE / "case.json")

    def errors(self):
        return {x["code"] for x in audit_case(self.data, FIXTURE) if x["severity"] == "ERROR"}

    def test_background_sources_cannot_support_formal_claims(self):
        for role in ("prior-art", "context"):
            self.data["sources"][0]["role"] = role
            self.assertIn("BACKGROUND_AS_DISCLOSURE", self.errors())

    def test_filed_support_uses_actual_original_document_part(self):
        self.data["stage"] = "filed"
        self.data["sources"][0].update(role="original-application", document_kind="specification")
        for feature in self.data["features"]:
            feature["original_refs"] = deepcopy(feature["source_refs"])
        self.assertFalse(self.errors())
        self.data["features"][0]["original_refs"][0]["document_part"] = "abstract"
        self.assertIn("ORIGINAL_PART", self.errors())
        for part in ("receipt","later-supplement"):
            self.data["features"][0]["original_refs"][0]["document_part"] = part
            self.assertIn("ORIGINAL_PART", self.errors())

    def test_legacy_original_part_is_unresolved_warning(self):
        self.data["stage"] = "filed"
        self.data["sources"][0]["role"] = "original-application"
        for feature in self.data["features"]:
            feature["original_refs"] = deepcopy(feature["source_refs"])
        self.assertFalse(self.errors())
        self.assertIn("ORIGINAL_PART_UNRESOLVED", {x["code"] for x in audit_case(self.data, FIXTURE)})

    def test_invalid_role_and_hash_have_findings_without_crashing(self):
        self.data["sources"][0].update(role=[], sha256="not-a-hash")
        self.assertTrue({"SOURCE_ROLE","SOURCE_HASH"} <= self.errors())


class DeliveryFreshnessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="light-patent-freshness-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "note.txt"
        self.source.write_bytes((FIXTURE / "inventor-note.txt").read_bytes())
        self.data = read_case(FIXTURE / "case.json")
        self.data["sources"][0]["path"] = "note.txt"
        self.case = self.base / "case.json"
        self.save()
        self.out = export_case(self.case, self.base / "delivery", fmt="md")

    def save(self):
        self.case.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")

    def test_current_delivery_is_verified_without_certifying_visual_review(self):
        r = verify_export(self.case, self.out)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["scope"], "recorded_case_sources_and_exports")
        self.assertEqual(r["visual_review"], "not-performed")

    def test_source_change_is_detected_even_without_case_declared_hash(self):
        self.source.write_text("Changed inventor material", encoding="utf-8")
        self.assertTrue(any("Recorded source changed" in e for e in verify_export(self.case, self.out)["errors"]))

    def test_missing_source_is_structured_mismatch(self):
        self.source.unlink()
        self.assertFalse(verify_export(self.case, self.out)["ok"])

    def test_case_change_is_detected(self):
        self.data["questions"].append({"question":"New fact needs review"})
        self.save()
        self.assertIn("Case record changed", verify_export(self.case, self.out)["errors"])

    def test_output_change_is_detected(self):
        p = self.out / "02_权利要求书.md"
        p.write_text(p.read_text(encoding="utf-8")+"Changed", encoding="utf-8")
        self.assertFalse(verify_export(self.case, self.out)["ok"])

    def test_legacy_manifest_scope_is_explicit(self):
        m = read_case(self.out / "交付清单.json")
        del m["source_inputs"]
        (self.out / "交付清单.json").write_text(json.dumps(m), encoding="utf-8")
        r = verify_export(self.case, self.out)
        self.assertTrue(r["ok"])
        self.assertEqual(r["scope"], "recorded_case_and_exports_only")

    def test_unsafe_manifest_paths_are_rejected(self):
        m = read_case(self.out / "交付清单.json")
        m["files"][0]["path"] = "../outside.md"
        (self.out / "交付清单.json").write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_export(self.case, self.out)

    def test_verify_cli_returns_mismatch_status(self):
        cmd = [sys.executable,"-B",str(ROOT/"scripts/export_case.py"),str(self.case),"--out",str(self.out),"--verify"]
        self.assertEqual(subprocess.run(cmd,capture_output=True).returncode, 0)
        self.source.write_text("Changed", encoding="utf-8")
        self.assertEqual(subprocess.run(cmd,capture_output=True).returncode, 2)

    def test_figure_source_and_export_are_bound(self):
        # Native source is tracked even when it is not copied into the delivery.
        from PIL import Image
        Image.new("RGB", (100,50), "white").save(self.base/"figure.png")
        (self.base/"figure.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        self.data["figures"] = [{"id":"G1","title":"图1 合成测试图","path":"figure.png","source_path":"figure.svg"}]
        self.data["abstract_figure_id"] = "G1"
        self.data["documents"]["specification"].append({"id":"I1","type":"image","figure_id":"G1"})
        self.save()
        out = export_case(self.case,self.base/"figure-delivery",fmt="md")
        self.assertTrue(verify_export(self.case,out)["ok"])
        (self.base/"figure.svg").write_text("Changed native drawing",encoding="utf-8")
        self.assertTrue(any("figure:G1:source_path" in e for e in verify_export(self.case,out)["errors"]))


if __name__ == "__main__":
    unittest.main()
