# ToolSandbox Semantic Repair Official v1

## Claim Summary

| verdict | value |
|---|---:|
| protocol_complete | true |
| semantic_repair_mechanism_supported | true |
| interaction_not_cheating_supported | true |
| probe_only_success_caveat_present | true |
| primary_result_ready | true |

## Row-Level Slice Summary

| system | slice | strict | verified | reply_usable | target_aligned | effective_patch | post_query_progress | useful_round | mean_user_queries | mean_tool_calls |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2_planner | probe_only_control | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.167 |
| a2_planner | repair_semantic_positive | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| a3_full_interaction | probe_only_control | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.167 |
| a3_full_interaction | repair_semantic_positive | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 2.000 |
| a3_no_query | probe_only_control | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.167 |
| a3_no_query | repair_semantic_positive | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| a3_noisy_user | probe_only_control | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.167 |
| a3_noisy_user | repair_semantic_positive | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |

## Round-Level Summary

| system | slice | rounds | reply_usable | target_aligned | effective_patch | post_query_progress | useful_round |
|---|---|---:|---:|---:|---:|---:|---:|
| a3_full_interaction | repair_semantic_positive | 18 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_noisy_user | repair_semantic_positive | 18 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |