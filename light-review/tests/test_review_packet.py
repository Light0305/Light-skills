"""Behavioral invariants of the offline helper, not a scientific-quality benchmark."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_packet", ROOT / "scripts" / "review_packet.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="light-review-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "paper with spaces.md"
        self.source.write_text("Synthetic proposition. Proof is supplied.\n", encoding="utf-8")
        self.dest = self.root / "round-01" / "packet"
        self.packet = rp.freeze_packet(self.dest, [f"manuscript={self.source}"])
        self.stub = rp.load_json(self.dest / "review.stub.json")
        self.pointer = {"material_id": "M001", "anchor": "paragraph 1"}

    def tearDown(self):
        self.temp.cleanup()

    def ready_record(self):
        r = copy.deepcopy(self.stub)
        r.update(review_status="final", assessment_complete=True, summary="Synthetic local helper fixture.", limitations=[])
        r["coverage"][0].update(status="inspected", notes="Fixture material inspected for this test declaration.")
        for check in r["checks"]:
            check.update(status="passed", notes="Test declaration; not a real review.", evidence=[self.pointer])
        r["checks"][-1].update(status="not_applicable", notes="Venue review not requested.", evidence=[])
        r["claims"] = [{"id": "C1", "text": "Synthetic proposition.", "central": True, "location": self.pointer, "evidence": [self.pointer], "assessment": "supported"}]
        r["readiness"] = {"scientific": "ready", "submission": "not_requested", "rationale": "Synthetic consistency fixture only."}
        return r

    def issue(self, **changes):
        item = {"id": "LR-001", "severity": "major", "category": "claim", "basis": "review", "evidence_status": "unresolved", "confidence": "medium", "blocking": False, "required": True, "status": "open", "claim_ids": ["C1"], "location": self.pointer, "evidence": [self.pointer], "source_ids": [], "observation": "A synthetic uncertainty.", "impact": "Central proposition requires clarification.", "suggested_fix": "Clarify the stated assumption.", "closure_test": "Read the new assumption and dependent proposition.", "owner": "light-write", "resolution_evidence": []}
        item.update(changes)
        if item["status"] in rp.CLOSED:
            item["closure_check"] = {"packet_id": self.packet["packet_id"], "method": "rechecked", "notes": "Synthetic test declaration only."}
        return item

    def recheck_records(self):
        old = self.ready_record()
        old["issues"] = [self.issue()]
        old["readiness"]["scientific"] = "revise"
        path = self.root / "previous.json"
        rp.dump_new(path, old)
        self.source.write_text("Revised synthetic proposition. Conditions clarified.\n", encoding="utf-8")
        dest = self.root / "round-02" / "packet"
        packet = rp.freeze_packet(dest, [f"manuscript={self.source}"])
        current = copy.deepcopy(old)
        current.update(packet_id=packet["packet_id"], scope="recheck", previous_review={"packet_id": self.packet["packet_id"], "record_sha256": rp.digest_file(path)[0]})
        return old, current, packet, dest, path

    def transition(self, old, current, packet, path):
        return rp.validate_transition(current, packet, old, self.packet, rp.digest_file(path)[0])

    def close(self, current, packet, method="rechecked"):
        current["issues"][0].update(status="verified", resolution_evidence=[self.pointer], closure_check={"packet_id": packet["packet_id"], "method": method, "notes": "Checked dependent locations in the synthetic new version."})

    def cli_validate(self, current, dest, *extra):
        path = self.root / "current.json"
        path.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/review_packet.py"), "validate", "--packet", str(dest), "--record", str(path), *map(str, extra)], capture_output=True, text=True, encoding="utf-8")

    def test_snapshot_does_not_mutate_original_and_stub_does_not_claim_review(self):
        self.assertEqual(self.source.read_text(), "Synthetic proposition. Proof is supplied.\n")
        rp.verify_packet(self.dest)
        rp.validate_record(self.stub, self.packet)
        self.assertFalse(self.stub["assessment_complete"])
        self.assertEqual(self.stub["coverage"][0]["status"], "not_read")
        self.assertEqual(self.stub["readiness"]["scientific"], "not_assessable")

    def test_original_edit_does_not_change_frozen_version(self):
        self.source.write_text("Revised original.\n", encoding="utf-8")
        self.assertEqual(rp.verify_packet(self.dest)["packet_id"], self.packet["packet_id"])
        new = rp.freeze_packet(self.root / "round-02", [f"manuscript={self.source}"])
        self.assertNotEqual(new["packet_id"], self.packet["packet_id"])

    def test_corrupted_snapshot_is_detected(self):
        path = self.dest / self.packet["materials"][0]["path"]
        path.write_text("Changed frozen material", encoding="utf-8")
        with self.assertRaises(ValueError):
            rp.verify_packet(self.dest)

    def test_existing_output_is_never_overwritten(self):
        before = (self.dest / "packet.json").read_bytes()
        with self.assertRaises(ValueError):
            rp.freeze_packet(self.dest, [f"manuscript={self.source}"])
        self.assertEqual(before, (self.dest / "packet.json").read_bytes())

    def test_duplicate_inputs_rejected_before_output_creation(self):
        out = self.root / "duplicate"
        with self.assertRaises(ValueError):
            rp.freeze_packet(out, [f"manuscript={self.source}", f"context={self.source}"])
        self.assertFalse(out.exists())

    def test_incomplete_snapshot_not_usable(self):
        (self.dest / ".incomplete").touch()
        with self.assertRaises(ValueError):
            rp.verify_packet(self.dest)

    def test_path_escape_rejected_even_with_matching_manifest_id(self):
        p = copy.deepcopy(self.packet)
        p["materials"][0]["path"] = "../../paper with spaces.md"
        p["packet_id"] = rp.packet_digest(p["materials"])
        (self.dest / "packet.json").write_text(json.dumps(p), encoding="utf-8")
        with self.assertRaises(ValueError):
            rp.verify_packet(self.dest)

    def test_correct_complete_record_is_accepted(self):
        self.assertEqual(rp.validate_record(self.ready_record(), self.packet)["open_required"], 0)

    def test_wrong_version_is_rejected(self):
        r = self.ready_record()
        r["packet_id"] = "sha256:" + "0" * 64
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_focused_review_cannot_claim_full_ready(self):
        r = self.ready_record()
        r.update(scope="focused", assessment_complete=False)
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_unreadable_core_material_prevents_complete_assessment(self):
        r = self.ready_record()
        r["coverage"][0]["status"] = "unreadable"
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_unresolved_blocker_can_be_reported_but_requires_hold(self):
        r = self.ready_record()
        r["issues"] = [self.issue(severity="critical", blocking=True)]
        r["readiness"]["scientific"] = "hold"
        rp.validate_record(r, self.packet)
        r["readiness"]["scientific"] = "revise"
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_scientific_hold_does_not_falsely_assert_venue_defect(self):
        r = self.ready_record()
        r["issues"] = [self.issue(blocking=True)]
        r["readiness"].update(scientific="hold", submission="not_assessable")
        rp.validate_record(r, self.packet)
        r["readiness"]["submission"] = "ready"
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_author_addressed_does_not_mean_verified(self):
        r = self.ready_record()
        r["issues"] = [self.issue(status="addressed", resolution_evidence=[self.pointer])]
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_verified_requires_actual_resolution_pointer(self):
        r = self.ready_record()
        r["issues"] = [self.issue(status="verified")]
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)
        r["issues"][0]["resolution_evidence"] = [self.pointer]
        rp.validate_record(r, self.packet)

    def test_dismissed_requires_reason_and_evidence(self):
        r = self.ready_record()
        r["issues"] = [self.issue(status="dismissed", resolution_evidence=[self.pointer])]
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)
        r["issues"][0]["dismissal_reason"] = "Supplied assumption rules out the concern."
        rp.validate_record(r, self.packet)

    def test_required_deferred_stays_open_optional_deferred_does_not_block(self):
        r = self.ready_record()
        r["issues"] = [self.issue(status="deferred")]
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)
        r["issues"][0].update(severity="minor", required=False)
        rp.validate_record(r, self.packet)

    def test_unknown_evidence_target_rejected(self):
        r = self.ready_record()
        r["claims"][0]["evidence"] = [{"material_id": "M999", "anchor": "p1"}]
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_unsupported_central_claim_prevents_ready(self):
        r = self.ready_record()
        r["claims"][0].update(assessment="unsupported", evidence=[])
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_submission_ready_requires_venue_verification(self):
        r = self.ready_record()
        r["readiness"]["submission"] = "ready"
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)
        r["checks"][-1].update(status="passed", notes="Synthetic venue requirement inspected.", evidence=[self.pointer])
        rp.validate_record(r, self.packet)

    def test_ready_rejects_draft_and_incomplete_checks(self):
        r = self.ready_record()
        r["review_status"] = "draft"
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)
        r["review_status"] = "final"
        r["checks"][0].update(status="not_assessable", evidence=[])
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_missing_or_duplicated_coverage_rejected(self):
        r = self.ready_record()
        r["coverage"] = []
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)
        r["coverage"] = [copy.deepcopy(self.stub["coverage"][0])] * 2
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_duplicate_issue_ids_rejected(self):
        r = self.ready_record()
        r["readiness"]["scientific"] = "revise"
        r["issues"] = [self.issue(), self.issue()]
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_cli_exit_codes_and_malformed_record(self):
        command = [sys.executable, str(ROOT / "scripts" / "review_packet.py")]
        result = subprocess.run(command + ["verify", "--packet", str(self.dest)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        malformed = self.root / "malformed.json"
        malformed.write_text('{"issues": []}', encoding="utf-8")
        result = subprocess.run(command + ["validate", "--packet", str(self.dest), "--record", str(malformed)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stderr)["ok"])

    def test_unread_material_cannot_supply_positive_check_evidence(self):
        for status in ("not_read", "unreadable", "not_applicable"):
            with self.subTest(status=status):
                r = self.ready_record()
                r.update(scope="focused", assessment_complete=False)
                r["readiness"]["scientific"] = "not_assessable"
                r["coverage"][0]["status"] = status
                with self.assertRaisesRegex(ValueError, "evidence requires"):
                    rp.validate_record(r, self.packet)

    def test_partial_read_supports_focused_anchors_without_full_ready(self):
        r = self.ready_record()
        r.update(scope="focused", assessment_complete=False)
        r["coverage"][0].update(status="partial", notes="Only paragraph 1 inspected.")
        r["readiness"]["scientific"] = "not_assessable"
        rp.validate_record(r, self.packet)
        r["assessment_complete"] = True
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_unread_data_cannot_close_issue(self):
        data = self.root / "data.csv"
        data.write_text("unit,value\n1,2\n", encoding="utf-8")
        p = rp.freeze_packet(self.root / "with-data", [f"manuscript={self.source}", f"data={data}"])
        r = self.ready_record(); r["packet_id"] = p["packet_id"]
        r["coverage"].append({"material_id":"M002", "status":"not_read", "notes":"Not inspected."})
        r["issues"] = [self.issue(status="verified", resolution_evidence=[{"material_id":"M002", "anchor":"row 2"}])]
        with self.assertRaisesRegex(ValueError, "evidence requires"):
            rp.validate_record(r, p)

    def test_current_schema_recheck_requires_parent_binding(self):
        r = self.ready_record(); r["scope"] = "recheck"
        with self.assertRaisesRegex(ValueError, "requires previous_review"):
            rp.validate_record(r, self.packet)

    def test_current_schema_closure_requires_current_packet_and_notes(self):
        r = self.ready_record()
        r["issues"] = [self.issue(status="verified", resolution_evidence=[self.pointer])]
        r["issues"][0]["closure_check"]["packet_id"] = "sha256:" + "0"*64
        with self.assertRaisesRegex(ValueError, "current packet"):
            rp.validate_record(r, self.packet)
        r["issues"][0]["closure_check"].update(packet_id=self.packet["packet_id"], notes="")
        with self.assertRaises(ValueError):
            rp.validate_record(r, self.packet)

    def test_legacy_record_still_valid_and_unbound_recheck_warns(self):
        r = self.ready_record(); r.update(schema_version="1.0", scope="recheck")
        r.pop("previous_review")
        r["issues"] = [self.issue(status="verified", resolution_evidence=[self.pointer])]
        r["issues"][0].pop("closure_check")
        rp.validate_record(r, self.packet)
        result = self.cli_validate(r, self.dest)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["lineage"], "not_checked")
        self.assertIn("Legacy unbound", output["warning"])

    def test_dropped_previous_issue_rejected(self):
        old, current, p, _, path = self.recheck_records()
        current["issues"] = []; current["readiness"]["scientific"] = "ready"
        with self.assertRaisesRegex(ValueError, "missing: LR-001"):
            self.transition(old, current, p, path)

    def test_closed_previous_issue_cannot_disappear(self):
        old, current, p, _, path = self.recheck_records()
        self.close(old, self.packet)
        current["issues"] = []
        with self.assertRaisesRegex(ValueError, "missing: LR-001"):
            self.transition(old, current, p, path)

    def test_parent_record_hash_and_packet_are_checked(self):
        old, current, p, _, path = self.recheck_records()
        for key, value in (("record_sha256", "0"*64), ("packet_id", "sha256:"+"0"*64)):
            with self.subTest(key=key):
                bad = copy.deepcopy(current); bad["previous_review"][key] = value
                with self.assertRaises(ValueError):
                    self.transition(old, bad, p, path)

    def test_silent_downgrade_or_issue_replacement_rejected(self):
        old, current, p, _, path = self.recheck_records()
        for field, value in (("severity","minor"), ("required",False), ("observation","A different concern."), ("category","presentation"), ("closure_test","Check spelling only.")):
            with self.subTest(field=field):
                bad = copy.deepcopy(current); bad["issues"][0][field] = value
                with self.assertRaises(ValueError):
                    self.transition(old, bad, p, path)

    def test_evidenced_reassessment_allowed_and_retains_issue_id(self):
        old, current, p, _, path = self.recheck_records()
        current["issues"][0].update(severity="minor", required=False, reassessment={"reason":"The central assertion was narrowed, leaving an optional wording issue.", "evidence":[self.pointer]})
        self.assertEqual(self.transition(old, current, p, path)["previous_issues"], 1)
        current["issues"][0]["reassessment"]["evidence"] = []
        with self.assertRaises(ValueError):
            self.transition(old, current, p, path)

    def test_new_issue_id_must_exceed_previous_maximum(self):
        old, current, p, _, path = self.recheck_records()
        old["issues"][0]["id"] = current["issues"][0]["id"] = "LR-009"
        current["issues"].append(self.issue(id="LR-002"))
        with self.assertRaisesRegex(ValueError, "previous maximum"):
            self.transition(old, current, p, path)
        current["issues"][-1]["id"] = "LR-010"
        self.assertEqual(self.transition(old, current, p, path)["new_issues"], 1)

    def test_rechecked_closure_is_accepted_for_changed_version(self):
        old, current, p, _, path = self.recheck_records()
        self.close(current, p); current["readiness"]["scientific"] = "ready"
        self.assertEqual(self.transition(old, current, p, path)["lineage"], "immediate_parent_checked")

    def test_copied_closure_stamp_is_not_current(self):
        old, current, p, _, path = self.recheck_records()
        self.close(current, self.packet)
        with self.assertRaisesRegex(ValueError, "current packet"):
            self.transition(old, current, p, path)

    def test_unchanged_evidence_does_not_close_previously_open_issue(self):
        old, current, p, _, path = self.recheck_records()
        self.close(current, p, "unchanged_evidence")
        with self.assertRaisesRegex(ValueError, "unclosed"):
            self.transition(old, current, p, path)

    def test_changed_evidence_cannot_inherit_prior_closure(self):
        old, current, p, _, path = self.recheck_records()
        self.close(old, self.packet); self.close(current, p, "unchanged_evidence")
        with self.assertRaisesRegex(ValueError, "changed; recheck"):
            self.transition(old, current, p, path)

    def test_identical_cited_bytes_allow_declared_closure_inheritance(self):
        old, current, p, _, path = self.recheck_records()
        self.close(old, self.packet)
        current["packet_id"] = self.packet["packet_id"]
        self.close(current, self.packet, "unchanged_evidence")
        self.assertEqual(self.transition(old, current, self.packet, path)["lineage"], "immediate_parent_checked")
        current["issues"][0]["resolution_evidence"][0] = {"material_id":"M001", "anchor":"paragraph 2"}
        with self.assertRaises(ValueError):
            self.transition(old, current, self.packet, path)

    def test_reopening_closed_issue_is_allowed(self):
        old, current, p, _, path = self.recheck_records()
        self.close(old, self.packet)
        self.transition(old, current, p, path)

    def test_current_real_owner_routes_and_legacy_label_supported(self):
        r = self.ready_record(); r["readiness"]["scientific"] = "revise"
        for owner in ("light-chart", "light-diagram", "light-design", "light-journal-select", "figure-workflow"):
            with self.subTest(owner=owner):
                r["issues"] = [self.issue(owner=owner)]
                rp.validate_record(r, self.packet)

    def test_duplicate_json_keys_rejected_instead_of_overriding(self):
        path = self.root / "duplicate.json"
        path.write_text('{"readiness":{"scientific":"hold","scientific":"ready"}}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            rp.load_json(path)

    def test_cli_requires_parent_arguments_and_checks_real_previous_bytes(self):
        old, current, p, dest, path = self.recheck_records()
        result = self.cli_validate(current, dest)
        self.assertEqual(result.returncode, 2)
        result = self.cli_validate(current, dest, "--previous-packet", self.dest)
        self.assertEqual(result.returncode, 2)
        args = ("--previous-packet", self.dest, "--previous-record", path)
        result = self.cli_validate(current, dest, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["lineage"], "immediate_parent_checked")
        path.write_text(json.dumps(old)+"\n", encoding="utf-8")
        result = self.cli_validate(current, dest, *args)
        self.assertEqual(result.returncode, 2)
        self.assertIn("record hash", json.loads(result.stderr)["error"])

    def test_cli_rejects_corrupted_previous_packet(self):
        _, current, _, dest, path = self.recheck_records()
        (self.dest / self.packet["materials"][0]["path"]).write_text("Changed frozen copy", encoding="utf-8")
        result = self.cli_validate(current, dest, "--previous-packet", self.dest, "--previous-record", path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("hash or size changed", json.loads(result.stderr)["error"])

    def test_cli_chinese_paths_output_utf8_under_ascii_environment(self):
        import os
        command = [sys.executable, str(ROOT / "scripts/review_packet.py"), "verify", "--packet", str(self.root/"不存在")]
        result = subprocess.run(command, capture_output=True, env={**os.environ,"PYTHONIOENCODING":"ascii"})
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stderr.decode("utf-8"))["ok"])

    def test_claim_location_must_be_read_when_assessed(self):
        r = copy.deepcopy(self.stub)
        r["claims"] = self.ready_record()["claims"]
        with self.assertRaisesRegex(ValueError, "evidence requires"):
            rp.validate_record(r, self.packet)
        r["claims"][0].update(assessment="not_assessable", evidence=[])
        rp.validate_record(r, self.packet)

    def test_issue_evidence_cannot_assert_unread_content(self):
        r = copy.deepcopy(self.stub)
        r["issues"] = [self.issue(claim_ids=[])]
        with self.assertRaisesRegex(ValueError, "evidence requires"):
            rp.validate_record(r, self.packet)

    def test_transition_can_adopt_a_legacy_previous_record(self):
        old, current, p, _, path = self.recheck_records()
        old["schema_version"] = "1.0"; old.pop("previous_review")
        path.write_text(json.dumps(old), encoding="utf-8")
        current["previous_review"]["record_sha256"] = rp.digest_file(path)[0]
        self.transition(old, current, p, path)

    def test_inherited_closure_cannot_skip_evidenced_reassessment(self):
        old, current, _, _, path = self.recheck_records()
        self.close(old, self.packet)
        current["packet_id"] = self.packet["packet_id"]
        self.close(current, self.packet, "unchanged_evidence")
        current["issues"][0].update(severity="minor", reassessment={"reason":"New interpretation.","evidence":[self.pointer]})
        with self.assertRaisesRegex(ValueError, "new closure check"):
            self.transition(old, current, self.packet, path)

    def test_unchanged_evidence_can_follow_renumbered_material_ids(self):
        old, current, _, _, path = self.recheck_records()
        self.close(old, self.packet)
        path.write_text(json.dumps(old), encoding="utf-8")
        current["previous_review"]["record_sha256"] = rp.digest_file(path)[0]
        self.source.write_text("Synthetic proposition. Proof is supplied.\n", encoding="utf-8")
        extra = self.root / "unrelated.txt"; extra.write_text("Unrelated input", encoding="utf-8")
        p = rp.freeze_packet(self.root / "renumbered", [f"context={extra}", f"manuscript={self.source}"])
        current["packet_id"] = p["packet_id"]
        current["coverage"] = [{"material_id":"M001", "status":"not_read", "notes":"Unrelated."}, {"material_id":"M002","status":"inspected","notes":"Same cited manuscript bytes."}]
        for check in current["checks"]:
            for pointer in check["evidence"]:
                pointer["material_id"] = "M002"
        # Replace independent structures; do not relabel the prior record's pointers.
        current["claims"] = copy.deepcopy(old["claims"])
        current["claims"][0]["location"]["material_id"] = "M002"
        current["claims"][0]["evidence"] = [{"material_id":"M002", "anchor":"paragraph 1"}]
        current["issues"] = copy.deepcopy(old["issues"])
        for key in ("evidence", "resolution_evidence"):
            current["issues"][0][key] = [{"material_id":"M002", "anchor":"paragraph 1"}]
        current["issues"][0]["location"] = {"material_id":"M002", "anchor":"paragraph 1"}
        current["issues"][0]["closure_check"].update(packet_id=p["packet_id"], method="unchanged_evidence")
        self.transition(old, current, p, path)

    def test_changed_dismissal_reason_needs_fresh_closure_check(self):
        old, current, _, _, path = self.recheck_records()
        for r in (old, current):
            self.close(r, self.packet)
            r["issues"][0].update(status="dismissed", dismissal_reason="The concern was disproved.")
        current["packet_id"] = self.packet["packet_id"]
        current["issues"][0]["closure_check"]["method"] = "unchanged_evidence"
        current["issues"][0]["dismissal_reason"] = "A different rationale."
        with self.assertRaisesRegex(ValueError, "dismissal reason changed"):
            self.transition(old, current, self.packet, path)

    def test_cli_only_checks_immediate_parent_of_a_later_round(self):
        old, current, p, dest, path = self.recheck_records()
        previous_path = self.root / "middle.json"
        rp.dump_new(previous_path, current)
        latest = copy.deepcopy(current)
        latest["previous_review"] = {"packet_id":p["packet_id"], "record_sha256":rp.digest_file(previous_path)[0]}
        result = self.cli_validate(latest, dest, "--previous-packet", dest, "--previous-record", previous_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["lineage"], "immediate_parent_checked")


if __name__ == "__main__":
    unittest.main()
