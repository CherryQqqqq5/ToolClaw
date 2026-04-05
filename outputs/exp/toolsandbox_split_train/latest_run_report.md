# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a4_reuse | 5 | 1.000 | 1.000 | 2.20 | 0.60 | 0.20 | 2.00 | 0.000 | 0.200 | 0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | stop_reason | failure_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---|---|---:|---:|
| toolsandbox_state_dep_001 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 0 | 0.000 |
| toolsandbox_state_dep_002 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | state_dependency | 1 | 0.000 |
| toolsandbox_missing_info_001 | t1_static_recovery | a4_reuse | 1 | 3 | 0 | 1 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| toolsandbox_missing_info_002 | t1_static_recovery | a4_reuse | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_001 | t3_must_interact | a4_reuse | 1 | 2 | 0 | 2 | success_criteria_satisfied | multiple_user_turn | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a4_reuse | binding_failure | 1 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a4_reuse | environment_failure | 1 | 1.000 | 1.000 | 3.00 | 1.00 | 0.00 | 0.000 |
| a4_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a4_reuse | binding_failure | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | environment_failure | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | state_dependency | 2 | 1.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a4_reuse | t1_static_recovery | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t2_dynamic_branching | 2 | 1.000 | 0.500 | 0.000 |
| a4_reuse | t3_must_interact | 1 | 1.000 | 0.000 | 0.000 |

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