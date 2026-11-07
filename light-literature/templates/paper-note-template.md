# {{title}}

> **Paper card**
> Authors: {{authors}} · Year: {{year}} · Venue: {{venue}} · DOI: {{doi}}
> PDF: `paper.pdf` · source Markdown: `paper.md` · Translation: `paper.zh.md`
> Reading mode: {{skim | review | implement | teach}} · Confidence: {{low | medium | high}}
> Note status: {{complete | partial — state what was read}}

> **Rules for this note**
> - This is **not a summary**. It is an evidence-anchored reading note for future idea generation.
> - Separate **[Author]** claims from **[Analyst]** inferences.
> - Every factual claim needs an anchor: section, page, figure, table, equation, or algorithm.
> - If a section cannot be assessed from the supplied material, write **“Not assessable from supplied material.”** Do not invent.
> - Every main figure/table must be embedded with a relative image path and a short “what it shows / why it matters / counter-reading” block.
> - Keep the authors' hedging: “may” ≠ “does”; “suggests” ≠ “shows”.

## 0. One-sentence takeaway

{{One sentence that a researcher could quote in a related-work section.}}

## 1. Identification and provenance

- **Title:**
- **Authors / labs:**
- **Year / venue / review status:**
- **DOI / arXiv / code / data:**
- **Source form:** PDF / source Markdown / publisher HTML
- **What was actually read:** body / appendix / supplementary / captions / partial
- **Extraction issues:** missing figures, garbled equations, missing appendix, etc.

## 2. Problem, motivation, and research question

- **Concrete failure or gap [Author]:**
- **Why it matters [Author]:**
- **Research question / hypothesis [Author]:**
- **The authors' central bet [Analyst]:**
- **Scope and assumptions [Author]:**

## 3. Contributions (author-framed)

List only what the authors claim, without inflation.

- **C1:**
- **C2:**
- **C3:**

## 4. Contribution → evidence matrix

| ID | Claim [Author] | Evidence offered | Anchor | Strength | Analyst verdict |
|---|---|---|---|---|---|
| C1 | | | § / p. / Fig. / Tab. / Eq. | present / weak / absent | |
| C2 | | | | | |
| C3 | | | | | |

**Rule:** if the evidence cannot be anchored, record it as **absent**, not “probably in the paper”.

## 5. Method reconstruction

### 5.1 Pipeline

| Stage | What it does | Inputs | Outputs | Anchor |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

- **Essential design choices vs incidental choices:**
- **What was ablated / controlled:**
- **What was not ablated:**
- **Dependencies and failure modes:**

### 5.2 Symbols, assumptions, and math

- **Symbol table:** symbol → meaning → role
- **Prominent equations:** equation → what it enforces → anchor
- **Assumptions the method relies on:**
- **A concrete numerical micro-example:**

## 6. Data and experimental design

- **Datasets / splits / sizes:**
- **Baselines and whether they share data, steps, and tuning budget:**
- **Metrics and why they fit the claim:**
- **Training / inference cost:**
- **Leakage checks:** preprocessing, test-set tuning, temporal leakage, duplicate papers
- **Statistical reporting:** seeds, error bars, confidence intervals, significance

## 7. Key figures and tables

For each main figure/table, copy the image and write the three-part reading.

### Figure / Table {{N}} — {{short title}}

![{{caption}}]({{relative path to image}})

- **What the authors want it to support [Author]:**
- **What it actually shows [Analyst]:**
- **Counter-reading:** crossing curves, overlapping error bars, log axes, single seed, cherry-picked examples, missing baseline
- **Anchor:** § / p. / Fig. / Tab.
- **Why it matters for future work:**

{{Repeat for every main figure/table. If an image is unavailable, say so explicitly.}}

## 8. What I believe, what I doubt, what changed

- **I believe:** claims with strong evidence + anchor
- **I doubt:** claims with weak/absent evidence + why
- **What changed in my understanding:**
- **What I would tell a colleague in 30 seconds:**

## 9. Critical layer

### 9.1 Author-stated limitations

- [Author] …

### 9.2 Analyst critique

- [Analyst] …

### 9.3 Red flags (max 3, ranked)

1. **{{claim}}** — evidence gap / anchor / why it threatens the conclusion
2. …
3. …

### 9.4 Uncertainty flags

- **Unreported quantity needed for the conclusion:**
- **Claim depends on a condition not tested:**
- **Ambiguous wording / hedging:**

## 10. Relation to prior work

- **What this paper claims is new:**
- **Closest prior art (with anchors / citations):**
- **What is genuinely different [Analyst]:**
- **What is a reframing of existing work:**
- **Citation context:** is this paper cited as a baseline, method, critique, or application?

## 11. Reusable assets

- **Method components I could reuse:**
- **Experimental designs / ablations I could copy:**
- **Datasets, metrics, or evaluation protocols:**
- **Writing / framing moves:**
- **Code / data links:**

## 12. Gaps and open questions

- **Population / data gap:**
- **Method gap:**
- **Mechanism gap:**
- **Measurement gap:**
- **Boundary-condition gap:**
- **Contradiction with other work:**
- **What would close each gap:**

## 13. Idea cards (3–5)

Each card must be a testable research idea, not a topic.

### Idea 1 — {{short title}}

- **Closest prior art:** paper IDs / citations
- **Delta:** what is new relative to prior art
- **Why now:** new data, compute, model, or evaluation
- **Feasibility:** data, compute, time, expertise
- **Discriminating experiment:** the experiment that separates this idea from the prior art
- **Expected negative result:** what would falsify the idea
- **Risks / confounders:**

{{Repeat. If you cannot produce 3 defensible ideas, write fewer and explain why.}}

## 14. Reproduction checklist

- [ ] Pipeline stages implemented in the same order
- [ ] Equations / loss functions match the paper
- [ ] Hyperparameters and search space recorded
- [ ] Data splits and preprocessing reproduced
- [ ] Baselines share the same tuning budget
- [ ] Metrics implemented identically
- [ ] Seeds / error bars / significance reported
- [ ] Testable claims listed
- [ ] Known gotchas recorded

## 15. Key quotes and equations

> “{{exact quote}}” — § / p.

$$
{{equation}}
$$

- **Why this quote/equation matters:**

## 16. Links and reading log

- **Related notes in this Literature folder:**
- **Follow-up papers to read:**
- **Code / data / project page:**
- **Reading log:** date started / finished / time spent
- **Next action:** {{replicate / critique / extend / cite / discard}}
