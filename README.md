# ToolClaw

ToolClaw is a training-free workflow intelligence layer for tool-calling agents under controlled execution backends.

The repository currently contains:

- a stable phase-1-style implementation contract for planning, recovery, interaction, and reuse
- phase-2 follow-up mechanisms that have been implemented and benchmarked on targeted slices
- benchmark runners and reports for ToolSandbox-style evaluations, including simulator-backed and OpenRouter-backed interaction experiments

The authoritative implementation boundary is [docs/method.md](docs/method.md). This README is a repository status summary, not a broader claim than the method contract.

Paper-facing benchmark planning now lives in [docs/paper_benchmark_portfolio.md](docs/paper_benchmark_portfolio.md) and [configs/paper_claim_matrix.yaml](configs/paper_claim_matrix.yaml).

## Current Status

- Phase-1 contract: implemented and reproducible
- Phase-2 follow-ups: partially implemented and partially validated
- Current paper-facing ToolSandbox headline source: `outputs/paper_suite/toolsandbox_official_core_reproducible_planner_admission`
- Current strict 405-core ladder from the runtime-visible certified planner-admission bundle: `s0=0.659259`, `s1=0.703704`, `s2=0.703704`, `s3=0.706173`, `s4=0.706173`
- Interaction is bounded by the latest full-core cost audit: `s3` adds 3 strict wins over `s2` with 0 losses and 1212 ties, at 120 user queries and 119 probe queries per additional win; planner broad core utility remains unsupported
- Reuse has no demonstrated full405 strict-success lift over interaction and does not establish broad transfer-reuse gains
- Exact-match reuse cost reduction is supported only on targeted high-headroom recovery cases

## System Ladder

The current system ladder is defined in [scripts/run_eval.py](scripts/run_eval.py).

- `a0_baseline`: baseline execution over the demo workflow
- `a1_recovery`: recovery-only execution over the demo workflow
- `a2_planner`: planner + recovery
- `a3_interaction`: planner + recovery + interaction
- `a4_reuse`: `a3_interaction` + reuse compilation / retrieval

Important interpretation rule:

- this ladder describes mechanism addition
- it does not guarantee monotonic gains on every benchmark slice

## Runtime Architecture

### Planner and binder

- `HTGPPlanner` builds workflows from task/context
- `ToolBinder` uses lexical, capability, metadata, state-precondition, ordering, and backup-tool signals
- ordering-sensitive tasks can emit checkpoint / fallback / rollback hints into the workflow graph

### Recovery and interaction

- the executor runs until success, failure, or blocked interaction
- the interaction shell uses:
  - rule-based uncertainty detection
  - rule-based query planning
  - configurable reply providers
  - rule-based semantic decoding and repair update application

### Reuse

- SWPC compiles successful traces into reusable artifacts
- registry matching now tracks stricter reuse admission
- reuse distinguishes exact vs transfer-style matches internally
- reuse can roll back to `a3_interaction` behavior when early deviation / repair-overflow signals are detected
- repair-sensitive missing inputs are intentionally suppressed from early reuse injection
- exact-match auto-replay can pre-apply selected verified patch / fallback continuations on matched recovery cases

## Interaction Backends

ToolClaw interaction is not an end-to-end LLM agent loop.

Current split:

- query generation: rule-based
- reply provider: simulator / human / CLI / LLM
- reply decoding: rule-based

The `llm` reply backend is wired through [scripts/run_eval.py](scripts/run_eval.py) and [scripts/run_toolsandbox_bench.py](scripts/run_toolsandbox_bench.py). In benchmark runs it can call OpenRouter-backed chat completions, but the policy and decoder layers remain programmatic.

## What The Repository Supports

Current repository-supported claims:

- controlled workflow intelligence over `mock`, `semantic_mock`, and `hybrid` execution backends
- planner / recovery / interaction / reuse layer activation on ToolSandbox-style tasks
- simulator-backed and OpenRouter-backed interaction reply experiments
- heuristic artifact promotion with contamination guards
- stricter reuse admission and rollback behavior than the earlier repo state
- exact-match reusable continuation replay for selected repair / fallback suffixes

