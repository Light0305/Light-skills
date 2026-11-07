# Sources and distribution terms — Light Chart 0.11.0

The root MIT license covers Light-Science's own work. This package also contains
separately licensed components; their original attribution and license text remain
in force. It is not an all-MIT resource collection.

| Component | Attribution and terms |
| --- | --- |
| SciPilot figure skill | Haojae, 2026; supplied scipilot-figure-skill snapshot. MIT: `licenses/scipilot-MIT.txt`. Profiling, style, export, layout and checks were adapted for identifiers, pairs, physical sizes, fonts and package paths. |
| nature-figure | Supplied standalone snapshot, manifest 2.8.0; its README identifies the repository's own work as MIT. The declaration and terms are retained in `licenses/nature-figure-source-declaration.txt`; no separate LICENSE file was supplied. Numerical safety, plot templates, PDF/text and layout checks retain their origin. Nested figures4papers material keeps its separate terms. |
| nature-shared | Supplied `Yuan1z0825/nature-skills` family resources; Apache-2.0 text in `licenses/nature-skills-Apache-2.0.txt`. This family license is not used as a substitute for the separate standalone figure snapshot's terms. |
| figures4papers | Chen Liu and contributors, https://github.com/ChenLiu-1996/figures4papers. CC BY-NC 4.0: `licenses/figures4papers-CC-BY-NC-4.0.txt`, including derived nature assets, retained guides, source examples, reported arrays and corresponding previews. Adaptations make coordinates, missingness, sizes and input mappings explicit; they are not independent verification of the original papers. Commercial use is not granted by MIT. |
| Domain figure references | `assets/library/domain-layouts.json` and `references/domain-layouts/` record paper/figure identity, source URL, attribution, license evidence and interpretation limits. Only authorized previews are bundled. Other entries are link-only, including materials whose reproduction grant is not established and cases requiring separate permission. Link-only entries are not local images or callable analysis coverage. |
| Example datasets | Captions and source manifests identify R datasets, survival::lung, UCI, public omics and other inputs actually used. Original dataset terms and study limitations remain relevant; examples do not become new experiments. |

## Independently implemented review resources

`scripts/review_engine.py`, `scripts/raster_diagnostics.py`,
`scripts/generate_review_examples.py`, `references/visual-review/` and
`assets/examples/visual-review/` are authored for Light-Science and covered by MIT.
The ten analytical/generated examples include their inputs, generator and captions;
they are explicitly synthetic and make no experimental claims.

FigMirror (VILA-Lab, https://github.com/VILA-Lab/FigMirror) informed earlier
exploration of reference comparison and visual revision. No redistribution license
was established for its bundled snapshot. The public v2 distribution excludes its
two original scripts, nineteen original guides and ten source images. The new
tools and guides are independently authored implementations for this package;
preserved schema field names support existing Light Chart tasks. This is not a
relicensing of upstream files, a claim of upstream ownership, or a claim that the
FigMirror native orchestration runs here.

Four local R teaching scripts and twelve local article screenshots with unresolved
redistribution terms are also excluded. Their presence in development study notes
does not grant permission or make them part of the published library.

## Provenance and verification limits

`sources.json` preserves historical snapshot/adaptation records and adds the current
`public_distribution` scope. Historical hashes identify past development inputs;
they are not a current inventory or a certification that every recorded file is
shipped. Current runtime indexes point only to packaged resources or explicit
external links. Prior visual-view records describe the actual source viewed on the
recorded date, not a new desktop or scientific validation in this release.

New evidence, routing, composition, domain, source-binding and review integration
retain the relevant conceptual/source attribution in their headers and manifests.
An automated pass verifies only the documented checks. It cannot certify study
validity, hidden geometry, independent review or publication quality.
