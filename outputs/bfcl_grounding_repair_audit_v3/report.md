# ToolClaw Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 66 | 0.152 | 0.000 | 0.91 | 0.00 | 0.00 | 0.91 | 0.000 | 0.0 | 0.848 | 0.000 | 0.000 |
| fc_preflight_only | 66 | 0.121 | 0.000 | 0.00 | 0.00 | 0.00 | 0.92 | 0.000 | 0.0 | 0.879 | 0.000 | 0.000 |
| fc_grounding_recovery | 66 | 0.152 | 0.000 | 0.23 | 0.00 | 0.00 | 0.92 | 0.000 | 0.0 | 0.848 | 0.000 | 0.000 |
| a4_reuse | 66 | 0.152 | 0.000 | 0.92 | 0.68 | 0.24 | 0.92 | 0.000 | 0.0 | 0.848 | 0.000 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.000 |
| avg_tool_calls | +0.02 |
| avg_user_turns | +0.68 |
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
| live_multiple_1005-234-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1005-234-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1016-245-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1028-256-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1046-273-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1046-273-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1048-275-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1048-275-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_1049-276-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1049-276-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_1051-278-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_121-46-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_122-46-1 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_123-46-2 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_134-51-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_137-52-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_138-53-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_139-53-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_139-53-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_141-54-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_142-55-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_146-58-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_147-58-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_152-58-6 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_175-72-1 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_175-72-1 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_multiple_176-73-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_114-70-0 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_12-3-8 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_120-76-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| live_simple_121-77-0 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_126-82-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_simple_127-82-1 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_simple_127-82-1 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_10 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_10 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_10 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_10 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_102 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_102 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_102 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_102 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_106 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_106 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_106 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_106 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_11 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_11 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_11 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_112 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_112 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_112 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_112 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_114 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_114 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_114 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_114 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_115 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_115 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_115 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_115 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_116 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_116 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_116 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| multiple_116 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| multiple_117 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_117 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_117 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_117 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_118 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_118 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_118 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_118 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| multiple_119 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| multiple_119 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| multiple_119 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| multiple_119 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_101 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_101 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_101 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_101 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_103 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_103 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_103 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_103 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_104 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_104 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_104 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_104 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_105 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_105 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_105 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_105 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_11 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_11 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_11 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_113 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_113 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_113 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_113 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_117 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_117 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_117 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_117 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_118 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_118 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_118 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_118 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_100 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_100 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_100 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_100 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_102 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_102 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_102 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_102 | t0_general | a4_reuse | recovery | 0 | 2 | 2 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_104 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_104 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_104 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_104 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| parallel_multiple_109 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_109 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_109 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_109 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_11 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_11 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_11 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_11 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 2 | 2.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_110 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_110 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_110 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_110 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_113 | t0_general | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_113 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_113 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_113 | t0_general | a4_reuse | recovery | 0 | 2 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_118 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| parallel_multiple_118 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| parallel_multiple_118 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| parallel_multiple_118 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_101 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_101 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_101 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_101 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_106 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_106 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_106 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_106 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |
| simple_python_107 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_107 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_107 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| simple_python_107 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| simple_python_109 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| simple_python_109 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| simple_python_109 | t0_general | fc_grounding_recovery | recovery | 0 | 0 | 0 | 0 | 1.00 | awaiting_user_interaction | bfcl | binding_failure | 0 | 0.000 |
| simple_python_109 | t0_general | a4_reuse | recovery | 0 | 1 | 1 | 1 | 1.00 | success_criteria_satisfied | bfcl | binding_failure | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | bfcl | 66 | 0.152 | 0.000 | 0.91 | 0.00 | 0.00 | 0.848 |
| a4_reuse | bfcl | 66 | 0.152 | 0.000 | 0.92 | 0.68 | 0.24 | 0.848 |
| fc_grounding_recovery | bfcl | 66 | 0.152 | 0.000 | 0.23 | 0.00 | 0.00 | 0.848 |
| fc_preflight_only | bfcl | 66 | 0.121 | 0.000 | 0.00 | 0.00 | 0.00 | 0.879 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | recovery | 66 | 0.152 | 0.000 | 0.848 | 0.00 |
| a4_reuse | recovery | 66 | 0.152 | 0.000 | 0.848 | 0.68 |
| fc_grounding_recovery | recovery | 66 | 0.152 | 0.000 | 0.848 | 0.67 |
| fc_preflight_only | recovery | 66 | 0.121 | 0.000 | 0.879 | 0.00 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | bfcl | 66 | 0.152 | 0.000 | 0.848 |
| a4_reuse | bfcl | 66 | 0.152 | 0.000 | 0.848 |
| fc_grounding_recovery | bfcl | 66 | 0.152 | 0.000 | 0.848 |
| fc_preflight_only | bfcl | 66 | 0.121 | 0.000 | 0.879 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | none | 66 | 0.152 | 0.000 | 0.000 | 0.000 |
| a4_reuse | bfcl | 22 | 0.455 | 0.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 44 | 0.000 | 0.000 | 1.000 | 1.000 |
| fc_grounding_recovery | bfcl | 22 | 0.455 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | binding_failure | 44 | 0.000 | 0.000 | 0.000 | 0.000 |
| fc_preflight_only | bfcl | 66 | 0.121 | 0.000 | 0.000 | 0.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count | safe_abort_rate | policy_compliance_success_rate | state_repair_success_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_preflight_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 0.667 | 0.667 | 0.000 | 0.667 | 0.00 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 66 | 0.152 | 0.000 | 0.000 |
| a4_reuse | t0_general | 66 | 0.152 | 0.182 | 0.000 |
| fc_grounding_recovery | t0_general | 66 | 0.152 | 0.000 | 0.000 |
| fc_preflight_only | t0_general | 66 | 0.121 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_preflight_only | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.67 | 0.000 |
| a4_reuse | 0.667 | 0.70 | 0.68 | 0.667 | 0.000 | 0.0 | 0.68 | 0.000 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 0.152 | 0.91 | 0.00 | 0.00 | 0.000 |
| fc_preflight_only | 0.121 | 0.00 | 0.00 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.152 | 0.23 | 0.00 | 0.67 | 0.000 |
| a4_reuse | 0.152 | 0.92 | 0.68 | 0.68 | 0.000 |

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

_ Results generated from commit 4335051bcc31324eabb7125cb1626875038b5c13. _