# Paper Claim Boundary on 2026-04-24

This is the canonical paper-facing claim boundary note. If this file conflicts with older benchmark reports or exploratory run notes, use this file and `configs/paper_claim_matrix.yaml` as the source of truth.

## Allowed Core Narrative

ToolSandbox official supports the end-to-end interaction headline. ToolSandbox semantic repair official v1 provides targeted official-slice evidence for semantic repair. Interaction Live validates the semantic decoder and patch mechanism under controlled user modes. ToolSandbox causal v2 is boundary evidence showing that probe and contract effects can mediate full-suite gains. BFCL fc_core is a paper-safe negative transfer result for planner/binder headline lift. HTGP planner structural contribution is pending a dedicated planner-sensitive protocol. Reuse v2 and TAU2 family remain pending or supporting evidence until larger formal bundles are available.

## Claim Matrix

| claim | claim_strength | primary evidence | supporting evidence | allowed wording | forbidden wording |
|---|---|---|---|---|---|
| `interaction_headline` | `headline` | `toolsandbox_official` | ToolSandbox official frozen reports | ToolClaw improves end-to-end ToolSandbox strict success through interaction/stateful workflow control. | Planner alone is the headline source of ToolSandbox gain. |
| `interaction_semantic_usefulness_mechanism` | `mechanism_primary` | `toolsandbox_semantic_repair_official_v1` | `toolsandbox_interaction_live_v1` | On targeted official repair-semantic tasks, usable replies become target-aligned effective patches and post-query progress. | Full ToolSandbox causal v2 proves all interaction gains are semantic repair. |
| `interaction_live_semantic_gate` | `mechanism_supporting` | `toolsandbox_interaction_live_v1` | semantic repair official v1 | Controlled oracle/partial replies are useful; noisy, irrelevant, and wrong-parameter replies are rejected as useful repair. | Interaction Live alone is the official headline benchmark. |
| `causal_v2_probe_boundary` | `boundary` | `toolsandbox_interaction_causality_formal_v2` | semantic repair official v1 | Causal v2 exposes that official full-suite gains can include probe/contract effects, motivating targeted semantic repair evaluation. | Causal v2 is positive semantic repair mechanism evidence. |
| `planner_binding_headline` | `limitation` | `bfcl_fc_core` | BFCL diagnostics | BFCL fc_core is paper-safe but negative for planner/binder headline lift. | BFCL currently shows a ToolClaw planner/binder headline gain. |
| `planner_structural_mechanism` | `pending` | `toolsandbox_planner_sensitive_v1` formal v1 | hint leakage audit | HTGP has targeted 24-task effect-size evidence under a planner-sensitive protocol, but this remains pending until expanded beyond 40 tasks and revalidated. | Existing full benchmarks already prove strong planner-alone contribution, or 24 curated tasks are enough for a strong planner headline. |
| `reuse_exact_match_cost` | `pending` | `toolsandbox_reuse_persistent_v2` dataset | server-side smoke only | Reuse is under a narrow exact/matched-signature second-run cost protocol, pending committed formal evidence. | Persistent reuse has a proven paper-safe second-run cost reduction. |
| `dual_control_interaction` | `boundary` | `tau2_dual_control_family_v1` dataset | old TAU2 formal/smoke bundles | TAU2 currently provides supporting/boundary evidence for dual-control and approval interaction. | TAU2 dual-control is a headline benchmark claim. |

## Current Evidence Status

| experiment line | current status | next required action |
|---|---|---|
| ToolSandbox official | Headline supported. | Keep stable; do not reinterpret as semantic repair by itself. |
| Semantic repair official v1 | Mechanism supported on a targeted official slice. | Add paired wins/losses table from the committed scored bundle. |
| Interaction Live | Supporting mechanism validation. | Keep as controlled validation, not primary official evidence. |
| Causal v2 | Boundary/caveat evidence. | Keep it as probe/contract analysis; do not promote to positive mechanism claim. |
| BFCL fc_core | Paper-safe negative transfer result. | Either write limitation or separately repair BFCL adapter path; do not use as positive headline. |
| BFCL grounding/multi-turn | Older evidence is not paper-safe where dependency/coverage gaps remain. | Keep separate from fc_core formal. |
| Planner-sensitive v1 | 24-task x 3-run formal v1 passes effect-size gates with no hint leakage, but remains below the size needed for a strong planner claim. | Expand beyond 40 tasks, rerun formal, and require the same hint-leakage, paired effect-size, bypass, and cost-control gates before promotion. |
| Reuse v2 | Dataset ready; committed formal evidence missing. | Commit a paper-safe smoke/formal bundle only after warm exact hit, low sham false positive, and positive cost/headroom delta. |
| TAU2 family | Supporting dataset; compound slice sparse. | Expand compound approval plus repair to at least 8-10 tasks before stronger claims. |

## Semantic Repair Paired Evidence Target

The semantic repair official v1 paired summary must be computed from `comparison.scored.csv`, not by rerunning the benchmark. The paired key is `(task_id, run_index)`.

Expected repair-semantic-positive result from the current committed bundle:

| comparison | expected wins | expected losses | expected ties | expected mean_delta |
|---|---:|---:|---:|---:|
| `a3_full_interaction - a2_planner` | 18 | 0 | 0 | 1.0 |
| `a3_full_interaction - a3_no_query` | 18 | 0 | 0 | 1.0 |
| `a3_full_interaction - a3_noisy_user` | 18 | 0 | 0 | 1.0 |

The probe-only control slice must remain a caveat table. If full and noisy systems both achieve strict success there, that is contract/probe evidence, not semantic repair evidence, because useful/effective patch metrics remain zero.

## Non-Negotiable Boundaries

- Do not use causal v2 as primary positive semantic repair evidence.
- Do not write TAU2 dual-control as headline until the family is larger and formalized.
- Do not write BFCL fc_core as positive planner/binder transfer evidence.
- Do not write HTGP planner structural contribution as a mechanism-primary claim until `toolsandbox_planner_sensitive_v1` passes formal gates and ideally expands beyond 40 tasks.
- Do not write reuse as a performance claim until a committed v2 formal bundle shows cost/headroom gains.
- Do not mix server-side smoke observations with committed paper-safe artifacts without labeling the distinction.
