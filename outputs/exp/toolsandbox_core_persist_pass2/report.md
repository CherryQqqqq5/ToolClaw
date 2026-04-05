# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.official.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/exp/toolsandbox_core_persist_pass2/prepared/toolsandbox.normalized.json`
- samples: `10`
- runs: `3`
- systems: `a3_interaction, a4_reuse`
- raw_comparison: `outputs/exp/toolsandbox_core_persist_pass2/comparison.raw.csv`
- scored_comparison: `outputs/exp/toolsandbox_core_persist_pass2/comparison.scored.csv`
- focused_slice_summary: `outputs/exp/toolsandbox_core_persist_pass2/focused_slice_summary.md`

## Aggregate

| system | mean_success_rate | pass@k | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 0.520 | 1.000 | 0.000 |
| a4_reuse | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 0.480 | 1.000 | 0.000 |

## Category Breakdown

| system | category | rows | success_rate | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a3_interaction | canonicalization | 15 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.560 | 1.000 | 0.000 |
| a3_interaction | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.500 | 1.000 | 0.000 |
| a3_interaction | multiple_tool | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 | 0.500 | 1.000 | 0.000 |
| a3_interaction | multiple_user_turn | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.133 | 1.000 | 0.000 |
| a3_interaction | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a3_interaction | single_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a3_interaction | state_dependency | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |
| a4_reuse | canonicalization | 15 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.520 | 1.000 | 0.000 |
| a4_reuse | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.400 | 1.000 | 0.000 |
| a4_reuse | multiple_tool | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 | 0.500 | 1.000 | 0.000 |
| a4_reuse | multiple_user_turn | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.067 | 1.000 | 0.000 |
| a4_reuse | single_tool | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a4_reuse | single_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 |
| a4_reuse | state_dependency | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 | 1.000 | 0.000 |

## Interpretation

- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.
- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.