# Quotes example (L0_STATIC)

A small, public, server-rendered target used to prove the generic spider.

```bash
python templates/spider/generic_spider.py \
  --config examples/quotes/site.json \
  --out runs/quotes.jsonl \
  --max-pages 1
```

Expected: 10 items on the first page, with `text`, `author` and `tags`.

This example is for smoke testing, not for a production crawl. Respect the
target's robots.txt and rate limits.
