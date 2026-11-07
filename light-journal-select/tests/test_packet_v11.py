"""Synthetic scope, decision and file regressions; no journal ranking evaluation."""
import copy
import hashlib
import io
import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from test_audit_selection import MODULE, packet as legacy_packet


def packet():
    value = legacy_packet()
    value.update(schema_version="1.1", as_of="2026-11-06")
    value["research"] = {"basis": "Synthetic result excerpt; not a real project.", "inputs": []}
    value["decision"] = {"status": "proposed", "target_id": "J1", "basis": "Model proposal only."}
    target = {"publisher": "Synthetic publisher", "homepage": "https://example.invalid/journal",
              "issns": ["1932-6203"], "article_type": "Research Article",
              "publication_route": "gold_oa", "submission_stage": "initial"}
    value["candidates"][0]["target"] = target
    value["constraints"][0]["kind"] = "fees"
    for facet in MODULE.FACET_KINDS:
        value["candidates"][0][facet]["status"] = "pass"
    for source in value["sources"]:
        source["applies_to"] = [{"candidate_id": "J1", "article_type": target["article_type"],
                                  "publication_route": target["publication_route"]}]
    return value


class BoundPacketTests(unittest.TestCase):
    def test_proposal_does_not_claim_author_decision(self):
        result = MODULE.audit(packet())
        self.assertTrue(result["valid"])
        self.assertTrue(result["handoff"]["evidence_ready"])
        self.assertFalse(result["handoff"]["target_authorized"])

    def test_author_selection_retained_when_candidate_fails(self):
        value = packet(); value["decision"]["status"] = "author_selected"
        row = value["candidates"][0]; row["recommended"] = False
        row["article_type"]["status"] = "fail"
        result = MODULE.audit(value)
        self.assertTrue(result["valid"])
        self.assertTrue(result["handoff"]["target_authorized"])
        self.assertFalse(result["handoff"]["evidence_ready"])
        self.assertEqual(result["candidates"][0]["eligibility"], "excluded")

    def test_explicit_facet_fail_excludes_unknown_is_conditional(self):
        for facet in MODULE.FACET_KINDS:
            for status, expected in (("fail", "excluded"), ("unknown", "conditional")):
                value = packet(); value["candidates"][0][facet]["status"] = status
                with self.subTest(facet=facet, status=status):
                    result = MODULE.audit(value)
                    self.assertFalse(result["valid"])
                    self.assertEqual(result["candidates"][0]["eligibility"], expected)

    def test_broad_scope_cannot_verify_article_type_or_fees(self):
        value = packet(); value["sources"][0]["applies_to"] = [{"candidate_id": "J1"}]
        with self.assertRaisesRegex(MODULE.PacketError, "applicability"): MODULE.audit(value)

    def test_wrong_candidate_type_or_route_rejected(self):
        for field, replacement in (("candidate_id", "missing"), ("article_type", "Review"),
                                   ("publication_route", "subscription")):
            value = packet(); value["sources"][0]["applies_to"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_source_can_explicitly_cover_two_candidates(self):
        value = packet(); second = copy.deepcopy(value["candidates"][0]); second["id"] = "J2"
        value["candidates"].append(second)
        for source in value["sources"]:
            binding = copy.deepcopy(source["applies_to"][0]); binding["candidate_id"] = "J2"
            source["applies_to"].append(binding)
        self.assertTrue(MODULE.audit(value)["valid"])

    def test_source_cannot_be_reused_by_id_alone(self):
        value = packet(); second = copy.deepcopy(value["candidates"][0]); second["id"] = "J2"
        value["candidates"].append(second)
        with self.assertRaisesRegex(MODULE.PacketError, "applicability"): MODULE.audit(value)

    def test_index_gate_needs_index_authority(self):
        value = packet(); value["constraints"][0]["kind"] = "indexing"
        with self.assertRaisesRegex(MODULE.PacketError, "source kind"): MODULE.audit(value)
        source = copy.deepcopy(value["sources"][0]); source.update(id="S3", kind="official_index")
        value["sources"].append(source)
        value["candidates"][0]["checks"][0]["source_ids"] = ["S3"]
        self.assertTrue(MODULE.audit(value)["valid"])

    def test_unknown_route_can_cite_general_policy_without_false_pass(self):
        value = packet(); source = copy.deepcopy(value['sources'][0])
        source.update(id='S3', applies_to=[{'candidate_id': 'J1'}]); value['sources'].append(source)
        row = value['candidates'][0]; row['recommended'] = False
        row['checks'][0].update(status='unknown', source_ids=['S3'])
        result = MODULE.audit(value)
        self.assertTrue(result['valid'])
        self.assertEqual(result['candidates'][0]['eligibility'], 'conditional')

    def test_legacy_future_article_is_not_a_published_precedent(self):
        value = legacy_packet(); value['candidates'][0]['comparables'][0]['year'] = 2099
        with self.assertRaisesRegex(MODULE.PacketError, 'future'): MODULE.audit(value)

    def test_unknown_article_type_can_retain_general_source(self):
        value = packet(); source = copy.deepcopy(value['sources'][0])
        source.update(id='S3', applies_to=[{'candidate_id': 'J1'}]); value['sources'].append(source)
        row = value['candidates'][0]; row['recommended'] = False
        row['article_type'].update(status='unknown', source_ids=['S3'])
        self.assertTrue(MODULE.audit(value)['valid'])

    def test_blank_template_is_not_an_audited_recommendation(self):
        path = Path(__file__).resolve().parents[1] / 'templates/selection-packet.json'
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(MODULE.main([str(path)]), 2)

    def test_synthetic_example_matches_current_contract(self):
        path = Path(__file__).resolve().parents[1] / 'templates/selection-packet.example.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        self.assertIn('Synthetic', value['research']['basis'])
        self.assertTrue(MODULE.audit(value, packet_dir=path.parent)['valid'])

    def test_fee_blog_cannot_pass_route_gate(self):
        value = packet(); source = copy.deepcopy(value["sources"][0])
        source.update(id="S3", kind="secondary"); value["sources"].append(source)
        value["candidates"][0]["checks"][0]["source_ids"] = ["S3"]
        with self.assertRaisesRegex(MODULE.PacketError, "source kind"): MODULE.audit(value)

    def test_future_as_of_and_comparable_year_rejected(self):
        for field in ("as_of", "year"):
            value = packet()
            if field == "as_of": value[field] = "9999-01-01"
            else: value["candidates"][0]["comparables"][0][field] = 2099
            with self.subTest(field=field), self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_duplicate_binding_and_unknown_target_rejected(self):
        for field in ("binding", "decision"):
            value = packet()
            if field == "binding": value["sources"][0]["applies_to"] *= 2
            else: value["decision"]["target_id"] = "missing"
            with self.subTest(field=field), self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_unselected_has_no_target_or_approval(self):
        value = packet(); value["decision"].update(status="unselected", target_id=None)
        self.assertFalse(MODULE.audit(value)["handoff"]["target_authorized"])
        value["decision"]["target_id"] = "J1"
        with self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_legacy_compatible_with_visible_scope_limits(self):
        result = MODULE.audit(legacy_packet())
        self.assertTrue(result["valid"])
        self.assertEqual(result["audit_level"], "legacy_1.0")
        self.assertTrue(any("legacy" in w.lower() for w in result["warnings"]))

    def test_advance_online_article_can_have_future_issue_year(self):
        value = packet(); paper = value['candidates'][0]['comparables'][0]
        paper.update(year=2027, published_on='2026-10-01')
        self.assertTrue(MODULE.audit(value)['valid'])
        paper['published_on'] = '2026-12-01'
        with self.assertRaises(MODULE.PacketError): MODULE.audit(value)

    def test_misspelled_applicability_not_silently_ignored(self):
        value = packet(); value['sources'][0]['applies_to'][0]['publication_routes'] = 'subscription'
        with self.assertRaisesRegex(MODULE.PacketError, 'applicability'): MODULE.audit(value)

    def test_bad_modern_shapes_raise_packet_error(self):
        for field, replacement in (("research", []), ("decision", None)):
            value = packet(); value[field] = replacement
            with self.subTest(field=field), self.assertRaises(MODULE.PacketError): MODULE.audit(value)
        for field in ("target", "applies_to"):
            value = packet()
            if field == "target": value["candidates"][0][field] = []
            else: value["sources"][0][field] = "J1"
            with self.subTest(field=field), self.assertRaises(MODULE.PacketError): MODULE.audit(value)


class InputSnapshotTests(unittest.TestCase):
    def bound(self, root):
        path = root / "研究结果.md"; path.write_text("Synthetic negative result.", encoding="utf-8")
        value = packet()
        value["research"]["inputs"] = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
        return value, path

    def test_unchanged_input_cli_read_only_from_other_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); value, _ = self.bound(root)
            self.assertTrue(MODULE.audit(value, packet_dir=root)["valid"])
            path = root / "packet.json"; path.write_text(json.dumps(value), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(MODULE.main([str(path)]), 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_changed_missing_or_directory_input_invalidates_recommendation(self):
        for mutation in ("changed", "deleted", "directory"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); value, path = self.bound(root)
                if mutation == "changed": path.write_text("Changed conclusion.", encoding="utf-8")
                else:
                    path.unlink()
                    if mutation == "directory": path.mkdir()
                result = MODULE.audit(value, packet_dir=root)
                self.assertFalse(result["valid"])
                self.assertFalse(result["handoff"]["evidence_ready"])
                self.assertFalse(result["candidates"][0]["recommendation_ready"])

    def test_no_base_cannot_claim_unchecked_inputs_match(self):
        with tempfile.TemporaryDirectory() as folder:
            value, _ = self.bound(Path(folder))
            self.assertFalse(MODULE.audit(value)["valid"])

    def test_bad_hash_and_duplicate_input_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            value, _ = self.bound(Path(folder)); value["research"]["inputs"] *= 2
            with self.assertRaises(MODULE.PacketError): MODULE.audit(value, packet_dir=Path(folder))
            value["research"]["inputs"] = [{"path": "one", "sha256": "not-a-hash"}]
            with self.assertRaises(MODULE.PacketError): MODULE.audit(value, packet_dir=Path(folder))

    def test_message_only_context_explicit_not_blocked(self):
        result = MODULE.audit(packet())
        self.assertTrue(result["valid"])
        self.assertEqual(result["input_integrity"], "not_bound")
        self.assertTrue(any("snapshot" in w for w in result["warnings"]))

    def test_duplicate_resolved_alias_and_missing_file_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); value, path = self.bound(root)
            alias = dict(value['research']['inputs'][0]); alias['path'] = './' + alias['path']
            value['research']['inputs'].append(alias)
            with self.assertRaisesRegex(MODULE.PacketError, 'duplicate resolved'): MODULE.audit(value, packet_dir=root)
            value['research']['inputs'].pop(); path.unlink()
            packet_path = root / 'packet.json'; packet_path.write_text(json.dumps(value), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(MODULE.main([str(packet_path)]), 1)


if __name__ == "__main__":
    unittest.main()
