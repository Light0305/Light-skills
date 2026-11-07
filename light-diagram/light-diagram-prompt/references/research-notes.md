# Research Notes for the Prompt Skill

This note records which local references informed the workflow and what was adopted. It is not a runtime prompt template and should not be pasted verbatim into a generated figure prompt.

## Cross-source synthesis

- **PaperBanana** separates retrieval, planning, styling, visualization, and critique. Adopted: plan before prompt prose; retrieve by visual intent and domain; evaluate faithfulness, readability, concision, and aesthetics separately; provide actionable revisions. Not adopted: a required hosted service/MCP dependency or chart generation path.
- **happy-figure-skill** separates discipline-specific visual language, figure-type constraints, language/model adaptation, and reference-style patches. Adopted: distinguish content community from visual treatment; adapt references without replacing domain science; whitelist visible text; don't leave unresolved schema placeholders. Avoided: hard-coded model capability claims and a default style-selection pause for every request.
- **CCF-Figure** classifies research intent and diagram structure before rendering instructions. Adopted: no universal left-input/center-model/right-output layout; single visual claim; type-specific structure; iteration should diagnose structural versus cosmetic issues.
- **BioRender mechanism skill** emphasizes actors, compartments, causal sequence, and accurate pathway direction. Adopted where relevant across domains: scientific relations before aesthetics, source-grounded labels, exact arrows. Its biomedical look is not generalized to other disciplines.
- **CVPR-Figure** emphasizes the claim, archetype, contribution, semantic colors, short labels, visual audit, and reviewer-risk checks. Adopted as conceptual quality guidance. Its deterministic spec renderer and format/export workflow are explicitly excluded here.
- **AutoFigure / AutoFigure-Edit** demonstrate critique/refine cycles and editable reconstruction. Adopted: image generation should be treated as an iterative draft with human verification. Excluded: their code execution, segmentation, SVG reconstruction, and tool-specific pipelines.
- **FigMirror** contributes a careful distinction between reference style and data semantics. Adopted: reference traits must be observable and must not change source truth. Excluded: its plot-specific visual analysis, matplotlib code, and quantitative review gates.
- **Awesome Research Figure Prompts** offers category-diverse examples. Adopted: use precise named objects and relationships instead of generic quality words. Avoided: treating prompt examples as verified scientific truth or combining incompatible styles.

## Visual lessons from the inspected paper figures

- Some strong figures organize the story through a multi-panel comparison rather than a single sequential flow.
- A large conceptual ring can work when its segments encode a real cyclical or categorical relationship; do not use radial layouts merely for novelty.
- Teaser figures may deliberately combine photos, diagrams, and data displays. The prompt must keep factual evidence distinct from generated schematic elements.
- Image-led compositions can foreground a real device, human interaction, or environment when those assets are central to the research claim; generic icons should not replace domain-specific evidence.
- Information density varies by venue and purpose. A proceedings Figure 1, a mechanism explanation, and a premium graphical abstract do not share one fixed label count, aspect ratio, or rendering style.

## Important disagreements resolved

- **One universal flat-vector style vs. style diversity:** use a clean, restrained default for scientific legibility, but select field-appropriate visual treatment from the source, reference, and user goal. Do not forbid all depth, texture, or illustration when these help encode real spatial structure.
- **Always use minimal labels vs. richly labeled prompts:** use controlled labels sufficient to express the workflow; do not force a universal count. Reduce labels when model text reliability or density is a problem, preserving technical meaning and reserving space for later annotation if exact typography matters.
- **Never use image models for figures vs. use generation as a first draft:** this skill's job is precisely to write image prompts, but it must not promise exact scientific reconstruction. Encourage human review and keep factual evidence/data out of generated image content.
- **Venue recipe as style vs. content and finish separated:** venue/community informs information organization; a separate visual-treatment choice governs surface aesthetics.
- **Reference example as template vs. reference as evidence:** inspect a small relevant set; transfer only reusable visual traits and never reuse its scientific content or signature assets.
