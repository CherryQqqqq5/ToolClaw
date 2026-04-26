# Planner-Sensitive V2 Held-Out Robustness Note (2026-04-26)

## Summary

`toolsandbox_planner_sensitive_v2_heldout` is a robustness check for the HTGP planner structural mechanism, not a headline benchmark. It tests whether the V2 F2 planner-sensitive result transfers beyond the original templates under held-out paraphrases, renamed tools, shuffled candidates, and stronger distractors.

The result is positive but bounded: `a2_planner` separates from `a1_recovery` with a 43.75pp strict-success lift and zero paired losses, but the effect is positive in 3/4 structural families rather than all four. This supports mechanism-level robustness, not a general planner or exact function-calling claim.

## Suite Design

- Source: `data/toolsandbox_planner_sensitive_v2_heldout.jsonl`
- Manifest: `data/toolsandbox_planner_sensitive_v2_heldout.manifest.json`
- Result bundle: `outputs/paper_suite/toolsandbox_planner_sensitive_v2_heldout`
- Protocol: `planner_sensitive_v2_heldout`
- Size: 80 tasks, 4 structural families, 20 tasks per family
- Families: `retrieve_summarize_write`, `check_modify_verify`, `branch_select_execute`, `multi_source_merge_write`
- Stressors: held-out paraphrase templates, renamed tool IDs, deterministic candidate-order shuffling, and strong lexical distractors
- Leakage controls: planner-visible metadata omits family-name hints; expected order and dependency edges remain scorer-side only in `scorer_gold`

## Formal Three-Run Result

| metric | value |
|---|---:|
| source_task_count | 80 |
| family_positive_count | 3 |
| a2_minus_a1_success_delta | 0.4375 |
| paired wins/losses/ties | 105 / 0 / 135 |
| capability_order_delta | 0.6875 |
| dependency_edge_delta | 0.6875 |
| instance_dependency_edge_delta | 0.4375 |
| tool_sequence_delta | 0.4375 |
| planner_bypass_known_rate | 1.000 |
| known-row planner_bypass_rate | 0.000 |
| leakage_task_count | 0 |
| ordered_gold_structure_leakage_task_count | 0 |
| v2_promotion_ready | true |

Family deltas for `a2_planner - a1_recovery`:

| family | strict-success delta | interpretation |
|---|---:|---|
| retrieve_summarize_write | 0.750 | positive |
| check_modify_verify | 0.750 | positive |
| multi_source_merge_write | 0.250 | positive |
| branch_select_execute | 0.000 | unresolved in held-out |

## Claim Boundary

Allowed wording: HTGP shows held-out robustness on planner-sensitive structural tasks, with positive separation in 3/4 families under paraphrase, tool renaming, candidate shuffling, and distractor stress.

Forbidden wording: HTGP carries the paper headline, HTGP generalizes to broad external function-calling, BFCL transfer is positive, or held-out results show complete family coverage.

The canonical strong mechanism evidence remains `toolsandbox_planner_sensitive_v2_f2`; this held-out suite is a robustness support and boundary check.

## No-Patch Policy

Do not patch the planner or binder against failures from this held-out suite if it is used as paper evidence. Patching against these 80 tasks would convert the suite into a development set. If the unresolved `branch_select_execute` family is repaired, create a fresh blind held-out-B suite with new paraphrases, renamed tools, shuffled candidates, and distractors before using the repaired result as robustness evidence.

## BFCL Boundary

This result does not change BFCL status. BFCL remains a boundary and limitation for exact function-calling transfer; it must not be folded into the planner structural mechanism claim.
