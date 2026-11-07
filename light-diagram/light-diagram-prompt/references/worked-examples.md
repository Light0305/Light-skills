# Worked Examples

These are **hypothetical teaching inputs**, not claims about a published study. Each final prompt is complete and contains no fill-in placeholders. In a real request, replace all content with source-verified entities and relationships; never reuse the science below as if it came from the user's paper.

## 1. AI system framework — evidence-grounded answering

### Teaching input
A language model receives a user question, retrieves passages from a read-only document index, assembles the query and evidence into context, drafts an answer, and checks whether the cited passages support the answer. The system does not learn online and never writes back to the index.

### Design decision
A sequential system framework with a separate read-only store. The index-to-retriever edge and retriever-to-context edge have distinct, explicit directions. No generic robot icon or invented quality score.

### Final prompt

```text
Create a computer-science system framework diagram for a research paper. Its central message is that evidence is retrieved and checked before an answer is returned.

Use a landscape, left-to-right composition. Place User Query at the far left and connect it to Retriever. Place Document Index above Retriever as a separate read-only store. Draw one arrow from Document Index into Retriever to mean document lookup; then draw a separate arrow from Retriever to Evidence Passages, and connect those passages to Context Builder. Also draw a thin query connection from User Query to Context Builder. Context Builder combines the query and evidence and sends them to Language Model. Send the draft answer from Language Model to Citation Check, then return the checked result as Answer. Make the main answer path visually dominant and the index subordinate. Do not draw any arrow writing to Document Index.

Use a restrained CS paper-figure treatment: white background, fine dark outlines, pale neutral or cool-blue grouping fills, and one muted teal accent on Citation Check. Use consistent geometric module shapes, short readable labels, ample separation for unambiguous arrow endpoints, and no perspective effects. Avoid decorative robots, dashboard UI, glossy 3D, heavy shadows, and marketing-poster styling.

The only visible text allowed is: "User Query", "Retriever", "Document Index", "Evidence Passages", "Context Builder", "Language Model", "Citation Check", "Answer". Preserve the wording and capitalization exactly. Do not render a title, caption, legend, extra module, explanatory sentence, random symbols, or prompt-section headings.

Show only the stated components and relationships. Do not invent online learning, index write-back, extra agents, confidence scores, benchmark values, or internal model layers. This is a schematic, not a quantitative results figure.
```

## 2. Biomedical mechanism — compartment-aware signaling

### Teaching input
A hypothetical paper states that ligand L binds surface receptor R; R activates kinase K; K moves transcription factor T into the nucleus; T increases expression of gene G. Inhibitor I blocks K. These names and edges are deliberately fictional and are used only to demonstrate structure.

### Design decision
A spatial mechanism with extracellular, membrane, cytoplasm, and nucleus regions. Activation, movement, transcription, and inhibition use distinct line semantics. Keep the molecules schematic rather than implying known atomic structures.

### Final prompt

```text
Create a biomedical mechanism schematic explaining a fictional ligand-to-gene signaling pathway. Organize the cell vertically: Extracellular Space above the Plasma Membrane, Cytoplasm below it, and a clearly bounded Nucleus inside the cytoplasm. Keep ligand L outside the cell, receptor R embedded in the membrane, kinase K in the cytoplasm, and transcription factor T inside the nucleus after nuclear entry.

Show the stated sequence only: ligand L binds receptor R; R activates K; K enables T to enter the nucleus; T increases expression of gene G. Show inhibitor I with a blunt-ended inhibitory connector terminating at K. Use arrowheads for activation or movement, and the blunt end only for inhibition. Do not imply that I blocks receptor binding or gene transcription directly. Make the main signaling route visually primary and the inhibitor secondary.

Use an original, clean biomedical schematic style with coherent compartment boundaries, simple flat molecular symbols, restrained muted colors, consistent fine outlines, and short non-overlapping arrows. Use no photorealistic tissue, dramatic glow, commercial iconography, or atomically detailed protein shapes.

The only visible text allowed is: "Ligand L", "Receptor R", "Kinase K", "Transcription Factor T", "Gene G", "Inhibitor I", "Extracellular Space", "Plasma Membrane", "Cytoplasm", "Nucleus". Use this exact text only. Do not add a title, caption, legend, dose, experimental result, or any other label.

This is a fictional teaching schematic, not biomedical evidence. Add no molecules, compartments, causal links, doses, response measurements, or microscopy images beyond those explicitly specified here.
```

## 3. Materials / chemistry — layered interface transport

### Teaching input
A hypothetical device has three named layers: a top electrode, a solid electrolyte, and a bottom electrode. During operation, lithium ions pass through the solid electrolyte from the top electrode to the bottom electrode; electrons travel from the top electrode to the bottom electrode through an external circuit. No numerical material properties are provided.

### Design decision
A labeled cross-section, because layer order and transport path are the claim. Ion transport through the electrolyte is distinct from electron flow through the external circuit. Avoid atomic structure, voltage labels, or performance plots.

### Final prompt

