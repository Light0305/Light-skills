# Architecture

## 1. Why this exists

Most agent scraping fails in one of two ways:

1. It treats every target as a browser task, so a 10,000-page crawl becomes 10,000
   model turns.
2. It treats reverse engineering as the first move, so a simple HTML page spends
   an hour in DevTools.

`light-crawl` is a control plane that decides **where to spend effort** and keeps
the result reproducible.

## 2. System boundary

```text
┌──────────────────────────────────────────────────────────────┐
│ Control plane: light-crawl                                   │
│ scope gate · router · state machine · artifact bus · report  │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
┌───────────────▼──────────────┐  ┌────────────▼───────────────┐
│ Acquisition                  │  │ Understanding              │
│ Scrapling Fetcher            │  │ js-reverse MCP             │
│ Scrapling StealthySession    │  │ reverse-skill JS SOP       │
│ Scrapling Spider             │  │ REA static/runtime tools   │
└───────────────┬──────────────┘  └────────────┬───────────────┘
                │                              │
┌───────────────▼──────────────────────────────▼───────────────┐
│ Knowledge plane                                               │
│ site packs · fixtures · signature patterns · regression tests │
└───────────────────────────────────────────────────────────────┘
```

The control plane is deterministic Python. The agent supplies judgment:
what data matters, whether a route is plausible, what a paused call frame means,
and whether a selector is semantically correct.

## 3. State machine

```text
INTAKE
  └─ create case, scope, target
PROBED
  └─ cheap HTTP classification, no browser
ROUTED
  └─ lane + delivery + confidence + next actions
CAPTURED
  └─ request, script, breakpoint, HAR or session artifact
UNDERSTOOD
  └─ endpoint/signature/dom contract described in evidence
REPRODUCED
  └─ replay/sign script works against fixtures
BUILT
  └─ spider or extractor exists
VERIFIED
  └─ fixtures + sample run pass
OPERATING
  └─ scheduled/observable run
LEARNED
  └─ site pack promoted
```

Backward transitions are rejected. A new hypothesis gets a new case, which keeps
the evidence for the old one intact.

## 4. Router

The router consumes a `ProbeResult` and a `TargetProfile`. It does not inspect the
live page again. Signals:

- status, content type, visible text, script count;
- SPA markers (`__NEXT_DATA__`, `__NUXT__`, initial state, empty root);
- API candidates and signature hints;
- Cloudflare/challenge/captcha markers;
- target kind, volume, auth and demo flag.

Priority:

1. Packaged/native target → `L4_APP`.
2. Probe failed → `L1_DYNAMIC` with low confidence and a network check.
3. Blocked → `L3_BLOCKED`.
4. Strong signature + API → `L2_SIGNED`.
5. JSON → `L0_API`.
6. SPA → `L1_DYNAMIC`.
7. Server HTML → `L0_STATIC`.
8. Unknown → cheapest plausible lane.

Confidence is explicit. A low-confidence route is a prompt to investigate, not a
license to scale.

## 5. Artifact bus

Tool outputs are not passed through the chat as the primary transport. They are
written to disk:

- `artifacts/` — hashed copies of important files;
- `har/` — network captures;
- `fixtures/` — redacted request/response samples;
- `repro/` — local reproduction code;
- `spider/` — acquisition code;
- `evidence.jsonl` — append-only observations and inferences.

`capture` has two engines:

- `http`: raw HTTP body, allow-listed headers, SHA-256, no browser;
- `scrapling`: rendered body, network summary (`url/status/bytes`) and browser
  seconds, with `real_chrome=True` by default and optional Cloudflare solving.

Benefits:

- the context stays small;
- the case is reviewable by a human;
- a later agent can resume without replaying the whole conversation;
- every report line can point to an artifact.

## 6. Browser ownership

Browsers are the most conflict-prone resource. Rules:

1. One process owns a given profile at a time.
2. `js-reverse` default profile and `--cloak` profile are physically separate.
3. Scrapling sessions use their own storage; do not point two tools at the same
   user-data directory.
4. When handing off, export cookies/state/HAR and let the next tool start clean.
5. If a tool supports CDP attach, attach to a browser owned by one component;
   otherwise export and replay.

The skill records this as a case-level decision, so a later agent does not open a
second browser against the same profile.

### 6.1 Profile locks

`sessions.py` implements a filesystem lease per profile. `session acquire`
writes `{profile, owner, pid, created_at, expires_at}`; a conflicting owner gets
exit code 3. `session release` is idempotent for the owner and refuses a
different owner. Expired leases are cleaned by `session cleanup`. The stealth
spider template acquires a lock before launching and releases it in `finally`.

## 7. Verification

A route is a hypothesis. A spider is code. Neither is evidence that the data is
correct.

The verification gate has three levels:

1. **Contract** — `templates/verify/verify_case.py` checks required files,
   artifact hashes and secret-like fixture keys.
2. **Fixture replay** — the reproduction script must pass known request/response
   pairs without network access.
3. **Live sample** — a 3-item sample against the authorized target, with rate
   limits, then a larger run.

`VERIFIED` requires at least a fixture. A production claim requires the live
sample and an operating record.

### 7.1 Benchmark

