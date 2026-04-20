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

## BFCL status on 2026-04-20

This repository now has a prepared formal BFCL split and a working official-eval bridge, but the reported evidence is still based on small `fc_core` probes rather than a full 4291-row paper run.

### Prepared dataset status

- Formal prepared source: [data/bfcl_formal/manifest.json](../data/bfcl_formal/manifest.json)
- Current counts:
  - `fc_core = 4291`
  - `agentic_ext = 455`
  - `excluded = 150`
- Official wrapper path recorded in the manifest:
  - [scripts/bfcl_official_wrapper.py](../scripts/bfcl_official_wrapper.py)

### Current scored outputs

- Small 3-case probe:
  - scoreboard: [outputs/paper_suite_bfcl_refresh3/bfcl_fc_core/official_scoreboard.json](../outputs/paper_suite_bfcl_refresh3/bfcl_fc_core/official_scoreboard.json)
  - diagnostics: [outputs/paper_suite_bfcl_refresh3/bfcl_fc_core/toolclaw_diagnostics.json](../outputs/paper_suite_bfcl_refresh3/bfcl_fc_core/toolclaw_diagnostics.json)
- Current 12-case pilot:
  - scoreboard: [outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/official_scoreboard.json](../outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/official_scoreboard.json)
  - scored rows: [outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/comparison.scored.csv](../outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/comparison.scored.csv)
  - diagnostics: [outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/toolclaw_diagnostics.json](../outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/toolclaw_diagnostics.json)

### Probe3 result summary

The current 3-case probe is no longer a fake-positive baseline run. All systems now execute BFCL tools directly and land at the same official score:

| system | official success | tool selection | argument | structure |
| --- | ---: | ---: | ---: | ---: |
| `a0_baseline` | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| `a1_recovery` | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| `a2_planner` | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| `a3_interaction` | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| `a4_reuse` | 0.6667 | 0.6667 | 0.6667 | 0.6667 |

Passed tasks for all five systems:

- `live_simple_0-0-0`
- `simple_python_0`

Failed task for all five systems:

- `multi_turn_base_0`

Interpretation: the single-turn BFCL path is now working, but the multi-turn path remains unsolved.

### Pilot12 result summary

The current 12-case pilot is the best compact view of BFCL `fc_core` performance:

| system | official success | count | tool selection | argument | structure |
| --- | ---: | ---: | ---: | ---: | ---: |
| `a0_baseline` | 0.5833 | 7/12 | 0.6667 | 0.5833 | 0.6667 |
| `a1_recovery` | 0.5833 | 7/12 | 0.6667 | 0.5833 | 0.6667 |
| `a2_planner` | 0.5000 | 6/12 | 0.5833 | 0.5000 | 0.5833 |
| `a3_interaction` | 0.3333 | 4/12 | 0.5000 | 0.3333 | 0.4167 |
| `a4_reuse` | 0.3333 | 4/12 | 0.5000 | 0.3333 | 0.4167 |

Passed task IDs by system:

- `a0_baseline` and `a1_recovery`
  - `live_multiple_0-0-0`
  - `live_simple_0-0-0`
  - `live_simple_1-1-0`
  - `parallel_0`
  - `parallel_1`
  - `simple_python_0`
  - `simple_python_1`
- `a2_planner`
  - `live_simple_0-0-0`
  - `live_simple_1-1-0`
  - `parallel_0`
  - `parallel_1`
  - `simple_python_0`
  - `simple_python_1`
- `a3_interaction` and `a4_reuse`
  - `live_simple_0-0-0`
  - `live_simple_1-1-0`
  - `simple_python_0`
  - `simple_python_1`

Main failed buckets:

- All systems still fail:
  - `multi_turn_base_0`
  - `multi_turn_base_1`
  - `multi_turn_miss_param_0`
  - `multi_turn_miss_param_1`
  - `live_multiple_1-0-1`
- `a2_planner` also loses:
  - `live_multiple_0-0-0`
- `a3_interaction` and `a4_reuse` also lose:
  - `live_multiple_0-0-0`
  - `parallel_0`
  - `parallel_1`

### Why BFCL currently shows weak system separation

The present BFCL results do not support a monotonic `a0 -> a4` performance ladder. The reasons are structural, not just noise.

1. BFCL `fc_core` currently rewards function-call correctness more than ToolClaw's higher-level control stack.
   - The official output only scores `success`, `tool_selection`, `argument`, and `structure`.
   - It does not directly reward interaction quality, repair quality, or reuse utility in the main score.

2. The higher ToolClaw layers are barely activated in the current BFCL pilot.
   - In [outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/toolclaw_diagnostics.json](../outputs/paper_suite_bfcl_pilot12_refresh3/bfcl_fc_core/toolclaw_diagnostics.json), all five systems have `toolclaw_diagnostics_repair_overhead = 0.0`.
   - This means the BFCL tasks in the current pilot are not producing the blocked, repair-heavy execution pattern that normally reveals `a1`, `a3`, or `a4`.

3. The current BFCL runtime backend is still a stubbed function-call environment.
   - Representative traces record `run_manifest.tool_runtime_backend = "bfcl_stub"`.
   - This keeps the task close to function-call generation and away from the richer stateful recovery loop where ToolClaw's interaction layer is strongest.

4. `a3_interaction` only helps when execution actually blocks.
   - In [scripts/run_eval.py](../scripts/run_eval.py), `a3_interaction` and `a4_reuse` differ from planner/executor mainly through `shell.run(...)`.
   - In [src/toolclaw/interaction/irc.py](../src/toolclaw/interaction/irc.py), the real interaction loop only expands once `outcome.blocked` is true.
   - The current BFCL pilot mostly does not block, so `a3` has little chance to produce upside.

5. `a4_reuse` does not yet have a strong BFCL reuse regime.
   - Hard cases such as `multi_turn_base_0` still show `reuse_mode = "none"` and empty `selected_match`.
   - Easier cases can load a transfer prior, but the recorded `utility_gain_score` is still `0.0`, which means reuse is not generating additional measurable correctness on this pilot.

### Current BFCL claim boundary

- Supported today:
  - ToolClaw can now execute a meaningful single-turn and partial parallel BFCL `fc_core` slice with real official scoring.
  - The benchmark is usable as a planner/binder competence check.
- Not supported today:
  - A headline claim that planner, interaction, or reuse produces clear lift on BFCL.
  - A strong multi-turn BFCL claim.

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
