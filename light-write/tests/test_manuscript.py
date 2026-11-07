"""Synthetic file/anchor checks; these tests do not grade scientific writing."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manuscript_audit', ROOT / 'scripts/audit_manuscript.py')
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
spec = importlib.util.spec_from_file_location('writing_metrics', ROOT / 'scripts/text_metrics.py')
metrics = importlib.util.module_from_spec(spec); spec.loader.exec_module(metrics)


def ref(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class ManuscriptTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='writing-audit-'); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / '原始结果.md'
        self.body = 'The observed association was 1.2 (95% CI 0.9–1.3) [@source1].'
        self.source.write_text(self.body, encoding='utf-8')
        self.draft = self.root / 'draft-v01.md'; self.draft.write_text(self.body, encoding='utf-8')
        self.packet = {'schema_version': '1.0', 'basis': 'Synthetic author-provided result, no real study',
            'manuscript': {'paper_id': 'PAPER-0001', 'revision': 'v01', **ref(self.draft)},
            'sources': [{'id': 'S1', 'role': 'analysis', **ref(self.source)}],
            'claims': [{'id': 'C1', 'anchor': self.body, 'status': 'supported',
                        'boundary': 'Synthetic association, no causal conclusion',
                        'evidence': [{'source_id': 'S1', 'locator': 'Paragraph 1'}]}],
            'protected_literals': [{'source_id': 'S1', 'text': '95% CI 0.9–1.3'},
                                   {'source_id': 'S1', 'text': '[@source1]'}], 'parent': None}

    def run_audit(self, packet=None):
        return audit.audit(self.packet if packet is None else packet, self.root)

    def revise(self, body):
        self.draft.write_text(body, encoding='utf-8')
        self.packet['manuscript'].update(ref(self.draft))
        self.packet['claims'][0]['anchor'] = body

    def test_current_files_and_declared_links_pass_read_only(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertTrue(self.run_audit()['checks_passed'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_source_and_draft_drift_are_not_silently_resnapshotted(self):
        for which in ('source', 'draft'):
            with self.subTest(which=which):
                path = getattr(self, which); old = path.read_bytes(); path.write_bytes(b'changed')
                self.assertFalse(self.run_audit()['checks_passed']); path.write_bytes(old)

    def test_missing_or_directory_source_reports_failure(self):
        self.source.unlink()
        self.assertFalse(self.run_audit()['checks_passed'])
        self.source.mkdir()
        self.assertFalse(self.run_audit()['checks_passed'])

    def test_anchor_must_exist_in_current_draft(self):
        self.packet['claims'][0]['anchor'] = 'A sentence not in this manuscript'
        self.assertFalse(self.run_audit()['checks_passed'])

    def test_lost_ci_or_citation_literal_is_found(self):
        for body in ('The association was 1.2 [@source1].', '95% CI 0.9–1.3 with no citation.'):
            self.revise(body)
            with self.subTest(body=body): self.assertFalse(self.run_audit()['checks_passed'])

    def test_protected_literal_cannot_be_invented_from_an_unrelated_source(self):
        self.packet['protected_literals'][0]['text'] = 'Not supplied'
        self.assertFalse(self.run_audit()['checks_passed'])

    def test_claim_unknown_source_missing_support_and_bad_status_rejected(self):
        for mutation in ('unknown', 'empty', 'status'):
            value = copy.deepcopy(self.packet); claim = value['claims'][0]
            if mutation == 'unknown': claim['evidence'][0]['source_id'] = 'absent'
            elif mutation == 'empty': claim['evidence'] = []
            else: claim['status'] = 'proved'
            with self.subTest(mutation=mutation), self.assertRaises(audit.PacketError): self.run_audit(value)

    def test_interpretation_still_requires_a_cited_source(self):
        self.packet['claims'][0].update(status='interpretation', evidence=[])
        with self.assertRaises(audit.PacketError): self.run_audit()

    def test_honest_unresolved_draft_is_not_mistaken_for_scientific_approval(self):
        for status in ('planned', 'needs_evidence', 'disputed'):
            self.packet['claims'][0].update(status=status, evidence=[])
            result = self.run_audit()
            self.assertTrue(result['checks_passed'])
            self.assertEqual(result['unresolved_claims'], ['C1'])
            self.assertTrue(result['warnings'])

    def test_no_declared_claims_and_no_sources_have_explicit_limits(self):
        self.packet.update(claims=[], sources=[], protected_literals=[])
        result = self.run_audit()
        self.assertTrue(result['checks_passed']); self.assertEqual(len(result['warnings']), 2)

    def test_duplicate_ids_and_nonobject_shapes_rejected(self):
        for part in ('sources', 'claims'):
            value = copy.deepcopy(self.packet); value[part] *= 2
            with self.subTest(part=part), self.assertRaises(audit.PacketError): self.run_audit(value)
        for part in ('sources', 'claims', 'protected_literals'):
            value = copy.deepcopy(self.packet); value[part] = {}
            with self.subTest(part=part), self.assertRaises(audit.PacketError): self.run_audit(value)

    def test_draft_cannot_be_its_own_source(self):
        self.packet['sources'][0].update(ref(self.draft))
        with self.assertRaises(audit.PacketError): self.run_audit()

    def test_bad_hash_and_no_base_fail_closed(self):
        self.packet['manuscript']['sha256'] = 'wrong'
        with self.assertRaises(audit.PacketError): self.run_audit()
        with self.assertRaises(audit.PacketError): audit.audit(self.packet, None)

    def test_binary_artifact_can_be_hashed_but_not_treated_as_read_text(self):
        self.draft.write_bytes(bytes([255, 254, 0]))
        self.packet['manuscript'].update(ref(self.draft))
        self.assertFalse(self.run_audit()['checks_passed'])
        self.packet.update(claims=[], protected_literals=[])
        self.assertTrue(self.run_audit()['checks_passed'])

    def test_parent_binds_prior_packet_without_revalidating_old_sources(self):
        old = self.root / 'v01-packet.json'; old.write_text(json.dumps(self.packet), encoding='utf-8')
        self.source.write_text('Revised source observation.', encoding='utf-8')
        self.packet['sources'][0].update(ref(self.source))
        self.packet['manuscript']['revision'] = 'v02'
        self.packet.update(parent=ref(old), protected_literals=[])
        self.assertTrue(self.run_audit()['checks_passed'])
        old.write_text('Changed old receipt', encoding='utf-8')
        self.assertFalse(self.run_audit()['checks_passed'])

    def test_parent_another_paper_or_same_revision_rejected(self):
        for field in ('paper_id', 'revision'):
            old = copy.deepcopy(self.packet)
            old['manuscript'][field] = 'another-paper' if field == 'paper_id' else 'v01'
            path = self.root / 'old.json'; path.write_text(json.dumps(old), encoding='utf-8')
            self.packet['parent'] = ref(path)
            with self.subTest(field=field), self.assertRaises(audit.PacketError): self.run_audit()

    def test_parent_missing_revision_and_blank_template_are_not_receipts(self):
        old = copy.deepcopy(self.packet); old['manuscript'].pop('revision')
        path = self.root / 'old.json'; path.write_text(json.dumps(old), encoding='utf-8')
        self.packet['parent'] = ref(path); self.packet['manuscript']['revision'] = 'v02'
        with self.assertRaises(audit.PacketError): self.run_audit()
        blank = ROOT / 'templates/manuscript-packet.json'
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(audit.main([str(blank)]), 2)

    def test_literal_presence_does_not_certify_causal_meaning(self):
        self.revise(self.body.replace('observed association', 'proven causal effect'))
        self.assertTrue(self.run_audit()['checks_passed'])
        # A human evidence/claim review must reject this; the script does not parse inference.

    def test_cli_from_other_directory_and_relative_paths(self):
        self.packet['manuscript']['path'] = self.draft.name
        self.packet['sources'][0]['path'] = self.source.name
        path = self.root / 'packet.json'; path.write_text(json.dumps(self.packet), encoding='utf-8')
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(ROOT/'scripts/audit_manuscript.py'), str(path)],
                                cwd=ROOT.parent, capture_output=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['checks_passed'])

    def test_cli_exit_codes_and_invalid_json_are_structured(self):
        path = self.root / 'packet.json'
        for raw in ('null', '[]', '{', '{"schema_version":"1.0","schema_version":"1.0"}', '{"x":NaN}'):
            path.write_text(raw, encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(audit.main([str(path)]), 2)
        path.write_text(json.dumps(self.packet), encoding='utf-8'); self.source.unlink()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(audit.main([str(path)]), 1)


class TextMetricsTests(unittest.TestCase):
    def test_han_excludes_latin_numbers_and_punctuation(self):
        self.assertEqual(metrics.measure('研究ABC-12，结果未改变。', 'han')['count'], 7)

    def test_supplementary_and_compatibility_han_are_counted(self):
        self.assertEqual(metrics.measure('𠀀﨑 A-1', 'han')['count'], 2)

    def test_bounds_include_both_endpoints(self):
        for low, high, okay in ((2, 2, True), (3, 4, False), (0, 1, False)):
            self.assertEqual(metrics.measure('两字', 'han', low, high)['within_limits'], okay)

    def test_whitespace_convention_is_explicit_not_a_journal_claim(self):
        result = metrics.measure('An AI-based result. Two units.', 'whitespace_words')
        self.assertEqual(result['count'], 5)
        self.assertIn('not a universal', result['convention'])

    def test_bad_units_or_bounds_rejected(self):
        for args in (('x', 'words'), ('x', 'han', -1), ('x', 'han', True), ('x', 'han', 3, 2)):
            with self.subTest(args=args), self.assertRaises(ValueError): metrics.measure(*args)

    def test_stdin_empty_and_unreadable_cli(self):
        from unittest.mock import patch
        with patch.object(sys, 'stdin', io.StringIO('两字')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(metrics.main(['-', '--unit', 'han', '--min', '3']), 1)
        with patch.object(sys, 'stdin', io.StringIO('')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(metrics.main(['-', '--unit', 'han', '--min', '0', '--max', '0']), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(metrics.main(['does-not-exist.txt', '--unit', 'han']), 2)


if __name__ == '__main__':
    unittest.main()
