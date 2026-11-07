# Learning loop and site packs

## 1. The point

A successful crawl is a one-off. A site pack is an asset.

`light-crawl learn <case>` promotes the reusable parts of a case:

```text
sites/<domain>/
  site.json
  README.md
  probe.json
  route.json
  spider/
  repro/
  fixtures/
```

The next case for the same domain starts here, not from zero.

## 2. What to promote

Promote:

- selector maps and pagination rules;
- the replay/signature implementation;
- redacted fixtures that prove the contract;
- rate-limit and auth notes;
- the route and the reason it was chosen.

Do not promote:

- cookies, tokens, API keys;
- personal data;
- huge raw HTML dumps;
- one-off screenshots with sensitive content;
- code copied from a third-party repository without its license.

## 3. Fixtures

A fixture is a small, reviewable input/output pair:

```text
fixtures/
  request.json
  response.json
  request-after-reload.json
  response-after-reload.json
  expected.json
```

Rules:

1. Redact secrets.
2. Keep the bytes that matter (signature, body, headers).
3. Record the expected extracted fields.
4. Include one variation (reload, different page, different user if authorized).
5. Never use a fixture as a license to hit the live target repeatedly.

## 4. Regression tests

Minimum:

- signature reproduction matches all fixtures;
- selector extraction returns the expected number of items;
- required fields are non-empty;
- dedupe key is stable;
- pagination stops at the configured page budget;
- a changed selector is caught by a failing fixture, not a silent empty result.

## 5. Metrics

Measure per case:

| Metric | Why |
|---|---|
| Success rate | Did the target fields appear? |
| Requests per item | Is the crawler wasteful? |
| Browser seconds | Is the browser needed? |
| Tokens per 1000 items | Is the agent doing bulk work? |
| Throughput | Items/minute at the chosen concurrency |
| Retry rate | Is the site rate-limiting? |
| Block rate | Is the route stable? |
| Drift recovery | Does the fixture catch a selector change? |
| Reproducibility | Does a fixture replay match live output? |

Store metrics in `case.json` via `light-crawl` or the case API. A report without
metrics is an anecdote.

Record measured values on a case:

```powershell
light-crawl metrics record my-case `
  --items 100 --requests 120 --browser-seconds 50 --tokens 4000 `
  --success-rate 0.95 --drift-recovery 0.8 --note "first production sample"
light-crawl metrics show my-case
```

The command computes `requests_per_item`, `browser_seconds_per_item` and
`tokens_per_1k_items`, and appends a metrics evidence entry.

The committed benchmark lives in `benchmarks/cases/` and is run with
`light-crawl benchmark`. It covers static, API, signed, Cloudflare and Electron
routing; its report also aggregates the five metrics above. Missing values render
as `-`, not zero. The signed and Cloudflare fixtures can be exercised live with
`python benchmarks/live_check.py`.

## 6. Pattern library

Over time, promote recurring patterns:

```text
patterns/
  md5-query-salt.md
  hmac-canonical-json.md
  aes-cbc-constant-key.md
  wasm-export-abi.md
  cloudflare-turnstile.md
  nextjs-api-discovery.md
  shopify-collection.md
```

A pattern note contains:

- the observable signal;
- the proof;
- the reproduction snippet;
- the failure modes;
- a fixture;
- the license/source of any borrowed code.

## 7. Evolution rules

1. Change one selector at a time.
2. Add or update a fixture with every change.
3. Re-run the contract verifier.
4. Keep the old fixture; do not delete the evidence of a previous contract.
5. If an upstream API changes, update the adapter, not every site pack.
6. Pin versions and record them in `site.json`.

## 8. When not to learn

Do not create a site pack when:

- the data is personal and you cannot store it safely;
- the case was a one-off with no reusable contract;
- the reproduction is unverified;
- the license of copied code is unclear;
- the pack would contain secrets.

In those cases, keep the case report and delete the sensitive artifacts.
