# BFCL fc_core 36751d0 Rerun Diagnostic Note

## Provenance
- Commit: `36751d0f0febfc455105d8c41f491593166ab2a3`
- Command: `PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core`
- Output root: `outputs/paper_suite/bfcl_fc_core`
- Claim update: none. BFCL remains limitation/unsupported because success and missing-required gates did not pass.

## Primary Result
The serial selected-call materialization patch worked as a diagnostic repair, but did not make BFCL claim-supporting.

A2 selected-correct migration versus the prior baseline:

| Metric | Prior | 36751d0 rerun | Interpretation |
|---|---:|---:|---|
| `wrong_call_count_zero_emitted` | 524 | 149 | materially reduced |
| `zero_emitted_after_schema_selection` | 524 | 149 | materially reduced |
| `zero_emitted_due_to_call_shape_canonicalizer` | 375 | 0 | serial/canonicalizer suppression removed |
| `wrong_call_count_missing_calls` | 569 | 194 | materially reduced |
| `selected_correct_success` | 154 | 64 | did not improve; more rows now fail in argument/shape buckets |

A2 selected-correct failure buckets after rerun:

| Bucket | Count |
|---|---:|
| `missing_required_given_selected_is_expected` | 436 |
| `parallel_shape_error_given_selected_is_expected` | 195 |
| `wrong_call_count_given_selected_is_expected` | 171 |
| `wrong_arg_value_given_selected_is_expected` | 136 |
| `wrong_arg_structure_given_selected_is_expected` | 14 |
| `wrong_arg_type_given_selected_is_expected` | 8 |

## Case-Type Diagnosis
For A2 selected-correct rows:

| Case type | Selected | Success | Main blocker |
|---|---:|---:|---|
| `live:serial` | 386 | 28 | missing required / wrong arg value / residual wrong call count |
| `non_live:serial` | 427 | 31 | missing required dominates |
| `non_live:parallel` | 199 | 3 | parallel shape and missing calls dominate |
| `live:parallel` | 12 | 2 | parallel shape / wrong arg value |

Serial rows now show `trace_metric_tool_calls == selected` for both `live:serial` and `non_live:serial`, so the immediate no-call suppression path is no longer the primary serial blocker. Parallel rows remain under-materialized and still require a separate parallel clause/grouping repair.

## Claim Gates
- `a2_wrong_func_name_le_a0 = true`
- `a2_tool_selection_ge_a0 = true`
- `a2_success_ge_a0 = false`
- `a2_missing_required_lt_a0 = false`
- `baseline_missing_required_slice_ready = false`
- `wrong_function_bucket_non_regression = true`
- `exact_function_guard_claim_ready = false`

Interpretation: wrong-function regression remains controlled, but BFCL is still Case D. No BFCL claim should be upgraded.

## Next Blocker
The next BFCL work should not tune planner override, candidate pool, or schema ranker weights. The dominant remaining blockers are:

1. Serial argument grounding: missing required and wrong argument values after the selected function is materialized.
2. Non-live parallel call materialization: parallel rows still lose clause calls or collapse shape.

Recommended next patch: repair non-live parallel clause expansion/grouping separately, then address serial argument grounding/value normalization.

## Representative Traces
- `representative_traces/a2_serial_success_materialized_live_simple_0-0-0.json`
- `representative_traces/a2_serial_missing_required_materialized_live_simple_5-3-1.json`
- `representative_traces/a2_serial_wrong_arg_value_materialized_live_simple_4-3-0.json`
- `representative_traces/a2_parallel_shape_remaining_parallel_2.json`
