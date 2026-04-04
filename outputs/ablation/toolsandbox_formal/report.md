# ToolSandbox Benchmark Report

- source: `/Users/cherry/Documents/ToolClaw/data/toolsandbox.formal.official.json`
- normalized_taskset: `/Users/cherry/Documents/ToolClaw/outputs/ablation/toolsandbox_formal/prepared/toolsandbox.normalized.json`
- samples: `10`
- runs: `1`
- systems: `a0_baseline, a1_recovery, a2_planner, a3_interaction, a4_reuse`

## Aggregate

| system | mean_success_rate | pass@k | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 0.700 | 0.700 | 1.000 | 0.792 | 0.792 | 1.000 | 1.000 | 1.000 | 0.760 | 1.000 | 0.000 |
| a1_recovery | 0.700 | 0.700 | 1.000 | 0.733 | 0.733 | 0.900 | 1.000 | 1.000 | 0.780 | 1.000 | 0.000 |
| a2_planner | 0.700 | 0.700 | 1.000 | 0.733 | 0.733 | 0.900 | 1.000 | 0.970 | 0.740 | 1.000 | 0.000 |
| a3_interaction | 0.900 | 0.900 | 1.000 | 0.967 | 0.967 | 1.000 | 1.000 | 0.835 | 0.340 | 1.000 | 0.000 |
| a4_reuse | 0.900 | 0.900 | 1.000 | 0.967 | 0.967 | 1.000 | 1.000 | 0.835 | 0.300 | 1.000 | 0.000 |

## Category Breakdown

| system | category | rows | success_rate | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | canonicalization | 5 | 0.800 | 0.850 | 0.850 | 1.000 | 1.000 | 1.000 | 0.720 | 1.000 | 0.000 |
| a0_baseline | insufficient_information | 2 | 0.000 | 0.333 | 0.333 | 1.000 | 1.000 | 1.000 | 0.900 | 1.000 | 0.000 |
| a0_baseline | multiple_tool | 4 | 0.750 | 0.833 | 0.833 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| a0_baseline | multiple_user_turn | 3 | 0.333 | 0.528 | 0.528 | 1.000 | 1.000 | 1.000 | 0.933 | 1.000 | 0.000 |
| a0_baseline | single_tool | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a0_baseline | single_user_turn | 2 | 0.500 | 0.667 | 0.667 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a0_baseline | state_dependency | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.650 | 1.000 | 0.000 |
| a1_recovery | canonicalization | 5 | 0.800 | 0.800 | 0.800 | 1.000 | 1.000 | 1.000 | 0.720 | 1.000 | 0.000 |
| a1_recovery | insufficient_information | 2 | 0.500 | 0.667 | 0.667 | 1.000 | 1.000 | 1.000 | 0.900 | 1.000 | 0.000 |
| a1_recovery | multiple_tool | 4 | 0.750 | 0.833 | 0.833 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| a1_recovery | multiple_user_turn | 3 | 0.000 | 0.111 | 0.111 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| a1_recovery | single_tool | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a1_recovery | single_user_turn | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a1_recovery | state_dependency | 4 | 0.750 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| a2_planner | canonicalization | 5 | 0.800 | 0.800 | 0.800 | 1.000 | 1.000 | 0.970 | 0.680 | 1.000 | 0.000 |
| a2_planner | insufficient_information | 2 | 0.500 | 0.667 | 0.667 | 1.000 | 1.000 | 1.000 | 0.900 | 1.000 | 0.000 |
| a2_planner | multiple_tool | 4 | 0.750 | 0.833 | 0.833 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| a2_planner | multiple_user_turn | 3 | 0.000 | 0.111 | 0.111 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| a2_planner | single_tool | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.850 | 0.600 | 1.000 | 0.000 |
| a2_planner | single_user_turn | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.700 | 1.000 | 0.000 |
| a2_planner | state_dependency | 4 | 0.750 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| a3_interaction | canonicalization | 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.880 | 0.400 | 1.000 | 0.000 |
| a3_interaction | insufficient_information | 2 | 0.500 | 0.833 | 0.833 | 1.000 | 1.000 | 0.775 | 0.400 | 1.000 | 0.000 |
| a3_interaction | multiple_tool | 4 | 0.750 | 0.917 | 0.917 | 1.000 | 1.000 | 0.887 | 0.450 | 1.000 | 0.000 |
| a3_interaction | multiple_user_turn | 3 | 0.667 | 0.889 | 0.889 | 1.000 | 1.000 | 0.850 | 0.067 | 1.000 | 0.000 |
| a3_interaction | single_tool | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.400 | 0.000 | 1.000 | 0.000 |
| a3_interaction | single_user_turn | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.700 | 0.400 | 1.000 | 0.000 |
| a3_interaction | state_dependency | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |
| a4_reuse | canonicalization | 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.880 | 0.360 | 1.000 | 0.000 |
| a4_reuse | insufficient_information | 2 | 0.500 | 0.833 | 0.833 | 1.000 | 1.000 | 0.775 | 0.300 | 1.000 | 0.000 |
| a4_reuse | multiple_tool | 4 | 0.750 | 0.917 | 0.917 | 1.000 | 1.000 | 0.887 | 0.450 | 1.000 | 0.000 |
| a4_reuse | multiple_user_turn | 3 | 0.667 | 0.889 | 0.889 | 1.000 | 1.000 | 0.850 | 0.000 | 1.000 | 0.000 |
| a4_reuse | single_tool | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.400 | 0.000 | 1.000 | 0.000 |
| a4_reuse | single_user_turn | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.700 | 0.300 | 1.000 | 0.000 |
| a4_reuse | state_dependency | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |

## Interpretation

- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.