# light-write

`light-write` is a writing skill for drafting, polishing, and consistency-checking scientific manuscripts, currently **0.3.0**. It adapts the task distinction and evidence-aware principles in `nature-writing` and `nature-polishing` from [nature-skills](https://github.com/Yuan1z0825/nature-skills) into a reorganized, standalone workflow for scientific writing in general.

## What it does

- **Drafting and argument restructuring:** Develops requested manuscript sections from author-provided research questions, results, methods, notes, or existing text.
- **Polishing and translation:** Improves academic expression, reduces redundancy, makes requested structural edits, or translates between Chinese and English while preserving scientific meaning and evidence boundaries.
- **Manuscript consistency checks:** Checks terminology, values, populations, analysis definitions, citations, and claim strength across sections.
- **Genre-aware writing:** Adapts the argument load for empirical, methods/technical, review/synthesis, theory/hypothesis, and protocol manuscripts instead of forcing one template.
- **Cross-domain modules:** Routes by domain, genre, and exact venue, loading focused guidance only when relevant. All first-wave field modules are draft; none has expert review or model quality evaluation.
- **Reproducible evaluation design:** Specifies fixed configurations, blinded review, serious-error reporting, and revision-cost recording. Bundled synthetic cases are smoke/regression fixtures, not proof of writing quality.
- **Results allocation:** For substantial Results restructuring, classifies findings and helps decide what belongs in prose, captions, Methods, Source Data, or supplementary material; includes a proportional compression audit.
- **Working ledgers:** Uses compact source, claim–evidence, terminology, and recurring numerical-fact records for multi-section tasks.
- **Synthetic examples:** Includes small, explicitly fictional teaching examples showing evidence-to-prose decisions.
- **Optional journal adaptation:** Adapts framing to a journal or style named by the user. Specific submission requirements should be checked against current official sources.
- **LaTeX and PDF delivery:** Manuscripts default to editable LaTeX source and an actually compiled, inspected PDF. Bundled double/single-column layouts require the user's choice if unspecified; a supplied LaTeX/Word template takes precedence.

Creating or editing figures, charts, images, or graphical abstracts is outside this skill; route those tasks to the figure skill in your research workflow. `light-write` can draft captions or manuscript references to figures based on materials provided by the author.

## Continuing projects and revisions

One core paper uses one `Write/PAPER-0001_工作标题/` workspace; revisions and retargeting stay within it. Local edits do not require project initialization, a ledger, or a JSON packet.

- Recover relevant Memory/Workflow context, then read actual adopted analysis, literature, Journal guidance, and manuscript/figure versions. Retain native Analysis verification warnings; Memory does not replace evidence.
- Journal 1.1 separates the author's/authorized target decision from evidence readiness. Preserve article type, publication route, submission stage, and unverified policies. Generic argument/outline work may proceed under a provisional target.
- Source corrections require rereading and impact checks across affected claims, abstract/body, captions, and response letters before adopting the new version. Chart/Diagram retain figure sources; Review fixes refer to the actual reviewed revision and need rechecking.
- An in-scope request to save or continue the manuscript authorizes necessary file updates. Requested Word/PDF outputs use available document/build tools and actual verification; Word redlines require native tracked changes.

Optional `scripts/audit_manuscript.py` reads the revision receipt in `templates/manuscript-packet.json`. It checks listed file SHA-256 values, declared claim anchors, and selected literal presence; it never writes files or refreshes hashes. It cannot certify semantics, citations, scientific validity, or submission readiness, and unresolved draft claims remain warnings even when file checks pass. See [project integration](references/project-integration.md) and the [optional receipt contract](references/manuscript-packet.md).

## Installation

Install the complete `light-write` directory in a Claude Code skills directory. Retain `SKILL.md`, `references/`, `modules/`, `templates/`, `scripts/`, and referenced standards; copying the complete package is recommended. For example:

```text
<project>/.claude/skills/light-write/
```

You may also use the user-level skills directory supported by your Claude Code setup. Copying only `SKILL.md` omits the on-demand guidance. Once installed, invoke it with tasks such as “draft the Discussion,” “polish this paragraph,” or “check terminology and results across the manuscript.”

## Useful input

Provide whatever is relevant to the task; the full list is not required:

- Requested section, article type, target journal/readers, language, length, and output format.
- Research question, methods, results, statistics, figure descriptions, limitations, and author-confirmed conclusions.
- Terms, abbreviations, values, citation keys, or wording that must be retained.
- Permitted edit level: language-only, tightening, local restructuring, or substantial argument reconstruction.

## Output

Manuscript and typeset-file tasks default to **editable LaTeX source plus a
compiled PDF**. Follow a supplied LaTeX or Word template first, preserving its
native structure and format. Continue an existing project's adopted layout.
Otherwise use the bundled **double-column** or **single-column** generic
LaTeX template. If columns are unspecified, ask the user to choose before
drafting and wait for the answer. Do not silently choose double column,
generate both versions, or ask again on each revision.

The double-column layout uses A4/10 pt with a full-width title, authors, and
abstract. The single-column layout uses A4/11 pt with the same visual hierarchy.
Neither is an official venue template. Suggested new-project paths are
`Write/PAPER-0001_工作标题/latex/` for source and adjacent `build/` for the PDF;
explicit paths and existing project layouts take precedence.

Local wording edits, outlines, check-only tasks, and explicit text/Markdown-only
requests still return the requested text without a layout question or a build.
A full-section draft may include a short outline and major claim/evidence map;
local edits need no table. Do not hide factual conflicts behind minimal output.

After the user chooses a layout, run only its initialization command:

```bash
python scripts/latex_project.py init "<paper-workspace>/latex" --layout double --language en
python scripts/latex_project.py build "<paper-workspace>/latex"
```

Use `--layout single` for single column and `--language zh` for Chinese/mixed
text. XeLaTeX is the default build engine. Compilation requires latexmk, the
engine, and relevant packages including biblatex/biber in TeX Live or MiKTeX.
Initialization refuses a nonempty destination; PDFs must actually be rendered
and inspected after compilation. See [templates and delivery](references/latex-output.md).

Layout previews: [double-column PDF](templates/latex/previews/double-column.pdf)
and [single-column PDF](templates/latex/previews/single-column.pdf). Their text
is template guidance with explicit author-information placeholders, not a
research manuscript. Initialization includes the shared resources in
`templates/latex/common/`.

## Research integrity and boundaries

- Do not invent data, sample sizes, statistical results, methods, mechanisms, sources, search procedures, or DOIs.
- Do not turn correlation into causation, prediction/simulation into mechanistic proof/real-world deployment, or limited evidence into unsupported novelty, generality, or superiority claims.
- Preserve units, numerical direction, comparison baselines, p values, intervals, negation, qualifiers, citation associations, and material limitations. Flag conflicting inputs for author confirmation.
- Mark missing information with specific placeholders rather than guessing from disciplinary convention. User-provided citations are not presumed verified.
- Distinguish hard journal requirements from writing advice; do not claim a requirement is current if it cannot be verified.
- This skill owns manuscript prose. New research analyses, literature searches, figure-source changes, independent peer review, and submission operations use their relevant workflows. File deliverables can use suitable document/typesetting tools; unbuilt or unverified artifacts must not be presented as complete.

## Files

- `SKILL.md`: entry point, routing, and core boundaries.
- `references/`: focused guides for drafting, polishing, section workflows, article types, ledgers, Results allocation, evidence integrity, consistency checks, journal adaptation, and examples.
- `modules/`: seven draft field guides and the static catalog; their scopes are starting points, not validated coverage.
- `standards/`, `templates/`, `schemas/`: module and evaluation standards, contributor templates, and machine-readable contracts.
- `tests/scenarios.md` and `tests/cases.jsonl`: manual scenarios and synthetic development fixtures; neither is an executed quality report.
- `scripts/validate.py`: optional offline structural checks; no model calls.
- `scripts/audit_manuscript.py` and `scripts/text_metrics.py`: optional read-only revision checks and explicit-scope text counts, not automated scientific review.
- `templates/latex/` and `scripts/latex_project.py`: generic double/single-column templates, explicit-layout initialization, and compilation; build success is not visual or scientific approval.
- `CONTRIBUTING.md`: extension, review, data-rights, and licensing guidance.
- `THIRD_PARTY_NOTICES.md` and `LICENSES/Apache-2.0.txt`: upstream provenance and applicable license information.

## Architecture and current coverage

The general core handles drafting, editing, evidence fidelity, and consistency. Field modules describe evidence forms and argument practices; genre guidance adapts article purpose; exact venue modules cover only in-scope official requirements and editorial guidance. See `references/module-routing.md`. Interdisciplinary work can combine relevant rules. Uncovered areas fall back to the general core; the skill must not invent specialist authority.

The first-wave modules are computing, life-sciences, clinical-health, physical-sciences-engineering, social-behavioral, mathematics-theory, and humanities. These are drafts awaiting specialist contributors, not complete coverage or a guarantee of top-tier writing across those fields. No exact profiles for Science, Cell, CVPR, or other venues are bundled yet. CCF A is a ranking category and IEEE is a publishing organization/system, not a single style.

Maturity progresses from draft to reviewed to evaluated. “Evaluated” means evidence exists for a defined scope; whether targets were met must be read from the report. All bundled modules currently have empty review and evaluation references.

## Validation and evaluation

From the package root, run:

```bash
python -I scripts/validate.py
python -B -m unittest discover -s tests -q
```

Text-only writing needs no external runtime. Template initialization/build helpers and contributor validation use Python 3.10+ standard library; compiling PDFs additionally needs a TeX environment, and visual checking needs a PDF renderer. The validator checks package structure, metadata, paths, module/case associations, and an implemented subset of the data contracts. It is not a full JSON Schema engine. `--run` can validate a separately produced record; the script does not generate or execute model outputs.

The evaluation protocol is in [standards/evaluation.md](standards/evaluation.md). Development cases are in [tests/cases.jsonl](tests/cases.jsonl), with manual scenarios in [tests/scenarios.md](tests/scenarios.md). An actual model-call development pilot now retains upstream comparisons, post-change reruns, full inputs/outputs, hashes, and blinded model-assisted ratings; see [the pilot report](evaluations/2026-10-27-pilot/REPORT.md). No independent domain-expert blind review or top-tier validation has been conducted. These synthetic short-passage results do not generalize to all fields, long manuscripts, or other models.

The historical pilot led to argument/prose guidance, explicit length-range and Chinese-character checks, and clearer mathematical parameter dependence. Fourteen post-change outputs were completed, also exposing regressions in engineering and humanities tasks. The final domain-specific corrections are pending retest: all seven planned follow-up calls hit the usage limit and produced no writing. Reused cases are regression cases after tuning. `scripts/analyze_pilot.py` writes derived summaries: use an isolated bundle copy with its BUNDLE explicitly configured rather than rerunning it on archived history as if read-only. Generation/review actions in `scripts/run_pilot.py` call the locally authenticated Codex CLI and consume its allowance; they are not offline structure checks.

The 0.2.0 upgrade adds project integration, revision receipts, explicit Han/whitespace-token counting, and protection for failed/interrupted evaluation attempts. Offline regressions and an isolated native Analysis→Journal→Write handoff were executed; see [the upgrade record](evaluations/2026-11-06-upgrade.md). No new independent model writing-quality evaluation or real research-project validation was performed. The seven field modules remain draft. The counter measures only supplied text; it does not parse Markdown/TeX or implement a venue's counting policy.

Version 0.3.0 adds default LaTeX+PDF delivery, user-template priority, an explicit
pre-drafting single/double-column choice, and two generic layouts. Both layouts
were built locally with XeLaTeX in English and Chinese and their rendered pages
inspected. Explicit synthetic fixtures exercised biber, cross-references,
footnotes, and a full-width table across page transitions. The 54 offline tests
cover selection, existing-source preservation, build failures, stale PDFs,
missing tools, unresolved references, and pending visual review, among the
package's other contracts. These are not new model writing-quality evaluations.

## Upstream provenance and distribution

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for upstream provenance. This package includes an Apache-2.0 license text for applicable upstream obligations; **this does not mean all original light-write material has been assigned Apache-2.0**. Maintainers must choose and add a clear project license before open-source distribution. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution requirements.
