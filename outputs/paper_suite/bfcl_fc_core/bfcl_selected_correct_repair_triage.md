# BFCL Selected-Correct Repair Triage

This scorer-side report chooses a narrow next runtime target from by-tool selected-correct failures. It does not change BFCL claim status.

- audit_schema_version: `bfcl_selected_correct_repair_triage_v1`
- claim_status_changed: `False`
- selection_rule: rank by selected_is_expected_count - selected_correct_success_count, then choose the top non-deferred tool::case_type with a plausible targeted repair bucket

## Recommended Target

| field | value |
|---|---|
| tool_case | get_current_weather::live:serial |
| tool_id | get_current_weather |
| case_type | live:serial |
| selected_correct_failure_count | 320 |
| selected_is_expected_count | 320 |
| selected_correct_success_count | 0 |
| dominant_failure_bucket | wrong_call_count |
| recommended_track | serial_call_count_canonicalization |
| missing_required_count | 15 |
| wrong_arg_value_count | 75 |
| wrong_call_count_count | 230 |
| parallel_shape_error_count | 0 |

## Top Tool/Case Offenders

| rank | tool_case | failures | selected expected | success | dominant bucket | track | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error |
|---:|---|---:|---:|---:|---|---|---:|---:|---:|---:|
| 1 | get_current_weather::live:serial | 320 | 320 | 0 | wrong_call_count | serial_call_count_canonicalization | 15 | 75 | 230 | 0 |
| 2 | requests.get::live:serial | 255 | 255 | 0 | wrong_call_count | serial_call_count_canonicalization | 25 | 0 | 200 | 0 |
| 3 | cmd_controller.execute::live:serial | 90 | 90 | 0 | wrong_arg_value | schema_alias_argument_repair | 30 | 50 | 0 | 0 |
| 4 | Weather_1_GetWeather::live:serial | 80 | 80 | 0 | missing_required | schema_alias_argument_repair | 75 | 5 | 0 | 0 |
| 5 | Movies_3_FindMovies::live:serial | 75 | 90 | 15 | missing_required | schema_alias_argument_repair | 40 | 35 | 0 | 0 |
| 6 | get_response::live:serial | 70 | 70 | 0 | wrong_call_count | serial_call_count_canonicalization | 0 | 0 | 70 | 0 |
| 7 | ThinQ_Connect::live:serial | 45 | 45 | 0 | wrong_arg_structure | schema_alias_argument_repair | 15 | 0 | 0 | 0 |
| 8 | getDataForProfessional::live:serial | 40 | 40 | 0 | wrong_call_count | serial_call_count_canonicalization | 15 | 0 | 25 | 0 |
| 9 | record::live:serial | 40 | 40 | 0 | wrong_arg_value | schema_alias_argument_repair | 0 | 35 | 5 | 0 |
| 10 | get_current_weather::live:parallel | 35 | 35 | 0 | wrong_arg_value | schema_alias_argument_repair | 0 | 20 | 0 | 15 |
| 11 | get_service_id::live:serial | 35 | 35 | 0 | missing_required | schema_alias_argument_repair | 30 | 0 | 5 | 0 |
| 12 | play_spotify_song::live:serial | 35 | 35 | 0 | wrong_arg_value | schema_alias_argument_repair | 0 | 35 | 0 | 0 |
| 13 | get_service_providers::live:serial | 30 | 30 | 0 | missing_required | schema_alias_argument_repair | 20 | 0 | 10 | 0 |
| 14 | todo::live:serial | 30 | 40 | 10 | wrong_arg_value | schema_alias_argument_repair | 0 | 30 | 0 | 0 |
| 15 | book_flight::live:serial | 25 | 25 | 0 | wrong_arg_value | schema_alias_argument_repair | 0 | 20 | 5 | 0 |
| 16 | detect_beats_and_filter::live:serial | 25 | 25 | 0 | missing_required | schema_alias_argument_repair | 10 | 0 | 5 | 0 |
| 17 | sitefinity_create_contentitem::live:serial | 25 | 25 | 0 | wrong_arg_value | schema_alias_argument_repair | 0 | 20 | 5 | 0 |
| 18 | answer.string::live:serial | 15 | 20 | 5 | wrong_arg_value | schema_alias_argument_repair | 0 | 15 | 0 | 0 |
| 19 | calculate_bmi::non_live:parallel | 15 | 15 | 0 | parallel_shape_error | parallel_argument_set_repair | 5 | 0 | 0 | 10 |
| 20 | calculate_compound_interest::non_live:serial | 15 | 15 | 0 | missing_required | schema_alias_argument_repair | 10 | 0 | 5 | 0 |
| 21 | calculate_sum::live:serial | 15 | 15 | 0 | wrong_call_count | serial_call_count_canonicalization | 5 | 0 | 10 | 0 |
| 22 | calculate_tax::live:serial | 15 | 15 | 0 | missing_required | schema_alias_argument_repair | 10 | 0 | 0 | 0 |
| 23 | get_items::live:serial | 15 | 15 | 0 | wrong_arg_value | schema_alias_argument_repair | 0 | 15 | 0 | 0 |
| 24 | get_stock_price::non_live:serial | 15 | 15 | 0 | missing_required | schema_alias_argument_repair | 10 | 5 | 0 | 0 |
| 25 | lawsuit_search::non_live:serial | 15 | 15 | 0 | missing_required | schema_alias_argument_repair | 5 | 5 | 5 | 0 |

## Deferred Tracks

- multi_turn
- no_expected_function
- broad_tool_selection
- claim_or_docs_update
