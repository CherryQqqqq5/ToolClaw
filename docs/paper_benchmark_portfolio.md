# Paper Benchmark Portfolio

This note updates the paper-facing benchmark plan after reviewing the current repository, archived outputs, and the newer benchmark landscape.

Canonical claim boundaries are now maintained in [paper_claim_boundary_20260424.md](paper_claim_boundary_20260424.md). If older exploratory notes in this file conflict with that boundary document, use the boundary document and [configs/paper_claim_matrix.yaml](../configs/paper_claim_matrix.yaml) as the source of truth.

## Current mapping

- `toolsandbox_official_core_reproducible_strict`
  - role: current headline source for stateful, conversational, on-policy workflow intelligence on the reproducible ToolSandbox core subset
  - current claims: `interaction_headline`, `strict_layer_monotonicity`
  - result bundle: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict`
  - reason: the 405-row executed core frozen export supersedes the legacy 88-row frozen export for future ToolSandbox headline experiments. The strict ladder has `0 / 4860` adjacent primary-success regressions, with strict success `s0=0.659259`, `s1=0.703704`, `s2=0.703704`, `s3=0.706173`, and `s4=0.706173`.
  - boundary: this is a core reproducible subset, not the external/API ToolSandbox suite; planner overlay and reuse overlay are conservative non-regression layers here, not independent broad-lift claims.

- `toolsandbox_legacy_frozen88`
  - role: historical legacy frozen official-run subset
  - current claim: historical consistency only
  - reason: the 88-row export is retained for provenance but no longer carries the current ToolSandbox core headline source

- `toolsandbox_interaction_causality_formal`
  - role: boundary / caveat suite
  - current claim: `causal_v2_probe_boundary`
  - reason: the full causal suite shows that ToolSandbox gains can be probe/contract-mediated, so it motivates the targeted semantic repair official slice rather than carrying the positive semantic repair mechanism claim itself
  - protocol:
    - `overall`: retained for interaction headline context only
    - `repair_semantic`: `failure_type == state_dependency`
    - `probe_only`: `failure_type in {multiple_user_turn, insufficient_information}`

- `toolsandbox_interaction_live_v1`
  - role: mechanism benchmark for interaction as workflow control signal
  - current claim: mechanism supporting evidence for `interaction_semantic_usefulness_mechanism`
  - reason: the live suite validates the semantic decoder and patch compiler under oracle, partial, noisy, irrelevant, and wrong-parameter user modes; it is supporting evidence, not the primary official mechanism suite
  - protocol:
    - `repair_semantic_primary`: `state_dependency` tasks where the main claim is evaluated
    - `probe_only_control`: `multiple_user_turn` and `insufficient_information` tasks used only as contract/probe caveats
    - negative user modes must keep usefulness metrics near zero and must not count as semantic repair

- `toolsandbox_semantic_repair_official_v1`
  - role: primary targeted official semantic-repair mechanism suite
  - current claim: `interaction_semantic_usefulness_mechanism`
  - reason: the 3-run official-slice bundle shows `a3_full_interaction` separates from `a2_planner`, `a3_no_query`, and `a3_noisy_user` on repair-semantic-positive tasks while useful/effective patch metrics remain zero on probe-only controls
  - protocol:
    - `repair_semantic_positive`: trace-backed official tasks with human-reviewed useful repair signal
    - `probe_only_control`: contract/probe caveat tasks that must not be counted as semantic repair

- `toolsandbox_planner_sensitive_v2_f2` and `toolsandbox_planner_sensitive_v2_heldout`
  - role: mechanism-supporting HTGP structural planner suite plus held-out robustness check
  - current claim: `planner_structural_mechanism`
  - primary result bundle: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_f2_formal`
  - held-out result bundle: `outputs/paper_suite/toolsandbox_planner_sensitive_v2_heldout`
  - reason: the 42-task x 3-run F2 formal bundle remains the canonical strong mechanism evidence with `a2_minus_a1_success_delta = 1.0`, paired wins/losses/ties `126/0/0`, no hint or ordered-gold leakage, known bypass telemetry, controlled cost, and 4/4 positive families. The 80-task held-out suite adds robustness support under paraphrased goals, renamed tools, shuffled candidates, and strong distractors: `a2_minus_a1_success_delta = 0.4375`, paired wins/losses/ties `105/0/135`, no leakage, and 3/4 positive families.
  - boundary: this supports planner structural mechanism evidence and held-out robustness, not a headline or general planner claim; BFCL exact function-calling transfer remains negative and must not be folded into this claim

