# Reference Observations

These are observations from images that were actually opened during skill development. They are reusable visual cues only, not scientific templates. Several images combine schematic and quantitative content; those parts must remain separate in a prompt.

## User-curated examples

### `light-diagram-prompt/Some papers' diagram/Hu_EverMemOS_2026.jpg`

- **Observed structure:** a comparison narrative with a shared interaction-history band across the top and two vertically organized method columns below.
- **Transferable cues:** clear comparison symmetry; method-specific intermediate states; a central horizontal divider; response panels at the bottom; a restrained blue/teal/cream palette with color used for method identity.
- **Do not transfer:** conversation wording, memory names, user examples, exact panel geometry, or the medical-safety conclusion shown in the image.
- **Boundary:** good for comparison or method-contrast prompts, not a universal pipeline template.

### `light-diagram-prompt/Some papers' diagram/Liu_MolecularLLM_2024.jpg`

- **Observed structure:** a radial task overview around a central generation concept, with local task vignettes and a separate matrix-like task table below.
- **Transferable cues:** a ring is useful for a real task family or cyclical relationship; local vignettes can explain each sector; overview and detailed comparison can be separated into panels.
- **Do not transfer:** molecule names, model names, task numbers, color assignments, or the exact circular geometry.
- **Boundary:** the lower matrix includes categorical/quantitative content; use it only as an author-supplied or separately drawn panel if needed.

### `light-diagram-prompt/Some papers' diagram/Ji_ColonX_2025.jpg`

- **Observed structure:** a wide teaser combining a left-side data curation workflow, central evaluation panels, and a right-side reasoning/system narrative.
- **Transferable cues:** a wide multi-region story can combine process, evaluation, and application only when the figure has one clear overarching claim; soft clouds and panel separators guide reading order.
- **Do not transfer:** clinical task names, model names, radar/bar-chart values, icons, or reported performance claims.
- **Boundary:** includes real-looking charts and measurements; never ask an image model to invent those panels.

### `light-diagram-prompt/Some papers' diagram/Ze_TWIST2_2025.jpg`

- **Observed structure:** central human/device image with four surrounding photo-led application panels and a pale blue directional motif.
- **Transferable cues:** a central contribution can anchor a teaser; surrounding panels can represent distinct application modes; image-led evidence can be stronger than generic icons when real assets are supplied.
- **Do not transfer:** robot/user photographs, the product name, exact arrow motif, or claims about portability and data collection.
- **Boundary:** this is a photo-led teaser, not a default method architecture.

## Additional opened examples

### `light-diagram-prompt/Some papers' diagram/biorxiv-2020.05.01.062802.full__p8__fig3.thumb.webp`

- **Observed structure:** five matched panels (a–e), each pairing a network-like node diagram with small plots and a triangular summary chart; a legend explains node and edge encodings.
- **Transferable cues:** matched panels work for controlled comparisons; keep the same local geometry and panel roles; put a compact legend outside the repeated panels only when necessary.
- **Do not transfer:** kinase labels, edge meanings, chart values, panel titles, or colors.
- **Boundary:** data plots dominate part of every panel. Preserve real plots as separate author assets and generate only the structural schematic if requested.

### `light-diagram-prompt/Some papers' diagram/biorxiv-2025.12.09.693237.full__p3__fig1.thumb.webp`

- **Observed structure:** a concise left-to-right pipeline: two modality grids, a central alignment module with paired spatial shapes, then aligned outputs shown as connected colored forms.
- **Transferable cues:** explicit input modality separation; a single named central transformation; dashed correspondence links; compact explanatory annotation beneath the core method.
- **Do not transfer:** spatial-multiomics labels, tissue shape, color map, or method name.
- **Boundary:** the colored maps may be data-derived. Do not fabricate them; use a schematic placeholder or supplied image.

### `light-diagram-prompt/Some papers' diagram/ndss-2026-s141-paper__p6__fig7.webp`

- **Observed structure:** a wide engineering pipeline with dashed subsystem boundaries, data traces, a neural reconstruction block, training stages, a sensing input, and a reconstructed output.
- **Transferable cues:** dashed containers can mark system subsystems; separate training/inference stages; use large directional arrows between major regions and smaller labels inside modules.
- **Do not transfer:** GPU, DRAM, signal traces, victim-device imagery, section labels, or reconstruction claims.
- **Boundary:** includes waveform plots and device imagery; these require real assets or separate deterministic rendering.

## Provenance and limitations

- These files were opened locally for visual inspection during skill development; no claim is made that every image in the corpus was inspected.
- Metadata matching and gallery pattern tags can help find candidates but cannot establish visual similarity or scientific correctness.
- When presenting a reference to a user, include the local path and available paper/source metadata. Do not redistribute the image as a generated asset or remove attribution.
- If an image is unavailable in a later environment, omit its observation rather than reconstructing it from the filename.
