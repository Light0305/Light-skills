# Optional manuscript revision receipt, version 1.0

This packet is useful for saved revisions and repeated handoffs. It is not required for a local edit, a message-only task, or every project. A compact human ledger may suffice. The read-only auditor does not generate prose, execute analysis, use the network, create directories, or modify files.

Start from `templates/manuscript-packet.json` only when useful. Its blank fields deliberately fail until filled with real adopted materials; it is not a completed example. Use JSON, not a parallel YAML contract.

## Contents and path rules

| Field | Meaning |
|---|---|
| `schema_version` | Exactly `"1.0"`. |
| `basis` | Actual task/materials, read scope, and important verification limits. |
| `manuscript` | Nonempty `paper_id`, `revision`, `path`, and lower-case 64-digit `sha256` of the saved draft's actual bytes. Same paper, new revision on material handoff. |
| `sources` | Array of distinct nonempty `id` values; each has `role`, `path`, `sha256`. Bind actual adopted analysis report/handoff/inputs, Journal brief/packet, literature, or figure files as relevant. The manuscript cannot cite itself as independent support. |
| `claims` | Optional array: unique `id`, exact text `anchor` occurring in the draft, `status`, nonempty `boundary`, and `evidence` array of `source_id` plus nonempty `locator` into that source. |
| `protected_literals` | Optional array of `source_id` and exact `text` to preserve in both that readable source and the draft, e.g. an interval, denominator, or citation key. Select deliberately; do not copy every number mechanically. |
| `parent` | Optional `null` or prior packet's `path`/`sha256`. Must refer to version 1.0 of the same `paper_id` with a different nonempty `revision`; historical sources are not recursively rechecked or rewritten. |

All paths resolve relative to the packet's directory, not the process working directory; absolute paths are also accepted. Keep project-relative references where practical. SHA-256 binds bytes, not scientific correctness or ownership. Compute it from the actual file (for example with `Get-FileHash -Algorithm SHA256`, converting the hex to lower case); never type an invented digest or refresh one just to silence a changed-source warning.

Claim statuses:

- `supported`: directly grounded in the listed source(s).
- `interpretation`: a reasoned interpretation grounded in listed source(s), with explicit scope/alternatives in `boundary`.
- `planned`, `needs_evidence`, `disputed`: unresolved work/support/conflict, surfaced as warnings. These are legitimate draft states, not completed results.

Both supported and interpretation require at least one known source reference. A source can be author-provided without independent verification; record that limit in basis/boundary. A citation key's presence does not verify its bibliography or its support for the sentence.

## Run and interpret

From any directory:

```text
python <skill-root>/scripts/audit_manuscript.py <draft-dir>/manuscript-packet.json
```

The output includes `checks_passed`, listed file matches, errors, warnings, declared claim count, unresolved claim IDs, and an explicit capability boundary.

- Exit `0`: listed byte/anchor/literal checks passed. Read warnings: unresolved claims can remain. This is not scientific, editorial, citation, visual, permission, or submission approval.
- Exit `1`: a listed file is unavailable/changed, an anchor is absent, or a declared literal was lost/not present in its source.
- Exit `2`: malformed packet/JSON, bad references/shape/hash, invalid parent, or unreadable packet.

The auditor checks anchor presence, not uniqueness or meaning; locators are required text, not automatically dereferenced. Only listed files are covered. Bind relevant native inputs and run upstream native verification separately. A changed unlisted dependency may be invisible. Figures/DOCX/PDF may be fingerprinted as binary files, but anchor/literal checks require a real UTF-8 text representation. Hashing a binary artifact does not mean its content was read.

The auditor does not extract every number, compare causal language, verify proofs, authenticate research data, validate journal policy, or find missing citations. An incorrectly strengthened claim can pass if its declared strings/files match. Perform the evidence and consistency review even when checks pass. On drift, follow `references/project-integration.md`; do not automatically update sources, overwrite history, or mark the manuscript ready.

## Plain-text length checks

```text
python <skill-root>/scripts/text_metrics.py <selected-prose.txt> --unit han --min 180 --max 220
python <skill-root>/scripts/text_metrics.py <selected-prose.txt> --unit whitespace_words --max 250
```

`-` accepts stdin. `han` counts Unicode-named CJK unified/compatibility ideographs under the reported Python Unicode version, excluding Latin tokens, numbers, and punctuation. `whitespace_words` counts whitespace-delimited tokens; it is not a universal journal word count. Bounds are inclusive; exit `0` is within bounds, `1` outside, `2` invalid input. It counts exactly the supplied text, including any markup, headings, or notes; select/extract the intended prose first. A venue's own counting convention takes priority.
