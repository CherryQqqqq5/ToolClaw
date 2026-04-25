# BFCL fc_core 21e70bf Full Rerun Diagnostic Note

## Provenance

- Commit: `21e70bf919aba027b6826066dc6f4e87fbcda04f`
- Branch: `main`
- Command: `PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core`
- Output root: `outputs/paper_suite/bfcl_fc_core`
- Scope: evaluate BFCL non-live parallel clause materialization repair.
- Claim update: none. BFCL remains Case D / limitation because the success non-regression gate is still false.

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
| `full_suite_supporting_ready` | `False` |

## Official Scores

| System | Success | Tool Selection | Structure |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.252855 | 0.615668 | 0.602191 |
| `a2_planner` | 0.247495 | 0.615766 | 0.602657 |
| `a3_interaction` | 0.247961 | 0.653476 | 0.611979 |
| `a4_reuse` | 0.247961 | 0.653476 | 0.611979 |

A2 remains below A0 on official success, so the exact-function/call-materialization diagnostic claim is not claim-ready.

## A2 Selected-Correct Movement vs cfefc07 Baseline

| Metric | cfefc07 baseline | 21e70bf | Direction |
| --- | ---: | ---: | --- |
| `success_given_selected_is_expected` | 84 | 81 | down |
| `parallel_shape_error_given_selected_is_expected` | 195 | 200 | up |
| `wrong_call_count_given_selected_is_expected` | 171 | 171 | flat |
| `parallel_expected_but_serial_emitted` | 41 | 31 | down |
| `wrong_call_count_missing_calls` | n/a | 195 | diagnostic only |
| `parallel_argument_sets_extracted` | n/a | 90 | diagnostic only |
| `parallel_argument_set_count` | n/a | 307 | diagnostic only |
| `parallel_clause_materialized_count` | n/a | 307 | diagnostic only |
| `parallel_collapsed_to_serial` | n/a | 0 | diagnostic only |

## A2 non_live:parallel

| Metric | Value |
| --- | ---: |
| `selected_is_expected_count` | 199 |
| `success_given_selected_is_expected` | 2 |
| `parallel_shape_error_given_selected_is_expected` | 192 |
| `wrong_call_count_missing_calls` | 190 |
| `parallel_expected_but_serial_emitted` | 31 |
| `wrong_call_count_zero_emitted` | 155 |
| `parallel_argument_sets_extracted` | 81 |
| `parallel_argument_set_count` | 281 |
| `parallel_clause_materialized_count` | 281 |
| `parallel_clause_drop_count` | 0 |
| `parallel_collapsed_to_serial` | 0 |

## Interpretation

- The non-live parallel repair did not produce the desired success movement. A2 selected-correct success decreased from 84 to 81 overall, and `a2_planner::non_live:parallel` success is 2 out of 199 selected-correct rows.
- The patch reduced A2 `parallel_expected_but_serial_emitted` from 41 to 31, so serial collapse improved, but `parallel_shape_error` increased from 195 to 200 overall and from the prior non-live parallel baseline of 190 to 192.
- Runtime diagnostics show the new path is active: A2 extracted parallel argument sets on 90 rows and materialized 307 clause-level calls. For `non_live:parallel`, 81 rows extracted sets and 281 clauses were materialized.
- Many failing non-live parallel rows still have zero scorer-visible calls even when argument sets were extracted and materialized in diagnostics. Representative example: `parallel_4` has 2 extracted/materialized clauses but 0 trace/scorer-visible tool calls.
- The next blocker is not candidate visibility, ranker ordering, or serial grounding. It is the bridge from parallel argument-set materialization metadata to scorer-visible trace/final calls, plus alignment with official parallel grouping expectations.

## Representative Traces

- `outputs/paper_suite/bfcl_fc_core/representative_traces/21e70bf_a2_non_live_parallel_success_parallel_0.json`
- `outputs/paper_suite/bfcl_fc_core/representative_traces/21e70bf_a2_non_live_parallel_shape_zero_emitted_parallel_4.json`
- `outputs/paper_suite/bfcl_fc_core/representative_traces/21e70bf_a2_non_live_parallel_serial_collapse_parallel_25.json`

## Next Step

Do not upgrade BFCL claims. Before another broad parallel patch, audit rows where `parallel_argument_sets_extracted=true` and `parallel_clause_materialized_count>0` but `trace_metric_tool_calls=0` or `emitted_call_count=0`; this will distinguish materializer metadata-only success from actual scorer-visible call emission.
