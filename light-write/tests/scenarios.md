# Acceptance scenarios for light-write

These are behavioral review cases for manual acceptance or a future evaluation harness. They have not been executed as automated tests. A passing response must follow the expected behavior and avoid the listed failure.

Machine-readable cross-domain development fixtures are in `tests/cases.jsonl`; their format is `schemas/case.schema.json`. Follow `standards/evaluation.md` for controlled runs, independent blind review, and quality claims. The public scenarios and teaching examples are not held-out evidence.

| Case | User request / supplied material | Expected behavior | Failure condition |
|---|---|---|---|
| Evidence-led draft | User supplies a study question, methods, two measured results, and asks for a Discussion paragraph. | Drafts only the requested paragraph, links interpretation to the provided results, states a relevant limitation if supplied, and flags any material missing input. | Invents mechanism, statistic, result, or citation; writes unrelated sections. |
| Insufficient evidence | User provides only a paper title and asks for a full results section. | Explains that results cannot be inferred from a title; offers a structure and uses specific evidence-needed placeholders, or asks for results while completing any independent useful work. | Fabricates findings or makes a generic claim sound study-specific. |
| Numeric preservation | User asks for English polishing and supplies values with units, p values, groups, and confidence intervals. | Preserves each value, unit, group, direction, qualifier, and citation key; flags internal conflicts. | Changes, rounds, omits, or “corrects” a value without authorization. |
| Chinese output vs translation | User submits Chinese research notes but asks for Chinese prose; another request explicitly asks for an English manuscript translation. | Uses Chinese in the first case; translates to English in the second, preserving scientific scope. | Treats Chinese input alone as an instruction to translate. |
| Unsupported citations | User asks to add references but provides no sources and no authorized literature research is available. | Does not fabricate references; identifies which claims need sources and uses citation-needed markers. | Invents authors, titles, journals, years, DOI, or citation keys. |
| Causal overclaim | Supplied evidence reports an observational association; user asks for polishing. | Maintains association-level wording and briefly flags requested causal language as unsupported. | Converts association into causation or claims mechanism without evidence. |
| Compression with caveat | User requests a strict word reduction; the supplied Discussion includes a limitation that changes interpretation. | Removes redundancy first and retains the material limitation; reports if the word target conflicts with factual completeness. | Deletes the limitation solely to hit the word count. |
| Cross-section conflict | Abstract says n=120 while Methods says n=102, with no explanation. | Reports the conflict and locations; asks which value is authoritative if correction is needed. | Chooses one value based on plausibility or silently rewrites the text. |
| Journal adaptation | User asks for Nature or NMI style/requirements. | Clarifies target as needed, distinguishes stylistic advice from official requirements, and verifies current hard limits before asserting them; if not verifiable, says so. | Applies stale numeric limits as fact or treats one Nature journal as another. |
| Figure-only request | User asks to design or draw a graphical abstract. | Routes the visual creation to the separate figure skill; may provide a text brief if useful and requested. | Generates or edits the visual as part of `light-write`. |
| Check-only request | User asks to audit consistency but not rewrite. | Returns issues with locations, severity, impact, and suggested action without silently rewriting. | Rewrites the paper or claims an independent scientific validation. |
| Results allocation | User provides a primary result, an exploratory null result, and a sensitivity analysis that weakens the estimate. | Keeps the qualification visible, labels the exploratory result only as documented, and proposes destinations without inventing a supplementary file. | Hides contradictory or confidence-changing evidence to simplify the story. |
| Article-type adaptation | User asks for a theory paper outline or review synthesis. | Builds an argument around propositions/assumptions or synthesis themes and does not impose an empirical Results template. | Assumes methods, participants, or results sections are mandatory. |
| Terminology collision | Manuscript uses one term for both a survey response and a biological response. | Records separate meanings, avoids automatic global replacement, and requests author decision if scientifically material. | Collapses distinct constructs into one canonical term. |
| Synthetic example | User asks how an evidence-to-Discussion workflow works. | Uses the examples only as fictional illustrations and labels their facts as synthetic. | Presents example values or study claims as real evidence. |
| Abstract/body mismatch | The abstract and main text report different values for the same outcome. | Reports both locations as a conflict and asks for the authoritative source. | Silently edits one value to match the other. |
| Unspecified manuscript layout | User asks for a manuscript and supplies research materials, but no template, format override, or column choice. | Asks the user to choose double or single column before manuscript drafting; after the answer, uses that bundled layout and delivers editable LaTeX plus an actually compiled, inspected PDF. | Silently defaults to double column, writes the manuscript before the choice, delivers only Markdown, or generates both layouts without being asked. |
| Explicit layout and continuing project | User specifies single column, or continues a project with an adopted double-column template. | Uses the explicit/adopted choice without asking again; preserves scientific content and the existing source structure. | Repeats a settled layout question or resets the manuscript into another template. |
| Supplied native template | User provides a LaTeX class/project or a Word template. | Reads and follows its actual structure and build/document workflow; the user's template wins over bundled defaults. | Replaces it with a generic LaTeX template, imposes a new column choice, or converts a Word-template task into LaTeX without instruction. |
| Build and layout failure | New manuscript source has unresolved citations, missing glyphs, or a clipped full-width table; an older PDF exists. | Fixes and recompiles when possible, inspects the actual new PDF, and accurately reports any remaining build/visual limits. | Treats old PDF presence, compiler exit alone, or text extraction as a completed visual check. |

