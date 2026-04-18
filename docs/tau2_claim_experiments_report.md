# Tau2 Claim-Oriented Experiment Report

## 1. Report scope

This report records only the final, usable, claim-oriented Tau2 experiments after the approval fixes and the `a2_planner` definition fix.

Included experiments:

- `exp09_tau2_a2fix_r3_openrouter`
- `exp07_tau2_approval_only_r3_openrouter`
- `exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter`

Excluded from this report:

- `exp05_tau2_approvalfix_r3_openrouter`
  - debug-stage run used to separate accounting bugs from execution bugs
- `exp06_tau2_step_local_approval_focus4_r3_openrouter`
  - transitional slice used before the full run
- `exp06_tau2_step_local_approval_r3_openrouter`
  - predates the `a2` system-definition fix and should not be used for final claims involving `a2_planner`

## 2. Experiment goal

The overall goal was to determine which Tau2 claims are actually supported after fixing:

1. approval accounting
2. approval execution semantics
3. the `a2_planner` system definition

The concrete claim questions were:

1. Can interaction-enabled systems solve approval-gated Tau2 tasks after the semantic fix?
2. After the `a2` fix, does `a2_planner` behave like `a1_recovery + planner` on the full benchmark?
3. Is the apparent `a4_reuse` advantage on `tau2_binding_plus_approval_001` stable, or only a reuse-state artifact?

## 3. Relevant code changes

These experiments were run after the following changes:

- [src/toolclaw/benchmarks/adapters.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/src/toolclaw/benchmarks/adapters.py)
  - Tau2 approval metadata was changed to failure-step-local (`approval_scope=failure_step`, `approval_target_step=failure_step`)
- [scripts/run_eval.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_eval.py)
  - Tau2 approval is applied only to the target failure step
  - `requires_user_confirmation` is preserved in `workflow_overrides`
  - `a2_planner` now correctly inherits `a1_recovery`'s repair/fallback behavior
- [scripts/check_benchmark_consistency.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/check_benchmark_consistency.py)
  - consistency checking uses benchmark-scored success when available

Local regression coverage:

- [tests/test_tau2_adapter.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/tests/test_tau2_adapter.py)
- [tests/test_eval_script.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/tests/test_eval_script.py)
- [tests/test_check_benchmark_consistency.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/tests/test_check_benchmark_consistency.py)

## 4. Common experiment entry

All server-side runs used:

- `scripts/run_tau2_bench.py`

Common runtime setup:

```bash
cd /cephfs/qiuyn/ToolClaw
export PYTHONPATH=/cephfs/qiuyn/ToolClaw/src
export TOOLCLAW_BENCHMARK_PROXY_PROVIDER=openrouter
export TOOLCLAW_BENCHMARK_PROXY_FORCE=1
export OPENAI_API_KEY='YOUR_OPENROUTER_KEY'
export TOOLSANDBOX_OPENROUTER_MODEL='x-ai/grok-3'
```

Consistency was checked with:

- `scripts/check_benchmark_consistency.py`

## 5. Experiment A: Full Tau2 after approval + `a2` fix

### 5.1 Purpose

Measure the final full-benchmark Tau2 behavior after:

1. step-local approval semantics were fixed
2. `a2_planner` was corrected to mean `a1_recovery + planner`

### 5.2 Entry

```bash
/cephfs/qiuyn/miniconda3/bin/python3.13 scripts/run_tau2_bench.py \
  --source /cephfs/qiuyn/ToolClaw/data/tau2_bench.formal.json \
  --outdir /cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter \
  --mode planner \
  --systems a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse \
  --num-runs 3
```

### 5.3 Input files

- Source: `/cephfs/qiuyn/ToolClaw/data/tau2_bench.formal.json`

### 5.4 Output files

- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter`
- Scoreboard: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter/scoreboard.json`
- Per-system summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter/per_system_summary.json`
- Normalized taskset: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter/prepared/tau2_bench.normalized.json`

### 5.5 Final results

