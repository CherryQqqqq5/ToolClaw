# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.official.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/prepared/toolsandbox.normalized.json`
- samples: `1`
- runs: `3`
- systems: `a0_baseline, a1_recovery, a2_planner, a3_interaction, a4_reuse`
- raw_execution_report: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/latest_run_raw_report.md`
- raw_comparison: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/comparison.raw.csv`
- scored_comparison: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/comparison.scored.csv`
- focused_slice_summary: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/focused_slice_summary.md`
- failtax_summary: `/cephfs/qiuyn/ToolClaw/outputs/toolsandbox_bench_official_formal/per_failtax_summary.json`

## Aggregate

| system | mean_success_rate | execution_verified_success | proxy_summary_success | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a0_baseline | 0.000 | 0.000 | 0.000 | 1.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | toolclaw_proxy |
| a1_recovery | 0.000 | 0.000 | 0.000 | 1.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | toolclaw_proxy |
| a2_planner | 0.000 | 0.000 | 0.000 | 1.000 | 0.500 | 0.500 | 0.500 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | toolclaw_proxy |
| a3_interaction | 0.000 | 0.000 | 0.000 | 1.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | toolclaw_proxy |
| a4_reuse | 0.000 | 0.000 | 0.000 | 1.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | toolclaw_proxy |

## FailTax Breakdown

| system | primary_failtax | rows | success_rate | pass@k | consistency |
|---|---|---:|---:|---:|---:|
| a0_baseline | state | 1 | 0.000 | 0.000 | 1.000 |
| a1_recovery | state | 1 | 0.000 | 0.000 | 1.000 |
| a2_planner | state | 1 | 0.000 | 0.000 | 1.000 |
| a3_interaction | state | 1 | 0.000 | 0.000 | 1.000 |
| a4_reuse | state | 1 | 0.000 | 0.000 | 1.000 |

## Category Breakdown

| system | category | rows | success_rate | execution_verified_success | proxy_summary_success | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a0_baseline | multiple_tool | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a0_baseline | multiple_user_turn | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a0_baseline | no_distraction_tools | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a0_baseline | state_dependency | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a1_recovery | multiple_tool | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a1_recovery | multiple_user_turn | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a1_recovery | no_distraction_tools | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a1_recovery | state_dependency | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a2_planner | multiple_tool | 3 | 0.000 | 0.000 | 0.000 | 0.500 | 0.500 | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a2_planner | multiple_user_turn | 3 | 0.000 | 0.000 | 0.000 | 0.500 | 0.500 | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a2_planner | no_distraction_tools | 3 | 0.000 | 0.000 | 0.000 | 0.500 | 0.500 | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a2_planner | state_dependency | 3 | 0.000 | 0.000 | 0.000 | 0.500 | 0.500 | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a3_interaction | multiple_tool | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a3_interaction | multiple_user_turn | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a3_interaction | no_distraction_tools | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a3_interaction | state_dependency | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a4_reuse | multiple_tool | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a4_reuse | multiple_user_turn | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a4_reuse | no_distraction_tools | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |
| a4_reuse | state_dependency | 3 | 0.000 | 0.000 | 0.000 | 0.750 | 0.750 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | toolclaw_proxy |

## Result Summary Sources

| system | result_summary_source | rows |
|---|---|---:|
| a0_baseline | toolclaw_proxy | 3 |
| a1_recovery | toolclaw_proxy | 3 |
| a2_planner | toolclaw_proxy | 3 |
| a3_interaction | toolclaw_proxy | 3 |
| a4_reuse | toolclaw_proxy | 3 |

## Interpretation

- `mean_success_rate` is computed from `execution_verified_success`, not from proxy summaries alone.
- `proxy_summary_success` tracks runs that looked successful under the attached ToolClaw proxy summary path.
- `result_summary_source` is reported explicitly so proxy-derived runs are visible in the main report.
- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.
- FailTax is the default slicing axis for phase-2 style failure studies; category tables remain useful but secondary.
- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.
- `latest_run_raw_report.md` preserves the raw `run_eval.py` report so it is not confused with this scored benchmark report.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.
- `budget_violation_rate` and `recovery_budget_used` are the budget-side controls for phase-2 evaluation.