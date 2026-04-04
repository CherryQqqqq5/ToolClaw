# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 665 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 |
| a1_recovery | 665 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.000 |
| a2_planner | 665 | 1.000 | 0.000 | 1.98 | 0.00 | 0.00 | 1.98 | 0.000 |
| a3_interaction | 665 | 1.000 | 0.000 | 1.98 | 0.00 | 0.00 | 1.98 | 0.000 |
| a4_reuse | 665 | 1.000 | 0.000 | 1.98 | 0.00 | 0.00 | 1.98 | 0.000 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.000 |
| avg_tool_calls | -0.02 |
| avg_user_turns | +0.00 |
| fail_stop_rate | +0.000 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate |
|---|---:|---:|---:|---:|
| A0 vs A1 | +0.000 | +0.000 | +0.00 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 |
| A2 vs A3 | +0.000 | +0.000 | +0.00 | +0.000 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | success | 665 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | success | 665 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | success | 665 | 1.000 | 0.000 | 1.98 | 0.00 | 0.00 | 0.000 |
| a3_interaction | success | 665 | 1.000 | 0.000 | 1.98 | 0.00 | 0.00 | 0.000 |
| a4_reuse | success | 665 | 1.000 | 0.000 | 1.98 | 0.00 | 0.00 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **tie**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- Use per-task CSV to inspect failure clusters by scenario and stop_reason.
- If total task count is small (<30), treat this as a pilot rather than a final conclusion.