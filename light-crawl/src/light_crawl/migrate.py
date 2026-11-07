"""Schema migration for `site.json` site packs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .state import LightCrawlError
from .utils import read_json, utc_now, write_json


SCHEMA_VERSION = 2


def _default_entrypoints(pack: Path) -> dict[str, str]:
    entrypoints: dict[str, str] = {}
    if (pack / "spider" / "site.json").exists() and (pack / "spider" / "spider.py").exists():
        entrypoints["spider"] = "spider/"
    if (pack / "repro").is_dir():
        entrypoints["repro"] = "repro/"
    if (pack / "fixtures").is_dir():
        entrypoints["fixtures"] = "fixtures/"
    return entrypoints


def migrate_site_pack(pack: Path, *, write: bool = False) -> dict[str, Any]:
    pack = Path(pack).resolve()
    site_file = pack / "site.json"
    if not site_file.is_file():
        raise LightCrawlError(f"Site pack is missing site.json: {pack}")

    data = read_json(site_file, default={}) or {}
    from_version = int(data.get("schema_version", 1) or 1)
    if from_version > SCHEMA_VERSION:
        raise LightCrawlError(
            f"Pack schema v{from_version} is newer than supported v{SCHEMA_VERSION}: {pack}"
        )

    changes: list[str] = []
    if from_version < 2:
        data["version"] = int(data.get("version", 1) or 1)
        data["last_verified_at"] = str(data.get("last_verified_at") or "")
        if not data.get("entrypoints"):
            data["entrypoints"] = _default_entrypoints(pack)
            changes.append("entrypoints")
        if not data.get("policy"):
            data["policy"] = {
                "robots_txt_obey": True,
                "store_credentials": False,
                "redact_fixtures": True,
            }
            changes.append("policy")
        data["schema_version"] = 2
        data["migration"] = {
            "from": from_version,
            "to": 2,
            "at": utc_now(),
        }
        changes.extend(["schema_version", "version", "last_verified_at", "migration"])

    changed = from_version < SCHEMA_VERSION
    wrote = False
    if changed and write:
        write_json(site_file, data)
        wrote = True
    return {
        "pack": str(pack),
        "from_version": from_version,
        "to_version": SCHEMA_VERSION if changed else from_version,
        "changed": changed,
        "wrote": wrote,
        "changes": changes,
    }
