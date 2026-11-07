# Reproduction templates

- `replay.py` — replay a captured request without a browser.
- `sign_lab.py` — hash/HMAC/timestamp/canonical-JSON helpers.
- `request.example.json` — the request fixture shape.

Workflow:

1. Copy a captured request into `fixtures/request.json`.
2. Redact cookies, authorization headers and personal data.
3. `python replay.py --request fixtures/request.json --dry-run`.
4. Compare the live response with `fixtures/response.json`.
5. Put the site-specific signature in `repro/sign.py`, and import `sign_lab.py`
   only for the primitives it already implements.

Never commit a live cookie, bearer token or API key.
