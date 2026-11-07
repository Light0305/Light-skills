# Verification record

Initial local checks: 2026-10-26. Updated: 2026-10-27 with a four-paper live image-generation pilot. Local helper tests and generated-image review are distinct validations. Host installation and an independent external LLM benchmark were not run.

## Generation routing update: 2026-11-02

The skill now delivers prompts first and optionally generates through native host tools or a configured OpenAI-compatible Image API. Prompt-only remains a supported result when explicitly requested or generation is unavailable. The historical pilot below predates this routing update.

41 local tests passed: the existing 16 document/search tests plus 25 generation-route/client tests. Client checks sent real HTTP requests only to a localhost mock service with a synthetic one-pixel fixture, covering base64 and URL outputs, exact Unicode prompt transmission, credential isolation, failed/queued/non-image responses, no automatic retry, publication declaration, version changes and existing-file protection. No external API key or new scientific image was used. Shared handoff regression checks and new synthetic status checks are recorded in [the routing evaluation](../evaluations/2026-11-02-generation-routing/REPORT.md).

## Live pilot: 2026-10-27

Separate from this historical pilot, the [2026-11-02 custom service test](../evaluations/2026-11-02-custom-service-test/REPORT.md) actually called the user's configured service. The first POST returned 403; a second verification after a diagnosed client compatibility fix produced one 1536×1024 image. This validates that service/model configuration and a simple six-label/five-arrow prompt only. The 29 targeted client tests passed after endpoint normalization and application User-Agent support; no complex scientific-figure benchmark is implied.

Four real papers, ten actual built-in image-generation calls (nine new generations and one image edit). Complete prompts, original outputs, sources, observed defects and residual limitations are recorded in evaluations/2026-10-27/REPORT.md and its case folders. The browser-readable index is evaluations/2026-10-27/index.html. CRISPR v3, perovskite v2 and acoustics v1 met the limited conceptual checks by assistant visual inspection; the detailed Transformer graph retains an extra/ambiguous residual route after editing and is not marked fully correct. This is a small iterative pilot, not a success-rate estimate. No exact backend model or random seed was returned.

## Passed checks

- 16 unittest cases: 5 document checks and 11 search-helper cases.
- Skill frontmatter name and description length; bundled file references; Markdown fences including nested response-format fences.
- Five complete cross-domain prompts and one style-patch example contain no unresolved placeholders. The five complete prompts embed exact visible-text lists.
- Main SKILL.md has no machine-specific absolute-path dependency or fixed corpus count.
- Search: metadata mapping across the gallery's `images/` prefix, preferred pattern matching, nonmatching query, absent metadata, empty corpus, result limit, single-image root, duplicate basenames with different source paths, UTF-8 paths with Chinese/spaces/apostrophes, malformed metadata, invalid input, and CLI help.
- Contact sheets: image output creation, existing-file protection, and no-Pillow fallback (`python -I -S`) that retains text results.
- Python compilation of the helper and both test files succeeded.
- Real-corpus integration: queried the nested local conference gallery using `robot` and preferred pattern `framework`, matched metadata for three candidates, returned source-paper links, and generated `reference-candidates/robot-framework-candidates.png`.

## Manual content checks

- Compared the five teaching inputs with their prompts: entity names, relation directions, compartment/layer placement, and allowed text. Corrected a missing direct query-to-context edge and an inconsistent electron-path statement during development.
- Teaching examples are explicitly hypothetical, not summaries of papers or validated domain mechanisms.
- Domain guidance covers CS/AI, biomedical, materials/chemistry/energy, physical engineering/apparatus, ecology/environment, and social/education/public-health research. It provides semantic safeguards, not universal journal rules.
- Actual figure observations are recorded separately from source metadata. Observations cover only the images opened during development; the full 3,658-image collection was not visually reviewed.

## Limits

- Search is filename/metadata text matching. `--pattern` is preferred in ordering; a topic match of another pattern can still appear. With a query and a pattern, either kind of positive match can qualify; inspect `match_reasons` and select relevant candidates manually.
- A contact sheet is a thumbnail review aid, not a semantic image index. Small text must be checked in original images. Corrupt image slots are marked unreadable; a produced sheet alone is not proof that all inputs decoded.
- Reference notes without verified paper metadata are identified by local filename only; filenames do not establish paper title or publication status.
- Document tests validate structure and selected safeguards, not the scientific truth of a user's future input or how faithfully an LLM follows the skill.
- Generated appearance, labels and scientific relationships were inspected in the limited live pilot above. Other fields, Chinese labels, other image providers, independent expert review and statistical repeatability remain untested by that pilot. It used a separate built-in image tool; it does not validate the newly configurable API client. The three downstream tool skills have their own native-application case reports.
- The folder is a skill source package. Host discovery/slash-command installation was not performed or verified.

## Repeat local tests

```bash
python -I -m unittest discover -s "D:/Light-Science/light-diagram/light-diagram-prompt/tests" -v
```
