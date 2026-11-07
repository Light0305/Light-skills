# Benchmark

The benchmark has two jobs:

1. prove the router still chooses the intended lane;
2. keep a small, explicit budget for the cost of each lane.

```powershell
.\.venv\Scripts\light-crawl.exe benchmark
```

Outputs:

- `benchmarks/results/results.json`
- `benchmarks/results/report.md`

## Cases

| Case | Expected | Provenance |
|---|---|---|
| `static_quotes` | `L0_STATIC` / `single` | Actual probe from `quotes.toscrape.com`; actual spider run produced 10 items |
| `api_json` | `L0_API` / `single` | Actual probe from the public GitHub API (`/repos/python/cpython`) |
| `signed_api` | `L2_SIGNED` / `single` | Synthetic signed-API pattern: API-shaped traffic plus `sign`/`timestamp`/`nonce` hints |
| `cloudflare` | `L3_BLOCKED` / `single` | Synthetic 403 challenge snapshot with Cloudflare headers and challenge body |
| `electron_asar` | `L4_APP` / `single` | Local Electron source fixture under `benchmarks/fixtures/electron-demo` |

The two synthetic cases exist because a live signed API and a live Cloudflare
challenge are not safe to depend on in CI. They are snapshots of the signals the
router sees, not claims about a specific production site.

The same two patterns can be exercised end to end against local servers:

```powershell
python benchmarks/live_check.py
```

This starts a signed-API fixture and a Cloudflare-style challenge fixture, probes
them, and checks `L2_SIGNED` / `L3_BLOCKED`.

The signed fixture also has a full reproduction sequence:

```powershell
python benchmarks\signed_repro.py
```

It makes an unsigned request (403), computes the page/ts/nonce/sign chain, and
makes a signed request (200 with two orders). This is the L2 contract in
miniature.

## Measured metrics

Add a `measured.json` next to `case.json` to attach actual run values:

```json
{
  "source": "generic_spider.py --max-pages 1",
  "items": 10,
  "requests": 1,
  "browser_seconds": 0,
  "tokens": 0,
  "success_rate": 1.0,
  "drift_recovery_rate": 1.0
}
```

The benchmark report shows a separate **Measured metrics** table and measured
aggregates. A missing `measured.json` renders as `-`, never as zero. The
`case.json` metrics remain budgets, not measurements.

To pull actual metrics from a normal case created with `light-crawl new-case` and
`light-crawl metrics record`, add:

```json
{
  "source_case": "quotes-capture"
}
```

Then run:

```powershell
light-crawl benchmark --source-cases cases
```

Source-case metrics override `measured.json` when both exist. The report includes
`measured_from_source_cases` in `results.json` so you can tell where the numbers
came from.

## Metrics

`metrics` in each `case.json` are **budgets or measured values**, not a promise:

| Metric | Meaning |
|---|---|
| `success_rate` | Fraction of expected fields extracted |
| `requests_per_item` | HTTP requests per item |
| `browser_seconds_per_item` | Browser wall time per item |
| `tokens_per_1k_items` | Agent tokens per 1,000 items |
| `drift_recovery_rate` | Fraction of selector/signature drifts caught by fixtures |

A missing value is rendered as `-`, never as zero. Add measured values only after
a real run.

## Add a case

```text
benchmarks/cases/my-case/
  case.json
  probe.json
```

`case.json`:

```json
{
  "slug": "my-case",
  "target": {
    "url": "https://example.com/",
    "kind": "web",
    "volume": 100,
    "auth": "none",
    "authorized": true
  },
  "expected": {
    "lane": "L0_STATIC",
    "delivery": "single",
    "min_confidence": 0.7
  },
  "metrics": {
    "success_rate": 1.0,
    "requests_per_item": 0.1,
    "browser_seconds_per_item": 0,
    "tokens_per_1k_items": 0,
    "drift_recovery_rate": 1.0
  },
  "notes": "What this case proves."
}
```

`probe.json` is the output of `light-crawl probe` or `probe_target(...)`.
