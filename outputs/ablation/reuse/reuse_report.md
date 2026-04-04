# ToolClaw Reuse Experiment

| system | pass | rows | success_rate | avg_tool_calls | avg_user_turns | fail_stop_rate |
|---|---:|---:|---:|---:|---:|---:|
| a3_interaction | 1 | 3 | 1.000 | 2.00 | 0.00 | 0.000 |
| a3_interaction | 2 | 3 | 1.000 | 2.00 | 0.00 | 0.000 |
| a4_reuse | 1 | 3 | 1.000 | 2.00 | 0.00 | 0.000 |
| a4_reuse | 2 | 3 | 1.000 | 2.00 | 0.00 | 0.000 |

## Second-Run Delta

| system | success_rate | avg_tool_calls | avg_user_turns | fail_stop_rate |
|---|---:|---:|---:|---:|
| a3_interaction | +0.000 | +0.00 | +0.00 | +0.000 |
| a4_reuse | +0.000 | +0.00 | +0.00 | +0.000 |

## Per-Family First-vs-Second-Run

| system | repeat_family | pass_1_success | pass_2_success | pass_2_reused_artifact | second_run_improvement |
|---|---|---:|---:|---:|---:|
| a3_interaction | task_binding_001 | 1.000 | 1.000 | 0.000 | 0.000 |
| a3_interaction | task_env_001 | 1.000 | 1.000 | 0.000 | 0.000 |
| a3_interaction | task_success_001 | 1.000 | 1.000 | 0.000 | 0.000 |
| a4_reuse | task_binding_001 | 1.000 | 1.000 | 1.000 | 0.000 |
| a4_reuse | task_env_001 | 1.000 | 1.000 | 1.000 | 0.000 |
| a4_reuse | task_success_001 | 1.000 | 1.000 | 1.000 | 0.000 |