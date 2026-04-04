# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 10 | 0.700 | 0.000 | 2.00 | 0.00 | 0.00 | 2.00 | 0.300 |
| a1_recovery | 10 | 0.700 | 0.250 | 1.60 | 0.00 | 0.10 | 2.00 | 0.300 |
| a2_planner | 10 | 0.700 | 0.250 | 1.60 | 0.00 | 0.10 | 2.00 | 0.300 |
| a3_interaction | 10 | 0.900 | 0.750 | 2.30 | 0.70 | 0.20 | 2.00 | 0.100 |
| a4_reuse | 10 | 0.900 | 0.750 | 2.30 | 0.70 | 0.20 | 2.00 | 0.100 |

## Delta (A4 Reuse vs A0 Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.200 |
| avg_tool_calls | +0.30 |
| avg_user_turns | +0.70 |
| fail_stop_rate | -0.200 |

## Ablation Deltas

| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate |
|---|---:|---:|---:|---:|
| A0 vs A1 | +0.000 | +0.250 | +0.00 | +0.000 |
| A1 vs A2 | +0.000 | +0.000 | +0.00 | +0.000 |
| A2 vs A3 | +0.200 | +0.500 | +0.70 | -0.200 |
| A3 vs A4 | +0.000 | +0.000 | +0.00 | +0.000 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | binding_failure | 2 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a0_baseline | multiple_user_turn | 1 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | single_tool | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a0_baseline | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| a1_recovery | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | multiple_user_turn | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a1_recovery | single_tool | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a1_recovery | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | binding_failure | 2 | 0.500 | 0.500 | 1.00 | 0.00 | 0.50 | 0.500 |
| a2_planner | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | environment_failure | 1 | 0.000 | 0.000 | 2.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | multiple_user_turn | 1 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 | 1.000 |
| a2_planner | single_tool | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a2_planner | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a3_interaction | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | environment_failure | 1 | 0.000 | 0.000 | 5.00 | 3.00 | 0.00 | 1.000 |
| a3_interaction | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a3_interaction | single_tool | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a3_interaction | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | binding_failure | 2 | 1.000 | 1.000 | 2.00 | 1.00 | 1.00 | 0.000 |
| a4_reuse | canonicalization | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | environment_failure | 1 | 0.000 | 0.000 | 5.00 | 3.00 | 0.00 | 1.000 |
| a4_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 2.00 | 2.00 | 0.00 | 0.000 |
| a4_reuse | single_tool | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |
| a4_reuse | state_dependency | 2 | 1.000 | 0.000 | 2.00 | 0.00 | 0.00 | 0.000 |

## Interpretation (auto-generated)

- Verdict: **a4_reuse_advantage**.
- Compare success_rate first; this is the primary reliability indicator.
- repair_success_rate isolates whether triggered recovery paths actually salvage runs.
- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.
- fail_stop_rate should fall as recovery and interaction layers are added.
- Use per-task CSV to inspect failure clusters by scenario and stop_reason.
- If total task count is small (<30), treat this as a pilot rather than a final conclusion.