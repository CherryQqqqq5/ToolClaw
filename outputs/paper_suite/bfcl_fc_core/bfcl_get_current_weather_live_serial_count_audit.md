# BFCL get_current_weather live:serial Count Audit

This report is gold-enriched after execution and targets selected-correct `get_current_weather::live:serial` rows only.

- audit_schema_version: `bfcl_get_current_weather_live_serial_count_audit_v1`
- runtime_diagnostics_gold_free: `True`
- recommended_next_runtime_target: `repair_live_serial_no_call_irrelevance_over_emission`

## Summary

| metric | value |
|---|---:|
| selected_is_expected_count | 320 |
| selected_correct_success_count | 0 |
| wrong_call_count_count | 230 |
| wrong_arg_value_count | 75 |
| missing_required_count | 15 |
| expected_zero_emitted_zero_count | 0 |
| expected_zero_emitted_one_count | 230 |
| expected_zero_emitted_multi_count | 0 |
| expected_one_emitted_zero_count | 0 |
| expected_one_emitted_one_count | 90 |
| expected_one_emitted_multi_count | 0 |
| wrong_arg_value_after_count_aligned_count | 75 |

## Count Distributions

| distribution | values |
|---|---|
| expected_call_count_distribution | `{"0": 230, "1": 90}` |
| emitted_call_count_distribution | `{"1": 320}` |
| materialized_call_count_distribution | `{"1": 320}` |
| trace_metric_tool_calls_distribution | `{"1": 320}` |

## Interpretation

Dominant bucket is expected-zero/emitted-one. Next runtime repair should suppress live-serial no-call or irrelevance over-emission for selected weather, not generic multi-call collapse.
