# Routing

## 1. The ladder

| Lane | Use when | First move | Exit condition |
|---|---|---|---|
| `L0_STATIC` | Server HTML contains the data | `Scrapling Fetcher` | Selectors + pagination confirmed on 3 pages |
| `L0_API` | JSON endpoint returns the data | Replay the request | Required headers + cursor/schema confirmed |
| `L1_DYNAMIC` | HTML is a shell or needs a session | `StealthySession` with `record_requests=True` | The backing API or a stable DOM contract is identified |
| `L2_SIGNED` | Signature/token/encryption gates the API | js-reverse breakpoint | Local reproduction passes fixtures |
| `L3_BLOCKED` | Challenge, 403/429, Cloudflare | Scrapling stealth first | A stable authorized session or a human stop |
| `L4_APP` | Electron/APK/native/HAR has the protocol | REA CLI | Request contract handed back to L0/L1 |
| `L5_SCALE` | Volume ≥1000 or repeated runs | Scrapling `Spider` | Checkpointed run + metrics |

`L5_SCALE` is a delivery decision. It does not replace the acquisition lane.

## 2. Signals, not certainties

### Static

- meaningful server-rendered text (`visible_text_chars` ≥ 200);
- low script count;
- data present in headings, tables, lists or JSON-LD.

Do not trust a 200 alone. Some sites return a 200 shell with a challenge script.

### API

- `content-type` contains `json`;
- body starts with `{` or `[`;
- XHR/fetch URLs with `/api`, `/graphql`, `/v1/`, `.json`.

An API response can still be signed or session-bound. Check the request, not only
the response.

### SPA

- `__NEXT_DATA__`, `__NUXT__`, `__INITIAL_STATE__`, `__APOLLO_STATE__`;
- empty `#root`, `#app`, `#__next`;
- many scripts and little text.

The best outcome for an SPA is often `L0_API`: find the JSON endpoint and leave
the browser behind.

### Signed

Strong hints:

- `sign`, `signature`, `encrypt`, `decrypt`, `hmac`, `x-sign`, `x-signature`;
- query parameters like `sign=`, `token=`, `timestamp=`, `nonce=`;
- an initiator stack that enters a function with `encrypt`, `sign`, `getSign`,
  `wasm`, or a crypto library.

Weak hints:

- a random `token` string;
- `timestamp` used only for cache busting;
- minified names that happen to contain `sign`.

Require at least one strong hint **and** an API-shaped request.

### Blocked

- 403/429;
- challenge markers (`cf-chl`, "Just a moment", "Enable JavaScript and cookies");
- CAPTCHA markers;
- Cloudflare headers plus a challenge body.

Cloudflare headers alone are not a block: many sites serve normal content through
Cloudflare.

### App

- Electron/ASAR, APK/IPA, native binary, HAR/SAZ, pcap;
- a web surface that requires a desktop/mobile client certificate or proprietary
  protocol;
- an app-only endpoint that the website never calls.

## 3. Failure taxonomy

| Class | Symptom | Next move |
|---|---|---|
| `NETWORK` | DNS/timeout/TLS failure | Fix egress/proxy first; do not blame the site |
| `BLOCK` | 403/429/challenge | Stealth session, then cloak, then human |
| `AUTH` | 401/redirect to login | Obtain authorized state; never guess credentials |
| `RENDER` | Empty root, skeleton | Browser session + `record_requests=True` |
| `SIGN` | API rejects `sign`/`token` | js-reverse breakpoint + rebuild |
| `SCHEMA` | Selector returns null after a site change | Fixture + adaptive selector + regression |
| `APP` | Data only in a packaged client | REA |
| `POLICY` | robots/ToS/authorization conflict | Stop; do not engineer around it |

## 4. Escalation rules

```text
L0_STATIC ──(no data / JS shell)──▶ L1_DYNAMIC
L0_API ─────(signature error)─────▶ L2_SIGNED
L1_DYNAMIC ─(challenge)───────────▶ L3_BLOCKED
L2_SIGNED ──(client-only protocol)▶ L4_APP
any lane ───(volume ≥1000)────────▶ spider delivery
```

Never escalate two levels at once. If `L0_API` fails, inspect the request before
opening a browser. If `L1_DYNAMIC` gets a 403, capture the response before trying
cloak.

## 5. Budgets

Set these before the first large run:

- max pages per lane;
- max browser seconds;
- max requests per minute;
- max retries per URL;
- max wall-clock time;
- max output size;
- token budget for the agent.

When a budget is exhausted, stop and write a blocker. Do not silently continue
with a more aggressive method.

## 6. Route review checklist

- [ ] Does the evidence actually support the lane?
- [ ] Is there a cheaper lane that has not been tried?
- [ ] Is the target authorized for this volume and method?
- [ ] Is the browser profile owned by exactly one process?
- [ ] Is the next action concrete enough to execute without guessing?
- [ ] Is the stop condition explicit?
