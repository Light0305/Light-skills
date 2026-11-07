# Prompt Quality Check

Before returning a prompt, check each applicable item.

## Scientific fidelity

- [ ] The figure's main claim is singular, specific, and supported by the source.
- [ ] The chosen archetype represents the real logic rather than a generic default.
- [ ] Module names, entities, stages, conditions, and terminology are preserved accurately.
- [ ] Arrow endpoints, directions, branch/merge behavior, polarity, compartments, and loop semantics are explicit where they matter.
- [ ] Repeated nodes can be distinguished internally; every critical edge is traced to its actual source and target, with duplicate inputs, missing residuals, and dangling lines checked after revisions.
- [ ] For multilevel encoder–decoder figures, state labels identify a specific wire or output, not a nearby decorative feature plane. Check state count and direction separately. An apparently shared vertical bus must not mix independent levels; residual/gating bypasses name the exact post-merge source, and arrowheads at both ends are checked.
- [ ] Label leader endpoints touch the named object, not an adjacent RNA/DNA strand, additive, or boundary; chain continuity and repeat-bracket scope are correct.
- [ ] Every introduced visual object has a source-supported or explicitly non-factual illustrative role.
- [ ] Abstract molecular/additive symbols do not suggest unverified atomic structures; schematic counts and geometry do not imply measured amounts.
- [ ] No unprovided mechanism, parameter, metric, measurement, outcome, formula, sample, equipment, or causal claim was added.
- [ ] Any real data, photograph, microscopy, plot, scale bar, or result is identified as an author-supplied immutable asset or omitted.

## Structure and communication

- [ ] Multiple consequences are not arranged as a causal chain just to fit a row. Name a common cause and use branches when supported; for example, polysulfide shuttling can contribute to active-material loss and anode passivation, which does not establish that lithium loss causes passivation. A zoom callout must name and touch the same physical layer shown in the inset.
- [ ] Figure type, audience, reading order, and canvas proportions are explicit where useful.
- [ ] The layout is selected from content logic; it is not a mechanically applied left-to-right pipeline.
- [ ] Main contribution has a clear focal hierarchy; secondary context does not compete.
- [ ] Complexity is controlled by grouping, panels, whitespace, or an inset rather than by deleting a critical relationship.
- [ ] Comparisons use matched visual scales and consistent encoding.
- [ ] The prompt does not mix incompatible visual styles or contradictory layout instructions.

## Text and rendering

- [ ] A complete exact visible-text whitelist is embedded in the prompt, in the right language.
- [ ] Every label is necessary, concise, correctly spelled, and supported by the source.
- [ ] Prompt-internal headings are explicitly excluded from rendered text.
- [ ] No unintended title, caption, legend, footnote, axis, random glyphs, or watermark is requested.
- [ ] Any equations, subscripts, uncommon characters, and long labels are called out as high-risk for image-model rendering.
- [ ] If exact typography is essential, the prompt uses a minimal-label strategy and does not promise perfect text rendering.

## Style, reference use, and delivery

- [ ] Domain conventions and visual treatment are chosen independently where needed.
- [ ] Style instructions describe observable choices (layout, color roles, forms, line language, background, finish), not only aesthetic adjectives.
- [ ] Palette is restrained and semantic; information is not communicated by color alone.
- [ ] Reference-image observations are based on images actually inspected and separated from scientific content.
- [ ] The prompt learns reusable visual traits without copying another paper's scientific content, unique composition, logo, or watermark.
- [ ] There are no unresolved placeholders, internal notes, implementation-only fields, or contradictory negative prompts.
- [ ] The post-generation reminder names scientific structure, text, and data/evidence checks that apply to this figure.

## Common repair moves

- **Generic flowchart:** replace the template with the actual visual archetype; add domain-native entities and the distinctive relationship.
- **Overcrowded figure:** preserve the claim and key path; demote implementation details to a small inset or remove only content outside the requested claim.
- **Ambiguous arrows:** name source and target and define arrow meaning; separate data, control, feedback, and inhibition if all occur.
- **Bad labels:** reduce the whitelist, shorten without changing terminology, or reserve blank annotation areas for later editing.
- **Style drift:** remove conflicting style words; specify field-appropriate forms and a small semantic palette.
- **Fake evidence risk:** remove all generated numeric/empirical content and make the real asset's provenance explicit.
- **Reference over-copying:** retain only high-level traits such as reading path, whitespace, hierarchy, palette roles, and line grammar.