`benchmark.py` runs the router over five committed cases and compares lane,
delivery and minimum confidence. It also aggregates budgets for success rate,
requests per item, browser seconds per item, tokens per 1k items and drift
recovery. Missing metrics render as `-`, never zero.

The five cases are:

- `static_quotes` — actual probe and spider result from a public page;
- `api_json` — actual probe from a public JSON API;
- `signed_api` — synthetic signed-API signal pattern;
- `cloudflare` — synthetic 403/challenge signal pattern;
- `electron_asar` — local Electron source fixture.

The synthetic cases are signal snapshots, not claims about a production site.

The signed case has a real local reproduction loop: `benchmarks/signed_repro.py`
gets a 403 without a signature, computes `base64(page|ts|nonce:secret)`, and gets
a 200 with two orders. This is a deliberately weak demo signature; its purpose is
to prove the L2 workflow, not to model production crypto.

Benchmark cases can add `measured.json` to attach actual run values. The report
shows **Reference metrics (budgets)** and **Measured metrics** separately, with
separate aggregates. A missing measurement is `-`, not zero.

A benchmark case can also declare `"source_case": "quotes-capture"`. With
`benchmark --source-cases cases`, the runner reads the standard case's
`metrics` and lets them override the static measured file. This connects
`metrics record` to the benchmark without hand-copying numbers.

The tracked packs under `examples/site-packs/` are the reference shapes:

- `quotes` — static HTML, selectors, captured fixture, replay, regression;
- `books` — real paginated catalogue, 3 pages / 60 items, page-1 fixture;
- `github-api` — one JSON endpoint, field map, offline response fixture;
- `signed-local` — local signed fixture, explicit signer and unsigned → signed
  verification;
- `login-local` — local cookie/session login, private endpoint and
  `FetcherSession` reuse.

Each pack carries `schema_version`, `version` and `last_verified_at`.
`schema_version: 2` adds normalized entrypoints/policy defaults and a migration
record; `site migrate` is dry-run by default and `--write` applies it. `site list
--stale-days` marks a pack stale; `site check <pack> --write` runs the offline
verifier and updates the timestamp only on success. `scripts/drift.ps1` iterates
every pack, runs `site check`, and writes a JSON report under `runs/`.

`scripts/schedule-drift.ps1` only prints the registration command by default.
`-Register` creates a daily Windows task; `-Unregister` removes it. The tool
never registers a task silently.

The `login-local` pack persists the cookie jar through
`repro/session.py`. It keeps cookies only, never credentials, and verifies a new
`FetcherSession` can read the private endpoint from the saved state. On Windows
the state is DPAPI-encrypted with the current user's credentials; the raw file
does not contain the cookie value. Other platforms fall back to a 0600 JSON file
and mark the mode.

At v1.0 the documented CLI and schemas are frozen; see `docs/STABILITY.md` and
`docs/CLI.md`.

`site list` and `site show` read only the pack's `site.json` and filesystem
contract; they do not execute anything. `scripts/ci.ps1` (and `ci.sh`) run unit
tests, the routing benchmark, all offline pack verifiers and the local L3
browser check. Live pack runs are opt-in via `-Online`/`ONLINE=1` because they
need network access.

`light-crawl site run <pack>` executes only the conventional
`spider/spider.py --config ... --out ...` contract, then counts output items,
compares `expected_items` and runs `verify.py`. It does not execute arbitrary
commands from `site.json`; the run block is documentation, not a shell hook.

The L3 browser-capture check uses a local JS challenge that sets a cookie and
redirects to `/ok`. It proves the browser capture path follows a challenge flow;
it does not claim to solve real Cloudflare.

## 8. Learning loop

A case is useful once. A site pack is useful repeatedly.

`light-crawl learn` copies:

- spider code and config;
- reproduction scripts;
- redacted fixtures;
- probe and route JSON;
- a `site.json` with provenance and policy.

The next case for the same domain starts from the pack, not from zero. The pack
also becomes the regression target when a selector or signature changes.

## 9. Licensing strategy

The core is MIT. The four upstream projects are used as dependencies or as
separate processes:

- Scrapling: BSD-3-Clause, installed with pip.
- js-reverse-mcp: Apache-2.0, installed globally and registered as MCP.
- REA: MIT, invoked through CLI/MCP; commercial analysis engines are not bundled.
- reverse-skill: MIT main repository; its GPLv3 submodule and AGPL external tool
  are not copied.

Only small, stable MIT/Apache reference material should be vendored, with
attribution. Fast-moving code stays a dependency so upstream fixes can be taken
without a manual merge.

## 10. Known limitations

- The probe does not execute JavaScript. It can misclassify a JS shell, which is
  why the route has a confidence score and an explicit next action.
- Signature detection is heuristic. A `token` string is not proof of a signature.
- The generic spider is HTTP-first. Browser-rendered spiders need a custom
  `StealthySession` implementation.
- The verifier is structural; it does not prove semantic correctness.
- The router cannot prove authorization, robots compliance or Terms of Service
  compliance. Those remain human responsibilities.
- REA runs through a project-local `npx` wrapper; the first run populates npm's
  cache, and no global install is required.
- The benchmark's signed/Cloudflare cases are signal snapshots, not live sites.
- A profile lock prevents cooperative collisions; it cannot stop a non-cooperative
  process from launching the same browser directory.
