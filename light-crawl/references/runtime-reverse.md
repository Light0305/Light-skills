# Runtime reverse-engineering (L2/L3)

## 1. Division of labour

- **js-reverse MCP** is the runtime instrument: it opens the page, sets
  breakpoints, pauses execution, reads call frames and exports requests.
- **reverse-skill/js-reverse** is the methodology: Observe → Capture → Rebuild →
  Patch → DeepDive.
- **light-crawl** owns the case state and the artifact bus.

Do not ask the model to "look at the JS" without a concrete request, script,
function or breakpoint. Do not guess a signature from minified text.

## 2. Tool map

Client tool names may be prefixed (`js-reverse_list_scripts`). The underlying
names are:

| Job | Tools |
|---|---|
| Open/navigate | `new_page`, `navigate_page`, `select_page`, `select_frame` |
| Find scripts | `list_scripts`, `search_in_sources`, `get_script_source`, `save_script_source` |
| Find the request | `list_network_requests`, `get_request_initiator` |
| Break on request | `break_on_xhr` |
| Break on code | `set_breakpoint_on_text`, `list_breakpoints`, `remove_breakpoint` |
| Inspect pause | `get_paused_info`, `step`, `pause_or_resume` |
| Evaluate | `evaluate_script` |
| WebSocket | `get_websocket_messages` |
| State | `clear_site_data` |
| Browser actions | `click_element`, `take_screenshot` |

## 3. Observe

Goal: identify the target request and the scripts that could produce it.

1. `new_page` with the target URL.
2. `list_network_requests` to find the data-bearing request.
3. `get_request_initiator` to see the JS call stack.
4. `list_scripts` / `search_in_sources` for `sign`, `encrypt`, `nonce`,
   `timestamp`, `x-sign`, `getSign`, `wasm`.
5. Save the candidate script with `save_script_source` into `artifacts/`.

Record in evidence:

- request URL and method;
- initiator chain;
- candidate script URL(s);
- one sentence explaining why the candidate is plausible.

## 4. Capture

Goal: get one real request/response pair and the exact inputs to the signature.

Preferred order:

1. `break_on_xhr` with the URL pattern. This is the least invasive way to catch
   the request before it leaves the browser.
2. `set_breakpoint_on_text` only when the code is minified and XHR breakpoints are
   insufficient.
3. When paused, `get_paused_info` to read the call stack and scoped variables.
4. `evaluate_script` in the paused call frame to compute candidate inputs, hash
   intermediate values, or inspect closures.
5. `step` to follow one function at a time.

Export:

- request headers (redact cookies/tokens before committing);
- request body;
- response status/body;
- caller script range;
- the exact runtime values that feed the signature.

Write them to `fixtures/request.json`, `fixtures/response.json`, and
`artifacts/caller.js`.

## 5. Rebuild

Goal: reproduce the parameter outside the browser.

1. Create `repro/sign.py` from `templates/repro/sign_lab.py`.
2. Implement the smallest chain that matches the observed output.
3. Feed it values from the captured request.
4. Compare the output to the real request byte-for-byte.
5. Add at least 10 fixtures, including one after a page reload and one with a
   different user/session if authorized.

Common chains:

- `MD5(sorted_query + salt)`;
- `SHA256(timestamp + nonce + body)`;
- `HMAC-SHA256(secret, canonical_json)`;
- AES-CBC with a key derived from a constant or a request;
- WASM export called with a struct;
- browser fingerprint mixed into the payload.

Do not claim "it is AES" from a 32-character string. Prove it with a fixture.

## 6. Patch

Goal: handle the browser environment only where the script needs it.

- Run the saved script in Node.
- Read the first divergence: `window is not defined`, wrong `navigator`, missing
  `crypto.subtle`, wrong timezone, missing `localStorage`.
- Patch one dependency at a time.
- Re-run after every patch.
- Record each patch in evidence with the error that justified it.

Do not preload a giant fake browser. A large fake environment is itself a source
of divergence.

## 7. DeepDive

Only after the signature works:

- AST deobfuscation;
- control-flow flattening recovery;
- string-array decoding;
- VM/opcode interpretation;
- WebAssembly boundary analysis.

If the task only needs one parameter, stop at a working reproduction. DeepDive is
for long-term reuse, not for vanity.

## 8. Anti-bot escalation

Default js-reverse mode already uses the project's Patchright fork for
protocol-level stealth. `--cloak` is a **separate startup mode** with a different
Chromium binary and profile. It never turns on automatically.

Escalation:

1. Default browser, normal session.
2. `--isolated` to rule out stale cookies/storage.
3. A separate `js-reverse-cloak` instance.
4. Human check if an interactive CAPTCHA appears.

Do not put `--cloak` on the default server; that would make every site use the
heavier browser and lose the default login state.

## 9. Evidence checklist

- [ ] Request URL, method, status.
- [ ] Initiator stack with script URL and line.
- [ ] Paused function and relevant scoped values.
- [ ] Script source saved.
- [ ] Request/response fixtures saved and redacted.
- [ ] Reproduction script and at least 10 fixtures.
- [ ] First divergence and each environment patch recorded.
- [ ] A statement of what is observed vs inferred vs still unknown.

## 10. Stop conditions

- The only path forward is a CAPTCHA, account takeover or credential guessing.
- The target is outside the authorized scope.
- The signature depends on a server secret that cannot be obtained lawfully.
- The page requires a client certificate or device attestation you do not have.
- The cost of reproduction exceeds the value of the data; hand it to a human.
