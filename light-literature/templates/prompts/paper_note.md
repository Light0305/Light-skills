# Paper note task

Use this task for a requested comprehensive, evidence-anchored reading note.
A local question, excerpt explanation or requested brief summary can be answered
directly at that depth; do not force the complete template onto those requests.

## Inputs

- `paper.md` — host-model-transcribed full text (primary source)
- `paper.pdf` — original PDF (check figures, tables, appendix)
- `paper.zh.md` — optional Chinese translation
- image folders referenced by `paper.md`
- `source_map.json` — stable paragraph, figure, table and equation IDs

## Output

Write `note.md` using `templates/paper-note-template.md`. Keep sections 0–16 in
order. You may add subsections, but do not drop sections.

## Evidence rules

1. Every factual claim needs an anchor: section, page, figure, table, equation,
   algorithm, or appendix. If you cannot anchor it, write “Not assessable from
   supplied material.”
2. Separate **[Author]** claims from **[Analyst]** inferences. Never present your
   interpretation as the authors' claim.
3. Read the body, appendix, footnotes, and figure/table captions. If you only read
   part of the paper, say so in Section 1.
4. Cross-check prose, tables, and figures. If they disagree, record the disagreement
   as a finding.
5. Preserve hedging. “May” is not “does”; “suggests” is not “proves”.
6. Do not invent numbers, baselines, datasets, or citations.
7. Before drafting, inventory the material actually read and choose
   `page-grounded`, `structure-grounded` or `source-limited` based on its locators.
   Link claims to source-map IDs when available. Unseen appendices and missing
   experiments remain unassessable, even if the abstract mentions them.
8. Label external facts and new hypotheses separately from author claims and
   analyst inferences. External claims require a verified source URL/DOI; keep
   them distinct from observations made in this paper.

## Reconstruct the research path

Use the existing problem and method sections of the note to explain the obstacle,
the authors' working bet, the design it motivated and the evidence testing it.
For load-bearing components, state what removing them would change and whether
an actual ablation supports that statement. Do not invent the authors' private
history or treat an intuitive component explanation as an ablation result.

For central equations, give symbol meanings and shapes, assumptions and a small
worked example when useful. Label invented example values as teaching values,
never as experimental measurements. For non-method papers, adapt the lens to the
study design rather than inventing an algorithm.

## Figure rules

- For a comprehensive note, embed or directly link every available main
  figure/table using its actual relative image/page path. For example,
  `![Figure 1](images/actual-figure.png)` only when that file really exists.
- For each, write:
  - what the authors want it to support,
  - what it actually shows,
  - a counter-reading (crossing curves, overlapping error bars, log axes, single
    seed, missing baseline, cherry-picked examples),
  - the anchor.
- If an image is missing, say “image missing” and still analyze the caption.

## Critical layer

- Author-stated limitations and your critique must be separate.
- Rank at most three red flags. A red flag must threaten a load-bearing claim, not
  be a copy-editing issue.
- Record uncertainty flags: unreported quantities, untested conditions, ambiguous
  wording.

## Idea cards

Write 3–5 testable ideas derived from the paper. Each card needs:

- closest prior art,
- delta,
- why now,
- feasibility,
- a discriminating experiment,
- an expected negative result.

If you cannot produce three defensible ideas, write fewer and explain why. Do not
pad with generic “apply method X to domain Y” ideas.

## Style

- Default language: **Chinese**. Translate all section headings into Chinese and
  keep technical terms in English in parentheses on first use. Use
  `templates/paper-note-template.zh.md` for the Chinese contract.
- An English note is optional; if produced, save it as `note.en.md`.
- Be concrete and quantitative. Prefer “Table 2 shows +3.2 points on X” over
  “the method performs better”.
- This is a research note, not a press release. Critique is expected.
