# ToolClaw x ToolSandbox Experiment Design

This note fixes one concrete evaluation design for running ToolClaw on top of the ToolSandbox benchmark.

Important distinction for any paper or experiment note:

- `official ToolSandbox execution`: scenarios are executed inside the official ToolSandbox environment and scored by its own artifacts
- `ToolClaw proxy evaluation over ToolSandbox-style tasks`: ToolClaw executes normalized tasks derived from ToolSandbox scenarios, and ToolClaw then writes a fresh proxy `toolsandbox_result` summary onto each trace

Do not report proxy-evaluation numbers as official ToolSandbox execution numbers.

## 0. Experimental Guardrails

The current ToolSandbox scripts support several modes that look similar from the outside but are not interchangeable in a writeup.

### Official-source requirement

If you want to claim a real ToolSandbox-derived formal benchmark, you should have an official run directory under:

- `data/external/ToolSandbox/data/<official_run_dir>/`

At minimum this should include:

- `result_summary.json`

Preferably it should also include:

- `trajectories/<scenario>/conversation.json`
- `trajectories/<scenario>/scenario_export.json` or another accepted scenario export file

That is the data path consumed by `prepare_toolsandbox_official_run.py` and `prepare_toolsandbox_formal_dataset.py`.

### Core vs full benchmark

Current wrapper semantics:

- `scripts/run_toolsandbox_formal.sh` by default runs the **core benchmark** because augmentations are excluded
- `scripts/run_toolsandbox_formal.sh --full-benchmark` is the stronger mode for a real full benchmark because it:
  - rebuilds from an official run
  - includes augmentations
  - disables fallback to the bundled core dataset

If no official run exists locally, the wrapper can still seed `data/toolsandbox.formal.official.json` from the bundled `data/toolsandbox.formal.json`, but that output is only a local convenience path and should not be described as a full official benchmark.

### Repeat count

`num_runs=1` is useful for smoke or one-shot debugging only.

If you want `mean_success_rate`, `pass@k`, or `consistency` to be meaningful, run with `--num-runs >= 3`.

### Reuse persistence

Default Phase-1 execution uses an in-memory asset registry, so A4 reuse is only guaranteed within the current process.

If you want reuse artifacts to survive across repeated CLI invocations, you must opt into a file-backed registry with:

- `run_eval.py --asset-registry-root ...`
- `run_toolsandbox_bench.py --asset-registry-root ...`
- `run_toolsandbox_formal.sh --asset-registry-root ...`

The immediate goal is not to maximize a single leaderboard number. The goal is to isolate where ToolClaw's workflow layer should create measurable gains over a direct tool-calling baseline:

- planning under multi-tool dependencies
- clarification under missing information
- recovery under stateful execution
- safer behavior when the correct action is to ask instead of hallucinate

## 1. Interface Assumption

`ToolSandboxAdapter` accepts JSON / JSONL samples in a ToolSandbox-style shape and normalizes them into ToolClaw `PlanningRequest`s.

Recommended fields:

- `name` / `sample_id`
- `messages`
- `tool_allow_list`
- `categories`
- `milestones`
- `ideal_turn_count`
- `ideal_tool_calls`
- `result_summary` (optional, for post-run scoring)

The adapter currently emits:

- normalized `query`
- ToolClaw `candidate_tools`
- ToolSandbox-aware metadata (`categories`, `milestone_count`, `requires_interaction`)
- score fields aligned to ToolSandbox-style evaluation: `milestone_similarity`, `milestone_coverage`, `turn_efficiency`, `tool_efficiency`, `interaction_efficiency`, `hallucination_avoidance`

## 2. Primary Experiment Table

| Experiment slice | Main question | Primary metric | Secondary metrics | Baseline definition | Expected ToolClaw gain |
|---|---|---|---|---|---|
| All categories | Does ToolClaw improve end-to-end task completion on ToolSandbox? | `milestone_similarity` and binary success rate | `milestone_coverage`, `tool_efficiency`, `turn_efficiency` | Same backbone model, same tool list, same ToolSandbox tasks, but no ToolClaw planner / repair / interaction controller | Medium |
| `state_dependency` + `multiple_tool` | Does explicit workflow structure help when correct actions depend on prior tool state? | `milestone_similarity` | `tool_efficiency`, recovery salvage rate | Same model with direct next-step tool calling only | High |
| `insufficient_information` + `multiple_user_turn` | Does ToolClaw ask clarifying questions instead of hallucinating? | `hallucination_avoidance`, `interaction_efficiency` | success rate, `milestone_similarity` | Same model, same user simulator, but no explicit ask-user / resume loop | Highest |
| `canonicalization` | Does ToolClaw reduce argument-formatting / slot-binding errors? | `milestone_coverage` | `tool_efficiency`, invalid-call rate | Same model with direct tool calling and no binding repair | Medium |
| `single_tool` + `single_user_turn` | Does ToolClaw impose avoidable overhead on easy cases? | success parity | `tool_efficiency`, `turn_efficiency` | Same model, same tool interface | Low or neutral |

## 3. What To Measure

Use one primary metric family and two control metric families.

