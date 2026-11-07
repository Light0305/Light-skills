"""Bind the supplied figure inputs to local bytes; never certify their scientific use."""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import sys


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_sources(source_files=None, *, source_data=None):
    """Accept a path, paths, or named paths. In-memory tables have no file binding."""
    if source_files is None:
        paths = {}
    elif isinstance(source_files, Mapping):
        paths = dict(source_files)
    else:
        values = [source_files] if isinstance(source_files, (str, Path)) else list(source_files)
        paths = {}
        for value in values:
            name = Path(value).name
            if name in paths:
                raise ValueError("Duplicate source filename; use named source_files: " + name)
            paths[name] = value
    if isinstance(source_data, (str, Path)):
        path = Path(source_data).resolve()
        if not any(Path(value).resolve() == path for value in paths.values()):
            if "source_data" in paths:
                raise ValueError("source_data name already used; name the other source explicitly")
            paths["source_data"] = path
    result = {}
    for name, value in paths.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Source names must be nonempty strings")
        path = Path(value).resolve(strict=True)
        if not path.is_file():
            raise ValueError("Source must be a file: " + str(path))
        result[name] = {"path": str(path), "sha256": file_sha256(path), "bytes": path.stat().st_size}
    return result


def verify_sources(report):
    """Return drift/unavailable errors for declared files; do not invent legacy paths."""
    manifest = report.get("source_manifest", {})
    if not isinstance(manifest, dict):
        return ["Malformed source_manifest"]
    errors = []
    for name, entry in manifest.items():
        if not isinstance(entry, dict) or not entry.get("path") or not entry.get("sha256"):
            errors.append("Source has no recheckable path/hash: " + str(name))
            continue
        try:
            path = Path(entry["path"])
            if not path.is_absolute():
                errors.append("Source path is not absolute: " + str(name))
            elif not path.is_file() or file_sha256(path) != entry["sha256"]:
                errors.append("Source changed or is missing: " + str(name))
        except (OSError, TypeError, ValueError) as exc:
            errors.append("Source unavailable: " + str(name) + ": " + str(exc))
    return errors


def binding_scope(report):
    return "exports_and_recorded_sources" if report.get("source_manifest") else "exports_only"


def verify_report(report):
    """Read-only adoption check. An archived review can be valid for an older input."""
    from review_tools import verify_exports
    errors = verify_exports(report) + verify_sources(report)
    return {"status": "stale_or_unavailable" if errors else "recorded_files_match",
            "scope": binding_scope(report), "errors": errors,
            "source_file_count": len(report.get("source_manifest") or {}),
            "boundary": "Only recorded files are checked. No execution, mapping, statistics, visual quality or independent review is certified."}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qa", help="Existing figure QA JSON; no files are modified")
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.qa).read_text(encoding="utf-8"))
        result = verify_report(report)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "invalid_report", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
