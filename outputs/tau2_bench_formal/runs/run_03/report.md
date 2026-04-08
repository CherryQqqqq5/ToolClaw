# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 8 | 0.375 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.625 | 0.000 | 0.000 |
| a1_recovery | 8 | 0.250 | 0.250 | 1.25 | 0.00 | 0.25 | 2.00 | 0.000 | 0.0 | 0.750 | 0.000 | 0.000 |
| a2_planner | 8 | 0.250 | 0.250 | 1.25 | 0.00 | 0.25 | 2.00 | 0.000 | 0.0 | 0.750 | 0.000 | 0.000 |
| a3_interaction | 8 | 0.875 | 0.875 | 2.38 | 1.12 | 0.38 | 2.00 | 0.000 | 0.0 | 0.125 | 0.000 | 0.000 |
| a4_reuse | 8 | 0.875 | 0.875 | 2.25 | 1.12 | 0.25 | 2.00 | 0.000 | 0.0 | 0.125 | 0.000 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.500 |
| avg_tool_calls | +0.25 |
| avg_user_turns | +1.12 |
| avg_token_cost | +0.000 |
| avg_wall_clock_ms | +0.0 |
| fail_stop_rate | -0.500 |
| budget_violation_rate | +0.000 |
| mean_second_run_improvement | +0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A0 vs A1 | -0.125 | +0.250 | +0.00 | +0.125 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A2 vs A3 | +0.625 | +0.625 | +1.12 | -0.625 | +0.000 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | primary_failtax | success | tool_calls | repair_actions | user_turns | recovery_budget_used | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| tau2_binding_auto_001 | t1_static_recovery | a0_baseline | selection | 0 | 2 | 0 | 0 | 0.00 | step_failed:step_02:missing required field: target_path | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001 | t1_static_recovery | a1_recovery | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001 | t1_static_recovery | a2_planner | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001 | t1_static_recovery | a3_interaction | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001 | t1_static_recovery | a4_reuse | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_env_backup_001 | t1_static_recovery | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | step_failed:step_02:environment unavailable for write operation | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001 | t1_static_recovery | a1_recovery | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001 | t1_static_recovery | a2_planner | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001 | t1_static_recovery | a3_interaction | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001 | t1_static_recovery | a4_reuse | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001 | t1_static_recovery | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | step_failed:step_02:environment unavailable for write operation | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001 | t1_static_recovery | a1_recovery | recovery | 0 | 2 | 0 | 0 | 1.00 | awaiting_user_interaction | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001 | t1_static_recovery | a2_planner | recovery | 0 | 2 | 0 | 0 | 1.00 | awaiting_user_interaction | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001 | t1_static_recovery | a3_interaction | recovery | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001 | t1_static_recovery | a4_reuse | recovery | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | environment_failure | environment_failure | 1 | 0.000 |
| tau2_approval_gate_001 | t3_must_interact | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | approval_required | none | 0 | 0.000 |
| tau2_approval_gate_001 | t3_must_interact | a1_recovery | recovery | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | approval_required | approval_required | 0 | 0.000 |
| tau2_approval_gate_001 | t3_must_interact | a2_planner | recovery | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | approval_required | approval_required | 0 | 0.000 |
| tau2_approval_gate_001 | t3_must_interact | a3_interaction | recovery | 1 | 2 | 0 | 2 | 2.00 | success_criteria_satisfied | approval_required | approval_required | 0 | 0.000 |
| tau2_approval_gate_001 | t3_must_interact | a4_reuse | recovery | 1 | 2 | 0 | 2 | 2.00 | success_criteria_satisfied | approval_required | approval_required | 0 | 0.000 |
| tau2_binding_plus_approval_001 | t1_static_recovery | a0_baseline | selection | 0 | 2 | 0 | 0 | 0.00 | step_failed:step_02:missing required field: target_path | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001 | t1_static_recovery | a1_recovery | selection | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001 | t1_static_recovery | a2_planner | selection | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001 | t1_static_recovery | a3_interaction | selection | 1 | 3 | 1 | 2 | 2.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001 | t1_static_recovery | a4_reuse | selection | 1 | 2 | 0 | 2 | 2.00 | success_criteria_satisfied | binding_failure | binding_failure | 1 | 0.000 |
| tau2_dual_control_001 | t0_general | a0_baseline | ordering | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | dual_control | none | 0 | 0.000 |
| tau2_dual_control_001 | t0_general | a1_recovery | ordering | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | dual_control | dual_control | 0 | 0.000 |
| tau2_dual_control_001 | t0_general | a2_planner | ordering | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | dual_control | dual_control | 0 | 0.000 |
| tau2_dual_control_001 | t0_general | a3_interaction | ordering | 1 | 2 | 0 | 2 | 2.00 | success_criteria_satisfied | dual_control | dual_control | 0 | 0.000 |
| tau2_dual_control_001 | t0_general | a4_reuse | ordering | 1 | 2 | 0 | 2 | 2.00 | success_criteria_satisfied | dual_control | dual_control | 0 | 0.000 |
| tau2_interaction_failure_001 | t1_static_recovery | a0_baseline | recovery | 0 | 2 | 0 | 0 | 0.00 | step_failed:step_02:environment unavailable for write operation | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001 | t1_static_recovery | a1_recovery | recovery | 0 | 2 | 0 | 0 | 1.00 | awaiting_user_interaction | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001 | t1_static_recovery | a2_planner | recovery | 0 | 2 | 0 | 0 | 1.00 | awaiting_user_interaction | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001 | t1_static_recovery | a3_interaction | recovery | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001 | t1_static_recovery | a4_reuse | recovery | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | environment_failure | environment_failure | 1 | 0.000 |
| tau2_policy_abort_001 | t1_static_recovery | a0_baseline | recovery | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | policy_failure | none | 0 | 0.000 |
| tau2_policy_abort_001 | t1_static_recovery | a1_recovery | recovery | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | policy_failure | policy_failure | 0 | 0.000 |
| tau2_policy_abort_001 | t1_static_recovery | a2_planner | recovery | 0 | 0 | 0 | 0 | 0.00 | awaiting_user_interaction | policy_failure | policy_failure | 0 | 0.000 |
| tau2_policy_abort_001 | t1_static_recovery | a3_interaction | recovery | 0 | 0 | 0 | 1 | 1.00 | invalid_user_reply | policy_failure | policy_failure | 0 | 0.000 |
| tau2_policy_abort_001 | t1_static_recovery | a4_reuse | recovery | 0 | 0 | 0 | 1 | 1.00 | invalid_user_reply | policy_failure | policy_failure | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | approval_required | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | dual_control | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | environment_failure | 3 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | policy_failure | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | approval_required | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 1.50 | 0.00 | 0.50 | 0.500 |
| a1_recovery | dual_control | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | environment_failure | 3 | 0.333 | 0.333 | 2.33 | 0.00 | 0.33 | 0.667 |
| a1_recovery | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | approval_required | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 1.50 | 0.00 | 0.50 | 0.500 |
| a2_planner | dual_control | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | environment_failure | 3 | 0.333 | 0.333 | 2.33 | 0.00 | 0.33 | 0.667 |
| a2_planner | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a3_interaction | approval_required | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 3.00 | 1.00 | 1.00 | 0.000 |
| a3_interaction | dual_control | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | environment_failure | 3 | 1.000 | 1.000 | 3.00 | 0.67 | 0.33 | 0.000 |
| a3_interaction | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 1.00 | 0.00 | 1.000 |
| a4_reuse | approval_required | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 2.50 | 1.00 | 0.50 | 0.000 |
| a4_reuse | dual_control | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 3 | 1.000 | 1.000 | 3.00 | 0.67 | 0.33 | 0.000 |
| a4_reuse | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 1.00 | 0.00 | 1.000 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | ordering | 1 | 1.000 | 0.000 | 0.000 | 0.00 |
| a0_baseline | recovery | 5 | 0.400 | 0.000 | 0.600 | 0.00 |
| a0_baseline | selection | 2 | 0.000 | 0.000 | 1.000 | 0.00 |
| a1_recovery | ordering | 1 | 0.000 | 0.000 | 1.000 | 0.00 |
| a1_recovery | recovery | 5 | 0.200 | 0.200 | 0.800 | 0.60 |
| a1_recovery | selection | 2 | 0.500 | 0.500 | 0.500 | 0.50 |
| a2_planner | ordering | 1 | 0.000 | 0.000 | 1.000 | 0.00 |
| a2_planner | recovery | 5 | 0.200 | 0.200 | 0.800 | 0.60 |
| a2_planner | selection | 2 | 0.500 | 0.500 | 0.500 | 0.50 |
| a3_interaction | ordering | 1 | 1.000 | 1.000 | 0.000 | 2.00 |
| a3_interaction | recovery | 5 | 0.800 | 0.800 | 0.200 | 1.60 |
| a3_interaction | selection | 2 | 1.000 | 1.000 | 0.000 | 1.50 |
| a4_reuse | ordering | 1 | 1.000 | 1.000 | 0.000 | 2.00 |
| a4_reuse | recovery | 5 | 0.800 | 0.800 | 0.200 | 1.60 |
| a4_reuse | selection | 2 | 1.000 | 1.000 | 0.000 | 1.50 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | approval_required | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 1.000 |
| a0_baseline | dual_control | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | environment_failure | 3 | 0.000 | 0.000 | 1.000 |
| a0_baseline | policy_failure | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | approval_required | 1 | 0.000 | 0.000 | 1.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 0.500 |
| a1_recovery | dual_control | 1 | 0.000 | 0.000 | 1.000 |
| a1_recovery | environment_failure | 3 | 0.333 | 0.333 | 0.667 |
| a1_recovery | policy_failure | 1 | 0.000 | 0.000 | 1.000 |
| a2_planner | approval_required | 1 | 0.000 | 0.000 | 1.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 0.500 |
| a2_planner | dual_control | 1 | 0.000 | 0.000 | 1.000 |
| a2_planner | environment_failure | 3 | 0.333 | 0.333 | 0.667 |
| a2_planner | policy_failure | 1 | 0.000 | 0.000 | 1.000 |
| a3_interaction | approval_required | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| a3_interaction | dual_control | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | environment_failure | 3 | 1.000 | 1.000 | 0.000 |
| a3_interaction | policy_failure | 1 | 0.000 | 0.000 | 1.000 |
| a4_reuse | approval_required | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| a4_reuse | dual_control | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | environment_failure | 3 | 1.000 | 1.000 | 0.000 |
| a4_reuse | policy_failure | 1 | 0.000 | 0.000 | 1.000 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| a0_baseline | environment_failure | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| a0_baseline | none | 3 | 1.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | approval_required | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 0.500 | 0.000 |
| a1_recovery | dual_control | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | environment_failure | 3 | 0.333 | 0.333 | 0.333 | 0.000 |
| a1_recovery | policy_failure | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | approval_required | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 0.500 | 0.000 |
| a2_planner | dual_control | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | environment_failure | 3 | 0.333 | 0.333 | 0.333 | 0.000 |
| a2_planner | policy_failure | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_interaction | approval_required | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 1.000 | 0.500 |
| a3_interaction | dual_control | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | environment_failure | 3 | 1.000 | 1.000 | 1.000 | 0.667 |
| a3_interaction | policy_failure | 1 | 0.000 | 0.000 | 0.000 | 1.000 |
| a4_reuse | approval_required | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 1.000 | 0.500 |
| a4_reuse | dual_control | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | environment_failure | 3 | 1.000 | 1.000 | 1.000 | 0.667 |
| a4_reuse | policy_failure | 1 | 0.000 | 0.000 | 0.000 | 1.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 |
| a1_recovery | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 |
| a2_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 |
| a3_interaction | 0.750 | 0.750 | 0.000 | 0.625 | 0.00 |
| a4_reuse | 0.750 | 0.750 | 0.000 | 0.625 | 0.00 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | t1_static_recovery | 6 | 0.167 | 0.000 | 0.000 |
| a0_baseline | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t0_general | 1 | 0.000 | 0.000 | 0.000 |
| a1_recovery | t1_static_recovery | 6 | 0.333 | 0.000 | 0.000 |
| a1_recovery | t3_must_interact | 1 | 0.000 | 0.000 | 0.000 |
| a2_planner | t0_general | 1 | 0.000 | 0.000 | 0.000 |
| a2_planner | t1_static_recovery | 6 | 0.333 | 0.000 | 0.000 |
| a2_planner | t3_must_interact | 1 | 0.000 | 0.000 | 0.000 |
| a3_interaction | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t1_static_recovery | 6 | 0.833 | 0.000 | 0.000 |
| a3_interaction | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t1_static_recovery | 6 | 0.833 | 0.500 | 0.000 |
| a4_reuse | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| a1_recovery | 0.250 | 0.25 | 0.00 | 0.000 | 0.000 | 0.0 | 0.50 | 0.000 |
| a2_planner | 0.250 | 0.25 | 0.00 | 0.000 | 0.000 | 0.0 | 0.50 | 0.000 |
| a3_interaction | 0.875 | 1.38 | 1.12 | 0.750 | 0.000 | 0.0 | 1.62 | 0.000 |
| a4_reuse | 0.875 | 1.25 | 1.12 | 0.750 | 0.000 | 0.0 | 1.62 | 0.000 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 0.375 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | 0.250 | 1.25 | 0.00 | 0.50 | 0.000 |
| a2_planner | 0.250 | 1.25 | 0.00 | 0.50 | 0.000 |
| a3_interaction | 0.875 | 2.38 | 1.12 | 1.62 | 0.000 |
| a4_reuse | 0.875 | 2.25 | 1.12 | 1.62 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **a4_reuse_advantage**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- FailTax tables are the default slicing axis; failure_type tables are secondary dataset views.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- clarification_precision / clarification_recall measure whether the interaction stack asks only when needed and patches correctly after replies.
- budget_violation_rate and the Pareto view keep success claims tied to explicit execution budgets.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact, but second-run delta tables are the main reuse evidence.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Interpret A4 reuse gains primarily through second_run_* deltas, not usage-rate alone.
- Use primary_failtax and task_family tables to keep benchmark slicing aligned with experimental claims.