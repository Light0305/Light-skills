# Stability policy (v1.0)

## CLI freeze

The commands and flags documented in [CLI.md](CLI.md) are **stable** as of
`v1.0.0`. `v1.1.x` / `v1.2.x` are additive: runtime installer flags, all-client MCP
registration, online drift and portable defaults do not remove or rename
existing CLI surface.
`v1.3.0` adds explicit execution receipts and research dataset handoffs. Old case
layouts and commands stay readable; missing execution evidence remains a warning,
not retroactive certification. Promotion and stale-input rejection are validation
fixes. Capture result paths now identify versioned snapshots; top-level fixture
paths remain working copies for compatibility.

| Change | Version bump |
|---|---|
| Add a command or optional flag | minor |
| Add a JSON field | minor |
| Change default output text | minor |
| Remove/rename a command or required flag | major |
| Change JSON field meaning | major |
| Change exit-code meaning | major |

Deprecations are announced for at least one minor release before removal.

## Data schemas

| File | Schema | Notes |
|---|---|---|
| `case.json` | 1 | Case state; `schema_version` field |
| `site.json` | 2 | Site pack; use `site migrate` from v1 |
| `benchmark case.json` | 1 | Routing expectations and budgets |
| `measured.json` | 1 | Optional measured metrics |
| check `receipt.json` | 1 | Explicit local execution, bound inputs and logs |
| `dataset-v*.json` | 1 | Selected files and recorded scientific metadata |

`site migrate` is the supported upgrade path for `site.json`. It is dry-run by
default and writes only with `--write`.

## Pack contract

A runnable site pack has:

- `site.json` (schema 2);
- `spider/spider.py` and `spider/site.json` for `site run`;
- `verify.py` for offline regression;
- optional `repro/` and `fixtures/`.

The `run.command` field is documentation. `site run` executes only the
conventional spider contract:
`spider/spider.py --config spider/site.json --out <file>`.

## What is not frozen

- heuristic routing thresholds;
- the exact wording of reports;
- internal Python module layout (imports outside the documented CLI are not a
  public API);
- third-party tool behavior and output.

## Compatibility

- Python 3.11+.
- Scrapling is optional for the core probe/route/report/site-registry commands.
- Browser capture, `site run` on real packs and the live L3 check need Scrapling
  and a browser.
