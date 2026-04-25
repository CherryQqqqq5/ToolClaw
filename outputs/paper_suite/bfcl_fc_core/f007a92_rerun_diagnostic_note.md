# BFCL fc_core f007a92 Rerun Diagnostic Note

## Provenance
- Commit: `f007a9261cf343902d4d0ea23044188fcdc3f9ca`
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
- `a0_official_success`: 0.2535539501281753
- `a2_official_success`: 0.24819389419715684

## A2 Selected-Correct Movement
| metric | prior efbcf03 | f007a92 | delta |
| --- | ---: | ---: | ---: |
| `selected_is_expected_count` | 1024 | 1024 | 0 |
| `success_given_selected_is_expected` | 86 | 84 | -2 |
| `missing_required_given_selected_is_expected` | 323 | 337 | 14 |
| `wrong_arg_value_given_selected_is_expected` | 191 | 188 | -3 |
| `parallel_shape_error_given_selected_is_expected` | 195 | 195 | 0 |
| `wrong_call_count_given_selected_is_expected` | 171 | 171 | 0 |

Interpretation: value validation reduced `wrong_arg_value_given_selected_is_expected` slightly, but it also raised `missing_required_given_selected_is_expected` and reduced selected-correct success. This is a conservative-validation result, not claim support. It indicates the validation layer blocked some low-confidence assignments, but did not convert enough selected-correct rows into official successes.

## A2 Missing-Required Subcauses
- `missing_required_due_to_no_query_cue`: 221
- `missing_required_due_to_schema_alias_mismatch`: 174
- `missing_required_due_to_grounder_not_attempted`: 5
- `missing_required_due_to_value_filtered`: 9
- `missing_required_due_to_final_answer_serializer_drop`: 0

Compared with efbcf03, `missing_required_due_to_no_query_cue` increased from 205 to 221, while `schema_alias_mismatch` stayed at 174. The next serial blocker is not grounder path coverage or final-answer serialization; it is selective relaxation for high-evidence alias/type cases plus continued schema descriptor matching.

## A2 Case-Type Breakdown
| case type | selected | success | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error | wrong_arg_type | wrong_arg_structure | no_query_cue | schema_alias | grounder_not_attempted | value_filtered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `live:parallel` | 12 | 2 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| `live:serial` | 386 | 29 | 97 | 97 | 141 | 0 | 8 | 14 | 55 | 40 | 0 | 9 |
| `non_live:parallel` | 199 | 3 | 5 | 1 | 0 | 190 | 0 | 0 | 0 | 0 | 5 | 0 |
| `non_live:serial` | 427 | 50 | 235 | 85 | 30 | 0 | 24 | 3 | 166 | 134 | 0 | 0 |

## Candidate Coverage Snapshot
- `expected_in_prepared_schema`: 1625
- `expected_in_runtime_candidates`: 1024
- `expected_in_schema_top5`: 1625
- `expected_is_schema_top1`: 1625
- `selected_is_expected`: 1024
- `selected_expected_success`: 84

## Representative Traces
- `representative_traces/a2_serial_success_value_validation_live_relevance_2-2-0.json`: selected-correct serial success after value validation.
- `representative_traces/a2_serial_missing_required_value_validation_live_simple_5-3-1.json`: selected-correct serial missing-required after value validation.
- `representative_traces/a2_serial_wrong_arg_value_value_validation_live_simple_4-3-0.json`: selected-correct serial wrong-argument-value after value validation.
- `representative_traces/a2_non_live_parallel_shape_value_validation_parallel_2.json`: parallel shape blocker unchanged by serial-only validation.

## Next Blocker
Do not tune planner override, candidate pool, schema ranker, serial materialization, schema preflight, or final-answer serialization from this result. The f007a92 validation patch made value assignment more conservative, slightly reducing wrong-argument-value but increasing missing-required and reducing selected-correct success.

The next useful BFCL work is targeted relaxation of high-evidence serial assignments, especially where schema descriptors, exact type cues, or parameter-name-specific `from`/`to` evidence exist. Do not restore broad quoted-string or broad `from`/`to` alias fallback. Parallel remains a separate blocker dominated by `parallel_shape_error` and should be handled in a separate patch.

BFCL claim state remains unchanged: `planner_binding_headline` is a limitation, `bfcl_exact_function_guard` is not claim-ready because success non-regression fails, and `bfcl_missing_required_guarded_reduction` remains unsupported because its slice gate still fails.
