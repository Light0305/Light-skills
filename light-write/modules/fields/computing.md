# Computing and computational methods

- **ID:** computing
- **Maturity:** draft
- **Scope:** Writing about algorithms, machine learning, computer vision, software, and systems evaluations where supplied evidence includes experiments, benchmarks, proofs, or system measurements.
- **Out of scope:** A complete guide to all computing subfields; current rules of CVPR, AAAI, IEEE venues, or any ranking system.
- **Provenance:** Editorial starting guide derived from general research-writing principles; no domain-expert review or corpus study has been performed.
- **Last reviewed:** Not reviewed

## Argument and evidence load

Identify the contribution precisely: algorithm, theoretical property, dataset, evaluation finding, system, or application. A benchmark improvement is not interchangeable with novelty, mechanistic understanding, efficiency, robustness, or deployment utility. Separate mathematical results from measured outcomes and proposed explanations.

## Writing decisions

- **Motivation:** When describing a technical gap, connect the limitation to the actual task, data assumptions, resource setting, and proposed design. Do not claim prior methods fail universally from one setup or call an unsearched topic unprecedented.
- **Method:** Explain inputs, outputs, assumptions, objective, and the role of each component. Preserve notation consistently. Distinguish a design rationale from evidence that a component caused an improvement; an ablation can be informative without isolating every confound.
- **Evaluation:** Tie each claim to the tested dataset, split, metric, baseline, compute budget, and conditions that the author provides. If fairness of comparison, leakage control, seeds, variance, or baseline tuning is unspecified, flag the detail rather than asserting it was controlled.
- **Results:** State what improves and by how much with the correct units. Percentage-point differences and relative percentage changes are different; do not compute or reinterpret them unless requested and justified. Do not turn one run into a statistically established gain.
- **Efficiency:** Scope runtime, latency, memory, energy, or complexity claims to their source. Asymptotic analysis does not establish measured hardware speed, and measured speed does not establish asymptotic complexity.
- **Discussion:** Bound generalization by evaluation coverage; do not call a model robust, safe, fair, causal, or production-ready from accuracy alone. A real-world deployment claim needs evidence beyond an offline benchmark.
- **Language:** Prefer precise contribution labels over “novel”, “significant”, or “state-of-the-art” without defined evidence. Preserve algorithm names, variable meanings, and metric directions.

## Common failure modes

| Failure | Corrective check |
|---|---|
| Benchmark rank becomes universal superiority | Which datasets, tasks, baselines, and resource budgets were actually tested? |
| Ablation becomes mechanism proof | Could other changes or interactions explain the result? |
| Missing evaluation conditions are filled by convention | Is the split, test protocol, or tuning procedure actually documented? |
| Mathematical and empirical claims blur | Which statement is proved, observed, or conjectured? |

## Interactions

Combine with clinical-health for patient-facing evaluations, with physical-sciences-engineering for hardware systems, or with mathematics-theory for formal claims when applicable. Do not apply empirical Results rules to a proof-only paper.

## Sources and verification

No external field sources have been verified for this draft. No venue policy is encoded.

- **Expert review record:** None
- **Evaluation record:** None
- **Known gaps:** Specialized conventions and subfields need expert review; no claim of top-tier output quality is supported yet.
