# Paper Benchmark Portfolio

This note updates the paper-facing benchmark plan after reviewing the current repository, archived outputs, and the newer benchmark landscape.

## Current mapping

- `toolsandbox_official`
  - role: headline benchmark for stateful, conversational, on-policy workflow intelligence
  - current claim: `interaction_headline`
  - reason: the archived official run already makes interaction/stateful control visible, while `a2_planner = a1_recovery` keeps planner lift non-headline here

- `toolsandbox_interaction_causality_formal`
  - role: mechanism-only ToolSandbox causality suite
  - current claim: `interaction_semantic_usefulness_mechanism`
  - reason: semantic-usefulness is not a safe whole-benchmark claim on ToolSandbox aggregate; it should be anchored only to repair-sensitive `state_dependency` slices, with `multiple_user_turn` and `insufficient_information` treated as probe-only / contract-sensitive supporting strata
  - protocol:
    - `overall`: retained for interaction headline context only
    - `repair_semantic`: `failure_type == state_dependency`
    - `probe_only`: `failure_type in {multiple_user_turn, insufficient_information}`

- `toolsandbox_interaction_live_v1`
  - role: mechanism benchmark for interaction as workflow control signal
  - current claim: `interaction_semantic_usefulness_mechanism`
  - reason: the live suite turns the causality finding into a versioned dataset with oracle, partial, noisy, irrelevant, and wrong-parameter user modes, then scores whether replies become target-aligned effective patches and post-query progress
  - protocol:
    - `repair_semantic_primary`: `state_dependency` tasks where the main claim is evaluated
    - `probe_only_control`: `multiple_user_turn` and `insufficient_information` tasks used only as contract/probe caveats
    - negative user modes must keep usefulness metrics near zero and must not count as semantic repair

- `bfcl_fc_core`
  - role: headline planner / binder / parameter correctness benchmark
  - current claim: `planner_binding_headline`
  - reason: only the function-calling core strata should carry the planner/binder headline claim
  - protocol: include `non_live`, `live`, and `multi_turn` function-calling rows; exclude `web_search`, `memory`, and `format_sensitivity`

- `bfcl_agentic_ext`
  - role: supporting-only BFCL v4 extension benchmark
  - current claim: `bfcl_agentic_supporting`
  - reason: BFCL v4 also contains broader agentic capabilities that should not be conflated with binder correctness
  - protocol: route `web_search`, `memory`, and `format_sensitivity` here and keep them out of the main BFCL headline table

- `tau2_dual_control`
  - role: dual-control interaction benchmark
  - current claim: `dual_control_interaction`
  - reason: shared-world approval and coordination errors are much closer to ToolClaw's interactive correction claim than generic tool benchmarks

- `tau_bench_supporting`
  - role: supporting-only benchmark pending audit promotion
  - current claim: `tau_bench_supporting`
  - reason: the current alignment pipeline is useful for internal comparison, but it is not yet paper-safe for headline claims until the semantic audit gate passes

- `reuse_exact_match`
  - role: narrow reuse claim benchmark
  - current claim: `reuse_exact_match_cost`
  - reason: the repo only supports an exact-match cost-compression claim today, not a broad transfer claim

## Current evidence boundary

- ToolSandbox official should stay the main headline benchmark.
- ToolSandbox semantic-usefulness should be treated as a mechanism claim, not a whole-benchmark headline claim.
- Planner should not be sold as a headline lift on ToolSandbox official until a planner-visible benchmark is added.
- Reuse should stay scoped to exact/matched-signature cost reduction, and persistent-reuse claims must use a two-stage registry protocol rather than same-process cache hits.
- ToolGym is best treated as a later supplementary stress test, not the main paper anchor.
- WebArena, WorkArena, and OSWorld are strong benchmarks, but they move the paper toward browser or computer-use agents rather than workflow intelligence over tool calling.

## ToolSandbox persistent reuse boundary on 2026-04-23

The paper-facing reuse path is now `toolsandbox_reuse_persistent_v1`, backed by a versioned paired source:

