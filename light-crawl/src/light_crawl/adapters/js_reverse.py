"""js-reverse MCP discovery and the tool surface used by the L2 playbook."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..doctor import configured_clients

TOOL_NAMES = [
    "select_page",
    "new_page",
    "navigate_page",
    "select_frame",
    "click_element",
    "take_screenshot",
    "list_scripts",
    "get_script_source",
    "save_script_source",
    "search_in_sources",
    "set_breakpoint_on_text",
    "break_on_xhr",
    "remove_breakpoint",
    "list_breakpoints",
    "get_paused_info",
    "pause_or_resume",
    "step",
    "list_network_requests",
    "clear_network_requests",
    "get_request_initiator",
    "get_websocket_messages",
    "clear_site_data",
    "evaluate_script",
    "list_console_messages",
]


def find_binary() -> str | None:
    binary = shutil.which("js-reverse-mcp")
    if binary:
        return binary
    candidate = Path.home() / "AppData" / "Roaming" / "npm" / "js-reverse-mcp.cmd"
    return str(candidate) if candidate.exists() else None


def available() -> bool:
    return find_binary() is not None


def version() -> str:
    binary = find_binary()
    if not binary:
        return ""
    try:
        completed = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15, check=False)
        return (completed.stdout or completed.stderr or "").strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError):
        return ""


def configured_in() -> list[str]:
    return configured_clients("js-reverse")


def install_hint() -> str:
    return "npm install -g js-reverse-mcp"


def l2_contract() -> str:
    return (
        "Use break_on_xhr or set_breakpoint_on_text, then get_paused_info and step. "
        "Export request bodies, headers and the caller script with save_script_source. "
        "Rebuild the signature outside the browser and verify against fixtures before "
        "asking Scrapling to scale it."
    )
