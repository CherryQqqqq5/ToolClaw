# ToolSandbox Focused Slice Summary

Focused categories:
- insufficient_information, multiple_user_turn, single_tool

| system | category | success_rate | milestone_similarity | interaction_efficiency | tool_efficiency | turn_efficiency |
|---|---|---:|---:|---:|---:|---:|
| a0_baseline | insufficient_information | 0.000 | 0.333 | 0.000 | 1.000 | 0.900 |
| a0_baseline | multiple_user_turn | 0.333 | 0.528 | 0.283 | 1.000 | 0.933 |
| a0_baseline | single_tool | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 |
| a1_recovery | insufficient_information | 0.500 | 0.667 | 0.425 | 1.000 | 0.900 |
| a1_recovery | multiple_user_turn | 0.000 | 0.111 | 0.000 | 1.000 | 1.000 |
| a1_recovery | single_tool | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 |
| a2_planner | insufficient_information | 0.500 | 0.667 | 0.425 | 1.000 | 0.900 |
| a2_planner | multiple_user_turn | 0.000 | 0.111 | 0.000 | 1.000 | 1.000 |
| a2_planner | single_tool | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 |
| a3_interaction | insufficient_information | 1.000 | 1.000 | 0.625 | 0.925 | 0.500 |
| a3_interaction | multiple_user_turn | 1.000 | 1.000 | 0.350 | 0.950 | 0.133 |
| a3_interaction | single_tool | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 |
| a4_reuse | insufficient_information | 1.000 | 1.000 | 0.625 | 0.925 | 0.500 |
| a4_reuse | multiple_user_turn | 1.000 | 1.000 | 0.300 | 0.950 | 0.067 |
| a4_reuse | single_tool | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 |

## Focused Deltas

| delta | category | success_rate | milestone_similarity | interaction_efficiency | tool_efficiency | turn_efficiency |
|---|---|---:|---:|---:|---:|---:|
| a3_interaction_minus_a0_baseline | insufficient_information | +1.000 | +0.667 | +0.625 | -0.075 | -0.400 |
| a3_interaction_minus_a0_baseline | multiple_user_turn | +0.667 | +0.472 | +0.067 | -0.050 | -0.800 |
| a3_interaction_minus_a0_baseline | single_tool | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |
| a3_interaction_minus_a1_recovery | insufficient_information | +0.500 | +0.333 | +0.200 | -0.075 | -0.400 |
| a3_interaction_minus_a1_recovery | multiple_user_turn | +1.000 | +0.889 | +0.350 | -0.050 | -0.867 |
| a3_interaction_minus_a1_recovery | single_tool | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |
| a3_interaction_minus_a2_planner | insufficient_information | +0.500 | +0.333 | +0.200 | -0.075 | -0.400 |
| a3_interaction_minus_a2_planner | multiple_user_turn | +1.000 | +0.889 | +0.350 | -0.050 | -0.867 |
| a3_interaction_minus_a2_planner | single_tool | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |
| a4_reuse_minus_a3_interaction | insufficient_information | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |
| a4_reuse_minus_a3_interaction | multiple_user_turn | +0.000 | +0.000 | -0.050 | +0.000 | -0.067 |
| a4_reuse_minus_a3_interaction | single_tool | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |