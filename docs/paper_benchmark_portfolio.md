# Paper Benchmark Portfolio

This note updates the paper-facing benchmark plan after reviewing the current repository, archived outputs, and the newer benchmark landscape.

## Current mapping

- `toolsandbox_official`
  - role: headline benchmark for stateful, conversational, on-policy workflow intelligence
  - current claim: `interaction_headline`
  - reason: the archived official run already makes interaction/stateful control visible, while `a2_planner = a1_recovery` keeps planner lift non-headline here

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
- Planner should not be sold as a headline lift on ToolSandbox official until a planner-visible benchmark is added.
- Reuse should stay scoped to matched-signature cost reduction.
- ToolGym is best treated as a later supplementary stress test, not the main paper anchor.
- WebArena, WorkArena, and OSWorld are strong benchmarks, but they move the paper toward browser or computer-use agents rather than workflow intelligence over tool calling.

## BFCL status on 2026-04-21

BFCL `fc_core` protocol and the official-eval bridge are implemented. A full formal `bfcl_fc_core` run has completed at [outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json](../outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json), and the earlier all-zero official result was traced to two scorer-side failures: the scorer launched the upstream wrapper with server-default `python3.8`, and the wrapper escalated per-row multi-turn dependency failures into a process-wide crash. Both issues are now fixed in benchmark-side code. The current formal bundle yields non-zero official metrics on supported strata, but `paper_safe_for_claim` remains `false` because multi-turn strata still require missing upstream dependency `mpmath`.

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
- The current BFCL headline claim is still not paper-safe because the official evaluator remains unsupported for several multi-turn strata.

### Formal `bfcl_fc_core` observations

The full formal run now exposes meaningful official scores on supported strata instead of collapsing all systems to zero. Current official results are:

- `a0_baseline`: success `0.0291`, tool selection `0.4265`, structure `0.3873`
- `a1_recovery`: success `0.0280`, tool selection `0.4265`, structure `0.3873`
- `a2_planner`: success `0.0226`, tool selection `0.3407`, structure `0.3020`
- `a3_interaction`: success `0.0221`, tool selection `0.3409`, structure `0.3018`
- `a4_reuse`: success `0.0221`, tool selection `0.3409`, structure `0.3018`

Unsupported official strata are currently:

- `multi_turn_base`
- `multi_turn_long_context`
- `multi_turn_miss_func`
- `multi_turn_miss_param`

All four are blocked by the same upstream runtime dependency gap: `missing_multi_turn_dependency:mpmath`.

These formal observations support a competence-check framing only:

- supported:
  - BFCL `fc_core` is implemented as a protocol path for planner/binder competence evaluation
  - official evaluator connectivity is now working for supported strata on the full formal run
  - the earlier all-zero BFCL result was a scorer artifact, not a faithful system result
- not yet supported:
  - a paper-safe headline BFCL claim
  - a headline claim that ToolClaw already shows clear BFCL lift
  - a strong multi-turn BFCL claim

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
