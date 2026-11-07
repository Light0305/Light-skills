#!/usr/bin/env python
"""Register js-reverse-mcp in the common local MCP client configs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _default_appdata() -> Path:
    if os.name == "nt":
        return Path.home() / "AppData" / "Roaming"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path.home() / ".config"


def _native_path(value: str) -> str:
    """Convert a Git-Bash /c/... path to a Windows path when needed."""
    if os.name == "nt":
        match = re.match(r"^/([A-Za-z])/(.*)$", value)
        if match:
            return f"{match.group(1).upper()}:\\" + match.group(2).replace("/", "\\")
    return str(Path(value).resolve())


def _backup(path: Path, backup_root: Path) -> None:
    if not path.exists():
        return
    backup_root.mkdir(parents=True, exist_ok=True)
    safe = str(path).replace("\\", "_").replace("/", "_").replace(":", "_")
    shutil.copy2(path, backup_root / safe)


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _set_server(
    path: Path,
    root_key: str,
    server: dict,
    backup_root: Path,
    *,
    require_parent: bool = True,
) -> bool:
    if require_parent and not path.parent.exists():
        return False
    _backup(path, backup_root)
    data = _read(path)
    if root_key not in data or not isinstance(data[root_key], dict):
        data[root_key] = {}
    data[root_key]["js-reverse"] = server
    _write(path, data)
    return True


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register js-reverse-mcp in local clients.")
    parser.add_argument("--node", required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--appdata", default=str(_default_appdata()))
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument("--skip-codex", action="store_true")
    args = parser.parse_args(argv)

    node = _native_path(args.node)
    entry = _native_path(args.entry)
    if not Path(entry).exists():
        raise SystemExit(f"js-reverse entry not found: {entry}")

    home = Path(args.home)
    appdata = Path(args.appdata)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = home / ".light-crawl" / "backups" / f"mcp-{stamp}"

    stdio = {"command": node, "args": [entry]}
    vscode = {"type": "stdio", "command": node, "args": [entry]}
    opencode = {"type": "local", "command": [node, entry], "enabled": True}

    targets = [
        ("Cursor", home / ".cursor" / "mcp.json", "mcpServers", stdio),
        ("Windsurf", home / ".codeium" / "windsurf" / "mcp_config.json", "mcpServers", stdio),
        ("OpenCode", home / ".config" / "opencode" / "opencode.json", "mcp", opencode),
        ("Gemini CLI", home / ".gemini" / "settings.json", "mcpServers", stdio),
        ("Antigravity", home / ".gemini" / "antigravity" / "mcp_config.json", "mcpServers", stdio),
        ("Copilot CLI", home / ".copilot" / "mcp-config.json", "mcpServers", stdio),
        ("VS Code", appdata / "Code" / "User" / "mcp.json", "servers", vscode),
    ]

    updated: list[str] = []
    for name, path, root, server in targets:
        if _set_server(path, root, server, backup_root):
            updated.append(name)

    claude_cmd = shutil.which("claude")
    if not args.skip_claude and claude_cmd:
        check = _run([claude_cmd, "mcp", "list"])
        if "js-reverse" in (check.stdout or "") + (check.stderr or ""):
            updated.append("Claude Code")
        else:
            added = _run([claude_cmd, "mcp", "add", "--scope", "user", "js-reverse", "--", node, entry])
            if added.returncode == 0:
                updated.append("Claude Code")
            else:
                print(f"Claude Code registration failed: {added.stderr.strip()}")

    codex_cmd = shutil.which("codex")
    if not args.skip_codex and codex_cmd:
        check = _run([codex_cmd, "mcp", "list"])
        if "js-reverse" in (check.stdout or "") + (check.stderr or ""):
            updated.append("Codex")
        else:
            added = _run([codex_cmd, "mcp", "add", "js-reverse", "--", node, entry])
            if added.returncode == 0:
                updated.append("Codex")
            else:
                print(f"Codex registration failed: {added.stderr.strip()}")

    print("updated: " + ", ".join(updated))
    print(f"backup: {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
