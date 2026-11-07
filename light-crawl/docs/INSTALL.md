# Install

There are two different install layers. They are not the same command.

| Layer | What it installs | What it does not install |
|---|---|---|
| Plugin install | Skill/plugin files into Claude/Codex | Python, Scrapling, browser, MCP servers |
| Runtime install | Python venv, Scrapling, browser, project copy | Claude/Codex plugin registration |

`install.ps1` / `install.sh` do the runtime layer. Add `-InstallClaude` /
`-InstallCodex` (or `--install-claude` / `--install-codex`) to also register the
plugin.

## Local checkout

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -InstallClaude -InstallCodex
```

Linux/macOS:

```bash
./install.sh
./install.sh --install-claude --install-codex
```

Installs to `%USERPROFILE%\.light-crawl` (`~/.light-crawl` on Unix):

```text
.light-crawl/
  src/light-crawl/   # source copy
  venv/              # Python runtime
```

## Remote, after publishing the repo

The installer needs the repository URL when it is not running from a checkout.
Set it explicitly:

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/OWNER/light-crawl/main/install.ps1"))) `
  -RepoUrl "https://github.com/OWNER/light-crawl" `
  -InstallClaude -InstallCodex
```

Or set the environment variable and use the simpler form:

```powershell
$env:LIGHT_CRAWL_REPO = "https://github.com/OWNER/light-crawl"
irm "https://raw.githubusercontent.com/OWNER/light-crawl/main/install.ps1" | iex
```

Replace `OWNER` with the account or organization that hosts the repository.

### Truly "everything" (explicit)

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/OWNER/light-crawl/main/install.ps1"))) `
  -RepoUrl "https://github.com/OWNER/light-crawl" `
  -Full
```

`-Full` means:

- runtime + Scrapling + browser;
- global `js-reverse-mcp` plus MCP registration for Claude/Codex;
- REA npx cache warm-up;
- Claude and Codex plugin registration.

This is the one that changes global npm and client MCP configuration. It is
deliberately not the default.

## Options

| Option | Meaning |
|---|---|
| `-SourcePath <dir>` | Install from a local checkout |
| `-RepoUrl <url>` | Download a GitHub archive |
| `-RuntimeHome <dir>` | Override `%USERPROFILE%\.light-crawl` |
| `-SkipBrowsers` | Skip `scrapling install` |
| `-InstallClaude` | Add the local marketplace and install the plugin |
| `-InstallCodex` | Add the local marketplace and install the plugin |
| `-InstallJsReverse` | `npm install -g js-reverse-mcp`; register for Claude/Codex/Cursor/Gemini/Antigravity/OpenCode/Windsurf/Copilot/VS Code where config dirs exist |
| `-WarmRea` | Populate the npm cache with `rea-agents` via `npx` |
| `-Full` | Enable all install options above |

`install.sh` uses `--source`, `--repo`, `--runtime-home`, `--skip-browsers`,
`--install-claude`, `--install-codex`, `--install-js-reverse`, `--warm-rea`,
`--full`. It is tested in Git Bash on Windows as well as POSIX shells (the venv
layout is detected as `Scripts/python.exe` or `bin/python`).

## After install

```powershell
& "$env:USERPROFILE\.light-crawl\src\light-crawl\scripts\light-crawl.ps1" doctor
& "$env:USERPROFILE\.light-crawl\src\light-crawl\scripts\light-crawl.ps1" site list
```

If you used a custom `-RuntimeHome`, set `LIGHT_CRAWL_HOME` so the plugin
wrapper resolves it.

## Platform notes

| Platform | Runtime | Login state | Browser |
|---|---|---|---|
| Windows | `install.ps1` / PowerShell | DPAPI, cookie-only | System Chrome, then bundled |
| macOS | `install.sh` / bash | `plain-0600` JSON | System Chrome/Chromium, then bundled |
| Linux | `install.sh` / bash | `plain-0600` JSON | `google-chrome`/`chromium`, then bundled |

The `plain-0600` file contains cookies only, never credentials. Treat it as a
secret and keep it outside version control.

## What the one-line command does not do

- It does not install `js-reverse-mcp`; that remains a separate MCP choice.
- It does not install REA globally; the skill uses `npx` on first use.
- It does not register a scheduled task.
- It does not grant authorization to any target.
