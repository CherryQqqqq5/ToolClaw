# Layer Delta Evidence Matrix - 2026-04-27

## Verdict

The paper evidence should be read as a layered headroom story, not as a requirement that every mechanism visibly improves the same broad aggregate score. The 405-scenario ToolSandbox core strict ladder is the broad paper-facing non-regression result. Layer-specific suites carry the recovery, planner, interaction, and reuse deltas on the headroom where each mechanism is designed to operate.

This matrix is the compact source-of-truth view for layer-specific deltas. It does not change claim statuses in `configs/paper_claim_matrix.yaml`.

## Evidence Matrix

| layer | mechanism | primary evidence | delta | paired wins/losses/ties | status | boundary |
|---|---|---|---:|---:|---|---|
| Recovery | generic recovery on broad ToolSandbox core failures | `toolsandbox_official_core_reproducible_strict` | `s1 - s0 = +0.044445` strict success | `54 / 0 / 1161` | supported on broad core | This is broad-core recovery headroom. It is not evidence for task-specific ToolSandbox rules. |
| Planner | HTGP structural planning plus admitted-planner safety on core | `toolsandbox_planner_sensitive_v2_f2`; `toolsandbox_planner_sensitive_v2_heldout`; core residual audit | F2 `a2 - a1 = +1.0`; held-out `a2 - a1 = +0.4375`; core `s2 - s1 = 0` | F2 `126 / 0 / 0`; held-out `105 / 0 / 135`; core residual `339 interaction_contract / 0 other` | mechanism-supporting | Planner utility is supported by planner-sensitive suites. Broad ToolSandbox core supports safe admitted planning/non-regression only: `planner_takeover_on_s1_fail_count=339`, `planner_utility_win_count=0`, all takeover residuals are interaction-contract. |
| Interaction | semantic repair from user signal | `toolsandbox_semantic_repair_official_v2` | repair-positive `a3_full_interaction - a2/no_query/noisy = +0.833333` mean delta | `15 / 0 / 3` | 405-core provenance refresh and supporting mechanism evidence | Probe-only controls remain caveats. This should not be read as all interaction gain being semantic repair. |
| Reuse | guarded exact matched-signature second-run prior | `toolsandbox_reuse_persistent_v3` | primary exact/headroom tool-call reduction `+1.0` | `54 / 0 / 0` | mechanism-supporting | Exact matched-signature and high-headroom only. No broad success, transfer, BFCL, or verifier-backed skill-learning claim. |
| BFCL boundary | exact function-calling transfer and binder stress | `bfcl_fc_core` | unsupported for current planner/reuse lift | n/a | limitation | BFCL remains a boundary. Do not use BFCL to support reuse lift, planner transfer, or broad exact function-calling transfer. |

## Current Layer Read

- Broad ToolSandbox core: use `toolsandbox_official_core_reproducible_strict` to show paper-facing strict ladder performance and zero adjacent primary-success regressions.
- Recovery: the broad core delta is visible directly in the strict ladder (`s1 > s0`).
- Planner: use planner-sensitive F2 and held-out suites for HTGP structural mechanism evidence; do not force this claim through the broad core aggregate. The core planner residual audit from `outputs/paper_suite/toolsandbox_official_core_reproducible_planner_admission/planner_takeover_residual_audit.json` reports `residual_row_count=339`, `top_bucket=interaction_contract`, and all other residual buckets at `0`, so broad-core `s2` utility headroom is interaction-limited rather than planner-limited.
- Interaction: use semantic repair official v2 as the 405-core refreshed targeted repair signal, with probe-only caveats retained.
- Reuse: use reuse persistent v3 for exact matched-signature second-run cost reduction; do not require reuse to improve single-run core success.
- BFCL: keep as limitation and transfer boundary.

## Future Generic Mechanism Roadmap

These are future implementation lines only. They are not part of the current evidence claim.

- Add a non-mutating `s4` failure taxonomy report that classifies failures by generic categories such as missing input, state precondition, approval, binding, execution, ambiguity, and success-verification gap.
- The failure taxonomy report must not suggest scenario-name, benchmark-row, or tool-name rules.
- Do not continue tuning planner admission on broad ToolSandbox core unless a future audit identifies non-interaction planner-admissible residuals. Current admitted takeovers are safe but do not convert any `s1` failure into `s2` success on core.
- PlannerOverlay V2 should consume planner hints only after a failure or preflight block. It must not override the primary tool, insert normal-path steps, or introduce ToolSandbox-specific templates.
- Interaction V2 should broaden generic query policy for missing schema inputs, ambiguous references, approval, and typed value extraction. It must not ask unnecessary questions on already-solvable tasks.
- Reuse improvements should remain in the persistent exact-reuse protocol, not the single-run ToolSandbox core strict ladder.

## Boundary Wording

Allowed: ToolClaw provides a non-regressive, training-free workflow-control layer on the ToolSandbox core strict ladder, with layer-specific deltas on recovery, planner-sensitive structure, semantic repair, and exact persistent reuse headroom.

Forbidden: claiming a ToolSandbox SOTA result, treating 405-core as the full external/API suite, claiming broad planner overlay lift on ToolSandbox core, saying HTGP improves broad ToolSandbox core success, treating reuse v3 as transfer reuse, or using BFCL as reuse/planner lift evidence.
