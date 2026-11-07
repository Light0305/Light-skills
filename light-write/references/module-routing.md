# Module routing and precedence

`light-write` separates reusable writing operations from context-specific guidance. Route only as far as the task needs; modules are additive lenses, not independent authorities.

## Routing sequence

1. **Task and scale:** choose draft, polish, or check; local passage, section, or whole manuscript.
2. **Domain and evidence form:** identify the intellectual domain and what counts as evidence in the supplied work. Use one or more field modules only when they materially improve the task.
3. **Article type:** select empirical, methods/technical, review/synthesis, theory/hypothesis, protocol, or a justified hybrid using `references/article-types.md`.
4. **Section:** load only the relevant section guide. For substantial empirical Results organization, load `references/results-allocation.md`.
5. **Venue:** resolve an exact journal/conference and article type before applying a venue module. Read official requirements only when the task involves compliance or exact limits.
6. **Integrity:** preserve the source, evidence boundary, and author decisions regardless of module.

The static module index is `modules/catalog.json`. Paths in it are relative to the skill root. Catalog entries describe available guidance and maturity; they are not a script or automatic classifier.

## Applicability and ambiguity

- Prefer the author's description over an inferred discipline label. Fields overlap: a clinical machine-learning study may need both clinical-health and computing guidance.
- Combine modules only when each addresses a real part of the paper. Do not concatenate complete checklists mechanically or let one module overwrite the other.
- A discipline name does not determine a study design, acceptable evidence, or causal interpretation. Use the actual methods and supplied reporting standard.
- If the exact venue is unknown, use general writing guidance. A publisher family, ranking category, or venue list is not a single style profile: for example, CCF rank is metadata, and IEEE covers many venues.
- If a user names an ambiguous acronym, ask what they mean before routing to a venue profile. Do not silently reinterpret names such as “AIII”.
- When no relevant domain module exists, say so only when it affects the requested judgment, then use the general core and ask for domain conventions or an expert source as appropriate. Do not pretend to have venue-specific expertise.

## Precedence and conflicts

1. Preserve scientific facts, evidence boundaries, ethics, and the author's explicit scope.
2. Respect applicable reporting standards and author-confirmed study decisions.
3. Apply verified, current official venue requirements to format and submission constraints.
4. Use reviewed domain/genre guidance for disciplinary argument and evidence conventions.
5. Use venue editorial patterns and general writing advice as optional style guidance.

These layers do not always conflict cleanly. Official format rules cannot justify changing a result or omitting a material limitation; domain conventions cannot override an explicitly documented method; general advice cannot be represented as official policy. If two requirements genuinely conflict, identify the conflict and request author direction or point to the venue's official clarification. Do not resolve the conflict by hiding evidence.

## Maturity and provenance

Before relying on a module's authority, check its `maturity` and `provenance` in the catalog and module file. A `draft` module is a starting hypothesis, not expert-validated guidance. Do not call an `evaluated` module validated unless its evaluation record identifies cases, configuration, reviewers, and limitations. Follow `standards/modules.md` for maturity definitions.
