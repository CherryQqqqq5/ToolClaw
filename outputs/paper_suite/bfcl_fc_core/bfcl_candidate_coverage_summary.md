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
| expected_in_runtime_candidates | 4245 |
| expected_in_schema_top5 | 8125 |
| expected_is_schema_top1 | 8125 |
| selected_is_expected | 4245 |
| selected_expected_success | 302 |
| coverage_raw | 0.37869960382195295 |
| coverage_prepared | 0.37869960382195295 |
| coverage_runtime | 0.19785597762759263 |
| coverage_top5 | 0.37869960382195295 |
| ranker_top1 | 1.9140164899882215 |
| selection_accuracy | 1.0 |
| arg_success_given_correct_tool | 0.07114252061248527 |

## Drop Stages

| drop_stage | count |
|---|---:|
| bfcl_abstain_candidate_elision | 3880 |
| no_expected_function | 13330 |
| selected_correct_arg_or_shape_error | 3943 |
| selected_correct_success | 302 |

## By Case Type

| case_type | total | runtime coverage | top5 coverage | selected expected | top drop stage |
|---|---:|---:|---:|---:|---|
| live:parallel | 200 | 0.3 | 0.35 | 60 | no_expected_function |
| live:serial | 11055 | 0.10900045228403438 | 0.3487109905020353 | 1205 | no_expected_function |
| multi_turn:serial | 4000 | 0.0 | 0.0 | 0 | no_expected_function |
| non_live:parallel | 2000 | 0.4975 | 0.5 | 995 | no_expected_function |
| non_live:serial | 4200 | 0.4726190476190476 | 0.7619047619047619 | 1985 | selected_correct_arg_or_shape_error |
