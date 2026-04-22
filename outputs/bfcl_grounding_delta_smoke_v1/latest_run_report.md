# ToolClaw Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | budget_violation_rate | mean_second_run_improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 4 | 0.750 | 0.000 | 0.75 | 0.00 | 0.00 | 0.75 | 0.000 | 0.0 | 0.250 | 0.000 | 0.000 |
| fc_preflight_only | 4 | 0.250 | 0.000 | 0.00 | 0.00 | 0.00 | 0.75 | 0.000 | 0.0 | 0.750 | 0.000 | 0.000 |
| fc_grounding_recovery | 4 | 0.750 | 0.000 | 0.75 | 0.00 | 0.00 | 0.75 | 0.000 | 0.0 | 0.250 | 0.000 | 0.000 |
| a4_reuse | 4 | 0.750 | 0.000 | 0.75 | 0.00 | 0.00 | 0.75 | 0.000 | 0.0 | 0.250 | 0.000 | 0.000 |

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

## Per-Task Results

| task_id | task_family | system | primary_failtax | success | tool_calls | repair_actions | user_turns | recovery_budget_used | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| live_irrelevance_120-9-0 | t0_general | a0_baseline | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_irrelevance_120-9-0 | t0_general | fc_preflight_only | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_120-9-0 | t0_general | fc_grounding_recovery | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_irrelevance_120-9-0 | t0_general | a4_reuse | recovery | 1 | 0 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_2-1-0 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | a0_baseline | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | fc_grounding_recovery | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_4-2-1 | t0_general | a4_reuse | recovery | 1 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |
| live_multiple_13-4-5 | t0_general | a0_baseline | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | none | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | fc_preflight_only | recovery | 0 | 0 | 0 | 0 | 0.00 | repair_disabled | bfcl | bfcl | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | fc_grounding_recovery | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 0 | 0.000 |
| live_multiple_13-4-5 | t0_general | a4_reuse | recovery | 0 | 1 | 0 | 0 | 0.00 | success_criteria_satisfied | bfcl | bfcl | 1 | 0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | bfcl | 4 | 0.750 | 0.000 | 0.75 | 0.00 | 0.00 | 0.250 |
| a4_reuse | bfcl | 4 | 0.750 | 0.000 | 0.75 | 0.00 | 0.00 | 0.250 |
| fc_grounding_recovery | bfcl | 4 | 0.750 | 0.000 | 0.75 | 0.00 | 0.00 | 0.250 |
| fc_preflight_only | bfcl | 4 | 0.250 | 0.000 | 0.00 | 0.00 | 0.00 | 0.750 |

## FailTax Breakdown

| system | primary_failtax | tasks | success_rate | repair_success_rate | fail_stop_rate | avg_recovery_budget_used |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | recovery | 4 | 0.750 | 0.000 | 0.250 | 0.00 |
| a4_reuse | recovery | 4 | 0.750 | 0.000 | 0.250 | 0.00 |
| fc_grounding_recovery | recovery | 4 | 0.750 | 0.000 | 0.250 | 0.00 |
| fc_preflight_only | recovery | 4 | 0.250 | 0.000 | 0.750 | 0.00 |

## Failure-Type Breakdown

| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |
|---|---|---:|---:|---:|---:|
| a0_baseline | bfcl | 4 | 0.750 | 0.000 | 0.250 |
| a4_reuse | bfcl | 4 | 0.750 | 0.000 | 0.250 |
| fc_grounding_recovery | bfcl | 4 | 0.750 | 0.000 | 0.250 |
| fc_preflight_only | bfcl | 4 | 0.250 | 0.000 | 0.750 |

## Observed Error-Type Breakdown

| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | none | 4 | 0.750 | 0.000 | 0.000 | 0.000 |
| a4_reuse | bfcl | 4 | 0.750 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | bfcl | 4 | 0.750 | 0.000 | 0.000 | 0.000 |
| fc_preflight_only | bfcl | 4 | 0.250 | 0.000 | 0.000 | 0.000 |

## Interaction Quality

| system | clarification_precision | clarification_recall | unnecessary_question_rate | patch_success_rate | post_answer_retry_count | safe_abort_rate | policy_compliance_success_rate | state_repair_success_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_preflight_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| fc_grounding_recovery | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |

## Task-Family Breakdown

| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |
|---|---|---:|---:|---:|---:|
| a0_baseline | t0_general | 4 | 0.750 | 0.000 | 0.000 |
| a4_reuse | t0_general | 4 | 0.750 | 0.500 | 0.000 |
| fc_grounding_recovery | t0_general | 4 | 0.750 | 0.000 | 0.000 |
| fc_preflight_only | t0_general | 4 | 0.250 | 0.000 | 0.000 |

## Recovery And Cost

| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_preflight_only | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |
| a4_reuse | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.0 | 0.00 | 0.000 |

## Budget Pareto Views

| system | success_rate | avg_tool_calls | avg_user_turns | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---:|---:|---:|---:|
| a0_baseline | 0.750 | 0.75 | 0.00 | 0.00 | 0.000 |
| fc_preflight_only | 0.250 | 0.00 | 0.00 | 0.00 | 0.000 |
| fc_grounding_recovery | 0.750 | 0.75 | 0.00 | 0.00 | 0.000 |
| a4_reuse | 0.750 | 0.75 | 0.00 | 0.00 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **tie**.
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

_ Results generated from commit b2bf49e05f3292970bae637c8ab4dd38b4815130. _