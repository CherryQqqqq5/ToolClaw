# Paper Claim Boundary on 2026-04-24

This is the canonical paper-facing claim boundary note. If this file conflicts with older benchmark reports or exploratory run notes, use this file and `configs/paper_claim_matrix.yaml` as the source of truth.

## Allowed Core Narrative

The 405-scenario ToolSandbox core reproducible strict formal bundle supports the end-to-end ToolSandbox headline for the paper-facing strict ladder: strict success is `s0=0.659259`, `s1=0.703704`, `s2=0.703704`, `s3=0.706173`, and `s4=0.706173`, with `0 / 4860` adjacent primary-success regressions. ToolSandbox semantic repair official v1 provides targeted official-slice evidence for semantic repair. Interaction Live validates the semantic decoder and patch mechanism under controlled user modes. ToolSandbox causal v2 is boundary evidence showing that probe and contract effects can mediate full-suite gains. BFCL fc_core is a paper-safe negative transfer result for planner/binder headline lift. The BFCL schema-top1 guard and candidate-preservation rerun remain unsupported for claim purposes: they suppress a2 wrong-function regression and repair executable candidate visibility, but do not pass success or missing-required gates, and they do not promote planner/binder headline transfer. HTGP planner structural contribution is mechanism-supporting evidence after the planner-sensitive V2 f2 formal bundle, with held-out robustness support from `toolsandbox_planner_sensitive_v2_heldout`: F2 passes structured-observability, leakage, bypass, cost, and all-four-family coverage gates, while the held-out suite remains positive in 3/4 structural families under paraphrase, tool renaming, shuffled candidates, and distractor stress. The HTGP claim remains mechanism-level rather than headline because held-out coverage is not universal and external exact function-calling transfer, especially BFCL, is still not positive. Reuse v2 and TAU2 family remain pending or supporting evidence until larger formal bundles are available.

## Claim Matrix

