---
name: light-write
description: Draft, restructure, polish, translate, shorten, or consistency-check scientific manuscripts from author-provided evidence. Use for academic writing, paper drafts, manuscript editing, 中英文论文写作、论文润色、学术翻译、论文结构修改、全文一致性检查. Does not create or edit figures.
metadata:
  version: "0.3.0"
---

# light-write

## 项目目录与续作

需要落盘或继续已有项目时，先读 [项目目录约定](references/project-layout.md)，按其中的本阶段位置、版本与关联规则保存；用户指定路径和旧项目优先。包内资源相对本 skill，研究产物相对真实项目，二者不要混用。只做局部讨论时无需初始化目录。

Write or revise scientific manuscripts so that each claim is clear, useful, and supported by the material available. Treat the author's scientific meaning and evidence boundaries as invariants. Select only the workflow needed for the request.

## Route the request

First select the requested task and scale. Resolve every package path relative to the directory containing this `SKILL.md`, including paths mentioned inside reference or module files.

| Request | Load |
|---|---|
| Draft or substantially restructure a section | `references/drafting.md` and the relevant section(s) of `references/sections.md` |
| Develop a paragraph's argument or substantially improve its progression | `references/argument-and-prose.md` |
| Polish, translate, or shorten existing text | `references/polishing.md`; add the relevant section guide only for structural edits |
| Check internal consistency without rewriting | `references/consistency-check.md` |
| Organize/compress empirical findings or relocate content | `references/results-allocation.md` and `references/sections.md#results-or-findings` |
| Whole paper or multi-section translation | `references/working-ledgers.md` and `references/consistency-check.md` |
| Recurring technical terms within a section | Relevant terminology entries in `references/working-ledgers.md`; check the supplied passage, not an unavailable whole paper |
| Select structure for a genre or hybrid paper | `references/article-types.md` |
| Route domain, genre, and exact venue guidance | `references/module-routing.md` plus relevant entries in `modules/catalog.json` |
| Named journal/conference and verified requirements | `references/journal-adaptation.md`; load an exact venue module only if one exists and is applicable |
| Manuscript/section file delivery, template choice, or LaTeX/PDF build | `references/latex-output.md` |
| Continue a manuscript project, adopt Analysis/Journal outputs, or revise after Review | `references/project-integration.md` |
| Check which local draft/source files a saved revision adopted | `references/manuscript-packet.md`; optional read-only audit, not required for local edits |
| Worked synthetic illustration requested or useful for explaining approach | `references/examples.md` |
| Any task that handles research claims, data, methods, or citations | `references/integrity-and-evidence.md` |

A local sentence or paragraph normally needs only its task guide and the relevant integrity checks. Do not load every reference by default. For substantial work, use article-type routing before selecting section patterns; empirical Results allocation rules do not automatically apply to theory or review papers.

## Choose the task

- **Draft** — create text from research notes, results, an outline, or an existing draft; or restructure an argument when requested.
- **Polish** — revise existing prose for language, translation, concision, or explicitly requested structural improvement.
- **Check** — audit supplied text for internal consistency without rewriting it.

Choose from the actual user request. If the user asks only for an edit, do not draft unrelated sections. Preserve the requested output language and format. Chinese input does not by itself mean the user wants English output; translate only when asked or clearly required by the deliverable.

## Manuscript output and template choice

For manuscript drafting and typeset file delivery, read `references/latex-output.md`.
Default delivery is editable **LaTeX source plus a compiled, visually inspected
PDF**. A user-supplied LaTeX or Word template takes precedence; follow its native
format and structure. Preserve an existing project's adopted template/layout.
Without either, use the bundled generic double-column or single-column LaTeX
template. If the user has not specified the column count, **ask them to choose
double or single column before drafting**, and wait for the choice. Do not
silently assume double column, generate both, or repeat a settled choice on
each revision. Explicit text/Markdown-only requests, local wording edits,
outlines, and check-only tasks do not require this layout question or a build.

## Domain, genre, and venue

For substantial work, read `references/module-routing.md` and select applicable field guidance from `modules/catalog.json`. Compose task → evidence form/domain → article type → section → exact venue, rather than imposing a publisher's prose style on every field. Local edits need field modules only when domain meaning or inference is at stake.

All bundled field modules are draft starting guides, not expert-reviewed or performance-validated modules. No exact venue profiles are currently bundled. For an unrepresented field, fall back to the general core and use author-supplied conventions; do not invent a module or claim specialist authority. For interdisciplinary work, combine only the relevant rules from matching modules. A ranking category or publisher family is not a venue style.

## Article type and scale

Use the author's stated article type. If unclear, infer provisionally only when the materials make it safe; ask only if the type changes the structure materially. Read `references/article-types.md` for empirical research, methods/technical work, reviews/syntheses, theory/hypothesis papers, and protocols. Hybrids may combine approaches.

Scale the workflow:

- **Local edit:** preserve nearby context and verify only meaning-bearing details affected by the edit.
- **Full section:** identify paragraph jobs, build a compact claim–evidence plan, draft/edit, and check section-specific obligations.
- **Whole paper or major restructure:** use compact source, terminology, numerical-fact, and claim ledgers; check cross-section alignment and audit substantial content moves.

Ledgers need not be shown as large tables unless useful or requested. A request to save a manuscript or continue work in its project authorizes the necessary in-scope file updates; do not request the same permission again. A chat-only edit needs no project files.

