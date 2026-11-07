# GitHub API site pack

An `L0_API` pack: one public JSON endpoint, no browser, no HTML parsing.

```powershell
light-crawl site run examples\site-packs\github-api
```

Expected: 1 item, `verify.py` passes.

## Fields

| Field | JSON path |
|---|---|
| `full_name` | `full_name` |
| `stars` | `stargazers_count` |
| `forks` | `forks_count` |
| `open_issues` | `open_issues_count` |
| `html_url` | `html_url` |

## Offline regression

```powershell
python examples\site-packs\github-api\verify.py
```

The fixture is a real response captured from the public endpoint; it contains no
token or personal data. GitHub rate-limits unauthenticated requests, so the pack
is deliberately a one-item lookup, not a crawl.
