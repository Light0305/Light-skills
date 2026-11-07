# Methodology & reading list

This skill is PRISMA-**informed**, not PRISMA-compliant. It searches, deduplicates,
screens titles/abstracts, expands citations once, and records the protocol. It does
not replace full-text assessment, dual screening, or a librarian peer review.

The design borrows from four traditions:

1. **Systematic review methodology** — a priori questions, explicit criteria,
   reproducible search reporting.
2. **Citation-network discovery** — backward/forward snowballing, co-citation,
   bibliographic coupling, bridge papers.
3. **Information retrieval** — multi-source union, query expansion, recency and
   citation-stratified retrieval, saturation.
4. **Evidence-grounded LLM synthesis** — every claim tied to a retrieved source,
   evidence-depth labels, citation verification.

---

## 1. Repositories worth studying

| Project | What to learn | What to watch out for |
|---|---|---|
| [nature-skills](https://github.com/Yuan1z0825/nature-skills) — `nature-literature-pipeline`, `nature-academic-search` | Multi-source fallback; six-dimension scoring; evidence-depth labels; archival boundary; manifest routing; citation auditing | Weak query front end; fixed weights; top-5 delivery bias; no formal saturation |
| [paper-search-pro](https://github.com/O0000-code/paper-search-pro) | PICO/SPIDER/PEO query planning; Quick/Standard/Deep/Audit tiers; parallel screening; coverage curve; PRISMA-S log; raw vs derived separation | OpenAlex-heavy; closed databases only get paste-ready strategies; Audit is long |
| [paper-search-mcp](https://github.com/openags/paper-search-mcp) | 20+ sources behind one CLI/MCP; `search`/`read`/`download`; source presets; DOI resolution | Retrieval only; no question decomposition, screening, or synthesis |
| [literature-review-skill](https://github.com/YANZHANLIN/literature-review-skill) | Five sub-skills; PICO/SPIDER + PRISMA-S; Keshav three-pass reading; concept-centric synthesis | Review-writing workflow, not a discovery engine; PDF access depends on subscriptions |
| [litdb](https://github.com/jkitchin/litdb) | LLM-generated query variants; citation-count stratification; semantic rerank; iterative references/citations/related expansion | Local-collection scope; OpenAlex records are often title+abstract only |
| [paper-qa](https://github.com/Future-House/paper-qa) / [OpenScholar](https://www.nature.com/articles/s41586-025-10072-4) | Evidence-grounded synthesis; citation faithfulness; iterative refinement; coverage vs precision trade-off | Reading/answering systems, not recall-oriented search front ends |
| [awesome-paper-research-skills](https://github.com/fengmo11/awesome-paper-research-skills) | Index of idea-discovery, search, citation, writing, and review skills | Quality varies; check methodology docs |

A useful distinction: most existing skills optimize the **back end** (retrieve,
score, summarize). The weakest shared part is the **front end** — turning a vague
direction into concepts, synonyms, operationalized questions, and source-specific
queries. This skill puts most of its design effort there.

---

## 2. Core methods

### 2.1 PRISMA 2020 and PRISMA-S

PRISMA-S is the search-reporting extension of PRISMA. It has 16 items. Two matter
most for this skill:

- **Item 5**: state whether cited references or citing references were examined,
  and how they were located.
- **Item 8**: report the full search strategies exactly as run.

The skill records `query_plan.json`, `compiled_queries.json`, and `search_log.json`
so another person can rerun the search.

- [PRISMA-S official page](https://www.prisma-statement.org/prisma-search)
- [Rethlefsen et al. 2021, Systematic Reviews](https://link.springer.com/article/10.1186/s13643-020-01542-z)

### 2.2 Snowballing

Wohlin (2014) defines:

- **Backward snowballing**: follow the reference list of an included paper.
- **Forward snowballing**: find papers that cite an included paper.
- Iterate until no new studies appear.

The main threat is **seed-set bias**. If the seeds come from one database or one
school of thought, snowballing amplifies that bias. Use multiple seeds from
different lenses and sources.

- [Wohlin 2014, EASE](https://dl.acm.org/doi/10.1145/2601248.2601268)
- [Badampudi, Wohlin & Petersen 2015](https://dl.acm.org/doi/10.1145/2745802.2745815)

### 2.3 Question frameworks

- **PICO / PICOS**: population, intervention, comparison, outcome, study design.
  Best for effectiveness questions.
- **PECO**: population, exposure, comparison, outcome. Best for risk/prognosis.
- **SPIDER**: sample, phenomenon of interest, design, evaluation, research type.
  Best for qualitative and mixed-methods questions.
- **TMDMB** (this skill's CS extension): task, method, dataset, metric, baseline.

The framework is a thinking aid, not a ritual. Do not force PICO onto a systems
paper or TMDMB onto a qualitative health study.

- [Cooke, Smith & Booth 2012 — SPIDER](https://doi.org/10.1177/1049732312452938)
- [PICO/PICOS/SPIDER comparison (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4310146/)

### 2.4 Review types

Snyder (2019) distinguishes systematic, semi-systematic, and integrative reviews.
Choose the type before choosing the method. A "systematic review" label without a
protocol, full-text assessment, and reproducible search is misleading.

- [Snyder 2019, Journal of Business Research](https://doi.org/10.1016/j.jbusres.2019.07.039)

### 2.5 Reading

Keshav's three-pass method:

1. **First pass (5–10 min)**: title, abstract, introduction, headings, conclusions,
   references; answer the five C's (category, context, correctness, contributions,
   clarity).
2. **Second pass (~1 hour)**: figures, evidence, assumptions; summarize the main
   thrust.
3. **Third pass (hours)**: virtually re-implement the paper; find hidden assumptions
   and future work.

The report's reading path uses these tiers to decide what to read first.

- [Keshav 2007 PDF](http://www.sigcomm.org/sites/default/files/ccr/papers/2007/July/1273445-1273458.pdf)

### 2.6 Evidence-grounded synthesis

OpenScholar (Nature, 2026) and PaperQA2 show that retrieval-augmented synthesis can
be competitive with expert answers when coverage and citation faithfulness are
measured. PaperQA2 has high citation precision but low coverage; OpenScholar covers
more papers and improves citation accuracy. The lesson: **do not optimize only for
precision or only for recall**. Report both, and verify citations mechanically.

- [OpenScholar, Nature 2026](https://www.nature.com/articles/s41586-025-10072-4)
- [PaperQA2 / LitQA2, arXiv 2409.13740](https://arxiv.org/abs/2409.13740)

---

## 3. Search-quality pitfalls

### 3.1 Query errors

Sampson & McGowan (2006) and the Cochrane search peer-review literature document
common errors: missing MeSH/controlled vocabulary, irrelevant terms, missed
spelling variants, Boolean logic errors, line-combination errors, and syntax copied
from another database. In Cochrane reviews, 73–90% of searches had at least one
problem; many affected recall.

- [Sampson & McGowan 2006](https://www.sciencedirect.com/science/article/abs/pii/S0895435606000436)
- [Cochrane Search Peer Review Essentials](https://community.cochrane.org/sites/default/files/uploads/inline-files/Search-Peer-Review_Essentials_April2022.pdf)
- [PRESS checklist (McGowan et al. 2016)](https://onlinelibrary.wiley.com/doi/pdf/10.1002/jrsm.40)

**Countermeasures in this skill**: concept blocks, synonyms and spelling variants,
source-specific query compilers, `plan validate --strict`, and a search log that
records the exact query.

### 3.2 Single-database and language bias

A single database misses papers indexed elsewhere. English-only searches miss
non-English literature. Grey literature and negative results are systematically
underrepresented.

**Countermeasures**: multi-source union, source status reporting, explicit language
and date bounds, and a limitations section that says what was not searched.

### 3.3 Citation-count worship

Citation counts favor old papers and established groups. A brand-new paper with
zero citations can be the most important paper in the set. Journal impact factor is
not relevance.

**Countermeasures**: a transparent score (relevance 35, recency 20, citation impact
15, source agreement 10, evidence depth 10, metadata 10), recency-sorted retrieval
variants, and a frontier bonus.

### 3.4 Snowballing limits

Citation searching is a safety net, not a completeness guarantee:

- Cantrell et al. (2022) found citation searching identified no additional
  direct-evidence studies in one case study, though it helped confirm the
  bibliographic record.
- A 2023 *J Clin Epidemiol* study found citation searching raised recall from 62.4%
  to 83.2%, but 12.9% of included studies were still unretrieved.
- Cochrane MR000026 warns that reference lists contain citation errors and that
  uninformative titles/abstracts can cause relevant studies to be screened out.

- [Cantrell et al. 2022](https://onlinelibrary.wiley.com/doi/full/10.1111/hir.12428)
- [Supplementary strategies, J Clin Epidemiol 2023](https://www.sciencedirect.com/science/article/pii/S0895435623001051)
- [Cochrane MR000026](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.MR000026.pub2/full)

**Countermeasures**: multiple seeds, backward + forward expansion, edge provenance,
and a provisional saturation record — never a completeness claim.

### 3.5 Screening errors

Abstract-only screening can miss relevant studies or overstate quality. Inconsistent
criteria across papers produce irreproducible decisions.

**Countermeasures**: a six-dimension rubric, reason codes, evidence-depth labels,
and a rule prescreen that only applies hard filters.

### 3.6 LLM citation hallucination

Multiple 2026 studies report fabricated citation rates roughly in the 3–25% range,
depending on model, topic, and prompt. Even "real" citations often have wrong DOIs
or metadata. Deep-research agents are not automatically safer.

- [Medical LLM review citation fabrication](https://www.sciencedirect.com/science/article/abs/pii/S0377123726000808)
- [Fluency Without Fidelity](https://link.springer.com/content/pdf/10.1007/s41347-026-00630-6.pdf)
- [HALLMARK citation verifier benchmark](https://export.arxiv.org/abs/2607.18360)

**Countermeasures**: `papers.jsonl` is the only source of truth; `[[p_id]]` tokens;
the renderer fails on unknown IDs; BibTeX is generated from records, never from
model memory; `verify` checks unresolved tokens.

### 3.7 Reproducibility failures

If the search date, query, filters, and source versions are not recorded, the search
cannot be reproduced or audited.

**Countermeasures**: `query_plan.json`, `compiled_queries.json`, `search_log.json`,
`merge_log.json`, and cache.

### 3.8 Ethics and access

Do not scrape paywalled databases, do not use Sci-Hub, and do not redistribute
PDFs. Use metadata, abstracts, and open-access links. Check retraction status.

---

## 4. How this skill maps to the methods

| Method idea | Implementation |
|---|---|
| Question ladder | `query_plan.questions` with `operationalization` |
| Field-adaptive framework | `framework.name` + `fields` (PICO/PICOS/PECO/SPIDER/TMDMB/CUSTOM) |
| Concept blocks | `concept_blocks[].terms` with free/controlled vocabulary |
| Multi-perspective search | `lenses[]` with query legs and sort variants |
| PRISMA-S reporting | `compiled_queries.json` + `search_log.json` |
| Backward/forward snowballing | `citations expand --directions forward,backward` |
| Saturation | `saturation.json` with per-round yield and stopping reason |
| Evidence depth | `Paper.evidence_depth` + screening column |
| Citation faithfulness | `synthesis.json` tokens + `verify` |
| Bilingual reporting | `report.en.md` / `report.zh.md` / `report.bilingual.md` |

---

## 5. A short reading order

If you only read five things:

1. PRISMA-S (what to report).
2. Wohlin 2014 (how to snowball).
3. Sampson & McGowan 2006 (how searches fail).
4. Snyder 2019 (what kind of review you are actually doing).
5. OpenScholar / PaperQA2 (why coverage and citation faithfulness must be measured).

If you are building the skill itself, also read `paper-search-pro`'s SKILL.md and
`nature-skills`' literature pipeline. They are the closest prior art.
