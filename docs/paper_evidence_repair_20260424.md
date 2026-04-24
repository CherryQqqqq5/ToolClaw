# Paper Evidence Repair Status on 2026-04-24

## Priority Decision

The paper-evidence repair plan is prioritized over the older BFCL planner-path repair plan.

This file is a roadmap, not the canonical claim source. The canonical paper-facing claim boundary is [paper_claim_boundary_20260424.md](paper_claim_boundary_20260424.md), with machine-readable roles in [configs/paper_claim_matrix.yaml](../configs/paper_claim_matrix.yaml).

## ToolSandbox Semantic Repair Official V1

Artifacts:

- `data/toolsandbox_semantic_repair_official_v1.jsonl`
- `data/toolsandbox_semantic_repair_official_v1.manifest.json`
- `outputs/paper_final_freeze_20260424/toolsandbox_semantic_repair_official_v1/claim_summary.json`
- `outputs/paper_final_freeze_20260424/toolsandbox_semantic_repair_official_v1/report.md`
- `outputs/paper_final_freeze_20260424/toolsandbox_semantic_repair_official_v1/paired_delta_summary.json`
- `outputs/paper_final_freeze_20260424/toolsandbox_semantic_repair_official_v1/paired_delta_summary.md`

The formal 3-run bundle supports the semantic repair mechanism claim when `claim_summary.json` reports:

- `protocol_complete = true`
- `semantic_repair_mechanism_supported = true`
- `interaction_not_cheating_supported = true`
- `probe_only_success_caveat_present = true`
- `primary_result_ready = true`

Paired evidence is now committed. On `repair_semantic_positive`, `a3_full_interaction` beats `a2_planner`, `a3_no_query`, and `a3_noisy_user` with `wins=18`, `losses=0`, `ties=0`, `mean_delta=1.0` for each comparison. On `probe_only_control`, `a3_full_interaction` ties `a3_noisy_user` with `ties=18`, `mean_delta=0.0`, so probe-only success remains a caveat rather than semantic repair evidence.

## BFCL Guarded Function Selection

Artifacts after the next guarded run should include:

- `bfcl_function_selection_audit.json`
- `bfcl_function_selection_audit.md`
- `claim_summary.json` with `bfcl_guard_claim_gates`

Status: implementation and audit scaffolding are in progress for a deterministic schema-top1 BFCL guard. This does not change the current BFCL claim boundary: `planner_binding_headline` remains a limitation because the existing paper-safe formal bundle is negative for planner/binder transfer. The guard can only become narrow supporting evidence after a guarded formal rerun passes all pre-registered gates.

Required full-suite gates before `bfcl_exact_function_guard` can become supporting:

- `a2_wrong_func_name <= a0_wrong_func_name`
- `a2_missing_required < a0_missing_required`
- `a2_tool_selection >= a0_tool_selection`
- `a2_success >= a0_success`

Required pre-registered `baseline_missing_required_slice` gates before `bfcl_missing_required_guarded_reduction` can become supporting:

- rows are selected by `a0_baseline` official failure bucket `missing_required` before analyzing guarded outcomes;
- `a2_guarded_missing_required_rate < a0_missing_required_rate`;
- `a2_guarded_wrong_func_name_rate <= a0_wrong_func_name_rate`;
- `a2_guarded_success_rate >= a0_success_rate`.

Artifact safety requirements:

- runtime selection diagnostics are gold-free;
- expected function and official failure bucket appear only in scorer/audit artifacts;
- schema ranker tie-break is deterministic under shuffled candidate order;
- guardability buckets report whether schema top-1/top-2/top-5 could have recovered planner wrong-function rows;
- `a4_reuse` is explicitly non-reuse evidence on BFCL.

## Persistent Reuse V2

Artifacts:

- `data/toolsandbox_reuse_persistent_v2.jsonl`
- `data/toolsandbox_reuse_persistent_v2.manifest.json`
- `outputs/reuse_persistent_v2_smoke/claim_summary.json`

Reuse remains pending. Server-side smoke indicates the sham false-positive issue has been addressed, but no committed paper-safe v2 formal bundle currently demonstrates warm exact hits plus positive cost/headroom delta.

## TAU2 Dual-Control Family V1

Artifacts:

- `data/tau2_dual_control_family_v1.json`
- `data/tau2_dual_control_family_v1.manifest.json`

This is a supporting/boundary family dataset, not headline evidence. Compound approval plus repair remains sparse and must be expanded before any stronger TAU2 dual-control claim.

## HTGP Planner-Sensitive V2 F2

Artifacts:

- `data/toolsandbox_planner_sensitive_v2.jsonl`
- `data/toolsandbox_planner_sensitive_v2.manifest.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/planner_sensitive_summary.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/planner_sensitive_summary.md`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/hint_leakage_report.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/hint_leakage_report.md`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/planner_sensitive_family_diagnostics.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/planner_sensitive_family_diagnostics.md`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/experiment_manifest.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal/comparison.scored.csv`

Status: mechanism-supporting evidence is now available and committed as the canonical planner-sensitive bundle. The f2 formal bundle reports `source_task_count = 42`, `family_positive_count = 4`, `a2_minus_a1_success_delta = 1.0`, paired wins/losses/ties `126/0/0`, `leakage_detected = false`, `ordered_gold_structure_leakage_detected = false`, `planner_bypass_known_rate = 1.0`, known-row `planner_bypass_rate = 0.0`, `v2_promotion_ready = true`, and `paper_safe_for_planner_claim = true`.

Claim boundary: this upgrades HTGP planner-sensitive evidence to `mechanism_supporting`, not headline. The earlier `planner_sensitive_v2_capability_fix_formal` bundle remains historical 3/4 evidence; f2 resolves the multi-source execution gap inside the planner-sensitive protocol. External exact function-calling transfer, especially BFCL fc_core, remains negative and must stay a limitation.

Next steps before any stronger planner claim:

- Build a held-out paraphrase suite with 60-80 tasks, 15-20 per structural family, no reused query templates or family-name hints, scorer-gold isolation, randomized tool order, renamed tool IDs, and stronger distractor overlap.
- Run cross-suite regression on ToolSandbox official frozen, semantic repair official v1, Interaction Live v1, BFCL fc_core smoke, and reuse persistent v2 smoke to confirm the planner-sensitive repairs did not contaminate other benchmark lines.
- Keep HTGP at `mechanism_supporting` until held-out evidence and cross-suite regression are committed.
