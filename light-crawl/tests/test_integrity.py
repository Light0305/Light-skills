from __future__ import annotations

import json
import sys
import tempfile
import unittest
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from light_crawl.capture import _save_fixtures, capture_target
from light_crawl.cli import main
from light_crawl.models import Phase, ProbeResult, TargetProfile
from light_crawl.report import render_report
from light_crawl.site import run_site_pack
from light_crawl.state import CaseStore, LightCrawlError
from light_crawl.utils import write_json
from light_crawl.verify import verify_case


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = CaseStore.create(self.root / 'cases', 'research',
            TargetProfile(url='http://127.0.0.1/data', authorized=True))
        write_json(self.store.probe_file, ProbeResult(url=self.store.target.url, status=200).to_dict())

    def capture(self, body=b'{}'):
        return _save_fixtures(self.store, url=self.store.target.url, final_url=self.store.target.url,
            status=200, headers={}, content_type='application/json', body=body,
            elapsed_ms=1, request_headers={}, engine='http')

    def test_capture_retains_previous_raw_response(self):
        first = self.capture()
        second = self.capture(b'[]')
        self.assertNotEqual(first.body_path, second.body_path)
        self.assertEqual(first.body_path.read_bytes(), b'{}')

    def test_modified_capture_fails_verification(self):
        result = self.capture()
        result.body_path.write_bytes(b'[]')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_empty_response_has_real_sha256(self):
        result = self.capture(b'')
        self.assertEqual(len(result.sha256), 64)

    def test_capture_requires_authorization_before_io(self):
        self.store.state.target['authorized'] = False
        self.store.save()
        with patch('light_crawl.capture._capture_http') as acquire:
            with self.assertRaises(LightCrawlError):
                capture_target(self.store)
            acquire.assert_not_called()

    def test_probe_requires_authorization_before_io(self):
        self.store.state.target['authorized'] = False
        self.store.save()
        with patch('light_crawl.cli.probe_target') as acquire:
            code = main(['probe', str(self.store.directory), '--json'])
            self.assertEqual(code, 2)
            acquire.assert_not_called()

    def test_artifact_versions_do_not_overwrite(self):
        source = self.root / 'sample.txt'
        source.write_text('first', encoding='utf-8')
        first = self.store.add_artifact(source, 'sample')
        source.write_text('second', encoding='utf-8')
        second = self.store.add_artifact(source, 'sample')
        self.assertNotEqual(first, second)
        self.assertEqual((self.store.directory / first).read_text(encoding='utf-8'), 'first')

    def test_directory_artifact_change_is_detected(self):
        folder = self.root / 'bundle'
        folder.mkdir()
        (folder / 'raw.txt').write_text('original', encoding='utf-8')
        ref = self.store.add_artifact(folder)
        (self.store.directory / ref / 'raw.txt').write_text('changed', encoding='utf-8')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_artifact_path_cannot_escape_case(self):
        self.store.state.artifacts['../outside.txt'] = {'sha256': '', 'bytes': 1}
        (self.store.directory.parent / 'outside.txt').write_text('x', encoding='utf-8')
        self.store.save()
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_malformed_case_is_a_finding(self):
        self.store.case_file.write_text('[1]', encoding='utf-8')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_duplicate_evidence_id_fails(self):
        entry = self.store.add_evidence(phase='CAPTURED', source='test', action='read', observation='data')
        with self.store.evidence_file.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(entry.to_dict()) + '\n')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_phase_label_does_not_claim_executed_verification(self):
        self.store.advance(Phase.VERIFIED, 'operator label only')
        self.assertNotIn('Verified against fixtures or a controlled replay.', render_report(self.store))

    def test_stale_site_output_is_not_reused(self):
        pack = self.root / 'pack'
        (pack / 'spider').mkdir(parents=True)
        write_json(pack / 'site.json', {'run': {'expected_items': 1}})
        write_json(pack / 'spider/site.json', {})
        (pack / 'spider/spider.py').write_text('pass', encoding='utf-8')
        output = self.root / 'old.jsonl'
        old = json.dumps({'id': 1}) + '\n'
        output.write_text(old, encoding='utf-8')
        with self.assertRaises(LightCrawlError):
            run_site_pack(pack, output=output, verify=False)
        self.assertEqual(output.read_text(encoding='utf-8'), old)

    def test_reprobe_and_reroute_keep_original_evidence(self):
        with patch('light_crawl.cli.probe_target', return_value=ProbeResult(url=self.store.target.url, status=200)), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['probe', str(self.store.directory)]), 0)
            self.assertEqual(main(['route', str(self.store.directory)]), 0)
            first = CaseStore.load(self.store.directory).evidence()
            paths = [self.store.directory / row['artifact'] for row in first]
            old = [p.read_bytes() for p in paths]
            self.store = CaseStore.load(self.store.directory)
            self.capture()
            self.assertEqual(main(['probe', str(self.store.directory)]), 0)
            self.assertEqual(main(['route', str(self.store.directory), '--lane', 'L0_API']), 0)
        current = CaseStore.load(self.store.directory)
        self.assertEqual(current.state.phase, 'CAPTURED')
        self.assertEqual(current.state.lane, 'L0_API')
        self.assertEqual([p.read_bytes() for p in paths], old)

    def test_failed_probe_returns_failure_status(self):
        with patch('light_crawl.cli.probe_target', return_value=ProbeResult(url=self.store.target.url, error='fixture timeout')), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['probe', str(self.store.directory)]), 1)

    def test_removing_registry_cannot_hide_changed_raw_evidence(self):
        result = self.capture()
        self.store.state.artifacts.clear()
        self.store.save()
        result.body_path.write_text('[]', encoding='utf-8')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_nonboolean_authorization_is_not_truthy_permission(self):
        self.store.state.target['authorized'] = 'false'
        self.assertFalse(self.store.target.authorized)


if __name__ == '__main__':
    unittest.main()
