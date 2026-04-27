# ToolSandbox Core Strict Failure Taxonomy - 2026-04-27

## Verdict

The strict core failures are not runtime execution failures in the current formal bundle. The `s4_reuse_overlay` failures are executor-success / strict-benchmark failures concentrated in interaction-required rows where the strict ladder does not ask a user question.

This is a diagnostic note only. It does not change claims, runtime behavior, scorer behavior, datasets, or reuse evidence.

## Source

- source bundle: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict`
- comparison file: `comparison.scored.csv`
- taxonomy artifacts:
  - `strict_s4_failure_taxonomy.json`
  - `strict_s4_failure_taxonomy.md`
- target system: `s4_reuse_overlay`
- analyzer: `scripts/analyze_toolsandbox_strict_failures.py`

## Summary

| metric | value |
|---|---:|
| `s4` failed scored rows | 357 |
| unique failed tasks | 119 |
| raw success but strict fail | 357 |
| runtime execution failures | 0 |
| first failed layer | `s0_baseline` for 357 rows |
| candidate owning layer | `s3_interaction_overlay` for 357 rows |

## Failure Categories

| category | count | interpretation |
|---|---:|---|
| `interaction_trigger_or_decoder_gap` | 357 | The executor completed with `success_criteria_satisfied`, but strict scoring still failed on interaction-requiring rows with no user-query path. |

## Implication

The next likely high-value implementation line is generic interaction repair expansion, not ToolSandbox-specific recovery templates. The failure pattern points to interaction trigger/query/decoder coverage for missing or underspecified user-provided information.

Do not patch using scenario names, task IDs, ToolSandbox tool names, or milestone-specific logic. Any follow-up should remain schema- and evidence-driven:

- trigger interaction only when lower layers are blocked or when required information is unresolved
- generate questions from generic repair metadata such as missing targets, state slot, failed tool, and expected answer type
- decode generic reply types such as approval, scalar value, date/time, phone/email, path, entity reference, and state toggle
- preserve the strict no-op guard on already-solvable tasks

## Boundary

This taxonomy does not weaken the strict ladder result: adjacent strict-layer regressions remain zero. It identifies remaining broad-core headroom for future generic interaction work. Reuse remains supported by `toolsandbox_reuse_persistent_v3`, not by single-run `s4` core success.
