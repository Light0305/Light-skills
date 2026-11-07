"""Synthetic local cases; no real journals, research, network, or model evaluation."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "audit_selection", Path(__file__).resolve().parents[1] / "scripts" / "audit_selection.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def packet():
    def facet():
        return {"status": "verified", "basis": "Synthetic official evidence.", "source_ids": ["S1"]}
    return {
        "schema_version": "1.0", "as_of": "2026-11-02",
        "constraints": [{"id": "budget", "requirement": "Synthetic hard budget.", "hard": True, "origin": "user"}],
        "sources": [
            {"id": "S1", "kind": "official_journal", "locator": "https://example.invalid/journal", "accessed_on": "2026-11-02"},
            {"id": "S2", "kind": "primary_article", "locator": "https://example.invalid/article", "accessed_on": "2026-11-02"},
        ],
        "candidates": [{
            "id": "J1", "name": "Synthetic Journal A", "recommended": True,
            "checks": [{"constraint_id": "budget", "status": "pass", "basis": "Synthetic route fits.", "source_ids": ["S1"]}],
            "identity": facet(), "scope": facet(), "article_type": facet(),
            "fit": {"band": "strong", "rationale": "Synthetic topic and audience match.", "counterevidence": "Synthetic method gap remains."},
            "comparables": [{"title": "Synthetic example only", "year": 2025, "locator": "https://example.invalid/article", "status": "verified", "source_ids": ["S2"], "shared_axes": "Question and evidence form.", "important_difference": "Different validation scope."}],
        }],
    }


class AuditTests(unittest.TestCase):
    def test_supported_candidate_is_ready(self):
        result = MODULE.audit(packet())
        self.assertTrue(result["valid"])
        self.assertTrue(result["candidates"][0]["recommendation_ready"])

    def test_strong_fit_cannot_offset_failed_budget(self):
        value = packet(); value["candidates"][0]["checks"][0]["status"] = "fail"
        result = MODULE.audit(value)
        self.assertFalse(result["valid"])
        self.assertEqual(result["candidates"][0]["eligibility"], "excluded")

    def test_unknown_is_conditional_and_cannot_be_recommended(self):
        value = packet(); check = value["candidates"][0]["checks"][0]
        check.update(status="unknown", source_ids=[])
        result = MODULE.audit(value)
        self.assertFalse(result["valid"])
        self.assertEqual(result["candidates"][0]["eligibility"], "conditional")
        value["candidates"][0]["recommended"] = False
        self.assertTrue(MODULE.audit(value)["valid"])

    def test_missing_hard_check_is_not_pass(self):
        value = packet(); value["candidates"][0]["checks"] = []
        result = MODULE.audit(value)
        self.assertEqual(result["candidates"][0]["unknown_hard_constraints"], ["budget"])
        self.assertFalse(result["valid"])

    def test_soft_failure_does_not_exclude(self):
        value = packet(); value["constraints"][0]["hard"] = False
        value["candidates"][0]["checks"][0]["status"] = "fail"
        self.assertTrue(MODULE.audit(value)["valid"])

    def test_working_assumption_cannot_be_hardened(self):
        value = packet(); value["constraints"][0]["origin"] = "assumption"
        with self.assertRaisesRegex(MODULE.PacketError, "assumption cannot"):
            MODULE.audit(value)
        value["constraints"][0]["hard"] = False
        self.assertTrue(MODULE.audit(value)["valid"])

    def test_mismatch_excludes_despite_all_hard_pass(self):
        value = packet(); value["candidates"][0]["fit"]["band"] = "mismatch"
        result = MODULE.audit(value)
        self.assertEqual(result["candidates"][0]["eligibility"], "excluded")
        self.assertFalse(result["valid"])

    def test_blog_cannot_verify_official_scope(self):
        value = packet(); value["sources"][0]["kind"] = "secondary"
        with self.assertRaisesRegex(MODULE.PacketError, "source kind"):
            MODULE.audit(value)

    def test_dangling_source_and_evidenceless_pass_are_invalid(self):
        for ids in (["missing"], []):
            with self.subTest(ids=ids):
                value = packet(); value["candidates"][0]["checks"][0]["source_ids"] = ids
                with self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_no_comparable_requires_sourced_visible_exception(self):
        value = packet(); row = value["candidates"][0]; row["comparables"] = []
        self.assertFalse(MODULE.audit(value)["valid"])
        row["precedent_exception"] = {"reason": "Synthetic new-journal exception; limited content evidence.", "source_ids": ["S1"]}
        result = MODULE.audit(value)
        self.assertTrue(result["valid"])
        self.assertTrue(result["candidates"][0]["uses_precedent_exception"])

    def test_unverified_paper_does_not_count_as_precedent(self):
        value = packet(); value["candidates"][0]["comparables"][0]["status"] = "unverified"
        self.assertFalse(MODULE.audit(value)["valid"])

    def test_future_access_date_and_bad_types_rejected(self):
        for field, replacement in (("as_of", "2026-11-01"), ("constraints", {}), ("candidates", None)):
            with self.subTest(field=field):
                value = packet(); value[field] = replacement
                with self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_duplicate_ids_checks_and_invalid_enum_rejected(self):
        for part in ("sources", "constraints", "candidates", "checks", "status"):
            value = packet()
            if part == "checks":
                value["candidates"][0]["checks"] *= 2
            elif part == "status":
                value["candidates"][0]["checks"][0]["status"] = "probably"
            else:
                value[part].append(copy.deepcopy(value[part][0]))
            with self.subTest(part=part), self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_cli_exit_codes_and_no_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.json"
            for status, exit_code in (("pass", 0), ("unknown", 1)):
                value = packet(); value["candidates"][0]["checks"][0]["status"] = status
                path.write_text(json.dumps(value), encoding="utf-8")
                before = path.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(MODULE.main([str(path)]), exit_code)
                self.assertEqual(path.read_bytes(), before)
            path.write_text('{"schema_version":"1.0","schema_version":"2.0"}', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(MODULE.main([str(path)]), 2)

    def test_non_object_json_and_bad_utf8_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for raw in (b"[]", b"null", b"{", b"\xff"):
                path.write_bytes(raw)
                with self.subTest(raw=raw), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(MODULE.main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