```text
Create a materials-science cross-section schematic of a hypothetical three-layer electrochemical device. Show, from top to bottom, Top Electrode, Solid Electrolyte, and Bottom Electrode as three continuous, clearly separated layers. Preserve this exact order and make the electrolyte boundary visible.

Draw lithium-ion transport from Top Electrode through Solid Electrolyte toward Bottom Electrode using a set of small circles and a solid arrow labeled by its legend-free visible label "Li+ transport". Draw electron flow from Top Electrode to Bottom Electrode through a clearly external circuit path connecting the electrodes; do not route electrons through the solid electrolyte. Use a distinct line style and a separate label, "Electron flow", so the two transport processes cannot be confused. Keep paths and arrowheads physically unambiguous.

Use a clean engineering-oriented scientific schematic: white background, flat layer fills in muted gray-blue and sand tones, dark fine outlines, consistent line weights, and a simple cross-section without perspective distortion. Do not add crystal lattices, atomic bonds, defects, coatings, reaction products, or microstructures because none were specified.

The only visible text allowed is: "Top Electrode", "Solid Electrolyte", "Bottom Electrode", "Li+ transport", "Electron flow". Do not include a title, caption, legend, voltage, current, efficiency, scale bar, graph, or any other text.

This is a conceptual schematic, not a measured device image. Invent no material composition, numerical parameter, performance result, or unsupported transport mechanism.
```

## 4. Laboratory workflow — sample processing

### Teaching input
A hypothetical protocol has four ordered stages: collect samples, prepare samples, run an assay named Assay Q, and analyze the resulting measurements. The source does not specify equipment, times, reagent amounts, group allocation, or results.

### Design decision
A simple four-stage sequential workflow. Show samples as a generic labeled vessel only; don't invent instruments or numeric annotations.

### Final prompt

```text
Create a four-stage laboratory workflow schematic for a hypothetical study. Arrange these stages left to right in exactly this order: Sample Collection → Sample Preparation → Assay Q → Data Analysis. Show a generic sample vessel entering Sample Collection and a generic measurement record leaving Data Analysis; do not depict any specific instrument or reagent.

Give each stage a clearly separated but visually consistent panel. Use a white background, restrained scientific colors, simple flat line-art symbols, aligned stage centers, readable short labels, and solid arrows with clear endpoints. Keep the flow strictly linear: no branching control group, repeat cycle, or feedback loop.

The only visible text allowed is: "Sample Collection", "Sample Preparation", "Assay Q", "Data Analysis", "Sample", "Measurement Record". Do not render a title, caption, legend, protocol detail, equipment model, parameter, or other text.

Do not invent sample counts, treatment groups, reagent names or amounts, timings, instrument models, plots, measured values, or outcomes. This is a process schematic; any actual data or result image must be supplied by the author and must not be synthesized.
```

## 5. Ecology — reservoir and exchange concept

### Teaching input
A hypothetical conceptual figure describes carbon exchange between atmosphere, vegetation, and soil. Photosynthesis transfers carbon from atmosphere to vegetation; litterfall transfers carbon from vegetation to soil; soil respiration transfers carbon from soil to atmosphere. No flux magnitudes or measured rates are supplied.

### Design decision
A triangular conceptual cycle, not a map or quantitative flow diagram. Arrow width is constant because there are no supplied flux magnitudes. Use simple domain-appropriate symbols and no invented species or locations.

### Final prompt

```text
Create a conceptual ecology diagram of carbon exchange among three reservoirs: Atmosphere, Vegetation, and Soil. Arrange them as a balanced triangular cycle with Atmosphere at the top, Vegetation at the lower left, and Soil at the lower right. Show photosynthesis as carbon transfer from Atmosphere to Vegetation, litterfall from Vegetation to Soil, and soil respiration from Soil to Atmosphere. Label each arrow with its process name and make the direction explicit.

Use a clean field-guide-inspired scientific schematic: white background, simple recognizable atmosphere/plant/soil symbols, muted green and earth colors, consistent fine outlines, and enough spacing to keep all three arrows distinct. The drawing is conceptual rather than a geographic scene. Use the same arrow width for every process because no magnitude data are available.

The only visible text allowed is: "Atmosphere", "Vegetation", "Soil", "Photosynthesis", "Litterfall", "Soil respiration". Do not include a title, legend, location name, species, carbon amount, rate, scale, map, or additional label.

Do not invent flux values, land-cover classes, species, sampling sites, or measurement evidence. This is a conceptual cycle, not a quantitative carbon-budget figure.
```

## 6. Reference-style patch

If a reference is inspected and it shows two aligned comparison panels, a shared center, muted blue/orange accents, and rounded panel boundaries, the style patch could say:

```text
Use the inspected reference only for these transferable visual traits: two aligned comparison panels, one shared central focal object, muted blue/orange accent roles, and consistent rounded panel boundaries. Keep the target figure's scientific entities, labels, relationships, and evidence strictly tied to its own source. Do not copy the reference's subject, wording, data, logo, watermark, unique assets, or exact distinctive composition.
```

Describe only visible traits; do not claim a trait you did not inspect. If no image was inspected, do not use a style patch.

## 7. Boundary examples

- **Abstract only:** produce a high-level conceptual prompt if the claim is clear; do not infer internal modules. State that a detailed method diagram needs method details.
- **Mixed schematic plus plot:** prompt only the schematic; identify the plot as a real author-supplied asset or an empty reserved space. Never synthesize values, axes, significance, or error bars.
- **Image supplied but unreadable:** do not claim visual observations. Ask for a description or continue from text alone and note the limitation.
- **User asks for exact lettering:** include the required visible-text whitelist, but explain that image models may still misspell it. Offer a minimal-label composition with blank annotation spaces; do not claim guaranteed exact typography.
- **User requests prompt only:** return just the complete copy-ready prompt, without an explanation or postscript.
