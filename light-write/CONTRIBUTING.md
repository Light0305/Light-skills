# Contributing to light-write

Thank you for helping make scientific-writing guidance more accurate across fields. Contributions should add bounded, sourced, testable guidance—not promises that a module writes at “top-tier” quality.

## Before adding a module

1. Identify a real gap not handled by the general core or an existing module.
2. Choose a narrow scope, article types, evidence forms, language, and explicit exclusions. Do not add a venue module for a publisher family or ranking label.
3. Start from `templates/field-module.md` or `templates/venue-module.md` and follow `standards/modules.md`.
4. Cite only sources you actually consulted. For official rules, record the official URL, access date, applicability, effective date when known, and unknowns. Separate mandatory policy from editorial inference.
5. Add the module to `modules/catalog.json`; include provenance and honest maturity. Draft modules have no review/evaluation references.
6. Add at least one synthetic development fixture and acceptance notes. A synthetic fixture is a smoke test, not evidence of expert-level quality. Do not put test rubric fields into model-visible inputs.
7. Run `python -I scripts/validate.py` and review errors. This validates selected file/metadata/data-contract rules only; it does not run a full JSON Schema engine, a model, or a writing-quality benchmark.

## Maturity and review

Use only the states in `standards/modules.md`. To move beyond `draft`, attach the actual review/evaluation record and evidence required by that standard. Preserve original independent ratings, reviewer consent/anonymity, disagreements, raw outputs, configuration, and limitations. Never invent reviewers or mark an evaluation complete because the validator passes.

## Evaluation and data rights

Follow `standards/evaluation.md`. Freeze model/harness and skill snapshots; retain full failures; use blinded domain-qualified review for quality claims. Confirm rights and de-identify human research material before evaluation or publication. Never add confidential, identifiable, embargoed, or unlicensed manuscript material to public fixtures.

## Provenance and license

The current package contains an Apache-2.0 license copy and an upstream notice for nature-skills-derived workflow ideas. That does **not** establish that all original light-write content has an open-source license. Before public redistribution, maintainers must select and add a clear project license and confirm rights for contributions. Contributors should state that they have authority to submit their work and identify any third-party source or license. Do not copy upstream material without complying with its applicable license and notices.

## What review does not mean

A domain review checks a documented scope; an evaluation checks a defined sample under recorded conditions. Neither alone proves universal field coverage, acceptance probability, publication quality, or superiority to another skill. Public claims must match the evaluated scope and evidence.