- `bfcl_fc_core`
  - role: planner / binder / parameter correctness limitation benchmark, with a completed guarded coverage-funnel diagnostic
  - current claim: `planner_binding_headline`, `bfcl_exact_function_guard`, and `bfcl_missing_required_guarded_reduction` remain limitations after the guarded coverage rerun
  - reason: the current full formal bundle is paper-safe but negative for planner/binder headline lift; the schema-top1 guard is designed to test whether wrong-function negative transfer can be suppressed without losing missing-required or argument-repair benefits
  - protocol: include `non_live`, `live`, and `multi_turn` function-calling rows; exclude `web_search`, `memory`, and `format_sensitivity`; runtime selection diagnostics must remain gold-free and A4 must be marked as non-reuse evidence

- `bfcl_agentic_ext`
  - role: supporting-only BFCL v4 extension benchmark
  - current claim: `bfcl_agentic_supporting`
  - reason: BFCL v4 also contains broader agentic capabilities that should not be conflated with binder correctness
  - protocol: route `web_search`, `memory`, and `format_sensitivity` here and keep them out of the main BFCL headline table

- `tau2_dual_control`
  - role: supporting / boundary dual-control interaction benchmark
  - current claim: `dual_control_interaction`
  - reason: shared-world approval and coordination errors are relevant to ToolClaw, but the new TAU2 family still has a sparse compound approval-plus-repair slice and cannot carry a headline claim

- `tau_bench_supporting`
  - role: supporting-only benchmark pending audit promotion
  - current claim: `tau_bench_supporting`
  - reason: the current alignment pipeline is useful for internal comparison, but it is not yet paper-safe for headline claims until the semantic audit gate passes

- `toolsandbox_reuse_persistent_v3`
  - role: mechanism-supporting exact matched-signature reuse benchmark
  - current claim: `reuse_exact_match_cost`
  - result bundle: `outputs/paper_suite/toolsandbox_reuse_persistent_v3`
  - reason: the 3-run formal supports a narrow exact-reuse cost claim on pilot-confirmed high-headroom ToolSandbox core families: 18 primary exact families, 54 primary paired effects, warm exact hit and correct-source rates of 1.0, sham false-positive rate 0.0, and primary tool-call wins/losses/ties 54/0/0
  - boundary: exact matched signatures only; no transfer reuse, BFCL reuse lift, broad ToolSandbox success lift, or verifier-backed skill-learning claim

## Current evidence boundary

- `toolsandbox_official_core_reproducible_strict` is the current ToolSandbox core headline source; the legacy 88-row frozen export is historical evidence only.
- ToolSandbox semantic-usefulness should be treated as a targeted mechanism claim anchored to `toolsandbox_semantic_repair_official_v1`, not a whole-benchmark headline claim.
- Planner overlay should not be sold as an independent ToolSandbox core headline lift. The dedicated `toolsandbox_planner_sensitive_v2_f2` bundle remains the canonical mechanism evidence across all four V2 structural families, and `toolsandbox_planner_sensitive_v2_heldout` adds a robustness check with positive separation in 3/4 held-out families under paraphrase, tool renaming, shuffled candidates, and distractor stress. BFCL exact function-calling transfer remains a limitation. The guarded BFCL adapter can only become narrow supporting evidence after full-suite non-regression gates and the pre-registered baseline-missing-required slice gates pass.
- Reuse is now supported only for the narrow `toolsandbox_reuse_persistent_v3` exact matched-signature second-run tool-call cost claim; no-headroom, transfer, and sham controls remain separate and do not support a broad reuse claim.
- ToolGym is best treated as a later supplementary stress test, not the main paper anchor.
- WebArena, WorkArena, and OSWorld are strong benchmarks, but they move the paper toward browser or computer-use agents rather than workflow intelligence over tool calling.



