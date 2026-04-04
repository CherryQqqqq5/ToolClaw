# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 16 | 0.625 | 0.625 | 2.12 | 1.38 | 0.38 | 2.00 | 0.375 |
| a4_reuse | 16 | 0.625 | 0.625 | 2.12 | 1.38 | 0.38 | 2.00 | 0.375 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate |
|---|---:|---:|---:|---:|
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | approval_required | 2 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | binding_failure | 4 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a3_interaction | dual_control | 2 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | environment_failure | 6 | 0.333 | 0.333 | 3.00 | 1.33 | 0.33 | 0.667 |
| a3_interaction | policy_failure | 2 | 0.000 | 0.000 | 0.00 | 1.00 | 0.00 | 1.000 |
| a4_reuse | approval_required | 2 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 4 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a4_reuse | dual_control | 2 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 6 | 0.333 | 0.333 | 3.00 | 1.33 | 0.33 | 0.667 |
| a4_reuse | policy_failure | 2 | 0.000 | 0.000 | 0.00 | 1.00 | 0.00 | 1.000 |

## Interpretation (auto-generated)

- Verdict: **inconclusive**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- Use per-task CSV to inspect failure clusters by scenario and stop_reason.
- If total task count is small (<30), treat this as a pilot rather than a final conclusion.