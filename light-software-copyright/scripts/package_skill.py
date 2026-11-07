#!/usr/bin/env python3
"""Create a portable skill archive using a strict, source-only allowlist."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile


def package(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    paths = [root / "SKILL.md", root / "requirements-render.txt"]
    for folder in ("agents", "assets", "references", "scripts"):
        paths.extend(p for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"})
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Package inputs must be regular files inside the skill")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path, Path("light-software-copyright") / path.relative_to(root))
    return {"path": str(output), "files": len(set(paths)), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="Destination zip; default <skill>/dist/light-software-copyright.zip")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(package(root, args.out or root / "dist" / "light-software-copyright.zip"), ensure_ascii=False, indent=2))
