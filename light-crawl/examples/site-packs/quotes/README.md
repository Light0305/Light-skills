# quotes.toscrape.com site pack

A small, tracked example of a `light-crawl learn` site pack. It is built from a
real captured page and proves that the pack can be run and regression-checked
without guessing at the target.

## Run

```powershell
python templates/spider/generic_spider.py `
  --config examples/site-packs/quotes/spider/site.json `
  --out runs/quotes.jsonl `
  --max-pages 1
```

Expected: 10 items with `text`, `author` and `tags`.

## Regression check

```powershell
python examples/site-packs/quotes/verify.py
```

The check parses `fixtures/response.html` offline with Scrapling's `Selector` and
asserts the item count and the first item's fields. It does not hit the network.

## Contents

| Path | Meaning |
|---|---|
| `site.json` | provenance, lane, capture facts and run contract |
| `spider/site.json` | selectors and page budget |
| `spider/spider.py` | the generic Scrapling spider |
| `repro/replay.py` | replay the captured GET request |
| `fixtures/request.json` | redacted request fixture |
| `fixtures/response.html` | real captured HTML |
| `fixtures/response.meta.json` | status, headers and hash |
| `verify.py` | offline selector regression |

The HTML fixture is public content from the demo site. It contains no cookies,
tokens or personal data.
