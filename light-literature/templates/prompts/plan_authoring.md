# Query-plan authoring contract

You are the host agent. Your job is to turn a research direction into a
machine-readable `query_plan.json`. The scripts will not invent questions,
synonyms, or inclusion criteria for you.

Read `SKILL.md` and `references/methodology.md` first.

---

## 0. Bilingual rule

**Output bilingual does not mean search bilingual.** The default sources are
English-indexed (OpenAlex, Crossref, Europe PMC, OpenAIRE). If the user's
direction is Chinese:

- translate it into English canonical terms;
- put those English terms in `concept_blocks`;
- keep the Chinese text in `direction.zh` and the questions/answers;
- never leave a required concept block Chinese-only.

Use:

```bash
python run_litsearch.py plan init \
  --direction "人工智能在科学文献综述中的应用" \
  --direction-en "artificial intelligence for scientific literature review" \
  --domain cs --lang both --out runs/my-run/query_plan.json
```

or edit the skeleton. A Chinese-only query such as
`"人工智能在科学文献综述中的应用"` is treated as one exact phrase by English
indexes and returns noise, not the intended literature. CNKI/Wanfang are not
covered; do not promise exhaustive Chinese-language coverage.

---

## 1. Clarify (at most three questions)

Ask only if the answer changes the search:

1. What decision will this map support (scope, systematic review, proposal,
   method choice, gap finding)?
2. What is in scope: population/context, intervention/exposure/task, comparator,
   outcome/metric, data setting?
3. What are the hard constraints: years, languages, peer review, exclusions?

If the user does not answer, state assumptions in the plan and proceed.

---

## 2. Build the question ladder

Write:

- 1 grand challenge;
- 3–5 answerable questions;
- 1–3 testable sub-questions.

Every answerable question must have an `operationalization` of at least 20
characters. A good operationalization names:

```text
population/context + intervention/exposure/task + comparator + outcome/metric + data setting
```

Examples:

- **PICO**: adults with type 2 diabetes; GLP-1 receptor agonist; usual care;
  cognitive decline; RCT or cohort; 2015–2026.
- **SPIDER**: remote knowledge workers; well-being; interviews or surveys;
  burnout/engagement; qualitative or mixed methods.
- **TMDMB**: literature review; retrieval-augmented generation; paper corpora;
  recall/faithfulness; LLM-only or single-database baselines.

Avoid questions that cannot be answered by a paper. "What is the future of X?" is
not answerable; "What evidence exists that X improves Y under Z?" is.

---

## 3. Choose the framework

| Domain | Framework |
|---|---|
| Biomed / health | PICO or PICOS / PECO |
| Social science / qualitative | SPIDER |
| CS / ML | TMDMB |
| General / exploratory | CUSTOM |

Fill `framework.fields` with concrete values, not empty strings, when possible.

---

## 4. Build concept blocks

Each block is one concept. Within a block, terms are OR-ed. Blocks are AND-ed.

For each block:

- canonical term;
- synonyms and abbreviations (`retrieval-augmented generation`, `RAG`);
- spelling/hyphen variants (`retrieval augmented generation`);
- broader/narrower terms;
- controlled vocabulary if available (MeSH, Emtree, ACM CCS, JEL);
- Chinese terms if the user wants Chinese coverage.

Do not put two different concepts in one block. Do not put generic words
(`study`, `paper`, `review`, `systematic review`, `analysis`, `literature search`)
in a required block unless they are central. In PubMed, `"systematic review"[tiab]`
matches almost every medical systematic review, and `"literature search"[tiab]`
appears in the methods paragraph of most reviews; together they can recall a huge
number of irrelevant papers. If you need a study type filter, put it in
`filters.types` or a separate optional leg, not in the core concept block. Strict
validation rejects a required block that contains only generic terms.

A good block:

```json
{
  "id": "C1",
  "label": {"en": "retrieval / RAG", "zh": "检索 / RAG"},
  "required": true,
  "terms": [
    {"text": "retrieval-augmented generation", "lang": "en", "type": "free", "vocab": "none"},
    {"text": "RAG", "lang": "en", "type": "free", "vocab": "none"},
    {"text": "retrieval augmented generation", "lang": "en", "type": "free", "vocab": "none"}
  ]
}
```

A bad block: one term equal to the entire direction sentence.

---

## 5. Choose lenses

Default to three:

- `foundation_frontier`: seminal works, surveys, recent frontier.
- `skeptic_method`: critiques, negative results, limitations, benchmarks.
- `practitioner`: applications, deployment, case studies, adjacent fields.

Each lens has one or more `query_legs`. A leg selects concept blocks and may add
`terms_override` (for example, `limitation`, `failure`, `benchmark`, `deployment`).
Use overrides sparingly; they narrow the query.

In deep mode, add:

- `historical`: older terminology and foundational work.
- `adjacent`: a neighbouring field that may have solved the problem.

---

## 6. Set filters and budgets

- `year_from`, `year_to`: be explicit.
- `languages`: at least `["en"]`; add `"zh"` if Chinese coverage matters.
- `include_preprints`: true for CS/ML, false for clinical evidence.
- `exclude_retracted`: true unless the user asks otherwise.
- `min_abstract_chars`: 0 by default; raise to 200 if you want to skip stubs.
- `max_per_source`: 40–100 for a standard run; higher for audit.
- `max_requests_per_source`: 9 by default.
- `max_citation_seeds`: 10.

---

## 7. Set inclusion/exclusion criteria

Write criteria that a human can apply to a title and abstract. Avoid vague
criteria such as "high quality" unless you define an operational proxy.

Example:

```json
{
  "include_criteria": [
    "Directly addresses at least one listed question.",
    "Reports primary evidence, a method, a benchmark, or a substantive critique."
  ],
  "exclude_criteria": [
    "Editorial, comment, erratum, or non-research news.",
    "Outside the stated population/context/date/language scope."
  ]
}
```

---

## 8. Validate

```bash
python run_litsearch.py plan validate --plan runs/my-run/query_plan.json --strict
```

Fix every error. Then compile:

```bash
python run_litsearch.py plan compile --plan runs/my-run/query_plan.json --out runs/my-run/compiled_queries.json
```

Inspect the compiled queries. If a query is too narrow (one exact long phrase) or
too broad (only generic words), go back to the concept blocks.
