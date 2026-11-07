# Diagram Archetypes for Light Diagram Prompt

Choose the structure that explains the figure's claim. The labels below describe visual intent, not scientific disciplines. A paper may need a hybrid, but one archetype should dominate.

## Archetype picker

| Archetype | Use when the figure answers… | Typical layout | Preserve explicitly |
|---|---|---|---|
| **Framework / system overview** | What are the major parts and how do they cooperate? | Bounded zones, hub-and-spoke, layered stack, or deliberately asymmetric composition | Module ownership, boundaries, interfaces, message/data flow, the system's focal contribution |
| **Pipeline / process workflow** | What happens, and in what order? | Left-to-right, top-to-bottom, staged, or folded flow | Exact stage order, branches, merges, loops, inputs/outputs, process vs. data artifacts |
| **Model architecture** | How is the model internally organized? | Hierarchical layers, parallel branches, encoder/decoder, backbone + heads, or macro-to-micro inset | Tensor/feature flow, shared vs. separate weights, trainable/frozen status, skip/conditioning paths when supported |
| **Mechanism / causal pathway** | What causes, regulates, transports, transforms, or inhibits what? | Causal chain, spatial compartments, interacting entities, feedback, or before/after comparison | Entity identity, compartment, direction, activation/inhibition/modification semantics, uncertain or indirect links |
| **Experimental setup / apparatus** | What physical setup is used and how do samples/signals move? | Apparatus cutaway, central setup with callouts, or sample → instrument → readout | Only stated equipment and connections; distinguish sample, reagent, physical flow, signal, and analysis |
| **Conceptual / visual metaphor** | What abstraction makes the core idea intuitive? | One dominant metaphor with a small number of supporting annotations | Keep metaphor subordinate to literal scientific meaning; label the mapping and avoid metaphor-induced false claims |
| **Comparison / contrast** | How do conditions, methods, states, or paradigms differ? | Matched panels, side-by-side states, aligned rows, or a transformation | Same visual scale and categories; explicit differences; do not invent evidence or imply causal proof |
| **Taxonomy / landscape** | How are tasks, methods, components, or capability families organized? | Tree, nested sets, matrix, rings, or grouped map | Inclusion/exclusion rules, hierarchy level, overlap, and mutually exclusive vs. overlapping categories |
| **Graphical abstract / narrative summary** | What is the paper's main story from problem to contribution/implication? | One continuous visual narrative or a few linked scenes | One central claim, readable sequence, scientific restraint; omit secondary results unless provided |
| **Teaser / paradigm shift** | Why is the problem important and what changes with the proposed idea? | Contrast, central visual, split scene, or visual metaphor | Accurate comparison, no unsupported superiority claims, no fake metrics or results |
| **Multiscale / zoom-in** | How does a large-scale object relate to a smaller mechanism? | Context view with linked zoom inset(s) | Scale transition, correspondence, orientation, and which details are known vs. schematic |
| **Closed-loop interaction** | How do sensing, decisions, actions, and environment update each other? | Explicit loop with directionally distinct stages | Loop direction, timing/update point, observation/action distinction, and any separate training vs. inference paths |

## Selection rules

1. Write the figure's one-sentence claim. Choose the archetype that best answers it.
2. Use sequence only when order matters; use parallel panels when alternatives are compared; use spatial layout when location/compartment matters; use a loop only when feedback is real.
3. Do not force a single linear pipeline over branches, interaction graphs, taxonomies, or spatial mechanisms.
4. For a dense method, show the main path at overview level and use one or two insets for the contribution. Avoid turning the figure into a complete inventory of every implementation detail.
5. Preserve asymmetry when the method itself is asymmetric. Neat grids are not inherently clearer.
6. Keep quantitative plots out of the image-model prompt. If a real plot is part of a composite figure, specify a reserved placeholder or use the supplied plot as an immutable asset.
7. If two claims need different visual grammars (e.g. a causal mechanism plus a benchmark taxonomy), split into panels with a clear shared message or recommend separate figures.

## Community and visual treatment are separate

For computer science and AI work, identify both:

- **Content community:** determines familiar information organization and domain objects. Examples include NeurIPS/ICML/ICLR for ML, CVPR/ICCV/ECCV for vision, ACL/EMNLP for NLP, ACM SIGMOD/VLDB/KDD/WWW for data/web, and USENIX/OSDI/SOSP for systems/security.
- **Visual treatment:** determines surface finish: strict paper figure, premium academic graphical abstract, technical presentation overview, minimal flat vector, or a user-specified reference treatment.

Do not let venue labels become a substitute for actual design decisions. For other disciplines, use the relevant field's conventions (e.g. cells/compartments for biology, crystal/interface and reaction representations for materials/chemistry, physical components and signals for engineering) only when the source supports those semantics.

## Mixed data and schematic figures

This skill is for the non-data portions. If the user asks for a diagram with plots, reported statistics, microscope images, or experimental photos:

- identify each factual asset as user-supplied, author-generated, or a clearly marked placeholder;
- never prompt a generative image model to invent or retouch evidence;
- keep plot axes, values, error bars, scale bars, and labels out of generated illustration unless the user supplies them as exact labels and the figure is explicitly schematic;
- explain that any placeholder needs replacement with the real asset before publication.
