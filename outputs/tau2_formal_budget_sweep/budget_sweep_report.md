# Tau2-Bench Budget Sweep

- source: `/cephfs/qiuyn/ToolClaw/data/tau2_bench.formal.json`
- mode: `planner`

## Frontier

| sweep | value | system | success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_recovery_budget_used | budget_violation_rate |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| max_user_turns | 0 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_user_turns | 0 | a3_interaction | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.750 |
| max_user_turns | 0 | a4_reuse | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.750 |
| max_user_turns | 1 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_user_turns | 1 | a3_interaction | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_user_turns | 1 | a4_reuse | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_user_turns | 2 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_user_turns | 2 | a3_interaction | 0.500 | 1.92 | 1.00 | 0.17 | 1.58 | 0.500 |
| max_user_turns | 2 | a4_reuse | 0.500 | 1.92 | 1.00 | 0.17 | 1.58 | 0.500 |
| max_repair_attempts | 0 | a2_planner | 0.083 | 1.33 | 0.00 | 0.00 | 0.58 | 0.583 |
| max_repair_attempts | 0 | a3_interaction | 0.167 | 1.58 | 0.33 | 0.00 | 0.92 | 0.833 |
| max_repair_attempts | 0 | a4_reuse | 0.167 | 1.58 | 0.33 | 0.00 | 0.92 | 0.833 |
| max_repair_attempts | 1 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_repair_attempts | 1 | a3_interaction | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_repair_attempts | 1 | a4_reuse | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_repair_attempts | 2 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_repair_attempts | 2 | a3_interaction | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_repair_attempts | 2 | a4_reuse | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_tool_calls | 2 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_tool_calls | 2 | a3_interaction | 0.333 | 1.75 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_tool_calls | 2 | a4_reuse | 0.333 | 1.75 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_tool_calls | 3 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_tool_calls | 3 | a3_interaction | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_tool_calls | 3 | a4_reuse | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_tool_calls | 4 | a2_planner | 0.250 | 1.50 | 0.00 | 0.17 | 0.58 | 0.000 |
| max_tool_calls | 4 | a3_interaction | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |
| max_tool_calls | 4 | a4_reuse | 0.500 | 1.92 | 0.75 | 0.17 | 1.33 | 0.500 |