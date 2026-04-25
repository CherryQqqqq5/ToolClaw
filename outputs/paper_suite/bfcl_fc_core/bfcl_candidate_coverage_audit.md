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
| expected_in_runtime_candidates | 5120 |
| expected_in_schema_top5 | 8125 |
| expected_is_schema_top1 | 8125 |
| selected_is_expected | 5120 |
| selected_expected_success | 342 |
| coverage_raw | 0.37869960382195295 |
| coverage_prepared | 0.37869960382195295 |
| coverage_runtime | 0.23863901188534142 |
| coverage_top5 | 0.37869960382195295 |
| ranker_top1 | 1.5869140625 |
| selection_accuracy | 1.0 |
| arg_success_given_correct_tool | 0.066796875 |

## Drop Stages

| drop_stage | count |
|---|---:|
| bfcl_abstain_candidate_elision | 3005 |
| no_expected_function | 13330 |
| selected_correct_arg_or_shape_error | 4778 |
| selected_correct_success | 342 |

## By Case Type

| case_type | total | runtime coverage | top5 coverage | selected expected | top drop stage |
|---|---:|---:|---:|---:|---|
| live:parallel | 200 | 0.3 | 0.35 | 60 | no_expected_function |
| live:serial | 11055 | 0.17458163726820444 | 0.3487109905020353 | 1930 | no_expected_function |
| multi_turn:serial | 4000 | 0.0 | 0.0 | 0 | no_expected_function |
| non_live:parallel | 2000 | 0.4975 | 0.5 | 995 | no_expected_function |
| non_live:serial | 4200 | 0.5083333333333333 | 0.7619047619047619 | 2135 | selected_correct_arg_or_shape_error |
