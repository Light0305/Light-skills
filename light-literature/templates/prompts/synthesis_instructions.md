# Synthesis contract

You are writing `runs/<run>/synthesis.json`. This is the only place where the host
agent writes prose. The renderer will reject unknown paper IDs and unresolved
tokens.

Read `papers.jsonl`, `screening.csv`, `citation_edges.jsonl`, and
`saturation.json` first.

---

## 1. Citation tokens

Every claim that depends on a paper must use an internal ID token:

```text
... multi-source retrieval improves coverage [[p_ab12cd34ef56]].
```

Rules:

- The ID must exist in `papers.jsonl`.
- Use the paper's `paper_id`, not a DOI, title, or guessed ID.
- The renderer replaces tokens with `[1]`, `[2]`, … in order of first appearance.
- An unknown ID is a hard error.
- Do not cite a paper that is not in the included/maybe set unless you explicitly
  mark it as background in the text.
- Do not write BibTeX or a reference list manually; exports come from records.

---

## 2. Schema

```json
{
  "schema_version": "1.0",
  "summary": {
    "en": "...",
    "zh": "..."
  },
  "question_answers": [
    {
      "question_id": "Q1",
      "answer": {"en": "...", "zh": "..."},
      "paper_ids": ["p_..."]
    }
  ],
  "reading_path": [
    {
      "tier": "foundation|core|method|frontier|contrarian|adjacent",
      "paper_ids": ["p_..."],
      "rationale": {"en": "...", "zh": "..."}
    }
  ],
  "gaps": [
    {
      "gap_id": "G1",
      "type": "method|data|population|contradiction|linkage|measurement|translation",
      "statement": {"en": "...", "zh": "..."},
      "evidence_paper_ids": ["p_..."],
      "confidence": "low|medium|high",
      "evidence_types": ["author_limitation", "contradiction", "missing_link", "method_gap", "data_gap"]
    }
  ],
  "idea_cards": [
    {
      "idea_id": "I1",
      "title": {"en": "...", "zh": "..."},
      "closest_prior_art": ["p_..."],
      "delta": {"en": "...", "zh": "..."},
      "feasibility": {"en": "...", "zh": "..."},
      "discriminating_experiment": {"en": "...", "zh": "..."},
      "expected_negative_result": {"en": "...", "zh": "..."}
    }
  ],
  "limitations": {"en": "...", "zh": "..."}
}
```

---

## 3. What good looks like

### Summary

- State what the map covers and what it does not.
- Name the main clusters, not every paper.
- Use 2–4 citations.
- Do not say "the literature shows" without a citation.
- Do not claim completeness.

### Question answers

- Answer the operationalized question, not the vague direction.
- If the evidence is thin, say so.
- One paragraph per question.
- Cite at least one paper per empirical claim.

### Reading path

- `foundation`: read first; surveys, seminal papers, method comparisons.
- `core`: directly answers the questions.
- `method`: what to borrow or replicate.
- `frontier`: recent, high-potential work.
- `contrarian`: critiques, negative results, retractions, contradictions.
- `adjacent`: background or cross-field inspiration.

Each tier needs a rationale. Do not put every paper in `core`.

### Gap candidates

A gap is not "few papers exist". A defensible gap has at least two evidence types:

- an author-stated limitation;
- a contradiction between studies;
- a missing citation link (two literatures that should talk but do not);
- a method gap (no causal design, no benchmark, no longitudinal data);
- a data/population gap;
- a measurement gap;
- a translation gap (lab to practice).

If you only have one weak signal, set `confidence: low` and say what would close
the gap.

### Idea cards

Each card must answer:

1. What is the closest prior art?
2. What exactly is new (delta)?
3. Can it be done with available data/compute/time?
4. What experiment would distinguish it from the prior art?
5. What negative result would falsify it?

An idea without a discriminating experiment is a slogan, not a research idea.

### Limitations

Always state:

- PRISMA-informed, not PRISMA-compliant;
- title/abstract screening only;
- one citation round;
- sources, years, languages;
- any degraded source;
- any evidence depth limitations.

---

## 4. Validate

```bash
python run_litsearch.py report --run runs/<run> --lang both
python run_litsearch.py verify --run runs/<run> --strict
```

If `verify` reports `[zh missing]`, write the Chinese text. Do not leave a
half-translated report.
