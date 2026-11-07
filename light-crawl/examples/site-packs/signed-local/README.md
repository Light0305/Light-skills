# signed-local site pack

An `L2_SIGNED` reference pack. It is deliberately local: the target is
`benchmarks/fixtures/signed_app`, not a production site.

The signature chain is:

```text
base64("page|ts|nonce:demo-secret")
```

## Verify

```powershell
python examples\site-packs\signed-local\verify.py
```

Expected:

```text
PASS unsigned=403 signed=200 orders=2
```

## Print a signed URL

```powershell
python examples\site-packs\signed-local\repro\sign.py --base http://127.0.0.1:8765
```

## What this pack demonstrates

- the signature input is explicit (`page`, `ts`, `nonce`);
- the unsigned path is rejected;
- the reproduction lives in `repro/sign.py`, not in a chat transcript;
- the response fixture is small and contains no credentials.

It is not a reusable production signer and does not claim production crypto.
