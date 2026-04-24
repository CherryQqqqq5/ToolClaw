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

The formal 3-run bundle supports the semantic repair mechanism claim when `claim_summary.json` reports:

- `protocol_complete = true`
- `semantic_repair_mechanism_supported = true`
- `interaction_not_cheating_supported = true`
- `probe_only_success_caveat_present = true`
- `primary_result_ready = true`

Next required artifact: regenerate the scorer on the committed bundle to add `paired_delta_summary.json` and `paired_delta_summary.md`. The target repair-semantic-positive paired result is `a3_full_interaction` beating `a2_planner`, `a3_no_query`, and `a3_noisy_user` with `wins=18`, `losses=0`, `ties=0` for each comparison.

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
