# Screening instructions

You are screening titles and abstracts. You are **not** writing a review yet.

Read `runs/<run>/papers.jsonl` and `runs/<run>/screening.csv` (or `.jsonl`).
Work in batches of 10–20. Preserve the CSV header.

---

## 1. Evidence boundary

- Use only the title, abstract, metadata, and the user's stated criteria.
- Do not use your memory of a paper to fill missing evidence.
- If the abstract is missing, mark `evidence_depth: metadata_only` and lower
  confidence.
- Do not claim a method works; only record what the abstract says.

---

## 2. Eligibility first; rubric as a reading aid

Apply the plan's actual inclusion/exclusion criteria before any score. Decide
from observable eligibility, not an arbitrary total, prestige, positive results
or how much methodology an abstract happens to describe. Missing information is
unknown and normally needs `maybe` plus targeted retrieval. Reviews, theoretical
work, qualitative studies, negative results and preprints can be in scope when
the plan permits them. `NO_PRIMARY_DATA` or `NOT_PEER_REVIEWED` is an exclusion
only when the corresponding requirement belongs to the actual plan.

The following 0–2 dimensions can organize notes or prioritize reading. A missing
method detail is unassessable, not demonstrated poor rigor. Do not substitute this
generic rubric for a study-type-specific full-text appraisal.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Question fit | different question | adjacent | directly answers a listed question |
| Population/context | wrong setting | partly comparable | matches scope |
| Method/design rigor | no discernible method | weak/unclear | appropriate and described |
| Evidence/data | no primary evidence | limited | sufficient for the claim |
| Perspective value | none | background | foundation/frontier/skeptic/method/practitioner |
| Recency/currency | superseded | some value | current or historically essential |

Decision:

- `include`: meets the actual eligibility criteria with a specific explanation.
- `maybe`: relevant eligibility information is missing or conflicting; state what resolves it.
- `exclude`: a documented criterion is actually violated; cite that criterion.

`min_abstract_chars` is a readiness signal for manual/source review, not proof
that a study is ineligible. Preserve such records in the review queue.

---

## 3. Reason codes

Use exactly one:

```text
PENDING_REVIEW          # maybe; not yet judged
IN_SCOPE                # include; directly answers a question
OUT_OF_SCOPE
WRONG_POPULATION
WRONG_DESIGN
NO_PRIMARY_DATA
NOT_PEER_REVIEWED
DUPLICATE_VERSION
LANGUAGE
DATE_RANGE
RETRACTED
LOW_RELEVANCE
INSUFFICIENT_EVIDENCE   # maybe or exclude
UNABLE_TO_VERIFY
BUDGET_LIMIT
NO_TITLE
```

- `include` → `IN_SCOPE` (or a more specific positive code if you add one).
- `maybe` → `PENDING_REVIEW` or `INSUFFICIENT_EVIDENCE`.
- `exclude` → one of the negative codes.

`reason_text` is the authoritative explanation. Make it specific:

- Good: "Directly compares multi-source retrieval with snowballing under a fixed
  recall budget; matches Q3."
- Bad: "Relevant."

Do not use `IN_SCOPE` with `exclude`, and do not leave `PENDING_REVIEW` on an
`include` — the validator rejects it.

---

## 4. Output

Write back to `screening.csv` (UTF-8 with BOM) and/or `screening.jsonl`.
Fields:

```text
paper_id, title, year, venue, doi, evidence_depth,
decision, reason_code, reason_text, question_ids, scores,
confidence, lens_tags, notes, screened_by, screened_at
```

Set `screened_by` to `agent`. Set `confidence` to `low|medium|high`.
Do not delete rows; update them.

Then run:

```bash
python run_litsearch.py screen validate --run runs/<run>
```

Fix every error before rendering the report.

---

## 5. Calibration

Before screening 100 papers, screen 10 and re-read the criteria. Ask:

- Would another researcher make the same decision from this abstract?
- Am I including a paper because it is famous, or because it answers a question?
- Am I excluding a paper because it is a preprint, or because it is irrelevant?
- Are the `maybe` decisions genuinely uncertain, or am I avoiding a judgment?

Record disagreements in `notes`; do not silently average them away.
