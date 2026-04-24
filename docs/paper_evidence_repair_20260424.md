# Paper Evidence Repair Status on 2026-04-24

## Priority Decision

The paper-evidence repair plan is prioritized over the older BFCL planner-path repair plan.

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

## Persistent Reuse V2

Artifacts:

- `data/toolsandbox_reuse_persistent_v2.jsonl`
- `data/toolsandbox_reuse_persistent_v2.manifest.json`
- `outputs/reuse_persistent_v2_smoke/claim_summary.json`

Reuse remains gated unless the smoke bundle shows low sham false positives and positive cost headroom.

## TAU2 Dual-Control Family V1

Artifacts:

- `data/tau2_dual_control_family_v1.json`
- `data/tau2_dual_control_family_v1.manifest.json`

This is a supporting family dataset. Compound approval plus repair remains boundary evidence unless expanded beyond the sparse slice.
