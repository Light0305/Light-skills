# Evaluation protocol

Evaluate the skill's effect on writing, not whether a response resembles one journal's prose. Structural checks and synthetic fixtures cannot establish expert-level quality. A retained synthetic development pilot with actual model outputs is documented in [the pilot report](../evaluations/2026-10-27-pilot/REPORT.md); no independent domain-expert evaluation has been completed. Its model-assisted ratings do not establish expert-level quality.

## 1. Define the claim and freeze the comparison

State the domain, subfield, genre, language, task, manuscript scale, and target venue/type/edition when relevant. Predeclare the quality threshold, serious-error definitions, sample size, repetitions, exclusions, and budget before generation. Choose a configuration the operator can actually reproduce; record unavailable settings as unavailable, never guess them.

Useful comparison arms:

- **Baseline:** same model/harness without writing guidance.
- **light-write:** a frozen snapshot of the entire package, with actual loaded files recorded.
- **Upstream:** nature-writing for drafting and nature-polishing for editing, installed with the required shared/reference dependencies. Record upstream commit and actual loaded files. For check-only tasks, predeclare the appropriate upstream route.

Hold the model/version, effort and supported generation settings, maximum output, harness/system instructions, tools/permissions, input, and user output requirements constant. Record cross-arm differences if an equivalent setup is impossible. A plain prompt with concatenated files tests a fixed-context prompt, not automatic skill discovery; label it accordingly. Separate routing/installation tests from writing-quality tests.

## 2. Source cases and prevent leakage

Each JSONL case follows `schemas/case.schema.json`. Give the model the same `source_facts` and `request` in each arm. Do not give it the rubric fields (`must_preserve`, `must_not`, `expected_modules`, `scoring_notes`); those are evaluator-only annotations. Frozen source text may be included verbatim in source_facts. For larger source files, establish a new versioned case contract with immutable attachment hashes before evaluation; do not silently substitute a summary.

The bundled `tests/cases.jsonl` contains only synthetic **development** fixtures for smoke/regression checks. They are public, inspectable, and unsuitable as held-out evidence. `references/examples.md` is teaching material, not a test set.

For quality claims, obtain legally reusable, de-identified real research material with author consent where needed. Record provenance/rights and exclude confidential, embargoed, participant-identifying, or unlicensed material from public releases. Maintain development, validation, and held-out test cases separated by source project/manuscript, not just by paragraph. Do not tune on the test cases or publish their scores repeatedly while editing against them. Public release makes a held-out set public; replace it for future claims where contamination matters.

Sample more than one field, genre, task, and manuscript scale. A single fixture per broad field says nothing about the field's overall writing quality. Select sample size based on the comparison and uncertainty you need; report limitations rather than claiming universal coverage from convenience cases.

## 3. Run and retain evidence

For each arm/case/repetition, use a fresh context and the frozen input. Record the effective provider/model, resolved fallback model if any, harness version, all settings/system instructions, tool policy, skill snapshot identifier, loaded file paths with SHA-256 hashes, full input and output, stop reason, and tool evidence. An unobserved tool/loading event is unknown, not a successful load. Retain refusals, truncations, installation failures, and failed outputs; label them rather than silently retrying until a good sample appears. Record every retry as a separate run or with the full attempt trail.

Use `schemas/run.schema.json` for completed generation records. `reviews: []` means not yet rated; an unrated run is not a pass. `status` is generation status, not scientific correctness. Each artifact path is relative to the retained evaluation bundle, with hashes recorded; no credentials belong in a record. The optional `scripts/run_pilot.py` is a locally authenticated fixed-context model runner; generation/review consumes the operator's allowance and is never part of offline tests. Choose the setup and budget before making calls.