| System | Mean success rate | Approval following | Interaction efficiency | Safe abort rate | State repair success rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `a0_baseline` | 0.0000 | 0.8333 | 0.0000 | 0.0000 | 0.0000 |
| `a1_recovery` | 0.5000 | 0.7083 | 0.7500 | 0.0000 | 0.3333 |
| `a2_planner` | 0.5000 | 0.7083 | 0.7500 | 0.0000 | 0.3333 |
| `a3_interaction` | 0.7500 | 1.0000 | 0.9167 | 0.0833 | 0.3333 |
| `a4_reuse` | 0.8333 | 1.0000 | 0.9167 | 0.0833 | 0.3333 |

Per-failtax summary:

| System | recovery | selection | ordering | state |
| --- | ---: | ---: | ---: | ---: |
| `a0_baseline` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `a1_recovery` | 0.2000 | 0.5000 | 0.0000 | 1.0000 |
| `a2_planner` | 0.2000 | 0.5000 | 0.0000 | 1.0000 |
| `a3_interaction` | 0.8000 | 0.0000 | 1.0000 | 1.0000 |
| `a4_reuse` | 0.8000 | 0.5000 | 1.0000 | 1.0000 |

Key sample-level results:

- `tau2_approval_gate_001`
  - `a1=0.0`, `a2=0.0`, `a3=1.0`, `a4=1.0`
- `tau2_dual_control_001`
  - `a1=0.0`, `a2=0.0`, `a3=1.0`, `a4=1.0`
- `tau2_binding_plus_approval_001`
  - `a1=0.0`, `a2=0.0`, `a3=0.0`, `a4=1.0`
- `tau2_policy_abort_001`
  - `a1=0.0`, `a2=0.0`, `a3=1.0`, `a4=1.0`

Validation:

- `scripts/check_benchmark_consistency.py`: `PASSED`

### 5.6 Conclusion

Supported by this run:

- `a2_planner` now matches `a1_recovery` on the full Tau2 benchmark
- `a3_interaction` and `a4_reuse` are both clearly stronger than `a1/a2`
- `a3` and `a4` both solve pure approval-gated tasks in the full benchmark
- `a4` is still the only system that solves `tau2_binding_plus_approval_001` in the mixed full-benchmark setting

## 6. Experiment B: Approval-only slice

### 6.1 Purpose

Isolate approval-related behavior from the rest of Tau2 and determine whether the remaining gains are truly about approval handling.

### 6.2 Slice construction

The source slice contained exactly three tasks:

- `tau2_approval_gate_001`
- `tau2_binding_plus_approval_001`
- `tau2_dual_control_001`

Generated file:

- `/cephfs/qiuyn/ToolClaw/data/tau2_bench.approval_only.json`

### 6.3 Entry

```bash
/cephfs/qiuyn/miniconda3/bin/python3.13 scripts/run_tau2_bench.py \
  --source /cephfs/qiuyn/ToolClaw/data/tau2_bench.approval_only.json \
  --outdir /cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter \
  --mode planner \
  --systems a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse \
  --num-runs 3
```

Recorded result:

- `CONSISTENCY CHECK: PASSED`

### 6.4 Output files

- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter`
- Scoreboard: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter/scoreboard.json`
- Per-system summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter/per_system_summary.json`
- Comparison CSV: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter/comparison.csv`

### 6.5 Final results

This slice is retained only for the `a3` vs `a4` claim, because it predates the `a2` fix and the paper does not need `a1/a2` approval-slice numbers.

Per-system summary for the retained claim:

| System | Mean success rate | Approval following | Interaction efficiency |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.0000 | 0.5000 | 0.0000 |
| `a3_interaction` | 0.6667 | 1.0000 | 1.0000 |
| `a4_reuse` | 1.0000 | 1.0000 | 1.0000 |

Per-sample success rates:

| Sample | `a3_interaction` | `a4_reuse` | Notes |
| --- | ---: | ---: | --- |
| `tau2_approval_gate_001` | 1.0 | 1.0 | both solved |
| `tau2_dual_control_001` | 1.0 | 1.0 | both solved |
| `tau2_binding_plus_approval_001` | 0.0 | 1.0 | only `a4` solved in this mixed slice |

### 6.6 Conclusion

This experiment established two things:

1. Pure approval tasks are solved stably by both `a3_interaction` and `a4_reuse`.
2. The only remaining difference inside this slice is concentrated in `tau2_binding_plus_approval_001`.

However, the `a4` success on `tau2_binding_plus_approval_001` still required an isolation test, because these successful runs also had `reused_artifact = True`.

