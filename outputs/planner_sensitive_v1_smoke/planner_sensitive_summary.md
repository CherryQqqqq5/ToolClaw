# ToolSandbox Planner-Sensitive Summary

- Protocol: `planner_sensitive_v1`
- Primary comparison: `a2_planner_vs_a1_recovery`
- Source task count: `24`
- Effect-size evidence ready: `True`
- Strong claim allowed: `False`
- Paper-safe planner claim: `False`
- Reason: passes effect-size gates but requires >=40 tasks before strong planner claim

## Deltas

- `a2_minus_a1_success_delta`: `0.75`
- `a2_minus_a1_capability_order_correct`: `0.75`
- `a2_minus_a1_dependency_edge_correct`: `0.75`
- `a2_minus_a1_tool_sequence_match`: `0.75`

## Paired Wins/Losses/Ties

- `wins`: `6`
- `losses`: `0`
- `ties`: `2`
- `pairs`: `8`

## Acceptance Checks

- `a2_success_delta_ge_20pp`: `True`
- `paired_wins_exceed_losses`: `True`
- `capability_order_delta_ge_20pp`: `True`
- `dependency_edge_delta_ge_20pp`: `True`
- `no_hint_leakage_detected`: `True`
- `a2_not_cost_explosion`: `True`
- `planner_bypass_rate_controlled`: `True`

## Per-System Metrics

- `a1_recovery`: success=0.0, capability_order=0.0, dependency_edges=0.0, tool_calls=2.0, bypass=unknown
- `a2_planner`: success=0.75, capability_order=0.75, dependency_edges=0.75, tool_calls=2.75, bypass=unknown
- `a3_interaction`: success=0.75, capability_order=0.75, dependency_edges=0.75, tool_calls=2.75, bypass=unknown
- `a4_reuse`: success=0.75, capability_order=0.75, dependency_edges=0.75, tool_calls=2.75, bypass=0.0
