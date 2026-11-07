"""Run a tracked site pack with controlled arguments."""

from __future__ import annotations

import json
import csv
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import LightCrawlError
from .utils import read_json, slugify, utc_now, write_json


@dataclass
class SitePackInfo:
    path: Path
    domain: str
    lane: str
    delivery: str
    expected_items: int | None
    has_spider: bool
    has_verify: bool
    notes: str
    schema_version: int = 1
    version: int = 1
    last_verified_at: str = ""
    age_days: int | None = None
    stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "domain": self.domain,
            "lane": self.lane,
            "delivery": self.delivery,
            "expected_items": self.expected_items,
            "has_spider": self.has_spider,
            "has_verify": self.has_verify,
            "notes": self.notes,
            "schema_version": self.schema_version,
            "version": self.version,
            "last_verified_at": self.last_verified_at,
            "age_days": self.age_days,
            "stale": self.stale,
        }


@dataclass
class SiteRunResult:
    pack: Path
    output: Path
    command: list[str]
    returncode: int
    items: int
    expected_items: int | None
    verify_returncode: int | None
    passed: bool
    stdout: str
    stderr: str
    started_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack": str(self.pack),
            "output": str(self.output),
            "command": self.command,
            "returncode": self.returncode,
            "items": self.items,
            "expected_items": self.expected_items,
            "verify_returncode": self.verify_returncode,
            "passed": self.passed,
            "stdout_tail": self.stdout[-4000:],
            "stderr_tail": self.stderr[-4000:],
            "started_at": self.started_at,
        }


def _age_days(value: str) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - parsed).days)


def read_site_pack_info(pack: Path, *, stale_days: int = 30) -> SitePackInfo:
    pack = Path(pack).resolve()
    site_file = pack / "site.json"
    if not site_file.is_file():
        raise LightCrawlError(f"Site pack is missing site.json: {pack}")
    data = read_json(site_file, default={}) or {}
    run_config = data.get("run", {}) or {}
    expected_raw = run_config.get("expected_items")
    last_verified = str(data.get("last_verified_at") or "")
    age = _age_days(last_verified)
    return SitePackInfo(
        path=pack,
        domain=str(data.get("domain") or pack.name),
        lane=str(data.get("lane") or "unrouted"),
        delivery=str(data.get("delivery") or "unknown"),
        expected_items=int(expected_raw) if expected_raw is not None else None,
        has_spider=(pack / "spider" / "spider.py").exists(),
        has_verify=(pack / "verify.py").exists(),
        notes=str(data.get("notes") or ""),
        schema_version=int(data.get("schema_version", 1) or 1),
        version=int(data.get("version", 1) or 1),
        last_verified_at=last_verified,
        age_days=age,
        stale=age is None or age > stale_days,
    )


def list_site_packs(
    root: Path = Path("examples/site-packs"),
    *,
    stale_days: int = 30,
) -> list[SitePackInfo]:
    root = Path(root)
    if not root.exists():
        raise LightCrawlError(f"Site-pack root not found: {root}")
    packs: list[SitePackInfo] = []
    for entry in sorted(root.iterdir()):
        if (entry / "site.json").is_file():
            packs.append(read_site_pack_info(entry, stale_days=stale_days))
    return packs


def check_site_pack(pack: Path, *, write: bool = False, timeout: int = 120) -> dict[str, Any]:
    pack = Path(pack).resolve()
    site_file = pack / "site.json"
    if not site_file.is_file():
        raise LightCrawlError(f"Site pack is missing site.json: {pack}")
    verify_script = pack / "verify.py"
    if not verify_script.exists():
        raise LightCrawlError(f"Site pack has no verify.py: {pack}")

    started = time.perf_counter()
    try:
        completed = _run([runtime_python(), str(verify_script)], pack, timeout)
    except subprocess.TimeoutExpired as error:
        raise LightCrawlError(f"site check timed out after {timeout}s: {pack}") from error

    passed = completed.returncode == 0
    checked_at = utc_now()
    if passed and write:
        data = read_json(site_file, default={}) or {}
        data["last_verified_at"] = checked_at
        data["version"] = int(data.get("version", 1) or 1)
        write_json(site_file, data)

    return {
        "pack": str(pack),
        "passed": passed,
        "returncode": completed.returncode,
        "checked_at": checked_at,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "wrote_timestamp": bool(passed and write),
        "stdout_tail": (completed.stdout or "")[-2000:],
        "stderr_tail": (completed.stderr or "")[-2000:],
    }


