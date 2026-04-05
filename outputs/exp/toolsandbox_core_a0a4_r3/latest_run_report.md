# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 10 | 0.700 | 0.000 | 1.80 | 0.00 | 0.00 | 1.80 | 0.300 | 0.000 | 0.000 |
| a1_recovery | 10 | 0.700 | 0.250 | 1.40 | 0.00 | 0.10 | 1.80 | 0.300 | 0.000 | 0.000 |
| a2_planner | 10 | 0.700 | 0.250 | 1.40 | 0.00 | 0.10 | 1.80 | 0.300 | 0.000 | 0.000 |
| a3_interaction | 10 | 1.000 | 1.000 | 1.90 | 0.50 | 0.20 | 1.80 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 10 | 1.000 | 1.000 | 1.90 | 0.50 | 0.10 | 1.80 | 0.000 | 0.300 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.300 |
| avg_tool_calls | +0.10 |
| avg_user_turns | +0.50 |
| fail_stop_rate | -0.300 |
| reuse_usage_rate | +0.300 |
| mean_second_run_improvement | +0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A0 vs A1 | +0.000 | +0.250 | +0.00 | +0.000 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A2 vs A3 | +0.300 | +0.750 | +0.50 | -0.300 | +0.000 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | stop_reason | failure_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---|---|---:|---:|
| toolsandbox_state_dep_001 | t2_dynamic_branching | a0_baseline | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | a1_recovery | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | a2_planner | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | a0_baseline | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | a1_recovery | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | a2_planner | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 1 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | a0_baseline | 0 | 2 | 0 | 0 | step_failed:step_02:environment unavailable for write operation | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | a1_recovery | 0 | 2 | 0 | 0 | awaiting_user_interaction | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | a2_planner | 0 | 2 | 0 | 0 | awaiting_user_interaction | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | a3_interaction | 1 | 3 | 0 | 1 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | a4_reuse | 1 | 3 | 0 | 1 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | a0_baseline | 0 | 2 | 0 | 0 | step_failed:step_02:missing required field: target_path | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | a1_recovery | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | a2_planner | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | a4_reuse | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | a0_baseline | 1 | 2 | 0 | 0 | success_criteria_satisfied | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | a1_recovery | 0 | 0 | 0 | 0 | awaiting_user_interaction | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | a2_planner | 0 | 0 | 0 | 0 | awaiting_user_interaction | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | a3_interaction | 1 | 2 | 0 | 2 | success_criteria_satisfied | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | a4_reuse | 1 | 2 | 0 | 2 | success_criteria_satisfied | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a0_baseline | 0 | 2 | 0 | 0 | step_failed:step_02:missing required field: target_path | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a1_recovery | 0 | 0 | 0 | 0 | awaiting_user_interaction | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a2_planner | 0 | 0 | 0 | 0 | awaiting_user_interaction | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a3_interaction | 1 | 2 | 1 | 2 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a4_reuse | 1 | 2 | 0 | 2 | success_criteria_satisfied | binding_failure | 1 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a0_baseline | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a1_recovery | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a2_planner | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a0_baseline | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a1_recovery | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a2_planner | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 1 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a0_baseline | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a1_recovery | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a2_planner | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a3_interaction | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a4_reuse | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a0_baseline | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a1_recovery | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a2_planner | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a3_interaction | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a4_reuse | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | multiple_user_turn | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| a1_recovery | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | multiple_user_turn | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| a2_planner | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | multiple_user_turn | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a3_interaction | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | environment_failure | 1 | 1.000 | 1.000 | 3.00 | 1.00 | 0.00 | 0.000 |
| a3_interaction | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 0.50 | 0.000 |
| a4_reuse | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 1 | 1.000 | 1.000 | 3.00 | 1.00 | 0.00 | 0.000 |
| a4_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 1.000 |
| a0_baseline | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a0_baseline | environment_failure | 1 | 0.000 | 0.000 | 1.000 |
| a0_baseline | multiple_user_turn | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| a0_baseline | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 0.500 |
| a1_recovery | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a1_recovery | environment_failure | 1 | 0.000 | 0.000 | 1.000 |
| a1_recovery | multiple_user_turn | 1 | 0.000 | 0.000 | 1.000 |
| a1_recovery | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| a1_recovery | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 0.500 |
| a2_planner | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a2_planner | environment_failure | 1 | 0.000 | 0.000 | 1.000 |
| a2_planner | multiple_user_turn | 1 | 0.000 | 0.000 | 1.000 |
| a2_planner | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| a2_planner | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| a3_interaction | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a3_interaction | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| a3_interaction | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| a4_reuse | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | state_dependency | 2 | 1.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | t1_static_recovery | 3 | 0.000 | 0.000 | 0.000 |
| a0_baseline | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| a0_baseline | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t1_static_recovery | 3 | 0.333 | 0.000 | 0.000 |
| a1_recovery | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t3_must_interact | 1 | 0.000 | 0.000 | 0.000 |
| a2_planner | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a2_planner | t1_static_recovery | 3 | 0.333 | 0.000 | 0.000 |
| a2_planner | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| a2_planner | t3_must_interact | 1 | 0.000 | 0.000 | 0.000 |
| a3_interaction | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t1_static_recovery | 3 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t1_static_recovery | 3 | 1.000 | 0.333 | 0.000 |
| a4_reuse | t2_dynamic_branching | 5 | 1.000 | 0.400 | 0.000 |
| a4_reuse | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **a4_reuse_advantage**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Interpret A4 reuse gains primarily through the repeated-family sections, not the full-task aggregate.
- Use failure_type and task_family tables to keep benchmark slicing aligned with experimental claims.