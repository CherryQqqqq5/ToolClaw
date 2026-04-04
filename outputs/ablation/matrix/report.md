# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 3 | 0.333 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.667 | 0.000 | 0.000 |
| a1_recovery | 3 | 1.000 | 1.000 | 2.00 | 0.00 | 0.67 | 2.00 | 0.000 | 0.000 | 0.000 |
| a2_planner | 3 | 1.000 | 1.000 | 2.00 | 0.00 | 0.67 | 2.00 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 3 | 1.000 | 1.000 | 2.00 | 0.00 | 0.67 | 2.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 3 | 1.000 | 1.000 | 2.00 | 0.00 | 0.33 | 2.00 | 0.000 | 0.667 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.667 |
| avg_tool_calls | +0.00 |
| avg_user_turns | +0.00 |
| fail_stop_rate | -0.667 |
| reuse_usage_rate | +0.667 |
| mean_second_run_improvement | +0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A0 vs A1 | +0.667 | +1.000 | +0.00 | -0.667 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A2 vs A3 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | stop_reason | failure_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---|---|---:|---:|
| task_success_001 | t0_general | a0_baseline | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_success_001 | t0_general | a1_recovery | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_success_001 | t0_general | a2_planner | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_success_001 | t0_general | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_success_001 | t0_general | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_binding_001 | t1_static_recovery | a0_baseline | 0 | 2 | 0 | 0 | step_failed:step_02:missing required field: target_path | binding_failure | 0 | 0.000 |
| task_binding_001 | t1_static_recovery | a1_recovery | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| task_binding_001 | t1_static_recovery | a2_planner | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| task_binding_001 | t1_static_recovery | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| task_binding_001 | t1_static_recovery | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | binding_failure | 1 | 0.000 |
| task_env_001 | t1_static_recovery | a0_baseline | 0 | 2 | 0 | 0 | step_failed:step_02:environment unavailable for write operation | environment_failure | 0 | 0.000 |
| task_env_001 | t1_static_recovery | a1_recovery | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| task_env_001 | t1_static_recovery | a2_planner | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| task_env_001 | t1_static_recovery | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| task_env_001 | t1_static_recovery | a4_reuse | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 1 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | binding_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | success | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | binding_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a1_recovery | environment_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a1_recovery | success | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | binding_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a2_planner | environment_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a2_planner | success | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | binding_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a3_interaction | environment_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a3_interaction | success | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a4_reuse | success | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | binding_failure | 1 | 0.000 | 0.000 | 1.000 |
| a0_baseline | environment_failure | 1 | 0.000 | 0.000 | 1.000 |
| a0_baseline | none | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | binding_failure | 1 | 1.000 | 1.000 | 0.000 |
| a1_recovery | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a1_recovery | none | 1 | 1.000 | 0.000 | 0.000 |
| a2_planner | binding_failure | 1 | 1.000 | 1.000 | 0.000 |
| a2_planner | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a2_planner | none | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | binding_failure | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | none | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | none | 1 | 1.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | t1_static_recovery | 2 | 0.000 | 0.000 | 0.000 |
| a1_recovery | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t1_static_recovery | 2 | 1.000 | 0.000 | 0.000 |
| a2_planner | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a2_planner | t1_static_recovery | 2 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t1_static_recovery | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t1_static_recovery | 2 | 1.000 | 1.000 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **a4_reuse_advantage**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Use failure_type and task_family tables to keep benchmark slicing aligned with experimental claims.