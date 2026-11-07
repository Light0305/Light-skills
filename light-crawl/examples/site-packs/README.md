# Site packs

Three reference packs, one per acquisition shape:

| Pack | Lane | Shape | Run |
|---|---|---|---|
| [quotes](quotes/) | `L0_STATIC` | Server HTML + selectors + captured fixture | `light-crawl site run examples\site-packs\quotes` |
| [books](books/) | `L0_STATIC` | Real paginated catalogue, 3 pages | `light-crawl site run examples\site-packs\books` |
| [github-api](github-api/) | `L0_API` | One JSON endpoint + field map | `light-crawl site run examples\site-packs\github-api` |
| [signed-local](signed-local/) | `L2_SIGNED` | Local signed fixture + reproduction | `python examples\site-packs\signed-local\verify.py` |
| [login-local](login-local/) | `L1_DYNAMIC` | Local cookie/session flow | `python examples\site-packs\login-local\verify.py` |

All three have an offline `verify.py` (or an offline path) so a selector or
signature change can be caught without guessing.

The static and API packs are real captures. `books` adds pagination; `quotes`
is the smallest static pack. The signed and login packs are intentionally local
fixtures because a production signer/session is target-specific and must not be
committed as if it were universal.

Use `light-crawl site list` to see the registry and `light-crawl site show <pack>`
for a single entry.
