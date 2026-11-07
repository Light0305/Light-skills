"""Execute an explicitly selected local check and bind it to its actual inputs."""
from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

from .integrity import case_path, fingerprint
from .state import CaseStore, LightCrawlError
from .utils import read_json, read_jsonl, utc_now, write_json


def check_inputs(root: Path) -> dict:
    files = [root / name for name in ('scope.md', 'target.json', 'probe.json', 'route.json') if (root / name).exists()]
    for name in ('repro', 'spider', 'fixtures'):
        files.extend(p for p in (root / name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {p.relative_to(root).as_posix(): fingerprint(p) for p in sorted(files)}


def run_check(store: CaseStore, script: str, timeout: int = 60) -> dict:
    try:
        path = case_path(store.directory, script)
        if path.suffix != '.py' or path.parts[-2] not in ('repro', 'spider', 'fixtures'):
            raise ValueError('Select a Python check directly inside repro/, spider/ or fixtures/')
        fingerprint(path)
        before = check_inputs(store.directory)
    except (ValueError, OSError) as error:
        raise LightCrawlError(str(error)) from error
    folder = store.reports_dir / 'checks' / ('CHK-' + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-B', str(path.resolve())]
    started = utc_now()
    try:
        with (folder / 'stdout.log').open('xb') as out, (folder / 'stderr.log').open('xb') as err:
            try:
                result = subprocess.run(command, cwd=store.directory.resolve(), stdout=out, stderr=err,
                    timeout=max(1, timeout), check=False)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
            except OSError as error:
                err.write(str(error).encode('utf-8'))
                code = 127
        unchanged = before == check_inputs(store.directory)
    except (ValueError, OSError):
        unchanged = False
        code = 125
    receipt = {'schema_version': 1, 'case_id': store.state.case_id, 'kind': 'controlled_check',
        'command': command, 'started_at': started, 'finished_at': utc_now(), 'returncode': code,
        'inputs': before, 'inputs_unchanged': unchanged, 'passed': code == 0 and unchanged,
        'logs': {p.name: fingerprint(p) for p in (folder / 'stdout.log', folder / 'stderr.log')}}
    receipt_path = folder / 'receipt.json'
    write_json(receipt_path, receipt)
    write_json(store.reports_dir / 'verification.json',
        {'path': receipt_path.relative_to(store.directory).as_posix(), **fingerprint(receipt_path)})
    store.add_evidence(phase=store.state.phase, source='light-crawl verify', action='execute selected local check',
        observation=f'returncode={code}; inputs_unchanged={unchanged}', artifact=receipt_path.relative_to(store.directory).as_posix(),
        metadata={'kind': 'controlled_check', 'passed': receipt['passed']})
    return receipt


def checked_receipt(root: Path) -> dict | None:
    pointer = read_json(root / 'reports/verification.json')
    if pointer is None:
        return None
    if not isinstance(pointer, dict):
        raise ValueError('Invalid verification pointer')
    history = [r for r in read_jsonl(root / 'evidence.jsonl') if isinstance(r, dict) and r.get('source') == 'light-crawl verify']
    if not history or history[-1].get('artifact') != pointer.get('path'):
        raise ValueError('Verification pointer does not identify the latest executed check')
    path = case_path(root, pointer.get('path', ''))
    if fingerprint(path) != {k: pointer.get(k) for k in ('bytes', 'sha256')}:
        raise ValueError('Verification receipt changed')
    receipt = read_json(path)
    if not isinstance(receipt, dict) or receipt.get('schema_version') != 1:
        raise ValueError('Invalid verification receipt')
    case = read_json(root / 'case.json')
    if not isinstance(case, dict) or receipt.get('case_id') != case.get('case_id') or receipt.get('kind') != 'controlled_check':
        raise ValueError('Verification receipt belongs to a different case/check')
    if receipt.get('passed') is not True or receipt.get('returncode') != 0 or receipt.get('inputs_unchanged') is not True:
        raise ValueError('Recorded check failed or its inputs changed during execution')
    if receipt.get('inputs') != check_inputs(root):
        raise ValueError('Verification is stale: code, fixtures or acquisition scope changed')
    if not isinstance(receipt.get('logs'), dict):
        raise ValueError('Invalid verification log records')
    for name in ('stdout.log', 'stderr.log'):
        if fingerprint(path.parent / name) != receipt.get('logs', {}).get(name):
            raise ValueError('Verification execution log changed')
    return receipt
