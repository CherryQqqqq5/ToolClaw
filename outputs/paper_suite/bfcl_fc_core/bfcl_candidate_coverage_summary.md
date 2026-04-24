# BFCL Candidate Coverage Audit

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_candidate_coverage_audit_v1`
- runtime_diagnostics_gold_free: `True`

## Funnel Summary

| metric | value |
|---|---:|
| total_rows | 21455 |
| expected_in_raw_function_docs | 8125 |
| expected_in_prepared_schema | 8125 |
| expected_in_runtime_candidates | 3990 |
| expected_in_schema_top5 | 3990 |
| expected_is_schema_top1 | 3990 |
| selected_is_expected | 3990 |
| selected_expected_success | 262 |
| coverage_raw | 0.37869960382195295 |
| coverage_prepared | 0.37869960382195295 |
| coverage_runtime | 0.1859706362153344 |
| coverage_top5 | 0.1859706362153344 |
| ranker_top1 | 1.0 |
| selection_accuracy | 1.0 |
| arg_success_given_correct_tool | 0.06566416040100251 |

## Drop Stages

| drop_stage | count |
|---|---:|
| no_expected_function | 13330 |
| prepared_to_runtime_drop | 4135 |
| selected_correct_arg_or_shape_error | 3728 |
| selected_correct_success | 262 |

## By Case Type

| case_type | total | runtime coverage | top5 coverage | selected expected | top drop stage |
|---|---:|---:|---:|---:|---|
| live:parallel | 200 | 0.225 | 0.225 | 45 | no_expected_function |
| live:serial | 11055 | 0.09859791949344188 | 0.09859791949344188 | 1090 | no_expected_function |
| multi_turn:serial | 4000 | 0.0 | 0.0 | 0 | no_expected_function |
| non_live:parallel | 2000 | 0.4825 | 0.4825 | 965 | no_expected_function |
| non_live:serial | 4200 | 0.45 | 0.45 | 1890 | selected_correct_arg_or_shape_error |
