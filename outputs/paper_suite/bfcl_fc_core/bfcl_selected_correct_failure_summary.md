# BFCL Selected-Correct Failure Audit

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_selected_correct_failure_audit_v1`
- runtime_diagnostics_gold_free: `True`

## Summary

| metric | value |
|---|---:|
| selected_is_expected_count | 5120 |
| success_given_selected_is_expected | 592 |
| success_rate_given_selected_is_expected | 0.115625 |
| missing_required_given_selected_is_expected | 851 |
| wrong_arg_value_given_selected_is_expected | 820 |
| wrong_arg_type_given_selected_is_expected | 92 |
| wrong_arg_structure_given_selected_is_expected | 124 |
| wrong_call_count_given_selected_is_expected | 1704 |
| wrong_call_order_given_selected_is_expected | 0 |
| parallel_shape_error_given_selected_is_expected | 930 |
| multi_turn_state_error_given_selected_is_expected | 0 |
| wrong_call_count_missing_calls | 2027 |
| wrong_call_count_extra_calls | 620 |
| wrong_call_count_zero_emitted | 1574 |
| wrong_call_count_single_for_multiple | 395 |
| wrong_call_count_multiple_for_single | 0 |
| parallel_expected_but_serial_emitted | 395 |
| serial_expected_but_parallel_emitted | 0 |
| parallel_grouping_mismatch | 0 |
| parallel_call_count_correct_but_grouping_wrong | 0 |
| parallel_order_only_mismatch | 0 |
| trace_missing_or_unparseable_given_selected_is_expected | 0 |
| other_selected_correct_failure_given_selected_is_expected | 7 |

## Failure Buckets

| bucket | count |
|---|---:|
| missing_required | 851 |
| other_selected_correct_failure | 7 |
| parallel_shape_error | 930 |
| selected_correct_success | 592 |
| wrong_arg_structure | 124 |
| wrong_arg_type | 92 |
| wrong_arg_value | 820 |
| wrong_call_count | 1704 |

## By Case Type

| case_type | selected expected | success | top bucket |
|---|---:|---:|---|
| live:parallel | 60 | 10 | wrong_arg_value |
| live:serial | 1930 | 337 | wrong_call_count |
| multi_turn:serial | 0 | 0 | none |
| non_live:parallel | 995 | 15 | parallel_shape_error |
| non_live:serial | 2135 | 230 | wrong_call_count |
