# Source playbook

Maintainer notes for the adapters. The default set can attempt bounded requests
without registration. This is an access strategy, not a guarantee of service,
budget or full recall. Semantic Scholar remains optional and skipped unless a
key is present.

## Access recheck — 2026-11-06

- [OpenAlex authentication](https://help.openalex.org/api/authentication/)
  currently permits small keyless use, with larger budgets and some pagination
  requiring a key. Handle actual responses, partial coverage and truncation;
  do not promise that a keyless full-field map will finish.
- [Crossref authentication](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication)
  supports public access and a polite contact route. Collection field selection
  must not be reused for `/works/{doi}`: an actual request with `select` returned
  400; the unselected request returned 200. The corrected adapter successfully
  retrieved metadata and two backward reference edges from one public DOI.
- The health table dated 2026-10-22 below is a historical observation from its
  test network, not current availability for every adapter. Legacy quota numbers
  below are historical context; use current documentation/response headers for a job.

This recheck did not query every provider or evaluate search recall. The
[upgrade record](../evaluations/2026-11-06-upgrade.md) distinguishes live calls,
offline regressions and pending host-model reading checks.

## Coverage and key matrix

| Source | Key needed? | Strong coverage | Weak / missing |
|---|---|---|---|
| OpenAlex | Optional for small use; current pagination/budgets may require it | All disciplines, authors, institutions, topics, citation graph | Abstract/metadata gaps; humanities and non-English records uneven; expansion records vary in quality |
| Semantic Scholar | Free key recommended | CS, neuroscience, biomedicine; citation contexts/intents; TLDR | English bias; humanities/law/economics partial; books/patents limited; contexts sparse |
| Europe PMC | No | Biomedicine, preprints, full text, citation links | Non-biomedical coverage weak |
| PubMed | Optional `NCBI_API_KEY` | Biomedicine, MeSH, clinical literature | Not general-purpose; no citation list endpoint |
| arXiv | No | CS, physics, math, quantitative biology | Preprints only; no citation data; 3 s request interval |
| Crossref | No; polite `mailto` recommended | DOI metadata, journals, books, datasets, references | Search relevance weaker; references may be incomplete; no forward citation endpoint |
| OpenCitations | No | Forward/backward DOI citation edges | Metadata-poor; coverage uneven; DOI-bearing works only |

**Keys are per provider, not per skill.** An OpenAlex key does not work for
Semantic Scholar, and vice versa. One key can be shared by multiple tools, but they
consume the same quota. Never commit a key.

The default keyless bundle is `openalex, crossref, europepmc, openaire`; CS adds
`arxiv`, biomed adds `pubmed`. No registration is required. Optional enhancements:

```text
LITSEARCH_MAILTO=you@example.com     # polite pool; also enables Unpaywall
OPENALEX_API_KEY=...                 # optional; better heavy-use budget
S2_API_KEY=...                       # optional; Semantic Scholar becomes available
NCBI_API_KEY=...                     # optional; use current NCBI limits
```

What this covers well: English-language STEM and biomedicine, plus broad metadata.
What it does **not** cover: CNKI/Wanfang, Web of Science/Scopus/Embase, IEEE/ACM
full text, books/monographs outside Crossref, standards/patents, most grey
literature, clinical trial registries, and non-English regional literatures.
Closed databases are not covered; the skill does not hand the user a manual
search task.

## Keyless-first stack

For an open-source skill, the default should require **zero registration**. Most
users do not need a key; keys are optional enhancements for heavy use.

| Source | Key | What it adds | Notes |
|---|---|---|---|
| OpenAlex | none (optional free key) | broad all-discipline discovery, authors, topics, citation graph | Keyless has a daily budget; normal personal use usually fits; heavy use benefits from a key |
| Crossref | none (`mailto` optional) | DOI metadata, journals, books, references | free |
| Europe PMC | none | biomedicine, preprints, full text links, citation edges | free |
| PubMed | none (optional NCBI key) | biomedical recall, MeSH | 3 req/s keyless |
| arXiv | none | CS/physics/math preprints | 3 s between requests |
| OpenAIRE | none | all-discipline repository aggregator, projects, OA links | anonymous ~60 req/hour; use as a supplement, not every query |
| DOAJ | none | ~9–10M open-access articles | no key; max 100/page; **experimental: 502/403 on some networks** |
| DBLP | none | ~6.5M CS publications, venues, authors | no abstracts/citations; **experimental: Anubis bot challenge on dblp.org** |
| OpenCitations | none | DOI-based citation edges | metadata-poor |
| OpenReview | none | ICLR/NeurIPS/ICML submissions/reviews | **experimental: challenge verification required on some networks** |
| Fatcat / Internet Archive Scholar | none | open full-text search index | query-only; respect copyright; **experimental: connection failures observed** |
| Unpaywall | email only, no registration | OA PDF locations by DOI | default project contact; override with `LITSEARCH_MAILTO` or `UNPAYWALL_EMAIL` |

### Observed source health (2026-10-22)

| Source | Status | Handling |
|---|---|---|
| OpenAlex | works; key helps heavy use | retry, fallback to other sources |
| OpenAIRE | works | cap 2 queries/run (anonymous ~60/hour) |
| Unpaywall | works | email-only; optional enrichment |
| Crossref / Europe PMC / PubMed / arXiv / OpenCitations | works | default / domain bundles |
| DOAJ | 502 / 403 from the test network | experimental; record `error`, continue |
| DBLP | Anubis challenge | experimental; record `blocked`, continue |
| OpenReview | challenge verification | not enabled; deferred |
| Fatcat | connection failure | experimental; deferred |
| Semantic Scholar | keyless 429 | skipped unless `S2_API_KEY` is set |
| IEEE / WoS / Scopus / CNKI / Wanfang | keyed/closed | not covered; no manual handoff |

Optional keyed sources (never required):

- **Semantic Scholar** — keyless is frequently 429; use only if a key is present.
- **IEEE Xplore** — free metadata key; full text needs institutional access.
- **CORE** — free key; OA aggregator.
- **NCBI** — free key; PubMed speed.
- **Web of Science / Scopus / CNKI / Wanfang** — closed; not covered, and no
  manual-search handoff.

### Why not ship a shared key or proxy?

A maintainer-hosted proxy with one shared key is tempting but usually a bad idea:

- API terms typically prohibit key sharing/resale; the key can be revoked.
- One key's quota is consumed by all users; a few heavy users can starve everyone.
- Abuse, cost, logging, and privacy become the maintainer's problem.
- The key must be rotated; downtime breaks every user at once.

A shared key is acceptable only if the provider explicitly grants a sponsored or
institutional key for the project, with a rate-limited proxy and a privacy policy.
That is a service, not a skill, and should not be the MVP.

### Discipline bundles

Use a small number of high-value sources per discipline; do not query every
source for every lens.

| Discipline | Primary keyless | Supplement |
|---|---|---|
| Biomedicine | PubMed, Europe PMC, OpenAlex, Crossref | DOAJ, OpenAIRE |
| CS / ML | arXiv, OpenAlex, Crossref, OpenAIRE | DBLP (experimental), OpenReview (experimental), Semantic Scholar (key) |
| Physics / math | arXiv, OpenAlex, Crossref | OpenAIRE, DOAJ |
| Social science / humanities | OpenAlex, Crossref, OpenAIRE | DOAJ, HAL, Zenodo |
| General / unknown | OpenAlex, Crossref, OpenAIRE | DOAJ, Europe PMC |

This keeps request budgets low and avoids hitting OpenAIRE's anonymous 60/hour
limit or OpenAlex's keyless daily budget.

## PDF acquisition

**A DOI identifies a paper; it does not guarantee a PDF.** The skill uses a
best-effort OA pipeline:

1. Prefer direct PDFs from arXiv, PMC/Europe PMC, ACL Anthology, and repository
   copies.
2. For DOI-bearing papers, query Unpaywall and try `oa_locations` with
   `url_for_pdf`, repository locations first.
3. Verify the response is actually a PDF (`%PDF` magic bytes or
   `Content-Type: application/pdf`), not an HTML landing page.
4. Download only confirmed OA or known-OA-host PDFs; record `blocked` (403),
   `not_pdf` (HTML), `unavailable` (no legal OA copy), and `already_present`.
5. Never bypass paywalls, logins, Cloudflare, or publisher bot protection.

What fails in practice:

- Publisher PDFs may return 403 even when the article is OA (MDPI was observed).
- Some DOI/OUP links return an HTML landing page, not a PDF.
- Some PDFs are slow/large; the per-file and total time caps stop the run.
- Closed papers have no legal automated copy; use institutional access or an
  author copy outside the skill.

`litsearch pdf fetch` writes `pdfs/<paper_id>.pdf` and `pdf_manifest.json`; this
manifest is the handoff for Phase 2 (host-model reading/translation).

## Closed platforms vs. ranking lists

These are often confused:

| Name | What it is | Can this skill search it? | Practical route |
|---|---|---|---|
| **IEEE Xplore** | Publisher database / index | Not currently | IEEE has an official API: free metadata/abstract access after application; paywalled full text needs institutional access. IEEE papers often have DOIs and appear in OpenAlex/Crossref/S2, but coverage is incomplete. |
| **CCF** | China Computer Federation's recommended venue catalog (A/B/C), not a database | No — there is nothing to "search" | Search papers through DBLP/OpenAlex/S2, then **filter/annotate by CCF rank** using a local CCF catalog JSON. DBLP is ideal when accessible; OpenAIRE/OpenAlex/Crossref are the keyless fallback. |
| **DBLP** | Free CS bibliography (~6.5M publications) | Adapter exists, but blocked on some networks | `https://dblp.org/search/publ/api?q=...&format=json`; no key; venue/author/year fields; no abstracts or citation counts. Current Anubis challenge means it is **experimental**, not default. |
| **OpenReview** | Free ML conference submission/review platform | Not enabled | Public API; challenge verification required on some networks; deferred. |
| **Web of Science / Scopus / Embase** | Subscription indexes | No | Not covered; institutional API keys only, no manual handoff. |
| **CNKI / Wanfang** | Chinese subscription indexes | No public API | Not covered; do not scrape. |
| **ACM DL / SpringerLink / ScienceDirect** | Publisher platforms | Metadata partially via Crossref/OpenAlex; full text no | DOI metadata is often present; full text needs subscription. |
| **Google Scholar** | Web search engine | No official API | Do not scrape; use OpenAlex/S2/Crossref instead. |

Recommended additions, in order:

1. **OpenAIRE** (done) — keyless all-discipline supplement.
2. **Unpaywall** (done) — email-only OA PDF links.
3. **CCF catalog filter** — vendor a public CCF A/B/C JSON (e.g. the 2026 catalog
   extraction) and annotate/filter by venue; do not treat CCF as a search index.
4. **DBLP via official XML data dump** — build a local venue index; do not bypass
   the Anubis challenge on the live API.
5. **OpenReview** — ICLR/NeurIPS/ICML accepted papers; currently challenge-gated.
6. **IEEE Xplore adapter** (optional, free metadata key) — engineering/optics.

Manual strategy export is intentionally out of scope: the skill should not ask the
user to run searches elsewhere.

## Endpoints and rates

| Source | Endpoint | Auth | Conservative rate | Citation expansion |
|---|---|---|---|---|
| Europe PMC | `https://www.ebi.ac.uk/europepmc/webservices/rest` | none | ~5 req/s | `/MED/{id}/citations`, `/references` |
| PubMed | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | optional `NCBI_API_KEY` | 3 req/s (10 with key) | none (use Europe PMC for PMIDs) |
| arXiv | `https://export.arxiv.org/api/query` | none | 1 req / 3 s | none |
| Crossref | `https://api.crossref.org/works` | polite `mailto` | ~1 req/s | `reference` array (backward only) |
| OpenCitations | `https://api.opencitations.net/index/v2` | none | ~180 req/min | `/citations/doi:...`, `/references/doi:...` |
| OpenAlex | `https://api.openalex.org/works` | optional `OPENALEX_API_KEY` | 1 req/s keyless | `filter=cites:W...`; `referenced_works` |
| Semantic Scholar | `https://api.semanticscholar.org/graph/v1` | optional `S2_API_KEY` | ~1 req/s keyed | `/paper/{id}/citations`, `/references` |

## Query syntax used by the compiler

### Europe PMC

```text
(TITLE_ABS:"retrieval-augmented generation" OR TITLE_ABS:"RAG")
AND (TITLE_ABS:"literature review" OR TITLE_ABS:"evidence synthesis")
AND (PUB_YEAR:[2018 TO 2026])
```

Sorts: default relevance, `P_PDATE_D desc`, `CITED desc`.

### PubMed

```text
("retrieval-augmented generation"[tiab] OR "RAG"[tiab])
AND ("literature review"[tiab] OR "evidence synthesis"[tiab])
AND ("2018"[dp] : "2026"[dp])
```

`esearch` returns PMIDs; `efetch` returns XML. The adapter parses title, abstract,
authors, journal, year, DOI, PMCID, publication types, and MeSH descriptors.

Known trap: generic phrases such as `"systematic review"[tiab]` and
`"literature search"[tiab]` appear in most review abstracts and can dominate the
result set. Keep them out of required concept blocks.

### arXiv

```text
(all:"retrieval-augmented generation" OR all:"RAG")
AND (all:"literature review" OR all:"evidence synthesis")
AND submittedDate:[201801010000 TO 202612312359]
```

Sorts: `relevance` or `submittedDate`. The adapter parses Atom XML, arXiv IDs,
DOI, journal reference, categories, and the PDF link.

### Crossref

```text
GET /works?query.bibliographic=...
  &filter=from-pub-date:2018-01-01,until-pub-date:2026-12-31
  &sort=relevance&order=desc
  &select=DOI,title,author,issued,container-title,abstract,is-referenced-by-count,type,URL,link,subject
```

Crossref has no reliable Boolean search; the compiler sends a plain-text
bibliographic query. `language` is **not** a valid `select` field on this route.
`reference` arrays are works' backward citations; there is no forward citation
endpoint. Some references are unstructured and have no DOI.

### OpenCitations

```text
GET /index/v2/citations/doi:10.1234/example
GET /index/v2/references/doi:10.1234/example
```

Returns `context`-less edges with `oci`, `citing`, `cited`, and `creation`.
DOI extraction is required; records are metadata-poor, so the adapter creates
stubs and optionally resolves them through Crossref.

### OpenAlex

```text
GET /works?search=...&filter=from_publication_date:2018-01-01,type:article&sort=relevance_score:desc
GET /works?filter=cites:W123456789
GET /works?filter=openalex:W123|W456
```

Useful fields: `referenced_works`, `related_works`, `abstract_inverted_index`,
`cited_by_count`, `citation_normalized_percentile`, `primary_topic`.
`filter=cites:<id>` is the canonical forward-citation query. A free key is
recommended; without it the shared daily budget can be exhausted.

### Semantic Scholar

```text
GET /graph/v1/paper/search?query=...&limit=...&fields=...
GET /graph/v1/paper/{paperId}/citations?fields=contexts,intents,isInfluential,...
GET /graph/v1/paper/{paperId}/references?fields=...
```

`contexts` and `intents` are sparse; do not assume every edge has them. A free
key gives a predictable ~1 req/s; keyless requests may return 429.

## Failure handling

- 429 / 5xx: retry with exponential backoff and `Retry-After`, up to 3 times.
- 401/403 on optional sources: mark `auth_required`, continue with keyless sources.
- 429 on optional sources: mark `rate_limited`, continue.
- Missing abstract: `evidence_depth = metadata_only`; no full-text claims.
- Missing DOI/PMID: citation expansion skips the seed and records `no_citation_data`.
- All sources failed: `search` exits with code 3. A single source failure never
  aborts the run.

## Adding a source

1. Implement `Adapter.search` and, optionally, `Adapter.citations`.
2. Return `SearchResult` / `CitationResult`; never return raw API payloads.
3. Populate `Paper.source_records` with source, query ID, rank, and URL.
4. Register the adapter in `adapters/__init__.py`.
5. Add an offline fixture test. Do not make the default suite depend on the network.
