---
name: light-diagram-prompt
description: >-
  Turn research papers, methods, mechanisms, systems, experiments, and user
  concepts into rigorous, copy-ready prompts for AI image generation of
  non-data scientific diagrams. Use for method/framework figures, model and
  system architectures, mechanism/pathway illustrations, research workflows,
  experimental setup schematics, graphical abstracts, conceptual diagrams,
  taxonomies, comparison narratives, and reference-guided scientific figures.
  Also use for 科研绘图提示词、论文方法图、机制图、机理图、技术路线图、
  实验流程图、装置示意图、网络结构图、图形摘要、参考图风格迁移。
  Deliver prompts first; optionally generate via host tools or configured APIs.
  Do not use for quantitative charts, plots, or for drawing/rebuilding the
  final editable figure in Illustrator, PowerPoint, or Visio.
metadata:
  version: "0.2.0"
---

# Light Diagram Prompt

## 项目目录与续作

需要落盘或继续已有项目时，先读 [项目目录约定](references/project-layout.md)，按其中的本阶段位置、版本与关联规则保存；用户指定路径和旧项目优先。包内资源相对本 skill，研究产物相对真实项目，二者不要混用。只做局部讨论时无需初始化目录。

Produce a scientifically faithful, visually intentional, copy-ready image-generation prompt for a **non-data scientific figure**. Always deliver the prompt before generation. Unless the user requests prompt-only, use an available host image tool, otherwise a user-configured image service; without either, deliver the prompt alone. Editable reconstruction belongs to the Illustrator, PowerPoint or Visio skills.

When invoked through the parent [light-diagram workflow](../SKILL.md), reuse its brief, source scope, label list and critical relationships. Use the same generation route and return actual prompt/image paths, hashes and review findings; the parent continues editing-tool selection. Do not generate twice across the handoff. Record revisions separately from executed prompts. Direct prompt-only requests end at the prompt; other direct requests may end at a reviewed generated image.

持续项目先读取有关 Memory，再回实际论文、设计、分析及采用的稿图版本核对。保留实际阅读范围和来源定位、FIG/修订身份、关键关系与证据边界；生成图只作视觉参考。将采用的提示词/图版本、图注需同步事项、未决问题和有来源的决定交回 Write/Review 与 Memory。直接请求无需创建整套交接。

## Scope gate

- **In scope:** method/framework diagrams, model/system architectures, mechanism and pathway figures, research/experimental workflows, apparatus schematics, conceptual diagrams, taxonomies, comparison narratives, graphical abstracts, and non-quantitative teasers.
- **Out of scope:** bar/line/scatter plots, heatmaps, ROC/PR curves, statistical panels, ablation plots, or any visualization whose main content is measured data. Route those to a data-visualization workflow. If an otherwise in-scope figure includes a real plot as one panel, preserve it as a provided/author-produced asset; never ask the image model to invent or redraw its data.
- Never imply that an image-generation model can guarantee exact scientific truth, exact text, or pixel-perfect reproduction. The deliverable is a strong visual draft prompt; authors must verify the result.

## Operating principles

1. **Science before style.** Preserve what the source says; do not invent entities, causal links, steps, equipment, formulas, parameter values, outcomes, or evidence. Mark unsupported details as unknown, omit them, or ask one focused question when they change the diagram materially.
2. **One figure, one visual claim.** Identify the single idea the figure should make easy to understand. If the content has multiple independent claims, recommend separating panels/figures rather than cramming everything together.
3. **Choose structure from the story.** Never default automatically to a left-input → center-model → right-output layout. Select a structure appropriate to the actual relationship: sequence, parallel streams, feedback loop, hierarchy, spatial mechanism, comparison, taxonomy, hub-and-spoke, or mixed panels.
4. **Separate content community from visual treatment.** The research field/venue determines information conventions and domain objects; the requested aesthetic determines finish. Do not apply biomedical conventions to a CS paper or a generic conference template to a discipline-specific mechanism.
5. **Ground visual choices in evidence.** Prefer relevant examples from the supplied reference images and the local paper-figure gallery; use prompt repositories as methods to learn from, not templates to paste wholesale. Do not copy another paper's scientific content, exact composition, distinctive assets, logos, or labels.
6. **Treat image models as image models.** Specify visible text exactly and keep it controlled, but warn internally that spelling, equations, and fine typography may still fail. When text must be exact, prepare a minimal-label image prompt and explicitly identify text needing later manual placement; do not promise perfect lettering.
7. **Keep data and illustration separate.** Never ask the model to fabricate quantitative evidence, measurement labels, plot scales, microscopy/photos, or study outcomes. Distinguish schematic illustration from real evidence assets.

