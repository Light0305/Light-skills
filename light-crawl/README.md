# light-crawl

A routing-first crawler skill for agents and humans.

`light-crawl` turns a target into a **repeatable, evidence-backed scraper**:
probe the cheap HTTP surface, choose an acquisition lane, use runtime reverse
engineering only when needed, reproduce the request, build a Scrapling spider,
verify it, and promote the reusable parts into a site pack.

It is not a single monolithic crawler. It is the control plane around four
specialists:

| Specialist | Role |
|---|---|
| [Scrapling](https://github.com/D4Vinci/Scrapling) | Production acquisition: HTTP, stealth browser, spiders, proxies, checkpoints |
| [js-reverse-mcp](https://github.com/zhizhuodemao/js-reverse-mcp) | Runtime eyes: scripts, breakpoints, call frames, XHR/WS, request export |
| [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | JS reverse-engineering SOP: Observe → Capture → Rebuild → Patch → DeepDive |
| [REA](https://github.com/morluto/rea) | Deep static/runtime analysis for Electron, APK, native, HAR/SAZ |

The new value is the routing, the artifact bus, the verification gate and the
learning loop — not a fifth copy of the same scraper.

## Install (one command)

The plugin install command only copies skill files. To install the Python
runtime, Scrapling and browsers in one go, use the installer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
```

With Claude/Codex plugin registration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -InstallClaude -InstallCodex
```

Everything, including global js-reverse MCP, REA cache warm-up and client plugin
registration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -Full
```

`-Full` is explicit because it changes global npm and MCP client configuration.

It installs to `%USERPROFILE%\.light-crawl` (`src/` + `venv/`), not into the
plugin cache. See [docs/INSTALL.md](docs/INSTALL.md) for the remote one-liner and
all options.

## Quick start

From this directory:

```bash
python run_light_crawl.py doctor
python run_light_crawl.py demo --out runs/demo --force
python run_light_crawl.py new-case my-case --target https://example.com --authorized
python run_light_crawl.py probe cases/my-case
python run_light_crawl.py route cases/my-case
python run_light_crawl.py report cases/my-case
```

Install the package once:

```bash
pip install -e .
light-crawl --help
```

Install the optional acquisition stack:

```bash
pip install -e ".[fetchers]"
scrapling install
```

`scrapling install` downloads the browser dependencies. The core `probe`,
`route`, `report` and `learn` commands use only the Python standard library and
work before Scrapling is installed. If the bundled-browser download is slow, run
`scripts/bootstrap.ps1 -SkipBrowsers`; `templates/spider/stealth_spider.py`
auto-selects system Chrome when present and otherwise uses the bundled browser.

## What it does

```text
INTAKE → PROBED → ROUTED → CAPTURED → UNDERSTOOD → REPRODUCED → BUILT → VERIFIED → OPERATING → LEARNED
```

| Lane | What it means | Default tool |
|---|---|---|
| `L0_STATIC` | Server-rendered HTML | Scrapling `Fetcher` |
| `L0_API` | JSON/API response | Scrapling `Fetcher` + replay |
| `L1_DYNAMIC` | JS shell / SPA / login state | Scrapling `StealthySession` |
| `L2_SIGNED` | signature, token, encryption | js-reverse + reverse-skill SOP |
| `L3_BLOCKED` | Cloudflare, 403/429, CAPTCHA | Scrapling stealth, then js-reverse cloak |
| `L4_APP` | Electron/APK/native/HAR | REA CLI, MCP on demand |
| `L5_SCALE` | ≥1000 items or repeated runs | Scrapling `Spider` |

The router is deliberately conservative: it chooses the cheapest plausible lane
and records why. A route is a hypothesis with a confidence score, not a finding.
`learn` only accepts a `VERIFIED` case, so an unverified spider cannot become a
site pack.

## Case layout

```text
cases/<slug>/
  case.json
  scope.md
  target.json
  probe.json
  route.json
  evidence.jsonl
  artifacts/
  har/
  fixtures/
  repro/
  spider/
  reports/report.md
```

Everything the next phase needs is a file. Tool output is copied into
`artifacts/` with a SHA-256, and every meaningful observation is appended to
`evidence.jsonl`.

## Commands

```bash
light-crawl doctor
light-crawl new-case <slug> --target <url> [--kind web] [--volume 1000] [--authorized]
light-crawl probe <case> [--timeout 20] [--header KEY=VALUE]
light-crawl capture <case> [--engine http|scrapling] [--max-bytes 10000000]
light-crawl route <case> [--lane L2_SIGNED] [--delivery spider]
light-crawl status <case>
light-crawl evidence <case> --source ... --action ... --observation ... [--artifact-file path]
light-crawl verify <case>
light-crawl advance <case> VERIFIED --note "fixtures and 3-item sample passed"
light-crawl metrics record <case> --items 100 --requests 120 --browser-seconds 50 --tokens 4000 --success-rate 0.95
light-crawl metrics show <case>
light-crawl session acquire js-reverse-default --owner my-case
light-crawl session status js-reverse-default
light-crawl session release js-reverse-default --owner my-case
light-crawl benchmark
light-crawl site list --stale-days 30
light-crawl site show examples/site-packs/books
light-crawl site check examples/site-packs/books --write
light-crawl site migrate --all
light-crawl site run examples/site-packs/quotes
light-crawl report <case>
light-crawl learn <case> [--domain example.com]
light-crawl adapters
light-crawl demo
```

All commands accept `--json` where the output is structured.

## Templates

- `templates/spider/generic_spider.py` — config-driven HTTP Scrapling spider.
- `templates/spider/stealth_spider.py` — browser-backed Scrapling spider for L1/L3.
- `templates/repro/replay.py` — replay a captured request without a browser.
- `templates/repro/sign_lab.py` — hash/HMAC/timestamp/canonical-JSON helpers.
- `templates/verify/verify_case.py` — offline contract and secret scan.
- `templates/case/` — scope and target documents.
- `examples/quotes/site.json` — a working `quotes.toscrape.com` config.
- `examples/site-packs/` — five tracked packs: static HTML (`quotes`), paginated
  HTML (`books`), JSON API (`github-api`), local signed reproduction
  (`signed-local`), and local login/session (`login-local`). All are on
  `schema_version: 2`.

Run the example after installing Scrapling:

```bash
python templates/spider/generic_spider.py --config examples/quotes/site.json --out runs/quotes.jsonl
```

## Design principles

1. **HTTP before browser.** A browser is expensive and noisy.
2. **API before DOM.** A page is often just a renderer for a clean JSON endpoint.
3. **Evidence before code.** Record the request, the script, the breakpoint and the inference.
4. **Compile, don't crawl by chat.** Bulk collection runs as code; the model handles exceptions.
5. **One browser owner per profile.** Export state/HAR instead of letting tools fight.
6. **Fixtures are the contract.** A signature is not rebuilt until fixtures pass.
7. **Site packs are the learning loop.** Every case should make the next case cheaper.
8. **No authorization, no traffic.** Open source is not target authorization.

## Distribution

Build the Claude/Codex plugin and standalone skill:

```powershell
python scripts\package.py
```

Artifacts:

- `dist/light-crawl-marketplace/` — local marketplace for Claude Code and Codex
- `dist/light-crawl-plugin.zip`
- `dist/light-crawl-skill.zip`
- `dist/light-crawl-marketplace.zip`
- `dist/SHA256SUMS.txt`

Install:

```powershell
# Claude Code
claude plugin marketplace add "D:\Light-Science\light-crawl\dist\light-crawl-marketplace"
claude plugin install light-crawl@light-crawl

# Codex
codex plugin marketplace add "D:\Light-Science\light-crawl\dist\light-crawl-marketplace"
codex plugin add light-crawl@light-crawl
```

See [docs/PACKAGING.md](docs/PACKAGING.md).

## v1.2 additions

- **All-client MCP registration** — `-InstallJsReverse` / `-Full` register
  js-reverse for Claude Code, Codex, Cursor, Gemini CLI, Antigravity, OpenCode,
  Windsurf, Copilot CLI and VS Code.
- **Online drift** — `scripts/drift.ps1 -Online` runs live spiders for packs that
  have one, with offline verifiers for local-only packs.
- **Installer portability** — `install.sh` now works in Git Bash on Windows.
- **Pack path resolution** — `site run/check/show/migrate` fall back to the skill
  directory when a relative pack path is not in the caller's cwd.

## v1.1 additions

- **One-command runtime installer** — `install.ps1` / `install.sh` install the
  source copy, `.venv`, Scrapling and browsers under
  `%USERPROFILE%\.light-crawl`; runtime is separate from the plugin cache.
- **Runtime-aware wrapper** — `scripts/light-crawl.ps1` resolves
  `LIGHT_CRAWL_HOME` / `%USERPROFILE%\.light-crawl` first.
- **Full install option** — `-InstallJsReverse`, `-WarmRea`, `-Full` for global
  js-reverse MCP, REA cache warm-up and client plugin registration.
- **Portable defaults** — `site list` and `benchmark` resolve to the skill
  directory, so they work from a plugin cache or arbitrary cwd.
- **Online drift** — `scripts/drift.ps1 -Online` runs live spiders for packs
  that have one, in addition to the offline verifiers.

## v1.0 additions

- **CLI freeze** — the documented commands/flags in [docs/CLI.md](docs/CLI.md)
  are stable; changes follow [docs/STABILITY.md](docs/STABILITY.md).
- **DPAPI login state** — the login-local cookie jar is encrypted with Windows
  DPAPI; the raw state file does not contain the cookie value.
- **Docs** — [docs/INDEX.md](docs/INDEX.md) indexes CLI, stability, scheduling,
  architecture and references.
- **Scheduling guide** — [docs/SCHEDULING.md](docs/SCHEDULING.md) covers
  dry-run, register, verify and remove for the drift task.

## v0.9 additions

- **Schema v2 migration** — `site migrate <pack>` (or `--all`) upgrades
  `site.json` from v1 to v2, adds entrypoints/policy defaults and records a
  migration block. `--write` is explicit.
- **Persisted login state** — `login-local/repro/session.py` saves/restores the
  cookie jar, then proves a new session can read `/private` without logging in
  again.
- **Drift scheduler** — `scripts/schedule-drift.ps1` prints the task command by
  default; only `-Register` creates the Windows scheduled task.

## v0.8 additions

- **Pack versioning** — `site.json` has `version` and `last_verified_at`;
  `site list` marks packs stale after `--stale-days` (default 30).
- **`site check`** — runs a pack's offline verifier and can update
  `last_verified_at` with `--write`.
- **Login-state pack** — `examples/site-packs/login-local/` proves a
  `FetcherSession` login, cookie reuse and a private endpoint.
- **Drift script** — `scripts/drift.ps1` checks every pack and writes a JSON
  report under `runs/`.

## v0.7 additions

- **Site-pack registry** — `light-crawl site list` and `site show <pack>` report
  domain, lane, expected items, spider/verify availability and path.
- **CI** — `scripts/ci.ps1` runs unit tests, the routing benchmark, all offline
  pack verifiers and the local L3 browser capture. `-Online` adds live pack runs.
- **Second real static pack** — `books.toscrape.com` with 3-page pagination,
  60 items and an offline page-1 fixture.

## v0.6 additions

- **L3 browser capture check** — `benchmarks/l3_capture_check.py` follows a local
  JS challenge (`/js-challenge` → cookie → `/ok`) with the scrapling browser
  engine and saves the final body.
- **`light-crawl site run <pack>`** — runs a pack's spider, counts the output,
  compares `expected_items`, and runs the pack's offline `verify.py`.
- **Three tracked packs** — static (`quotes`), API (`github-api`), and signed
  (`signed-local`), each with an offline regression path.

## v0.5 additions

- **Browser capture** — `light-crawl capture --engine scrapling` uses
  `StealthySession`, saves the rendered DOM/body, a `network` summary in
  `response.meta.json`, and `last_capture_browser_seconds`.
- **Benchmark source cases** — a benchmark case can point at a normal case with
  `"source_case": "quotes-capture"`; `benchmark --source-cases cases` reads that
  case's real `metrics` and overrides the static `measured.json`.
- **Tracked site pack** — `examples/site-packs/quotes/` contains a real captured
  page, selectors, replay, and an offline regression check.

## v0.4 additions

- **Signed reproduction** — the local signed fixture now validates
  `base64(page|ts|nonce:secret)`. `benchmarks/signed_repro.py` proves the full
  sequence: unsigned 403 → compute signature → signed 200.
- **Measured benchmark** — `measured.json` next to a benchmark case adds actual
  run values; the report shows budgets and measurements separately.
- **Better JS discovery** — the probe now recognizes backtick/template-literal
  API URLs, not only single/double-quoted ones.

## v0.3 additions

- **capture** — save `fixtures/request.json`, the raw response body and a
  redacted `response.meta.json`, then append evidence.
- **verify** — code-level case contract check: required files, phase gates,
  artifact hashes, fixture JSON and secret-like keys.
- **metrics** — record items, requests, browser seconds, tokens, success rate and
  drift recovery; compute per-item/per-1k values and attach them to the case.
- **live fixtures** — `benchmarks/live_check.py` starts local signed-API and
  Cloudflare-style servers and verifies the L2/L3 routes end to end.

## v0.2 additions

- **Profile broker** — `light-crawl session acquire/status/release` enforces one
  owner per browser profile; the stealth spider obtains and releases the lock in
  code.
- **Benchmark** — five routing cases (static, API, signed, Cloudflare, Electron)
  plus success-rate, request, browser-time, token and drift budgets.
- **Project-local REA** — `scripts/rea.ps1` runs `npx -y rea-agents@latest`; no
  global npm install is required.
- **Bundled browser fix** — `scrapling install` works through the Playwright CDN
  or the npmmirror `PLAYWRIGHT_DOWNLOAD_HOST`; system Chrome remains
  auto-selected when present.

Run the benchmark:

```bash
light-crawl benchmark
```

## Requirements

- Python 3.11+
- Optional: Scrapling with browsers for L0/L1/L3/L5
- Optional: Node.js 20.19+ and js-reverse MCP for L2
- Optional: REA CLI/MCP for L4
- Optional: Chrome stable

`light-crawl doctor` reports what is present and what is missing.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests use a local HTTP server and do not touch the network.

## License

MIT for the original code and documentation in this repository. The four
upstream projects keep their own licenses; see `THIRD_PARTY_NOTICES.md`.

This skill does not grant permission to access any website. Use it only on
targets you own or are authorized to test, and respect robots.txt, Terms of
Service, rate limits and privacy law.