## Default workflow

1. Identify deliverable, audience, article type, section, language, length, journal (if any), and output format. For manuscript file delivery, resolve the supplied/adopted template or ask the required single/double-column choice above. Infer other routine details when safe; ask only when a material ambiguity would change the argument or make the deliverable unusable.
2. Inventory the supplied evidence and constraints. For a continuing project, recover relevant Memory/Workflow context and then read the actual adopted sources; use `references/project-integration.md`. Distinguish author-provided information from externally verified information, inference, and missing support.
3. Load the minimum relevant workflow references using the table above.
4. For substantial work, define the central argument and major claim–evidence links before prose. Track recurring terminology and values where the task warrants it.
5. Draft or edit with claims close to their evidence. Preserve technical meaning, citations, numbers, uncertainty, and limitations.
6. Run a proportional check: verify the edited passage locally; for multi-section work, check terminology, numbers, definitions, abstract/body alignment, methods/results alignment, and claim strength. Record unresolved evidence and changed-source impacts; a clean file check does not settle scientific questions.
7. Deliver the requested artifact first: for the default manuscript route, compile and visually inspect the PDF and provide editable LaTeX source; follow supplied Word/LaTeX templates and explicit format overrides. For text-only/local work, deliver the revised text. Add only useful notes: material assumptions, evidence gaps, claim-boundary risks, or a concise summary of substantive changes. Respect rewrite-only requests while flagging unresolved factual conflicts that could mislead.

Before delivery, check the requested language, number of sentences/paragraphs,
edit scope, and both ends of any length range. English word counts and Chinese
character counts are different: follow the specified convention, and do not
count Latin abbreviations, numerals, or punctuation as Chinese characters when
the request explicitly specifies Han characters. Aim inside the range rather
than at a boundary. Use a counting tool when available and permitted; otherwise
revise conservatively and do not claim an exact verified count. Add substantive,
supported reasoning to reach a minimum; remove repetition before cutting
meaning-bearing content to reach a maximum. The optional `scripts/text_metrics.py`
counts a supplied UTF-8 passage using `--unit han` or `--unit whitespace_words`
and inclusive `--min`/`--max` bounds. Select the requested prose scope first;
it does not parse markup or implement a journal's counting policy.

## Non-negotiable boundaries

- Never invent data, sample sizes, statistical results, methods, mechanisms, citations, quotations, study outcomes, search procedures, author decisions, or submission files.
- Do not upgrade correlation to causation, prediction to mechanism, simulation to real-world deployment, association to proof, or a limited result to a universal claim.
- Preserve direction, units, symbols, denominators, comparisons, confidence intervals, p values, sample definitions, negation, and uncertainty. If the source conflicts with itself, flag the conflict rather than choosing a value.
- Keep relevant limitations and contrary evidence visible. Do not move evidence out of the main narrative if doing so would change interpretation.
- Use a specific placeholder such as `[Evidence needed: provide the independent validation cohort and primary metric]` for essential missing information. List material placeholders; never silently fill them.
- Treat a user's citations as supplied material, not verified sources. Preserve citation keys and intended associations; do not claim verification or fabricate bibliographic details.
- Separate hard journal requirements from editorial conventions and corpus-based advice. Verify current official requirements before asserting a limit or mandatory policy.
- This skill owns manuscript prose, captions, and their consistency with the adopted figure version. Inspect an available figure to check labels, values, and prose references, stating any unread content. Scientific/visual figure QA and figure creation/editing belong to `light-chart` or `light-diagram`; preserve their source files.
- Deliver requested manuscript files through available document/build tools and verify the actual output. Native Word redlines require real tracked changes. A change summary, coloured text, or strikethrough is not a tracked redline; never claim an unbuilt or uninspected Word/PDF artifact is ready.

## Proportional output

For a full section draft, include a concise outline and a claim–evidence map for major claims when useful. For local edits, provide the revised passage and only material notes. For a consistency audit, report issue, location, why it matters, and a concrete suggested fix; do not rewrite the whole paper unless requested. For substantial Results restructuring, provide a compact allocation/change audit when useful. Follow the user's requested format over these defaults.

## Workflow references

- `references/integrity-and-evidence.md` — source fidelity, claims, citations, numerical integrity, missing inputs, and compression safeguards.
- `references/drafting.md` — evidence-led drafting and argument reconstruction.
- `references/argument-and-prose.md` — argument progression, manuscript voice, and scoped conclusions.
- `references/polishing.md` — editing, translation, tightening, and revision reporting.
- `references/sections.md` — operational prompts for common manuscript sections.
- `references/article-types.md` — genre-specific argument loads and structure cautions.
- `references/working-ledgers.md` — source, claim, terminology, and numerical-fact ledgers.
- `references/results-allocation.md` — finding classification, placement, and compression audits.
- `references/consistency-check.md` — cross-section terminology, numbers, claims, and references.
- `references/journal-adaptation.md` — optional target-journal adaptation and official-requirement checks.
- `references/latex-output.md` — user-template priority, required column selection, bundled LaTeX templates, compilation, and PDF inspection.
- `references/examples.md` — synthetic examples for ledger-to-prose and evidence allocation.
- `references/project-integration.md` — project recovery, native upstream checks, source changes, and manuscript/figure/review loops.
- `references/manuscript-packet.md` — optional local revision receipt and narrowly scoped file/text checks.
