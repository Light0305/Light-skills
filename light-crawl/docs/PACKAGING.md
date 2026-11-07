# Packaging and distribution

`scripts/package.py` builds a self-contained plugin and two standalone artifacts.

## Build

```powershell
python scripts\package.py
```

Artifacts:

| File | Use |
|---|---|
| `dist/light-crawl-marketplace/` | Local marketplace for Claude Code and Codex |
| `dist/light-crawl-plugin.zip` | Upload-ready plugin archive (`light-crawl/` root) |
| `dist/light-crawl-skill.zip` | Standalone Agent Skill archive (`light-crawl/` root) |
| `dist/light-crawl-marketplace.zip` | Marketplace repository archive |
| `dist/SHA256SUMS.txt` | Checksums for the three ZIPs |

The plugin archive contains the skill, CLI, references, templates, docs, examples
and benchmarks. It excludes `.venv`, `cases`, `runs`, `sites`, `dist` and
`benchmarks/results`.

## Claude Code

Local marketplace:

```bash
claude plugin marketplace add "D:\Light-Science\light-crawl\dist\light-crawl-marketplace"
claude plugin install light-crawl@light-crawl
```

From a Git marketplace, use the repository URL instead of the local path. The
marketplace declares `plugin` as a local source.

The plugin exposes one skill: `light-crawl`.

## Codex

Local marketplace:

```bash
codex plugin marketplace add "D:\Light-Science\light-crawl\dist\light-crawl-marketplace"
codex plugin add light-crawl@light-crawl
```

Codex reads the plugin's `.codex-plugin/plugin.json` and its `skills/` directory.

## Runtime installer

`install.ps1` / `install.sh` install the source copy, `.venv`, Scrapling and
browsers under `%USERPROFILE%\.light-crawl`. Plugin cache only holds skill files;
the runtime is separate. See [INSTALL.md](INSTALL.md).

## Standalone skill

Unzip `dist/light-crawl-skill.zip` and copy the `light-crawl/` directory into your
agent's skill directory, or run the bundled CLI from that directory:

```powershell
python run_light_crawl.py doctor
python run_light_crawl.py site list
```

## Validation performed

- Claude Code marketplace add/install in a temporary `CLAUDE_CONFIG_DIR`.
- Codex marketplace add/install in a temporary `CODEX_HOME`.
- Standalone skill ZIP extracted to a temp directory and `python
  run_light_crawl.py --version` / `site list`.
- Plugin manifests and required files checked by `scripts/package.py`.

## Versioning

The package version comes from `src/light_crawl/__init__.py`. Bump it with the
CLI/schema policy in [STABILITY.md](STABILITY.md), rebuild, and keep the
`SHA256SUMS.txt` with the release.

`dist/` is gitignored. Rebuild from a clean checkout; do not edit generated
files.