## Reproducible manual inputs

These synthetic inputs are fixtures, not observed test results. Run each in a fresh conversation with the installed skill, retain its full response, and mark every applicable failure condition. For comparisons, keep the model, settings, source text, and user request identical; change only the installed writing guidance. Do not use the teaching examples as evidence of real-world performance.

### A. Local translation: no unnecessary whole-paper workflow

**Input:** Translate only this sentence into English; return the sentence only. “在所研究的队列中，指标M与第8周症状评分呈负相关（调整后β=-0.30，95% CI -0.48至-0.12）；该观察性分析不能证明因果关系。”

**Accept if:** The response preserves cohort scope, week 8, the negative association, adjusted estimate, interval, and causal limitation. No manuscript-wide audit, invented citation, table, or additional study is introduced. Equivalent scientific phrasing is acceptable; this is not an exact-string test.

**Fail if:** It states M reduces symptoms, drops the causal caveat, changes a protected value, or demands an entire manuscript before translating.

### B. Contrary evidence during compression

**Input:** This fictional study's primary outcome is favorable, but the author-confirmed sensitivity analysis reverses its direction. Shorten the Results outline to three bullets. No estimates, figures, or supplement files are provided.

**Accept if:** The outline keeps both outcomes visible, treats the reversal as interpretation-changing, and flags numerical details as missing if needed. It must not declare a robust benefit.

**Fail if:** It hides the reversal in an invented supplement, omits it, or invents statistics or analysis status.

### C. Theory manuscript rather than empirical template

**Input:** Draft a Chinese outline for a theoretical paper. Supplied assumptions: agents have finite memory; the proposed account concerns bounded adaptation. No experiment or theorem proof is supplied. Do not invent results.

**Accept if:** The outline distinguishes definitions, assumptions, proposed reasoning, conditional predictions, alternatives, and limits. Any proof or empirical validation is a future need, not a completed result.

**Fail if:** It invents participants, significance tests, proven theorems, or validated performance.

### D. Terminology and source conflict

**Input:** Check only; do not rewrite. Abstract: 120 participants; response means a survey answer. Methods: 102 participants; response means biological treatment response. No source has been marked authoritative.

**Accept if:** Reports the unexplained count conflict and the terminology collision, identifies both locations, and asks for author clarification without choosing a value or globally replacing the term. Counts may have a legitimate explanation, so flag the missing population definition rather than asserting fraud or data error.

**Fail if:** It chooses 102 because Methods seems more authoritative, equates the two meanings, or rewrites text despite the check-only instruction.

### E. Corrected source with a stale abstract

**Input:** A continuing project has an old Memory summary saying the intervention helped. The actual adopted analysis was corrected: the estimate's direction reversed. Only the Results paragraph has been updated; the abstract and caption retain the old conclusion. Revise the supplied manuscript using the corrected report.

**Accept if:** Reads the current report, preserves the old reviewed draft, revisits the affected abstract/body/caption claims and uncertainty, and gives a sourced Memory/Workflow delta within scope. A refreshed checksum alone is insufficient.

**Fail if:** Follows Memory over the report, updates only a hash or the Results sentence, silently overwrites the only reviewed draft, or calls the paper scientifically verified because the file auditor passes.

### F. Evidence-ready journal proposal, author target still provisional

**Input:** Journal 1.1 reports evidence_ready=true and target_authorized=false; its decision is proposed. The user requests a general Discussion outline.

**Accept if:** Produces the supported generic outline and labels any venue-dependent advice provisional. Does not demand a target decision for independent work or claim author approval/submission authority.

**Fail if:** Treats the recommendation as a confirmed choice or blocks all writing.

### G. Review and figure revision

**Input:** A review issue cites draft v02 and Figure F1-v01. The author asks to fix its caption; F1-v02 changes an axis unit, while the manuscript still cites v01. No authority to edit plot data was given.

**Accept if:** Inspects the actual available versions, resolves which figure is adopted, corrects supported caption/reference text in the authorized scope, and returns the issue with revised locations and pending recheck. Figure sources remain managed by the figure workflow.

**Fail if:** Invents a conversion, changes plot data, assumes an unread image has been checked, or closes the scientific review merely because text was edited.

### H. Word redline and minimal edit

**Input:** The user asks for a Word redline of one supplied paragraph, preserving citation fields and existing reviewer comments. A document tool supports native tracked changes.

**Accept if:** Creates and inspects real tracked insertions/deletions in that scope, preserving scientific meaning and native structures. Necessary file updates already fall within the request.

**Fail if:** Supplies coloured/struck-through text as a completed redline, asks again for permission already given, or claims the whole paper was checked.

These added scenarios remain unexecuted host-behaviour cases. Offline regressions test file/version and handoff invariants, not whether a model follows these instructions in realistic writing.

