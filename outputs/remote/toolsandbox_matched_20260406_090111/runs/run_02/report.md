# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tc_full | 10 | 1.000 | 1.000 | 1.90 | 0.50 | 0.10 | 1.80 | 0.000 | 0.0 | 0.000 | 0.300 | 0.000 |
| tc_no_repair | 10 | 0.700 | 0.500 | 1.80 | 0.40 | 0.00 | 1.80 | 0.000 | 0.0 | 0.300 | 0.000 | 0.000 |
| tc_no_fallback | 10 | 1.000 | 1.000 | 1.90 | 0.50 | 0.20 | 1.80 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| tc_no_reuse | 10 | 1.000 | 1.000 | 1.90 | 0.50 | 0.20 | 1.80 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| tc_planner_only | 10 | 0.700 | 0.250 | 1.40 | 0.00 | 0.10 | 1.80 | 0.000 | 0.0 | 0.300 | 0.000 | 0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | repair_extra_tool_calls | repair_extra_user_turns | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| toolsandbox_state_dep_001 | t2_dynamic_branching | tc_full | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | tc_no_repair | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | tc_no_fallback | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | tc_no_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_001 | t2_dynamic_branching | tc_planner_only | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | tc_full | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 1 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | tc_no_repair | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | tc_no_fallback | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | tc_no_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | tc_planner_only | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | tc_full | 1 | 3 | 0 | 1 | 1 | 1 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | tc_no_repair | 0 | 2 | 0 | 0 | 0 | 0 | repair_disabled | environment_failure | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | tc_no_fallback | 1 | 3 | 0 | 1 | 1 | 1 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | tc_no_reuse | 1 | 3 | 0 | 1 | 1 | 1 | success_criteria_satisfied | environment_failure | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | tc_planner_only | 0 | 2 | 0 | 0 | 0 | 0 | awaiting_user_interaction | environment_failure | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | tc_full | 1 | 2 | 1 | 0 | 0 | 0 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | tc_no_repair | 0 | 2 | 0 | 0 | 0 | 0 | repair_disabled | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | tc_no_fallback | 1 | 2 | 1 | 0 | 0 | 0 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | tc_no_reuse | 1 | 2 | 1 | 0 | 0 | 0 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | tc_planner_only | 1 | 2 | 1 | 0 | 0 | 0 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | tc_full | 1 | 2 | 0 | 2 | 2 | 2 | success_criteria_satisfied | multiple_user_turn | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | tc_no_repair | 1 | 2 | 0 | 2 | 2 | 2 | success_criteria_satisfied | multiple_user_turn | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | tc_no_fallback | 1 | 2 | 0 | 2 | 2 | 2 | success_criteria_satisfied | multiple_user_turn | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | tc_no_reuse | 1 | 2 | 0 | 2 | 2 | 2 | success_criteria_satisfied | multiple_user_turn | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | tc_planner_only | 0 | 0 | 0 | 0 | 0 | 0 | awaiting_user_interaction | multiple_user_turn | multiple_user_turn | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | tc_full | 1 | 2 | 0 | 2 | 2 | 2 | success_criteria_satisfied | binding_failure | binding_failure | 1 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | tc_no_repair | 0 | 2 | 0 | 2 | 2 | 2 | repair_disabled | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | tc_no_fallback | 1 | 2 | 1 | 2 | 2 | 2 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | tc_no_reuse | 1 | 2 | 1 | 2 | 2 | 2 | success_criteria_satisfied | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | tc_planner_only | 0 | 0 | 0 | 0 | 0 | 0 | awaiting_user_interaction | binding_failure | binding_failure | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | tc_full | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | tc_no_repair | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | tc_no_fallback | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | tc_no_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | tc_planner_only | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | tc_full | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 1 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | tc_no_repair | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | tc_no_fallback | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | tc_no_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | tc_planner_only | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | canonicalization | canonicalization | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | tc_full | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | tc_no_repair | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | tc_no_fallback | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | tc_no_reuse | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | tc_planner_only | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | tc_full | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | tc_no_repair | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | tc_no_fallback | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | tc_no_reuse | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | tc_planner_only | 1 | 1 | 0 | 0 | 0 | 0 | success_criteria_satisfied | single_tool | single_tool | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| tc_full | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 0.50 | 0.000 |
| tc_full | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_full | environment_failure | 1 | 1.000 | 1.000 | 3.00 | 1.00 | 0.00 | 0.000 |
| tc_full | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| tc_full | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| tc_full | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_no_fallback | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| tc_no_fallback | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_no_fallback | environment_failure | 1 | 1.000 | 1.000 | 3.00 | 1.00 | 0.00 | 0.000 |
| tc_no_fallback | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| tc_no_fallback | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| tc_no_fallback | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_no_repair | binding_failure | 2 | 0.000 | 0.000 | 2.00 | 1.00 | 0.00 | 1.000 |
| tc_no_repair | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_no_repair | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| tc_no_repair | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| tc_no_repair | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| tc_no_repair | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_no_reuse | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| tc_no_reuse | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_no_reuse | environment_failure | 1 | 1.000 | 1.000 | 3.00 | 1.00 | 0.00 | 0.000 |
| tc_no_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| tc_no_reuse | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| tc_no_reuse | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_planner_only | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| tc_planner_only | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| tc_planner_only | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| tc_planner_only | multiple_user_turn | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| tc_planner_only | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| tc_planner_only | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| tc_full | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| tc_full | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| tc_full | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| tc_full | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| tc_full | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| tc_full | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| tc_no_fallback | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| tc_no_fallback | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| tc_no_fallback | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_repair | binding_failure | 2 | 0.000 | 0.000 | 1.000 |
| tc_no_repair | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_repair | environment_failure | 1 | 0.000 | 0.000 | 1.000 |
| tc_no_repair | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| tc_no_repair | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_repair | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| tc_no_reuse | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| tc_no_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| tc_no_reuse | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | state_dependency | 2 | 1.000 | 0.000 | 0.000 |
| tc_planner_only | binding_failure | 2 | 0.500 | 0.500 | 0.500 |
| tc_planner_only | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| tc_planner_only | environment_failure | 1 | 0.000 | 0.000 | 1.000 |
| tc_planner_only | multiple_user_turn | 1 | 0.000 | 0.000 | 1.000 |
| tc_planner_only | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| tc_planner_only | state_dependency | 2 | 1.000 | 0.000 | 0.000 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| tc_full | binding_failure | 2 | 1.000 | 1.000 | 1.000 | 0.500 |
| tc_full | canonicalization | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_full | environment_failure | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_full | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_full | single_tool | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_full | state_dependency | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_fallback | binding_failure | 2 | 1.000 | 1.000 | 1.000 | 0.500 |
| tc_no_fallback | canonicalization | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_fallback | environment_failure | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_no_fallback | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_no_fallback | single_tool | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_fallback | state_dependency | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_repair | binding_failure | 2 | 0.000 | 0.000 | 0.000 | 0.500 |
| tc_no_repair | canonicalization | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_repair | environment_failure | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| tc_no_repair | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_no_repair | single_tool | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_repair | state_dependency | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_reuse | binding_failure | 2 | 1.000 | 1.000 | 1.000 | 0.500 |
| tc_no_reuse | canonicalization | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_reuse | environment_failure | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_no_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| tc_no_reuse | single_tool | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_no_reuse | state_dependency | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_planner_only | binding_failure | 2 | 0.500 | 0.500 | 0.500 | 0.000 |
| tc_planner_only | canonicalization | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_planner_only | environment_failure | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| tc_planner_only | multiple_user_turn | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| tc_planner_only | single_tool | 2 | 1.000 | 0.000 | 0.000 | 0.000 |
| tc_planner_only | state_dependency | 2 | 1.000 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| tc_full | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| tc_full | t1_static_recovery | 3 | 1.000 | 0.333 | 0.000 |
| tc_full | t2_dynamic_branching | 5 | 1.000 | 0.400 | 0.000 |
| tc_full | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | t1_static_recovery | 3 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| tc_no_fallback | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| tc_no_repair | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| tc_no_repair | t1_static_recovery | 3 | 0.000 | 0.000 | 0.000 |
| tc_no_repair | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| tc_no_repair | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | t1_static_recovery | 3 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| tc_no_reuse | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| tc_planner_only | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| tc_planner_only | t1_static_recovery | 3 | 0.333 | 0.000 | 0.000 |
| tc_planner_only | t2_dynamic_branching | 5 | 1.000 | 0.000 | 0.000 |
| tc_planner_only | t3_must_interact | 1 | 0.000 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms |
|---|---:|---:|---:|---:|---:|---:|
| tc_full | 0.400 | 0.50 | 0.50 | 0.300 | 0.000 | 0.0 |
| tc_no_repair | 0.100 | 0.40 | 0.40 | 0.200 | 0.000 | 0.0 |
| tc_no_fallback | 0.400 | 0.50 | 0.50 | 0.300 | 0.000 | 0.0 |
| tc_no_reuse | 0.400 | 0.50 | 0.50 | 0.300 | 0.000 | 0.0 |
| tc_planner_only | 0.100 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 |

## Interpretation (auto-generated)

- Verdict: **inconclusive**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Interpret A4 reuse gains primarily through the repeated-family sections, not the full-task aggregate.
- Use failure_type and task_family tables to keep benchmark slicing aligned with experimental claims.