## Workflow

### 1. Parse the request and source material

Use what the user supplied: paper text or files, abstract, methods, caption, protocol, research plan, existing figure, reference image(s), desired audience, output context, and target image model if named.

If files are supplied, read/extract the relevant parts using available file-reading tools. For long papers, prioritize the method/approach, figure caption, definitions of the key modules, and passages that establish their relationships. Do not silently base a detailed method figure on an abstract alone: state the limitation and either produce a high-level conceptual prompt or request methods details if those details determine the structure.

Extract a compact **Figure Brief**:

- research domain and intended audience/venue;
- figure job and one-sentence visual claim;
- figure type (primary and, if needed, secondary);
- canonical entities and terminology;
- process/causal/containment relationships, including edge direction and polarity;
- required, optional, and prohibited elements;
- evidence boundary (schematic vs. real data/assets);
- visible-label candidates and language;
- likely canvas orientation/aspect ratio and intended use;
- uncertainty that could change the figure.

Do not ask the user to fill in fields that can be safely inferred. Ask only when two plausible interpretations would produce materially different science or layout. Otherwise state a reasonable assumption and proceed.

### 2. Choose the visual structure

Select one primary archetype based on the visual claim, not merely paper topic. Consult `references/diagram-archetypes.md` when useful. Combine archetypes only when it makes the relationships clearer.

Read the relevant section of `references/domain-visual-language.md` for domain objects, relationship semantics, and failure modes. Use `references/worked-examples.md` for complete teaching examples; their invented study settings are not evidence for the user's paper.

For CS/ML, also choose a **content community** (e.g. NeurIPS/ICML/ICLR, CVPR/ICCV/ECCV, ACL/EMNLP, ACM systems/data, USENIX/OSDI/SOSP) separately from a **visual treatment** (strict paper figure, premium academic graphical abstract, technical presentation overview, minimal vector, or a user-specified treatment). For other fields, infer the field's actual publishing and diagram conventions rather than borrowing these examples.

When style is unspecified, choose and briefly state a suitable direction and deliver the prompt. Ask a concise preference question only if materially different readings would make the result unusable; do not introduce a mandatory approval pause. If the user asks for alternatives, supply 2–3 distinct directions or complete prompts.

### 3. Learn from references without copying

When a local corpus or user-provided reference figures are available, retrieve a small, relevant set based on **visual intent first, domain second**:

1. match figure archetype/pattern (framework, pipeline, architecture, conceptual, taxonomy, comparison, teaser);
2. then match research domain and visual vocabulary;
3. favor coherent, legible, publication-style examples; do not treat a gallery's score, venue, year, or inclusion as proof of scientific correctness or universal quality;
4. inspect roughly 3–6 examples, or fewer when the user supplied one clear style anchor;
5. extract reusable properties: reading path, panel rhythm, hierarchy, density, grouping, whitespace, palette roles, line/arrow language, use of real imagery, and annotation style;
6. keep content distinct. Reference images guide visual conventions only unless the user explicitly asks to reproduce their own figure.

Resolve bundled paths relative to this skill's directory, not the caller's working directory. The optional local corpus is `Some papers' diagram/`; see `references/reference-corpus.md` for discovery and CLI examples. `scripts/search_reference_figures.py` performs offline filename/metadata matching and can produce a contact sheet if Pillow is installed. It does not perform visual similarity search. Prefer curated metadata when available; inspect original images after candidate retrieval. Metadata coverage may differ from the image inventory. Missing corpus, metadata, or Pillow must not block prompt generation. No reference repository is a runtime dependency. Provide source paths/metadata for inspected examples and distinguish observations from interpretations.

