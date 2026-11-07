# Evidence and reports

## 1. Why a ledger

The ledger is the case's memory. It lets a later agent or human answer:

- What did we actually observe?
- Which tool produced it?
- Which artifact proves it?
- What did we infer, and how confident are we?
- What is still unknown?

An observation is not an inference. A request that returns 200 is an observation.
"Therefore the signature is MD5" is an inference. Keep them separate.

## 2. Record shape

`evidence.jsonl` contains one JSON object per line:

```json
{
  "evidence_id": "E0004",
  "ts": "2026-10-25T06:20:00Z",
  "phase": "CAPTURED",
  "source": "js-reverse",
  "action": "set_breakpoint_on_text near `sign(` then submit the form",
  "observation": "paused in `sign(t, e)`; t contains method, path, timestamp; e is a 32-char hex string",
  "inference": "the 32-char value may be MD5 of the canonical query plus a salt",
  "confidence": "medium",
  "artifact": "artifacts/caller.js",
  "metadata": {
    "request": "fixtures/request.json",
    "script_url": "https://example.com/static/app.js",
    "line": 1821
  }
}
```

## 3. Confidence

| Level | Use when |
|---|---|
| `high` | Directly observed and reproduced, or multiple independent artifacts agree |
| `medium` | Observed once, plausible, not yet reproduced |
| `low` | A guess, a single weak signal, or a heuristic |

Do not use `high` for a route decision. A route is a hypothesis.

## 4. Artifacts

- Store the smallest useful artifact.
- Hash files added with `light-crawl evidence` or the case API.
- Redact cookies, authorization headers, API keys and personal data.
- Keep raw and redacted versions separate when both matter.
- Never commit a live session state file.

New artifact files have content-based names; repeated labels do not overwrite
old evidence. New directory archives carry an inventory/tree hash. Old unsealed
directories remain readable with a warning, not a new integrity certification.
These are local consistency checks, not tamper-proof provenance.

Naming:

```text
artifacts/
  caller.js
  network-list.json
  rea-js-app.json
  screenshot-01.png
fixtures/
  request.json
  response.html
  response.meta.json
  request-after-reload.json
```

`light-crawl capture` creates the first three automatically:

- `request.json` — method, URL and non-secret headers;
- `response.html` / `.json` / `.txt` / `.bin` — the raw body;
- `response.meta.json` — status, final URL, allow-listed headers, byte count,
  SHA-256 and timestamp.

Since v1.3 canonical captures live under `fixtures/captures/CAP-*/`; hashes are
registered in `case.json`. Top-level names are compatibility working copies.
Metadata records `body_path`, truncation and HTTP/browser representation.
Compressed bytes may use .bin; do not parse them or partial bytes as a full table.
Empty bodies still have a hash.

Cookies and authorization headers are not persisted. The capture is also written
to `evidence.jsonl` and to the case metrics (`last_capture_*`).
This describes header filtering only. Bodies, URLs and screenshots need review
before sharing; preserve raw locally and redact working copies. Raw capture
archives are excluded from `learn` copies.

## 5. Report contract

`light-crawl report` renders:

1. status (verified or not);
2. target and authorization state;
3. probe facts;
4. route and reasons;
5. evidence table;
6. artifact hashes;
7. metrics;
8. blockers;
9. next actions;
10. limitations and unknowns.

The report must never imply that:

- a route was proven;
- a built spider is production-ready;
- authorization or robots compliance was verified by the tool;
- a heuristic signature guess is a finding.

## 6. Phase gates

| Phase | Minimum evidence |
|---|---|
| `PROBED` | status, content type, page kind, script count, API candidates |
| `ROUTED` | reasons and confidence for the lane |
| `CAPTURED` | one request/response or one paused call frame |
| `UNDERSTOOD` | endpoint/physical script location and a stated hypothesis |
| `REPRODUCED` | local output matches at least one fixture |
| `BUILT` | spider or extractor exists and runs on a sample |
| `VERIFIED` | current executed check receipt; applicable live sample recorded separately |
| `OPERATING` | run metrics, schedule, failure policy |
| `LEARNED` | site pack with provenance and regression fixtures |

## 7. Redaction checklist

- [ ] `cookie` / `set-cookie` removed or replaced with `<redacted>`.
- [ ] `authorization` / bearer tokens removed.
- [ ] API keys, session IDs, CSRF tokens removed.
- [ ] Email, phone, address and other personal data removed.
- [ ] Internal hostnames and employee identifiers reviewed.
- [ ] Screenshots reviewed for visible personal data.

## 8. Evidence anti-patterns

1. Pasting a 2 MB script into the chat instead of saving it.
2. Writing "looks like AES" with no fixture.
3. Marking `VERIFIED` because the first request returned 200.
4. Recording only the conclusion and losing the artifact.
5. Mixing observation and inference in one sentence.
6. Storing a live cookie in `fixtures/` "for reproducibility".
