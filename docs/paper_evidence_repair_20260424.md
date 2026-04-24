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

## HTGP Planner-Sensitive V2 Capability Fix

Artifacts:

- `data/toolsandbox_planner_sensitive_v2.jsonl`
- `data/toolsandbox_planner_sensitive_v2.manifest.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/planner_sensitive_summary.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/hint_leakage_report.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/planner_sensitive_family_diagnostics.json`
- `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/experiment_manifest.json`

Status: mechanism-supporting evidence is now available and committed. The capability-fix formal bundle reports `source_task_count = 42`, `family_positive_count = 3`, `a2_minus_a1_success_delta = 0.7380952381`, paired wins/losses/ties `93/0/33`, `leakage_detected = false`, `ordered_gold_structure_leakage_detected = false`, `v2_promotion_ready = true`, and `paper_safe_for_planner_claim = true`.

Claim boundary: this upgrades HTGP from pending scaffold to `mechanism_supporting`, not headline. `multi_source_merge_write` remains a binder-selection gap and should be described as the next repair target before any stronger planner claim.