Before admitting an output to a review packet, require completed status, actual nonempty retained prose, and equality with the recorded output. A later completed attempt with missing/changed prose is not replaced silently by an earlier answer. Failed or interrupted attempts are retained; an explicit retry uses a fresh numbered directory, including when interruption occurred before record.json was written. `scripts/analyze_pilot.py` writes derived summaries; use an isolated bundle copy with its BUNDLE configured for re-auditing archived artifacts. Do not rerun generation, snapshotting, or derived-summary writes on a frozen historical bundle.

Keep manuscript-file/anchor tests and text-length checks separate from writing-quality evaluation. A passing `scripts/audit_manuscript.py` receipt can still accompany a scientifically overstated sentence: it checks declared byte/string links, not semantic entailment. Future quality runs must inspect the actual prose under the scientific rubric below.

## 4. Grade errors before elegance

Record these serious failure types separately, each with an output/source locator and rationale:

- fabricated evidence, method, statistic, source, quotation, or completed author action;
- unauthorized material change to a protected numerical or logical fact;
- unsupported causal, mechanistic, universal, novelty, or deployment claim;
- concealed counterevidence or qualification that changes interpretation;
- scope violation that makes the requested deliverable unusable.

Interpret these in context. An explicitly requested proposal is not a fabricated completed experiment; omission in an outline is not necessarily a meaning-changing omission. Adjudicate scientific errors with a qualified reviewer. Do not let a high language score offset serious errors. Automated numeric/citation checks are useful flags, not proof of semantic preservation.

Grade each dimension 0–4, or null when inapplicable, with a short reason and output locator:

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| factual_fidelity | Material facts/logical scope changed | Material ambiguities remain | Meaning and protected facts preserved |
| evidence_calibration | Claims exceed support | Some uncertainty/scope poorly expressed | Claims exactly calibrated to evidence |
| task_completion | Wrong/unusable task output | Partly meets requested deliverable | Meets scope, language, format and edit level |
| argument_quality | Incoherent or unsupported chain | Understandable but substantial gaps | Clear, purposeful, well-supported progression |
| domain_appropriateness | Imposes inappropriate conventions | Mixed disciplinary fit | Fits actual method, evidence form and audience |
| language_quality | Obscures meaning | Usable with substantial edits | Precise, readable and economical |
| gap_handling | Invents or hides missing inputs | Flags some gaps indiscriminately | Specific material gaps without blocking independent work |

Scores 1 and 3 represent intermediate performance. Null is not zero; do not count it in means. Record author revision time separately in minutes when measured, with task boundaries and a log of major repairs. Do not invent a minute estimate from a quality score.

## 5. Blind review and adjudication

Randomize response order and replace arm names with blind IDs. Keep the ID-to-arm map separate from reviewer packets. At least two domain-qualified reviewers independently rate quality cases using identical source material/rubrics, without seeing each other's ratings or module provenance. Record expertise (with consent/anonymization), conflicts, rating disagreements, and any disclosed unblinding. Scientific style is not a single correct answer: compare defensible alternatives, not similarity to a gold paragraph.

Preserve both original reviews. A separate adjudication record references run/case and reviewer IDs, disputed items, rationale, final judgments, adjudicator expertise, and date; never overwrite independent scores. Model-assisted review may triage issues, but is not a substitute for independent domain review or evidence of field-expert quality.

## 6. Report scope and uncertainty

Report per field/genre/task: case counts, all attempted runs, completion/truncation/refusal rates, serious-error counts/rates, dimensional score distributions, pairwise preferences if collected, and measured revision cost. Repetitions from one case are correlated; use cases/manuscripts as the comparison unit, or cluster uncertainty estimates at that level. State the method and intervals; do not imply a tiny sample yields a precise ranking.

Keep model/harness effects separate from skill effects and report loaded-context cost/latency where measured. Do not pool humanities interpretation and benchmark reporting into a universal style score. Register a new evaluation when major guidance changes. A module's `evaluated` maturity means evidence exists; the report must separately say whether the prespecified quality targets were met.

Claims such as “top-tier across all fields” require substantially broader evidence than these fixtures. Publish the tested scope and remaining gaps instead.
