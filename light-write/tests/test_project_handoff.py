"""Actual local arithmetic and native handoffs on isolated synthetic material.

No model, journal lookup, real participant data, or semantic-quality grading.
"""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = Path(os.environ.get('LIGHT_ANALYSIS_ROOT', ROOT.parent / 'light-analysis'))
JOURNAL = Path(os.environ.get('LIGHT_JOURNAL_ROOT', ROOT.parent / 'light-journal-select'))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def ref(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def put(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


@unittest.skipUnless((ANALYSIS / 'scripts/analysis_bridge.py').is_file()
                    and (JOURNAL / 'scripts/audit_selection.py').is_file(),
                    'Adjacent Analysis/Journal source is not installed')
class ProjectHandoffTests(unittest.TestCase):
    def setUp(self):
        self.bridge = module('write_native_analysis', ANALYSIS / 'scripts/analysis_bridge.py')
        self.journal = module('write_native_journal', JOURNAL / 'scripts/audit_selection.py')
        self.writer = module('write_native_receipt', ROOT / 'scripts/audit_manuscript.py')
        temp = tempfile.TemporaryDirectory(prefix='write-native-'); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.work = self.base / 'Analysis/AN-0001_合成验证'
        raw = self.base / 'paired.csv'
        raw.write_text(chr(10).join(['unit_id,a,b', 'u1,5,3', 'u2,8,6']), encoding='utf-8')
        self.bridge.ingest([], [raw], self.work)
        plan = self.bridge.read(self.work / 'analysis-plan.json')
        plan.update({k: 'Synthetic interface check, no real research' for k, v in plan.items() if v == ''})
        plan.update(timing='retrospective', sensitivity_branches=[])
        put(self.work / 'analysis-plan.json', plan); self.bridge.freeze_plan(self.work)
        with raw.open(encoding='utf-8', newline='') as stream:
            mean = statistics.mean(float(r['a']) - float(r['b']) for r in csv.DictReader(stream))
        self.assertEqual(mean, 2.0)
        finding = {'finding_id': 'F01', 'claim_refs': [], 'run_refs': [], 'mode': 'descriptive',
            'validity': 'usable', 'validity_basis': 'Known arithmetic, two synthetic paired units',
            'outcome': 'support', 'statement': f'The synthetic mean difference was {mean}.',
            'evidence': [{'input_id': 'S0001', 'locator': 'CSV rows 2-3, a-b'}],
            'estimates': [], 'limitations': ['Synthetic fixture only; no scientific or causal conclusion']}
        item = self.bridge.read(self.work / 'analysis.json')
        item.update(status='complete', data_kind='synthetic_validation', findings=[finding])
        item['loop_decision'].update(route='light-journal-select', finding_ids=['F01'],
            reason='Synthetic native handoff', target_question='Check manuscript adoption',
            next_action='Local handoff test', predictions=[],
            budget={'status': 'not_applicable', 'limit': None, 'basis': 'No new experiment'},
            stop_rule='Stop after test', reentry_condition='Source changes',
            execution_authorization='Local synthetic test only')
        put(self.work / 'analysis.json', item)
        self.report = self.work / 'analysis-report.md'
        self.report.write_text(finding['statement'], encoding='utf-8')
        verified = self.bridge.verify(self.work)
        self.assertTrue(verified['ok'], verified)
        self.bridge.export_handoff(self.work)
        handoff = self.work / 'handoff.json'; self.old_handoff = handoff.read_bytes()
        adopted = self.bridge.read(handoff)
        inputs = list(dict.fromkeys([handoff] + [self.work / s['path'] for s in adopted['sources']]))
        self.selection = json.loads((JOURNAL / 'templates/selection-packet.example.json').read_text(encoding='utf-8'))
        self.selection['research'] = {'basis': 'Synthetic F01, descriptive; native verify/export, no real journal recommendation',
                                     'inputs': [ref(p) for p in inputs]}
        self.selection['decision'].update(status='author_selected', basis='Synthetic test scenario author choice')
        self.selection_path = self.base / 'selection-packet.json'; put(self.selection_path, self.selection)
        self.brief = self.base / 'light-write-brief.md'
        self.brief.write_text('Synthetic target; Research Article; gold_oa; no real selection. Adopt F01 as descriptive only.',
                              encoding='utf-8')
        draft_dir = self.base / 'Write/PAPER-0001_合成验证/drafts/v01'; draft_dir.mkdir(parents=True)
        draft = draft_dir / 'manuscript.md'
        draft.write_text(finding['statement'] + ' This is a two-pair synthetic interface check, not a research result.',
                         encoding='utf-8')
        sources = [{'id': 'A' + str(i), 'role': 'analysis', **ref(p)} for i, p in enumerate(inputs)]
        source_id = next(s['id'] for s in sources if Path(s['path']) == self.report)
        sources += [{'id': 'J1', 'role': 'journal_packet', **ref(self.selection_path)},
                    {'id': 'J2', 'role': 'journal_brief', **ref(self.brief)}]
        self.native_verification = verified
        self.packet = {'schema_version': '1.0',
            'basis': 'Synthetic adoption test; native verification at adoption (recheck before reuse): '
                     + json.dumps(verified, ensure_ascii=False) + '; no semantic certification',
            'manuscript': {'paper_id': 'PAPER-0001', 'revision': 'v01', **ref(draft)},
            'sources': sources,
            'claims': [{'id': 'C1', 'anchor': finding['statement'], 'status': 'supported',
                'boundary': 'Descriptive synthetic arithmetic only',
                'evidence': [{'source_id': source_id, 'locator': 'F01, analysis-report.md paragraph 1'}]}],
            'protected_literals': [{'source_id': source_id, 'text': '2.0'}], 'parent': None}

    def test_native_analysis_journal_write_adoption_is_read_only(self):
        before = {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        selected = self.journal.audit(self.selection, packet_dir=self.base)
        self.assertTrue(selected['handoff']['target_authorized'])
        self.assertTrue(selected['handoff']['evidence_ready'])
        self.assertTrue(self.writer.audit(self.packet, self.base)['checks_passed'])
        self.assertIn(json.dumps(self.native_verification, ensure_ascii=False), self.packet['basis'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()})

    def test_changed_analysis_is_visible_at_all_three_stages_without_rewriting_history(self):
        self.report.write_text('Corrected finding; earlier wording must be reconsidered.', encoding='utf-8')
        self.assertFalse(self.bridge.verify(self.work)['ok'])
        self.assertFalse(self.journal.audit(self.selection, packet_dir=self.base)['handoff']['evidence_ready'])
        self.assertFalse(self.writer.audit(self.packet, self.base)['checks_passed'])
        self.assertEqual(self.old_handoff, (self.work / 'handoff.json').read_bytes())

    def test_changed_journal_brief_invalidates_adopted_draft_not_analysis(self):
        self.brief.write_text('Changed target guidance; reread affected manuscript requirements.', encoding='utf-8')
        self.assertFalse(self.writer.audit(self.packet, self.base)['checks_passed'])
        self.assertTrue(self.bridge.verify(self.work)['ok'])
        self.assertEqual(self.old_handoff, (self.work / 'handoff.json').read_bytes())

    def test_ready_proposal_does_not_become_author_decision(self):
        self.selection['decision'].update(status='proposed', basis='Synthetic unconfirmed recommendation')
        put(self.selection_path, self.selection)
        next(s for s in self.packet['sources'] if s['id'] == 'J1').update(ref(self.selection_path))
        result = self.journal.audit(self.selection, packet_dir=self.base)
        self.assertTrue(result['handoff']['evidence_ready'])
        self.assertFalse(result['handoff']['target_authorized'])
        # Generic drafting remains possible; this packet does not grant submission authority.
        self.assertTrue(self.writer.audit(self.packet, self.base)['checks_passed'])


if __name__ == '__main__':
    unittest.main()
