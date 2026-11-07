# Spider templates

`generic_spider.py` is a config-driven Scrapling spider for server-rendered and
HTTP-API targets.

```bash
python generic_spider.py --config site.json --out items.jsonl --max-pages 3
```

The config schema:

| Key | Meaning |
|---|---|
| `name` | Spider name |
| `start_urls` | Entry URLs |
| `allowed_domains` | Off-site guard |
| `item_selector` | Repeating item container |
| `fields` | Field name → `{selector, many?, default?}` |
| `next_selector` | Selector that returns the next-page href |
| `concurrency` | Concurrent requests |
| `robots_txt_obey` | Respect robots directives |
| `max_pages` | Hard page budget |

`stealth_spider.py` is the browser-backed variant for `L1_DYNAMIC`/`L3_BLOCKED`.
It uses `AsyncStealthySession` as the default session and keeps the same config
shape, plus optional `wait_selector`, `solve_cloudflare` and `headless` keys.

```bash
python stealth_spider.py --config site.json --out items.jsonl --max-pages 3
```

Do not enable a browser for every request by default. Start small, confirm the
backing API, and downgrade to the HTTP spider when possible.
