# books.toscrape.com site pack

A second real `L0_STATIC` target with pagination. The pack crawls three pages
(60 items by default) and has an offline regression check for page 1.

```powershell
light-crawl site run examples\site-packs\books
```

Expected: 60 items, `verify.py` passes.

## Offline regression

```powershell
python examples\site-packs\books\verify.py
```

Expected:

```text
PASS books=20 first_title='A Light in the Attic' next=catalogue/page-2.html
```

## Fields

| Field | Selector |
|---|---|
| `title` | `h3 a::attr(title)` |
| `price` | `p.price_color::text` |
| `availability` | `p.instock.availability::text` |
| `rating` | `p.star-rating::attr(class)` |
| `url` | `h3 a::attr(href)` |

The fixture is the real first page, with no cookies or personal data.
