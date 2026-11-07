# Acquisition with Scrapling

## 1. Install

```bash
pip install "scrapling[fetchers]"
scrapling install
```

If the browser CDN is slow, point Playwright at a mirror and retry:

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST = "https://cdn.npmmirror.com/binaries/playwright"
scrapling install
```

The core `light-crawl` probe works without Scrapling. Install it when a case
reaches `L0`/`L1`/`L3`/`L5`.

## 2. Choose the cheapest fetcher

| Need | Use | Why |
|---|---|---|
| Static HTML, JSON, plain API | `Fetcher` / `FetcherSession` | Fast, low memory, TLS impersonation |
| JS-rendered page | `StealthySession` | Real browser, fingerprint handling |
| Cloudflare Turnstile/Interstitial | `StealthySession(solve_cloudflare=True)` | Browser challenge flow |
| Repeated requests, login state | `FetcherSession` / `StealthySession` | Cookies and connections persist |
| Full crawl | `Spider` | Concurrency, retry, throttle, checkpoint |
| Markdown corpus | `ContentSpider` | Clean LLM-ready output |

## 3. HTTP first

```python
from scrapling.fetchers import Fetcher, FetcherSession

page = Fetcher.get("https://quotes.toscrape.com/", stealthy_headers=True)
quotes = page.css("div.quote span.text::text").getall()

with FetcherSession(impersonate="chrome") as session:
    page = session.get("https://quotes.toscrape.com/")
    next_page = page.css("li.next a::attr(href)").get()
```

Use `impersonate="chrome"` when the site checks TLS/header consistency. Do not
add a random User-Agent that contradicts the TLS fingerprint.

## 4. Browser session and API capture

The most valuable browser feature is not DOM parsing; it is discovering the JSON
API behind the page.

```python
from scrapling.fetchers import StealthySession

with StealthySession(
    headless=True,
    record_requests=True,
    network_idle=True,
) as session:
    page = session.fetch("https://example.com/app", wait_selector="main")
    # Read the page, then search the captured network history
    hits = session.network.search(limit=None)
```

Rules:

1. Open the page once.
2. Trigger the data load (scroll, click, search).
3. Search the recorded responses for the item array.
4. Capture the request headers/body.
5. Downgrade the case to `L0_API` and replay outside the browser.

Do not parse a rendered list when the page already fetched a clean JSON array.

## 5. Cloudflare

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    "https://example.com/protected",
    headless=False,
    solve_cloudflare=True,
)
```

- Try a normal browser first.
- If the challenge is interactive, stop and hand it to a human.
- Do not build a CAPTCHA farm.
- `--cloak` in js-reverse is a separate, heavier fallback; it is not automatic.
- The stealth template auto-selects an installed Google Chrome/Chromium when it
  can find one, otherwise it uses Scrapling's bundled browser. The bundled
  browser is still the more reproducible choice for a long-running deployment.

## 6. Spider delivery

```python
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    concurrent_requests = 4
    robots_txt_obey = True

    async def parse(self, response: Response):
        for quote in response.css("div.quote"):
            yield {
                "text": quote.css("span.text::text").get(),
                "author": quote.css("small.author::text").get(),
            }
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

result = QuotesSpider(crawldir="./crawl_data").start()
result.items.to_jsonl("quotes.jsonl")
```

Production checklist:

- `crawldir` for pause/resume;
- per-domain delay / AutoThrottle;
- retry policy for 429/5xx;
- proxy rotation only if authorized and necessary;
- bounded item size;
- dedupe key;
- export format and schema;
- a stop condition when the site starts blocking.

## 7. Generic spider template

`templates/spider/generic_spider.py` implements the config-driven case:

```bash
python templates/spider/generic_spider.py \
  --config examples/quotes/site.json \
  --out runs/quotes.jsonl \
  --crawldir runs/quotes.checkpoint \
  --max-pages 3
```

Use it for `L0_STATIC`/`L0_API`. For a browser-rendered site, write a custom
spider with `StealthySession` and a small page budget.

## 8. Parsing rules

- Prefer CSS/XPath that describes semantics, not layout (`div:nth-child(3)` is
  fragile).
- Keep the selector in `site.json` or a `selectors.py`, not buried in a prompt.
- For every field, define type, required/optional, and a normalizer.
- Use a stable ID or URL as the dedupe key.
- Use adaptive selectors only after a fixture proves the old selector worked.
- Save a raw HTML fixture before changing a selector.

## 9. CLI helpers

```bash
scrapling extract get "https://example.com" page.md --ai-targeted
scrapling extract fetch "https://example.com/app" page.md --ai-targeted --wait-selector "main"
scrapling extract fetch "https://example.com/protected" page.md --solve-cloudflare
scrapling shell
```

`--ai-targeted` reduces hidden/injected content before the page reaches the
model. Use it for exploration; keep the raw response as a fixture when debugging.

## 10. Common mistakes

1. Opening a browser for a page that `Fetcher` handles.
2. Parsing DOM when the page already fetched JSON.
3. Running 50 concurrent requests before measuring latency.
4. Sharing a browser profile between Scrapling and another tool.
5. Storing cookies/tokens in the repository.
6. Treating a successful 200 as proof that the schema is correct.
7. Scaling before fixtures and a 3-item sample pass.