def runtime_python() -> str:
    """Prefer the user-level runtime Python over whatever launched the CLI."""

    home = Path(os.environ.get("LIGHT_CRAWL_HOME") or (Path.home() / ".light-crawl"))
    candidates = (
        home / "venv" / "Scripts" / "python.exe",
        home / "venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _count_items(path: Path) -> int:
    if not path.exists():
        raise ValueError('Spider did not produce an output file')
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        count = 0
        with path.open(encoding='utf-8-sig') as stream:
            for line in stream:
                if line.strip():
                    if not isinstance(json.loads(line), dict):
                        raise ValueError('JSONL records must be objects')
                    count += 1
        return count
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            for key in ("items", "data", "results"):
                value = data.get(key)
                if isinstance(value, list):
                    return len(value)
        return 1
    if suffix == ".csv":
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = csv.DictReader(stream, strict=True)
            fields = rows.fieldnames
            if not fields or len(fields) != len(set(fields)):
                raise ValueError('CSV needs unique field names')
            count = 0
            for row in rows:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError('CSV row does not match its header')
                count += 1
            return count
    if suffix == ".xml":
        text = path.read_text(encoding="utf-8")
        return text.count("<item")
    return 0


def _run(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=max(10, timeout),
        check=False,
    )


def run_site_pack(
    pack: Path,
    *,
    output: Path,
    max_pages: int | None = None,
    crawldir: Path | None = None,
    verify: bool = True,
    timeout: int = 300,
) -> SiteRunResult:
    pack = Path(pack).resolve()
    site_file = pack / "site.json"
    spider_script = pack / "spider" / "spider.py"
    spider_config = pack / "spider" / "site.json"

    if not site_file.exists():
        raise LightCrawlError(f"Site pack is missing site.json: {pack}")
    if not spider_script.exists() or not spider_config.exists():
        raise LightCrawlError(
            f"Site pack needs spider/spider.py and spider/site.json: {pack}"
        )

    site = read_json(site_file, default={}) or {}
    run_config = site.get("run", {}) or {}
    expected_raw = run_config.get("expected_items")
    expected_items = int(expected_raw) if expected_raw is not None else None

    output = Path(output).resolve()
    if output.exists():
        raise LightCrawlError(f'Output already exists; select a new run output: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        runtime_python(),
        str(spider_script),
        "--config",
        str(spider_config),
        "--out",
        str(output),
    ]
    if max_pages is not None:
        command.extend(["--max-pages", str(max_pages)])
    if crawldir is not None:
        command.extend(["--crawldir", str(Path(crawldir).resolve())])

    started_at = utc_now()
    try:
        completed = _run(command, pack, timeout)
    except subprocess.TimeoutExpired as error:
        raise LightCrawlError(f"site spider timed out after {timeout}s: {pack}") from error

    output_error = ''
    try:
        items = _count_items(output)
    except (ValueError, OSError, csv.Error) as error:
        items = 0
        output_error = f'Output validation failed: {error}'
    verify_returncode: int | None = None
    verify_script = pack / "verify.py"
    if verify and verify_script.exists():
        try:
            verify_completed = _run(
                [runtime_python(), str(verify_script)],
                pack,
                min(timeout, 60),
            )
            verify_returncode = verify_completed.returncode
        except subprocess.TimeoutExpired:
            verify_returncode = 124

    passed = (
        completed.returncode == 0
        and not output_error
        and (expected_items is None or items == expected_items)
        and (verify_returncode is None or verify_returncode == 0)
    )
    return SiteRunResult(
        pack=pack,
        output=output,
        command=command,
        returncode=completed.returncode,
        items=items,
        expected_items=expected_items,
        verify_returncode=verify_returncode,
        passed=passed,
        stdout=completed.stdout or "",
        stderr=(completed.stderr or "") + ('\n' + output_error if output_error else ''),
        started_at=started_at,
    )


def default_output(pack: Path) -> Path:
    pack = Path(pack).resolve()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return Path("runs") / f"{slugify(pack.name, default='site')}-{stamp}.jsonl"
