# ToolClaw Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 24 | 0.500 | 0.455 | 1.92 | 0.75 | 0.17 | 2.00 | 0.000 | 0.0 | 0.500 | 0.500 | 0.000 |
| a4_reuse | 24 | 0.500 | 0.429 | 1.88 | 0.75 | 0.12 | 2.00 | 0.000 | 0.0 | 0.500 | 0.500 | 0.062 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A3 vs A4 | +0.000 | -0.026 | +0.00 | +0.000 | +0.062 |

## Per-Task Results

| task_id | task_family | system | primary_failtax | success | tool_calls | repair_actions | user_turns | recovery_budget_used | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| tau2_binding_auto_001__pass1 | t1_static_recovery | a3_interaction | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001__pass1 | t1_static_recovery | a4_reuse | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001__pass2 | t1_static_recovery | a3_interaction | selection | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_auto_001__pass2 | t1_static_recovery | a4_reuse | selection | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | binding_failure | binding_failure | 1 | 1.500 |
| tau2_env_backup_001__pass1 | t1_static_recovery | a3_interaction | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001__pass1 | t1_static_recovery | a4_reuse | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001__pass2 | t1_static_recovery | a3_interaction | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_backup_001__pass2 | t1_static_recovery | a4_reuse | recovery | 1 | 3 | 1 | 0 | 1.00 | success_criteria_satisfied | environment_failure | environment_failure | 1 | 0.000 |
| tau2_env_ask_user_001__pass1 | t1_static_recovery | a3_interaction | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001__pass1 | t1_static_recovery | a4_reuse | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 1 | 0.000 |
| tau2_env_ask_user_001__pass2 | t1_static_recovery | a3_interaction | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 0 | 0.000 |
| tau2_env_ask_user_001__pass2 | t1_static_recovery | a4_reuse | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 1 | 0.000 |
| tau2_approval_gate_001__pass1 | t3_must_interact | a3_interaction | recovery | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | approval_required | approval_required | 0 | 0.000 |
| tau2_approval_gate_001__pass1 | t3_must_interact | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | approval_required | approval_required | 0 | 0.000 |
| tau2_approval_gate_001__pass2 | t3_must_interact | a3_interaction | recovery | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | approval_required | approval_required | 0 | 0.000 |
| tau2_approval_gate_001__pass2 | t3_must_interact | a4_reuse | recovery | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | approval_required | approval_required | 0 | 0.000 |
| tau2_binding_plus_approval_001__pass1 | t3_must_interact | a3_interaction | selection | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001__pass1 | t3_must_interact | a4_reuse | selection | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001__pass2 | t3_must_interact | a3_interaction | selection | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | binding_failure | binding_failure | 0 | 0.000 |
| tau2_binding_plus_approval_001__pass2 | t3_must_interact | a4_reuse | selection | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | binding_failure | binding_failure | 0 | 0.000 |
| tau2_state_stale_slot_001__pass1 | t1_static_recovery | a3_interaction | state | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_stale_slot_001__pass1 | t1_static_recovery | a4_reuse | state | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_stale_slot_001__pass2 | t1_static_recovery | a3_interaction | state | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_stale_slot_001__pass2 | t1_static_recovery | a4_reuse | state | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_checkpoint_resume_001__pass1 | t1_static_recovery | a3_interaction | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_checkpoint_resume_001__pass1 | t1_static_recovery | a4_reuse | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_checkpoint_resume_001__pass2 | t1_static_recovery | a3_interaction | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_checkpoint_resume_001__pass2 | t1_static_recovery | a4_reuse | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 1 | 0.000 |
| tau2_state_wrong_write_target_001__pass1 | t1_static_recovery | a3_interaction | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_failure | state_failure | 0 | 0.000 |
| tau2_state_wrong_write_target_001__pass1 | t1_static_recovery | a4_reuse | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_failure | state_failure | 1 | 0.000 |
| tau2_state_wrong_write_target_001__pass2 | t1_static_recovery | a3_interaction | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_failure | state_failure | 0 | 0.000 |
| tau2_state_wrong_write_target_001__pass2 | t1_static_recovery | a4_reuse | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_failure | state_failure | 1 | 0.000 |
| tau2_state_recovery_not_committed_001__pass1 | t1_static_recovery | a3_interaction | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_recovery_not_committed_001__pass1 | t1_static_recovery | a4_reuse | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 1 | 0.000 |
| tau2_state_recovery_not_committed_001__pass2 | t1_static_recovery | a3_interaction | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 0 | 0.000 |
| tau2_state_recovery_not_committed_001__pass2 | t1_static_recovery | a4_reuse | state | 1 | 3 | 0 | 1 | 2.00 | success_criteria_satisfied | state_failure | environment_failure | 1 | 0.000 |
| tau2_dual_control_001__pass1 | t3_must_interact | a3_interaction | ordering | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | dual_control | dual_control | 0 | 0.000 |
| tau2_dual_control_001__pass1 | t3_must_interact | a4_reuse | ordering | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | dual_control | dual_control | 0 | 0.000 |
| tau2_dual_control_001__pass2 | t3_must_interact | a3_interaction | ordering | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | dual_control | dual_control | 0 | 0.000 |
| tau2_dual_control_001__pass2 | t3_must_interact | a4_reuse | ordering | 0 | 1 | 0 | 1 | 1.00 | max_user_turns_exceeded | dual_control | dual_control | 0 | 0.000 |
| tau2_interaction_failure_001__pass1 | t3_must_interact | a3_interaction | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001__pass1 | t3_must_interact | a4_reuse | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001__pass2 | t3_must_interact | a3_interaction | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 0 | 0.000 |
| tau2_interaction_failure_001__pass2 | t3_must_interact | a4_reuse | recovery | 0 | 2 | 0 | 1 | 2.00 | max_recovery_budget_exceeded | environment_failure | environment_failure | 0 | 0.000 |
| tau2_policy_abort_001__pass1 | t3_must_interact | a3_interaction | recovery | 1 | 0 | 0 | 1 | 1.00 | safe_abort_success | policy_failure | policy_failure | 0 | 0.000 |
| tau2_policy_abort_001__pass1 | t3_must_interact | a4_reuse | recovery | 1 | 0 | 0 | 1 | 1.00 | safe_abort_success | policy_failure | policy_failure | 0 | 0.000 |
| tau2_policy_abort_001__pass2 | t3_must_interact | a3_interaction | recovery | 1 | 0 | 0 | 1 | 1.00 | safe_abort_success | policy_failure | policy_failure | 0 | 0.000 |
| tau2_policy_abort_001__pass2 | t3_must_interact | a4_reuse | recovery | 1 | 0 | 0 | 1 | 1.00 | safe_abort_success | policy_failure | policy_failure | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | approval_required | 2 | 0.000 | 0.000 | 1.00 | 1.00 | 0.00 | 1.000 |
| a3_interaction | binding_failure | 4 | 0.500 | 0.500 | 2.00 | 0.50 | 0.50 | 0.500 |
| a3_interaction | dual_control | 2 | 0.000 | 0.000 | 1.00 | 1.00 | 0.00 | 1.000 |
| a3_interaction | environment_failure | 6 | 0.333 | 0.333 | 2.33 | 0.67 | 0.33 | 0.667 |
| a3_interaction | policy_failure | 2 | 1.000 | 1.000 | 0.00 | 1.00 | 0.00 | 0.000 |
| a3_interaction | state_failure | 8 | 0.750 | 0.667 | 2.50 | 0.75 | 0.00 | 0.250 |
| a4_reuse | approval_required | 2 | 0.000 | 0.000 | 1.00 | 1.00 | 0.00 | 1.000 |
| a4_reuse | binding_failure | 4 | 0.500 | 0.333 | 1.75 | 0.50 | 0.25 | 0.500 |
| a4_reuse | dual_control | 2 | 0.000 | 0.000 | 1.00 | 1.00 | 0.00 | 1.000 |
| a4_reuse | environment_failure | 6 | 0.333 | 0.333 | 2.33 | 0.67 | 0.33 | 0.667 |
| a4_reuse | policy_failure | 2 | 1.000 | 1.000 | 0.00 | 1.00 | 0.00 | 0.000 |
| a4_reuse | state_failure | 8 | 0.750 | 0.667 | 2.50 | 0.75 | 0.00 | 0.250 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a3_interaction | ordering | 2 | 0.000 | 0.000 | 1.000 | 1.00 |
| a3_interaction | recovery | 10 | 0.400 | 0.400 | 0.600 | 1.40 |
| a3_interaction | selection | 4 | 0.500 | 0.500 | 0.500 | 1.00 |
| a3_interaction | state | 8 | 0.750 | 0.667 | 0.250 | 1.50 |
| a4_reuse | ordering | 2 | 0.000 | 0.000 | 1.000 | 1.00 |
| a4_reuse | recovery | 10 | 0.400 | 0.400 | 0.600 | 1.40 |
| a4_reuse | selection | 4 | 0.500 | 0.333 | 0.500 | 0.75 |
| a4_reuse | state | 8 | 0.750 | 0.667 | 0.250 | 1.50 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a3_interaction | approval_required | 2 | 0.000 | 0.000 | 1.000 |
| a3_interaction | binding_failure | 4 | 0.500 | 0.500 | 0.500 |
| a3_interaction | dual_control | 2 | 0.000 | 0.000 | 1.000 |
| a3_interaction | environment_failure | 6 | 0.333 | 0.333 | 0.667 |
| a3_interaction | policy_failure | 2 | 1.000 | 1.000 | 0.000 |
| a3_interaction | state_failure | 8 | 0.750 | 0.667 | 0.250 |
| a4_reuse | approval_required | 2 | 0.000 | 0.000 | 1.000 |
| a4_reuse | binding_failure | 4 | 0.500 | 0.333 | 0.500 |
| a4_reuse | dual_control | 2 | 0.000 | 0.000 | 1.000 |
| a4_reuse | environment_failure | 6 | 0.333 | 0.333 | 0.667 |
| a4_reuse | policy_failure | 2 | 1.000 | 1.000 | 0.000 |
| a4_reuse | state_failure | 8 | 0.750 | 0.667 | 0.250 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a3_interaction | approval_required | 2 | 0.000 | 0.000 | 0.000 | 1.000 |
| a3_interaction | binding_failure | 4 | 0.500 | 0.500 | 0.500 | 0.500 |
| a3_interaction | dual_control | 2 | 0.000 | 0.000 | 0.000 | 1.000 |
| a3_interaction | environment_failure | 12 | 0.500 | 0.500 | 0.500 | 0.833 |
| a3_interaction | policy_failure | 2 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | state_failure | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| a4_reuse | approval_required | 2 | 0.000 | 0.000 | 0.000 | 1.000 |
| a4_reuse | binding_failure | 4 | 0.500 | 0.333 | 0.250 | 0.500 |
| a4_reuse | dual_control | 2 | 0.000 | 0.000 | 0.000 | 1.000 |
| a4_reuse | environment_failure | 12 | 0.500 | 0.500 | 0.500 | 0.833 |
| a4_reuse | policy_failure | 2 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | state_failure | 2 | 1.000 | 0.000 | 0.000 | 0.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count | safe_abort_rate | policy_compliance_success_rate | state_repair_success_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 0.667 | 0.667 | 0.000 | 0.417 | 0.00 | 0.083 | 0.333 | 0.500 |
| a4_reuse | 0.667 | 0.667 | 0.000 | 0.417 | 0.00 | 0.083 | 0.333 | 0.500 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a3_interaction | t1_static_recovery | 14 | 0.714 | 0.000 | 0.000 |
| a3_interaction | t3_must_interact | 10 | 0.200 | 0.000 | 0.000 |
| a4_reuse | t1_static_recovery | 14 | 0.714 | 0.643 | 0.107 |
| a4_reuse | t3_must_interact | 10 | 0.200 | 0.000 | 0.000 |

## Repeated-Family Analysis

| system | repeat_family | pass_1_success | pass_2_success | pass_1_tool_calls | pass_2_tool_calls | pass_1_user_turns | pass_2_user_turns | pass_2_reused_artifact | second_run_improvement | second_run_success_delta | second_run_repair_count_delta | second_run_tool_calls_delta | second_run_user_turns_delta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | tau2_approval_gate_001 | 0.000 | 0.000 | 1.00 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_binding_auto_001 | 1.000 | 1.000 | 3.00 | 3.00 | 0.00 | 0.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_binding_plus_approval_001 | 0.000 | 0.000 | 1.00 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_dual_control_001 | 0.000 | 0.000 | 1.00 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_env_ask_user_001 | 0.000 | 0.000 | 2.00 | 2.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_env_backup_001 | 1.000 | 1.000 | 3.00 | 3.00 | 0.00 | 0.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_interaction_failure_001 | 0.000 | 0.000 | 2.00 | 2.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_policy_abort_001 | 1.000 | 1.000 | 0.00 | 0.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_state_checkpoint_resume_001 | 1.000 | 1.000 | 3.00 | 3.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_state_recovery_not_committed_001 | 1.000 | 1.000 | 3.00 | 3.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_state_stale_slot_001 | 0.000 | 0.000 | 2.00 | 2.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a3_interaction | tau2_state_wrong_write_target_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_approval_gate_001 | 0.000 | 0.000 | 1.00 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_binding_auto_001 | 1.000 | 1.000 | 3.00 | 2.00 | 0.00 | 0.00 | 1.000 | 1.500 | +0.000 | -1.00 | -1.00 | +0.00 |
| a4_reuse | tau2_binding_plus_approval_001 | 0.000 | 0.000 | 1.00 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_dual_control_001 | 0.000 | 0.000 | 1.00 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_env_ask_user_001 | 0.000 | 0.000 | 2.00 | 2.00 | 1.00 | 1.00 | 1.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_env_backup_001 | 1.000 | 1.000 | 3.00 | 3.00 | 0.00 | 0.00 | 1.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_interaction_failure_001 | 0.000 | 0.000 | 2.00 | 2.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_policy_abort_001 | 1.000 | 1.000 | 0.00 | 0.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_state_checkpoint_resume_001 | 1.000 | 1.000 | 3.00 | 3.00 | 1.00 | 1.00 | 1.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_state_recovery_not_committed_001 | 1.000 | 1.000 | 3.00 | 3.00 | 1.00 | 1.00 | 1.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_state_stale_slot_001 | 0.000 | 0.000 | 2.00 | 2.00 | 1.00 | 1.00 | 0.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |
| a4_reuse | tau2_state_wrong_write_target_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 1.000 | 0.000 | +0.000 | +0.00 | +0.00 | +0.00 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 0.417 | 0.58 | 0.75 | 0.750 | 0.000 | 0.0 | 1.33 | 0.500 |
| a4_reuse | 0.375 | 0.54 | 0.75 | 0.750 | 0.000 | 0.0 | 1.29 | 0.500 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a3_interaction | 0.500 | 1.92 | 0.75 | 1.33 | 0.500 |
| a4_reuse | 0.500 | 1.88 | 0.75 | 1.29 | 0.500 |

## Interpretation (auto-generated)

- Verdict: **reuse_capability_gain**.
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

_ Results generated from commit 774dabee04c10e3c428c244de8453c31f6a39457. _