# login-local site pack

An `L1_DYNAMIC` reference pack for a **cookie-backed session**. It uses the local
`benchmarks/fixtures/login_app` fixture, not a production site.

## Verify

```powershell
python examples\site-packs\login-local\verify.py
```

Expected:

```text
PASS before=401 login=200 private=200 restored=200 user='demo' orders=2 encrypted=yes
```

The `restored` status is a second `FetcherSession` that loads the saved cookie
file. On Windows the state file is DPAPI-encrypted; the raw bytes do not contain
the cookie value. Credentials are never written.

## What it proves

- `/private` rejects an unauthenticated request;
- a `FetcherSession` POSTs the demo credentials and keeps the cookie;
- the same session then gets private JSON;
- the pack records the login flow in `repro/login.py`, not in chat.

The credentials (`demo` / `demo`) are local fixture values, not secrets and not
a pattern for storing real credentials.
