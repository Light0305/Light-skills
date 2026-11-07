# Changelog

## 0.12.0 — 2026-11-06

- Reorganize the skill entry by request depth: targeted discovery, evidence maps,
  reading, reference checking and resume; retain detailed search instructions in
  `references/search-workflow.md` and add Memory / Leader handoff guidance.
- Keep distinct DOI reports separate, prevent DOI-less bridges, retain known
  aliases and disambiguate colliding fallback IDs. Log possible duplicates for review.
- Normalize incremental citation identities, index learned identifiers and remap
  both edge endpoints across provider aliases; count raw intake versus unique additions.
- Fix Crossref single-work requests: `select` is only sent to collection search.
- Keep every article in the saved library manifest after partial imports. Record
  PDF hashes and stop conflicting replacements before preparing selected articles;
  do not infer publication year from PDF creation time.
- Add read-only `literature verify` for source bytes, index coverage and artifact
  presence, with explicit limits on scientific and reading-quality claims.
- Preserve short/missing-abstract candidates for review and make screening scores
  advisory rather than a universal eligibility threshold.
- Add defect-driven regressions and an actual native Idea intake check; document
  current source access and the precise validation scope in the upgrade record.

## 0.11.0 — 2026-11-02

Literature is the single working collection.

- Removed Obsidian export, vault discovery, CLI/URI launch, related environment
  examples, integration documentation and tests.
- Updated the CLI, skill, architecture and bilingual guides to use the original
  Literature files directly for reading, revision and later synthesis.
- `litsearch obsidian export/doctor` are no longer available. Existing Literature
  assets and files previously exported to external vaults are left in place.

## 0.10.0 — 2026-11-01

Host-model reading is the sole PDF transcription workflow.

- Removed Doc2X API/CLI, keys, quota branches, related flags and route-selection prompts.
- `literature add/build` prepare PDF assets and host-model tasks by default;
  neutral `parse_*` metadata replaces parser-specific fields on rebuilt entries.
- `--dry-run` previews without output writes/downloads; `--force-prepare` refreshes
  assets while preserving model-authored text, translations and notes.
- Stable folders and complete indexes survive repeated imports and partial builds.
- Reader prompts add source block IDs, aligned bilingual output on request and
  original images for uncertain equations; notes reconstruct research paths and
  evidence boundaries. Reference/acquisition guidance maps all six nature-skills.
- Documented optional local light-crawl invocation and evidence-file handoff.
- Existing reading artifacts and archived service logs are retained. Old
  `--doc2x-*`, `--no-doc2x`, `--quota-fallback` and `--max-pages` flags are removed;
  use the default command and `--force-prepare` for asset refresh.

## 0.9.0 — 2026-10-22

Obsidian export.

- `litsearch obsidian export`: writes `<vault>/<project>/Literature/<paper>/`
  with `paper.pdf`, `translation.md`, `note.md`, and `assets/` for figures.
- Adds YAML frontmatter, Obsidian-friendly link blocks, a `Literature.md` index,
  and `obsidian_export.json`.
- Vault detection from `--vault`, `OBSIDIAN_VAULT_PATH`, or the nearest vault
  from the current directory; `--project` defaults to the Literature parent.
- `--open` prefers the official `obsidian` CLI, then falls back to
  `obsidian://open?...`; `litsearch obsidian doctor` reports vaults and CLI
  status. If the CLI is missing, the hint points to Settings → About → Advanced
  → Command line interface.
- Direct filesystem export needs no plugin or MCP; `references/obsidian.md`
  documents optional Local REST API and filesystem MCP servers.