| Metric | Definition | Why it matters for ToolClaw |
|---|---|---|
| `milestone_similarity` | Official or ToolSandbox-style scenario similarity score | Best end-to-end correctness signal |
| Binary success rate | `similarity >= threshold` or benchmark-native success flag | Needed for clean A/B reporting |
| `milestone_coverage` | Matched milestones / expected milestones | Separates near-miss from total failure |
| `hallucination_avoidance` | No out-of-allow-list tool call when information is missing | Directly tests whether ToolClaw abstains and asks |
| `interaction_efficiency` | Whether user turns are used when needed and avoided when not needed | Tests ToolClaw's interaction loop as control logic |
| `tool_efficiency` | Extra tool calls relative to ideal tool budget | Prevents buying wins with brute-force retries |
| `turn_efficiency` | Extra turns relative to ideal turn budget | Controls user burden and latency |
| Recovery salvage rate | Success among runs that first entered a repair path | Tests ToolClaw's recovery layer directly |

Recommended reporting order:

1. Overall binary success rate
2. Mean `milestone_similarity`
3. Per-category breakdown
4. `hallucination_avoidance` on missing-information slices
5. `tool_efficiency` / `turn_efficiency` as overhead controls

## 4. Baseline Definition

Use a strict baseline first. Otherwise the comparison will not isolate ToolClaw.

| Baseline | Definition | Keep fixed |
|---|---|---|
| `B0_direct_agent` | Same backbone model, same prompt budget, same ToolSandbox tool list, same user simulator, but direct tool-calling only | model, task split, tool schema, max turns, decoding settings |
| `B1_native_toolsandbox_agent` | ToolSandbox's native direct agent implementation, if available for the chosen backbone | model, benchmark split, tool availability |
| `A_toolclaw` | Same backbone wrapped by ToolClaw planning + repair + interaction loop | everything above stays fixed except the workflow layer |

Do not change model, prompt length, or tool set between `B0/B1` and `A_toolclaw`.
If those move together, the result is no longer about ToolClaw.

## 5. Highest-Leverage Categories

If compute is limited, prioritize categories in this order.

| Priority | Category | Why it is likely to separate ToolClaw from baseline |
|---|---|---|
| 1 | `insufficient_information` | ToolClaw should ask, pause, and resume instead of fabricating tool arguments |
| 2 | `state_dependency` | ToolClaw's explicit workflow state and repair logic should help most here |
| 3 | `multiple_user_turn` | ToolClaw has a real interaction loop; direct agents often treat user turns as prompt noise |
| 4 | `multiple_tool` | Planning and dependency ordering should matter more than on easy slices |
| 5 | `canonicalization` | Binding repair may improve robustness, but gains are usually smaller than in interaction/state slices |
| 6 | `single_tool` / `single_user_turn` | Mostly an overhead sanity check, not the best place to show advantage |

## 6. Minimal Readout

For one paper-style table, report:

| System | All | State dep. | Missing info | Multi-user-turn | Multi-tool | Canonicalization | Tool eff. | Turn eff. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `B0_direct_agent` | success / similarity | ... | ... | ... | ... | ... | ... | ... |
| `A_toolclaw` | success / similarity | ... | ... | ... | ... | ... | ... | ... |
| Delta | ... | ... | ... | ... | ... | ... | ... | ... |

This is the smallest table that still answers whether ToolClaw helps, where it helps, and what it costs.

## 7. Recommended Commands

Core benchmark, local validation only:

```bash
scripts/run_toolsandbox_formal.sh \
  --num-runs 3
```

Current ToolSandbox benchmark outputs now also include a focused slice summary for the three highest-value paper slices:

- `focused_slice_summary.md`
- `focused_slice_summary.json`

These files prioritize:

- `insufficient_information`
- `multiple_user_turn`
- `single_tool`

and precompute A3-vs-baseline / A4-vs-A3 deltas for those categories.

Full benchmark from a real official run:

```bash
scripts/run_toolsandbox_formal.sh \
  --full-benchmark \
  --num-runs 3
```

Full benchmark with persistent A4 reuse across repeated launches:

```bash
scripts/run_toolsandbox_formal.sh \
  --full-benchmark \
  --num-runs 3 \
  --asset-registry-root outputs/toolsandbox_assets
```

Two-stage reuse protocol with compile/eval splits:

```bash
python3 scripts/run_reuse_split_experiment.py \
  --train-taskset data/toolsandbox.reuse.train.json \
  --eval-taskset data/toolsandbox.reuse.eval.json \
  --outdir outputs/reuse_split_toolsandbox \
  --asset-registry-root outputs/reuse_split_toolsandbox/assets
```

This protocol is preferable to exact pass-1/pass-2 reruns when the goal is to test transferable reuse rather than repeated-memory effects.

Default ablation entry now also launches a ToolSandbox sub-run. Its ToolSandbox defaults are:

- `--refresh`
- `--include-augmented`
- `--num-runs 3`

If you want ablation runs to fail when official ToolSandbox data is missing, set:

```bash
TOOLSANDBOX_ABLATION_REQUIRE_OFFICIAL=1 bash scripts/run_ablation.sh
```
