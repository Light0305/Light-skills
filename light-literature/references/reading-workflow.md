# Source-grounded reading and verification

These are workflow adaptations, not bundled copies or mandatory dependencies of
the upstream skills. Consult an installed skill's own `SKILL.md` when actually
invoking it. Keep the user's requested depth: an excerpt question does not require
a full reader, a complete card, or an external novelty search.

For source versions, all-library indexing and the bounded read-only
`literature verify` command, see [identity and integrity](identity-and-integrity.md).
This command complements the host reference-checking workflow below; it does not
automatically validate bibliographic fields or claim support.

## Reference map

| Reference | Applied here |
|---|---|
| [nature-reader](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-reader/README.md) | Stable source IDs, aligned translation, figures near discussion, uncertain formula images; `parse_pdf_model.md` and `translate_paper.md` |
| [nature-paper-xray](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-paper-xray/README.md) | Problem → working bet → design → evidence; load-bearing components and worked equations; `paper_note.md` |
| [nature-paper-card](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-paper-card/README.md) | Evidence inventory, claim-evidence matrix, grounding modes, claim boundaries and testable ideas; existing note template retained |
| [nature-ref-verifier](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-ref-verifier/README.md) | Field-level reference verification with evidence URLs and unresolved conflicts |
| [nature-academic-search](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-academic-search/README.md) | Discovery versus verification, controlled terms and explicit citation-count provenance |
| [nature-downloader](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-downloader/README.md) | Lawful acquisition routes, honest access status and supplemental-material coverage |

The upstream interfaces may change; verify the installed entrypoint before
calling its scripts. This project does not automatically invoke those scripts or
promise their complete citation-audit, institution-access or reference-manager features.

## Acquire only the missing source

1. Reuse a user-supplied PDF or an existing local file.
2. Prefer the current metadata APIs and `oa enrich` / `pdf fetch` for lawful OA
   copies; a DOI resolver or publisher landing page is not itself full text.
3. If an authorized publisher API or institutional route is available, use the
   appropriate downloader skill. Follow that tool's actual input contract. Record
   the access route and failure; do not invent a successful PDF download.
4. For public publisher pages, legal repositories, supplementary files or code
   pages needing reproducible extraction, follow [light-crawl.md](light-crawl.md).
5. Record whether supplements were supplied, obtained, absent or inaccessible.
   Request/download them when relevant to the task; do not claim to have read them
   from a mention in the main article. Never bypass access controls.

The built-in PDF downloader remains OA-only. External tools extend acquisition
only when available and authorized; they do not silently expand source coverage.

## Read with traceable locators

Use the original PDF as the visual authority, not extracted image objects alone.
Page images cover vector content and layouts; embedded images can be fragments.
Audit section order, captions, equations, tables, references and all pages.

`source_map.json` records paragraph (`P...`), figure (`F...`), table (`T...`) and
equation (`E...`) IDs matching anchors in the Markdown. Translation and optional
bilingual readers retain those IDs. PDF pages are 1-based file indices; printed
page numbers may differ. Keep unknown pages null, with structural locators.

Grounding modes describe evidence, not quality scores:

- `page-grounded`: actual PDF pages were inspected and mapped.
- `structure-grounded`: reliable sections/blocks but no trustworthy PDF pages.
- `source-limited`: only an abstract, excerpts or incomplete content is available.

Existing transcriptions can be reused regardless of their original parser. When
anchors are absent, add verified locators or explicitly use a weaker grounding
mode. Preserve completed notes and never manufacture page IDs to appear complete.

## Explain and make a durable note

Build an evidence inventory before prose. For each important claim record the
experiment/figure/table, source ID, conditions and limitation. Reconstruct the
method's inputs, outputs, assumptions and choices. Separate an actually measured
ablation from an analyst's counterfactual explanation. In numerical teaching
examples, distinguish illustrative inputs from reported measurements.

Keep the existing note template (sections 0–16); it is a local format, not a claim
of compatibility with the upstream card validator. Adapt method details to study
type. For missing results write “材料不足，无法判断”. Keep external facts, author
claims, analyst reasoning and new hypotheses distinguishable. New research ideas
need prior art, a specific delta and an experiment capable of refuting them.

## Verify references when requested or when a claim depends on them

Discovery records are candidates, not automatically verified references. Use DOI
registration records, PubMed or a publisher page for authoritative fields, and
cross-check independent sources for disputed fields. Repeated mirrors of the same
record do not count as independent verification. Check title, author order, year,
venue, volume, issue, pages/article number, DOI and publication status.

Record results in `reference_checks.json` or a Markdown table:

| Field | Meaning |
|---|---|
| `reference_id` | Local bibliography ID or paper ID |
| `field` | Metadata field being checked |
| `original` / `observed` | Supplied value versus source value |
| `source_url` / `checked_at` | Evidence URL and actual check time |
| `status` | confirmed, conflict, corrected suggestion, unverified |
| `reason` | Discrepancy, online/print-year distinction or access limitation |

Do not infer a publication year from a DOI suffix or overwrite an online/print
year conflict without explanation. Propose patches without silently changing a
user's external reference library. An inaccessible source remains unverified.
This is a host-model workflow, not a new automatic verification CLI.

For citation metrics, record source, retrieval date and counting rule. Citation
counts alone establish neither a citation edge nor strict non-self-citation.
Author/institution exclusions require actual identity evidence; unknown authors
remain uncertain. Use domain-specific controlled vocabulary (e.g. MeSH) where it
helps retrieval; never imply that an unqueried database was searched.
