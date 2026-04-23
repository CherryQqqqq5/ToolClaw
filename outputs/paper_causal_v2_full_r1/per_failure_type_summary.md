# ToolSandbox Failure-Type Summary

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