| claim | claim_strength | primary evidence | supporting evidence | allowed wording | forbidden wording |
|---|---|---|---|---|---|
| `interaction_headline` | `headline` | `toolsandbox_official_core_reproducible_strict` | 405-core reproducible strict formal, strict ladder audit | ToolClaw's paper-facing strict ladder improves end-to-end ToolSandbox core strict success from `s0` to `s4` while preserving adjacent primary success. | Planner alone is the headline source of ToolSandbox gain, or the 405-core subset is the full external/API ToolSandbox suite. |
| `strict_layer_monotonicity` | `mechanism_supporting` | `toolsandbox_official_core_reproducible_strict` | `strict_layer_monotonicity_audit.json/md`, runtime visibility audit | On the 405-row core frozen export, each adjacent strict overlay layer has zero primary-success regressions: paired wins/losses/ties are 54/0/1161, 0/0/1215, 3/0/1212, and 0/0/1215. | Planner overlay or reuse overlay independently carries broad ToolSandbox-core lift, or cost/user-turn/tool-call metrics must improve at every layer. |
| `interaction_semantic_usefulness_mechanism` | `mechanism_primary` | `toolsandbox_semantic_repair_official_v1` | `toolsandbox_interaction_live_v1` | On targeted official repair-semantic tasks, usable replies become target-aligned effective patches and post-query progress. | Full ToolSandbox causal v2 proves all interaction gains are semantic repair. |
| `interaction_live_semantic_gate` | `mechanism_supporting` | `toolsandbox_interaction_live_v1` | semantic repair official v1 | Controlled oracle/partial replies are useful; noisy, irrelevant, and wrong-parameter replies are rejected as useful repair. | Interaction Live alone is the official headline benchmark. |
| `causal_v2_probe_boundary` | `boundary` | `toolsandbox_interaction_causality_formal_v2` | semantic repair official v1 | Causal v2 exposes that official full-suite gains can include probe/contract effects, motivating targeted semantic repair evaluation. | Causal v2 is positive semantic repair mechanism evidence. |
| `planner_binding_headline` | `limitation` | `bfcl_fc_core` | BFCL diagnostics | BFCL fc_core is paper-safe but negative for planner/binder headline lift. | BFCL currently shows a ToolClaw planner/binder headline gain. |
| `bfcl_exact_function_guard` | `limitation` | guarded `bfcl_fc_core` coverage rerun | BFCL function-selection and candidate-coverage audits | The guard suppresses a2 wrong-function regression but fails success and missing-required gates; it is diagnostic only. | The guard proves ToolClaw improves BFCL or supports planner/binder transfer. |
| `bfcl_missing_required_guarded_reduction` | `limitation` | guarded `bfcl_fc_core` coverage rerun | pre-registered baseline-missing-required slice | Unsupported: the full-suite missing-required gate fails and the baseline-missing-required slice has zero a0 rows in the coverage rerun. | A slice-only or post-hoc missing-required observation is enough for support. |
| `bfcl_broad_transfer` | `limitation` | `bfcl_fc_core` | BFCL diagnostics | Broad exact function-calling transfer is unsupported in current evidence. | ToolClaw has solved BFCL broad transfer. |
| `bfcl_reuse_lift` | `limitation` | `bfcl_fc_core` | BFCL diagnostics | BFCL does not provide reuse-lift evidence; A4 is interpreted as a guarded execution variant only. | A4 BFCL changes measure persistent reuse lift. |
| `planner_structural_mechanism` | `mechanism_supporting` | `toolsandbox_planner_sensitive_v2_f2` | `toolsandbox_planner_sensitive_v2_heldout`, v1/v2 boundary bundles, capability-fix historical bundle, hint leakage audit, family diagnostics | HTGP shows structured planner-mechanism evidence on planner-sensitive V2 f2 and held-out robustness support: F2 has 42 tasks, a2-a1 delta 1.0, paired wins/losses/ties 126/0/0, no leakage, controlled bypass, and 4/4 positive families; held-out has 80 tasks, a2-a1 delta 0.4375, paired 105/0/135, no leakage, and 3/4 positive families. | HTGP carries a headline or general planner claim, HTGP has complete held-out family coverage, or BFCL proves planner/binder transfer. |
| `reuse_exact_match_cost` | `pending` | `toolsandbox_reuse_persistent_v2` dataset | server-side smoke only | Reuse is under a narrow exact/matched-signature second-run cost protocol, pending committed formal evidence. | Persistent reuse has a proven paper-safe second-run cost reduction. |
| `dual_control_interaction` | `boundary` | `tau2_dual_control_family_v1` dataset | old TAU2 formal/smoke bundles | TAU2 currently provides supporting/boundary evidence for dual-control and approval interaction. | TAU2 dual-control is a headline benchmark claim. |

## Current Evidence Status

| experiment line | current status | next required action |
|---|---|---|
| ToolSandbox core reproducible strict | Headline supported on the 405-row core frozen export; adjacent strict-layer non-regression is supported with `0 / 4860` regressions. | Use as the current ToolSandbox core headline source, while labeling legacy 88-row official export as historical and external/API scenarios as excluded boundary. |
| Semantic repair official v1 | Mechanism supported on a targeted official slice; paired delta summary is committed. | Keep paired evidence as primary mechanism table and retain probe-only rows as caveats. |
| Interaction Live | Supporting mechanism validation. | Keep as controlled validation, not primary official evidence. |
| Causal v2 | Boundary/caveat evidence. | Keep it as probe/contract analysis; do not promote to positive mechanism claim. |
| BFCL fc_core | Paper-safe negative transfer result; guarded schema-top1 candidate-preservation rerun remains Case D. | Keep `planner_binding_headline`, `bfcl_exact_function_guard`, and `bfcl_missing_required_guarded_reduction` as limitations. Candidate visibility is effectively repaired; use the funnel to guide argument/call-shape repair on selected-correct rows. |
| BFCL grounding/multi-turn | Older evidence is not paper-safe where dependency/coverage gaps remain. | Keep separate from fc_core formal. |
| Planner-sensitive v1 | 24-task x 3-run formal v1 is an effect-size scaffold but does not support strong HTGP claim. | Preserve as scaffold; do not promote. |
| Planner-sensitive v2 f2 + held-out | F2 mechanism-supporting formal evidence is committed at `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal`; held-out robustness evidence is available at `outputs/paper_suite/toolsandbox_planner_sensitive_v2_heldout`. | Treat as planner structural mechanism-supporting evidence only. Held-out robustness is positive in 3/4 families, so keep BFCL exact function-calling transfer as a limitation and do not promote HTGP to headline/general planner claim. |
| Strict ladder formal | `s0-s4` strict ladder formal is complete on the 405-row core export. | Use only for paper-facing primary-success non-regression; keep planner-sensitive F2/held-out and reuse v3 as separate mechanism/cost evidence lines. |
| Reuse v2/V3 | Dataset/pipeline ready; committed formal cost evidence missing. | Commit a paper-safe smoke/formal bundle only after warm exact hit, low sham false positive, and positive cost/headroom delta. |
| TAU2 family | Supporting dataset; compound slice sparse. | Expand compound approval plus repair to at least 8-10 tasks before stronger claims. |

## HTGP Planner-Sensitive F2 Evidence

Committed bundle: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal`. Canonical report: `planner_sensitive_summary.md`; generic `report.md` is non-canonical for planner-sensitive claims. The earlier `planner_sensitive_v2_capability_fix_formal` bundle remains historical 3/4 evidence and is superseded for current planner-structural claims.

Current formal results:

| metric | value |
|---|---:|
| source_task_count | 42 |
| family_positive_count | 4 |
| a2_minus_a1_success_delta | 1.000 |
| paired wins/losses/ties | 126 / 0 / 0 |
| capability_order_delta | 1.000 |
| instance_dependency_edge_delta | 1.000 |
| tool_sequence_delta | 1.000 |
| planner_bypass_known_rate | 1.000 |
| known-row planner_bypass_rate | 0.000 |
| leakage_detected | false |
| ordered_gold_structure_leakage_detected | false |
| v2_promotion_ready | true |

Family status:

| family | a2 strict success | interpretation |
|---|---:|---|
| retrieve_summarize_write | 1.000 | positive |
| check_modify_verify | 1.000 | positive |
| branch_select_execute | 1.000 | positive |
| multi_source_merge_write | 1.000 | positive after f2 multi-source execution repair |

Allowed wording: HTGP now has mechanism-supporting structural planner evidence across all four planner-sensitive V2 structural families. Forbidden wording: HTGP is the paper headline mechanism, BFCL exact function-calling transfer is solved, or this suite alone proves broad external planner/binder generalization.

## HTGP Planner-Sensitive Held-Out Robustness Evidence

Held-out bundle: `outputs/paper_suite/toolsandbox_planner_sensitive_v2_heldout`. This suite is a robustness check for the F2 mechanism result, not a replacement headline benchmark. It contains 80 tasks across the same four structural families with held-out paraphrases, renamed tool IDs, deterministic candidate shuffling, strong distractors, and scorer-gold isolation.

Current formal results:

| metric | value |
|---|---:|
| source_task_count | 80 |
| family_positive_count | 3 |
| a2_minus_a1_success_delta | 0.4375 |
| paired wins/losses/ties | 105 / 0 / 135 |
| capability_order_delta | 0.6875 |
| instance_dependency_edge_delta | 0.4375 |
| tool_sequence_delta | 0.4375 |
| planner_bypass_known_rate | 1.000 |
| known-row planner_bypass_rate | 0.000 |
| leakage_task_count | 0 |
| ordered_gold_structure_leakage_task_count | 0 |

Family deltas for `a2_planner - a1_recovery`:

| family | strict-success delta | interpretation |
|---|---:|---|
| retrieve_summarize_write | 0.750 | positive |
| check_modify_verify | 0.750 | positive |
| multi_source_merge_write | 0.250 | positive |
| branch_select_execute | 0.000 | unresolved in held-out |

Allowed wording: HTGP shows held-out robustness on planner-sensitive structural tasks, with positive separation in 3/4 families under paraphrase, tool renaming, shuffled candidates, and distractor stress. Forbidden wording: HTGP has universal held-out robustness, is a headline/general planner claim, or has solved BFCL/exact function-calling transfer.

Do not patch planner or binder against this held-out suite if it is used as paper evidence. Any repair targeting the unresolved held-out family requires a fresh blind held-out-B suite before use as robustness evidence.

Next evidence step before any stronger planner claim: do not patch against the current held-out suite if it remains paper evidence. If pursuing stronger planner robustness, create a fresh blind held-out-B suite rather than tuning on `toolsandbox_planner_sensitive_v2_heldout`; also run cross-suite regression for ToolSandbox official, semantic repair official v1, Interaction Live, BFCL fc_core smoke, and reuse persistent v2 smoke.

## Semantic Repair Paired Evidence

The semantic repair official v1 paired summary is committed at `outputs/paper_final_freeze_20260424/toolsandbox_semantic_repair_official_v1/paired_delta_summary.json` and was computed from `comparison.scored.csv` without rerunning the benchmark. The paired key is `(task_id, run_index)`.

Repair-semantic-positive result from the current committed bundle:

| comparison | expected wins | expected losses | expected ties | expected mean_delta |
|---|---:|---:|---:|---:|
| `a3_full_interaction - a2_planner` | 18 | 0 | 0 | 1.0 |
| `a3_full_interaction - a3_no_query` | 18 | 0 | 0 | 1.0 |
| `a3_full_interaction - a3_noisy_user` | 18 | 0 | 0 | 1.0 |

The probe-only control slice must remain a caveat table. In the current bundle, `a3_full_interaction` ties `a3_noisy_user` on probe-only strict success (`0/0/18`, mean_delta `0.0`), which is contract/probe evidence rather than semantic repair evidence because useful/effective patch metrics remain zero.

## Non-Negotiable Boundaries

- Do not use causal v2 as primary positive semantic repair evidence.
- Do not write TAU2 dual-control as headline until the family is larger and formalized.
- Do not write BFCL fc_core as positive planner/binder transfer evidence.
- Do not write HTGP planner structural contribution as a headline claim. The current f2 V2 bundle supports `mechanism_supporting`; promotion beyond that requires held-out paraphrase evidence and cross-suite regression, and BFCL exact function-calling transfer remains negative.
- Do not write reuse as a performance claim until a committed V3 formal bundle shows exact warm/cold/sham cost/headroom gains.
- Do not describe the strict formal as independent broad planner-overlay or reuse-overlay lift on ToolSandbox core.
- Do not describe cost, tool-call, or user-turn metrics as layer-by-layer monotone from the strict formal.
- Do not describe the 405-row core reproducible export as the complete external/API ToolSandbox suite.
- Do not mix server-side smoke observations with committed paper-safe artifacts without labeling the distinction.


## BFCL Coverage Funnel Update On 2026-04-24

The guarded `bfcl_fc_core` rerun at `869a72e1cc946a0e5e93117d7ac31ebb1f408e2c` remains Case D. `a2_planner` passes wrong-function and tool-selection non-regression versus `a0_baseline`, but official success remains lower and missing-required reduction does not hold. `bfcl_exact_function_guard` and `bfcl_missing_required_guarded_reduction` therefore remain unsupported, not supporting.

The candidate coverage funnel now shows executable candidate visibility is effectively repaired: raw and prepared expected-function coverage match, and the old apparent `prepared_to_runtime_drop=4135` splits into `bfcl_abstain_candidate_elision=4120` plus true `prepared_to_runtime_drop=15` overall (`3` for `a2_planner`). On rows where expected reaches runtime candidates, it reaches schema top-5/top-1 and is selected; the next blocker is argument/call-shape failure on selected-correct rows. See `docs/bfcl_candidate_coverage_rerun_diagnostic_20260424.md`.
