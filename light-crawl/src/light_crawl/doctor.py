"""Environment checks for the four-tool stack."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Check:
    name: str
    status: str
    detail: str
    hint: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "hint": self.hint,
        }


def _run(command: list[str], timeout: int = 15) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        return completed.returncode, output
    except (OSError, subprocess.SubprocessError) as error:
        return 1, str(error)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _appdata_dir() -> Path:
    if os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"])
    home = Path.home()
    if os.name == "nt":
        return home / "AppData" / "Roaming"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support"
    return home / ".config"


def _playwright_cache_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "ms-playwright"


def _config_paths() -> Iterable[tuple[str, Path]]:
    home = Path.home()
    appdata = _appdata_dir()
    yield "Claude Code", home / ".claude.json"
    yield "Codex", home / ".codex" / "config.toml"
    yield "Cursor", home / ".cursor" / "mcp.json"
    yield "Gemini CLI", home / ".gemini" / "settings.json"
    yield "Antigravity", home / ".gemini" / "antigravity" / "mcp_config.json"
    yield "OpenCode", home / ".config" / "opencode" / "opencode.json"
    yield "Windsurf", home / ".codeium" / "windsurf" / "mcp_config.json"
    yield "VS Code", appdata / "Code" / "User" / "mcp.json"
    yield "Copilot CLI", home / ".copilot" / "mcp-config.json"


def configured_clients(needle: str) -> list[str]:
    found: list[str] = []
    for name, path in _config_paths():
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle in text:
            found.append(name)
    return found


def run_doctor() -> list[Check]:
    checks: list[Check] = []

    version = sys.version_info
    checks.append(
        Check(
            "Python",
            "ok" if version >= (3, 11) else "fail",
            f"{version.major}.{version.minor}.{version.micro}",
            "Install Python 3.11 or newer.",
        )
    )

    node = _which("node")
    checks.append(
        Check(
            "Node.js",
            "ok" if node else "warn",
            node or "not found",
            "Install Node.js 20.19+ for js-reverse and REA MCP.",
        )
    )

    scrapling_module = importlib.util.find_spec("scrapling")
    scrapling_cli = _which("scrapling")
    if not scrapling_cli:
        candidate = Path(sys.executable).with_name("scrapling.exe")
        if candidate.exists():
            scrapling_cli = str(candidate)
        else:
            candidate = Path(sys.executable).with_name("scrapling")
            if candidate.exists():
                scrapling_cli = str(candidate)
    if scrapling_module or scrapling_cli:
        detail = scrapling_cli or "importable module"
        code, output = _run([scrapling_cli, "--version"]) if scrapling_cli else (0, "")
        if output:
            detail = f"{detail} · {output.splitlines()[0]}"
        checks.append(Check("Scrapling", "ok", detail))
    else:
        checks.append(
            Check(
                "Scrapling",
                "warn",
                "not installed",
                'Run `pip install -e ".[fetchers]"` and then `scrapling install`.',
            )
        )

    playwright_root = _playwright_cache_dir()
    chromium_dirs = sorted(playwright_root.glob("chromium-*")) if playwright_root.exists() else []
    if chromium_dirs:
        checks.append(
            Check(
                "Scrapling browser",
                "ok",
                str(chromium_dirs[-1]),
                "Bundled browser present; `real_chrome=True` remains available as a fallback.",
            )
        )
    else:
        checks.append(
            Check(
                "Scrapling browser",
                "warn",
                "no bundled Chromium found",
                "Run `scrapling install` (optionally with PLAYWRIGHT_DOWNLOAD_HOST) or use real_chrome=True.",
            )
        )

    from .utils import system_chrome_path

    chrome = system_chrome_path()
    checks.append(
        Check(
            "Chrome",
            "ok" if chrome else "warn",
            str(chrome) if chrome else "not found in standard locations",
            "Install Google Chrome stable; Scrapling and js-reverse both need a browser.",
        )
    )

    js_reverse = _which("js-reverse-mcp")
    if not js_reverse:
        candidate = Path.home() / "AppData" / "Roaming" / "npm" / "js-reverse-mcp.cmd"
        if candidate.exists():
            js_reverse = str(candidate)
    if js_reverse:
        code, output = _run([js_reverse, "--version"])
        detail = js_reverse
        if output:
            detail = f"{detail} · {output.splitlines()[0]}"
        checks.append(Check("js-reverse MCP", "ok", detail))
    else:
        checks.append(
            Check(
                "js-reverse MCP",
                "warn",
                "not installed",
                "Run `npm install -g js-reverse-mcp`.",
            )
        )

    clients = configured_clients("js-reverse")
    checks.append(
        Check(
            "js-reverse config",
            "ok" if clients else "warn",
            ", ".join(clients) if clients else "no client config contains js-reverse",
            "Add the server to at least one MCP client; see references/runtime-reverse.md.",
        )
    )

    rea = _which("rea")
    rea_skill = Path.home() / ".agents" / "skills" / "reverse-engineer-anything" / "SKILL.md"
    if rea:
        checks.append(Check("REA CLI", "ok", rea))
    elif _which("npx"):
        wrapper_name = "rea.ps1" if os.name == "nt" else "rea.sh"
        wrapper = Path(__file__).resolve().parents[2] / "scripts" / wrapper_name
        checks.append(
            Check(
                "REA CLI",
                "ok",
                f"project-local npx wrapper: {wrapper}",
                "No global install needed; the first run populates npm's cache.",
            )
        )
    else:
        checks.append(
            Check(
                "REA CLI",
                "warn",
                "not installed and npx not found",
                "Install Node.js; L4 can wait until a deep target appears.",
            )
        )
    checks.append(
        Check(
            "REA skill",
            "ok" if rea_skill.exists() else "warn",
            str(rea_skill) if rea_skill.exists() else "not installed",
            "The skill is enough for routing; enable the REA MCP only for interactive deep dives.",
        )
    )

    git = _which("git")
    checks.append(
        Check(
            "git",
            "ok" if git else "warn",
            git or "not found",
            "Install git to version site packs and review diffs.",
        )
    )

    return checks


def format_checks(checks: list[Check]) -> str:
    icons = {"ok": "✓", "warn": "!", "fail": "✗"}
    lines = ["light-crawl doctor", ""]
    for check in checks:
        lines.append(f"  {icons.get(check.status, '?')} {check.name:<18} {check.detail}")
        if check.hint and check.status != "ok":
            lines.append(f"      → {check.hint}")
    failures = sum(1 for check in checks if check.status == "fail")
    warnings = sum(1 for check in checks if check.status == "warn")
    lines.append("")
    lines.append(f"  {failures} failure(s), {warnings} warning(s)")
    return "\n".join(lines)