Current repository-non-claims:

- full real ToolSandbox execution fidelity
- verifier-backed artifact promotion with version governance
- production-grade external LLM orchestration service
- stable headline gains from reuse over `a3_interaction`
- broad transfer-reuse generalization gains
- stable interaction-turn reduction from reuse on approval-heavy exact-match cases

## Current Benchmark Picture

### Current 405-scenario ToolSandbox core strict ladder

The current paper-facing strict bundle is `outputs/paper_suite_runtime_visible_20260428/toolsandbox_official_core_reproducible_planner_admission`. It was rerun with `hint_policy=runtime_visible`, preserves the strict ladder numbers, and is the canonical current ToolSandbox core headline source. The matching boundary notes are `docs/paper_claim_boundary_20260424.md` and `docs/toolsandbox_core_strict_ladder_formal_20260427.md`.

Current repo-supported strict headline numbers:

| system | strict_success |
| --- | ---: |
| `s0_baseline` | 0.659259 |
| `s1_recovery` | 0.703704 |
| `s2_planner_overlay` | 0.703704 |
| `s3_interaction_overlay` | 0.706173 |
| `s4_reuse_overlay` | 0.706173 |

Adjacent paired counts:

| comparison | wins | losses | ties |
| --- | ---: | ---: | ---: |
| `s1>=s0` | 54 | 0 | 1161 |
| `s2>=s1` | 0 | 0 | 1215 |
| `s3_interaction_overlay_ge_s2_planner_overlay` | 3 | 0 | 1212 |
| `s4_reuse_overlay_ge_s3_interaction_overlay` | 0 | 0 | 1215 |

Interpretation:

- interaction adds only a small probe-heavy strict-core success delta after recovery and planning
- planner is mechanism evidence on planner-sensitive slices, not broad core lift
- reuse preserves strict-core interaction success but has no demonstrated full405 success lift

### Historical core-slice reuse problem

The historical pre-fix mechanism analysis showed:

- on the bundled 14-sample core slice, `a4_reuse = 0.857 < a3_interaction = 0.929`
- reuse held-out split did not show a stable success gain
- older Tau2 evidence did not justify a strong compound approval+repair claim; the 2026-04-23 v2 rerun now solves the isolated compound task for `a3` and `a4`, but reuse still does not exceed interaction

These older results should still be treated as the historical reason the reuse and interaction fixes were added.

### 2026-04-19 targeted follow-up results

Recent targeted follow-ups on the server update the interpretation of the reuse regression, but not the main official headline result.

1. Reuse failure analysis on `outputs/remote/toolsandbox_core_r3_persist_pass2`

- paired cases: `30`
- regressed cases: `6`
- regressed tasks: `2`
- all regressed cases were classified as `artifact_used_too_early`

2. Post-fix 3-run targeted core bench on `outputs/remote/toolsandbox_core_r3_gatefix_bench`

- paired cases: `30`
- regressed cases: `0`
- regressed tasks: `0`
- `a3_interaction` and `a4_reuse` both reached `mean_success_rate = 1.0`
- `a4_reuse` still reused artifacts on `12/30` rows in `comparison.raw.csv`
- those reuse hits were transfer-style (`transfer_reuse` / `unresolved_transfer_reuse`)
- they produced no observed score gain and no observed score regression versus `a3_interaction`

Current interpretation:

- the specific reuse-timing regression exposed by the earlier core analysis appears fixed
- current evidence supports "reuse is safer than before"
- current evidence still does not support "reuse improves over `a3_interaction`"

### 2026-04-19 exact-match continuation follow-up

Recent Tau2 repeated-task follow-ups refine the current reuse interpretation.

1. ToolSandbox persistent reuse slices remain weak positive-evidence generators

