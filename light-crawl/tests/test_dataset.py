from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from light_crawl.capture import _save_fixtures
from light_crawl.cli import main
from light_crawl.dataset import check_dataset, export_dataset
from light_crawl.models import ProbeResult, TargetProfile
from light_crawl.state import CaseStore, LightCrawlError
from light_crawl.utils import read_json, write_json


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = CaseStore.create(self.root / 'cases', 'data', TargetProfile(url='http://localhost/data', authorized=True))
        write_json(self.store.probe_file, ProbeResult(url=self.store.target.url, status=200).to_dict())
        self.raw = self.capture()
        self.spec = {'purpose': 'Evaluate a known-answer fixture, not a research discovery', 'intent': 'research_input',
            'selection': {'unit': 'synthetic record', 'inclusion': 'all supplied rows', 'exclusion': 'none', 'time_range': 'not applicable'},
            'fields': [{'name': 'value', 'meaning': 'known synthetic response', 'unit': 'arbitrary', 'missing': 'no missing values in fixture'}],
            'coverage': {'expected_records': 3, 'obtained_records': 3, 'missingness': 'none', 'duplicates': 'none', 'failures': []},
            'limitations': ['Synthetic fixture; no population claim'],
            'files': [{'id': 'raw', 'role': 'raw', 'path': self.raw.body_path.relative_to(self.store.directory).as_posix(), 'evidence_ids': ['E0001']}]}
        self.spec_path = self.root / 'spec.json'
        self.out = self.root / 'dataset-v01.json'

    def capture(self, **kwargs):
        return _save_fixtures(self.store, url=self.store.target.url, final_url=self.store.target.url, status=kwargs.pop('status', 200),
            headers={}, content_type='application/json', body=json.dumps([1, 2, 3]).encode(),
            elapsed_ms=1, request_headers={}, engine='http', **kwargs)

    def export(self):
        write_json(self.spec_path, self.spec)
        return export_dataset(self.store, self.spec_path, self.out)

    def test_export_roundtrip(self):
        result = self.export()
        self.assertTrue(result['ok'])
        self.assertTrue(check_dataset(self.out)['ok'])
        self.assertEqual(read_json(self.out)['files'][0]['sha256'], self.raw.sha256)

    def test_previous_export_not_overwritten(self):
        self.export()
        original = self.out.read_bytes()
        with self.assertRaises(LightCrawlError):
            self.export()
        self.assertEqual(self.out.read_bytes(), original)

    def test_new_capture_keeps_old_handoff_valid(self):
        self.export()
        self.capture()
        self.assertTrue(check_dataset(self.out)['ok'])

    def test_changed_raw_cannot_be_reblessed_at_export(self):
        self.raw.body_path.write_text('[]', encoding='utf-8')
        with self.assertRaises(LightCrawlError):
            self.export()
        self.assertFalse(self.out.exists())

    def test_changed_file_invalidates_handoff(self):
        self.export()
        self.raw.body_path.write_text('[]', encoding='utf-8')
        self.assertFalse(check_dataset(self.out)['ok'])

    def test_source_evidence_correction_invalidates_handoff(self):
        self.export()
        entries = self.store.evidence()
        entries[0]['observation'] = 'corrected source identity'
        self.store.evidence_file.write_text(''.join(json.dumps(e) + '\n' for e in entries), encoding='utf-8')
        self.assertFalse(check_dataset(self.out)['ok'])

    def test_missing_source_case_is_explicit_warning(self):
        self.export()
        packet = read_json(self.out)
        packet['case_dir'] = str(self.root / 'not-available')
        write_json(self.out, packet)
        result = check_dataset(self.out)
        self.assertTrue(result['ok'])
        self.assertTrue(result['warnings'])

    def test_truncated_response_is_diagnostic_only(self):
        result = self.capture(truncated=True)
        self.spec['files'][0].update(path=result.body_path.relative_to(self.store.directory).as_posix(), evidence_ids=['E0002'])
        with self.assertRaises(LightCrawlError):
            self.export()
        self.spec['intent'] = 'diagnostic'
        self.assertTrue(self.export()['ok'])
        self.assertTrue(check_dataset(self.out)['warnings'])

    def test_error_page_is_diagnostic_only(self):
        result = self.capture(status=403)
        self.spec['files'][0].update(path=result.body_path.relative_to(self.store.directory).as_posix(), evidence_ids=['E0002'])
        with self.assertRaises(LightCrawlError):
            self.export()

    def test_unknown_source_rejected(self):
        self.spec['files'][0]['evidence_ids'] = ['E9999']
        with self.assertRaises(LightCrawlError):
            self.export()

    def test_capture_source_cannot_be_assigned_to_other_file(self):
        external = self.root / 'unrelated.json'
        external.write_text('[9]', encoding='utf-8')
        self.spec['files'][0]['path'] = str(external)
        with self.assertRaises(LightCrawlError):
            self.export()

    def test_derived_data_needs_real_source_and_code_files(self):
        code = self.root / 'compute.py'
        code.write_text('print(2)', encoding='utf-8')
        data = self.root / 'mean.csv'
        data.write_text('mean\n2\n', encoding='utf-8')
        self.spec['files'].extend([{'id': 'code', 'role': 'code', 'path': str(code)},
            {'id': 'mean', 'role': 'derived', 'path': str(data), 'input_ids': ['raw', 'code'],
             'command': 'python compute.py', 'environment': 'fixture only; command registration is not proof of execution'}])
        self.assertTrue(self.export()['ok'])
        code.write_text('print(9)', encoding='utf-8')
        self.assertFalse(check_dataset(self.out)['ok'])

    def test_cycle_is_rejected_before_export(self):
        a, b = self.root / 'a.py', self.root / 'b.py'
        a.write_text('pass', encoding='utf-8')
        b.write_text('pass', encoding='utf-8')
        self.spec['files'].extend([{'id': 'a', 'role': 'code', 'path': str(a), 'input_ids': ['b']},
                                  {'id': 'b', 'role': 'code', 'path': str(b), 'input_ids': ['a']}])
        with self.assertRaises(LightCrawlError):
            self.export()
        self.assertFalse(self.out.exists())

    def test_nonfinite_spec_does_not_leave_partial_export(self):
        self.spec['invalid'] = float('nan')
        with self.assertRaises(LightCrawlError):
            self.export()
        self.assertFalse(self.out.exists())

    def test_cli_export_and_check(self):
        write_json(self.spec_path, self.spec)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['dataset', 'export', str(self.store.directory), '--spec', str(self.spec_path), '--out', str(self.out)]), 0)
            self.assertEqual(main(['dataset', 'check', str(self.out)]), 0)

    def test_manual_evidence_cannot_bypass_truncated_snapshot(self):
        result = self.capture(truncated=True)
        entry = self.store.add_evidence(phase='CAPTURED', source='operator', action='note', observation='diagnostic only')
        self.spec['files'][0].update(path=result.body_path.relative_to(self.store.directory).as_posix(), evidence_ids=[entry.evidence_id])
        with self.assertRaises(LightCrawlError):
            self.export()

    def test_changed_capture_metadata_invalidates_export(self):
        self.export()
        meta = read_json(self.raw.meta_path)
        meta['status'] = 403
        write_json(self.raw.meta_path, meta)
        self.assertFalse(check_dataset(self.out)['ok'])

    def test_exported_research_metadata_cannot_change_silently(self):
        self.export()
        packet = read_json(self.out)
        packet['spec']['selection']['unit'] = 'different research unit'
        write_json(self.out, packet)
        self.assertFalse(check_dataset(self.out)['ok'])


if __name__ == '__main__':
    unittest.main()
