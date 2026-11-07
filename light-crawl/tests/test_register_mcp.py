from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "register_mcp.py"


class RegisterMcpTests(unittest.TestCase):
    def test_registers_common_json_clients(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            appdata = home / "AppData"
            for relative in (
                ".cursor",
                ".gemini/antigravity",
                ".codeium/windsurf",
                ".config/opencode",
                ".copilot",
                "AppData/Code/User",
            ):
                (home / relative).mkdir(parents=True, exist_ok=True)
            (home / ".cursor/mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            (home / ".gemini/settings.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            (home / ".gemini/antigravity/mcp_config.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            (home / ".codeium/windsurf/mcp_config.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            (home / ".config/opencode/opencode.json").write_text('{"mcp": {}}', encoding="utf-8")
            (home / ".copilot/mcp-config.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            (appdata / "Code/User/mcp.json").write_text('{"servers": {}}', encoding="utf-8")
            entry = home / "fake-entry.js"
            entry.write_text("x", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--node",
                    sys.executable,
                    "--entry",
                    str(entry),
                    "--home",
                    str(home),
                    "--appdata",
                    str(appdata),
                    "--skip-claude",
                    "--skip-codex",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            cursor = json.loads((home / ".cursor/mcp.json").read_text(encoding="utf-8"))
            self.assertIn("js-reverse", cursor["mcpServers"])
            opencode = json.loads((home / ".config/opencode/opencode.json").read_text(encoding="utf-8"))
            self.assertTrue(opencode["mcp"]["js-reverse"]["enabled"])
            vscode = json.loads((appdata / "Code/User/mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(vscode["servers"]["js-reverse"]["type"], "stdio")


if __name__ == "__main__":
    unittest.main()
