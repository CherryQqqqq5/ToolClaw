# ToolSandbox Planner-Sensitive Summary

- Protocol: `planner_sensitive_v2`
- Primary comparison: `a2_planner_vs_a1_recovery`
- Source task count: `42`
- Effect-size evidence ready: `True`
- Strong claim allowed: `True`
- V2 promotion ready: `True`
- Paper-safe planner claim: `True`
- Family positive count: `4`
- Reason: all gates and size threshold passed

## Deltas

- `a2_minus_a1_success_delta`: `1.0`
- `a2_minus_a1_capability_order_correct`: `1.0`
- `a2_minus_a1_instance_capability_order_correct`: `1.0`
- `a2_minus_a1_dependency_edge_correct`: `1.0`
- `a2_minus_a1_instance_dependency_edge_correct`: `1.0`
- `a2_minus_a1_tool_sequence_match`: `1.0`

## Paired Wins/Losses/Ties

- `wins`: `126`
- `losses`: `0`
- `ties`: `0`
- `pairs`: `126`

## Acceptance Checks

- `a2_success_delta_ge_20pp`: `True`
- `paired_wins_exceed_losses`: `True`
- `capability_order_delta_ge_20pp`: `True`
- `dependency_edge_delta_ge_20pp`: `True`
- `instance_dependency_edge_delta_ge_20pp`: `True`
- `tool_sequence_delta_ge_20pp`: `True`
- `no_hint_leakage_detected`: `True`
- `no_ordered_gold_structure_leakage_detected`: `True`
- `a2_not_cost_explosion`: `True`
- `source_task_count_ge_40`: `True`
- `family_positive_count_ge_3`: `True`
- `planner_bypass_known_rate_ge_90pp`: `True`
- `planner_bypass_rate_controlled`: `True`

## Per-System Metrics

- `a1_recovery`: success=0.0, capability_order=0.0, dependency_edges=0.0, tool_calls=2.0, bypass=unknown, bypass_known=0.0
- `a2_planner`: success=1.0, capability_order=1.0, dependency_edges=1.0, tool_calls=3.5238095238095237, bypass=0.0, bypass_known=1.0
- `a3_interaction`: success=1.0, capability_order=1.0, dependency_edges=1.0, tool_calls=3.5238095238095237, bypass=0.0, bypass_known=1.0
- `a4_reuse`: success=1.0, capability_order=1.0, dependency_edges=1.0, tool_calls=3.5238095238095237, bypass=0.0, bypass_known=1.0