If no usable visual reference is available, proceed from the discipline and archetype; do not pretend to have inspected references. If the user provides a reference image, analyze style and structure separately from its scientific content. Reuse its palette/layout cues only within the user's requested scope; do not copy proprietary logos, watermarks, or another paper's scientific claims.

### 4. Build a structural blueprint before prose

For complex figures (more than four regions, parallel streams, feedback, multi-level hierarchy, dense labels, or strict layout constraints), create an internal or user-visible **Visual Schema** before writing the rendering prompt. Keep it concise and concrete:

- canvas and reading direction;
- named regions/panels and their relative placement;
- objects/modules in each region, including salient visual form;
- all important connections, direction, branching/merging, and feedback;
- focus/contribution and supporting context;
- labels, symbols, and legend only when necessary;
- style, palette roles, line/arrow grammar, typography, whitespace;
- scientific exclusions and unsupported details.

For error-prone details, give each repeated module an internal identifier and list critical edges as source → target → meaning. These identifiers guide planning; do not render them unless whitelisted. Define label leaders separately from scientific arrows: name the exact object and boundary where each leader ends. For nucleic acids, polymers, circuits, and layered systems, specify continuity and junctions; nearby shapes or color changes do not establish connectivity. State the scope of repeat brackets so preprocessing is not accidentally repeated.

For simple figures, use the brief directly. Do not output empty schema scaffolding or unresolved placeholders.

### 5. Compose the image-generation prompt

Use `references/prompt-structure.md` and `references/prompt-quality-check.md` as needed. The final prompt must be self-contained and directly pasteable into an image-generation model. It should include, in a natural order:

- what figure to create and what the reader should understand;
- exact canvas orientation/aspect ratio when justified;
- layout and reading order;
- specific domain-appropriate objects, modules, panels and spatial relationships;
- explicit arrows/links and what their visual grammar means;
- restrained semantic palette, hierarchy, typography/line style, spacing and background;
- exact visible-text whitelist and language;
- hard scientific boundaries and a short negative-constraints list.

Do not overload the prompt with generic quality adjectives. Replace vague words such as "professional", "beautiful", "high-end" or "top-conference quality" with observable design instructions. Do not prescribe exact hex colors, pixel sizes, or typographic implementation unless the target model/workflow explicitly benefits from them; such details can be rendered literally as text. Use relative spatial language and natural color descriptions by default.

The visible-text whitelist is mandatory in the final prompt. Include only labels the source supports. Explicitly say that prompt-internal headings (e.g. "ZONE 1", "CONNECTIONS") are instructions, not figure text, unless individually whitelisted. Do not ask for a title, caption, footnote, legend, axis, or annotation unless it is explicitly required and listed.

### 6. Adapt to the requested image model lightly

If a specific image model is named, adapt only what is needed for its text rendering, reference-image handling, aspect ratio controls, and image-editing capabilities. Do not assert unsupported features or current model availability. If current model capability is important and not known, verify from the provider's official documentation when web access is available; otherwise phrase the prompt model-neutrally and state the limitation.

If the model is unspecified, produce a model-neutral prompt with explicit spatial structure, controlled labels, and clear scientific constraints. Do not block on model selection unless it changes the result substantially.

### 7. Audit before delivery

Run the checklist in `references/prompt-quality-check.md`. At minimum, verify:

- the selected structure answers the visual claim and matches the paper's logic;
- domain, diagram type, audience, and visual treatment are not conflated;
- all required entities and important relationships are preserved;
- no unsupported module, direction, mechanism, quantitative result, or factual visual is introduced;
- text is exact, short, language-consistent, and explicitly whitelisted;
- the prompt does not mix schematic illustration with fabricated data/evidence;
- no contradictory layout/style instructions or unfilled placeholders remain;
- risks and assumptions are stated briefly outside the copyable prompt.

### 8. Deliver the prompt, then generate when available

Read [image-generation.md](references/image-generation.md) for routing, configuration and the helper. Before **every** generation/edit call, show the complete executable prompt in a user-visible message, or save it and show a clickable file link; continue without a routine approval pause. A tool log alone does not meet this requirement.

