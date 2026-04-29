# Layer Delta Evidence Matrix - 2026-04-27

## Verdict

The paper evidence should be read as a layered headroom story, not as a requirement that every mechanism visibly improves the same broad aggregate score. The 405-scenario ToolSandbox core strict ladder is the broad paper-facing non-regression result. Layer-specific suites carry the recovery, planner, interaction, and reuse deltas on the headroom where each mechanism is designed to operate.

This matrix is the compact source-of-truth view for layer-specific deltas. It does not change claim statuses in `configs/paper_claim_matrix.yaml`.

## Evidence Matrix

| layer | mechanism | primary evidence | delta | paired wins/losses/ties | status | boundary |
|---|---|---|---:|---:|---|---|
| Recovery | generic recovery on broad ToolSandbox core failures | `toolsandbox_official_core_reproducible_strict` | `s1 - s0 = +0.044445` strict success | `54 / 0 / 1161` | supported on broad core | This is broad-core recovery headroom. It is not evidence for task-specific ToolSandbox rules. |
| Planner | HTGP structural planning plus admitted-planner safety on core | `toolsandbox_planner_sensitive_v2_f2`; `toolsandbox_planner_sensitive_v2_heldout`; core residual audit | F2 `a2 - a1 = +1.0`; held-out `a2 - a1 = +0.4375`; core `s2 - s1 = 0` | F2 `126 / 0 / 0`; held-out `105 / 0 / 135`; core residual `339 interaction_contract / 0 other` | mechanism-supporting | Planner utility is supported by planner-sensitive suites. Broad ToolSandbox core supports safe admitted planning/non-regression only: `planner_takeover_on_s1_fail_count=339`, `planner_utility_win_count=0`, all takeover residuals are interaction-contract. |
| Interaction | bounded full405 interaction plus targeted semantic slices | `toolsandbox_official_core_reproducible_planner_admission`; interaction cost audit; targeted semantic-repair slices | core `s3` adds 3 strict wins over `s2`; 120 user queries and 119 probe queries per additional win; semantic credit lower bound 0 | core `3 / 0 / 1212`; repair-positive targeted slices remain separate | bounded strict non-regression plus limitation | Full405 `s3` evidence is small, probe-heavy, and not broad semantic-repair support. Targeted semantic-repair slices remain separate mechanism evidence, and probe-only controls remain caveats. |
| Reuse | exact matched-signature warm reuse | `toolsandbox_reuse_persistent_v3` | primary tool-call reduction mean `1.0`; warm exact hit/source-match rates `1.0`; sham false-positive rate `0.0` | `54 / 0 / 0` | mechanism-supporting | Exact matched-signature, pilot-confirmed high-headroom ToolSandbox core families only. No broad success, transfer, BFCL, external/API reuse, broad binding repair, verifier-backed skill-learning claim, or full405 reuse-over-interaction success lift. |
| BFCL boundary | exact function-calling transfer and binder stress | `bfcl_fc_core` | unsupported for current planner/reuse lift | n/a | limitation | BFCL remains a boundary. Do not use BFCL to support reuse lift, planner transfer, or broad exact function-calling transfer. |

## Current Layer Read

- Broad ToolSandbox core: use `toolsandbox_official_core_reproducible_planner_admission` to show paper-facing strict ladder performance and zero adjacent primary-success regressions.
- Recovery: the broad core delta is visible directly in the strict ladder (`s1 > s0`).
- Planner: use planner-sensitive F2 and held-out suites for HTGP structural mechanism evidence; do not force this claim through the broad core aggregate. The core planner residual audit from `outputs/paper_suite/toolsandbox_official_core_reproducible_planner_admission/planner_takeover_residual_audit.json` reports `residual_row_count=339`, `top_bucket=interaction_contract`, and all other residual buckets at `0`, so broad-core `s2` utility headroom is interaction-limited rather than planner-limited.
- Interaction: use the latest full405 cost audit as a boundary: `s3` has 3 additional strict wins over `s2`, 0 losses, 1212 ties, 120 user queries per additional win, 119 probe queries per additional win, and semantic credit lower bound 0. Targeted semantic-repair slices remain separate mechanism evidence, with probe-only caveats retained.
- Reuse: use reuse persistent v3 for exact matched-signature second-run tool-call cost reduction/no-regression; reuse should not be required or described as improving single-run full405 core success.
- BFCL: keep as limitation and transfer boundary.

## Future Generic Mechanism Roadmap

These are future implementation lines only. They are not part of the current evidence claim.

- Add a non-mutating `s4` failure taxonomy report that classifies failures by generic categories such as missing input, state precondition, approval, binding, execution, ambiguity, and success-verification gap.
- The failure taxonomy report must not suggest scenario-name, benchmark-row, or tool-name rules.
- Do not continue tuning planner admission on broad ToolSandbox core unless a future audit identifies non-interaction planner-admissible residuals. Current admitted takeovers are safe but do not convert any `s1` failure into `s2` success on core.
- PlannerOverlay V2 should consume planner hints only after a failure or preflight block. It must not override the primary tool, insert normal-path steps, or introduce ToolSandbox-specific templates.
- Interaction V2 should broaden generic query policy for missing schema inputs, ambiguous references, approval, and typed value extraction. It must not ask unnecessary questions on already-solvable tasks.
- Reuse improvements should remain in exact matched-signature reuse protocols, not the single-run ToolSandbox core strict ladder.

## Boundary Wording

Allowed: ToolClaw provides a non-regressive, training-free workflow-control layer on the ToolSandbox core strict ladder, with layer-specific evidence on recovery, planner-sensitive structure, targeted semantic repair, and exact matched-signature reuse headroom. Full405 interaction remains bounded by the cost/probe audit.

Forbidden: claiming a ToolSandbox SOTA result, treating 405-core as the full external/API suite, claiming broad planner overlay lift on ToolSandbox core, saying HTGP improves broad ToolSandbox core success, treating reuse v3 as transfer/general reuse or full405 reuse-over-interaction success lift, or using BFCL as reuse/planner lift evidence.
