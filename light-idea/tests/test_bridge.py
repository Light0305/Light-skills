"""Synthetic IO/contract fixtures only. These are not real papers or search evidence."""

from __future__ import annotations

import copy
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("idea_bridge", ROOT / "scripts" / "idea_bridge.py")
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def save(path: Path, value, *, jsonl=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in value) if jsonl else json.dumps(value, ensure_ascii=False)
    path.write_text(content + "\n", encoding="utf-8")


class BridgeCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="light-idea-test-")
        self.base = Path(self.temp.name)
        self.lit = self.base / "input" / "Literature"
        self.run = self.base / "input" / "runs" / "synthetic"
        self.out = self.base / "output"
        self.lit.mkdir(parents=True)
        self.run.mkdir(parents=True)
        self.records = [
            {"paper_id": "p_one", "title": "SYNTHETIC IO fixture 一", "doi": "10.0000/synthetic-one",
             "abstract": "Synthetic fixture; not scientific evidence.", "evidence_depth": "full_text_link"},
            {"paper_id": "p_two", "title": "SYNTHETIC IO fixture 二", "doi": "10.0000/synthetic-two"},
        ]
        save(self.run / "papers.jsonl", self.records, jsonl=True)
        with (self.run / "screening.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["paper_id", "decision", "reason_code", "screened_by"])
            writer.writeheader()
            writer.writerows([
                {"paper_id": "p_one", "decision": "maybe", "reason_code": "PENDING_REVIEW", "screened_by": "rule"},
                {"paper_id": "p_two", "decision": "exclude", "reason_code": "OUT_OF_SCOPE", "screened_by": "host"},
            ])
        entries = []
        for n, record in enumerate(self.records, 1):
            folder = self.lit / f"synthetic-{n}"
            save(folder / "meta.json", record)
            (folder / "paper.md").write_text("# Synthetic original\n\nMethods: fixture only.\n", encoding="utf-8")
            (folder / "note.md").write_text("# Synthetic note\nThis is not a scientific source.\n", encoding="utf-8")
            entries.append({**record, "folder": folder.name})
        save(self.lit / "manifest.json", {"entries": entries})

    def tearDown(self):
        self.temp.cleanup()

    def ingest(self, **kwargs):
        return bridge.ingest(self.lit, self.run, self.out, **kwargs)

    def snapshot(self):
        return {str(p): bridge.sha256(p) for p in (self.base / "input").rglob("*") if p.is_file()}

    def workspace(self, recommended=False):
        self.ingest()
        idea = {
            "idea_id": "I01", "version": 1, "title": "SYNTHETIC contract fixture",
            "status": "recommended" if recommended else "hold", "question": "Synthetic question for contract checks",
            "rationale": "IO test, not a scientific recommendation", "basis_evidence_ids": ["E01"],
            "claim_type": "empirical", "hypothesis": "Synthetic hypothesis",
            "prior_art": [{"paper_id": "p_one", "overlap": "Synthetic overlap", "delta": "Synthetic difference", "evidence_ids": ["E01"]}],
            "novelty": {"status": "differentiated_within_scope", "search_ids": ["N01", "N02"],
                        "conclusion": "Synthetic fixture only", "limitations": "No actual search was performed"},
            "gates": {"data_access": "confirmed", "resource_fit": "confirmed",
                      "data_access_basis": "Synthetic fixture only", "resource_fit_basis": "Synthetic fixture only"},
            "design": {field: f"Synthetic {field}; no experiment was performed" for field in bridge.DESIGN_FIELDS},
            "review": {"strongest_objection": "Synthetic objection", "response": "Synthetic response", "residual_risk": "Synthetic risk"},
            "decision_reason": "Synthetic contract fixture, not a real decision",
        }
        document = {"schema_version": "1.0", "topic": "SYNTHETIC TEST ONLY", "constraints": {}, "ideas": [idea]}
        source = self.lit / "synthetic-1" / "paper.md"
        evidence = [{"evidence_id": "E01", "paper_id": "p_one", "kind": "method", "statement": "Synthetic fixture statement",
                     "access_level": "full_text", "source_file": str(source.resolve()), "source_sha256": bridge.sha256(source),
                     "locator": "Methods / line 3", "verified": True}]
        searches = [{"search_id": f"N0{n}", "idea_ids": ["I01"], "idea_versions": {"I01": 1}, "date": "2026-11-02",
                     "idea_fingerprints": {"I01": bridge.idea_fingerprint(idea)},
                     "source": "OFFLINE FIXTURE; no actual search", "query": query, "intent": intent, "status": "ok",
                     "result_paper_ids": ["p_one"], "screened_summary": "Synthetic screening fixture",
                     "limitations": "No retrieval; tests referential integrity only"}
                    for n, query, intent in [(1, "synthetic exact question", "duplicate"), (2, "synthetic mechanism", "mechanism")]]
        self.write_bundle(document, evidence, searches)
        return document, evidence, searches

    def write_bundle(self, document, evidence, searches):
        save(self.out / "ideas.json", document)
        save(self.out / "evidence.jsonl", evidence, jsonl=True)
        save(self.out / "novelty_log.jsonl", searches, jsonl=True)

    def assert_fails(self, fragment):
        result = bridge.verify(self.out)
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(fragment in error for error in result["errors"]), result)

    def test_ingest_never_modifies_upstream(self):
        before = self.snapshot()
        self.ingest()
        self.assertEqual(before, self.snapshot())

    def test_availability_does_not_become_reading(self):
        result = self.ingest()
        context = bridge.read_json(self.out / "context.json")
        self.assertEqual(len(context["papers"]), 1)
        self.assertEqual(context["papers"][0]["reading_status"], "not_assessed")
        self.assertIn("paper.md", context["papers"][0]["assets"])
        self.assertTrue(any("screening not established" in w for w in result["warnings"]))

    def test_excluded_papers_require_explicit_inclusion(self):
        self.ingest(include_excluded=True)
        context = bridge.read_json(self.out / "context.json")
        self.assertEqual(len(context["papers"]), 2)
        self.assertEqual(context["papers"][1]["decision"], "exclude")

    def test_selecting_excluded_id_does_not_silently_include(self):
        with self.assertRaisesRegex(bridge.InputError, "is excluded"):
            self.ingest(paper_ids={"p_two"})

    def test_unknown_requested_id_is_error(self):
        with self.assertRaisesRegex(bridge.InputError, "not found"):
            self.ingest(paper_ids={"p_missing"})

    def test_no_implicit_index_overwrite(self):
        self.ingest()
        before = (self.out / "context.json").read_bytes()
        with self.assertRaisesRegex(bridge.InputError, "already exists"):
            self.ingest()
        self.assertEqual(before, (self.out / "context.json").read_bytes())

    def test_force_preserves_user_ideas_and_decision(self):
        self.ingest()
        (self.out / "decision.md").write_text("Preserve my decision", encoding="utf-8")
        save(self.out / "ideas.json", {"user": "authored"})
        self.ingest(force=True)
        self.assertEqual((self.out / "decision.md").read_text(encoding="utf-8"), "Preserve my decision")
        self.assertEqual(bridge.read_json(self.out / "ideas.json"), {"user": "authored"})

    def test_reject_output_inside_upstream(self):
        with self.assertRaisesRegex(bridge.InputError, "outside the input"):
            bridge.ingest(self.lit, self.run, self.lit / "new")

    def test_manifest_path_traversal_is_rejected(self):
        manifest = bridge.read_json(self.lit / "manifest.json")
        manifest["entries"][0]["folder"] = "../outside"
        save(self.lit / "manifest.json", manifest)
        with self.assertRaisesRegex(bridge.InputError, "escapes input root"):
            self.ingest()

    def test_compatible_repeated_run_id_preserves_provenance(self):
        first = {**self.records[0], "source_records": [{"source": "synthetic-a"}]}
        second = {**self.records[0], "source_records": [{"source": "synthetic-b"}]}
        save(self.run / "papers.jsonl", [first, second], jsonl=True)
        result = self.ingest()
        paper = bridge.read_json(self.out / "context.json")["papers"][0]
        self.assertEqual({item["source"] for item in paper["source_records"]}, {"synthetic-a", "synthetic-b"})
        self.assertTrue(any("Repeated paper_id" in warning for warning in result["warnings"]))

    def test_repeated_run_id_with_conflicting_doi_is_error(self):
        second = {**self.records[0], "doi": "10.0000/conflicting-synthetic"}
        save(self.run / "papers.jsonl", [self.records[0], second], jsonl=True)
        with self.assertRaisesRegex(bridge.InputError, "Conflicting DOI"):
            self.ingest()

    def test_identical_screening_duplicates_are_harmless(self):
        row = {"paper_id": "p_one", "decision": "maybe", "screened_by": "rule"}
        save(self.run / "screening.jsonl", [row, row], jsonl=True)
        result = self.ingest()
        self.assertTrue(any("identical screening" in warning for warning in result["warnings"]))

    def test_conflicting_screening_is_not_silently_resolved(self):
        save(self.run / "screening.jsonl", [{"paper_id": "p_one", "decision": "include"},
                                            {"paper_id": "p_one", "decision": "exclude"}], jsonl=True)
        with self.assertRaisesRegex(bridge.InputError, "Conflicting screening"):
            self.ingest()

    def test_conflicting_identity_is_not_silently_merged(self):
        meta = {**self.records[0], "doi": "10.0000/other-synthetic"}
        save(self.lit / "synthetic-1" / "meta.json", meta)
        with self.assertRaisesRegex(bridge.InputError, "DOI differs"):
            self.ingest()

    def test_project_root_and_single_paper_inputs(self):
        bridge.ingest(self.lit.parent, None, self.out)
        context = bridge.read_json(self.out / "context.json")
        self.assertEqual(len(context["papers"]), 2)
        bridge.ingest(self.lit / "synthetic-1", None, self.base / "single")
        self.assertEqual(bridge.read_json(self.base / "single" / "context.json")["papers"][0]["paper_id"], "p_one")

    def test_export_fallback_and_no_manifest(self):
        (self.run / "papers.jsonl").unlink()
        save(self.run / "exports" / "papers.json", self.records)
        (self.lit / "manifest.json").unlink()
        self.ingest()
        self.assertEqual(bridge.read_json(self.out / "context.json")["counts"]["papers"], 1)

    def test_bom_json_and_non_ascii(self):
        path = self.lit / "synthetic-1" / "meta.json"
        path.write_text(json.dumps(self.records[0], ensure_ascii=False), encoding="utf-8-sig")
        self.ingest()
        self.assertIn("一", bridge.read_json(self.out / "context.json")["papers"][0]["title"])

    def test_synthetic_complete_contract_passes(self):
        self.workspace(recommended=True)
        self.assertTrue(bridge.verify(self.out)["ok"])

    def test_explicit_hold_needs_no_fake_evidence(self):
        self.ingest()
        document = bridge.read_json(ROOT / "templates" / "ideas.example.json")
        save(self.out / "ideas.json", document)
        self.assertTrue(bridge.verify(self.out)["ok"])

    def test_unknown_evidence_and_citation_fail(self):
        doc, ev, searches = self.workspace()
        doc["ideas"][0]["basis_evidence_ids"] = ["E_missing"]
        doc["ideas"][0]["question"] += " [[p_fabricated]]"
        self.write_bundle(doc, ev, searches)
        self.assert_fails("unknown ID E_missing")
        self.assert_fails("unknown paper: p_fabricated")

    def test_unknown_search_result_fails(self):
        doc, ev, searches = self.workspace()
        searches[0]["result_paper_ids"] = ["p_fabricated"]
        self.write_bundle(doc, ev, searches)
        self.assert_fails("unknown ID p_fabricated")

    def test_unknown_markdown_citation_is_checked(self):
        self.workspace()
        (self.out / "cards").mkdir()
        (self.out / "cards" / "I01.md").write_text("A fabricated citation [[p_missing]]", encoding="utf-8")
        self.assert_fails("I01.md: citation token refers to unknown paper")

    def test_abstract_not_full_text_prior_art(self):
        doc, ev, searches = self.workspace(recommended=True)
        ev[0]["access_level"] = "abstract"
        self.write_bundle(doc, ev, searches)
        self.assert_fails("full-text closest-prior-art")

    def test_unchecked_evidence_does_not_support_recommendation(self):
        doc, ev, searches = self.workspace(recommended=True)
        ev[0]["verified"] = False
        self.write_bundle(doc, ev, searches)
        self.assert_fails("not checked")

    def test_pivot_cannot_inherit_old_search_pass(self):
        doc, ev, searches = self.workspace(recommended=True)
        doc["ideas"][0]["version"] = 2
        self.write_bundle(doc, ev, searches)
        self.assert_fails("current-version successful")

    def test_failed_searches_do_not_count_as_no_overlap(self):
        doc, ev, searches = self.workspace(recommended=True)
        searches[1]["status"] = "failed"
        self.write_bundle(doc, ev, searches)
        self.assert_fails("current-version successful")

    def test_same_query_two_labels_not_two_concepts(self):
        doc, ev, searches = self.workspace(recommended=True)
        searches[1]["query"] = searches[0]["query"].upper()
        self.write_bundle(doc, ev, searches)
        self.assert_fails("distinct-concept searches")

    def test_prior_art_evidence_must_belong_to_that_paper(self):
        doc, ev, searches = self.workspace(recommended=True)
        save(self.out / "external_papers.jsonl", [{"paper_id": "ext_two", "title": "SYNTHETIC external", "url": "https://fixture.invalid/paper", "retrieved_at": "2026-11-02"}], jsonl=True)
        doc["ideas"][0]["prior_art"][0]["paper_id"] = "ext_two"
        self.write_bundle(doc, ev, searches)
        self.assert_fails("belongs to a different paper")

    def test_blocked_resources_cannot_be_averaged_away(self):
        doc, ev, searches = self.workspace(recommended=True)
        doc["ideas"][0]["gates"]["data_access"] = "blocked"
        doc["ideas"][0]["assessment"] = {"novelty": {"score": 3}, "value": {"score": 3}}
        self.write_bundle(doc, ev, searches)
        self.assert_fails("confirmed data_access")

    def test_confirmed_resources_need_a_recorded_basis(self):
        doc, ev, searches = self.workspace(recommended=True)
        doc["ideas"][0]["gates"].pop("data_access_basis")
        self.write_bundle(doc, ev, searches)
        self.assert_fails("data_access_basis must")

    def test_test_needs_falsifier(self):
        doc, ev, searches = self.workspace(recommended=True)
        doc["ideas"][0]["design"]["falsifier"] = ""
        self.write_bundle(doc, ev, searches)
        self.assert_fails("falsifier must")

    def test_input_drift_is_detected(self):
        self.workspace()
        (self.lit / "synthetic-1" / "paper.md").write_text("Changed original", encoding="utf-8")
        self.assert_fails("changed since ingest")

    def test_missing_input_is_detected(self):
        self.workspace()
        (self.lit / "synthetic-1" / "paper.md").unlink()
        self.assert_fails("missing since ingest")

    def test_retracted_support_cannot_be_recommended(self):
        self.workspace(recommended=True)
        context = bridge.read_json(self.out / "context.json")
        context["papers"][0]["is_retracted"] = True
        save(self.out / "context.json", context)
        self.assert_fails("retracted paper")

    def test_malformed_shapes_report_errors_instead_of_crashing(self):
        original, evidence, searches = self.workspace(recommended=True)
        mutations = [
            ("idea status", lambda d, e, s: d["ideas"][0].update(status=[])),
            ("novelty", lambda d, e, s: d["ideas"][0].update(novelty=[])),
            ("basis", lambda d, e, s: d["ideas"][0].update(basis_evidence_ids="E01")),
            ("access_level", lambda d, e, s: e[0].update(access_level={})),
            ("paper_id", lambda d, e, s: e[0].update(paper_id=[])),
            ("search ideas", lambda d, e, s: s[0].update(idea_ids=None)),
            ("search version", lambda d, e, s: s[0].update(idea_versions=[])),
            ("search intent", lambda d, e, s: s[0].update(intent=[])),
            ("url", lambda d, e, s: e[0].update(source_url="https://[")),
        ]
        for name, mutation in mutations:
            with self.subTest(name=name):
                doc, ev, log = copy.deepcopy((original, evidence, searches))
                mutation(doc, ev, log)
                self.write_bundle(doc, ev, log)
                self.assertFalse(bridge.verify(self.out)["ok"])

    def test_theoretical_claim_uses_domain_appropriate_text(self):
        doc, ev, searches = self.workspace(recommended=True)
        idea = doc["ideas"][0]
        idea["claim_type"] = "theoretical"
        idea["design"].update(test="Check minimal counterexamples and the proof bottleneck",
                              baseline="Closest theorem and strongest known bound",
                              metric="Whether the claimed implication holds",
                              success="A valid proof under the stated assumptions",
                              falsifier="A valid counterexample")
        for search in searches:
            search["idea_fingerprints"] = {"I01": bridge.idea_fingerprint(idea)}
        self.write_bundle(doc, ev, searches)
        self.assertTrue(bridge.verify(self.out)["ok"])

    def test_cli_error_is_structured_and_exit_two(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "idea_bridge.py"), "ingest", "--out", str(self.out)],
                                capture_output=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