Respect explicit prompt-only requests first. Otherwise discover actual host image tools and prefer them, following the host image skill/tool rules. If the host has none, use the user's configured service (`url`, `api_key_env` or `api_key`, `model`, optional parameters). An explicit custom-provider preference overrides the default. With neither capability nor complete configuration, deliver the full prompt and briefly state that no image was generated; configuration is optional. Unknown host capability requires discovery rather than an assumed fallback.

The bundled custom adapter supports synchronous OpenAI-compatible Image APIs only; it does not imply that arbitrary vendor endpoints support that protocol. Do not read keys aloud, put them in prompts, copy them into case records or print full configuration. Follow the host imagegen and any available imagegen-fallback instructions. A previously authorized fallback after tool unavailability or technical failure may use its existing adapter/configuration; do not require a second API-key setup. Never route a safety refusal through another provider. Preserve the failed attempt and actual call lineage; do not silently switch or retry without a bound. Record actual calls and output hashes, inspect the returned image, and apply the checks below before claiming it passed. When no image was produced, report prompt delivery only.

### 9. Revise from feedback or a generated image

If the user returns an image, inspect it before claiming to assess it. Compare it with the brief in this order: scientific entities/relationships, missing or wrong labels, topology/readability, then visual finish. Identify concrete locations and changes; preserve correct content and any user-approved style. Return a complete revised prompt, not a fragment that requires copying old prompts. For edit-capable models, separate what to preserve from what to change, and do not claim pixel-perfect preservation. With text-only feedback, revise the stated problem and say that no image was inspected. Stop when requested fixes are covered; do not force repeated generations or extra variants. Deliver each revised prompt before executing it. The custom adapter is text-to-image only; do not label a new generation as an edit or silently omit edit targets/reference images.

When a draft is mostly correct and an edit-capable generator is available, a self-contained edit prompt with an explicit target image, preserved elements, and localized corrections may retain topology better than another full generation. Recheck the entire critical edge list after any revision: a corrected port can coexist with a newly missing module or wrongly sourced arrow. Record unresolved problems rather than declaring success from visual polish. If revisions remain unstable, offer a scoped overview plus a separate detail panel without silently omitting required science. See `references/generated-image-review.md` for observed failure patterns and the real-paper pilot.

## Default response format

Answer in the user's language. For Chinese requests, explain in Chinese; the copyable prompt and figure labels should follow the paper/venue/output language, not automatically the conversation language.

````markdown
## 图意与结构
- **核心表达：** ...
- **图类型 / 布局：** ...
- **领域语境 / 视觉气质：** ...
- **图中文字：** ...
- **依据与假设：** ...

## 参考图观察
[Only if references were actually inspected: 3–6 concise transferable observations and source paths/metadata when available. Omit otherwise.]

## 最终生图提示词
```text
[One complete prompt ready to paste into the image-generation model.]
```

## 生成后核查
[Briefly call out the most important scientific/text/data checks.]
````

If the user explicitly says "只要 prompt" / "prompt only", output only the final copyable prompt. If the user asks for several directions, provide distinct prompts rather than blending incompatible styles. Do not output internal reasoning or a long tutorial.

When generation will follow, deliver the prompt or its file link before the call; the final response includes that prompt/link, the image, the provider route and actual review limitations. If generation is unavailable or fails, keep the prompt as the usable deliverable and state the reason briefly. Do not call an ungenerated image complete.

## Reference guide

- `references/image-generation.md` — prompt-first routing, optional custom service configuration and actual invocation.

- `references/diagram-archetypes.md` — selecting an information structure for non-data scientific figures.
- `references/prompt-structure.md` — reusable blueprint and copy-ready prompt scaffold.
- `references/prompt-quality-check.md` — scientific, visual, text, and image-model audit checklist.
- `references/reference-corpus.md` — optional local corpus, retrieval commands, and provenance notes.
- `references/domain-visual-language.md` — domain-specific object and relationship semantics.
- `references/worked-examples.md` — complete cross-domain teaching inputs and prompts.
- `references/reference-observations.md` — observations of images actually inspected, with limitations.
- `references/acceptance-cases.md` — behavioral acceptance scenarios; not an executed model benchmark.
- `references/research-notes.md` — source synthesis and design decisions; not required on every invocation.
