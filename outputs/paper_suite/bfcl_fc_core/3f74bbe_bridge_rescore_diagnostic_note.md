# BFCL fc_core 3f74bbe Bridge Rescore Diagnostic Note

## Provenance

- Full executor run commit: `21e70bf919aba027b6826066dc6f4e87fbcda04f`
- Scorer/audit commit: `3f74bbec8731ffe5b22145c323c66ad8d4d59c9a`
- Branch: `main`
- Command: `PYTHONPATH=src python3 scripts/score_bfcl_outputs.py --outdir outputs/paper_suite/bfcl_fc_core --official-eval true --toolclaw-diagnostics true`
- Executor was not rerun; this rescore reuses existing `outputs/paper_suite/bfcl_fc_core/runs/run_01/traces`.
- Claim update: none. BFCL remains Case D / limitation because `a2_success_ge_a0=false`.

## Claim Gates

| Gate | Value |
| --- | --- |
| `a2_wrong_func_name_le_a0` | `True` |
| `a2_tool_selection_ge_a0` | `True` |
| `a2_success_ge_a0` | `False` |
| `a2_missing_required_lt_a0` | `False` |
| `wrong_function_bucket_non_regression` | `True` |
| `exact_function_guard_claim_ready` | `False` |
| `baseline_missing_required_slice_ready` | `False` |

## Official Scores

| System | Success | Tool Selection | Structure |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.252855 | 0.615668 | 0.602191 |
| `a2_planner` | 0.247495 | 0.615766 | 0.602657 |
| `a3_interaction` | 0.247961 | 0.653476 | 0.611979 |
| `a4_reuse` | 0.247961 | 0.653476 | 0.611979 |

## A2 Parallel Bridge Summary

| Metric | A2 overall | A2 non_live:parallel |
| --- | ---: | ---: |
| `parallel_argument_sets_extracted` | 90 | 81 |
| `parallel_argument_set_count` | 307 | 281 |
| `parallel_clause_materialized_count` | 307 | 281 |
| `materialized_gt0_trace0` | 69 | 67 |
| `trace_gt0_emitted0` | 0 | 0 |
| `emitted_gt0_wrong_count` | 40 | 37 |
| `emitted_count_correct_wrong_grouping` | 0 | 0 |
| `parallel_workflow_steps_built_but_preflight_blocked` | 69 | 67 |
| `parallel_workflow_steps_built_but_not_executed` | 0 | 0 |
| `parallel_tool_calls_in_trace_but_not_in_emitted_answer` | 0 | 0 |
| `parallel_emitted_calls_wrong_count` | 131 | 125 |
| `parallel_emitted_calls_but_wrong_official_grouping` | 0 | 0 |
| `parallel_emitted_calls_wrong_args` | 9 | 5 |
| `parallel_emitted_calls_success` | 2 | 2 |

## Bridge Stage Counts

A2 overall:

- `parallel_emitted_calls_success`: 2
- `parallel_emitted_calls_wrong_args`: 9
- `parallel_emitted_calls_wrong_count`: 131
- `parallel_workflow_steps_built_but_preflight_blocked`: 69

A2 non_live:parallel:

- `parallel_emitted_calls_success`: 2
- `parallel_emitted_calls_wrong_args`: 5
- `parallel_emitted_calls_wrong_count`: 125
- `parallel_workflow_steps_built_but_preflight_blocked`: 67

## Interpretation

- The dominant bridge bucket is `parallel_emitted_calls_wrong_count`: 131 for A2 overall and 125 for `a2_planner::non_live:parallel`. This means many rows do reach scorer-visible emitted calls, but the emitted count still does not match official expected count.
- The second blocker is `parallel_workflow_steps_built_but_preflight_blocked`: 69 for A2 overall and 67 for `non_live:parallel`. These are rows where materialized workflow steps exist but executor preflight blocks before tool calls, usually due missing required inputs.
- `parallel_tool_calls_in_trace_but_not_in_emitted_answer` is 0, so the main issue is not trace-to-answer extraction.
- `parallel_emitted_calls_but_wrong_official_grouping` is 0 under the current grouping heuristic, so grouping is not yet the dominant diagnosed stage.

## Next Step

Prioritize two focused repairs, in order: first audit/fix parallel emitted call count alignment for rows with scorer-visible calls; second apply a BFCL-parallel equivalent of serial partial-call materialization for rows blocked by preflight. Do not tune extraction patterns until emitted-count and preflight stages are addressed.
