# Manuscript templates and file delivery

Use for a manuscript, substantial manuscript revision, or a requested typeset
section/file deliverable. A local wording edit, outline, consistency report, or
explicit text/Markdown-only request does not require a new typeset project.

## Resolve the template and layout first

1. Follow an explicitly supplied LaTeX or Word template. Read its actual files
   and instructions before writing; preserve its class/styles, page geometry,
   column layout, bibliography system, native structures, and build method.
   A Word template routes to an editable Word document, using the available
   document workflow, rather than being restyled into the bundled LaTeX layout.
   Deliver its PDF preview too when requested or supported by the workflow,
   unless the user asks for Word only. If both template types are supplied and
   the intended deliverable is unclear, ask which one governs the output.
2. For a continuing project, keep its already adopted template and column
   choice unless the user requests a change. Do not reinitialize or ask the
   same layout question on every revision. A new explicit user template wins.
3. Without a supplied/adopted template, use the bundled generic LaTeX layouts.
   If the user has already said single/double column, use that choice. If not,
   ask **before drafting the manuscript**: “这次使用双栏论文版，还是单栏稿件版？”
   Present two choices, **双栏** and **单栏**. Wait for the choice before
   initializing the layout or writing the manuscript; independent source
   reading can continue. Do not silently pick double column or produce both
   versions. No response is not a selection.

Default file delivery on the bundled route is **editable LaTeX source plus an
actually compiled PDF**, not Markdown alone. This default does not override an
explicit format/text-only request. The templates are light-write's generic
layouts, not official publisher templates or evidence of venue compliance.
Changing columns must not change the scientific content or force an empirical
section structure on a theory/review/protocol paper.

## Bundled layouts

| Choice | Main template | Layout |
|---|---|---|
| Double column | `templates/latex/double-column.tex` | A4, 10 pt, 20 mm side margins, 6 mm column gap; title, authors, abstract, and keywords span both columns. |
| Single column | `templates/latex/single-column.tex` | A4, 11 pt, 25 mm side margins; the same title/abstract hierarchy and a wider text measure. |

`templates/latex/common/` holds the shared style, language setting, metadata,
abstract/body scaffold, and an intentionally empty bibliography. The scaffold
is explicitly template guidance, not research prose. Replace it with supported
content, author information, and article-appropriate sections. Do not invent
authors, affiliations, dates, findings, citations, or institutional branding.
Keep specific evidence-needed markers when inputs really are missing and
identify the result as a draft; remove irrelevant scaffold instructions.

Built previews are retained at `templates/latex/previews/double-column.pdf` and
`templates/latex/previews/single-column.pdf`. They show template instructions
and explicit author placeholders, not a scientific manuscript. They can be
reproduced by initializing and building each selected layout separately.

XeLaTeX is the bundled build default. `--language zh` enables Chinese or mixed
Chinese/English typesetting using ctex and Fandol fonts; it does not authorize
translation. English also supports LuaLaTeX or pdfLaTeX. Chinese needs XeLaTeX
or LuaLaTeX. Retain user-template engine/font requirements on the custom route.

## Create a source project

Respect the actual project layout and explicit paths. For a new manuscript,
use `Write/PAPER-0001_工作标题/latex/` for source and the adjacent `build/` for
compiled products. Do not migrate an existing `paper/latex/` project merely to
match this convention. Keep one authoritative manuscript source; Markdown
outlines and ledgers are optional planning aids, not a second divergent draft.

After the user selects a bundled layout, from the installed skill directory:

```bash
python scripts/latex_project.py init "<paper-workspace>/latex" --layout double --language en
# Or, after the user selects single column:
python scripts/latex_project.py init "<paper-workspace>/latex" --layout single --language zh
```

Run only the selected command with the manuscript's actual language. The helper
requires `--layout`; it has no implicit column default. It refuses a nonempty
destination. For a continuing project or supplied template, edit the existing
source in place instead of rerunning initialization.

The source project contains `main.tex`, `lightwrite.sty`, `language.tex`,
`metadata.tex`, `sections/abstract.tex`, `sections/body.tex`, and
`references.bib`. Split actual sections into their own `.tex` files and update
`\input` statements when useful. Add `figures/` and `tables/` only when needed.
For existing figures, keep the adopted version/source relationship; layout
placement is not permission to redraw figures or alter their scientific data.

Use native `\label`, `\ref`, `\eqref`, and citation commands. Ordinary figures
and tables use `\linewidth`; a double-column full-width object uses `figure*`
or `table*` and `\textwidth`. Fix wide equations/tables or adjust float placement
without deleting scientific qualifications or shrinking text into illegibility.
An appendix can switch to one column when the material warrants it, but is not
mandatory. Preserve bibliography keys and the user's citation-to-claim links.

## Compile and inspect the actual result

The helper needs Python 3.10+, latexmk, the chosen TeX engine, and the packages
used by the source. The bundled reference setup uses biblatex/biber. A TeX Live
or MiKTeX environment must provide these; Python alone cannot compile LaTeX.

```bash
python scripts/latex_project.py build "<paper-workspace>/latex"
# Optional engine/output for a compatible project:
python scripts/latex_project.py build "<paper-workspace>/latex" --engine lualatex --output "<paper-workspace>/build"
```

The helper runs latexmk with the source directory as its working directory,
resolves bibliography/cross-reference passes, and writes `main.pdf`, the final
engine log, and `latexmk-output.log` to the build directory. It uses a separate
output directory and disables shell escape. It is designed for the bundled
layouts and compatible projects; a supplied template needing its own latexmk
configuration, tools, or commands uses its actual documented build workflow.

Treat nonzero exit, missing output, unresolved citations/references, duplicate
labels, or missing glyphs as build failures. A PDF left from a prior build is
not evidence the current edit compiled. Inspect overfull/underfull box and
other warnings in context; compilation alone cannot approve the visual layout.
An empty bibliography is expected for an unfilled template preview, not an
excuse to omit available references from a real paper.

Render the final PDF pages with an available PDF renderer (for example,
`pdftoppm -r 120 -png`) and inspect page images. Check title/abstract fit, actual
column count, readable formulas, table/figure widths, float placement, caption
alignment, citation resolution, fonts, page numbers, and clipping/overlap. After
a layout fix, rebuild and inspect the affected pages again. The helper reports
`visual_review: pending`; only actual inspection can finish that check.

Deliver the compiled PDF and the editable source directory, with only useful
notes about draft evidence gaps or material limitations. If the environment
cannot compile or render, state exactly what remains unbuilt/uninspected;
never substitute a text-export PDF or call an old/unopened PDF verified.
Template previews are demonstrations, not completed papers or writing-quality
evaluations.
