#!/usr/bin/env python
"""Build Claude Code and Codex plugin distributions for light-crawl."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
MARKETPLACE = DIST / "light-crawl-marketplace"
PLUGIN = MARKETPLACE / "plugin"
SKILL = PLUGIN / "skills" / "light-crawl"

COPY_DIRS = ("src", "references", "templates", "docs", "scripts", "examples", "benchmarks", "tests")
COPY_FILES = (
    "SKILL.md",
    "README.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
    "run_light_crawl.py",
    "install.ps1",
    "install.sh",
)

IGNORE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "venv",
    "results",
    "runs",
    "sites",
    ".light-crawl",
}


def version() -> str:
    text = (ROOT / "src" / "light_crawl" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("Could not read __version__")
    return match.group(1)


def ignore(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_NAMES or name.endswith(".pyc")}


def copy_skill(version_value: str) -> None:
    SKILL.mkdir(parents=True, exist_ok=True)
    for name in COPY_FILES:
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, SKILL / name)
    for name in COPY_DIRS:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, SKILL / name, ignore=ignore)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_manifests(version_value: str) -> None:
    description = (
        "Routing-first web crawler and reverse-engineering skill. Probes the cheap HTTP surface, "
        "routes to Scrapling/js-reverse/REA only when needed, captures evidence, verifies fixtures, "
        "and promotes reusable site packs."
    )
    claude_plugin = {
        "name": "light-crawl",
        "version": version_value,
        "description": description,
        "author": {"name": "light-crawl"},
        "license": "MIT",
        "keywords": [
            "crawler",
            "scraping",
            "reverse-engineering",
            "scrapling",
            "js-reverse",
            "rea",
            "site-pack",
        ],
    }
    codex_plugin = {
        "name": "light-crawl",
        "version": version_value,
        "description": description,
        "author": {"name": "light-crawl"},
        "license": "MIT",
        "keywords": claude_plugin["keywords"],
        "skills": "./skills/",
        "interface": {
            "displayName": "light-crawl",
            "shortDescription": "Routing-first crawler and reverse-engineering skill",
            "longDescription": (
                "Use light-crawl to probe a target, choose an acquisition lane, capture runtime "
                "or network evidence, reproduce signatures, build a Scrapling spider, verify it, "
                "and promote reusable site packs."
            ),
            "developerName": "light-crawl",
            "category": "Development",
            "capabilities": ["Interactive", "Write"],
            "defaultPrompt": [
                "Use light-crawl to build a verified crawler for this site",
                "Use light-crawl to route this target and capture evidence",
            ],
        },
    }
    write_json(PLUGIN / ".claude-plugin" / "plugin.json", claude_plugin)
    write_json(PLUGIN / ".codex-plugin" / "plugin.json", codex_plugin)

    claude_marketplace = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": "light-crawl",
        "description": "Routing-first crawler and reverse-engineering skill.",
        "owner": {"name": "light-crawl"},
        "plugins": [
            {
                "name": "light-crawl",
                "description": description,
                "version": version_value,
                "category": "development",
                "source": "./plugin",
            }
        ],
    }
    codex_marketplace = {
        "name": "light-crawl",
        "plugins": [
            {
                "name": "light-crawl",
                "source": {"source": "local", "path": "./plugin"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                "category": "Development",
            }
        ],
    }
    write_json(MARKETPLACE / ".claude-plugin" / "marketplace.json", claude_marketplace)
    write_json(MARKETPLACE / ".agents" / "plugins" / "marketplace.json", codex_marketplace)


def write_readmes(version_value: str) -> None:
    plugin_readme = f"""# light-crawl plugin

Version {version_value}. Self-contained plugin for Claude Code and Codex.

- Claude Code skill: `skills/light-crawl/SKILL.md`
- Codex manifest: `.codex-plugin/plugin.json`
- Claude manifest: `.claude-plugin/plugin.json`

The skill directory includes the CLI, references, templates, docs, examples and
benchmarks. It does not include `.venv`, `cases`, `runs` or `sites`.
"""
    (PLUGIN / "README.md").write_text(plugin_readme, encoding="utf-8", newline="\n")

    marketplace_readme = f"""# light-crawl marketplace

Version {version_value}. A local marketplace for Claude Code and Codex.

## Claude Code

```bash
claude plugin marketplace add <this-directory-or-repo>
claude plugin install light-crawl@light-crawl
```

## Codex

```bash
codex plugin marketplace add <this-directory-or-repo>
codex plugin add light-crawl@light-crawl
```

## Standalone skill

Copy `plugin/skills/light-crawl/` into your agent's skill directory, or use the
`light-crawl-skill.zip` artifact.

## Build

```bash
python scripts/package.py
```

Artifacts are written to `dist/`.
"""
    (MARKETPLACE / "README.md").write_text(marketplace_readme, encoding="utf-8", newline="\n")
    shutil.copy2(ROOT / "LICENSE", MARKETPLACE / "LICENSE")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", MARKETPLACE / "THIRD_PARTY_NOTICES.md")
    shutil.copy2(ROOT / "LICENSE", PLUGIN / "LICENSE")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", PLUGIN / "THIRD_PARTY_NOTICES.md")


def make_zip(source: Path, target: Path, root_name: str) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, root_name + "/" + path.relative_to(source).as_posix())


def validate(version_value: str) -> list[str]:
    required = [
        PLUGIN / ".claude-plugin" / "plugin.json",
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / "skills" / "light-crawl" / "SKILL.md",
        MARKETPLACE / ".claude-plugin" / "marketplace.json",
        MARKETPLACE / ".agents" / "plugins" / "marketplace.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing required files:\n" + "\n".join(missing))
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if "name: light-crawl" not in skill_text:
        raise SystemExit("SKILL.md does not declare name: light-crawl")
    for path in required[:2]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != version_value:
            raise SystemExit(f"Version mismatch in {path}")
    return [str(path.relative_to(DIST)) for path in required]


def main() -> int:
    version_value = version()
    if DIST.exists():
        shutil.rmtree(DIST)
    SKILL.mkdir(parents=True, exist_ok=True)

    copy_skill(version_value)
    write_manifests(version_value)
    write_readmes(version_value)

    plugin_zip = DIST / "light-crawl-plugin.zip"
    skill_zip = DIST / "light-crawl-skill.zip"
    marketplace_zip = DIST / "light-crawl-marketplace.zip"
    make_zip(PLUGIN, plugin_zip, "light-crawl")
    make_zip(SKILL, skill_zip, "light-crawl")
    make_zip(MARKETPLACE, marketplace_zip, "light-crawl-marketplace")

    checksums = []
    for path in (plugin_zip, skill_zip, marketplace_zip):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {path.name}")
    (DIST / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    validate(version_value)
    print(f"Built light-crawl {version_value}")
    for path in (plugin_zip, skill_zip, marketplace_zip):
        print(f"  {path} ({path.stat().st_size} bytes)")
    print(f"  {DIST / 'SHA256SUMS.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
