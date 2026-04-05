# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 5 | 1.000 | 1.000 | 1.60 | 0.40 | 0.20 | 1.60 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 5 | 1.000 | 1.000 | 1.60 | 0.40 | 0.00 | 1.60 | 0.000 | 0.400 | 0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | stop_reason | failure_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---|---|---:|---:|
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a3_interaction | 1 | 2 | 1 | 2 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| toolsandbox_multi_turn_approval_002 | t1_static_recovery | a4_reuse | 1 | 2 | 0 | 2 | success_criteria_satisfied | binding_failure | 1 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_001 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 0 | 0.000 |
| toolsandbox_canonicalization_002 | t2_dynamic_branching | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | canonicalization | 1 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a3_interaction | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_001 | t0_general | a4_reuse | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a3_interaction | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |
| toolsandbox_single_tool_002 | t2_dynamic_branching | a4_reuse | 1 | 1 | 0 | 0 | success_criteria_satisfied | single_tool | 0 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | binding_failure | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 1.00 | 0.000 |
| a3_interaction | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | single_tool | 2 | 1.000 | 0.000 | 1.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a3_interaction | binding_failure | 1 | 1.000 | 1.000 | 0.000 |
| a3_interaction | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a3_interaction | single_tool | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | canonicalization | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | single_tool | 2 | 1.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a3_interaction | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t1_static_recovery | 1 | 1.000 | 0.000 | 0.000 |
| a3_interaction | t2_dynamic_branching | 3 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t0_general | 1 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t1_static_recovery | 1 | 1.000 | 1.000 | 0.000 |
| a4_reuse | t2_dynamic_branching | 3 | 1.000 | 0.333 | 0.000 |

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