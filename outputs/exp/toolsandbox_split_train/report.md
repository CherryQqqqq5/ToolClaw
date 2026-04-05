# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.train.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/exp/toolsandbox_split_train/prepared/toolsandbox.normalized.json`
- samples: `5`
- runs: `3`
- systems: `a4_reuse`
- raw_comparison: `outputs/exp/toolsandbox_split_train/comparison.raw.csv`
- scored_comparison: `outputs/exp/toolsandbox_split_train/comparison.scored.csv`
- focused_slice_summary: `outputs/exp/toolsandbox_split_train/focused_slice_summary.md`

## Aggregate

| system | mean_success_rate | pass@k | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a4_reuse | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 0.440 | 1.000 | 0.000 |

## Category Breakdown

| system | category | rows | success_rate | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a4_reuse | canonicalization | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.600 | 1.000 | 0.000 |
| a4_reuse | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.500 | 1.000 | 0.000 |
| a4_reuse | multiple_tool | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.467 | 1.000 | 0.000 |
| a4_reuse | multiple_user_turn | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.100 | 1.000 | 0.000 |
| a4_reuse | single_user_turn | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 |
| a4_reuse | state_dependency | 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.400 | 1.000 | 0.000 |

## Interpretation

- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.
- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.