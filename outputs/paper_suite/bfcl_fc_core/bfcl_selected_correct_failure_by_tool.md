# BFCL Selected-Correct Failure By Tool

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_selected_correct_failure_by_tool_v1`
- runtime_diagnostics_gold_free: `True`

## Top Tools By Selected-Correct Failures

| tool | selected expected | success | selected_correct_rows | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error |
|---|---:|---:|---:|---:|---:|---:|---:|
| get_current_weather | 365 | 5 | 365 | 15 | 95 | 230 | 20 |
| requests.get | 255 | 0 | 255 | 25 | 0 | 200 | 0 |
| cmd_controller.execute | 90 | 0 | 90 | 30 | 50 | 0 | 0 |
| Movies_3_FindMovies | 90 | 15 | 90 | 40 | 35 | 0 | 0 |
| Weather_1_GetWeather | 80 | 0 | 80 | 75 | 5 | 0 | 0 |
| get_response | 70 | 0 | 70 | 0 | 0 | 70 | 0 |
| todo | 45 | 10 | 45 | 0 | 32 | 0 | 3 |
| ThinQ_Connect | 45 | 0 | 45 | 15 | 0 | 0 | 0 |
| record | 40 | 0 | 40 | 0 | 35 | 5 | 0 |
| getDataForProfessional | 40 | 0 | 40 | 15 | 0 | 25 | 0 |
| play_spotify_song | 35 | 0 | 35 | 0 | 35 | 0 | 0 |
| get_service_id | 35 | 0 | 35 | 30 | 0 | 5 | 0 |
| get_service_providers | 30 | 0 | 30 | 20 | 0 | 10 | 0 |
| calculate_bmi | 30 | 10 | 30 | 5 | 5 | 0 | 10 |
| book_flight | 30 | 0 | 30 | 0 | 20 | 5 | 5 |
| sitefinity_create_contentitem | 25 | 0 | 25 | 0 | 20 | 5 | 0 |
| math.gcd | 25 | 15 | 25 | 0 | 0 | 0 | 10 |
| math.factorial | 25 | 10 | 25 | 0 | 0 | 0 | 15 |
| get_stock_price | 25 | 0 | 25 | 10 | 5 | 0 | 10 |
| detect_beats_and_filter | 25 | 0 | 25 | 10 | 0 | 5 | 0 |

## Top Tools By Missing Required

| tool | selected expected | success | missing_required | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error |
|---|---:|---:|---:|---:|---:|---:|---:|
| Weather_1_GetWeather | 80 | 0 | 75 | 75 | 5 | 0 | 0 |
| Movies_3_FindMovies | 90 | 15 | 40 | 40 | 35 | 0 | 0 |
| cmd_controller.execute | 90 | 0 | 30 | 30 | 50 | 0 | 0 |
| get_service_id | 35 | 0 | 30 | 30 | 0 | 5 | 0 |
| requests.get | 255 | 0 | 25 | 25 | 0 | 200 | 0 |
| get_service_providers | 30 | 0 | 20 | 20 | 0 | 10 | 0 |
| get_current_weather | 365 | 5 | 15 | 15 | 95 | 230 | 20 |
| ThinQ_Connect | 45 | 0 | 15 | 15 | 0 | 0 | 0 |
| getDataForProfessional | 40 | 0 | 15 | 15 | 0 | 25 | 0 |
| text_to_speech.convert | 15 | 0 | 15 | 15 | 0 | 0 | 0 |
| get_stock_price | 25 | 0 | 10 | 10 | 5 | 0 | 10 |
| detect_beats_and_filter | 25 | 0 | 10 | 10 | 0 | 5 | 0 |
| calculate_final_speed | 20 | 0 | 10 | 10 | 0 | 0 | 10 |
| calculate_distance | 20 | 0 | 10 | 10 | 0 | 0 | 10 |
| calculate_compound_interest | 20 | 0 | 10 | 10 | 0 | 5 | 5 |
| get_lawsuit_details | 15 | 0 | 10 | 10 | 5 | 0 | 0 |
| calculate_tax | 15 | 0 | 10 | 10 | 0 | 0 | 0 |
| sports_ranking | 10 | 0 | 10 | 10 | 0 | 0 | 0 |
| restaurant_finder | 10 | 0 | 10 | 10 | 0 | 0 | 0 |
| recipe_search | 10 | 0 | 10 | 10 | 0 | 0 | 0 |

## Top Tools By Wrong Arg Value

| tool | selected expected | success | wrong_arg_value | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error |
|---|---:|---:|---:|---:|---:|---:|---:|
| get_current_weather | 365 | 5 | 95 | 15 | 95 | 230 | 20 |
| cmd_controller.execute | 90 | 0 | 50 | 30 | 50 | 0 | 0 |
| Movies_3_FindMovies | 90 | 15 | 35 | 40 | 35 | 0 | 0 |
| record | 40 | 0 | 35 | 0 | 35 | 5 | 0 |
| play_spotify_song | 35 | 0 | 35 | 0 | 35 | 0 | 0 |
| todo | 45 | 10 | 32 | 0 | 32 | 0 | 3 |
| book_flight | 30 | 0 | 20 | 0 | 20 | 5 | 5 |
| sitefinity_create_contentitem | 25 | 0 | 20 | 0 | 20 | 5 | 0 |
| answer.string | 20 | 5 | 15 | 0 | 15 | 0 | 0 |
| get_items | 15 | 0 | 15 | 0 | 15 | 0 | 0 |
| uber.eat.order | 15 | 0 | 10 | 5 | 10 | 0 | 0 |
| send_email | 15 | 0 | 10 | 0 | 10 | 0 | 5 |
| todo_manager.handle_action | 10 | 0 | 10 | 0 | 10 | 0 | 0 |
| parseAnswer | 10 | 0 | 10 | 0 | 10 | 0 | 0 |
| get_movies | 10 | 0 | 10 | 0 | 10 | 0 | 0 |
| get_current_time | 10 | 0 | 10 | 0 | 10 | 0 | 0 |
| aws.lexv2_models.list_exports | 10 | 0 | 10 | 0 | 10 | 0 | 0 |
| Weather_1_GetWeather | 80 | 0 | 5 | 75 | 5 | 0 | 0 |
| calculate_bmi | 30 | 10 | 5 | 5 | 5 | 0 | 10 |
| get_stock_price | 25 | 0 | 5 | 10 | 5 | 0 | 10 |

## Top Tools By Parallel Or Call Shape

| tool | selected expected | success | call_shape_error | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error |
|---|---:|---:|---:|---:|---:|---:|---:|
| get_current_weather | 365 | 5 | 250 | 15 | 95 | 230 | 20 |
| requests.get | 255 | 0 | 200 | 25 | 0 | 200 | 0 |
| get_response | 70 | 0 | 70 | 0 | 0 | 70 | 0 |
| getDataForProfessional | 40 | 0 | 25 | 15 | 0 | 25 | 0 |
| math.factorial | 25 | 10 | 15 | 0 | 0 | 0 | 15 |
| user_authentication.login | 15 | 0 | 15 | 0 | 0 | 15 | 0 |
| determine_body_mass_index | 15 | 0 | 15 | 0 | 0 | 15 | 0 |
| get_service_providers | 30 | 0 | 10 | 20 | 0 | 10 | 0 |
| calculate_bmi | 30 | 10 | 10 | 5 | 5 | 0 | 10 |
| book_flight | 30 | 0 | 10 | 0 | 20 | 5 | 5 |
| math.gcd | 25 | 15 | 10 | 0 | 0 | 0 | 10 |
| get_stock_price | 25 | 0 | 10 | 10 | 5 | 0 | 10 |
| telemetry.flowrules.interfaceInfo.get | 20 | 10 | 10 | 0 | 0 | 10 | 0 |
| predict_house_price | 20 | 5 | 10 | 0 | 5 | 0 | 10 |
| lawsuit_search | 20 | 0 | 10 | 5 | 5 | 5 | 5 |
| calculate_final_velocity | 20 | 5 | 10 | 5 | 0 | 0 | 10 |
| calculate_final_speed | 20 | 0 | 10 | 10 | 0 | 0 | 10 |
| calculate_distance | 20 | 0 | 10 | 10 | 0 | 0 | 10 |
| calculate_density | 20 | 5 | 10 | 5 | 0 | 0 | 10 |
| calculate_compound_interest | 20 | 0 | 10 | 10 | 0 | 5 | 5 |

## Top Tool/Case Offenders

| tool | selected expected | success | selected_correct_rows | missing_required | wrong_arg_value | wrong_call_count | parallel_shape_error |
|---|---:|---:|---:|---:|---:|---:|---:|
| get_current_weather::live:serial | 320 | 0 | 320 | 15 | 75 | 230 | 0 |
| requests.get::live:serial | 255 | 0 | 255 | 25 | 0 | 200 | 0 |
| cmd_controller.execute::live:serial | 90 | 0 | 90 | 30 | 50 | 0 | 0 |
| Movies_3_FindMovies::live:serial | 90 | 15 | 90 | 40 | 35 | 0 | 0 |
| Weather_1_GetWeather::live:serial | 80 | 0 | 80 | 75 | 5 | 0 | 0 |
| get_response::live:serial | 70 | 0 | 70 | 0 | 0 | 70 | 0 |
| ThinQ_Connect::live:serial | 45 | 0 | 45 | 15 | 0 | 0 | 0 |
| todo::live:serial | 40 | 10 | 40 | 0 | 30 | 0 | 0 |
| record::live:serial | 40 | 0 | 40 | 0 | 35 | 5 | 0 |
| getDataForProfessional::live:serial | 40 | 0 | 40 | 15 | 0 | 25 | 0 |
| play_spotify_song::live:serial | 35 | 0 | 35 | 0 | 35 | 0 | 0 |
| get_service_id::live:serial | 35 | 0 | 35 | 30 | 0 | 5 | 0 |
| get_current_weather::live:parallel | 35 | 0 | 35 | 0 | 20 | 0 | 15 |
| get_service_providers::live:serial | 30 | 0 | 30 | 20 | 0 | 10 | 0 |
| sitefinity_create_contentitem::live:serial | 25 | 0 | 25 | 0 | 20 | 5 | 0 |
| detect_beats_and_filter::live:serial | 25 | 0 | 25 | 10 | 0 | 5 | 0 |
| book_flight::live:serial | 25 | 0 | 25 | 0 | 20 | 5 | 0 |
| uber.ride::live:serial | 20 | 10 | 20 | 0 | 5 | 5 | 0 |
| telemetry.flowrules.interfaceInfo.get::live:serial | 20 | 10 | 20 | 0 | 0 | 10 | 0 |
| answer.string::live:serial | 20 | 5 | 20 | 0 | 15 | 0 | 0 |

## Parallel Count Alignment Buckets

| tool | bucket | count |
|---|---|---:|
| get_current_weather | count_aligned | 20 |
| get_current_weather | emitted_more_than_expected | 20 |
| math.factorial | extracted_too_few_argument_sets | 9 |
| math.factorial | single_extracted_for_multi_expected | 6 |
| calculate_bmi | extracted_too_few_argument_sets | 6 |
| calculate_bmi | count_aligned | 5 |
| calculate_bmi | single_extracted_for_multi_expected | 4 |
| book_flight | extracted_too_few_argument_sets | 3 |
| book_flight | single_extracted_for_multi_expected | 2 |
| math.gcd | extracted_too_few_argument_sets | 6 |
| math.gcd | single_extracted_for_multi_expected | 4 |
| get_stock_price | extracted_too_few_argument_sets | 6 |
| get_stock_price | single_extracted_for_multi_expected | 4 |
| predict_house_price | emitted_more_than_expected | 5 |
| predict_house_price | extracted_too_few_argument_sets | 5 |
| lawsuit_search | extracted_too_few_argument_sets | 3 |
| lawsuit_search | single_extracted_for_multi_expected | 2 |
| calculate_final_velocity | extracted_too_few_argument_sets | 8 |
| calculate_final_velocity | single_extracted_for_multi_expected | 2 |
| calculate_final_speed | extracted_too_few_argument_sets | 6 |
| calculate_final_speed | single_extracted_for_multi_expected | 4 |
| calculate_distance | extracted_too_few_argument_sets | 6 |
| calculate_distance | single_extracted_for_multi_expected | 4 |
| calculate_density | extracted_too_few_argument_sets | 6 |
| calculate_density | single_extracted_for_multi_expected | 4 |
| calculate_compound_interest | extracted_too_few_argument_sets | 5 |

## Missing Required Subcauses

| tool | subcause | count |
|---|---|---:|
| Weather_1_GetWeather | missing_required_due_to_schema_alias_mismatch | 75 |
| Movies_3_FindMovies | missing_required_due_to_value_filtered | 40 |
| cmd_controller.execute | missing_required_due_to_no_query_cue | 30 |
| get_service_id | missing_required_due_to_no_query_cue | 20 |
| get_service_id | missing_required_due_to_schema_alias_mismatch | 10 |
| requests.get | missing_required_due_to_no_query_cue | 20 |
| requests.get | missing_required_due_to_schema_alias_mismatch | 10 |
| get_service_providers | missing_required_due_to_schema_alias_mismatch | 20 |
| get_current_weather | missing_required_due_to_schema_alias_mismatch | 15 |
| get_current_weather | missing_required_due_to_no_query_cue | 5 |
| ThinQ_Connect | missing_required_due_to_no_query_cue | 15 |
| getDataForProfessional | missing_required_due_to_schema_alias_mismatch | 15 |
| text_to_speech.convert | missing_required_due_to_schema_alias_mismatch | 10 |
| text_to_speech.convert | missing_required_due_to_no_query_cue | 5 |
| get_stock_price | missing_required_due_to_no_query_cue | 10 |
| get_stock_price | missing_required_due_to_schema_alias_mismatch | 5 |
| detect_beats_and_filter | missing_required_due_to_no_query_cue | 10 |
| calculate_final_speed | missing_required_due_to_schema_alias_mismatch | 10 |
| calculate_distance | missing_required_due_to_no_query_cue | 10 |
| calculate_distance | missing_required_due_to_schema_alias_mismatch | 5 |
| calculate_compound_interest | missing_required_due_to_schema_alias_mismatch | 10 |
| get_lawsuit_details | missing_required_due_to_grounder_not_attempted | 5 |
| get_lawsuit_details | missing_required_due_to_schema_alias_mismatch | 5 |
| calculate_tax | missing_required_due_to_no_query_cue | 10 |
| calculate_tax | missing_required_due_to_schema_alias_mismatch | 5 |
| sports_ranking | missing_required_due_to_no_query_cue | 10 |
| restaurant_finder | missing_required_due_to_grounder_not_attempted | 5 |
| restaurant_finder | missing_required_due_to_no_query_cue | 5 |
| restaurant_finder | missing_required_due_to_schema_alias_mismatch | 5 |
| recipe_search | missing_required_due_to_no_query_cue | 10 |
