# Manuscript consistency check

Use for a whole manuscript, multiple related sections, or an explicit consistency audit. For a local edit, check only the changed passage and nearby context unless asked to go wider. This is an editorial comparison of supplied text, not an independent scientific validation.

Use the source inventory and ledgers in `references/working-ledgers.md` when the manuscript is long enough that terms, numerical facts, or claims recur. Compare against the authoritative source when one is identified; otherwise mark the conflict rather than choosing the most recent draft. After an approved terminology or claim change, update the ledger and recheck affected occurrences across the supplied text.

## Compare across the manuscript

1. **Study identity and scope:** research question, objectives, population, materials, setting, inclusion criteria, and study design.
2. **Terminology:** preferred terms, spelling, capitalization, abbreviations, symbol conventions, and names for groups, outcomes, methods, and measures.
3. **Numbers and definitions:** sample counts, exclusions, denominators, time points, units, rounding, group labels, effect estimates, uncertainty intervals, p values, and outcome definitions.
4. **Evidence-to-claim alignment:** claims in the title, abstract, introduction, results, discussion, and conclusion; causal strength, certainty, novelty, and generality; primary versus exploratory status.
5. **Methods-to-results alignment:** each reported analysis has a corresponding described method; each described primary outcome or analysis is represented appropriately in results, subject to the provided material.
6. **Citations and cross-references:** citation keys, figure/table numbering, section references, supplementary references, and whether the cited object appears to support the associated text. Without source access, check only internal presence and consistency, not source accuracy.
7. **Limitations and qualifications:** important caveats remain consistent and are not contradicted or dropped between sections.
8. **Abstract alignment:** abstract claims, values, and conclusions match the body.
9. **Adopted versions:** the prose, captions, figures, analysis, and venue brief refer to the versions actually used. Inspect available referenced objects and preserve unread/unchecked scope. A changed source needs a substantive impact check, not just an updated hash; see `references/project-integration.md`.

If a numerical limit is part of the task, check both endpoints under the requested counting convention. `scripts/text_metrics.py` can count a selected plain-text scope, but does not select that scope, strip markup, or infer the venue's word-count rules.

## Report findings

Use a compact table when there are multiple issues:

| Severity | Location(s) | Inconsistency | Why it matters | Suggested action |
|---|---|---|---|---|

Use severity labels proportionally:

- **High:** could change scientific interpretation, primary claim, safety implication, or reported value.
- **Medium:** materially affects clarity, reproducibility, or alignment but does not obviously reverse the central conclusion.
- **Low:** terminology, style, or cross-reference inconsistency with limited interpretive effect.

Quote only the shortest passage needed to locate the issue. Distinguish confirmed textual inconsistency from a possible scientific issue requiring author review. Never resolve a conflict by choosing the value or claim that seems more plausible. End with a concise overall status and any author decisions required. Do not silently rewrite the manuscript during a check-only task.
