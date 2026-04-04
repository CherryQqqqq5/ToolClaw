# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 8 | 0.375 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.625 |
| a1_recovery | 8 | 0.250 | 0.250 | 1.00 | 0.00 | 0.25 | 2.00 | 0.750 |
| a2_planner | 8 | 0.250 | 0.250 | 1.00 | 0.00 | 0.25 | 2.00 | 0.750 |
| a3_interaction | 8 | 0.625 | 0.625 | 2.12 | 1.38 | 0.38 | 2.00 | 0.375 |
| a4_reuse | 8 | 0.625 | 0.625 | 2.12 | 1.38 | 0.38 | 2.00 | 0.375 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.250 |
| avg_tool_calls | +0.12 |
| avg_user_turns | +1.38 |
| fail_stop_rate | -0.250 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate |
|---|---:|---:|---:|---:|
| A0 vs A1 | -0.125 | +0.250 | +0.00 | +0.125 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 |
| A2 vs A3 | +0.375 | +0.375 | +1.38 | -0.375 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | approval_required | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | dual_control | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | environment_failure | 3 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | policy_failure | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | approval_required | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| a1_recovery | dual_control | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | environment_failure | 3 | 0.333 | 0.333 | 2.00 | 0.00 | 0.33 | 0.667 |
| a1_recovery | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | approval_required | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| a2_planner | dual_control | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | environment_failure | 3 | 0.333 | 0.333 | 2.00 | 0.00 | 0.33 | 0.667 |
| a2_planner | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a3_interaction | approval_required | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a3_interaction | dual_control | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | environment_failure | 3 | 0.333 | 0.333 | 3.00 | 1.33 | 0.33 | 0.667 |
| a3_interaction | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 1.00 | 0.00 | 1.000 |
| a4_reuse | approval_required | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a4_reuse | dual_control | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 3 | 0.333 | 0.333 | 3.00 | 1.33 | 0.33 | 0.667 |
| a4_reuse | policy_failure | 1 | 0.000 | 0.000 | 0.00 | 1.00 | 0.00 | 1.000 |

## Interpretation (auto-generated)

- Verdict: **a4_reuse_advantage**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- Use per-task CSV to inspect failure clusters by scenario and stop_reason.
- If total task count is small (<30), treat this as a pilot rather than a final conclusion.