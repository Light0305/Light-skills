"""REA discovery and deep-target command contracts."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..doctor import configured_clients


def find_cli() -> str | None:
    return shutil.which("rea")


def npx_available() -> bool:
    return shutil.which("npx") is not None


def available() -> bool:
    return find_cli() is not None or npx_available()


def wrapper_path() -> Path:
    """Project-local launcher; it keeps REA out of the global npm prefix."""

    return Path(__file__).resolve().parents[3] / "scripts" / "rea.ps1"


def wrapper_available() -> bool:
    return wrapper_path().exists()


def skill_path() -> Path:
    return Path.home() / ".agents" / "skills" / "reverse-engineer-anything" / "SKILL.md"


def configured_in() -> list[str]:
    return configured_clients("rea-agents")


def install_hint() -> str:
    return "No global install needed: use scripts/rea.ps1 (npx cache) or `npx -y rea-agents@latest`."


def static_javascript_command(path: str) -> str:
    if wrapper_available():
        return f'powershell -NoProfile -ExecutionPolicy Bypass -File "{wrapper_path()}" analyze-javascript-application "{path}" --format json'
    return f'npx -y rea-agents@latest analyze-javascript-application "{path}" --format json'


def deep_targets() -> list[str]:
    return [
        "Electron/ASAR or an extracted JavaScript application",
        "APK/IPA and packaged mobile applications",
        "HAR/SAZ, mitmproxy dumps and recorded network captures",
        "Native binaries, firmware and archive members",
    ]


def l4_contract() -> str:
    return (
        "Start with the CLI for static JavaScript/ASAR work; register the MCP only when "
        "interactive browser, Electron or device tooling is needed. Return a request "
        "contract (endpoint, headers, body, signature inputs) to the Scrapling lane, "
        "not a pile of raw decompiled output."
    )
