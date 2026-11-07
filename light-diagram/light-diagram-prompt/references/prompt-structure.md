# Prompt Structure and Figure Brief

Use this as an internal assembly guide, not as a rigid form that must appear verbatim in the final answer. A simple figure may need only the final prompt; a complex figure benefits from a Visual Schema first.

## Figure Brief fields

```text
Research domain / audience:
Figure job:
One-sentence visual claim:
Primary archetype:
Content community (if applicable):
Visual treatment:
Canvas orientation / ratio:
Reading order:
Regions and contents:
Connections and semantics:
Critical edges and internally distinguished repeated nodes:
Label leader targets and chain/junction continuity:
Focal contribution:
Visible text + language:
Required elements:
Optional elements:
Prohibited / unsupported elements:
Evidence assets vs. schematic illustration:
Uncertainties / assumptions:
Reference-derived visual traits:
```

Keep the brief concise. Every scientific element should trace to the provided source, an explicit user instruction, or a clearly marked convention that does not add a factual claim.

## Visual Schema for complex diagrams

```text
FIGURE PURPOSE
[What the reader should understand; one claim only.]

CANVAS AND READING ORDER
[Landscape/portrait/square and the reason; main reading direction.]

REGION A — [position and function]
- Visual objects: [specific entities, modules, or artifacts]
- Exact labels: [short labels or none]

REGION B — [position and function]
- Visual objects:
- Exact labels:

CONNECTIONS
1. [source] -> [target]: [meaning; solid/dashed/arrow/line grammar]
2. [source] -> [target]: [meaning]

HIERARCHY AND STYLE
[Focus, grouping, palette roles, line style, whitespace, background, typography.]

SCIENTIFIC BOUNDARIES
[What not to add, infer, exaggerate, or render as evidence.]
```

Do not include unresolved bracketed template text in the final prompt.

## Copy-ready prompt skeleton

Adapt and fully fill this in. Remove sections that do not apply; never leave angle-bracket placeholders in a delivered prompt.

```text
Create a [figure type] for [research context/audience]. The central point the reader should understand is: [one-sentence claim]. This is a scientific schematic, not a data plot or a marketing poster.

Canvas and composition: [orientation/aspect ratio if useful]. Arrange the figure as [chosen archetype and reading order]. Place [region/module A] at [relative location], containing [source-grounded objects]. Place [region/module B] at [relative location], containing [objects]. Make [contribution/focal object] visually primary; keep context elements subordinate. Use [whitespace/grouping/panel logic].

Connections: Draw [source] → [target] to mean [exact semantic relation]. Use [distinct line conventions] only when they encode [supported distinction]. Show [branches/merges/feedback/compartments] exactly as described. Do not imply an unsupported causal, temporal, or physical relationship.

Visual language: Use [discipline-appropriate rendering] with [background], [restrained semantic palette and what each color means], [consistent line weight/arrowheads], and [typography/label placement]. The style should be [observable traits]; avoid [specific mismatched treatments]. Keep scale and perspective consistent. Do not add decorative icons or visual effects that compete with the claim.

Visible text: The only text allowed in the image is the following exact text, in [language]: [complete label whitelist]. Do not render prompt section headings, an extra title, caption, legend, footnote, watermark, fake symbols, random text, or any unlisted label. Preserve capitalization, spelling, symbols, and technical terms exactly.

Scientific limits: Include only entities, relationships, values, and outcomes supported by the supplied content. Do not invent data, quantitative results, mechanisms, equipment, molecules, labels, or evidence images. [State which user-supplied real images/plots are immutable assets, if any.] Keep all unsupported details absent rather than guessing.
```

## Writing conventions

- Prefer exact nouns and verbs over adjective piles: “three parallel encoder streams merge at cross-attention” is more actionable than “a sophisticated, elegant architecture”.
- Describe geometry in relative terms: “upper-left context panel”, “two aligned parallel lanes”, “small linked inset”, “one dominant central object”.
- Give line style semantics. Do not use solid/dashed or color distinctions without defining the meaning.
- Use a small semantic palette. One color should consistently represent one concept; neutral gray can carry context. Never encode a critical distinction by color alone.
- Specify the physical endpoint of a label leader independently of scientific arrows. For repeated modules, distinguish source/target internally; for chains, specify independent strands versus covalent continuity; for repeat brackets, name included and excluded stages.
- Specify visual forms that carry meaning only when supported (e.g., tensor grids for feature maps, membrane boundaries for cell compartments, apparatus silhouettes for named equipment).
- Set the aspect ratio from the composition; do not assume every paper figure should be 16:9.
- Keep labels concise but not vague. Preserve proper nouns and technical labels verbatim; do not paraphrase terms in a way that changes their scientific meaning.
- If the model is unreliable at text, offer an alternate minimal-label prompt or request blank label spaces for later annotation; do not silently remove information essential to the claim.
