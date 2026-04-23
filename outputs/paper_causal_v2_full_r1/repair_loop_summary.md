# ToolSandbox Repair Loop Summary

## Per System

| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2_planner | 88 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | 88 | 33 | 0.375 | 0.068 | 0.307 | 0.068 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | 88 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | 88 | 33 | 0.307 | 0.068 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Per Failure Type

| system | failure_type | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | state_patch_count | policy_patch_count | binding_patch_count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2_planner | canonicalization | 29 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | insufficient_information | 2 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | multiple_user_turn | 25 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | single_user_turn | 20 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | state_dependency | 12 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | canonicalization | 29 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | insufficient_information | 2 | 2 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | multiple_user_turn | 25 | 25 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | single_user_turn | 20 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | state_dependency | 12 | 6 | 0.500 | 0.500 | 0.000 | 0.500 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | canonicalization | 29 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | insufficient_information | 2 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | multiple_user_turn | 25 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | single_user_turn | 20 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | state_dependency | 12 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | canonicalization | 29 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | insufficient_information | 2 | 2 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | multiple_user_turn | 25 | 25 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | single_user_turn | 20 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | state_dependency | 12 | 6 | 0.000 | 0.500 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |