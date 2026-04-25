# BFCL Selected-Correct Failure Audit

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_selected_correct_failure_audit_v1`
- runtime_diagnostics_gold_free: `True`

## Summary

| metric | value |
|---|---:|
| selected_is_expected_count | 5120 |
| success_given_selected_is_expected | 407 |
| success_rate_given_selected_is_expected | 0.0794921875 |
| missing_required_given_selected_is_expected | 1810 |
| wrong_arg_value_given_selected_is_expected | 945 |
| wrong_arg_type_given_selected_is_expected | 155 |
| wrong_arg_structure_given_selected_is_expected | 85 |
| wrong_call_count_given_selected_is_expected | 855 |
| wrong_call_order_given_selected_is_expected | 0 |
| parallel_shape_error_given_selected_is_expected | 863 |
| multi_turn_state_error_given_selected_is_expected | 0 |
| wrong_call_count_missing_calls | 721 |
| wrong_call_count_extra_calls | 1017 |
| wrong_call_count_zero_emitted | 103 |
| wrong_call_count_single_for_multiple | 508 |
| wrong_call_count_multiple_for_single | 0 |
| parallel_expected_but_serial_emitted | 508 |
| serial_expected_but_parallel_emitted | 0 |
| parallel_grouping_mismatch | 0 |
| parallel_call_count_correct_but_grouping_wrong | 0 |
| parallel_order_only_mismatch | 0 |
| trace_missing_or_unparseable_given_selected_is_expected | 0 |
| other_selected_correct_failure_given_selected_is_expected | 0 |
| missing_required_due_to_no_query_cue | 1100 |
| missing_required_due_to_schema_alias_mismatch | 870 |
| missing_required_due_to_grounder_not_attempted | 155 |
| missing_required_due_to_value_filtered | 45 |
| missing_required_due_to_final_answer_serializer_drop | 0 |

## Failure Buckets

| bucket | count |
|---|---:|
| missing_required | 1810 |
| parallel_shape_error | 863 |
| selected_correct_success | 407 |
| wrong_arg_structure | 85 |
| wrong_arg_type | 155 |
| wrong_arg_value | 945 |
| wrong_call_count | 855 |

## By Case Type

| case_type | selected expected | success | top bucket |
|---|---:|---:|---|
| live:parallel | 60 | 0 | parallel_shape_error |
| live:serial | 1930 | 147 | wrong_call_count |
| multi_turn:serial | 0 | 0 | none |
| non_live:parallel | 995 | 10 | parallel_shape_error |
| non_live:serial | 2135 | 250 | missing_required |