- `--dry-run`, `--overwrite`, and `--open` (obsidian:// URI).
- CLI reconfigures stdout/stderr to UTF-8 so Chinese vault paths print on Windows.
- `ARCHITECTURE.md` documents the full design logic, script/agent boundary, and
  trade-offs.
- 53 offline tests.

## 0.8.0 — 2026-10-22

Default PDF renderer switched to pypdfium2; PyMuPDF is an optional fallback.

- `pypdfium2` and `Pillow` are normal dependencies, so `pip install -e .`
  installs the B-route renderer automatically; no AGPL install prompt.
- pypdfium2 extracts image objects nested in Form XObjects, often returning a
  complete figure instead of PyMuPDF fragments; images dedupe by content hash.
- `pdf_assets.json` records `renderer`; `doctor` reports all available renderers.
- PyMuPDF remains optional (`.[pdf]`) for PDFs pypdfium2 cannot render.
- 45 offline tests.

## 0.7.0 — 2026-10-22

User PDF import + model-based PDF parsing fallback.

- `literature add --pdf ...`: import a user-supplied PDF, create the paper
  folder, copy the PDF, and run the Phase 2 parse path.
- `--doc2x-mode model`: host multimodal model parses the PDF into `paper.md`;
  pages are rendered to `pages/*.png`, embedded images to `images/*`, with
  `pdf_assets.json` and `MODEL_PARSE.md`.
- No-key A/B guidance in `DOC2X.md`: A = Doc2X API (key URL, ~¥0.02/page),
  B = current multimodal model (quality/token caveats).
- Mid-parse quota exhaustion: `--quota-fallback stop|model`; statuses
  `quota_exhausted` / `model_parse_required`.
- `--doc2x-mode model` also works for batch builds; already-parsed papers are
  skipped unless `--force-doc2x`.
- 42 offline tests.

## 0.6.0 — 2026-10-22

Phase 2: Literature folders + Doc2X API (CLI optional) + note contracts.

- `litsearch literature build`: creates `Literature/<year_author_title>/` per
  included paper, copies `paper.pdf`, runs Doc2X, writes `meta.json`,
  `AGENT_TASKS.md`, `DOC2X.md` on failure, and `Literature/README.md` index.
- Doc2X API v2 adapter: preupload → PUT → status → export → result → download;
  Bearer key only on API calls, never on signed URLs.
- Quota guard: local page estimate, `--max-pages` (default 20), `--dry-run`;
  `api_key_required` / `quota_budget` statuses.
- Doc2X CLI wrapper remains optional (`--doc2x-mode cli`).
- Phase 2 note contract: 16-section evidence-anchored template, figure/table
  anchoring, contribution→evidence matrix, critical layer, idea cards,
  reproduction checklist.
- Translation contract: full-text `paper.zh.md` by the host model, not Doc2X.
- Note-method research: nature-paper-card/xray, v0lka template, Rice template,
  KaleabTessera, dialectical notes, Keshav/Zettelkasten.
- 39 offline tests.

## 0.5.0 — 2026-10-22

Citation-graph retrieval and multi-round saturation.

- Multi-round citation expansion: per-round `round` provenance, `citation_seeds.json`,
  fresh-seed preference, per-round saturation table.
- `citations analyze`: co-cited references, bridge papers, and seed-pair intersections
  from existing edges; writes `citation_analysis.json`.
- Report: citation graph section, per-round saturation, source health, coverage,
  PRISMA-S audit.
- 35 offline tests.

## 0.4.0 — 2026-10-22

Retrieval audit and ranking improvements.

- Source capability matrix (`sources --json`, `doctor`, report).
- Persistent provider-health scores (EWMA) used to weight source agreement.
- Coverage curve / rediscovery / plateau heuristic in `search_log.json` and
  `saturation.json`.
- PRISMA-S-informed 16-item audit (`prisma_s_audit.json`), with performed /
  implicit / skipped / pending statuses.
- BM25 rerank blended with concept coverage (relevance = 0.6 lexical + 0.4 BM25).
- Citation/recency strata and stratified top-N selection.
- Report sections: coverage curve, strata, source health, PRISMA-S audit.
- `search` reports `partial` and `degraded_sources`.
- 34 offline tests.

## 0.3.0 — 2026-10-22

OA PDF acquisition and bilingual query guardrails.

- Added `litsearch pdf fetch`: verified OA-only PDF downloads with `%PDF` checks,
  per-file/total time caps, and `pdf_manifest.json`.
- Added `pdf_path`, `pdf_status`, `pdf_source`, `pdf_sha256` to Paper; CSV/BibTeX
  exports include local PDF paths.
- Unpaywall enrichment now returns multiple `pdf_urls`, preferring repository
  copies over publisher PDFs.
- Added `plan init --direction-en` and Chinese-only concept-block warnings; strict
  validation rejects Chinese-only required blocks.
- 30 offline tests.

## 0.2.0 — 2026-10-22

Keyless-first refactor.

- Added OpenAIRE Graph adapter (keyless, all-discipline supplement).
- Added experimental DOAJ and DBLP adapters with explicit `error`/`blocked` status.
- Added Unpaywall OA enrichment (`litsearch oa enrich`; email only).
- Default project contact for Unpaywall/polite pools; no user setup.
- Semantic Scholar is skipped unless `S2_API_KEY` is set; no keyless 429 noise.
- Domain source bundles: general/biomed/CS/social, keyless by default.
- `litsearch doctor`, `litsearch sources`, and per-source query caps.
- Per-source request caps for OpenAIRE (2/run), OpenAlex (6/run), DOAJ/DBLP.
- HTTP client supports per-request timeout/retry overrides for fragile sources.
- Optional `oa_status`/`license` fields and CSV export.
- Manual strategy export is explicitly out of scope; closed databases are not
  covered rather than handed to the user.
- 26 offline tests.

## 0.1.0 — 2026-10-22

First runnable MVP.

- Standalone package and `run_litsearch.py` launcher.
- Query plan skeleton, strict validation, and per-source query compilation.
- Adapters: Europe PMC, PubMed, arXiv, Crossref, OpenCitations, OpenAlex,
  Semantic Scholar.
- Conservative dedupe with merge log; transparent discovery score.
- Rule prescreen and screening validation.
- Backward/forward citation expansion with provider provenance.
- Provisional saturation record.
- Bilingual Markdown report, citation-token resolution, PRISMA-style counts.
- CSV/JSON/BibTeX exports.
- Offline synthetic demo and 22 offline tests.
- Methodology and agent prompt templates.
