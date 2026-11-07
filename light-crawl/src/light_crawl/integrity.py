"""Small file contracts shared by acquisition, checks and dataset handoffs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from .utils import sha256_file


def case_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('Expected a nonempty POSIX relative case path')
    part = PurePosixPath(relative)
    if not part.parts or part.is_absolute() or '..' in part.parts or ':' in relative:
        raise ValueError('Path must stay inside the case')
    root = root.resolve()
    path = root.joinpath(*part.parts)
    if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise ValueError('Linked or escaping case path')
    return path


def fingerprint(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Expected a regular file: {path}')
    return {'bytes': path.stat().st_size, 'sha256': sha256_file(path)}


def tree_records(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Expected an unlinked directory')
    records = []
    for child in sorted(path.rglob('*')):
        if child.is_symlink() or not (child.is_dir() or child.is_file()):
            raise ValueError('Directory contains linked/special files')
        if child.is_file():
            records.append({'path': child.relative_to(path).as_posix(), **fingerprint(child)})
    return records


def content_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
