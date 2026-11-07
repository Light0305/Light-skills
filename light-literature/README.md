# litsearch — literature discovery skill

A standalone, bilingual (Chinese/English) literature-search skill for research
directions. It turns a direction into a **reproducible search protocol**, a
deduplicated candidate set, a screening table, one round of citation expansion,
and an evidence-linked report.

It is designed for Claude Code / Codex-style agents that load a `SKILL.md`, but the
CLI works on its own.

**Keyless by default.** The default search uses OpenAlex, Crossref, Europe PMC,
and OpenAIRE and requires no registration. Keys are optional enhancements for heavy
use; Semantic Scholar is skipped unless a key is present.

Keyless startup is a bounded access option, not a promise of complete coverage.
OpenAlex pagination/authentication and service budgets change; record actual
limits, failures and truncation. See the dated [source notes](references/sources.md).

> **Phase boundary:** Phase 1 is retrieval, screening, citation analysis, and
> bilingual reports. Phase 2 builds per-paper `Literature/` folders with host-model
> transcription, translation, source maps and evidence-anchored notes.

For the full design rationale, script/agent boundary, and trade-offs, see
[ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quick start (offline demo)

```bash
python run_litsearch.py demo --out runs/demo --lang both
```

This creates synthetic records and a complete bilingual report. It proves the
report contract; it is **not** real literature.

Open:

- `runs/demo/report.en.md`
- `runs/demo/report.zh.md`
- `runs/demo/report.bilingual.md`
- `runs/demo/exports/references.bib`

---

## Install

Requirements: Python 3.11+, `requests`, `pypdfium2`, `Pillow`.

```bash
pip install -e .
litsearch --help
```

Host-model PDF reading uses `pypdfium2` for page
rendering and image extraction; it is installed automatically as a normal
dependency. `pypdfium2` is Apache-2.0/BSD-3-Clause-licensed, so it does not add
AGPL obligations to the MIT core.

Optional PyMuPDF fallback (AGPL-3.0/commercial; only needed if pypdfium2 fails
on a particular PDF or you prefer its extractor):

```bash
pip install -e ".[pdf]"
```

Without installation:

```bash
python run_litsearch.py --help
```

### Use as a Claude Code skill

Place this repository at `.claude/skills/literature-search/` (project) or
`~/.claude/skills/literature-search/` (user). Claude Code loads `SKILL.md` from
that directory.

When the skill runs from another project, either install it once:

```bash
pip install -e /path/to/light-literature
litsearch --help
```

or invoke the launcher with an absolute path:

```bash
python /path/to/light-literature/run_litsearch.py --help
```

All commands below use `python run_litsearch.py` for brevity; substitute the
installed `litsearch` command or an absolute path when needed.

---

## Live workflow

### 1. Create and edit a plan

```bash
python run_litsearch.py plan init \
  --direction "retrieval augmented generation for literature review" \
  --domain cs --lang both \
  --out runs/my-run/query_plan.json
```

Edit `query_plan.json`:

- 3–5 operationalized questions;
- 2–3 concept blocks with synonyms and abbreviations;
- 3 lenses (foundations/frontier, skeptic/method, practitioner);
- inclusion/exclusion criteria, years, languages, sources, budgets.

Validate:

```bash
python run_litsearch.py plan validate --plan runs/my-run/query_plan.json --strict
```

A filled example is in `references/query-plan.example.json`.

### 2. Search

```bash
python run_litsearch.py search \
  --plan runs/my-run/query_plan.json \
  --run runs/my-run \
  --sources europepmc,pubmed,arxiv,crossref \
  --max-per-source 80
```

Optional keyed sources:

```bash
python run_litsearch.py search ... --sources openalex,semantic_scholar --enable-optional
```

### 3. Screen

```bash
python run_litsearch.py screen prescreen --run runs/my-run
```

Edit `runs/my-run/screening.csv` or `.jsonl` using
`templates/prompts/screening_instructions.md`.

```bash
python run_litsearch.py screen validate --run runs/my-run
```

### 4. Expand citations

```bash
python run_litsearch.py citations expand \
  --run runs/my-run --seeds 10 \
  --sources europepmc,opencitations \
  --directions forward,backward
```

Target specific seeds:

```bash
python run_litsearch.py citations expand --run runs/my-run \
  --seed-paper-ids p_ab12cd34ef56,p_7890abcd1234
```

Then prescreen new records:

```bash
python run_litsearch.py screen prescreen --run runs/my-run
```

Optional co-citation / bridge analysis:

```bash
python run_litsearch.py citations analyze --run runs/my-run
```

This writes `citation_analysis.json` with co-cited references, bridge papers, and
seed-pair intersections.

### 5. Optional OA PDF links

```bash
python run_litsearch.py oa enrich --run runs/my-run --limit 20
```

Uses Unpaywall with `LITSEARCH_MAILTO` (or `UNPAYWALL_EMAIL`); no registration.
It fills `pdf_url`, `oa_status`, and `license` in `papers.jsonl`.

### 6. Optional OA PDF download

```bash
python run_litsearch.py pdf fetch --run runs/my-run --limit 20
```

Only downloads PDFs that are confirmed OA or hosted on a known-OA host (arXiv,
ACL Anthology, Europe PMC/PMC, MDPI, Frontiers, Research Square, Zenodo, HAL,
OpenReview, PMLR, CVF, JMLR). It verifies the `%PDF` magic bytes and writes:

- `runs/my-run/pdfs/<paper_id>.pdf`
- `runs/my-run/pdf_manifest.json` with `downloaded` / `already_present` /
  `blocked` / `not_pdf` / `unavailable` statuses.

It does **not** bypass paywalls or publisher bot protection. A DOI identifies a
paper, but it does not guarantee a downloadable PDF: MDPI may return 403, OUP may
return an HTML landing page, and closed papers have no legal automated copy.
If a PDF is unavailable, the manifest records the reason; the run continues.

### 7. Saturate and synthesize

```bash
python run_litsearch.py metrics saturation --run runs/my-run
```

Write `runs/my-run/synthesis.json` using
`templates/prompts/synthesis_instructions.md`. Every claim uses a token such as
`[[p_ab12cd34ef56]]`; unknown IDs are rejected.

### 8. Render and verify

```bash
python run_litsearch.py report --run runs/my-run --lang both
python run_litsearch.py verify --run runs/my-run
```

---

## Phase 2 — host-model reading

Import a local PDF or prepare papers from an existing screened run:

```bash
python run_litsearch.py literature add --pdf /path/paper.pdf --out /project/Literature
python run_litsearch.py literature build --run runs/my-run --out /project/Literature --status include --include-maybe
python run_litsearch.py literature verify --out /project/Literature
```

Optional metadata: `--title`, `--authors`, `--year`, `--doi` on `add`.
`--dry-run` previews selection and page counts without writing output or fetching
PDFs. `--force-prepare` refreshes assets/tasks while preserving completed text and
notes. Existing paper folders and all-paper indexes survive partial builds.

PDF bytes are recorded in `meta.json.pdf_sha256`. A different PDF for an existing
identity stops preparation before selected article files are updated; retain the
old source/reading artifacts and explicitly handle the version change.
`--force-prepare` does not bypass this protection. The read-only `literature
verify` command checks recorded source bytes, index coverage and file presence;
it does not certify reading or scientific correctness. See
[identity and integrity](references/identity-and-integrity.md) for legacy baselines,
same-DOI migration limits and exit codes.

The scripts copy PDFs, render page PNGs, extract embedded images and write
`MODEL_PARSE.md` / `AGENT_TASKS.md`; they do not call a model API. The **host
multimodal model** then completes transcription, translation and interpretation.
No parser-service key, quota, or route selection is needed.

```text
Literature/
├─ README.md / manifest.json
└─ <year>_<author>_<title>/
   ├─ paper.pdf
   ├─ pages/ / images/ / pdf_assets.json
   ├─ meta.json / MODEL_PARSE.md / AGENT_TASKS.md
   ├─ paper.md / source_map.json / model_parse_notes.md
   ├─ paper.zh.md / translation_notes.md
   ├─ reader.bilingual.md     # when requested
   └─ note.md                # optional English: note.en.md
```

The host follows [parse_pdf_model.md](templates/prompts/parse_pdf_model.md),
[translate_paper.md](templates/prompts/translate_paper.md) and
[paper_note.md](templates/prompts/paper_note.md). Stable paragraph/figure/table/
equation anchors support traceable translations and evidence matrices. Uncertain
formulas retain an original crop/page image. Deep notes explain the research
path, load-bearing designs, worked equations and evidence boundaries.

The [reading workflow](references/reading-workflow.md) applies ideas from
nature-reader, nature-paper-xray, nature-paper-card, nature-ref-verifier,
nature-academic-search and nature-downloader. Reference checking and external
acquisition are host workflows, not new automatic CLI services. For additional
lawful web materials use the optional [light-crawl handoff](references/light-crawl.md)
with the actual installed skill or checkout path.

Re-run the command after host-model work to refresh statuses. `already_present`
means source text exists; `model_parse_required` means the host must still read
it; `pdf_missing` means obtain the PDF first. Rendering failures/partial pages
are recorded separately in `assets_status`. File existence does not certify
completeness. Existing source text and notes remain usable; check their anchors
before downstream analysis.

### Working directly in Literature

Keep PDFs, source Markdown, translations, source maps and notes together in
`Literature/<paper>/`. Its `README.md` is the paper index; `manifest.json`
records the library and latest batch information. Read and edit the original files directly, keeping
relative image paths intact. Cross-paper synthesis can cite these reading
artifacts and the canonical records in `runs/`; no second library is required.

In 0.12.0, `manifest.json.entries` indexes the **whole library**;
`selected_paper_ids` and preparation counters describe the latest batch.
The command's returned `entries` still describes that batch. This preserves all
articles for downstream Idea intake after incremental imports.

## Sources

| Source | Key | Role |
|---|---|---|
| OpenAlex | optional for small requests; current pagination/budgets may require a key | broad all-discipline discovery + citation graph |
| Crossref | none (polite `mailto`) | broad metadata, DOI, references |
| Europe PMC | none | biomedical + citation expansion |
| OpenAIRE | none | all-discipline repository aggregator, OA supplement |
| PubMed | optional `NCBI_API_KEY` | biomedical recall, MeSH |
| arXiv | none | CS/physics/math preprints |
| OpenCitations | none | DOI-based forward/backward edges |
| DOAJ | none; **experimental** | OA articles; upstream access can fail |
| DBLP | none; **experimental** | CS venues; DBLP may serve an Anubis bot challenge |
| Unpaywall | email only, no registration | OA PDF links by DOI |
| Semantic Scholar | optional `S2_API_KEY`; skipped without key | citation contexts/intents |

**No key is required for the default sources.** The default keyless bundle is
`openalex, crossref, europepmc, openaire`; CS adds `arxiv`, biomed adds `pubmed`.
Semantic Scholar is skipped unless `S2_API_KEY` is set. DOAJ/DBLP are experimental:
they may fail on some networks and are recorded as degraded, never fatal.

Recommended setup: **none**. For heavy use, add a free `OPENALEX_API_KEY`; for
citation contexts, optionally add `S2_API_KEY`. `LITSEARCH_MAILTO` is a polite
identifier, not a secret; it also enables Unpaywall lookups. A project contact
placeholder (`litsearch@users.noreply.github.com`) is used when it is unset;
maintainers can replace it with a project alias.

Coverage roles: OpenAlex supplies broad cross-disciplinary records; OpenAIRE
aggregates repositories; Semantic Scholar supplies a scholarly graph and some
contexts; PubMed/Europe PMC specialize in biomedicine; arXiv supplies preprints;
Crossref supplies DOI metadata; OpenCitations supplies DOI-based citation edges.
Index size is not evidence of recall for a particular question.

**Bilingual output ≠ bilingual search.** Reports, screening tables, and synthesis
are bilingual, but the default sources are English-indexed. For a Chinese
direction, add English canonical terms to the concept blocks (or run
`plan init --direction-en ...`). Chinese-only queries return noise; CNKI/Wanfang
are not covered.

What this does **not** cover: CNKI/Wanfang, Web of Science/Scopus/Embase,
IEEE/ACM full text, books/monographs outside Crossref, standards/patents, most
grey literature, clinical trial registries, and non-English regional literatures.
Closed databases are simply **not covered**; the skill never asks the user to run
a manual search on another platform.

Two distinctions matter:

- **IEEE Xplore** is a publisher database. It has an official API with free
  metadata/abstract access after application, but paywalled full text needs
  institutional access. It is not in the current adapters; IEEE papers with DOIs
  are partially covered through OpenAlex/Crossref/Semantic Scholar.
- **CCF** is a recommended venue catalog (A/B/C), not a database. You cannot
  search "CCF"; you search DBLP/OpenAlex/Semantic Scholar and then filter or
  annotate by CCF rank. DBLP is the best free CS venue index, but its API is
  currently behind an Anubis bot challenge on some networks; the adapter records
  `blocked` rather than pretending it worked.

See [references/sources.md](references/sources.md) for the closed-platform matrix
and the keyless-first design.

Environment variables:

```text
LITSEARCH_MAILTO
NCBI_API_KEY
OPENALEX_API_KEY
S2_API_KEY
UNPAYWALL_EMAIL
LITSEARCH_CACHE_DIR
LITSEARCH_TIMEOUT_SECONDS
LITSEARCH_ALLOW_KEYLESS_OPTIONAL
```

The loader automatically reads `.env` from the repository root (or the path in
`LITSEARCH_ENV_FILE`), then falls back to the process environment. `.env` is
gitignored. Fill `OPENALEX_API_KEY` and `LITSEARCH_MAILTO`; Semantic Scholar is
optional and not in the default source set, so you can skip registering it.

Copy `.env.example` or `litsearch.toml.example` and fill only what you need.
Never commit keys.

---

## Output structure

```text
runs/<run>/
├─ query_plan.json
├─ compiled_queries.json
├─ search_log.json          # source runs + source health + coverage curve
├─ merge_log.json
├─ papers.jsonl
├─ screening.csv / screening.jsonl
├─ citation_edges.jsonl
├─ citation_analysis.json   # co-citation / bridges
├─ citation_seeds.json      # seeds used per expansion round
├─ saturation.json          # round yield + coverage/plateau
├─ prisma_s_audit.json      # 16-item PRISMA-S-informed audit
├─ synthesis.json
├─ oa_enrich.json           # Unpaywall enrichment summary
├─ pdf_manifest.json        # OA PDF download status
├─ pdfs/                    # downloaded PDFs
├─ report.en.md / report.zh.md / report.bilingual.md / report.md
└─ exports/
   ├─ papers.csv
   ├─ papers.json
   ├─ references.bib
   └─ screening.csv
```

---

## Design principles

1. **Scripts are deterministic; the agent reasons.** No LLM API key is required.
2. **Recall first, precision second.** Broad multi-source retrieval, then screening.
3. **Multiple signals, not citation count alone.** Relevance 35, recency 20,
   citation impact 15, source agreement 10, evidence depth 10, metadata 10.
4. **Every claim is traceable.** `papers.jsonl` is the only citation source.
5. **No completeness claims.** Coverage curve and plateau are heuristics; one
   citation round is `provisional: true`.
6. **Retrieval is audited.** Source capability matrix, persistent source health,
   coverage/rediscovery curve, BM25 + concept rerank, citation/recency strata,
   and a PRISMA-S-informed 16-item audit.
7. **Bilingual by contract.** Missing Chinese synthesis fails verification.

---

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

Offline tests cover normalization, dedupe and identity conflicts, query
compilation, screening, citation-edge remapping, PDF-version protection,
all-library indexing, read-only verification and actual Idea intake, as well as
demo rendering, scoring and exports. The latest [upgrade record](evaluations/2026-11-06-upgrade.md)
separates these from a small live Crossref check and pending host reading evaluations.

---

## Limitations

- PRISMA-informed, not PRISMA-compliant.
- Title/abstract screening only; no full-text quality appraisal.
- Citation expansion is bounded by seed/round budgets; not exhaustive.
- No CNKI/Wanfang/Web of Science/Scopus scraping. Closed databases are not
  covered; there is no manual-search handoff.
- Phase 2 requires a host multimodal model for transcription, translation and interpretation.
- API metadata can be incomplete; every record carries provenance and evidence
  depth.

---

## Repository layout

```text
SKILL.md                    agent entrypoint
ARCHITECTURE.md             design logic, boundaries, trade-offs
README.md                   this file
run_litsearch.py            zero-install launcher
src/litsearch/              package (CLI, adapters, pipeline, renderer, literature)
references/                 methodology, sources, note methods, query-plan example
templates/prompts/          plan/screening/synthesis/translation/note contracts
templates/paper-note-template.md
tests/                      offline tests
```

---

## License

MIT. See `LICENSE`.