- simulator headroom analysis on `outputs/remote/reuse_strata_toolsandbox_continuation_v3/reuse_headroom_analysis.json` reports `candidate_case_count = 0`
- LLM/OpenRouter headroom analysis on `outputs/remote/reuse_strata_toolsandbox_continuation_llm/reuse_headroom_analysis.json` also reports `candidate_case_count = 0`
- interpretation: these ToolSandbox persistent slices remain useful for safety / no-regression checks, but not for a strong positive reuse-gain claim

2. Tau2 exact-match high-headroom reuse now shows narrow cost benefit

- outdir: `outputs/remote/reuse_strata_tau2_auto_replay_v4`
- `exact_match_reuse`:
  - `paired_cases = 5`
  - `delta_tool_calls = -0.4`
  - `delta_repair_actions = -0.4`
  - `delta_user_turns = 0.0`
- `cross_family_transfer_reuse` remains at `0.0` delta on success and cost metrics
- the observed gain is concentrated in two exact-match high-headroom recovery cases:
  - `tau2_binding_auto_001__pass2`
  - `tau2_env_backup_001__pass2`
- in both cases, `a4_reuse` removes one repair and one downstream tool call relative to `a3_interaction`
- approval-heavy exact-match cases still do not reduce `user_turns`

Current interpretation:

- the repository now supports a narrow reuse claim under matched task signatures
- exact-match reuse can reduce downstream repair/tool cost on high-headroom recovery cases
- the repository still does not support broad transfer-reuse claims
- the repository still does not support a claim that reuse broadly improves over interaction across ToolSandbox-style benchmarks

## Quick Start

### Run tests

```bash
pytest -q
```

### Run one evaluation over a normalized taskset

```bash
PYTHONPATH=src python3 scripts/run_eval.py \
  --taskset data/eval_tasks.sample.json \
  --outdir outputs/eval \
  --systems a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse
```

Outputs:

- `outputs/eval/comparison.csv`
- `outputs/eval/report.md`
- `outputs/eval/traces/*.json`

### Run ToolSandbox benchmark slices

```bash
PYTHONPATH=src python3 scripts/run_toolsandbox_bench.py \
  --source data/toolsandbox.formal.official.json \
  --outdir outputs/toolsandbox_bench \
  --systems a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse \
  --num-runs 3
```

Outputs:

- `outputs/toolsandbox_bench/comparison.raw.csv`
- `outputs/toolsandbox_bench/comparison.scored.csv`
- `outputs/toolsandbox_bench/scoreboard.json`
- `outputs/toolsandbox_bench/per_system_summary.json`
- `outputs/toolsandbox_bench/report.md`

### Use OpenRouter-backed interaction replies

```bash
PYTHONPATH=src python3 scripts/run_toolsandbox_bench.py \
  --source data/toolsandbox.formal.official.json \
  --outdir outputs/toolsandbox_bench_openrouter \
  --systems a3_interaction,a4_reuse \
  --num-runs 1 \
  --interaction-target llm_openrouter \
  --openrouter-model openai/gpt-4o-mini
```

## Repository Structure

```text
ToolClaw/
├── src/toolclaw/
│   ├── planner/
│   ├── execution/
│   ├── interaction/
│   ├── compiler/
│   ├── benchmarks/
│   ├── schemas/
│   ├── tools/
│   ├── registry.py
│   └── main.py
├── docs/
│   ├── method.md
│   ├── toolsandbox_all_experiments_report.md
│   └── schemas/
├── scripts/
│   ├── run_eval.py
│   ├── run_toolsandbox_bench.py
│   ├── analyze_a3_a4_reuse_regressions.py
│   ├── analyze_reuse_strata.py
│   └── run_tau2_compound_approval_repair_ablation.py
├── data/
├── outputs/
└── tests/
```

## Practical Caveats

- prefer [docs/method.md](docs/method.md) for implementation-level claims
- prefer [docs/toolsandbox_all_experiments_report.md](docs/toolsandbox_all_experiments_report.md) for benchmark interpretation
- for reuse provenance, prefer `comparison.raw.csv` when auditing individual runs; some scored summaries may omit detailed reuse provenance columns
