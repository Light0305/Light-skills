# Translation task (host model)

You are translating a host-model-transcribed paper into Chinese. This is **not** a summary.

## Inputs

- `paper.md`: the source Markdown, including headings, equations, tables, figure links, and citations.
- `paper.pdf`: the original PDF, for checking captions and layout.
- `assets/` or other image folders: figures referenced by `paper.md`.

## Output

Write `paper.zh.md` in the same folder.

When the user requests side-by-side reading, also write `reader.bilingual.md`
with consecutive source/Chinese blocks sharing the same source ID. Keep figures
near their first substantive discussion, and include both original and translated
captions. This optional reader does not replace the full source or translation.

## Rules

1. **Translate the full text**, section by section. Do not omit the method, experiments,
   limitations, appendix, or figure captions.
2. Preserve the Markdown structure: headings, lists, tables, equations, code blocks,
   figure links, and citations. Do not renumber figures or equations.
3. Keep technical terms in English in parentheses on first use, e.g. “检索增强生成
   (retrieval-augmented generation, RAG)”.
4. Translate figure/table captions and any text inside tables. Keep numbers, units,
   dataset names, and metric names unchanged.
5. Keep LaTeX equations exactly as they are. Do not translate variable names.
6. Do not add claims, examples, or explanations that are not in the source. If a
   sentence is ambiguous, translate it faithfully and add a bracketed note
   `[译注: ...]` rather than guessing.
7. If the paper is long, translate in chunks by section, but keep one consistent
   terminology ledger in `translation_notes.md`.
8. Preserve the authors' hedging: “may” → “可能”, “suggests” → “提示/表明”,
   “demonstrates” → “证明/展示”. Do not strengthen claims.
9. Preserve all page and block anchors from `source_map.json`. Translation is authored by the host model.

## Quality bar

A reader should be able to read `paper.zh.md` without the English original for
understanding, while still being able to check every claim against `paper.md`.
