"""Read-only library indexing and recorded-source checks; no scientific grading."""
from pathlib import Path
from typing import Any

from .io import read_json
from .literature import _pdf_digest


def verify_literature(out_dir: str | Path) -> dict[str, Any]:
    root = Path(out_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"Literature directory does not exist: {root}")
    errors, review, entries = [], [], []
    identities, folders = set(), set()
    for path in sorted(root.glob("*/meta.json")):
        try:
            meta = read_json(path)
            if not isinstance(meta, dict) or not isinstance(meta.get("paper_id"), str) or not meta["paper_id"]:
                raise ValueError("Missing paper_id")
            pid, folder = meta["paper_id"], path.parent.name
            if pid in identities:
                errors.append(f"Duplicate paper_id: {pid}")
            if meta.get("folder") != folder:
                errors.append(f"Metadata folder differs from actual directory: {folder}")
            identities.add(pid)
            folders.add((pid, folder))
            pdf = path.parent / "paper.pdf"
            if pdf.is_file():
                actual = _pdf_digest(pdf)
                expected = meta.get("pdf_sha256")
                if not expected:
                    review.append({"paper_id": pid, "reason": "PDF baseline is unrecorded; inspect the source and establish a current baseline"})
                elif actual != expected:
                    review.append({"paper_id": pid, "reason": "PDF changed; reading, translation and notes need source-version review"})
            elif meta.get("pdf_status") == "present" or meta.get("pdf_sha256"):
                errors.append(f"Recorded PDF is missing: {folder}")
            artifacts = {}
            for name, field in (("paper.md", "parse_status"), ("paper.zh.md", "translation_status"),
                                ("note.md", "note_status"), ("source_map.json", "source_map_status")):
                file = path.parent / name
                nonempty = file.is_file() and file.stat().st_size > 0
                artifacts[name] = "present_unverified" if nonempty else "missing_or_empty"
                if meta.get(field) in {"present", "already_present"} and not nonempty:
                    review.append({"paper_id": pid, "reason": f"Recorded reading artifact is missing or empty: {name}"})
            entries.append({"paper_id": pid, "folder": folder,
                            "pdf_present": pdf.is_file(), "artifacts": artifacts})
        except (ValueError, OSError, TypeError) as exc:
            errors.append(f"{path}: {exc}")
    manifest_path = root / "manifest.json"
    if not entries:
        errors.append("No readable article metadata found")
    if manifest_path.is_file():
        try:
            manifest = read_json(manifest_path)
            indexed = manifest.get("entries") if isinstance(manifest, dict) else None
            if not isinstance(indexed, list) or any(not isinstance(x, dict) for x in indexed):
                raise ValueError("Manifest entries must be objects")
            pairs = [(x.get("paper_id"), x.get("folder")) for x in indexed]
            if len(set(pairs)) != len(pairs) or set(pairs) != folders:
                errors.append("Manifest does not index every actual article exactly once; refresh the full library index")
        except (ValueError, OSError, TypeError) as exc:
            errors.append(f"{manifest_path}: {exc}")
    else:
        errors.append("Library manifest is missing; refresh the index before downstream intake")
    return {"ok": not errors and not review, "integrity_ok": not errors,
            "errors": errors, "needs_review": review, "library_total": len(entries), "entries": entries,
            "boundary": "Checks index coverage, recorded PDF bytes and file presence; does not certify full reading, translation, reference validity or scientific correctness."}
