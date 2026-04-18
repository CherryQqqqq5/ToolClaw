# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/prepared/toolsandbox.normalized.json`
- samples: `14`
- runs: `3`
- systems: `a0_baseline, a1_recovery, a2_planner, a3_interaction, a4_reuse`
- raw_execution_report: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/latest_run_raw_report.md`
- raw_comparison: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/comparison.raw.csv`
- scored_comparison: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/comparison.scored.csv`
- focused_slice_summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/focused_slice_summary.md`
- reuse_focused_summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/reuse_focused_summary.md`
- per_failure_type_summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/per_failure_type_summary.md`
- repair_loop_summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/repair_loop_summary.md`
- statistical_robustness_summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/statistical_robustness_summary.json`
- failtax_summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/per_failtax_summary.json`

## Readiness

- reuse_scope: `within_invocation`
- asset_registry_root: `none`

- primary_result_ready: `False`
- caution_flags:
  - `no_reference_result_summaries`
  - `proxy_only_result_summaries`
  - `raw_vs_benchmark_success_gap`

## Aggregate

| system | mean_success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | consistency | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a0_baseline | 0.286 | 0.286 | 0.000 | 0.429 | 0.000 | 0.286 | 0.286 | 0.286 | 1.000 | 0.631 | 0.631 | 1.000 | 0.857 | 1.000 | 1.000 | 0.829 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | 0.214 | 0.214 | 0.000 | 0.429 | 0.000 | 0.929 | 0.786 | 0.786 | 1.000 | 0.952 | 0.952 | 1.000 | 1.000 | 1.000 | 0.854 | 0.600 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | 0.429 | 0.429 | 0.000 | 0.429 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.914 | 0.571 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | 0.929 | 0.929 | 0.429 | 0.929 | 0.429 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.914 | 0.371 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | 0.857 | 0.857 | 0.000 | 0.857 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.989 | 0.500 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |

## FailTax Breakdown

| system | primary_failtax | rows | success_rate | pass@k | consistency |
|---|---|---:|---:|---:|---:|
| a0_baseline | ordering | 9 | 0.333 | 0.333 | 1.000 |
| a0_baseline | selection | 1 | 1.000 | 1.000 | 1.000 |
| a0_baseline | state | 4 | 0.000 | 0.000 | 1.000 |
| a1_recovery | ordering | 9 | 0.111 | 0.111 | 1.000 |
| a1_recovery | selection | 1 | 0.000 | 0.000 | 1.000 |
| a1_recovery | state | 4 | 0.500 | 0.500 | 1.000 |
| a2_planner | ordering | 9 | 0.333 | 0.333 | 1.000 |
| a2_planner | selection | 1 | 1.000 | 1.000 | 1.000 |
| a2_planner | state | 4 | 0.500 | 0.500 | 1.000 |
| a3_interaction | ordering | 9 | 0.889 | 0.889 | 1.000 |
| a3_interaction | selection | 1 | 1.000 | 1.000 | 1.000 |
| a3_interaction | state | 4 | 1.000 | 1.000 | 1.000 |
| a4_reuse | ordering | 9 | 0.778 | 0.778 | 1.000 |
| a4_reuse | selection | 1 | 1.000 | 1.000 | 1.000 |
| a4_reuse | state | 4 | 1.000 | 1.000 | 1.000 |

## Category Breakdown

| system | category | rows | success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a0_baseline | canonicalization | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | insufficient_information | 18 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.639 | 0.639 | 1.000 | 1.000 | 1.000 | 1.000 | 0.833 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | multiple_tool | 33 | 0.273 | 0.273 | 0.000 | 0.455 | 0.000 | 0.273 | 0.273 | 0.273 | 0.712 | 0.712 | 1.000 | 0.909 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | multiple_user_turn | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.167 | 0.167 | 1.000 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | planner_sensitive | 12 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.650 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | single_user_turn | 6 | 0.500 | 0.500 | 0.000 | 0.500 | 0.000 | 0.500 | 0.500 | 0.500 | 0.833 | 0.833 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a0_baseline | state_dependency | 18 | 0.500 | 0.500 | 0.000 | 0.833 | 0.000 | 0.500 | 0.500 | 0.500 | 0.667 | 0.667 | 1.000 | 0.667 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | canonicalization | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.850 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | insufficient_information | 18 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.833 | 1.000 | 1.000 | 0.889 | 0.889 | 1.000 | 1.000 | 1.000 | 0.875 | 0.533 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | multiple_tool | 33 | 0.273 | 0.273 | 0.000 | 0.455 | 0.000 | 0.909 | 0.818 | 0.818 | 0.939 | 0.939 | 1.000 | 1.000 | 1.000 | 0.827 | 0.545 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | multiple_user_turn | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.900 | 0.667 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | planner_sensitive | 12 | 0.250 | 0.250 | 0.000 | 1.000 | 0.000 | 1.000 | 0.250 | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.750 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | single_tool | 3 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | single_user_turn | 6 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | 1.000 | 0.500 | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.700 | 1.000 | 0.000 | toolclaw_proxy |
| a1_recovery | state_dependency | 18 | 0.500 | 0.500 | 0.000 | 0.833 | 0.000 | 1.000 | 0.667 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.808 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | canonicalization | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.850 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | insufficient_information | 18 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.850 | 0.433 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | multiple_tool | 33 | 0.455 | 0.455 | 0.000 | 0.455 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.905 | 0.527 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | multiple_user_turn | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.900 | 0.667 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | planner_sensitive | 12 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.650 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | single_user_turn | 6 | 0.500 | 0.500 | 0.000 | 0.500 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | state_dependency | 18 | 0.833 | 0.833 | 0.000 | 0.833 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.975 | 0.667 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | canonicalization | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.850 | 0.200 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | insufficient_information | 18 | 1.000 | 1.000 | 0.833 | 1.000 | 0.833 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.850 | 0.033 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | multiple_tool | 33 | 1.000 | 1.000 | 0.455 | 1.000 | 0.455 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.905 | 0.309 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | multiple_user_turn | 9 | 0.667 | 0.667 | 0.333 | 0.667 | 0.333 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.900 | 0.400 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | planner_sensitive | 12 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.650 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | single_user_turn | 6 | 1.000 | 1.000 | 0.500 | 1.000 | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.925 | 0.400 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | state_dependency | 18 | 0.833 | 0.833 | 0.000 | 0.833 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.975 | 0.667 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | canonicalization | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | insufficient_information | 18 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.975 | 0.200 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | multiple_tool | 33 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.986 | 0.418 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | multiple_user_turn | 9 | 0.333 | 0.333 | 0.000 | 0.333 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | planner_sensitive | 12 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.650 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | single_user_turn | 6 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | state_dependency | 18 | 0.833 | 0.833 | 0.000 | 0.833 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.700 | 1.000 | 0.000 | toolclaw_proxy |

## Result Summary Sources

| system | result_summary_source | rows |
|---|---|---:|
| a0_baseline | toolclaw_proxy | 42 |
| a1_recovery | toolclaw_proxy | 42 |
| a2_planner | toolclaw_proxy | 42 |
| a3_interaction | toolclaw_proxy | 42 |
| a4_reuse | toolclaw_proxy | 42 |

## Failure Type Summary

| system | failure_type | rows | raw_execution_success | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | probe_user_queries | repair_user_queries | patch_success_rate | tool_calls | turn_count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | approval_required | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a0_baseline | binding_failure | 18 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.667 | 2.500 |
| a0_baseline | environment_failure | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 3.000 |
| a0_baseline | multiple_tool | 9 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a0_baseline | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.000 |
| a0_baseline | state_failure | 6 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.500 | 2.500 |
| a1_recovery | approval_required | 3 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a1_recovery | binding_failure | 18 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.667 | 4.500 |
| a1_recovery | environment_failure | 3 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 3.000 | 5.000 |
| a1_recovery | multiple_tool | 9 | 0.333 | 0.333 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 12.667 | 14.000 |
| a1_recovery | single_tool | 3 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| a1_recovery | state_failure | 6 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.500 | 4.500 |
| a2_planner | approval_required | 3 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a2_planner | binding_failure | 18 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 3.000 | 5.000 |
| a2_planner | environment_failure | 3 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 3.000 | 5.000 |
| a2_planner | multiple_tool | 9 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a2_planner | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.000 |
| a2_planner | state_failure | 6 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.500 | 4.500 |
| a3_interaction | approval_required | 3 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.000 | 4.000 |
| a3_interaction | binding_failure | 18 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 3.000 | 7.000 |
| a3_interaction | environment_failure | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 7.000 |
| a3_interaction | multiple_tool | 9 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a3_interaction | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.000 |
| a3_interaction | state_failure | 6 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.500 | 4.500 |
| a4_reuse | approval_required | 3 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.000 | 4.000 |
| a4_reuse | binding_failure | 18 | 1.000 | 0.833 | 0.000 | 0.833 | 0.000 | 0.833 | 0.000 | 0.167 | 2.000 | 5.667 |
| a4_reuse | environment_failure | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 7.000 |
| a4_reuse | multiple_tool | 9 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a4_reuse | single_tool | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.000 |
| a4_reuse | state_failure | 6 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |

## Repair Loop Summary

| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 42 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | 42 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | 42 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 42 | 18 | 0.429 | 0.429 | 0.071 | 0.500 | 0.500 | 0.500 | 0.714 | 0.714 | 0.429 | 0.286 | 0.000 |
| a4_reuse | 42 | 0 | 0.000 | 0.000 | 0.429 | 0.143 | 0.143 | 0.143 | 0.286 | 0.286 | 0.000 | 0.286 | 0.000 |

## Reuse Focused

| system | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 2.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | 2.500 | 0.750 | 0.750 | 0.750 | 0.000 | 0.000 | 0.625 | 0.750 |
| a2_planner | 3.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| a3_interaction | 3.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| a4_reuse | 2.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |

| reuse_delta | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a4_reuse_minus_a0_baseline | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +1.000 | +0.000 | +0.000 |
| a4_reuse_minus_a3_interaction | -1.000 | -1.000 | +0.000 | -1.000 | -1.000 | +1.000 | +0.000 | -1.000 |

## Statistical Robustness

- consistency=1.0 here mainly indicates deterministic replication stability across repeats.
- paired comparison is reported at task level (wins/losses/ties) with bootstrap 95% CI on mean success delta.

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 14 | 0 | 7 | 7 | -0.500 | [-0.714, -0.286] |
| a4_reuse vs a3_interaction | 14 | 0 | 1 | 13 | -0.071 | [-0.214, +0.000] |
| a4_reuse vs a0_baseline | 14 | 8 | 0 | 6 | +0.571 | [+0.357, +0.786] |

### Focused Slice: approval

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 2 | 0 | 1 | 1 | -0.500 | [-1.000, +0.000] |
| a4_reuse vs a3_interaction | 2 | 0 | 1 | 1 | -0.500 | [-1.000, +0.000] |
| a4_reuse vs a0_baseline | 2 | 0 | 0 | 2 | +0.000 | [+0.000, +0.000] |

### Focused Slice: planner_distractor_hard

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 4 | 0 | 0 | 4 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 4 | 0 | 0 | 4 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 4 | 0 | 0 | 4 | +0.000 | [+0.000, +0.000] |

### Focused Slice: repeated_reusable

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 4 | 0 | 4 | 0 | -1.000 | [-1.000, -1.000] |
| a4_reuse vs a3_interaction | 4 | 0 | 0 | 4 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 4 | 4 | 0 | 0 | +1.000 | [+1.000, +1.000] |

### Focused Slice: state_repair

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 2 | 0 | 0 | 2 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 2 | 0 | 0 | 2 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 2 | 2 | 0 | 0 | +1.000 | [+1.000, +1.000] |

## Interpretation

- `mean_success_rate` is computed from strict scored success, not from proxy summaries alone.
- `strict_scored_success` is the benchmark-facing success after the must-interact gate is applied.
- `repair_scored_success` is stricter: it only counts runs that both score successfully and include at least one non-probe repair interaction.
- `interaction_contract_satisfied` can be lifted by an interaction probe; `repair_interaction_satisfied` cannot.
- `raw_trace_success_rate` / `raw_execution_success_rate` are reported separately because executor success and benchmark-verified success can diverge.
- `proxy_summary_success` tracks runs that looked successful under the attached ToolClaw proxy summary path.
- `milestone_signal_coverage` shows whether the trace carried an explicit milestone verification signal; low coverage weakens benchmark claims even if proxy summaries exist.
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