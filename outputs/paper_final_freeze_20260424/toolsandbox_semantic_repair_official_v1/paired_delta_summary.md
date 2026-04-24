# ToolSandbox Semantic Repair Official v1 Paired Delta Summary

Paired key: `(task_id, run_index)`.

The repair-semantic-positive slice is the mechanism evidence. The probe-only control slice is a caveat: strict success there can be contract/probe-mediated and must not be interpreted as semantic repair.

| comparison | slice | pairs | wins | losses | ties | mean_delta | task_count |
|---|---|---:|---:|---:|---:|---:|---:|
| a3_full_interaction_vs_a2_planner | probe_only_control | 18 | 18 | 0 | 0 | 1.000 | 6 |
| a3_full_interaction_vs_a2_planner | repair_semantic_positive | 18 | 18 | 0 | 0 | 1.000 | 6 |
| a3_full_interaction_vs_a3_no_query | probe_only_control | 18 | 18 | 0 | 0 | 1.000 | 6 |
| a3_full_interaction_vs_a3_no_query | repair_semantic_positive | 18 | 18 | 0 | 0 | 1.000 | 6 |
| a3_full_interaction_vs_a3_noisy_user | probe_only_control | 18 | 0 | 0 | 18 | 0.000 | 6 |
| a3_full_interaction_vs_a3_noisy_user | repair_semantic_positive | 18 | 18 | 0 | 0 | 1.000 | 6 |
