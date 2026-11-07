#!/usr/bin/env python3
"""Local, read-only project inventory and traceable normal-deposit preparation.

Core commands use the Python standard library. No code execution, network calls,
legal conclusions, or edits to the analyzed project are performed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SCHEMA = 1
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv",
    "__pycache__", ".pytest_cache", "dist", "build", "target", ".next",
    ".nuxt", "coverage", "site-packages", ".mypy_cache", "软件著作权申请资料",
}
SOURCE_EXTS = set(".py .pyw .js .jsx .ts .tsx .mjs .cjs .vue .svelte .java .kt .kts .scala .c .h .cpp .hpp .cc .cs .fs .go .rs .rb .php .swift .m .mm .r .jl .lua .pl .pm .sh .bash .ps1 .bat .cmd .sql .html .css .scss .sass .less .s .asm .v .sv .vhd .vhdl .f .f90 .f95 .clj .ex .exs .erl .hs .dart .groovy .sol .zig .cu .cuh .proto".split())
DOC_EXTS = {".md", ".rst", ".txt", ".pdf", ".docx", ".doc", ".odt", ".wps", ".rtf"}
CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".lock"}
BINARY_EXTS = set(".png .jpg .jpeg .gif .webp .bmp .ico .svg .mp3 .wav .mp4 .mov .zip .gz .bz2 .7z .tar .rar .exe .dll .so .dylib .pyd .pyc .class .jar .ttf .ttc .otf .woff .woff2 .db .sqlite .parquet .npy .npz .h5 .hdf5 .pt .pth .bin .pkl .pickle .xlsx .xls .pptx".split())
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "credential_literal": re.compile(r'''(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd)\b\s*[:=]\s*["']([^"'\r\n]{8,})["']'''),
}
PLACEHOLDER = re.compile(r"【待[^】]*】|〖待[^〗]*〗|\b(?:UNKNOWN|TODO|TBD)\b|待确认|待补图|待填写")


class CaseError(ValueError):
    pass


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement; a failed run cannot leave a half-written manifest.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")
        temp = Path(f.name)
    os.replace(temp, path)


def contained(base, relative):
    """Reject absolute paths, traversal, symlink components, and root escape."""
    base = Path(base).resolve()
    relative = Path(relative)
    if relative.is_absolute() or relative.drive or ".." in relative.parts or not relative.parts:
        raise CaseError(f"Unsafe relative path: {relative}")
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CaseError(f"Symlink not allowed: {relative}")
    resolved = current.resolve()
    if not resolved.is_relative_to(base) or resolved == base:
        raise CaseError(f"Path outside root: {relative}")
    return resolved


def decode_source(raw):
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    if b"\x00" in raw:
        raise CaseError("binary_or_nul")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(encoding)
            if any(ord(c) < 32 and c not in "\n\r\t\f" for c in text):
                raise CaseError("unsupported_control_character")
            return text, encoding
        except UnicodeDecodeError:
            continue
    raise CaseError("unknown_encoding")


def source_records(path, raw):
    text, encoding = decode_source(raw)
    if Path(path).suffix.lower() != ".ipynb":
        return [(i, None, line) for i, line in enumerate(text.splitlines(), 1)], encoding
    notebook = json.loads(text)
    records = []
    for cell_no, cell in enumerate(notebook.get("cells", []), 1):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", [])
        src = src if isinstance(src, str) else "".join(src)
        records.extend((i, cell_no, line) for i, line in enumerate(src.splitlines(), 1))
    return records, encoding


def secrets_in(records, path):
    found = []
    for line_no, cell, text in records:
        for rule, pattern in SECRET_PATTERNS.items():
            m = pattern.search(text)
            if not m:
                continue
            # Common explicit placeholders are not secrets. Never print values.
            if rule == "credential_literal":
                value = m.group(1).lower()
                if value.startswith(("${", "{{", "<", "your_", "your-", "example", "replace_")):
                    continue
            found.append({"path": path, "line": line_no, "cell_index": cell, "rule": rule})
    return found


def allowed_secret(finding, selection):
    return any(
        all(entry.get(k) == finding.get(k) for k in ("path", "line", "cell_index", "rule"))
        and bool(str(entry.get("reason", "")).strip())
        for entry in selection.get("secret_allowlist", [])
    )


def label_file(relative, text):
    p = Path(relative)
    ext = p.suffix.lower()
    name = p.name.lower()
    if name.startswith(".env") or name in {"id_rsa", "id_ed25519"} or ext in {".pem", ".key", ".p12", ".pfx"}:
        return "sensitive", "credential_or_private_key_file"
    if name in {"license", "licence", "copying", "notice"} or name.startswith("license."):
        return "document", "license_evidence"
    if ext in DOC_EXTS:
        return "document", "documentation_evidence"
    if name.endswith((".min.js", ".min.css", ".map")) or name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "cargo.lock"}:
        return "generated", "generated_or_lock_file"
    if ext == ".ipynb":
        return "review", "notebook_code_cells_need_review"
    if ext in SOURCE_EXTS or text.startswith("#!"):
        if any(part.lower() in {"tests", "test", "fixtures", "examples", "demo"} for part in p.parts) or ".test." in name or ".spec." in name:
            return "review", "test_or_example_scope_review"
        if re.search(r"(?i)(?:auto[- ]generated|generated by|do not edit)", "\n".join(text.splitlines()[:8])):
            return "review", "possible_generated_source"
        return "source", "source_candidate_not_ownership_decision"
    if ext in CONFIG_EXTS or name.startswith(".env"):
        return "review", "configuration_may_contain_program_expression"
    return "review", "unknown_text_requires_review"


def git_ignored(root, paths):
    if not paths:
        return set(), "not_needed"
    try:
        result = subprocess.run(["git", "-C", str(root), "check-ignore", "-z", "--stdin"], input="\0".join(paths).encode("utf-8") + b"\0", capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return set(), "unavailable"
    if result.returncode not in (0, 1):
        return set(), "not_a_git_repository_or_unavailable"
    return set(result.stdout.decode("utf-8", errors="replace").strip("\0").split("\0")), "checked"


def init_case(project, case):
    project, case = Path(project).resolve(), Path(case).resolve()
    if not project.is_dir():
        raise CaseError("Project directory does not exist")
    if case == project:
        raise CaseError("Use a separate material directory, not the project root itself")
    case.mkdir(parents=True, exist_ok=True)
    target = case / "case.json"
    if target.exists():
        existing = read_json(target)
        if Path(existing["project_root"]).resolve() != project:
            raise CaseError("Existing case belongs to a different project")
        return {"case": str(case), "status": "existing_preserved"}
    data = {
        "schema_version": SCHEMA, "delivery_profile": "three-documents",
        "project_root": str(project), "jurisdiction": "CN",
        "software_name": None, "abbreviation": None, "version": None,
        "owners": [], "owner_type": None, "development_mode": None,
        "rights_acquisition": None, "rights_scope": None, "completed_on": None,
        "publication_status": None, "first_published_on": None, "first_published_place": None,
        "environments": {k: None for k in ("development_hardware", "development_os", "development_tools", "runtime_hardware", "runtime_os", "runtime_support")},
        "languages": [], "purpose": None, "industry": None, "main_functions": None,
        "technical_features": None, "features": [],
        "reviews": {"facts_confirmed": False, "confirmation_basis": None, "rights_basis": None, "third_party_review": None, "source_ending_review": None, "visual_review": None},
        "rules": {"checked_on": None, "official_form_verified": False, "sources": [], "notes": []},
    }
    write_json(target, data)
    return {"case": str(case), "status": "created"}


def scan_case(case, max_bytes=2_000_000, persist=True):
    case = Path(case).resolve()
    facts = read_json(case / "case.json")
    root = Path(facts["project_root"]).resolve()
    if not root.is_dir():
        raise CaseError("Project root no longer exists")
    files, skipped = [], []
    def walk_error(error):
        skipped.append({"path": str(error.filename), "reason": "directory_read_error"})
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        parent = Path(parent)
        for name in sorted(dirs[:]):
            path = parent / name
            if path.is_symlink() or name.lower() in EXCLUDED_DIRS or path.resolve() == case or path.resolve().is_relative_to(case):
                dirs.remove(name)
                skipped.append({"path": path.relative_to(root).as_posix(), "reason": "symlink_or_excluded_directory"})
        dirs.sort()
        for name in sorted(names):
            path = parent / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                skipped.append({"path": rel, "reason": "symlink"})
                continue
            ext = path.suffix.lower()
            if ext in BINARY_EXTS or ext in {".pdf", ".docx", ".doc", ".odt", ".wps", ".rtf"}:
                skipped.append({"path": rel, "reason": "binary_or_document_read_separately"})
                continue
            try:
                if path.stat().st_size > max_bytes:
                    skipped.append({"path": rel, "reason": "size_limit", "bytes": path.stat().st_size})
                    continue
                raw = path.read_bytes()
                text, encoding = decode_source(raw)
                category, reason = label_file(rel, text)
                records, _ = source_records(rel, raw)
                files.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "encoding": encoding,
                              "category": category, "reason": reason, "raw_lines": len(records),
                              "nonblank_lines": sum(bool(line.strip()) for _, _, line in records),
                              "secret_findings": secrets_in(records, rel)})
            except (OSError, ValueError, TypeError, KeyError) as error:
                skipped.append({"path": rel, "reason": type(error).__name__ + ": " + str(error)[:100] if isinstance(error, CaseError) else type(error).__name__})
    ignored, git_status = git_ignored(root, [f["path"] for f in files])
    for item in files:
        item["git_ignored"] = item["path"] in ignored
    inventory = {"schema_version": SCHEMA, "project_root": str(root), "max_bytes": max_bytes, "files": files, "skipped": skipped, "git_ignore_status": git_status}
    inventory["snapshot_sha256"] = fingerprint(inventory)
    if not persist:
        return inventory
    write_json(case / "inventory.json", inventory)
    selection_path = case / "selection.json"
    if not selection_path.exists():
        write_json(selection_path, {
            "schema_version": SCHEMA, "snapshot_sha256": inventory["snapshot_sha256"],
            "scope_reviewed": False, "scope_note": None, "skipped_review": None,
            "secret_allowlist": [],
            "files": [{"path": f["path"], "sha256": f["sha256"], "decision": "review", "reason": None} for f in files],
        })
    return {"files": len(files), "skipped": len(skipped), "snapshot_sha256": inventory["snapshot_sha256"], "selection_preserved": selection_path.exists()}


def checked_source(case):
    case = Path(case).resolve()
    facts, inv, selection = [read_json(case / n) for n in ("case.json", "inventory.json", "selection.json")]
    root = Path(facts["project_root"]).resolve()
    inv_copy = {k: v for k, v in inv.items() if k != "snapshot_sha256"}
    if fingerprint(inv_copy) != inv.get("snapshot_sha256"):
        raise CaseError("Inventory fingerprint changed; rescan and review")
    if str(root) != inv["project_root"] or selection.get("snapshot_sha256") != inv["snapshot_sha256"]:
        raise CaseError("Selection belongs to a different or stale inventory")
    current = scan_case(case, inv.get("max_bytes", 2_000_000), persist=False)
    if current["snapshot_sha256"] != inv["snapshot_sha256"]:
        raise CaseError("Project inventory changed (including added/removed files); rescan and review changes")
    if selection.get("scope_reviewed") is not True or not selection.get("scope_note"):
        raise CaseError("Review the complete program scope and record scope_note before extraction")
    if inv["skipped"] and not selection.get("skipped_review"):
        raise CaseError("Record how skipped directories/files affect scope in skipped_review")
    candidates = {f["path"]: f for f in inv["files"]}
    entries = selection.get("files", [])
    paths = [e.get("path") for e in entries]
    if len(paths) != len(set(paths)) or set(paths) != set(candidates):
        raise CaseError("Every inventory candidate must have exactly one selection decision")
    all_records, selected, risks = [], [], []
    for entry in entries:
        path = entry["path"]
        if entry.get("decision") not in {"include", "exclude"} or not str(entry.get("reason") or "").strip():
            raise CaseError(f"Unreviewed candidate or missing reason: {path}")
        source = contained(root, path)
        if not source.is_file() or file_hash(source) != candidates[path]["sha256"] or entry.get("sha256") != candidates[path]["sha256"]:
            raise CaseError(f"Source changed or selection hash mismatch: {path}")
        if entry["decision"] == "exclude":
            continue
        if candidates[path]["category"] in {"sensitive", "generated"}:
            raise CaseError(f"Sensitive/generated file cannot be included without rebuilding the reviewed inventory: {path}")
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise CaseError(f"Source changed during read: {path}")
        records, encoding = source_records(path, raw)
        risks.extend(f for f in secrets_in(records, path) if not allowed_secret(f, selection))
        selected.append({"path": path, "sha256": entry["sha256"], "encoding": encoding,
                         "raw_lines": len(records), "nonblank_lines": sum(bool(t.strip()) for _, _, t in records), "reason": entry["reason"]})
        all_records.extend({"path": path, "line": i, "cell_index": cell, "text": line} for i, cell, line in records if line.strip())
    if risks:
        # Findings never contain credential values.
        write_json(case / "secret-findings.json", risks)
        raise CaseError(f"Unresolved secret findings ({len(risks)}); see secret-findings.json, no source material exported")
    if not all_records:
        raise CaseError("No nonblank reviewed program source")
    return facts, inv, selection, selected, all_records


def make_pages(facts, inv, selection, selected, records):
    full = [records[i:i + 50] for i in range(0, len(records), 50)]
    indexes = list(range(len(full))) if len(full) < 60 else list(range(30)) + list(range(len(full) - 30, len(full)))
    pages = [{"submission_page": j, "source_page": index + 1, "lines": full[index]} for j, index in enumerate(indexes, 1)]
    return {
        "schema_version": SCHEMA, "software_name": facts.get("software_name"), "version": facts.get("version"),
        "snapshot_sha256": inv["snapshot_sha256"], "selection_sha256": fingerprint(selection),
        "source_files": selected, "raw_source_lines": sum(f["raw_lines"] for f in selected),
        "nonblank_source_lines": len(records), "complete_pages": len(full),
        "submitted_lines": sum(len(p["lines"]) for p in pages), "submitted_pages": len(pages),
        "mode": "all" if len(full) < 60 else "front_back_30", "lines_per_page": 50,
        "counting_basis": "raw splitlines and nonblank original program lines; notebook code cells only; comments retained",
        "pages": pages,
    }


def extract_case(case):
    facts, inv, selection, selected, records = checked_source(case)
    pages = make_pages(facts, inv, selection, selected, records)
    write_json(Path(case) / "source-pages.json", pages)
    return {k: pages[k] for k in ("mode", "raw_source_lines", "nonblank_source_lines", "complete_pages", "submitted_pages")}


def verify_pages(case):
    facts, inv, selection, selected, records = checked_source(case)
    expected = make_pages(facts, inv, selection, selected, records)
    actual = read_json(Path(case) / "source-pages.json")
    if actual != expected:
        raise CaseError("Source pages differ from actual snapshot/order/line mapping; re-extract")
    return actual


def title_for(facts):
    name, version = facts.get("software_name"), facts.get("version")
    if not isinstance(name, str) or not name.strip() or not isinstance(version, str) or not version.strip():
        raise CaseError("Set the real software_name and version before rendering")
    return name if name.rstrip().endswith(version) else f"{name} {version}"


def canonical_inputs(case):
    case = Path(case)
    return {name: file_hash(case / name) for name in ("case.json", "inventory.json", "selection.json", "source-pages.json", "manual.json", "functions.json", "layout-profile.json") if (case / name).is_file()}


def audit_case(case, kinds=None):
    case = Path(case).resolve()
    facts = read_json(case / "case.json")
    kinds = set(kinds or (("functions", "code", "manual") if facts.get("delivery_profile") == "three-documents" else ("application", "code", "manual")))
    if kinds == {"bundle"}:
        kinds = {"functions", "code", "manual"}
    if not kinds <= {"application", "code", "manual", "functions"}:
        raise CaseError("Unknown audit kind")
    errors, warnings = [], []
    if facts.get("jurisdiction") != "CN":
        errors.append("The bundled normal-deposit profile supports CN only")
    required = ("software_name", "version")
    if "application" in kinds:
        required += ("owners", "owner_type", "completed_on", "development_mode", "rights_acquisition", "rights_scope", "publication_status", "purpose", "main_functions", "technical_features", "languages")
    for field in required:
        value = facts.get(field)
        if not value or PLACEHOLDER.search(str(value)):
            errors.append(f"Missing/unresolved fact: {field}")
    for key in (("development_hardware", "development_os", "development_tools", "runtime_hardware", "runtime_os", "runtime_support") if "application" in kinds else ()):
        value = facts.get("environments", {}).get(key)
        if not value or PLACEHOLDER.search(str(value)):
            errors.append(f"Missing/unresolved environment: {key}")
    for field in ("completed_on", "first_published_on"):
        value = facts.get(field)
        if value:
            try:
                parsed = dt.date.fromisoformat(value)
                if parsed > dt.date.today():
                    errors.append(f"Future date needs correction: {field}")
            except (TypeError, ValueError):
                errors.append(f"Invalid ISO date: {field}")
    if facts.get("publication_status") == "已发表":
        if not facts.get("first_published_on") or not facts.get("first_published_place"):
            errors.append("Published software requires first publication date and place")
        if facts.get("completed_on") and facts.get("first_published_on") and str(facts["first_published_on"]) < str(facts["completed_on"]):
            errors.append("First publication precedes the stated completion date; confirm actual facts")
    elif facts.get("publication_status") == "未发表":
        if facts.get("first_published_on") or facts.get("first_published_place"):
            errors.append("Unpublished software has first-publication fields populated")
    elif facts.get("publication_status"):
        errors.append("Use 已发表 or 未发表 for the local worksheet publication_status")
    reviews = facts.get("reviews", {})
    if "application" in kinds and (reviews.get("facts_confirmed") is not True or not reviews.get("confirmation_basis")):
        errors.append("Applicant facts have not been confirmed with a recorded basis")
    review_fields = set()
    if "application" in kinds:
        review_fields.add("rights_basis")
    if "code" in kinds:
        review_fields.update(("third_party_review", "source_ending_review"))
    if kinds & {"code", "manual", "functions"}:
        review_fields.add("visual_review")
    for field in sorted(review_fields):
        if not reviews.get(field) or PLACEHOLDER.search(str(reviews[field])):
            errors.append(f"Review missing: {field}")
    rules = facts.get("rules", {})
    if rules.get("official_form_verified") is not True or not rules.get("checked_on") or not rules.get("sources"):
        warnings.append("Current portal form/signature requirements are unverified; local review does not imply filing readiness")
    elif rules.get("checked_on") != dt.date.today().isoformat():
        warnings.append("Rule verification is not dated today; recheck the actual form before filing")
    pages = None
    if kinds & {"application", "code"}:
        try:
            pages = verify_pages(case)
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append("Source verification: " + str(error))
    features = facts.get("features", [])
    if kinds & {"manual", "functions"} and not features:
        errors.append("No feature-to-project evidence recorded")
    feature_ids = set()
    for feature in features:
        fid = feature.get("id")
        if not fid or fid in feature_ids:
            errors.append("Feature IDs must be present and unique")
        feature_ids.add(fid)
        if feature.get("status") != "implemented" or not feature.get("evidence"):
            errors.append(f"Feature requires implemented status and evidence: {fid}")
        for evidence in feature.get("evidence", []):
            try:
                path = contained(facts["project_root"], evidence["path"])
                if not path.is_file():
                    raise CaseError("Evidence file missing")
                if evidence.get("sha256") and file_hash(path) != evidence["sha256"]:
                    raise CaseError("Evidence snapshot changed")
                if evidence.get("lines"):
                    start, end = evidence["lines"]
                    text, _ = decode_source(path.read_bytes())
                    if not (isinstance(start, int) and isinstance(end, int) and 1 <= start <= end <= len(text.splitlines())):
                        raise CaseError("Evidence line range is outside the actual file")
            except (OSError, ValueError, KeyError, TypeError) as error:
                errors.append(f"Feature {fid}: {error}")
    for document_kind in kinds & {"manual", "functions"}:
        try:
            name = "functions.json" if document_kind == "functions" else "manual.json"
            # Share the renderer's actual input contract instead of accepting
            # a different subset during release.
            from render_materials import load_document
            manual, _ = load_document(case, document_kind)
            if PLACEHOLDER.search(json.dumps(manual, ensure_ascii=False)):
                errors.append(f"{name} contains unresolved placeholders")
            headings = {s.get("heading") for s in manual.get("sections", [])}
            for feature in features:
                field = "function_heading" if document_kind == "functions" else "manual_heading"
                if not feature.get(field) or feature[field] not in headings:
                    errors.append(f"Feature missing from {document_kind} headings: {feature.get('id')}")
        except (OSError, ValueError, TypeError) as error:
            errors.append(f"{document_kind} unavailable: " + str(error))
    manifests = read_json(case / "deliverables.json") if (case / "deliverables.json").exists() else {"artifacts": []}
    artifacts = [a for a in manifests.get("artifacts", []) if a.get("kind") in kinds]
    for kind in sorted(kinds):
        if not any(a.get("kind") == kind for a in artifacts):
            errors.append(f"No generated {kind} artifact")
    try:
        title = title_for(facts)
    except CaseError as error:
        title = ""
        errors.append(str(error))
    for artifact in artifacts:
        try:
            path = contained(case, artifact["path"])
            if not path.is_file() or file_hash(path) != artifact["sha256"]:
                raise CaseError("Output missing or modified; preserve edits before rebuilding")
            for name, sha in artifact["inputs"].items():
                if file_hash(contained(case, name)) != sha:
                    raise CaseError(f"Stale artifact input: {name}")
            for name, sha in artifact.get("project_inputs", {}).items():
                if file_hash(contained(facts["project_root"], name)) != sha:
                    raise CaseError(f"Stale project evidence: {name}")
            inspect_artifact(path, artifact, title, pages, facts)
        except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
            errors.append(f"Artifact {artifact.get('path')}: {error}")
    if not artifacts:
        errors.append("No actual deliverable files to inspect")
    report = {"schema_version": SCHEMA, "status": "needs_fix" if errors else "local_review_ready",
              "errors": errors, "warnings": warnings, "inputs": canonical_inputs(case),
              "artifact_count": len(artifacts), "checked_kinds": sorted(kinds), "portal_ready": False,
              "scope": "Local material checks only; visual review, factual evidence and current portal requirements remain separate."}
    write_json(case / "audit.json", report)
    return report


def inspect_artifact(path, artifact, title, pages, facts):
    ext = path.suffix.lower()
    kind = artifact["kind"]
    if ext == ".txt":
        text = path.read_text(encoding="utf-8")
    elif ext == ".docx":
        import zipfile
        from xml.etree import ElementTree as ET
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n == "word/document.xml" or re.fullmatch(r"word/header\d+\.xml", n)]
            text = "\n".join("".join(ET.fromstring(z.read(n)).itertext()) for n in names)
    elif ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        if not reader.pages:
            raise CaseError("Empty PDF")
        extracted = []
        for index, page in enumerate(reader.pages):
            if abs(float(page.mediabox.width) - 595.276) > 2 or abs(float(page.mediabox.height) - 841.89) > 2:
                raise CaseError("PDF is not portrait A4")
            page_text = page.extract_text() or ""
            if title.replace(" ", "") not in re.sub(r"\s+", "", page_text):
                raise CaseError("PDF page missing the current software title/version")
            if kind == "code" and pages and index < len(pages["pages"]):
                expected_text = "".join(line["text"] for line in pages["pages"][index]["lines"])
                if re.sub(r"\s+", "", expected_text) not in re.sub(r"\s+", "", page_text):
                    raise CaseError("Rendered source text differs from the original line map")
            extracted.append(page_text)
        if kind == "code" and pages and len(reader.pages) != pages["submitted_pages"]:
            raise CaseError("Rendered code PDF page count differs from deposit map")
        if kind == "manual" and len(reader.pages) > 60:
            raise CaseError("Manual exceeds 60 pages; retain the full draft and prepare a verified continuous front/back deposit separately")
        text = "\n".join(extracted)
    else:
        raise CaseError("Unsupported artifact format")
    if title.replace(" ", "") not in re.sub(r"\s+", "", text):
        raise CaseError("Artifact missing software name/version")
    if "\ufffd" in text:
        raise CaseError("Replacement character in output")
    if kind != "code" and PLACEHOLDER.search(text):
        raise CaseError("Unresolved placeholder in deliverable")
    if kind == "application" and facts.get("owners"):
        if not all(owner in text for owner in facts["owners"]):
            raise CaseError("Worksheet does not contain current owner names")
    if kind == "code" and ext == ".docx" and pages:
        for page in pages["pages"]:
            expected_text = "".join(line["text"] for line in page["lines"])
            if re.sub(r"\s+", "", expected_text) not in re.sub(r"\s+", "", text):
                raise CaseError("DOCX source text differs from the original line map")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--project", required=True)
    p.add_argument("--case", required=True)
    for command in ("scan", "extract", "audit"):
        p = sub.add_parser(command)
        p.add_argument("--case", required=True)
        if command == "scan":
            p.add_argument("--max-bytes", type=int, default=2_000_000)
        if command == "audit":
            p.add_argument("--only", choices=["bundle", "functions", "application", "code", "manual"], help="Check just the requested material rather than a full packet")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_case(args.project, args.case)
        elif args.command == "scan":
            result = scan_case(args.case, args.max_bytes)
        elif args.command == "extract":
            result = extract_case(args.case)
        else:
            result = audit_case(args.case, [args.only] if args.only else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("status") == "needs_fix" else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
