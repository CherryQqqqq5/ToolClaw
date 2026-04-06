# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/remote/toolsandbox_matched_20260406_090111/prepared/toolsandbox.normalized.json`
- samples: `10`
- runs: `3`
- systems: `tc_full, tc_no_repair, tc_no_fallback, tc_no_reuse, tc_planner_only`
- raw_comparison: `outputs/remote/toolsandbox_matched_20260406_090111/comparison.raw.csv`
- scored_comparison: `outputs/remote/toolsandbox_matched_20260406_090111/comparison.scored.csv`
- focused_slice_summary: `outputs/remote/toolsandbox_matched_20260406_090111/focused_slice_summary.md`

## Aggregate

| system | mean_success_rate | pass@k | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tc_full | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 0.500 | 1.000 | 0.000 |
| tc_no_repair | 0.700 | 0.700 | 1.000 | 0.817 | 0.817 | 1.000 | 1.000 | 1.000 | 0.600 | 1.000 | 0.000 |
| tc_no_fallback | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 0.520 | 1.000 | 0.000 |
| tc_no_reuse | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 0.520 | 1.000 | 0.000 |
| tc_planner_only | 0.700 | 0.700 | 1.000 | 0.733 | 0.733 | 0.900 | 1.000 | 1.000 | 0.780 | 1.000 | 0.000 |

## Category Breakdown

| system | category | rows | success_rate | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tc_full | canonicalization | 15 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.520 | 1.000 | 0.000 |
| tc_full | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.500 | 1.000 | 0.000 |
| tc_full | multiple_tool | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 | 0.500 | 1.000 | 0.000 |
| tc_full | multiple_user_turn | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.067 | 1.000 | 0.000 |
| tc_full | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_full | single_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_full | state_dependency | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |
| tc_no_repair | canonicalization | 15 | 0.800 | 0.900 | 0.900 | 1.000 | 1.000 | 1.000 | 0.560 | 1.000 | 0.000 |
| tc_no_repair | insufficient_information | 6 | 0.000 | 0.333 | 0.333 | 1.000 | 1.000 | 1.000 | 0.900 | 1.000 | 0.000 |
| tc_no_repair | multiple_tool | 12 | 0.750 | 0.833 | 0.833 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| tc_no_repair | multiple_user_turn | 9 | 0.333 | 0.611 | 0.611 | 1.000 | 1.000 | 1.000 | 0.400 | 1.000 | 0.000 |
| tc_no_repair | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_no_repair | single_user_turn | 6 | 0.500 | 0.667 | 0.667 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_no_repair | state_dependency | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |
| tc_no_fallback | canonicalization | 15 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.560 | 1.000 | 0.000 |
| tc_no_fallback | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.500 | 1.000 | 0.000 |
| tc_no_fallback | multiple_tool | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 | 0.500 | 1.000 | 0.000 |
| tc_no_fallback | multiple_user_turn | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.133 | 1.000 | 0.000 |
| tc_no_fallback | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_no_fallback | single_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_no_fallback | state_dependency | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |
| tc_no_reuse | canonicalization | 15 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.560 | 1.000 | 0.000 |
| tc_no_reuse | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.500 | 1.000 | 0.000 |
| tc_no_reuse | multiple_tool | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 | 0.500 | 1.000 | 0.000 |
| tc_no_reuse | multiple_user_turn | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.133 | 1.000 | 0.000 |
| tc_no_reuse | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_no_reuse | single_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_no_reuse | state_dependency | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |
| tc_planner_only | canonicalization | 15 | 0.800 | 0.800 | 0.800 | 1.000 | 1.000 | 1.000 | 0.720 | 1.000 | 0.000 |
| tc_planner_only | insufficient_information | 6 | 0.500 | 0.667 | 0.667 | 1.000 | 1.000 | 1.000 | 0.900 | 1.000 | 0.000 |
| tc_planner_only | multiple_tool | 12 | 0.750 | 0.833 | 0.833 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| tc_planner_only | multiple_user_turn | 9 | 0.000 | 0.111 | 0.111 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| tc_planner_only | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_planner_only | single_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| tc_planner_only | state_dependency | 12 | 0.750 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |

## Interpretation

- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.
- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.