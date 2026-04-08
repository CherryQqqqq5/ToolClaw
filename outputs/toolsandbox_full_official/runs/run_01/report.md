# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a1_recovery | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a2_planner | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.000 |
| avg_tool_calls | +0.00 |
| avg_user_turns | +0.00 |
| avg_token_cost | +0.000 |
| avg_wall_clock_ms | +0.0 |
| fail_stop_rate | +0.000 |
| reuse_usage_rate | +0.000 |
| mean_second_run_improvement | +0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A0 vs A1 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A2 vs A3 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | repair_extra_tool_calls | repair_extra_user_turns | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| send_message_with_contact_content_cellular_off_3_distraction_tools_arg_description_scrambled | t2_dynamic_branching | a0_baseline | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | none | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_3_distraction_tools_arg_description_scrambled | t2_dynamic_branching | a1_recovery | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_3_distraction_tools_arg_description_scrambled | t2_dynamic_branching | a2_planner | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_3_distraction_tools_arg_description_scrambled | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_3_distraction_tools_arg_description_scrambled | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a0_baseline | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | none | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a1_recovery | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a2_planner | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a3_interaction | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a4_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn_10_distraction_tools | t3_must_interact | a0_baseline | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | none | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn_10_distraction_tools | t3_must_interact | a1_recovery | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn_10_distraction_tools | t3_must_interact | a2_planner | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn_10_distraction_tools | t3_must_interact | a3_interaction | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn_10_distraction_tools | t3_must_interact | a4_reuse | 1 | 2 | 0 | 0 | 0 | 0 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | state_dependency | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | state_dependency | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | state_dependency | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | state_dependency | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | state_dependency | 3 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | state_dependency | 3 | 1.000 | 0.000 | 0.000 |
| a1_recovery | state_dependency | 3 | 1.000 | 0.000 | 0.000 |
| a2_planner | state_dependency | 3 | 1.000 | 0.000 | 0.000 |
| a3_interaction | state_dependency | 3 | 1.000 | 0.000 | 0.000 |
| a4_reuse | state_dependency | 3 | 1.000 | 0.000 | 0.000 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | none | 3 | 1.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | state_dependency | 3 | 1.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | state_dependency | 3 | 1.000 | 0.000 | 0.000 | 0.000 |
| a3_interaction | state_dependency | 3 | 1.000 | 0.000 | 0.000 | 0.000 |
| a4_reuse | state_dependency | 3 | 1.000 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t2_dynamic_branching | 1 | 1.000 | 0.000 | 0.000 |
| a0_baseline | t3_must_interact | 2 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t2_dynamic_branching | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t3_must_interact | 2 | 1.000 | 0.000 | 0.000 |
| a2_planner | t2_dynamic_branching | 1 | 1.000 | 0.000 | 0.000 |
| a2_planner | t3_must_interact | 2 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t2_dynamic_branching | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t3_must_interact | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t2_dynamic_branching | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t3_must_interact | 2 | 1.000 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms |
|---|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 |
| a1_recovery | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 |
| a2_planner | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 |
| a3_interaction | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 |
| a4_reuse | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 |

## Interpretation (auto-generated)

- Verdict: **tie**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Interpret A4 reuse gains primarily through the repeated-family sections, not the full-task aggregate.
- Use failure_type and task_family tables to keep benchmark slicing aligned with experimental claims.