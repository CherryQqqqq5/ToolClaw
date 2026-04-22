# ToolClaw Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 256 | 0.105 | 0.000 | 1.00 | 0.00 | 0.00 | 1.00 | 0.000 | 0.0 | 0.895 | 0.000 | 0.000 |
| fc_preflight_only | 256 | 0.031 | 0.000 | 0.01 | 0.00 | 0.00 | 1.03 | 0.000 | 0.0 | 0.969 | 0.000 | 0.000 |
| fc_grounding_recovery | 256 | 0.105 | 0.000 | 0.81 | 0.00 | 0.23 | 1.03 | 0.000 | 0.0 | 0.895 | 0.000 | 0.000 |
| a4_reuse | 256 | 0.105 | 0.000 | 1.03 | 0.20 | 0.34 | 1.03 | 0.000 | 0.0 | 0.895 | 0.000 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.000 |
| avg_tool_calls | +0.02 |
| avg_user_turns | +0.20 |
| avg_token_cost | +0.000 |
| avg_wall_clock_ms | +0.0 |
| fail_stop_rate | +0.000 |
| budget_violation_rate | +0.000 |
| mean_second_run_improvement | +0.000 |

## Per-Task Results

| task_id | task_family | system | primary_failtax | success | tool_calls | repair_actions | user_turns | recovery_budget_used | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| irrelevance_0 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| irrelevance_0 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_0 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_0 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_1 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| irrelevance_1 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_1 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_1 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_10 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| irrelevance_10 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_10 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_10 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_100 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| irrelevance_100 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_100 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| irrelevance_100 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_0-0-0 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_irrelevance_0-0-0 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_0-0-0 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_0-0-0 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_1-0-1 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_irrelevance_1-0-1 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_1-0-1 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_1-0-1 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_10-1-0 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_irrelevance_10-1-0 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_10-1-0 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_10-1-0 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_100-2-88 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_irrelevance_100-2-88 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_100-2-88 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_100-2-88 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_0-0-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_0-0-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_0-0-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_0-0-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1-0-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1-0-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1-0-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1-0-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_10-4-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_10-4-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_10-4-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_10-4-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_100-42-4 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_100-42-4 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_100-42-4 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_100-42-4 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1000-231-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1000-231-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1000-231-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1000-231-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1001-232-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1001-232-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1001-232-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1001-232-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1002-232-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1002-232-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1002-232-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1002-232-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1003-232-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1003-232-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1003-232-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1003-232-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1004-233-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1004-233-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1004-233-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1004-233-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1006-235-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1006-235-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1006-235-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1006-235-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1008-237-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1008-237-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1008-237-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1008-237-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1009-238-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1009-238-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1009-238-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1009-238-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_101-42-5 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_101-42-5 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_101-42-5 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_101-42-5 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1010-239-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1010-239-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1010-239-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1010-239-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1013-242-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1013-242-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1013-242-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1013-242-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1014-243-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1014-243-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1014-243-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1014-243-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1015-244-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1015-244-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1015-244-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1015-244-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1016-245-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1017-246-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1017-246-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1017-246-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1017-246-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1021-250-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1021-250-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1021-250-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1021-250-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1022-251-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1022-251-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1022-251-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1022-251-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1024-253-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1024-253-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1024-253-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1024-253-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1025-254-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1025-254-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1025-254-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1025-254-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1026-255-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1026-255-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1026-255-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1026-255-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1027-255-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1027-255-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1027-255-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1027-255-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1028-256-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1029-257-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1029-257-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1029-257-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1029-257-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_103-43-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_103-43-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_103-43-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_103-43-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1030-258-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1030-258-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1030-258-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1030-258-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1032-260-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1032-260-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1032-260-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1032-260-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1033-261-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1033-261-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1033-261-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1033-261-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1034-262-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1034-262-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1034-262-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1034-262-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1035-263-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1035-263-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1035-263-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1035-263-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1036-263-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1036-263-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1036-263-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1036-263-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1037-264-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1037-264-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1037-264-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1037-264-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1038-265-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1038-265-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1038-265-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1038-265-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1039-266-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1039-266-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1039-266-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1039-266-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_104-43-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_104-43-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_104-43-2 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_104-43-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1040-267-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1040-267-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1040-267-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1040-267-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1041-268-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1041-268-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1041-268-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1041-268-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1042-269-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1042-269-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1042-269-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1042-269-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1043-270-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1043-270-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1043-270-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1043-270-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1044-271-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1044-271-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1044-271-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1044-271-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1047-274-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1047-274-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1047-274-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1047-274-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1050-277-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1050-277-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1050-277-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1050-277-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1052-279-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1052-279-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1052-279-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1052-279-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_106-43-4 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_106-43-4 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_106-43-4 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_106-43-4 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_11-4-3 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_11-4-3 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_11-4-3 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_11-4-3 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_111-43-9 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_111-43-9 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_111-43-9 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_111-43-9 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_114-44-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_114-44-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_114-44-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_114-44-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_115-45-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_115-45-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_115-45-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_115-45-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_116-45-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_116-45-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_116-45-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_116-45-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_12-4-4 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_12-4-4 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_12-4-4 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_12-4-4 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_121-46-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_124-47-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_124-47-0 | t0_general | fc_preflight_only | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_124-47-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_124-47-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_125-47-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_125-47-1 | t0_general | fc_preflight_only | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_125-47-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_125-47-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_126-48-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_126-48-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_126-48-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_126-48-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_127-49-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_127-49-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_127-49-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_127-49-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_128-50-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_128-50-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_128-50-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_128-50-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_129-50-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_129-50-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_129-50-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_129-50-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_13-4-5 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_130-50-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_130-50-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_130-50-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_130-50-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_131-50-3 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_131-50-3 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_131-50-3 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_131-50-3 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_132-50-4 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_132-50-4 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_132-50-4 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_132-50-4 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_133-50-5 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_133-50-5 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_133-50-5 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_133-50-5 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_134-51-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_135-51-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_135-51-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_135-51-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_135-51-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_136-52-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_136-52-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_136-52-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_136-52-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_14-4-6 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_14-4-6 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_14-4-6 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_14-4-6 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_140-54-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_140-54-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_140-54-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_140-54-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_143-55-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_143-55-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_143-55-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_143-55-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_144-56-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_144-56-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_144-56-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_144-56-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_145-57-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_145-57-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_145-57-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_145-57-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_146-58-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_148-58-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_148-58-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_148-58-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_148-58-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_149-58-3 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_149-58-3 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_149-58-3 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_149-58-3 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_15-4-7 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_15-4-7 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_15-4-7 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_15-4-7 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_150-58-4 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_150-58-4 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_150-58-4 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_150-58-4 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_151-58-5 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_151-58-5 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_151-58-5 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_151-58-5 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_152-58-6 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_153-58-7 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_153-58-7 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_153-58-7 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_153-58-7 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_154-58-8 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_154-58-8 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_154-58-8 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_154-58-8 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_155-58-9 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_155-58-9 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_155-58-9 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_155-58-9 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_156-59-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_156-59-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_156-59-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_156-59-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_157-60-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_157-60-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_157-60-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_157-60-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_158-61-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_158-61-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_158-61-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_158-61-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_159-62-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_159-62-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_159-62-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_159-62-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_16-4-8 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_16-4-8 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_16-4-8 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_16-4-8 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_160-62-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_160-62-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_160-62-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_160-62-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_161-63-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_161-63-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_161-63-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_161-63-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_162-63-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_162-63-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_162-63-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_162-63-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_163-64-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_163-64-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_163-64-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_163-64-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_164-65-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_164-65-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_164-65-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_164-65-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_165-65-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_165-65-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_165-65-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_165-65-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_166-66-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_166-66-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_166-66-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_166-66-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_167-67-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_167-67-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_167-67-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_167-67-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_168-68-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_168-68-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_168-68-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_168-68-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_169-69-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_169-69-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_169-69-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_169-69-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_170-70-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_170-70-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_170-70-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_170-70-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_171-71-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_171-71-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_171-71-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_171-71-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_172-71-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_172-71-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_172-71-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_172-71-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_173-71-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_173-71-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_173-71-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_173-71-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_174-72-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_174-72-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_174-72-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_174-72-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_177-74-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_177-74-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_177-74-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_177-74-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_178-75-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_178-75-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_178-75-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_178-75-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_179-75-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_179-75-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_179-75-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_179-75-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_18-4-10 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_18-4-10 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_18-4-10 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_18-4-10 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_180-76-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_180-76-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_180-76-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_180-76-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_181-76-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_181-76-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_181-76-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_181-76-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_182-77-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_182-77-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_182-77-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_182-77-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_183-78-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_183-78-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_183-78-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_183-78-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_184-79-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_184-79-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_184-79-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_184-79-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_0-0-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_0-0-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_0-0-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_0-0-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_1-1-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_1-1-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_1-1-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_1-1-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_10-3-6 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_10-3-6 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_10-3-6 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_10-3-6 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_100-59-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_100-59-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_100-59-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_100-59-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_101-60-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_101-60-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_101-60-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_101-60-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_102-61-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_102-61-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_102-61-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_102-61-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_103-61-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_103-61-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_103-61-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_103-61-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_104-61-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_104-61-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_104-61-2 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_104-61-2 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_105-62-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_105-62-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_105-62-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_105-62-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_106-63-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_106-63-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_106-63-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_106-63-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_107-64-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_107-64-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_107-64-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_107-64-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_108-65-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_108-65-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_108-65-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_108-65-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_11-3-7 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_11-3-7 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_11-3-7 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_11-3-7 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_112-68-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_112-68-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_112-68-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_112-68-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_113-69-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_113-69-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_113-69-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_113-69-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_115-71-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_115-71-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_115-71-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_115-71-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_116-72-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_116-72-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_116-72-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_116-72-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 1 | 0.000 |
| live_simple_117-73-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_117-73-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_117-73-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_117-73-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_118-74-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_118-74-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_118-74-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_118-74-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_119-75-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_119-75-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_119-75-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_119-75-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_122-78-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_122-78-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_122-78-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_122-78-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_123-79-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_123-79-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_123-79-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_123-79-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_124-80-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_124-80-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_124-80-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_124-80-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_125-81-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_125-81-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_125-81-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_125-81-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_126-82-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_128-83-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_128-83-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_128-83-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_128-83-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_129-83-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_129-83-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_129-83-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_129-83-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_1 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_1 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_1 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_10 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_10 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_10 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_10 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_100 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_100 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_100 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_100 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_101 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_101 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_101 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_101 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_102 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_102 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_102 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_102 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_103 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_103 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_103 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_103 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_104 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_104 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_104 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_104 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_105 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_105 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_105 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_105 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_106 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_106 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_106 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_106 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_107 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_107 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_107 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_107 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_108 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_108 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_108 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_108 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_109 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_109 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_109 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_109 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_11 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_11 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_11 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_110 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_110 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_110 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_110 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_111 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_111 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_111 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_111 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_112 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_112 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_112 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_112 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_113 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_113 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_113 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_113 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_114 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_114 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_114 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_114 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_115 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_115 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_115 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_115 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_116 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_116 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_116 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_116 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_117 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_117 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_117 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_117 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_118 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_118 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_118 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_118 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_119 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_119 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_119 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_119 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_0 | t0_general | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_0 | t0_general | fc_grounding_recovery | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_0 | t0_general | a4_reuse | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_1 | t0_general | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_1 | t0_general | fc_grounding_recovery | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_1 | t0_general | a4_reuse | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_10 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_10 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_10 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_10 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_100 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_100 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_100 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_100 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_101 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_101 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_101 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_101 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_102 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_102 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_102 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_102 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_103 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_103 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_103 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_103 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_104 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_104 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_104 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_104 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_105 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_105 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_105 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_105 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_106 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_106 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_106 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_106 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_107 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_107 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_107 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_107 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_108 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_108 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_108 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_108 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_109 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_109 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_109 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_109 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_11 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_11 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_11 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_111 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_111 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_111 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_111 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_112 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_112 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_112 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_112 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_113 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_113 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_113 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_113 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_114 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_114 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_114 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_114 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_115 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_115 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_115 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_115 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_116 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_116 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_116 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_116 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_117 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_117 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_117 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_117 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_118 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_118 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_118 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_118 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_119 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_119 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_119 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_119 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_12 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_12 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_12 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_12 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_0 | t0_general | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_0 | t0_general | fc_grounding_recovery | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_0 | t0_general | a4_reuse | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_1 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_1 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_1 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_10 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_10 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_10 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_10 | t0_general | a4_reuse | recovery | 0 | 2 | 2 | 2 | 3.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_100 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_100 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_100 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_100 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_101 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_101 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_101 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_101 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_102 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_102 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_102 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 2 | 0 | 2.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_102 | t0_general | a4_reuse | recovery | 0 | 2 | 2 | 0 | 2.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_103 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_103 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_103 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_103 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_104 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_104 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_104 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_104 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_105 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_105 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_105 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_105 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_106 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_106 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_106 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_106 | t0_general | a4_reuse | recovery | 0 | 2 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_107 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_107 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_107 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_107 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_108 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_108 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_108 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_108 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_109 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_109 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_109 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_109 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_11 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_11 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 2.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_11 | t0_general | a4_reuse | recovery | 0 | 2 | 2 | 0 | 2.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_110 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_110 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_110 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_110 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_111 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_111 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_111 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_111 | t0_general | a4_reuse | recovery | 0 | 2 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_112 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_112 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_112 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_112 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_113 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_113 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_113 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_113 | t0_general | a4_reuse | recovery | 0 | 2 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_114 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_114 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_114 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_114 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_115 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_115 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_115 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_115 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_116 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_116 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_116 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_116 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_117 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_117 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_117 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_117 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_118 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_118 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_118 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_118 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_119 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_119 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_119 | t0_general | fc_grounding_recovery | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_119 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_1 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_1 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_1 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_10 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_10 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_10 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_10 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_100 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_100 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_100 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_100 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_101 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_101 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_101 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_101 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_102 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_102 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_102 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_102 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_103 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_103 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_103 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_103 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_104 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_104 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_104 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_104 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_105 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_105 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_105 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_105 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_106 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_106 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_106 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_106 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_107 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_107 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_107 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_107 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_108 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_108 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_108 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_108 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_109 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_109 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_109 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_109 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_11 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_11 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_11 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_110 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_110 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_110 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_110 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_111 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_111 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_111 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_111 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | bfcl | 256 | 0.105 | 0.000 | 1.00 | 0.00 | 0.00 | 0.895 |
| a4_reuse | bfcl | 256 | 0.105 | 0.000 | 1.03 | 0.20 | 0.34 | 0.895 |
| fc_grounding_recovery | bfcl | 256 | 0.105 | 0.000 | 0.81 | 0.00 | 0.23 | 0.895 |
| fc_preflight_only | bfcl | 256 | 0.031 | 0.000 | 0.01 | 0.00 | 0.00 | 0.969 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | recovery | 256 | 0.105 | 0.000 | 0.895 | 0.00 |
| a4_reuse | recovery | 256 | 0.105 | 0.000 | 0.895 | 0.44 |
| fc_grounding_recovery | recovery | 256 | 0.105 | 0.000 | 0.895 | 0.43 |
| fc_preflight_only | recovery | 256 | 0.031 | 0.000 | 0.969 | 0.00 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | bfcl | 256 | 0.105 | 0.000 | 0.895 |
| a4_reuse | bfcl | 256 | 0.105 | 0.000 | 0.895 |
| fc_grounding_recovery | bfcl | 256 | 0.105 | 0.000 | 0.895 |
| fc_preflight_only | bfcl | 256 | 0.031 | 0.000 | 0.969 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | none | 256 | 0.105 | 0.000 | 0.000 | 0.000 |
| a4_reuse | bfcl | 147 | 0.184 | 0.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 109 | 0.000 | 0.000 | 1.000 | 0.468 |
| fc_grounding_recovery | bfcl | 147 | 0.184 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | binding_failure | 109 | 0.000 | 0.000 | 0.523 | 0.000 |
| fc_preflight_only | bfcl | 256 | 0.031 | 0.000 | 0.000 | 0.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count | safe_abort_rate | policy_compliance_success_rate | state_repair_success_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_preflight_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 0.199 | 0.199 | 0.000 | 0.199 | 0.00 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 256 | 0.105 | 0.000 | 0.000 |
| a4_reuse | t0_general | 256 | 0.105 | 0.477 | 0.000 |
| fc_grounding_recovery | t0_general | 256 | 0.105 | 0.000 | 0.000 |
| fc_preflight_only | t0_general | 256 | 0.031 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_preflight_only | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.223 | 0.23 | 0.00 | 0.000 | 0.000 | 0.0 | 0.43 | 0.000 |
| a4_reuse | 0.426 | 0.45 | 0.20 | 0.199 | 0.000 | 0.0 | 0.44 | 0.000 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 0.105 | 1.00 | 0.00 | 0.00 | 0.000 |
| fc_preflight_only | 0.031 | 0.01 | 0.00 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.105 | 0.81 | 0.00 | 0.43 | 0.000 |
| a4_reuse | 0.105 | 1.03 | 0.20 | 0.44 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **tie**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- FailTax tables are the default slicing axis; failure_type tables are secondary dataset views.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- clarification_precision / clarification_recall measure whether the interaction stack asks only when needed and patches correctly after replies.
- safe_abort_rate and policy_compliance_success_rate separate policy-compliant stops from true execution failures.
- state_repair_success_rate tracks whether state-slice repairs actually close the loop after the first blocked run.
- budget_violation_rate and the Pareto view keep success claims tied to explicit execution budgets.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact, but second-run delta tables are the main reuse evidence.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Interpret A4 reuse gains primarily through second_run_* deltas, not usage-rate alone.
- Use primary_failtax and task_family tables to keep benchmark slicing aligned with experimental claims.

_ Results generated from commit e344ba357695fd1abe2a3f2f12d5eb3f1fbf7f2f. _