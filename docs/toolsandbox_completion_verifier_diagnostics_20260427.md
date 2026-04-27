# ToolSandbox Completion Verifier Diagnostics - 2026-04-27

## Verdict

The gold-free completion verifier was added as diagnostics only. It does not change executor success, stop reasons, repair flow, interaction flow, scorer behavior, claims, or datasets.

On a 405-sample strict 1-run smoke, the verifier diagnostics preserve strict adjacent non-regression and explain the remaining `s4` raw-success / strict-fail rows as finalization evidence gaps rather than runtime execution failures.

## Smoke Source

- source: `data/toolsandbox.official_core_reproducible.frozen.json`
- outdir: `outputs/paper_suite/toolsandbox_official_core_reproducible_completion_verifier_smoke`
- systems: `s0_baseline,s1_recovery,s2_planner_overlay,s3_interaction_overlay,s4_reuse_overlay`
- runs: `1`

## Results

| metric | value |
|---|---:|
| samples | 405 |
| strict adjacent comparisons | 1620 |
| strict adjacent regressions | 0 |
| traces with completion verifier events | 2004 |
| `s4` failed rows | 119 |
| unique failed tasks | 119 |
| raw success but strict fail | 119 |
| runtime execution failures | 0 |

## Failure Subcause

| subcause | count | interpretation |
|---|---:|---|
| `final_response_milestone_gap` | 119 | The executor completed, but verifier diagnostics identify insufficient task-relevant finalization evidence before strict scoring. |

## Next Implementation Direction

The next behavior-changing patch should not target planner, reuse, or ToolSandbox-specific rules. The evidence points to a generic finalization layer:

- synthesize a final response from task goal, completed tool results, and state patches
- keep all synthesis gold-free and runtime-visible
- preserve no-op behavior on already-solvable tasks
- run strict smoke and require adjacent regression count `0`

Interaction expansion remains secondary: the current verifier smoke points first to finalization evidence, not runtime failure.

## Boundary

This note is diagnostic. It does not promote a new claim and does not alter the current strict ladder, semantic repair, planner-sensitive, reuse v3, or BFCL evidence boundaries.
