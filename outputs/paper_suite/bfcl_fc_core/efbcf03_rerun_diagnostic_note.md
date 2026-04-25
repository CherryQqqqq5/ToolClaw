# BFCL fc_core efbcf03 Rerun Diagnostic Note

## Provenance
- Commit: `efbcf039c0c51bf26a088db907e1a8169e1ef052`
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
- `missing_required_reduction_ready`: False
- `full_suite_supporting_ready`: False
- `a0_official_success`: 0.2542530878583081
- `a2_official_success`: 0.24889303192728968

## A2 Selected-Correct Movement
| metric | prior 5a39ca9 | efbcf03 | delta |
| --- | ---: | ---: | ---: |
| `selected_is_expected_count` | 1024 | 1024 | 0 |
| `success_given_selected_is_expected` | 68 | 86 | 18 |
| `missing_required_given_selected_is_expected` | 371 | 323 | -48 |
| `wrong_arg_value_given_selected_is_expected` | 180 | 191 | 11 |
| `parallel_shape_error_given_selected_is_expected` | 195 | 195 | 0 |
| `wrong_call_count_given_selected_is_expected` | 171 | 171 | 0 |

Interpretation: alias-aware serial assignment moved the selected-correct serial layer in the intended direction. Missing-required failures decreased and selected-correct successes increased, while wrong-argument-value rose only modestly. This is diagnostic progress, not claim support, because official `a2_success_ge_a0` remains false.

## A2 Missing-Required Subcauses
- `missing_required_due_to_no_query_cue`: 205
- `missing_required_due_to_schema_alias_mismatch`: 174
- `missing_required_due_to_grounder_not_attempted`: 5
- `missing_required_due_to_value_filtered`: 9
- `missing_required_due_to_final_answer_serializer_drop`: 0

Compared with 5a39ca9, `missing_required_due_to_no_query_cue` decreased from 276 to 205, while `schema_alias_mismatch` stayed at 174. The next serial blocker is therefore alias/descriptor coverage plus value validation, not grounder path coverage or final-answer serialization.

## A2 Case-Type Breakdown
| case type | selected | success | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error | wrong_arg_type | wrong_arg_structure | no_query_cue | schema_alias | grounder_not_attempted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `live:parallel` | 12 | 2 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| `live:serial` | 386 | 29 | 88 | 98 | 141 | 0 | 14 | 16 | 45 | 40 | 0 |
| `non_live:parallel` | 199 | 3 | 5 | 1 | 0 | 190 | 0 | 0 | 0 | 0 | 5 |
| `non_live:serial` | 427 | 52 | 230 | 87 | 30 | 0 | 25 | 3 | 160 | 134 | 0 |

## Candidate Coverage Snapshot
- `expected_in_prepared_schema`: 1625
- `expected_in_runtime_candidates`: 1024
- `expected_in_schema_top5`: 1625
- `expected_is_schema_top1`: 1625
- `selected_is_expected`: 1024
- `selected_expected_success`: 86

## Representative Traces
- `representative_traces/a2_serial_success_materialized_live_simple_0-0-0.json`: selected-correct serial success.
- `representative_traces/a2_serial_missing_required_materialized_live_simple_5-3-1.json`: selected-correct serial missing-required example.
- `representative_traces/a2_serial_wrong_arg_value_materialized_live_simple_4-3-0.json`: selected-correct serial wrong-argument-value example.
- `representative_traces/a2_parallel_shape_remaining_live_parallel_3-0-3.json`: live parallel shape/missing-call example.

## Next Blocker
Do not tune planner override, candidate pool, schema ranker, serial materialization, or final-answer serialization from this result. The serial v2 assignment patch improved the selected-correct layer, but BFCL remains below the official success baseline. The next useful BFCL work is either alias/descriptor-aware value validation for serial rows, because `schema_alias_mismatch` remains unchanged, or separate non-live parallel clause/grouping materialization, because parallel rows remain dominated by `parallel_shape_error`.

BFCL claim state remains unchanged: `planner_binding_headline` is a limitation, `bfcl_exact_function_guard` is not claim-ready because success non-regression fails, and `bfcl_missing_required_guarded_reduction` remains unsupported.