- source: `data/toolsandbox_reuse_persistent_v1.jsonl`
- manifest: `data/toolsandbox_reuse_persistent_v1.manifest.json`
- runner: `scripts/run_toolsandbox_reuse_persistent.py`
- scorer: `scripts/score_toolsandbox_reuse_persistent.py`

The suite separates pass-1 asset compilation from pass-2 evaluation and compares four pass-2 arms: `a3_interaction`, `a4_reuse_cold`, `a4_reuse_warm`, and `a4_reuse_sham`. The `sham` arm is mandatory because a paper-safe persistent-reuse claim requires showing that unrelated registries do not produce the same benefit.

Initial smoke status:

- registry preflight passes and `a4_reuse_warm` can hit persistent assets.
- `a4_reuse_cold` has no reuse hits, so same-invocation cache contamination is controlled.
- `a4_reuse_sham` still shows high reuse hits with wrong source-family matches.
- the current curated slice has no visible cost headroom: success, tool-call count, repair count, and user turns are already identical across cold and warm arms.

This means the current suite is implemented, but the formal run is intentionally gated. It currently supports a diagnostic statement that persistent reuse is triggerable, while also exposing an over-broad retrieval / false-positive risk. It does not yet support a second-run cost-reduction paper claim.

## ToolSandbox causality boundary on 2026-04-23

The current ToolSandbox causality instrumentation is implemented in the benchmark runner and analyzer:

- `reply_usable_rate`
- `target_aligned_patch_rate`
- `effective_patch_rate`
- `post_query_progress_rate`
- `useful_interaction_round_rate`

Exploratory bundle [outputs/paper_causal_v2_full_r1/causal_claim_summary.json](../outputs/paper_causal_v2_full_r1/causal_claim_summary.json) already shows that `interaction_not_cheating_supported = true`, but it also shows that the semantic-usefulness signal is sparse and concentrated in `state_dependency` rows. In that exploratory run, the useful interaction rounds are confined to six repair-sensitive tasks, while `multiple_user_turn` and `insufficient_information` mostly behave as probe-only / contract-satisfaction slices.

This means the current evidence supports the following boundary:

- supported after formal freeze:
  - a mechanism claim that semantic-usefulness and target-aligned patch explain interaction gains on repair-sensitive ToolSandbox slices
  - a caveat claim that must-query slices are not clean semantic-usefulness evidence
- not supported:
  - a claim that all ToolSandbox interaction gain comes from semantic-usefulness
  - a claim that noisy-user collapse should occur across the whole benchmark aggregate

The paper-facing causality suite therefore needs to be frozen separately from the main `toolsandbox_official` headline run.

Formal freeze on 2026-04-23:

- frozen bundle: `outputs/paper_final_freeze_20260423/toolsandbox_interaction_causality_formal`
- verdicts:
  - `overall_interaction_query_contribution_supported = true`
  - `repair_semantic_usefulness_supported = true`
  - `probe_only_success_caveat_present = true`
  - `interaction_not_cheating_supported = true`
- repair-semantic slice:
  - `a2_planner.strict_scored_success = 0.50`
  - `a3_full_interaction.strict_scored_success = 1.00`
  - `a3_no_query.strict_scored_success = 0.50`
  - `a3_noisy_user.strict_scored_success = 0.50`
  - `a3_full_interaction.reply_usable_rate = 0.50`
  - `a3_full_interaction.target_aligned_patch_rate = 0.50`
  - `a3_full_interaction.effective_patch_rate = 0.50`
  - `a3_full_interaction.post_query_progress_rate = 0.50`
  - `a3_full_interaction.useful_interaction_round_rate = 0.50`
  - `a3_noisy_user` usefulness metrics remain `0.00`
- probe-only slice:
  - `a3_full_interaction.strict_scored_success = 1.00`
  - `a3_noisy_user.strict_scored_success = 1.00`
  - both arms keep usefulness metrics at `0.00`
  - this slice therefore remains contract/probe evidence, not semantic patch evidence

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
- The current BFCL full formal bundle is paper-safe, but it does not support a headline planner/binder lift.
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
