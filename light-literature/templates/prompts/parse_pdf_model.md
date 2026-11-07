# Host-model PDF transcription

You are the host multimodal model. Parse `paper.pdf` into `paper.md`. This is a **transcription** task, not a summary.

## Inputs

- `paper.pdf` — original PDF.
- `pages/page_XXX.png` — 150-DPI page renders produced by `litsearch` (if available).
- `images/page_XXX_img_Y.*` — embedded images extracted from the PDF (if available).
- `pdf_assets.json` — page/image index.

If `pages/` is missing, read `paper.pdf` directly with the host PDF reader. Record
that in `model_parse_notes.md`.

## Outputs

1. `paper.md` — the parsed document.
2. `source_map.json` — page → section/figure/table anchors.
3. `model_parse_notes.md` — what was uncertain, missing, or approximated.

## Workflow

### Pass 1 — structure and prose

- Read **every page**, in chunks of 3–5 page images.
- Write the title, authors, abstract, keywords, section headings, and paragraphs
  in document order.
- Insert a page anchor before each page's content:

```markdown
<!-- page: 3 -->
```

- Give each paragraph a stable `P...` ID, each figure an `F...` ID, each table a
  `T...` ID and each independent equation an `E...` ID. Put `<a id="P001"></a>`
  before the corresponding block. Keep IDs stable when correcting or translating
  the text, and record them in `source_map.json`.

- Do not summarize. Do not merge sections. Preserve citations like `(12, 13)` and
  reference numbers.

### Pass 2 — equations, tables, figures

- Reconstruct equations as LaTeX (`$$ ... $$` for display, `$...$` for inline).
  If a symbol is ambiguous, preserve a crop of the original equation (or link
  its page image), mark the transcription uncertain, and record the issue in
  `model_parse_notes.md`. Do not substitute guessed LaTeX for an unreadable formula.
- Reconstruct tables as HTML `<table>...</table>` (preferred for complex tables)
  or Markdown tables. Preserve headers, units, and numbers exactly.
- For each main figure:
  - Reference the extracted image if available:
    `![Figure 1](images/page_005_img_1.png)`
  - Keep the original caption.
  - Check whether extracted objects are fragments or logos. Use a verified crop
    or page image for vector figures or split panels; never assume one image
    object is the entire figure. Keep the figure near its first substantive
    discussion and retain its original figure number.
  - If the image is missing, write `image missing` and keep the caption plus a
    factual description of what is visible on the page.
- Do not invent values that are not visible. If a number is unreadable, write
  `[unreadable]`.

### Pass 3 — completeness audit

Compare the result against the PDF page by page:

- [ ] Page count matches; no page skipped.
- [ ] All section headings present.
- [ ] All display equations present.
- [ ] All tables and main figures present.
- [ ] Figure/table captions present.
- [ ] References section present.
- [ ] Page anchors are present and monotonic.
- [ ] No summary-only paragraphs.

Fix omissions. If a page is unreadable, keep the page anchor and write
`[page unreadable: reason]` rather than guessing.

## Output format

- Use Markdown headings matching the paper's hierarchy.
- Preserve the paper's terminology; keep technical terms in English if that is
  how they appear.
- Use relative image paths (`images/...` or `pages/...`), never absolute paths.
- Keep the reference list as a list; do not translate references.

## `source_map.json`

```json
{
  "page_count": 13,
  "grounding": "page-grounded",
  "pages": [
    {"page": 1, "sections": ["Title", "Abstract"], "figures": [], "tables": []},
    {"page": 5, "sections": ["3 Results"], "figures": ["Figure 1"], "tables": ["Table 3"]}
  ],
  "blocks": [
    {"id": "P001", "kind": "paragraph", "page": 1, "section": "Abstract", "anchor": "P001"},
    {"id": "F001", "kind": "figure", "page": 5, "label": "Figure 1", "anchor": "F001", "asset": "images/page_005_img_1.png"},
    {"id": "E001", "kind": "equation", "page": 5, "anchor": "E001", "confidence": "uncertain", "asset": "pages/page_005.png"}
  ],
  "missing": ["Figure 2 image could not be extracted"]
}
```

The example is abbreviated: the completed map must cover every page actually
read and every anchored block, rather than copying the example's page count.
`page` means the 1-based PDF page index, independent of printed journal numbering.
For HTML/text without reliable PDF pages, use `structure-grounded` and `page: null`
with a real section/block locator. If only partial material is available, use
`source-limited`, list what was read and keep unseen content missing. Never map an
unknown page to page 1. `asset` is optional and must refer to a real local file.

## `model_parse_notes.md`

Record:

- pages read visually vs. text-extracted;
- equations/tables reconstructed with uncertainty;
- missing images;
- any content that could not be read;
- the model name/version and date.

## Quality bar

A reader should be able to use `paper.md` as the source for translation and a
note with sections 0–16 without reopening the PDF for ordinary prose. For equations,
tables, and figures, page anchors must let them verify against `paper.pdf`.
