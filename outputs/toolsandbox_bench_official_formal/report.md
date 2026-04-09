# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.official.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/prepared/toolsandbox.normalized.json`
- samples: `1`
- runs: `1`
- systems: `a0_baseline, a1_recovery, a2_planner, a3_interaction, a4_reuse`
- raw_comparison: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/comparison.raw.csv`
- scored_comparison: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/comparison.scored.csv`
- focused_slice_summary: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/focused_slice_summary.md`
- failtax_summary: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/per_failtax_summary.json`

## Aggregate

| system | mean_success_rate | pass@k | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| a1_recovery | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| a2_planner | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| a3_interaction | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| a4_reuse | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |

## FailTax Breakdown

| system | primary_failtax | rows | success_rate | pass@k | consistency |
|---|---|---:|---:|---:|---:|
| a0_baseline | state | 1 | 1.000 | 1.000 | 1.000 |
| a1_recovery | state | 1 | 1.000 | 1.000 | 1.000 |
| a2_planner | state | 1 | 1.000 | 1.000 | 1.000 |
| a3_interaction | state | 1 | 1.000 | 1.000 | 1.000 |
| a4_reuse | state | 1 | 1.000 | 1.000 | 1.000 |

## Category Breakdown

| system | category | rows | success_rate | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | multiple_tool | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a0_baseline | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a0_baseline | no_distraction_tools | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a0_baseline | state_dependency | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a1_recovery | multiple_tool | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a1_recovery | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a1_recovery | no_distraction_tools | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a1_recovery | state_dependency | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a2_planner | multiple_tool | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a2_planner | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a2_planner | no_distraction_tools | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a2_planner | state_dependency | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | multiple_tool | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | no_distraction_tools | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_interaction | state_dependency | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | multiple_tool | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | multiple_user_turn | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | no_distraction_tools | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a4_reuse | state_dependency | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.
- FailTax is the default slicing axis for phase-2 style failure studies; category tables remain useful but secondary.
- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.
- `budget_violation_rate` and `recovery_budget_used` are the budget-side controls for phase-2 evaluation.