## 7. Experiment C: Isolated stress test of `tau2_binding_plus_approval_001`

### 7.1 Purpose

Test whether the apparent `a4_reuse` advantage on `tau2_binding_plus_approval_001` is a stable per-sample capability, or whether it depends on artifact state induced by surrounding tasks.

### 7.2 Slice construction

The source slice contained exactly one task:

- `tau2_binding_plus_approval_001`

Generated file:

- `/cephfs/qiuyn/ToolClaw/data/tau2_bench.binding_plus_approval_only.json`

### 7.3 Entry

```bash
/cephfs/qiuyn/miniconda3/bin/python3.13 scripts/run_tau2_bench.py \
  --source /cephfs/qiuyn/ToolClaw/data/tau2_bench.binding_plus_approval_only.json \
  --outdir /cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter \
  --mode planner \
  --systems a3_interaction,a4_reuse \
  --num-runs 10
```

Recorded result:

- `CONSISTENCY CHECK: PASSED`

### 7.4 Output files

- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter`
- Scoreboard: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter/scoreboard.json`
- Comparison CSV: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter/comparison.csv`
- Per-system summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter/per_system_summary.json`

### 7.5 Final results

| System | Mean success rate | Pass@k | Consistency |
| --- | ---: | ---: | ---: |
| `a3_interaction` | 0.0000 | 0.0000 | 1.0000 |
| `a4_reuse` | 0.0000 | 0.0000 | 1.0000 |

Per-sample result for both systems:

- `tau2_binding_plus_approval_001`
  - `success_rate = 0.0`
  - `stop_reason = max_user_turns_exceeded` in all 10 runs
  - `approval_following = 1.0`
  - `interaction_efficiency = 1.0`
  - `repair_triggered = 2`
  - `reused_artifact = False`

### 7.6 Conclusion

This experiment overturns the earlier tentative interpretation that `a4_reuse` robustly solves `tau2_binding_plus_approval_001`.

What `exp08` shows:

- in isolated repeated evaluation, both `a3_interaction` and `a4_reuse` fail `tau2_binding_plus_approval_001` with the same failure mode
- the earlier `a4_reuse` success in mixed-task runs is therefore not stable evidence of an intrinsic per-sample capability
- the most defensible interpretation is that the earlier `a4_reuse` success depended on reuse state induced by the surrounding multi-task slice

## 8. Final claim status

### 8.1 Claims currently supported

1. The step-local approval fix is real and necessary.
   - Approval handling must be attached to the Tau2 failure step rather than applied as a task-global gate.

2. `a3_interaction` and `a4_reuse` both solve pure approval-gated Tau2 tasks after the fix.
   - Supported by `tau2_approval_gate_001` and `tau2_dual_control_001`.

3. After the system-definition fix, `a2_planner` behaves like `a1_recovery + planner` on the full Tau2 benchmark.
   - In `exp09`, `a1_recovery` and `a2_planner` tie at `0.5000`.

4. `a1_recovery` and `a2_planner` still do not implement a valid approval loop under Tau2 scoring.
   - On approval-gated tasks such as `tau2_approval_gate_001` and `tau2_dual_control_001`, they still show raw success with `approval_following = 0.0`.

### 8.2 Claims not currently supported

1. "`a4_reuse` robustly solves `tau2_binding_plus_approval_001`."
   - `exp08` directly falsifies this as a stable claim.

2. "`reuse` currently provides a stable advantage on compound approval + binding recovery."
   - There is a mixed-slice positive result in `exp07`, but it does not survive isolated repetition.

### 8.3 Most defensible paper-facing summary

The strongest paper-safe interpretation of the current Tau2 evidence is:

- the approval bug was first separated into an accounting problem and then corrected at the execution-semantics level
- after the semantic fix, interaction-enabled systems (`a3`, `a4`) can reliably solve pure approval-gated Tau2 tasks
- after the `a2` system-definition fix, `a2` now matches `a1` on the full benchmark, so the previous `a2` deficit was an implementation error rather than a meaningful scientific result
- however, the compound task `tau2_binding_plus_approval_001` remains unsolved under isolated repeated evaluation, including for `a4_reuse`

Therefore the current Tau2 evidence supports a claim about approval semantics and pure approval recovery, but it does not support a strong claim about robust compound approval + repair recovery.
