# ToolSandbox Benchmark Report

- source: `/Users/cherry/mnt/ToolClaw/data/toolsandbox.formal.official.json`
- normalized_taskset: `/Users/cherry/mnt/ToolClaw/outputs/paper_causal_v2_full_r1/prepared/toolsandbox.normalized.json`
- samples: `88`
- runs: `1`
- systems: `a2_planner, a3_full_interaction, a3_no_query, a3_noisy_user`
- raw_execution_report: `outputs/paper_causal_v2_full_r1/latest_run_raw_report.md`
- raw_comparison: `outputs/paper_causal_v2_full_r1/comparison.raw.csv`
- scored_comparison: `outputs/paper_causal_v2_full_r1/comparison.scored.csv`
- focused_slice_summary: `outputs/paper_causal_v2_full_r1/focused_slice_summary.md`
- reuse_focused_summary: `outputs/paper_causal_v2_full_r1/reuse_focused_summary.md`
- per_failure_type_summary: `outputs/paper_causal_v2_full_r1/per_failure_type_summary.md`
- repair_loop_summary: `outputs/paper_causal_v2_full_r1/repair_loop_summary.md`
- statistical_robustness_summary: `outputs/paper_causal_v2_full_r1/statistical_robustness_summary.json`
- failtax_summary: `outputs/paper_causal_v2_full_r1/per_failtax_summary.json`

## Readiness

- reuse_scope: `within_invocation`
- asset_registry_root: `none`

- primary_result_ready: `False`
- caution_flags:
  - `raw_vs_benchmark_success_gap`

## Aggregate

| system | mean_success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | consistency | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a2_planner | 0.625 | 0.625 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.932 | 0.932 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | 1.000 | 1.000 | 0.375 | 1.000 | 0.375 | 0.068 | 0.068 | 0.068 | 0.068 | 0.068 | 0.375 | 0.239 | 1.000 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | 0.625 | 0.625 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.932 | 0.932 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | 0.932 | 0.932 | 0.307 | 1.000 | 0.375 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.375 | 0.239 | 0.932 | 0.932 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |

## FailTax Breakdown

| system | primary_failtax | rows | success_rate | pass@k | consistency |
|---|---|---:|---:|---:|---:|
| a2_planner | ordering | 14 | 0.429 | 0.429 | 1.000 |
| a2_planner | selection | 60 | 0.750 | 0.750 | 1.000 |
| a2_planner | state | 14 | 0.286 | 0.286 | 1.000 |
| a3_full_interaction | ordering | 14 | 1.000 | 1.000 | 1.000 |
| a3_full_interaction | selection | 60 | 1.000 | 1.000 | 1.000 |
| a3_full_interaction | state | 14 | 1.000 | 1.000 | 1.000 |
| a3_no_query | ordering | 14 | 0.429 | 0.429 | 1.000 |
| a3_no_query | selection | 60 | 0.750 | 0.750 | 1.000 |
| a3_no_query | state | 14 | 0.286 | 0.286 | 1.000 |
| a3_noisy_user | ordering | 14 | 1.000 | 1.000 | 1.000 |
| a3_noisy_user | selection | 60 | 1.000 | 1.000 | 1.000 |
| a3_noisy_user | state | 14 | 0.571 | 0.571 | 1.000 |

## Category Breakdown

