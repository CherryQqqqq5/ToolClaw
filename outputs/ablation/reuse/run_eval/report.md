# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 6 | 1.000 | 1.000 | 2.00 | 0.00 | 0.67 | 2.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 6 | 1.000 | 1.000 | 2.00 | 0.00 | 0.33 | 2.00 | 0.000 | 0.833 | 0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 | +0.000 |

## Per-Task Results

| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | stop_reason | failure_type | reused_artifact | second_run_improvement |
|---|---|---|---:|---:|---:|---:|---|---|---:|---:|
| task_success_001__pass1 | t4_repeated_reusable | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_success_001__pass1 | t4_repeated_reusable | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_binding_001__pass1 | t4_repeated_reusable | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| task_binding_001__pass1 | t4_repeated_reusable | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | binding_failure | 1 | 0.000 |
| task_env_001__pass1 | t4_repeated_reusable | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| task_env_001__pass1 | t4_repeated_reusable | a4_reuse | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 1 | 0.000 |
| task_success_001__pass2 | t4_repeated_reusable | a3_interaction | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 0 | 0.000 |
| task_success_001__pass2 | t4_repeated_reusable | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | none | 1 | 0.000 |
| task_binding_001__pass2 | t4_repeated_reusable | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | binding_failure | 0 | 0.000 |
| task_binding_001__pass2 | t4_repeated_reusable | a4_reuse | 1 | 2 | 0 | 0 | success_criteria_satisfied | binding_failure | 1 | 0.000 |
| task_env_001__pass2 | t4_repeated_reusable | a3_interaction | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 0 | 0.000 |
| task_env_001__pass2 | t4_repeated_reusable | a4_reuse | 1 | 2 | 1 | 0 | success_criteria_satisfied | environment_failure | 1 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a3_interaction | environment_failure | 2 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a3_interaction | success | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 2 | 1.000 | 1.000 | 2.00 | 0.00 | 1.00 | 0.000 |
| a4_reuse | success | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 0.000 |
| a3_interaction | environment_failure | 2 | 1.000 | 1.000 | 0.000 |
| a3_interaction | none | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 0.000 | 0.000 |
| a4_reuse | environment_failure | 2 | 1.000 | 1.000 | 0.000 |
| a4_reuse | none | 2 | 1.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a3_interaction | t4_repeated_reusable | 6 | 1.000 | 0.000 | 0.000 |
| a4_reuse | t4_repeated_reusable | 6 | 1.000 | 0.833 | 0.000 |

## Repeated-Family Analysis

| system | repeat_family | pass_1_success | pass_2_success | pass_1_tool_calls | pass_2_tool_calls | pass_1_user_turns | pass_2_user_turns | pass_2_reused_artifact | second_run_improvement |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | task_binding_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| a3_interaction | task_env_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| a3_interaction | task_success_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| a4_reuse | task_binding_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 1.000 | 0.000 |
| a4_reuse | task_env_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 1.000 | 0.000 |
| a4_reuse | task_success_001 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.00 | 1.000 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **inconclusive**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact.
- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.
- Use failure_type and task_family tables to keep benchmark slicing aligned with experimental claims.