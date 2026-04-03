# ToolClaw Phase-1 Evaluation Report

## Aggregate Comparison

| system | tasks | success_rate | avg_tool_calls | avg_repair_actions | avg_total_steps |
|---|---:|---:|---:|---:|---:|
| baseline | 3 | 0.333 | 2.00 | 0.00 | 2.00 |
| toolclaw_lite | 3 | 1.000 | 2.00 | 0.67 | 2.00 |

## Delta (ToolClaw-lite vs Baseline)

| metric | delta |
|---|---:|
| success_rate | +0.667 |
| avg_tool_calls | +0.00 |
| avg_repair_actions | +0.67 |

## Scenario Breakdown

| system | scenario | tasks | success_rate | avg_tool_calls | avg_repair_actions |
|---|---|---:|---:|---:|---:|
| baseline | binding_failure | 1 | 0.000 | 2.00 | 0.00 |
| baseline | environment_failure | 1 | 0.000 | 2.00 | 0.00 |
| baseline | success | 1 | 1.000 | 2.00 | 0.00 |
| toolclaw_lite | binding_failure | 1 | 1.000 | 2.00 | 1.00 |
| toolclaw_lite | environment_failure | 1 | 1.000 | 2.00 | 1.00 |
| toolclaw_lite | success | 1 | 1.000 | 2.00 | 0.00 |

## Interpretation (auto-generated)

- Verdict: **toolclaw_lite_advantage**.
- Compare success_rate first; this is the primary reliability indicator.
- If ToolClaw-lite has higher success_rate with moderate call overhead, workflow intelligence is helping.
- Use per-task CSV to inspect failure clusters by scenario and stop_reason.
- If total task count is small (<30), treat this as a pilot rather than a final conclusion.