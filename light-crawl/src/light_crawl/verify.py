"""Offline verification of a case's structural contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .models import Phase
from .integrity import case_path, content_hash, fingerprint, tree_records
from .validation import checked_receipt
from .utils import read_json, read_jsonl


SECRET_KEYS = {
    "cookie",
    "cookies",
    "authorization",
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "secret",
    "session",
    "sessionid",
}


@dataclass
class Finding:
    level: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"level": self.level, "code": self.code, "message": self.message}


@dataclass
class VerificationReport:
    case_dir: Path
    slug: str
    phase: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def failures(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.level == "FAIL"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.level == "WARN"]

    @property
    def ok(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict:
        return {
            "case_dir": str(self.case_dir),
            "slug": self.slug,
            "phase": self.phase,
            "ok": self.ok,
            "failures": len(self.failures),
            "warnings": len(self.warnings),
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_secrets(value: object, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in SECRET_KEYS and child not in (None, "", {}, []):
                hits.append(f"{path}.{key}")
            hits.extend(_scan_secrets(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_scan_secrets(child, f"{path}[{index}]"))
    return hits


def verify_case(case_dir: Path) -> VerificationReport:
    case_dir = Path(case_dir).resolve()
    report = VerificationReport(case_dir=case_dir, slug=case_dir.name, phase="UNKNOWN")

    case_file = case_dir / "case.json"
    if not case_file.exists():
        report.findings.append(Finding("FAIL", "case_missing", f"missing {case_file}"))
        return report
    try:
        case = read_json(case_file) or {}
    except (ValueError, OSError) as error:
        report.findings.append(Finding("FAIL", "case_invalid", str(error)))
        return report
    if not isinstance(case, dict) or not isinstance(case.get('target'), dict):
        report.findings.append(Finding('FAIL', 'case_invalid', 'case and target must be objects'))
        return report

    report.slug = str(case.get("slug") or case_dir.name)
    report.phase = str(case.get("phase", "UNKNOWN"))
    if report.phase not in {phase.value for phase in Phase}:
        report.findings.append(Finding("FAIL", "phase_invalid", f"unknown phase: {report.phase}"))

    for name in ("scope.md", "target.json", "evidence.jsonl"):
        if not (case_dir / name).exists():
            report.findings.append(Finding("FAIL", "required_missing", f"missing {name}"))

    target = case.get("target") or {}
    try:
        if read_json(case_dir / 'target.json') != target:
            report.findings.append(Finding('FAIL', 'target_drift', 'target.json differs from the recorded case target'))
    except (ValueError, OSError) as error:
        report.findings.append(Finding('FAIL', 'target_invalid', str(error)))
    if target.get("authorized") is not True:
        report.findings.append(
            Finding("WARN", "authorization_unconfirmed", "target.authorized is not true in case.json")
        )

    try:
        evidence = read_jsonl(case_dir / "evidence.jsonl")
    except (ValueError, OSError) as error:
        report.findings.append(Finding("FAIL", "evidence_invalid", str(error)))
        evidence = []
    if not evidence:
        report.findings.append(Finding("WARN", "evidence_empty", "evidence.jsonl has no entries"))
    identities = set()
    for entry in evidence:
        if not isinstance(entry, dict) or not isinstance(entry.get('evidence_id'), str) or not entry['evidence_id'] or entry['evidence_id'] in identities:
            report.findings.append(Finding('FAIL', 'evidence_identity', 'Missing, malformed or duplicate evidence ID'))
            continue
        identities.add(entry['evidence_id'])
        try:
            reference = entry.get('metadata', {}).get('capture_meta')
            if reference:
                meta = read_json(case_path(case_dir, reference))
                if meta.get('body_path') != entry.get('artifact') or meta.get('sha256') != entry['metadata'].get('sha256'):
                    raise ValueError('Capture evidence and response metadata disagree')
                if fingerprint(case_path(case_dir, meta['body_path'])) != {k: meta.get(k) for k in ('bytes', 'sha256')}:
                    raise ValueError('Captured source changed or disappeared')
        except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
            report.findings.append(Finding('FAIL', 'capture_evidence_invalid', str(error)))

    for name in ("probe.json", "route.json"):
        path = case_dir / name
        if not path.exists():
            report.findings.append(Finding("WARN", "routing_missing", f"missing {name}"))
            continue
        try:
            if not isinstance(read_json(path), dict):
                raise ValueError('Expected an object')
        except (ValueError, OSError) as error:
            report.findings.append(Finding("FAIL", f"{name}_invalid", str(error)))

    artifacts = case.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        report.findings.append(Finding('FAIL', 'artifacts_invalid', 'Expected an artifact mapping'))
        artifacts = {}
    for relative, meta in artifacts.items():
        try:
            path = case_path(case_dir, relative)
            if not isinstance(meta, dict):
                raise ValueError('Expected artifact metadata')
            if path.is_dir():
                if meta.get('kind') != 'directory':
                    report.findings.append(Finding('WARN', 'directory_unsealed', relative))
                else:
                    records = tree_records(path)
                    if records != meta.get('records') or content_hash(records) != meta.get('sha256'):
                        raise ValueError('Directory inventory/hash mismatch')
            else:
                actual = fingerprint(path)
                if not meta.get('sha256'):
                    report.findings.append(Finding('WARN', 'artifact_unsealed', relative))
                elif actual != {k: meta.get(k) for k in ('bytes', 'sha256')}:
                    raise ValueError('File bytes/hash mismatch')
            if meta.get('kind') == 'capture_meta':
                capture = read_json(path)
                body = case_path(case_dir, capture['body_path'])
                if fingerprint(body) != {k: capture.get(k) for k in ('bytes', 'sha256')}:
                    raise ValueError('Captured response differs from its metadata')
                if capture.get('truncated'):
                    report.findings.append(Finding('WARN', 'capture_truncated', relative))
                if not 200 <= capture.get('status', 0) < 300:
                    report.findings.append(Finding('WARN', 'capture_http_error', relative))
        except (ValueError, OSError, TypeError, KeyError) as error:
            report.findings.append(Finding('FAIL', 'artifact_hash_mismatch', f'{relative}: {error}'))

    try:
        if checked_receipt(case_dir) is None:
            report.findings.append(Finding('WARN', 'verification_unrecorded', 'Structural checks only; no executed check receipt'))
    except (ValueError, OSError, TypeError, KeyError) as error:
        report.findings.append(Finding('FAIL', 'verification_invalid', str(error)))

    fixture_dir = case_dir / "fixtures"
    if fixture_dir.exists():
        for fixture in sorted(fixture_dir.rglob("*.json")):
            info = artifacts.get(fixture.relative_to(case_dir).as_posix(), {})
            if not isinstance(info, dict):
                continue
            if info.get('kind') == 'capture_body':
                continue
            try:
                hits = _scan_secrets(read_json(fixture))
            except (ValueError, OSError) as error:
                level = 'WARN' if fixture.name == 'response.json' else 'FAIL'
                report.findings.append(Finding(level, "fixture_invalid", f"{fixture.name}: {error}"))
                continue
            if hits:
                report.findings.append(
                    Finding("WARN", "fixture_secret", f"{fixture.name}: {', '.join(hits[:8])}")
                )

    phase_index = list(Phase).index(Phase(report.phase)) if report.phase in {p.value for p in Phase} else -1
    built_index = list(Phase).index(Phase.BUILT)
    verified_index = list(Phase).index(Phase.VERIFIED)

    if phase_index >= built_index:
        spider_files = list((case_dir / "spider").rglob("*.py")) if (case_dir / "spider").exists() else []
        repro_files = list((case_dir / "repro").rglob("*.py")) if (case_dir / "repro").exists() else []
        if not spider_files and not repro_files:
            report.findings.append(
                Finding("FAIL", "code_missing", "BUILT or later, but spider/ and repro/ contain no Python")
            )
        if not (case_dir / "reports" / "report.md").exists():
            report.findings.append(Finding("WARN", "report_missing", "reports/report.md is missing"))

    if phase_index >= verified_index:
        json_fixtures = list(fixture_dir.rglob("*.json")) if fixture_dir.exists() else []
        if not json_fixtures:
            report.findings.append(
                Finding("FAIL", "fixtures_missing", "VERIFIED or later, but fixtures/ has no JSON file")
            )

    return report


def format_report(report: VerificationReport) -> str:
    lines = [
        f"case={report.slug} phase={report.phase}",
    ]
    for finding in report.findings:
        lines.append(f"{finding.level} {finding.message}")
    result = "PASS" if report.ok else "FAIL"
    lines.append(f"result={result} failures={len(report.failures)} warnings={len(report.warnings)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a light-crawl case contract.")
    parser.add_argument("--case", required=True, help="Case directory.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    report = verify_case(Path(args.case))
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
