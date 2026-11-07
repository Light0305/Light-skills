# Changelog

All notable changes to `light-crawl` are recorded here.

## 1.3.0 — 2026-11-06

- Preserve versioned captures and hashed probe/route observations across retries and lane changes; archive directory inventories and prevent artifact-name overwrites.
- Bind selected local checks to actual code, fixtures, scope and logs. Phase labels alone do not prove verification. Promotion requires a current receipt; raw capture archives remain local.
- Add `dataset export/check` for research scope, fields, coverage and source/derivation links without copying large data. Truncated/error responses remain diagnostic inputs.
- Reject stale output reuse; validate JSONL/CSV and fail on missing or invalid output. Handle empty Scrapling version output.
- Enforce recorded scope before probe/capture. Preserve old layouts without inventing missing historical checks.

## 1.2.2 — 2026-10-25

### Fixed

- **macOS/Linux login pack:** the verifier no longer requires DPAPI ciphertext on
  non-Windows; it now checks `plain-0600` and the 0600 mode. `ctypes.wintypes` is
  imported only on Windows.
- **macOS/Linux doctor:** VS Code config, Playwright cache, Chrome discovery and
  the REA wrapper path are platform-aware.
- **Browser auto-selection:** system Chrome is used only when present; otherwise
  Scrapling's bundled browser is selected.
- **macOS/Linux VS Code MCP path:** `register_mcp.py` uses the platform app-data
  directory; Git-Bash `/c/...` paths are normalized on Windows.
- **Thin JS pages:** probe now classifies a page with little visible text and a
  large inline script as `spa_shell` instead of `static_html`.
- **Cross-shell installer:** `install.sh` detects `Scripts/python.exe` and falls
  back to Python for archive download/extraction when `curl`/`unzip` are absent.
- **Shell wrapper:** `scripts/light-crawl.sh` resolves Windows venv layouts too.

## 1.2.1 — 2026-10-25

### Fixed

- `install.ps1` / `install.sh` now run `claude plugin update` after install so a
  reinstall records the new plugin version instead of leaving the old one.
- `site run`/`site check` resolve relative pack paths against the skill
  directory when the caller's cwd does not contain the pack.
- `quotes` pack page budget matches its expected item count.
- `register_mcp.py` resolves Windows `.cmd` shims for Claude/Codex.

## 1.2.0 — 2026-10-25

### Added

- MCP registration now covers Claude Code, Codex, Cursor, Gemini CLI,
  Antigravity, OpenCode, Windsurf, Copilot CLI and VS Code, via
  `scripts/register_mcp.py`.
- `install.ps1 -InstallJsReverse` and `-Full` call the all-client registration
  path.
- `drift.ps1 -Online` runs live spiders for spider packs and keeps offline
  verifiers for the local-only packs.
- Pack arguments (`site run/check/show/migrate`) resolve against the skill
  directory when not found in the caller's cwd.
- `site run` / `site check` use the user-level runtime Python for subprocesses.

### Fixed

- `install.sh` works in Git Bash on Windows (venv `Scripts/python.exe`, Python
  fallback).
- `register_mcp.py` resolves Windows `.cmd` shims for Claude/Codex.
- `quotes` pack page budget matches its expected item count.

## 1.1.1 — 2026-10-25

### Fixed

- `site check` and `site run` now use the user-level runtime Python for their
  subprocesses when `LIGHT_CRAWL_HOME` / `%USERPROFILE%\.light-crawl` exists.
  This makes plugin-cache invocations work without a local `.venv`.
- `site list` / `benchmark` defaults resolve to the skill directory, not the
  caller's cwd.
- Installer docs clarify that `-InstallJsReverse` only registers Claude/Codex MCP
  when those client flags are also set.
- `drift.ps1 -Online` runs live spider packs; `quotes` pack max-page budget now
  matches its expected item count.

## 1.1.0 — 2026-10-25

### Added

- `install.ps1` / `install.sh`: one-command runtime install to
  `%USERPROFILE%\.light-crawl` (source copy, venv, Scrapling, browsers).
- Optional `-InstallClaude` / `-InstallCodex` plugin registration.
- Runtime-aware `scripts/light-crawl.ps1`: uses `LIGHT_CRAWL_HOME` or
  `%USERPROFILE%\.light-crawl` before falling back to a local `.venv`.
- `docs/INSTALL.md`.
- `install.ps1` / `install.sh` options for `js-reverse-mcp` and REA cache warm-up:
  `-InstallJsReverse`, `-WarmRea`, and `-Full` (all options).
- CLI defaults for `site list` and `benchmark` resolve to the skill directory,
  so they work from a plugin cache or arbitrary cwd.

## 1.0.0 — 2026-10-25

### Added

- CLI reference ([docs/CLI.md](docs/CLI.md)), stability policy
  ([docs/STABILITY.md](docs/STABILITY.md)), documentation index
  ([docs/INDEX.md](docs/INDEX.md)) and scheduling guide
  ([docs/SCHEDULING.md](docs/SCHEDULING.md)).
- Windows DPAPI encryption for the login-local cookie state; raw state bytes no
  longer contain the cookie value.
- `tests/test_login_encryption.py` for DPAPI round-trip and no-plaintext checks.

### Changed

- Version frozen at `1.0.0`; documented commands/flags are stable under the
  policy.

## 0.9.0 — 2026-10-25

### Added

- `site migrate` for `site.json` schema v1 → v2; dry-run by default, `--write`
  applies, `--all` migrates a root.
- `site list` shows schema and version; all tracked packs migrated to v2.
- `login-local/repro/session.py`: cookie save/restore and a second-session
  `/private` check.
