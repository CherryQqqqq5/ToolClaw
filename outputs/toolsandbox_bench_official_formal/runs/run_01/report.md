# ToolClaw Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a1_recovery | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a2_planner | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 | 0.0 | 0.000 | 0.000 | 0.000 |

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

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A0 vs A1 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A2 vs A3 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | primary_failtax | success | tool_calls | repair_actions | user_turns | recovery_budget_used | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a0_baseline | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_dependency | none | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a1_recovery | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_dependency | state_failure | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a2_planner | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a3_interaction | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |
| send_message_with_contact_content_cellular_off_multiple_user_turn | t3_must_interact | a4_reuse | state | 1 | 2 | 0 | 0 | 0.00 | success_criteria_satisfied | state_dependency | state_dependency | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | state_dependency | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | state_dependency | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | state_dependency | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | state_dependency | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | state_dependency | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | state | 1 | 1.000 | 0.000 | 0.000 | 0.00 |
| a1_recovery | state | 1 | 1.000 | 0.000 | 0.000 | 0.00 |
| a2_planner | state | 1 | 1.000 | 0.000 | 0.000 | 0.00 |
| a3_interaction | state | 1 | 1.000 | 0.000 | 0.000 | 0.00 |
| a4_reuse | state | 1 | 1.000 | 0.000 | 0.000 | 0.00 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | state_dependency | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | state_dependency | 1 | 1.000 | 0.000 | 0.000 |
| a2_planner | state_dependency | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | state_dependency | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | state_dependency | 1 | 1.000 | 0.000 | 0.000 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | none | 1 | 1.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | state_failure | 1 | 1.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | state_dependency | 1 | 1.000 | 0.000 | 0.000 | 0.000 |
| a3_interaction | state_dependency | 1 | 1.000 | 0.000 | 0.000 | 0.000 |
| a4_reuse | state_dependency | 1 | 1.000 | 0.000 | 0.000 | 0.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count | safe_abort_rate | policy_compliance_success_rate | state_repair_success_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a1_recovery | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a2_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a1_recovery | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a2_planner | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| a1_recovery | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| a2_planner | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| a3_interaction | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| a4_reuse | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 1.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | 1.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | 1.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | 1.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | 1.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **no_reuse_evidence**.
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

_ Results generated from commit 1c65a73dd4fa9d0eae83e1d33484c6b0b5621fab. _