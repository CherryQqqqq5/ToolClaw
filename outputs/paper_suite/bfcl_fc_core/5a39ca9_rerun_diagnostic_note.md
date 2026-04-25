# BFCL fc_core 5a39ca9 Rerun Diagnostic Note

## Provenance
- Commit: `5a39ca9f8edbeec4cafd0bc63df2c1fe67e065a3`
- Branch: `main`
- Command: `PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core`
- Output root: `outputs/paper_suite/bfcl_fc_core`
- Run-start worktree: clean by pre-run check; artifact files are dirty after rerun.
- Claim update: none. BFCL remains Case D / limitation.

## Gate Result
- `a2_wrong_func_name_le_a0`: True
- `a2_tool_selection_ge_a0`: True
- `a2_success_ge_a0`: False
- `a2_missing_required_lt_a0`: False
- `baseline_missing_required_slice_ready`: False
- `wrong_function_bucket_non_regression`: True
- `exact_function_guard_claim_ready`: False
- `a0_official_success`: 0.24726171055697974
- `a2_official_success`: 0.2419016546259613

## A2 Selected-Correct Movement
| metric | prior e79eb34 | 5a39ca9 |
| --- | ---: | ---: |
| `selected_is_expected_count` | 1024 | 1024 |
| `success_given_selected_is_expected` | 64 | 68 |
| `missing_required_given_selected_is_expected` | 436 | 371 |
| `wrong_arg_value_given_selected_is_expected` | 136 | 180 |
| `parallel_shape_error_given_selected_is_expected` | 195 | 195 |
| `wrong_call_count_given_selected_is_expected` | 171 | 171 |

Interpretation: the serial required-argument grounder produced the expected diagnostic migration. `missing_required` decreased and `wrong_arg_value` increased, with a small selected-correct success increase. This is progress in failure localization, not BFCL claim support, because official success non-regression still fails.

## A2 Missing-Required Subcauses
- `missing_required_due_to_no_query_cue`: 276
- `missing_required_due_to_schema_alias_mismatch`: 174
- `missing_required_due_to_grounder_not_attempted`: 5
- `missing_required_due_to_value_filtered`: 9
- `missing_required_due_to_final_answer_serializer_drop`: 0

## A2 Case-Type Breakdown
| case type | selected | success | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error | no_query_cue | schema_alias | grounder_not_attempted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `live:serial` | 386 | 28 | 105 | 95 | 141 | 0 | 64 | 40 | 0 |
| `non_live:serial` | 427 | 35 | 261 | 79 | 30 | 0 | 212 | 134 | 0 |
| `non_live:parallel` | 199 | 3 | 5 | 1 | 0 | 190 | 0 | 0 | 5 |
| `live:parallel` | 12 | 2 | 0 | 5 | 0 | 5 | 0 | 0 | 0 |

## Representative Traces
- `representative_traces/a2_serial_success_materialized_live_simple_0-0-0.json`: selected-correct serial success.
- `representative_traces/a2_serial_missing_required_materialized_live_simple_5-3-1.json`: selected-correct serial missing-required/no-query-cue example.
- `representative_traces/a2_serial_wrong_arg_value_materialized_live_simple_4-3-0.json`: selected-correct serial wrong-argument-value example.
- `representative_traces/a2_parallel_shape_remaining_parallel_2.json`: non-live parallel shape/missing-call example.

## Next Blocker
Do not tune planner override, candidate pool, or schema ranker from this result. The next useful BFCL work is:
1. Alias-aware and disambiguated serial argument assignment, especially for `schema_alias_mismatch`, `no_query_cue`, and over-broad quoted/list capture.
2. Separate non-live parallel clause/grouping materialization, because parallel rows remain dominated by `parallel_shape_error` and missing calls.

BFCL claim state remains unchanged: `planner_binding_headline` is a limitation, `bfcl_exact_function_guard` is not claim-ready, and `bfcl_missing_required_guarded_reduction` is unsupported for this suite because the baseline missing-required slice gate is not ready.