| system | category | rows | success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a2_planner | canonicalization | 46 | 0.674 | 0.674 | 0.000 | 0.674 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 1.000 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | insufficient_information | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | multiple_tool | 71 | 0.563 | 0.563 | 0.000 | 0.648 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.915 | 0.915 | 0.774 | 1.000 | 1.000 | 0.971 | 1.000 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | multiple_user_turn | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 1.000 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | no_distraction_tools | 88 | 0.625 | 0.625 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.932 | 0.932 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | single_tool | 15 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | single_user_turn | 61 | 0.902 | 0.902 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.262 | 0.902 | 0.902 | 0.820 | 1.000 | 1.000 | 0.978 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | state_dependency | 16 | 0.375 | 0.375 | 0.000 | 0.750 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.188 | 0.625 | 0.625 | 0.873 | 1.000 | 1.000 | 0.873 | 1.000 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | canonicalization | 46 | 1.000 | 1.000 | 0.326 | 1.000 | 0.326 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.326 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 1.000 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | insufficient_information | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | multiple_tool | 71 | 1.000 | 1.000 | 0.437 | 1.000 | 0.437 | 0.085 | 0.085 | 0.085 | 0.085 | 0.085 | 0.437 | 0.239 | 1.000 | 1.000 | 0.774 | 1.000 | 1.000 | 0.971 | 1.000 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | multiple_user_turn | 25 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 1.000 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | no_distraction_tools | 88 | 1.000 | 1.000 | 0.375 | 1.000 | 0.375 | 0.068 | 0.068 | 0.068 | 0.068 | 0.068 | 0.375 | 0.239 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | single_tool | 15 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | single_user_turn | 61 | 1.000 | 1.000 | 0.098 | 1.000 | 0.098 | 0.098 | 0.098 | 0.098 | 0.098 | 0.098 | 0.098 | 0.262 | 1.000 | 1.000 | 0.820 | 1.000 | 1.000 | 0.978 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_full_interaction | state_dependency | 16 | 1.000 | 1.000 | 0.625 | 1.000 | 0.625 | 0.375 | 0.375 | 0.375 | 0.375 | 0.375 | 0.625 | 0.188 | 1.000 | 1.000 | 0.873 | 1.000 | 1.000 | 0.873 | 1.000 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | canonicalization | 46 | 0.674 | 0.674 | 0.000 | 0.674 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 1.000 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | insufficient_information | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | multiple_tool | 71 | 0.563 | 0.563 | 0.000 | 0.648 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.915 | 0.915 | 0.774 | 1.000 | 1.000 | 0.971 | 1.000 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | multiple_user_turn | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 1.000 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | no_distraction_tools | 88 | 0.625 | 0.625 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.932 | 0.932 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | single_tool | 15 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | single_user_turn | 61 | 0.902 | 0.902 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.262 | 0.902 | 0.902 | 0.820 | 1.000 | 1.000 | 0.978 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_no_query | state_dependency | 16 | 0.375 | 0.375 | 0.000 | 0.750 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.188 | 0.625 | 0.625 | 0.873 | 1.000 | 1.000 | 0.873 | 1.000 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | canonicalization | 46 | 1.000 | 1.000 | 0.326 | 1.000 | 0.326 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.326 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 1.000 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | insufficient_information | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | multiple_tool | 71 | 0.915 | 0.915 | 0.352 | 1.000 | 0.437 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.437 | 0.239 | 0.915 | 0.915 | 0.774 | 1.000 | 1.000 | 0.971 | 1.000 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | multiple_user_turn | 25 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 1.000 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | no_distraction_tools | 88 | 0.932 | 0.932 | 0.307 | 1.000 | 0.375 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.375 | 0.239 | 0.932 | 0.932 | 0.790 | 1.000 | 1.000 | 0.977 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | single_tool | 15 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | single_user_turn | 61 | 0.902 | 0.902 | 0.000 | 1.000 | 0.098 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.098 | 0.262 | 0.902 | 0.902 | 0.820 | 1.000 | 1.000 | 0.978 | 1.000 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_noisy_user | state_dependency | 16 | 0.625 | 0.625 | 0.250 | 1.000 | 0.625 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.625 | 0.188 | 0.625 | 0.625 | 0.873 | 1.000 | 1.000 | 0.873 | 1.000 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |

## Result Summary Sources

| system | result_summary_source | rows |
|---|---|---:|
| a2_planner | reference_result_summary | 88 |
| a3_full_interaction | reference_result_summary | 88 |
| a3_no_query | reference_result_summary | 88 |
| a3_noisy_user | reference_result_summary | 88 |

## Failure Type Summary

| system | failure_type | rows | raw_execution_success | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | probe_user_queries | repair_user_queries | patch_success_rate | tool_calls | turn_count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2_planner | canonicalization | 29 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a2_planner | insufficient_information | 2 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a2_planner | multiple_user_turn | 25 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.240 | 11.160 |
| a2_planner | single_user_turn | 20 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a2_planner | state_dependency | 12 | 0.500 | 0.500 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 11.333 |
| a3_full_interaction | canonicalization | 29 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a3_full_interaction | insufficient_information | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a3_full_interaction | multiple_user_turn | 25 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.240 | 11.160 |
| a3_full_interaction | single_user_turn | 20 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a3_full_interaction | state_dependency | 12 | 1.000 | 1.000 | 0.500 | 1.000 | 0.500 | 0.000 | 0.500 | 0.500 | 1.500 | 11.333 |
| a3_no_query | canonicalization | 29 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a3_no_query | insufficient_information | 2 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a3_no_query | multiple_user_turn | 25 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.240 | 11.160 |
| a3_no_query | single_user_turn | 20 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a3_no_query | state_dependency | 12 | 0.500 | 0.500 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 11.333 |
| a3_noisy_user | canonicalization | 29 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a3_noisy_user | insufficient_information | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a3_noisy_user | multiple_user_turn | 25 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.240 | 11.160 |
| a3_noisy_user | single_user_turn | 20 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a3_noisy_user | state_dependency | 12 | 0.500 | 0.500 | 0.000 | 1.000 | 0.500 | 0.000 | 0.500 | 0.000 | 0.500 | 11.333 |

## Repair Loop Summary

| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2_planner | 88 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | 88 | 33 | 0.375 | 0.068 | 0.307 | 0.068 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | 88 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | 88 | 33 | 0.307 | 0.068 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Reuse Focused

| system | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|

## Statistical Robustness

- consistency=1.0 here mainly indicates deterministic replication stability across repeats.
- paired comparison is reported at task level (wins/losses/ties) with bootstrap 95% CI on mean success delta.

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: approval

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: planner_distractor_hard

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: repeated_reusable

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: state_repair

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

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