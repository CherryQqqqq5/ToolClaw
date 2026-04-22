# ToolClaw Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 32 | 0.344 | 0.000 | 1.00 | 0.00 | 0.00 | 1.00 | 0.000 | 0.0 | 0.656 | 0.000 | 0.000 |
| fc_preflight_only | 32 | 0.062 | 0.000 | 0.12 | 0.00 | 0.00 | 1.00 | 0.000 | 0.0 | 0.938 | 0.000 | 0.000 |
| fc_grounding_recovery | 32 | 0.344 | 0.000 | 1.00 | 0.00 | 0.06 | 1.00 | 0.000 | 0.0 | 0.656 | 0.000 | 0.000 |
| a4_reuse | 32 | 0.344 | 0.000 | 1.00 | 0.00 | 0.06 | 1.00 | 0.000 | 0.0 | 0.656 | 0.000 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.000 |
| avg_tool_calls | +0.00 |
| avg_user_turns | +0.00 |
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
| live_irrelevance_120-9-0 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_irrelevance_120-9-0 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_120-9-0 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_120-9-0 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_3-2-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_3-2-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_3-2-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_3-2-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_4-2-1 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_5-3-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_5-3-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_5-3-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_5-3-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_8-4-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_8-4-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_8-4-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_8-4-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_9-4-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_9-4-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_9-4-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_9-4-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_10-4-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_10-4-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_10-4-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_10-4-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_11-4-3 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_11-4-3 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_11-4-3 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_11-4-3 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_12-4-4 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_12-4-4 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_12-4-4 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_12-4-4 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_13-4-5 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_15-4-7 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_15-4-7 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_15-4-7 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_15-4-7 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_16-4-8 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_16-4-8 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_16-4-8 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_16-4-8 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_17-4-9 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_17-4-9 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_19-4-11 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_19-4-11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_19-4-11 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_19-4-11 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_20-4-12 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_20-4-12 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_20-4-12 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_20-4-12 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_21-4-13 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_21-4-13 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_21-4-13 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_21-4-13 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_23-5-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_23-5-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_23-5-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_23-5-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_24-5-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_24-5-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_24-5-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_24-5-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 0 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_25-6-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_25-6-0 | t0_general | fc_preflight_only | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_25-6-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_25-6-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_27-7-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_27-7-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_27-7-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_27-7-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_29-9-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_29-9-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_29-9-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_29-9-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_30-10-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_30-10-0 | t0_general | fc_preflight_only | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_30-10-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_30-10-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_31-10-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_31-10-1 | t0_general | fc_preflight_only | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_31-10-1 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_31-10-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_32-10-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_32-10-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_32-10-2 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_32-10-2 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_33-10-3 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_33-10-3 | t0_general | fc_preflight_only | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_33-10-3 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_33-10-3 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_61-29-1 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_61-29-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_61-29-1 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_61-29-1 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_34 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_34 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_34 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_34 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_0 | t0_general | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_0 | t0_general | fc_grounding_recovery | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_0 | t0_general | a4_reuse | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_0 | t0_general | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_0 | t0_general | fc_grounding_recovery | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_0 | t0_general | a4_reuse | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | bfcl | 32 | 0.344 | 0.000 | 1.00 | 0.00 | 0.00 | 0.656 |
| a4_reuse | bfcl | 32 | 0.344 | 0.000 | 1.00 | 0.00 | 0.06 | 0.656 |
| fc_grounding_recovery | bfcl | 32 | 0.344 | 0.000 | 1.00 | 0.00 | 0.06 | 0.656 |
| fc_preflight_only | bfcl | 32 | 0.062 | 0.000 | 0.12 | 0.00 | 0.00 | 0.938 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | recovery | 32 | 0.344 | 0.000 | 0.656 | 0.00 |
| a4_reuse | recovery | 32 | 0.344 | 0.000 | 0.656 | 0.06 |
| fc_grounding_recovery | recovery | 32 | 0.344 | 0.000 | 0.656 | 0.06 |
| fc_preflight_only | recovery | 32 | 0.062 | 0.000 | 0.938 | 0.00 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | bfcl | 32 | 0.344 | 0.000 | 0.656 |
| a4_reuse | bfcl | 32 | 0.344 | 0.000 | 0.656 |
| fc_grounding_recovery | bfcl | 32 | 0.344 | 0.000 | 0.656 |
| fc_preflight_only | bfcl | 32 | 0.062 | 0.000 | 0.938 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | none | 32 | 0.344 | 0.000 | 0.000 | 0.000 |
| a4_reuse | bfcl | 30 | 0.367 | 0.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 2 | 0.000 | 0.000 | 1.000 | 0.000 |
| fc_grounding_recovery | bfcl | 30 | 0.367 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | binding_failure | 2 | 0.000 | 0.000 | 1.000 | 0.000 |
| fc_preflight_only | bfcl | 32 | 0.062 | 0.000 | 0.000 | 0.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count | safe_abort_rate | policy_compliance_success_rate | state_repair_success_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_preflight_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 32 | 0.344 | 0.000 | 0.000 |
| a4_reuse | t0_general | 32 | 0.344 | 0.844 | 0.000 |
| fc_grounding_recovery | t0_general | 32 | 0.344 | 0.000 | 0.000 |
| fc_preflight_only | t0_general | 32 | 0.062 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_preflight_only | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.062 | 0.06 | 0.00 | 0.000 | 0.000 | 0.0 | 0.06 | 0.000 |
| a4_reuse | 0.062 | 0.06 | 0.00 | 0.000 | 0.000 | 0.0 | 0.06 | 0.000 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 0.344 | 1.00 | 0.00 | 0.00 | 0.000 |
| fc_preflight_only | 0.062 | 0.12 | 0.00 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.344 | 1.00 | 0.00 | 0.06 | 0.000 |
| a4_reuse | 0.344 | 1.00 | 0.00 | 0.06 | 0.000 |

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

_ Results generated from commit b2bf49e05f3292970bae637c8ab4dd38b4815130. _