# BFCL fc_core cfefc07 Rerun Diagnostic Note

## Provenance
- Git commit: `cfefc07e636eba1cd98b2425fa6141ac3a6f4f36`
- Branch: `main`
- Suite command: `PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core`
- Output root: `outputs/paper_suite/bfcl_fc_core`
- Claim update: none

## Claim Gates
- `a2_wrong_func_name_le_a0`: `True`
- `a2_tool_selection_ge_a0`: `True`
- `a2_success_ge_a0`: `False`
- `a2_missing_required_lt_a0`: `False`
- `baseline_missing_required_slice_ready`: `False`
- `wrong_function_bucket_non_regression`: `True`
- `exact_function_guard_claim_ready`: `False`
- `a2_guarded_missing_required_rate_lt_a0`: `False`
- `a2_guarded_wrong_func_name_rate_le_a0`: `True`
- `a2_guarded_success_rate_ge_a0`: `True`
- `a0_official_success`: `0.2535539501281753`
- `a2_official_success`: `0.24819389419715684`

Interpretation: BFCL remains Case D. Wrong-function and tool-selection non-regression hold, but success non-regression does not. No BFCL claim is upgraded.

## A2 Candidate And Selection Coverage
- `expected_in_prepared_schema`: `1625`
- `expected_in_runtime_candidates`: `1024`
- `expected_in_schema_top5`: `1625`
- `expected_is_schema_top1`: `1625`
- `selected_is_expected`: `1024`
- `selected_expected_success`: `84`

## A2 Selected-Correct Movement
Compared against the `f007a92` baseline:

| Metric | f007a92 | cfefc07 | Movement |
|---|---:|---:|---:|
| `selected_is_expected_count` | 1024 | 1024 | 0 |
| `success_given_selected_is_expected` | 84 | 84 | 0 |
| `missing_required_given_selected_is_expected` | 337 | 336 | -1 |
| `wrong_arg_value_given_selected_is_expected` | 188 | 190 | 2 |
| `parallel_shape_error_given_selected_is_expected` | 195 | 195 | 0 |
| `wrong_call_count_given_selected_is_expected` | 171 | 171 | 0 |

The high-evidence relaxation did not improve selected-correct success. It reduced missing-required by one row but increased wrong-argument-value by two rows, so it is diagnostic-only evidence, not claim support.

## Missing-Required Subcauses
- `missing_required_due_to_no_query_cue`: `220`
- `missing_required_due_to_schema_alias_mismatch`: `174`
- `missing_required_due_to_grounder_not_attempted`: `5`
- `missing_required_due_to_value_filtered`: `9`
- `missing_required_due_to_final_answer_serializer_drop`: `0`

The dominant remaining serial blockers are low-evidence/no-query-cue rows and schema alias mismatch. Grounder coverage and final-answer serialization are not primary blockers in this rerun.

## A2 Case-Type Breakdown
- `a2_planner::live:serial`: selected=`386`, success=`29`, buckets=`{'wrong_call_count': 141, 'selected_correct_success': 29, 'wrong_arg_value': 99, 'missing_required': 96, 'wrong_arg_structure': 14, 'wrong_arg_type': 7}`, missing_required_subcauses=`{'missing_required_due_to_no_query_cue': 54, 'missing_required_due_to_schema_alias_mismatch': 40, 'missing_required_due_to_value_filtered': 9}`
- `a2_planner::non_live:serial`: selected=`427`, success=`50`, buckets=`{'wrong_call_count': 30, 'selected_correct_success': 50, 'wrong_arg_value': 85, 'missing_required': 235, 'wrong_arg_type': 24, 'wrong_arg_structure': 3}`, missing_required_subcauses=`{'missing_required_due_to_no_query_cue': 166, 'missing_required_due_to_schema_alias_mismatch': 134}`
- `a2_planner::non_live:parallel`: selected=`199`, success=`3`, buckets=`{'selected_correct_success': 3, 'parallel_shape_error': 190, 'wrong_arg_value': 1, 'missing_required': 5}`, missing_required_subcauses=`{'missing_required_due_to_grounder_not_attempted': 5}`
- `a2_planner::live:parallel`: selected=`12`, success=`2`, buckets=`{'wrong_arg_value': 5, 'parallel_shape_error': 5, 'selected_correct_success': 2}`, missing_required_subcauses=`{}`
- `a2_planner::multi_turn:serial`: selected=`0`, success=`0`, buckets=`{}`, missing_required_subcauses=`{}`

## High-Evidence Assignment Reasons Observed In A2 Traces
- `numeric_type_cue`: `330`
- `descriptor_from_preposition`: `16`
- `array_local_argument_cue`: `11`
- `descriptor_to_preposition`: `11`
- `boolean_descriptor_cue`: `10`
- `email_type_cue`: `4`
- `enum_normalized_mention`: `3`

These diagnostics are present in runtime trace metadata and remain gold-free. The row-level scorer artifacts do not currently aggregate them into selected-correct success/failure attribution, so future work should aggregate high-evidence reason effectiveness if this path is revisited.

## Next Blocker
Do not broaden generic fallback filling. The next useful BFCL work is either targeted schema alias/descriptor mapping for non-live serial rows with observable cues, or a separate non-live parallel clause/grouping materialization patch. Since high-evidence serial relaxation did not move success, parallel shape repair is now a stronger candidate for the next intervention.
