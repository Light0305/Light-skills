# CLI reference (v1.3)

`light-crawl` is the command-line control plane. The package entry point is
`light-crawl`; from a source checkout without installation use
`python run_light_crawl.py` or `scripts/light-crawl.ps1`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Operation, output-validation or verification/benchmark failure |
| `2` | User/input error |
| `3` | Browser-profile lock conflict |

## Case workflow

### `doctor`

```bash
light-crawl doctor [--json] [--strict]
```

Checks Python, Node, Scrapling, bundled browser, system Chrome, js-reverse,
client configs, REA wrapper/skill and git. `--strict` fails on warnings.

### `new-case`

```bash
light-crawl new-case <slug> --target <url> [--kind web] [--volume 1000]
  [--auth none] [--geo <region>] [--authorized] [--notes <text>]
  [--case-root cases] [--force] [--json]
```

Creates `cases/<slug>/` with `case.json`, `scope.md`, `target.json`,
`evidence.jsonl` and artifact directories.

### `probe`

```bash
light-crawl probe <case> [--timeout 20] [--header KEY=VALUE] [--case-root cases] [--json]
```

Cheap HTTP classification. No browser. Writes `probe.json`, a hashed historical
observation and an evidence entry. Case probe/capture require recorded scope.
Transport errors return `1`; observed HTTP errors can still be classified.
Repeated observations preserve history without moving phase backwards.

### `capture`

```bash
light-crawl capture <case> [--engine http|scrapling] [--timeout 20]
  [--max-bytes 10000000] [--header KEY=VALUE] [--headed]
  [--solve-cloudflare] [--wait-selector <css>] [--case-root cases] [--json]
```

Writes hashed `fixtures/captures/CAP-*/request.json`, response body and metadata,
an evidence entry and `last_capture_*` metrics. Returned paths identify this
snapshot. Top-level `fixtures/request.json` / `response.*` remain compatibility
working copies. `http` is default; `scrapling` uses the browser and records a
network summary. Metadata records truncation and representation; body-size limits
do not bound total browser memory. Header filtering does not remove secrets/PII
from bodies, URLs or screenshots.

### `route`

```bash
light-crawl route <case> [--lane L0_STATIC|L0_API|L1_DYNAMIC|L2_SIGNED|L3_BLOCKED|L4_APP]
  [--delivery single|spider] [--case-root cases] [--json]
```

Writes `route.json` and a hashed historical observation, records reasons/confidence
and advances to at least `ROUTED`. Later lane revisions preserve current progress.

### `status`

```bash
light-crawl status <case> [--case-root cases] [--json]
```

Shows phase, lane, delivery, evidence count, artifact count and blockers.

### `evidence`

```bash
light-crawl evidence <case> --source <tool> --action <action> --observation <text>
  [--phase <PHASE>] [--inference <text>] [--confidence low|medium|high]
  [--artifact <label>] [--artifact-file <path>] [--case-root cases] [--json]
```

Appends an evidence entry. `--artifact-file` copies and hashes the file into
`artifacts/`.

### `verify`

```bash
light-crawl verify <case> [--case-root cases] [--json]
light-crawl verify <case> --run-check repro/verify.py [--timeout 60] [--json]
```

Offline contract check: required files, phase gates, artifact hashes, fixture
JSON and secret-like keys. Exit `1` on failure. Default verification does not
execute code or establish that a sample/replay passed. `--run-check` explicitly
executes a trusted Python check directly under repro/, spider/ or fixtures/; its
actions must stay within task scope. Receipts/logs stay under `reports/checks/`,
with `reports/verification.json` pointing at the latest. Changed inputs or failed
execution invalidate that check.

### `advance`

```bash
light-crawl advance <case> <PHASE> [--note <text>] [--case-root cases] [--json]
```

Forward-only phase transition: `INTAKE`, `PROBED`, `ROUTED`, `CAPTURED`,
`UNDERSTOOD`, `REPRODUCED`, `BUILT`, `VERIFIED`, `OPERATING`, `LEARNED`.
`learn` only accepts `VERIFIED` or later.

### `metrics`

```bash
light-crawl metrics record <case> --items N --requests N --browser-seconds N
  --tokens N --success-rate 0..1 --drift-recovery 0..1
  [--note <text>] [--case-root cases] [--json]
light-crawl metrics show <case> [--case-root cases] [--json]
```

Computes `requests_per_item`, `browser_seconds_per_item` and
`tokens_per_1k_items`.

### `report`

```bash
light-crawl report <case> [--case-root cases] [--json]
```

Writes `reports/report.md`.

### `learn`

```bash
light-crawl learn <case> [--domain <domain>] [--sites-root sites]
  [--force] [--case-root cases] [--json]
```

Requires `VERIFIED` or later, spider/reproduction code, a current executed check
and valid artifacts. Review flagged secrets. Raw `fixtures/captures/` archives
are excluded; prepare curated working fixtures for a reusable site pack.

## Research data

```bash
light-crawl dataset export <case> --spec <dataset-spec.json> --out <dataset-v01.json>
light-crawl dataset check <dataset-v01.json>
```

Both return JSON. Export explicitly selected files, hashes, source evidence and
research metadata without copying large data. Output must be new. Check validates
retained files and selected source records, warning if the source case is
unavailable. It does not re-contact the target or certify coverage/statistics.
See [research-data.md](../references/research-data.md).

## Sessions

```bash
light-crawl session status [profile] [--root .light-crawl/sessions] [--json]
light-crawl session acquire <profile> --owner <label> [--ttl 3600] [--note <text>]
  [--force] [--root .light-crawl/sessions] [--json]
light-crawl session release <profile> --owner <label> [--root .light-crawl/sessions] [--json]
light-crawl session cleanup [--root .light-crawl/sessions] [--json]
```

One owner per browser profile. Conflicts exit `3`.

## Benchmark

```bash
light-crawl benchmark [--cases benchmarks/cases] [--source-cases cases]
  [--out benchmarks/results] [--json]
```

Writes `results.json` and `report.md`; budget and measured metrics are reported
separately.

## Site packs

```bash
light-crawl site list [--root examples/site-packs] [--stale-days 30] [--json]
light-crawl site show <pack> [--json]
light-crawl site check <pack> [--write] [--timeout 120] [--json]
light-crawl site migrate <pack> [--all] [--root examples/site-packs] [--write] [--json]
light-crawl site run <pack> [--out <file>] [--max-pages N] [--crawldir <dir>]
  [--skip-verify] [--timeout 300] [--json]
```

`site migrate` is dry-run by default. `site check --write` updates
`last_verified_at` only on success.
`site run` requires a new output path and fails on missing/invalid data output.
It never reuses an old output as evidence of a new run.

## Utility

```bash
light-crawl adapters [--json]
light-crawl demo [--out runs/demo] [--force] [--json]
light-crawl --version
```

## JSON and paths

- Inspection/creation commands offer `--json`; dataset export/check always return JSON.
- `--case-root` defaults to `cases`.
- Case arguments accept a directory or a slug under `--case-root`.
- `doctor`, default `verify`, dataset export/check, site list/show and site migrate
  do not contact the target. `verify --run-check` and `site check` execute local
  code; review its scope rather than assuming it is network-free.
