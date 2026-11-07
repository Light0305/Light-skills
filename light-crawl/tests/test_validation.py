from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from light_crawl.adapters import scrapling
from light_crawl.learn import learn_case
from light_crawl.models import Phase, TargetProfile
from light_crawl.state import CaseStore, LightCrawlError
from light_crawl.validation import checked_receipt, run_check
from light_crawl.verify import verify_case
from light_crawl.utils import read_json, write_json


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = CaseStore.create(self.root / 'cases', 'validation', TargetProfile(url='http://localhost', authorized=True))
        self.script = self.store.repro_dir / 'verify.py'
        self.script.write_text('from pathlib import Path\nassert Path("fixtures/request.json").read_text() == "{}"\n', encoding='utf-8')
        (self.store.fixtures_dir / 'request.json').write_text('{}', encoding='utf-8')

    def test_real_check_records_inputs_and_execution(self):
        self.assertTrue(run_check(self.store, 'repro/verify.py')['passed'])
        self.assertTrue(checked_receipt(self.store.directory)['passed'])
        self.assertTrue(verify_case(self.store.directory).ok)

    def test_failed_check_is_not_verified(self):
        self.script.write_text('raise SystemExit(3)', encoding='utf-8')
        result = run_check(self.store, 'repro/verify.py')
        self.assertFalse(result['passed'])
        self.assertEqual(result['returncode'], 3)
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_code_change_invalidates_receipt(self):
        run_check(self.store, 'repro/verify.py')
        self.script.write_text('pass', encoding='utf-8')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_fixture_change_invalidates_receipt(self):
        run_check(self.store, 'repro/verify.py')
        (self.store.fixtures_dir / 'request.json').write_text('[]', encoding='utf-8')
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_check_cannot_change_its_own_inputs(self):
        self.script.write_text('from pathlib import Path\nPath("fixtures/request.json").write_text("[]")\n', encoding='utf-8')
        self.assertFalse(run_check(self.store, 'repro/verify.py')['passed'])
        self.assertFalse(verify_case(self.store.directory).ok)

    def test_timeout_is_recorded_as_failure(self):
        self.script.write_text('import time; time.sleep(3)', encoding='utf-8')
        result = run_check(self.store, 'repro/verify.py', timeout=1)
        self.assertEqual(result['returncode'], 124)
        self.assertFalse(result['passed'])

    def test_old_phase_label_cannot_promote_unchecked_pack(self):
        self.store.advance(Phase.VERIFIED, 'label only')
        with self.assertRaises(LightCrawlError):
            learn_case(self.store, self.root / 'sites')
        self.assertFalse((self.root / 'sites').exists())

    def test_new_check_preserves_previous_receipt(self):
        run_check(self.store, 'repro/verify.py')
        old = list((self.store.reports_dir / 'checks').glob('*/receipt.json'))[0]
        original = old.read_bytes()
        run_check(self.store, 'repro/verify.py')
        self.assertEqual(old.read_bytes(), original)
        self.assertEqual(len(list((self.store.reports_dir / 'checks').glob('*/receipt.json'))), 2)

    def test_empty_scrapling_version_output_is_not_a_crash(self):
        with patch.object(scrapling, 'find_cli', return_value='fixture'), patch.object(scrapling.subprocess, 'run',
                return_value=subprocess.CompletedProcess(['fixture'], 0, stdout='', stderr='')):
            self.assertEqual(scrapling.version(), '')

    def test_pointer_cannot_hide_the_latest_failed_check(self):
        run_check(self.store, 'repro/verify.py')
        pointer = self.store.reports_dir / 'verification.json'
        first = read_json(pointer)
        with patch('light_crawl.validation.subprocess.run', return_value=subprocess.CompletedProcess(['fixture'], 1)):
            self.assertFalse(run_check(self.store, 'repro/verify.py')['passed'])
        write_json(pointer, first)
        self.assertFalse(verify_case(self.store.directory).ok)


if __name__ == '__main__':
    unittest.main()
