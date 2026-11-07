"""Known-answer local HTTP acquisition through the real standalone Analysis entrypoint."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT.parent / 'light-anaysis/scripts/analysis_bridge.py'
sys.path.insert(0, str(ROOT / 'src'))
from light_crawl.cli import main
from light_crawl.dataset import check_dataset
from light_crawl.state import CaseStore
from light_crawl.utils import read_json, write_json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps([{'id': i, 'value': i} for i in (1, 2, 3)]).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@unittest.skipUnless(ANALYSIS.is_file(), 'Optional sibling Analysis source is not present')
class ResearchFlowTests(unittest.TestCase):
    def test_acquire_compute_export_and_native_analysis_intake(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = root / 'Acquisition/ACQ-0001/case'
                url = f'http://127.0.0.1:{server.server_port}/data'
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['new-case', 'case', '--case-root', str(case.parent), '--target', url, '--authorized']), 0)
                    self.assertEqual(main(['probe', str(case)]), 0)
                    self.assertEqual(main(['route', str(case)]), 0)
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(['capture', str(case), '--json']), 0)
                raw = Path(json.loads(output.getvalue())['capture']['body_path'])
                source = raw.read_bytes()
                (case / 'data').mkdir()
                code = case / 'repro/verify.py'
                code.write_text('import json, csv, statistics\nfrom pathlib import Path\n' +
                    'rows = json.loads(Path(' + repr(str(raw)) + ').read_text())\n' +
                    'assert len(rows) == 3 and statistics.mean(r["value"] for r in rows) == 2\n' +
                    'with Path("data/values.csv").open("w", newline="") as f:\n' +
                    '    writer = csv.DictWriter(f, fieldnames=["id", "value"]); writer.writeheader(); writer.writerows(rows)\n', encoding='utf-8')
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['verify', str(case), '--run-check', 'repro/verify.py']), 0)
                    self.assertEqual(main(['advance', str(case), 'VERIFIED', '--note', 'known-answer local check; not a public-site validation']), 0)
                store = CaseStore.load(case)
                capture_id = [e['evidence_id'] for e in store.evidence() if e['source'] == 'light-crawl capture'][0]
                spec = {'purpose': 'Local known-answer acquisition-to-analysis test', 'intent': 'research_input',
                    'selection': {'unit': 'synthetic record', 'inclusion': 'fixture rows 1-3', 'exclusion': 'none', 'time_range': 'not applicable'},
                    'fields': [{'name': 'value', 'meaning': 'known fixture response', 'unit': 'arbitrary', 'missing': 'none'}],
                    'coverage': {'expected_records': 3, 'obtained_records': 3, 'missingness': 'none', 'duplicates': 'none', 'failures': []},
                    'limitations': ['Synthetic values; no empirical or population claim'],
                    'files': [{'id': 'raw', 'role': 'raw', 'path': str(raw), 'evidence_ids': [capture_id]},
                        {'id': 'extract', 'role': 'code', 'path': str(code)},
                        {'id': 'values', 'role': 'derived', 'path': str(case / 'data/values.csv'),
                         'input_ids': ['raw', 'extract'], 'command': 'python -B repro/verify.py', 'environment': sys.version}]}
                spec_file, packet = root / 'spec.json', case / 'reports/dataset-v01.json'
                write_json(spec_file, spec)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['dataset', 'export', str(case), '--spec', str(spec_file), '--out', str(packet)]), 0)
                self.assertTrue(check_dataset(packet)['ok'])
                analysis = root / 'Analysis/AN-0001'
                command = [sys.executable, '-X', 'utf8', '-B', str(ANALYSIS), 'ingest', '--out', str(analysis)]
                for item in (packet, raw, code, case / 'data/values.csv'):
                    command.extend(['--input', str(item)])
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                context = read_json(analysis / 'context.json')
                self.assertEqual(len(context['inputs']), 4)
                self.assertEqual(context['executions'], [])
                self.assertEqual(raw.read_bytes(), source)
                verified = subprocess.run([sys.executable, '-B', str(ANALYSIS), 'verify', '--workspace', str(analysis)],
                    capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
                self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
                self.assertTrue(json.loads(verified.stdout)['ok'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
