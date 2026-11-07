"""Promote a case into a reusable site pack."""

from __future__ import annotations

import shutil
from pathlib import Path

from .models import Phase
from .scaffold import site_pack_readme
from .state import CaseStore, LightCrawlError
from .utils import domain_from_url, ensure_dir, read_json, safe_copy, slugify, utc_now, write_json


def _files_in(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return [item for item in path.rglob("*") if item.is_file()]


def learn_case(
    store: CaseStore,
    sites_root: Path,
    *,
    domain: str | None = None,
    force: bool = False,
) -> Path:
    phase = Phase(store.state.phase)
    if phase not in {Phase.VERIFIED, Phase.OPERATING, Phase.LEARNED}:
        raise LightCrawlError(
            "learn requires a VERIFIED case (or later). Finish the fixture and live-sample gate first; "
            "promoting unverified code would make the site pack look safer than it is."
        )

    target = store.target
    from .verify import verify_case
    from .validation import checked_receipt
    report = verify_case(store.directory)
    if not report.ok or checked_receipt(store.directory) is None:
        raise LightCrawlError('learn requires a current executed check receipt and valid case artifacts')
    if any(f.code == 'fixture_secret' for f in report.warnings):
        raise LightCrawlError('Review/redact flagged fixtures before promoting a shareable site pack')
    domain_name = (domain or domain_from_url(target.url)).strip().lower()
    if not domain_name:
        raise LightCrawlError(
            "Cannot infer a domain from the target. Pass --domain, for example --domain app.example.com."
        )

    spider_files = _files_in(store.spider_dir)
    repro_files = _files_in(store.repro_dir)
    fixture_files = _files_in(store.fixtures_dir)
    if not spider_files and not repro_files:
        raise LightCrawlError(
            "Nothing to learn yet: add a spider under spider/ or a reproduction under repro/ first."
        )

    sites_root = ensure_dir(Path(sites_root))
    pack_dir = sites_root / slugify(domain_name)
    if pack_dir.exists():
        if not force:
            raise LightCrawlError(f"Site pack already exists: {pack_dir}. Use --force to replace it.")
        shutil.rmtree(pack_dir)
    ensure_dir(pack_dir)

    copied: list[str] = []
    for name, source in (
        ("spider", store.spider_dir),
        ("repro", store.repro_dir),
        ("fixtures", store.fixtures_dir),
    ):
        if source.exists() and _files_in(source):
            if name == 'fixtures':
                # Raw acquisition snapshots stay with their source case. Site packs use curated working fixtures.
                shutil.copytree(source, pack_dir / name, ignore=shutil.ignore_patterns('captures', '__pycache__'))
            else:
                safe_copy(source, pack_dir / name)
            copied.append(name)

    for name in ("probe.json", "route.json"):
        source = store.directory / name
        if source.exists():
            safe_copy(source, pack_dir / name)
            copied.append(name)

    pack = {
        "schema_version": 1,
        "domain": domain_name,
        "source_case": store.state.case_id,
        "source_case_dir": str(store.directory.resolve()),
        "lane": store.state.lane,
        "delivery": store.state.delivery,
        "target": store.state.target,
        "created_at": utc_now(),
        "copied": copied,
        "entrypoints": {
            "spider": "spider/" if "spider" in copied else None,
            "repro": "repro/" if "repro" in copied else None,
            "fixtures": "fixtures/" if "fixtures" in copied else None,
        },
        "policy": {
            "robots_txt_obey": True,
            "store_credentials": False,
            "redact_fixtures": True,
        },
    }
    write_json(pack_dir / "site.json", pack)
    (pack_dir / "README.md").write_text(
        site_pack_readme(domain_name, store.state.case_id, store.state.lane, store.state.delivery),
        encoding="utf-8",
        newline="\n",
    )

    store.add_evidence(
        phase=store.state.phase,
        source="light-crawl learn",
        action=f"promoted site pack {domain_name}",
        observation=f"created {pack_dir} with {len(copied)} copied sections",
        inference="reusable selectors and reproduction code are now versionable outside the case",
        confidence="high",
        artifact=str(pack_dir),
    )
    store.advance("LEARNED", f"site pack created at {pack_dir}")
    return pack_dir


def site_pack_summary(path: Path) -> dict:
    data = read_json(Path(path) / "site.json", default={}) or {}
    return {
        "domain": data.get("domain", ""),
        "source_case": data.get("source_case", ""),
        "lane": data.get("lane"),
        "delivery": data.get("delivery"),
        "copied": data.get("copied", []),
    }
