'''Integration with the adjacent source Analysis API on isolated synthetic data.'''
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import unittest
from test_packet_v11 import MODULE, packet

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = Path(os.environ.get('LIGHT_ANALYSIS_ROOT', ROOT.parent / 'light-anaysis'))


@unittest.skipUnless((ANALYSIS / 'scripts/analysis_bridge.py').is_file(), 'Adjacent Analysis source not available')
class AnalysisHandoffTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('journal_native_analysis', ANALYSIS / 'scripts/analysis_bridge.py')
        self.bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.bridge)
        temp = tempfile.TemporaryDirectory(prefix='journal-native-'); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.work = self.base / 'Analysis' / 'AN-0001_合成验证'
        self.raw = self.base / 'paired.csv'
        self.raw.write_text(chr(10).join(['unit_id,a,b', 'u1,5,3', 'u2,8,6']), encoding='utf-8')
        self.bridge.ingest([], [self.raw], self.work)
        plan = self.bridge.read(self.work / 'analysis-plan.json')
        plan.update({k: 'Synthetic plumbing check, not a scientific experiment' for k, v in plan.items() if v == ''})
        plan.update(timing='retrospective', sensitivity_branches=[])
        self.put(self.work / 'analysis-plan.json', plan); self.bridge.freeze_plan(self.work)
        with self.raw.open(encoding='utf-8', newline='') as stream:
            differences = [float(r['a']) - float(r['b']) for r in csv.DictReader(stream)]
        self.assertEqual(statistics.mean(differences), 2.0)
        item = self.bridge.read(self.work / 'analysis.json')
        item.update(status='complete', data_kind='synthetic_validation')
        item['findings'] = [{'finding_id': 'F01', 'claim_refs': [], 'run_refs': [], 'mode': 'descriptive',
            'validity': 'usable', 'validity_basis': 'Known arithmetic answer, two synthetic paired units',
            'outcome': 'support', 'statement': f'Synthetic mean difference={statistics.mean(differences)}',
            'evidence': [{'input_id': 'S0001', 'locator': 'CSV rows 2-3, paired a-b'}],
            'estimates': [], 'limitations': ['Synthetic fixture only; no real study or causal inference']}]
        item['loop_decision'].update(route='light-journal-select', finding_ids=['F01'], reason='Test actual handoff',
            target_question='Check source and version plumbing', next_action='Synthetic selection audit', predictions=[],
            budget={'status': 'not_applicable', 'limit': None, 'basis': 'No new experiment'},
            stop_rule='Stop after local test', reentry_condition='Source changes', execution_authorization='Local synthetic test only')
        self.put(self.work / 'analysis.json', item)
        (self.work / 'analysis-report.md').write_text(item['findings'][0]['statement'], encoding='utf-8')
        self.assertTrue(self.bridge.verify(self.work)['ok'])
        self.bridge.export_handoff(self.work)
        self.handoff = self.work / 'handoff.json'; self.original_handoff = self.handoff.read_bytes()
        source = self.bridge.read(self.handoff)
        self.value = packet()
        self.value['research']['basis'] = f"Synthetic {source['analysis_id']}, F01, descriptive; actual native verify/export, no research claim."
        paths = [self.handoff] + [self.work / r['path'] for r in source['sources']]
        self.value['research']['inputs'] = [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]

    def put(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def test_native_analysis_to_journal_cli_from_other_cwd(self):
        target = self.base / 'Journal'; target.mkdir()
        path = target / 'selection-packet.json'; self.put(path, self.value)
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(ROOT / 'scripts/audit_selection.py'), str(path)],
                                cwd=self.base, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report['input_integrity'], 'matched')
        self.assertFalse(report['handoff']['target_authorized'])
        self.assertEqual(self.original_handoff, self.handoff.read_bytes())

    def test_report_change_invalidates_native_and_journal_without_changing_old_export(self):
        (self.work / 'analysis-report.md').write_text('Changed interpretation', encoding='utf-8')
        self.assertFalse(self.bridge.verify(self.work)['ok'])
        report = MODULE.audit(self.value, packet_dir=self.base)
        self.assertFalse(report['valid'])
        self.assertFalse(report['handoff']['evidence_ready'])
        self.assertEqual(self.original_handoff, self.handoff.read_bytes())

    def test_unlisted_dependency_is_not_claimed_as_verified(self):
        self.value['research']['inputs'] = self.value['research']['inputs'][:1]
        (self.work / 'analysis-report.md').write_text('Changed report not listed in Journal', encoding='utf-8')
        self.assertFalse(self.bridge.verify(self.work)['ok'])
        self.assertTrue(MODULE.audit(self.value, packet_dir=self.base)['valid'])
        # This proves the documented boundary: the native verify is still required.
