# Mathematics and formal theory

- **ID:** mathematics-theory
- **Maturity:** draft
- **Scope:** Expository revision of definitions, assumptions, propositions, proofs, counterexamples, and conditional theoretical arguments.
- **Out of scope:** Certifying proof correctness, supplying missing proofs as established facts, or imposing one discipline's notation/style.
- **Provenance:** Editorial starting guide; no mathematical-expert review or output evaluation.
- **Last reviewed:** Not reviewed

## Argument and evidence load

Separate definitions, assumptions, conjectures, lemmas, proved results, examples, and empirical observations. Preserve logical scope: a result under explicit conditions cannot become unconditional, and numerical evidence does not establish a theorem.

## Writing decisions

- **Parameter dependence:** When convergence or existence is proved for each fixed
  parameter, make permitted dependence visible in prose or notation. For example,
  a threshold written as N(epsilon) for a fixed theta may be clarified as
  N(epsilon, theta), with the notation explicitly explained. Do not infer a
  parameter-independent threshold, rate, constructive bound, or stronger theorem
  from that clarification. Preserve the original quantifier order.

- **Motivation:** Explain the mathematical question, object, or difficulty before claiming generality. Preserve what existing results actually establish; do not invent a priority gap or missing literature.
- **Definitions:** Introduce symbols before use and keep domains, quantifiers, dependence, and notation consistent. Apparent synonyms may denote distinct mathematical objects; do not normalize them without checking definitions.
- **Statements:** Preserve necessary/sufficient distinctions, existence/uniqueness, bounds, equality cases, limiting regimes, and assumptions. A smoother sentence must not change “there exists” to “for all”, local to global, or almost surely to surely.
- **Proof exposition:** Improve signposting and explain the role of a step when supported by the source. If a transition lacks justification, mark a proof gap rather than insert a plausible argument as if verified. Editing is not independent formal verification.
- **Examples/counterexamples:** Keep their logical function clear. One example illustrates; a valid counterexample refutes a universal statement; finite simulations do not prove a universal theorem.
- **Conclusion:** State consequences only within established assumptions. Describe unproved extensions as conjectures or open questions when the author intends them.

## Common failure modes

| Failure | Corrective check |
|---|---|
| A hypothesis or conjecture becomes a theorem | What proof is supplied and what status does the author assign? |
| Quantifiers or domain restrictions disappear | Does the revised statement have the same logical scope? |
| A proof gap is filled with unverified reasoning | Is the justification explicit or still missing? |
| Notation changes merge distinct objects | Are definitions and dependencies preserved? |

## Interactions

Combine with computing for algorithmic theory or physical-sciences-engineering for physical derivations. Theory in humanities/social sciences may use a different form of argument; do not force formal mathematics on interpretive theory.

## Sources and verification

No external disciplinary sources or venue rules have been verified for this draft.

- **Expert review record:** None
- **Evaluation record:** None
- **Known gaps:** Proof validity and subfield notation need specialist review; prose improvement does not certify mathematics.