- `scripts/schedule-drift.ps1`: dry-run by default, `-Register` creates a daily
  Windows scheduled task, `-Unregister` removes it.

## 0.8.0 — 2026-10-25

### Added

- Site-pack versioning: `version` and `last_verified_at` in `site.json`;
  `site list --stale-days` marks stale packs.
- `site check <pack> [--write]`: runs the offline verifier and optionally updates
  `last_verified_at`.
- `examples/site-packs/login-local/`: demo login, cookie reuse, private endpoint
  and a `FetcherSession`-based reproduction.
- `scripts/drift.ps1`: checks every pack, writes a JSON report under `runs/`.

## 0.7.0 — 2026-10-25

### Added

- `site list` and `site show`: a registry view over site packs with domain, lane,
  expected items, spider/verify availability and path.
- `books.toscrape.com` pack: real paginated catalogue, 3 pages / 60 items,
  offline page-1 fixture and regression.
- `scripts/ci.ps1` / `scripts/ci.sh`: unit tests, benchmark, all offline pack
  verifiers and the L3 browser capture; `-Online`/`ONLINE=1` adds live pack runs.

## 0.6.0 — 2026-10-25

### Added

- `light-crawl site run <pack>`: runs `spider/spider.py` with controlled args,
  counts output items, compares `expected_items`, and runs `verify.py`.
- Local L3 browser-capture check: a JS challenge sets a cookie and redirects to
  `/ok`; the scrapling capture engine follows it and saves the final body.
- `examples/site-packs/github-api/`: real JSON API pack with field map and
  offline regression.
- `examples/site-packs/signed-local/`: L2 pack with `repro/sign.py` and an
  end-to-end unsigned → signed verification.
- `examples/site-packs/README.md` index.

## 0.5.0 — 2026-10-25

### Added

- Browser capture engine: `light-crawl capture --engine scrapling` saves the
  rendered body, network summary and browser time.
- Benchmark `source_case` support: actual case `metrics` override static
  `measured.json` values; `--source-cases` controls the lookup root.
- Tracked `examples/site-packs/quotes/` pack with captured HTML, selectors,
  replay, site metadata and an offline regression check.

### Changed

- `benchmark` report distinguishes budget aggregates from measured aggregates.

## 0.4.0 — 2026-10-25

### Added

- Local signed-API fixture now validates a deterministic
  `base64(page|ts|nonce:secret)` signature and rejects stale timestamps.
- `benchmarks/signed_repro.py`: unsigned 403 → compute signature → signed 200.
- `measured.json` support in benchmark cases; the report now shows budget and
  measured metric tables plus separate aggregates.

### Fixed

- Probe API discovery recognizes backtick/template-literal URLs and `fetch(...)`
  calls, not only single/double-quoted literals.

## 0.3.0 — 2026-10-25

### Added

- `capture` command: saves `fixtures/request.json`, the raw response body and a
  redacted `response.meta.json`; appends evidence and capture metrics.
- `verify` command and `light_crawl.verify` module: required files, phase gates,
  artifact hashes, fixture JSON and secret-like key checks.
- `metrics record/show`: items, requests, browser seconds, tokens, success rate
  and drift recovery, with computed per-item/per-1k values.
- Local runnable benchmark fixtures for signed API and Cloudflare-style
  challenges, plus `benchmarks/live_check.py`.
- New-case now creates an empty `evidence.jsonl` so the contract is valid from
  day one.

### Changed

- The `templates/verify/verify_case.py` script is now a thin wrapper around the
  package verifier.
- Validation checklist and docs now use `light-crawl verify` and
  `light-crawl metrics`.

## 0.2.0 — 2026-10-25

### Added

- Filesystem session broker: `session acquire`, `status`, `release`, `cleanup`.
  Conflicting owners get exit code 3; stale leases expire.
- Stealth spider acquires a profile lock before launch and releases it in
  `finally`.
- Five-case routing benchmark: static, API, signed, Cloudflare, Electron.
- Benchmark aggregates success rate, requests/item, browser seconds/item,
  tokens/1k items and drift recovery; missing metrics render as `-`.
- Project-local REA launcher (`scripts/rea.ps1`) using `npx`, so no global npm
  install is required.
- Scrapling browser install guidance for slow CDNs
  (`PLAYWRIGHT_DOWNLOAD_HOST`), plus `real_chrome=True` fallback.

### Changed

- `doctor` now checks the bundled Scrapling browser and treats the project-local
  REA npx wrapper as OK.
- `learn` remains gated on `VERIFIED`.

## 0.1.0 — 2026-10-25

### Added

- Routing-first case workflow: `INTAKE` through `LEARNED`.
- Dependency-free HTTP probe with static/API/SPA/blocked classification.
- Router for `L0_STATIC`, `L0_API`, `L1_DYNAMIC`, `L2_SIGNED`, `L3_BLOCKED`,
  `L4_APP`, with spider delivery at volume.
- Case state, append-only evidence ledger, artifact hashing and report renderer.
- Site-pack promotion with fixtures, reproduction code and provenance.
- Doctor checks for Python, Scrapling, Chrome, js-reverse MCP, client configs,
  REA and git.
- `advance` command and `--artifact-file` evidence attachment.
- `learn` gate: only a `VERIFIED` case can become a site pack.
- Templates: HTTP spider, stealth-browser spider, request replay, signature
  helpers, case verifier.
- Offline demo case and local-HTTP tests.

### Design notes

- Scrapling is a pip dependency, not vendored.
- js-reverse is an MCP server, not vendored.
- REA is a CLI/MCP dependency, not vendored.
- reverse-skill is used as a methodology reference; its GPLv3/AGPL parts are not
  copied.
