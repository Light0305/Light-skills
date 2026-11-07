# Field and venue module contract

A module adds context-specific writing decisions to the general core. It must not duplicate integrity rules, invent official policies, or imply that a discipline has one writing style.

## Catalog entry

Each entry in `modules/catalog.json` has:

- `id`: stable lowercase slug; unique within the catalog.
- `kind`: `field` or `venue`.
- `path`: existing root-relative Markdown path within the package.
- `scope`: precise applicability, including exclusions where material.
- `maturity`: `draft`, `reviewed`, or `evaluated`.
- `provenance`: list of sources or an explicit statement that the guide is an unvalidated editorial draft. Never invent expert review, corpus studies, official sources, or access dates.
- `review_refs`: local records supporting expert review; empty for draft modules.
- `evaluation_refs`: local records supporting evaluation; empty until an actual evaluation exists.

See `schemas/module.schema.json` for the machine-readable catalog contract. The bundled validator checks selected invariants; it is not a full JSON Schema implementation.

## Required module sections

Use `templates/field-module.md` or `templates/venue-module.md`. Each module should explain scope and maturity, the argument/evidence load, concrete section and language decisions, failure modes, interaction with other modules, provenance, and verification status. A venue module additionally identifies the exact venue, article type, year/stage, official-rule sources and dates, and a policy for stale requirements.

Write actionable rules: a condition, a writing decision, and a limit or counterexample. “Write clearly and persuasively” is not sufficient. Illustrations must be synthetic or legally reusable with clear attribution. Do not turn a small corpus's local convention into a universal disciplinary norm.

## Maturity is evidence, not a badge

- **draft:** written guidance exists, but no documented independent expert review or performance evidence supports it. Bundled starting modules are all draft.
- **reviewed:** at least one recorded domain-expert review addresses the module's scope, major rules, disputed conventions, and changes. The record includes module version/hash, reviewer expertise/consent, date, unresolved limitations, and author action. Review alone establishes no output-quality benchmark.
- **evaluated:** a reviewed module has an actual evaluation record following `standards/evaluation.md`, with frozen guidance and case versions, configuration, raw outputs, blinded ratings, serious-failure counts, and limitations. This status means evaluated, not necessarily that it passed a quality target or generalizes beyond the tested scope.

A substantive change to evaluated rules requires review and a new evaluation; do not silently carry a maturity label across changes that invalidate its evidence. Records may use public anonymized reviewer identifiers, with expertise and consent recorded privately where appropriate. Do not publish identifying review records without permission.

## Maintenance and coverage

Use narrow submodules when a broad field guide no longer captures its internal variation. Add catalog metadata and cases for the new scope; do not make all users load it. Keep unsupported fields on the general-core fallback path. Report coverage by tested scope, genre, language, and task rather than “all disciplines supported at top-tier quality”.

For upstream-derived ideas, update `THIRD_PARTY_NOTICES.md` and retain required license notices. Original project content currently has no project-wide license; see `CONTRIBUTING.md` before redistribution or accepting external contributions.
