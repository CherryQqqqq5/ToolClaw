# BFCL Selected-Correct Failure Audit

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_selected_correct_failure_audit_v1`
- runtime_diagnostics_gold_free: `True`

## Summary

| metric | value |
|---|---:|
| selected_is_expected_count | 5120 |
| success_given_selected_is_expected | 342 |
| success_rate_given_selected_is_expected | 0.066796875 |
| missing_required_given_selected_is_expected | 1880 |
| wrong_arg_value_given_selected_is_expected | 908 |
| wrong_arg_type_given_selected_is_expected | 119 |
| wrong_arg_structure_given_selected_is_expected | 86 |
| wrong_call_count_given_selected_is_expected | 855 |
| wrong_call_order_given_selected_is_expected | 0 |
| parallel_shape_error_given_selected_is_expected | 930 |
| multi_turn_state_error_given_selected_is_expected | 0 |
| wrong_call_count_missing_calls | 901 |
| wrong_call_count_extra_calls | 904 |
| wrong_call_count_zero_emitted | 448 |
| wrong_call_count_single_for_multiple | 395 |
| wrong_call_count_multiple_for_single | 0 |
| parallel_expected_but_serial_emitted | 395 |
| serial_expected_but_parallel_emitted | 0 |
| parallel_grouping_mismatch | 0 |
| parallel_call_count_correct_but_grouping_wrong | 0 |
| parallel_order_only_mismatch | 0 |
| trace_missing_or_unparseable_given_selected_is_expected | 0 |
| other_selected_correct_failure_given_selected_is_expected | 0 |
| missing_required_due_to_no_query_cue | 1380 |
| missing_required_due_to_schema_alias_mismatch | 870 |
| missing_required_due_to_grounder_not_attempted | 50 |
| missing_required_due_to_value_filtered | 45 |
| missing_required_due_to_final_answer_serializer_drop | 0 |

## Failure Buckets

| bucket | count |
|---|---:|
| missing_required | 1880 |
| parallel_shape_error | 930 |
| selected_correct_success | 342 |
| wrong_arg_structure | 86 |
| wrong_arg_type | 119 |
| wrong_arg_value | 908 |
| wrong_call_count | 855 |

## By Case Type

| case_type | selected expected | success | top bucket |
|---|---:|---:|---|
| live:parallel | 60 | 10 | wrong_arg_value |
| live:serial | 1930 | 142 | wrong_call_count |
| multi_turn:serial | 0 | 0 | none |
| non_live:parallel | 995 | 15 | parallel_shape_error |
| non_live:serial | 2135 | 175 | missing_required |