## Strict ladder formal boundary on 2026-04-26

The strict `s0-s4` ladder is the paper-facing conservative-overlay ladder for the 405-row ToolSandbox core reproducible frozen export. It is separate from the atomic `a0-a4` mechanism-diagnostic systems.

Current strict formal result:

- source: `data/toolsandbox.official_core_reproducible.frozen.json`
- result bundle: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict`
- samples/runs/scored rows: `405 / 3 / 6075`
- adjacent primary-success regressions: `0 / 4860`
- strict success: `s0=0.659259`, `s1=0.703704`, `s2=0.703704`, `s3=0.706173`, `s4=0.706173`
- adjacent wins/losses/ties: `54/0/1161`, `0/0/1215`, `3/0/1212`, `0/0/1215`

Allowed interpretation: the paper-facing strict ladder is primary-success non-regressive on the ToolSandbox core reproducible subset. Do not use this result as planner-overlay broad lift, reuse cost-reduction, or layer-by-layer cost improvement evidence. Planner-sensitive F2/held-out and reuse persistent V3 remain separate mechanism and exact-cost protocols.

## BFCL guarded exact-function adapter boundary on 2026-04-24

The guarded BFCL path is a paper-safety and diagnostic repair, not a planner headline upgrade. It makes BFCL function selection deterministic and schema-top1-first:

- schema top-1 wins ties and zero-coverage planner overrides;
- planner-preferred tools are retained only when already selected by the registered schema ranking policy;
- runtime selection diagnostics exclude expected function, gold call count, gold order, and official failure bucket;
- `bfcl_function_selection_audit.json/md` may add expected function and guardability buckets after execution;
- `reuse_claim_enabled_for_bfcl = false` and `a4_interpreted_as_guarded_execution_variant_only = true`.

Promotion failed in the latest guarded candidate-preservation rerun. `bfcl_exact_function_guard` still requires full-suite wrong-function non-regression, missing-required reduction, tool-selection non-regression, and success non-regression; `a2_success_ge_a0` and `a2_missing_required_lt_a0` did not pass. `bfcl_missing_required_guarded_reduction` additionally requires the pre-registered `baseline_missing_required_slice` gates, which did not pass because the slice has zero a0 rows in this rerun. The funnel now shows candidate visibility is effectively repaired and the next blocker is argument/call-shape failure after the correct function is selected.

## ToolSandbox persistent reuse boundary on 2026-04-27

The paper-facing reuse path is now `toolsandbox_reuse_persistent_v3`, backed by a versioned paired source and a 3-run formal bundle:

- source: `data/toolsandbox_reuse_persistent_v3.jsonl`
- manifest: `data/toolsandbox_reuse_persistent_v3.manifest.json`
- runner: `scripts/run_toolsandbox_reuse_persistent.py`
- scorer: `scripts/score_toolsandbox_reuse_persistent.py`
- result bundle: `outputs/paper_suite/toolsandbox_reuse_persistent_v3`
- result note: `docs/toolsandbox_reuse_v3_formal_20260427.md`

The suite separates pass-1 asset compilation from pass-2 evaluation and compares four pass-2 arms: `a3_interaction`, `a4_reuse_cold`, `a4_reuse_warm`, and `a4_reuse_sham`. Primary gates are computed only on `claim_scope=exact_match_cost` and `claim_inclusion=true`.

Current formal status:

- total formal families: 38
- primary exact/headroom families: 18
- no-headroom controls: 12
- transfer controls: 8
- primary paired effects: 54
- warm exact reuse hit rate: 1.0
- warm exact correct-source match rate: 1.0
- sham false-positive rate: 0.0
- primary tool-call paired wins/losses/ties: 54 / 0 / 0

Allowed interpretation: exact matched-signature reuse reduces second-run tool-call cost on pilot-confirmed high-headroom ToolSandbox core families while preserving success and passing sham safety gates. Forbidden interpretation: broad transfer reuse, BFCL reuse lift, general ToolSandbox `a4 > a3` success, verifier-backed skill learning, or cost monotonicity across all metrics.

## ToolSandbox causality boundary on 2026-04-23

The current ToolSandbox causality instrumentation is implemented in the benchmark runner and analyzer:

- `reply_usable_rate`
- `target_aligned_patch_rate`
- `effective_patch_rate`
- `post_query_progress_rate`
- `useful_interaction_round_rate`

Current boundary:

- causal v2 is not the primary positive semantic repair mechanism evidence.
- causal v2 shows that full-suite gains can be probe/contract-mediated, especially on must-query or probe-only rows.
- the positive mechanism claim is now anchored to `toolsandbox_semantic_repair_official_v1`, whose primary slice is targeted to trace-backed semantic repair.
- noisy-user success on probe-only rows must remain a caveat, not a semantic repair win.

Interaction Live v1 formal run:

- dataset: [data/toolsandbox_interaction_live_v1.jsonl](../data/toolsandbox_interaction_live_v1.jsonl)
- manifest: [data/toolsandbox_interaction_live_v1.manifest.json](../data/toolsandbox_interaction_live_v1.manifest.json)
- result bundle: [outputs/interaction_live_v1_formal/claim_summary.json](../outputs/interaction_live_v1_formal/claim_summary.json)
- verdicts:
  - `interaction_as_control_signal_supported = true`
  - `semantic_usefulness_supported_on_repair_semantic = true`
  - `probe_only_success_caveat_present = true`
  - `noisy_user_not_counted_as_useful_repair = true`
  - `irrelevant_user_not_counted_as_useful_repair = true`
  - `wrong_parameter_not_counted_as_effective_patch = true`
  - `extraction_f1_gate_passed = true`
- repair-semantic success:
  - `a2_planner = 0.375`
  - `a3_no_query = 0.375`
  - `a3_full_interaction_oracle = 1.000`
  - `a3_full_interaction_noisy = 0.625`
- oracle repair-semantic interaction rounds:
  - `reply_usable_rate = 1.000`
  - `target_aligned_patch_rate = 1.000`
  - `effective_patch_rate = 1.000`
  - `post_query_progress_rate = 1.000`
  - `useful_interaction_round_rate = 1.000`
- noisy repair-semantic interaction rounds:
  - all usefulness and progress metrics remain `0.000`
- extraction:
  - `target_f1_oracle = 1.000`
  - `value_f1_oracle = 1.000`
  - `noisy_target_false_positive_rate = 0.000`

## BFCL status on 2026-04-23

BFCL `fc_core` protocol and the official-eval bridge are implemented. A full formal `bfcl_fc_core` run has completed at [outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json](../outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json), and the earlier all-zero official result was traced to two scorer-side failures: the scorer launched the upstream wrapper with server-default `python3.8`, and the wrapper escalated per-row multi-turn dependency failures into a process-wide crash. Both issues are now fixed in benchmark-side code. The current formal bundle is now `paper_safe_for_claim = true` after installing the upstream multi-turn dependency `mpmath` and adding a fail-fast dependency preflight to [scripts/score_bfcl_outputs.py](../scripts/score_bfcl_outputs.py).

### Prepared dataset status

- Tracked scaffold manifest:
  - [data/bfcl/manifest.json](../data/bfcl/manifest.json)
- Tracked formal-source manifest:
  - [data/bfcl_formal/manifest.json](../data/bfcl_formal/manifest.json)
- Tracked formal lock artifact:
  - [configs/bfcl_formal_lock.json](../configs/bfcl_formal_lock.json)
- Formal prepared-source counts recorded in the tracked formal manifest/lock:
  - `fc_core = 4291`
  - `agentic_ext = 455`
  - `excluded = 150`
- Official wrapper path recorded in the formal manifest/lock:
  - [scripts/bfcl_official_wrapper.py](../scripts/bfcl_official_wrapper.py)

### Evidence boundary

- The repository exposes a verifiable formal prepared-source manifest and lock.
- The current server-side formal result bundle is:
  - [outputs/paper_suite_formal/bfcl_fc_core/official_scoreboard.json](../outputs/paper_suite_formal/bfcl_fc_core/official_scoreboard.json)
  - [outputs/paper_suite_formal/bfcl_fc_core/toolclaw_diagnostics.json](../outputs/paper_suite_formal/bfcl_fc_core/toolclaw_diagnostics.json)
  - [outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json](../outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json)
- The current BFCL full formal bundle is paper-safe, but it does not support a planner/binder headline lift.
- Diagnostic slices are frozen at:
  - [outputs/paper_suite_formal/bfcl_fc_core/bfcl_failure_slice_summary.json](../outputs/paper_suite_formal/bfcl_fc_core/bfcl_failure_slice_summary.json)
  - [outputs/paper_suite_formal/bfcl_fc_core/bfcl_failure_slice_summary.md](../outputs/paper_suite_formal/bfcl_fc_core/bfcl_failure_slice_summary.md)

### Formal `bfcl_fc_core` observations

The full formal run now exposes meaningful official scores on supported strata instead of collapsing all systems to zero. Current official results are:

- `a0_baseline`: success `0.0291`, tool selection `0.4265`, structure `0.3873`
- `a1_recovery`: success `0.0280`, tool selection `0.4265`, structure `0.3873`
- `a2_planner`: success `0.0226`, tool selection `0.3407`, structure `0.3020`
- `a3_interaction`: success `0.0221`, tool selection `0.3409`, structure `0.3018`
- `a4_reuse`: success `0.0221`, tool selection `0.3409`, structure `0.3018`

Unsupported official strata are now empty after the `mpmath` dependency fix.

These formal observations support a competence-check framing only:

- supported:
  - BFCL `fc_core` is implemented as a protocol path for planner/binder competence evaluation
  - official evaluator connectivity is now working for all included `fc_core` strata on the full formal run
  - the earlier all-zero BFCL result was a scorer artifact, not a faithful system result
- not yet supported:
  - a headline claim that ToolClaw already shows clear BFCL lift
  - a strong multi-turn BFCL claim
  - a headline-level planner/binder claim where `a2_planner` beats `a0_baseline` or `a1_recovery`

The failure-slice diagnostic shows the main performance gap clearly:

- `a0/a1` retain higher tool-selection and structure scores on the full formal run.
- `a2/a3/a4` reduce `missing_required` failures but introduce many more `wrong_func_name` failures.
- `a2_planner.wrong_func_name = 642`, compared with `a0_baseline.wrong_func_name = 265`.
- `a2_planner.tool_selection = 0.3407`, compared with `a0_baseline.tool_selection = 0.4265`.

This means the remaining BFCL issue is not paper safety. It is planner-path behavior: the planner/adapter path currently introduces enough function-selection error to offset any parameter-grounding improvement.

### Why BFCL still shows weak system separation in local pilots

The current local BFCL pilots still behave more like function-call correctness checks than like blocked, stateful, repair-heavy control tasks.

- BFCL `fc_core` primarily rewards function-call correctness.
- The higher ToolClaw layers are not strongly activated in the current local BFCL pilots.
- Multi-turn decomposition remains the main unsolved path.
- Reuse and interaction therefore do not yet convert into visible BFCL gains.

### Refreshed medium subset on 2026-04-21

A refreshed BFCL medium subset run now exists at:

- [outputs/bfcl_medium_subset_v3/official_scoreboard.json](../outputs/bfcl_medium_subset_v3/official_scoreboard.json)
- [outputs/bfcl_medium_subset_v3/toolclaw_diagnostics.json](../outputs/bfcl_medium_subset_v3/toolclaw_diagnostics.json)
- [outputs/bfcl_medium_subset_v3/claim_summary.json](../outputs/bfcl_medium_subset_v3/claim_summary.json)

This subset uses 28 `fc_core` rows spanning `irrelevance`, `live_irrelevance`, `multiple`, `live_multiple`, `parallel`, `parallel_multiple`, and `simple_python`. After benchmark-side protocol cleanup, all five systems are aligned on the same official score profile:

- `a0_baseline = 0.5714`
- `a1_recovery = 0.5714`
- `a2_planner = 0.5714`
- `a3_interaction = 0.5714`
- `a4_reuse = 0.5714`

The important point is not that BFCL now shows a headline lift. It still does not. The important point is that the earlier separation on this subset was partly contaminated by protocol mismatch in the BFCL runner path. After removing BFCL-specific path artifacts, the remaining failures are concentrated in benchmark-content buckets rather than in system-path noise.

Current bucket observations on `bfcl_medium_subset_v3` are:

- `irrelevance` and `live_irrelevance`: all systems are `1.0`
- `live_multiple`: all systems are `0.5`
- `parallel_multiple`: all systems are `0.5`, with structure improved to `0.75`
- `parallel`: all systems are `0.5`
- `multiple`: all systems remain `0.0`
- `simple_python`: all systems are `0.5`

This refreshed subset is `paper_safe_for_claim = true` because the official evaluator fully covers the included rows. It supports a narrower and cleaner statement:

- supported:
  - the BFCL `fc_core` protocol path is now stable enough for paper-safe subset evaluation
  - current residual failures are concentrated in benchmark content buckets, not in benchmark-side runner corruption
- not supported:
  - any claim that ToolClaw already shows BFCL headline lift over its own lower-layer variants
  - any claim that BFCL currently separates interaction or reuse advantages

### Engineering note

To avoid benchmark overfitting, BFCL-specific argument shaping is intentionally kept outside the shared executor. The benchmark-specific logic lives in [src/toolclaw/bfcl_runtime.py](../src/toolclaw/bfcl_runtime.py) and BFCL runner/prep scripts, while the shared executor remains generic.

## Required repo actions

1. Keep the benchmark-to-claim mapping explicit in [configs/paper_claim_matrix.yaml](configs/paper_claim_matrix.yaml).
2. Use [scripts/run_paper_bench_suite.py](scripts/run_paper_bench_suite.py) as the paper-facing suite entry point.
3. Prepare BFCL source exports with [scripts/prepare_bfcl_source.py](scripts/prepare_bfcl_source.py), then run only protocol-defined BFCL tracks:
   - `bfcl_fc_core`
   - `bfcl_agentic_ext`
4. Keep `tau-bench` supporting-only until [configs/tau_bench_semantic_audit.json](configs/tau_bench_semantic_audit.json) sets `promote_tau_bench` to `true`.
5. Extend reuse evaluation with a deliberately tiered repeated paired taskset:
   - `exact_match_reuse`
   - `same_family_transfer_reuse`
   - `cross_family_transfer_reuse`
6. Keep paper-facing docs on repo-relative paths only.


## BFCL candidate coverage funnel on 2026-04-24

The guarded `bfcl_fc_core` rerun with runtime candidate preservation completed at commit `869a72e1cc946a0e5e93117d7ac31ebb1f408e2c`. It remains Case D: `a2_wrong_func_name_le_a0=true` and `a2_tool_selection_ge_a0=true`, but `a2_success_ge_a0=false` and `a2_missing_required_lt_a0=false`. No BFCL claim is promoted.

The funnel shows raw-to-prepared coverage is not the current blocker (`8125 -> 8125`) and executable candidate visibility is effectively repaired. The previous `prepared_to_runtime_drop=4135` now splits into `bfcl_abstain_candidate_elision=4120` and true `prepared_to_runtime_drop=15` overall; for `a2_planner`, true `prepared_to_runtime_drop=3`. When expected reaches runtime candidates, it reaches schema top-5/top-1 and is selected. The next BFCL implementation target is argument grounding and call-shape canonicalization on selected-correct rows (`selected_correct_arg_or_shape_error=3723` overall, `745` for `a2_planner`).
