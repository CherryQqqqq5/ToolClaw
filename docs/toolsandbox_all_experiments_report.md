# ToolSandbox Experiments: Consolidated Final Report

## 1. Scope

This report consolidates the final ToolSandbox-related experimental evidence currently usable for paper claims about ToolClaw after the `a2_planner` implementation fix.

Reporting rules:

1. Only experiments with final benchmark outputs are included in the main conclusion path.
2. Repeated debug runs, tiny pilots, and superseded provenance-ambiguous runs are excluded.
3. This report distinguishes clearly between:
   - the restored 88-sample **official frozen ToolSandbox benchmark**
   - the repo-bundled 14-sample **fallback/core slice** in `data/toolsandbox.formal.json`
4. Any experiment that still depends on the pre-fix `a2` definition is either superseded or explicitly excluded.

## 2. Datasets and provenance

The repo contains two ToolSandbox dataset paths with different roles. Their intended meanings are documented in [docs/toolsandbox_usage.md](/Users/cherry/.codex/worktrees/1bba/ToolClaw/docs/toolsandbox_usage.md:36).

### 2.1 Official frozen benchmark

- Path: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.official.json`
- Role in this report: **main benchmark dataset**
- Verified properties used in this report:
  - sample count: `88`
  - benchmark outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix`
  - result summary source in the final report: `reference_result_summary`
  - consistency check: `PASSED`

### 2.2 Bundled fallback/core slice

- Path: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.json`
- Role in this report: **mechanism-analysis slice**
- Verified properties:
  - sample count: `14`
  - ToolClaw-style task names such as `toolsandbox_env_backup_001`
  - fields such as `backup_tool_map`, `simulated_policy`, and `execution_scenario`
- Paper-safe interpretation:
  - use for internal ablation / mechanism analysis
  - do **not** use as the headline ToolSandbox benchmark

## 3. Included experiments

This report includes five final experiment groups:

1. ToolSandbox official frozen benchmark
2. ToolSandbox explicit bundled core-slice benchmark
3. Matched ToolSandbox ablation
4. ToolSandbox reuse split train/eval
5. Tau2 approval / recovery stress tests

## 4. System ladder after the `a2` fix

The intended system ladder is now correctly implemented in [scripts/run_eval.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_eval.py:68).

- `a0_baseline`: baseline execution
- `a1_recovery`: recovery-only
- `a2_planner`: `a1_recovery + planner`
- `a3_interaction`: `a2_planner + interaction`
- `a4_reuse`: `a3_interaction + reuse/compiler`

Important interpretation rule:

- from `a1` onward, each layer now adds one mechanism family to the previous layer
- this is a **design property**, not a guarantee of strictly monotonic success on every slice
- in the current final results:
  - `a2 = a1` on the official benchmark
  - `a2 > a1` on the bundled core slice
  - `a4 < a3` on the bundled core slice

Therefore the paper should claim **incremental mechanism addition**, not universal monotonic improvement.

## 5. Experiment A: ToolSandbox official frozen benchmark

### 5.1 Purpose

Measure end-to-end ToolClaw performance on the restored 88-sample ToolSandbox frozen benchmark and establish the main benchmark-facing ranking among:

- `a0_baseline`
- `a1_recovery`
- `a2_planner`
- `a3_interaction`
- `a4_reuse`

### 5.2 Entry

- Runner: [scripts/run_toolsandbox_bench.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_toolsandbox_bench.py)

### 5.3 Inputs and outputs

- Source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.official.json`
- Normalized taskset: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix/prepared/toolsandbox.normalized.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix`
- Report: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix/report.md`
- Scoreboard: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix/scoreboard.json`
- Per-system summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix/per_system_summary.json`
- Scored comparison: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix/comparison.scored.csv`

### 5.4 Process

1. Restore the correct 88-sample `toolsandbox.formal.official.json`.
2. Normalize the dataset.
3. Run all five systems for `3` repeats.
4. Score results with ToolClaw's ToolSandbox benchmark logic.
5. Aggregate by system, failtax, failure type, and category.
6. Validate with `scripts/check_benchmark_consistency.py`.

### 5.5 Final results

Aggregate:

| system | mean_success_rate | pass@k | consistency |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.659 | 0.659 | 1.000 |
| `a1_recovery` | 0.693 | 0.693 | 1.000 |
| `a2_planner` | 0.693 | 0.693 | 1.000 |
| `a3_interaction` | 1.000 | 1.000 | 1.000 |
| `a4_reuse` | 1.000 | 1.000 | 1.000 |

Failtax breakdown:

| system | ordering | selection | state |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.429 | 0.700 | 0.714 |
| `a1_recovery` | 0.429 | 0.750 | 0.714 |
| `a2_planner` | 0.429 | 0.750 | 0.714 |
| `a3_interaction` | 1.000 | 1.000 | 1.000 |
| `a4_reuse` | 1.000 | 1.000 | 1.000 |

High-signal categories:

| category | a0 | a1 | a2 | a3 | a4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `multiple_user_turn` | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| `insufficient_information` | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| `single_user_turn` | 0.951 | 1.000 | 1.000 | 1.000 | 1.000 |

Validation status:

- `scripts/check_benchmark_consistency.py`: `PASSED`
- `reference_summary_coverage = 1.000`
- dominant result summary source: `reference_result_summary`

### 5.6 Conclusion

This is the current headline ToolSandbox benchmark result.

Supported conclusions:

- interaction is the decisive capability jump
- planner on top of recovery does not hurt and matches recovery-only on the official benchmark
- both non-interaction recovery variants remain substantially below interaction
- reuse matches interaction but does not exceed it on this benchmark

Paper-safe claim:

- ToolClaw's interaction-enabled variants (`a3`, `a4`) solve the restored 88-sample ToolSandbox benchmark perfectly, while non-interaction variants remain in the `0.659` to `0.693` range.

## 6. Experiment B: ToolSandbox explicit bundled core-slice benchmark

### 6.1 Purpose

Evaluate the same systems on the explicit 14-sample bundled fallback/core slice so that the mechanism-analysis set is provenance-clean and no longer confused with the official benchmark.

### 6.2 Entry

- Runner: [scripts/run_toolsandbox_bench.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_toolsandbox_bench.py)

### 6.3 Inputs and outputs

- Source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.json`
- Normalized taskset: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/prepared/toolsandbox.normalized.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix`
- Report: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/report.md`
- Scoreboard: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/scoreboard.json`
- Per-system summary: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix/per_system_summary.json`

### 6.4 Process

1. Load the bundled 14-sample core slice.
2. Normalize the dataset.
3. Run all five systems for `3` repeats.
4. Score and aggregate by system, failtax, category, and repair loop behavior.
5. Run consistency checking.

### 6.5 Final results

Aggregate:

| system | mean_success_rate | pass@k | consistency |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.286 | 0.286 | 1.000 |
| `a1_recovery` | 0.214 | 0.214 | 1.000 |
| `a2_planner` | 0.429 | 0.429 | 1.000 |
| `a3_interaction` | 0.929 | 0.929 | 1.000 |
| `a4_reuse` | 0.857 | 0.857 | 1.000 |

Failtax breakdown:

| system | ordering | selection | state |
| --- | ---: | ---: | ---: |
| `a0_baseline` | 0.333 | 1.000 | 0.000 |
| `a1_recovery` | 0.111 | 0.000 | 0.500 |
| `a2_planner` | 0.333 | 1.000 | 0.500 |
| `a3_interaction` | 0.889 | 1.000 | 1.000 |
| `a4_reuse` | 0.778 | 1.000 | 1.000 |

Repair-loop highlights:

- `a3_interaction`
  - `repair_rows = 18`
  - `repair_scored_success = 0.429`
- `a4_reuse`
  - `repair_rows = 0`
  - `reused_artifact_rate = 1.000`

Validation status:

- The benchmark outputs are complete.
- `scripts/check_benchmark_consistency.py` reports a category-slice mismatch for `planner_sensitive`.
- The mismatch is in category summary bookkeeping, not in the main scoreboard totals.

### 6.6 Conclusion

This slice should be used as mechanism evidence, not as the headline ToolSandbox benchmark.

Supported conclusions:

- interaction is still the dominant mechanism
- adding planner on top of recovery helps on this slice (`a2 > a1`)
- on this slice, `a3_interaction` is slightly stronger than `a4_reuse`
- repair-enabled interaction is more important than reuse on this slice

Paper-safe claim:

- The bundled core slice strengthens the mechanism interpretation that planner-on-top-of-recovery helps on failure-heavy tasks, but interaction-driven recovery remains the dominant gain and reuse is not universally beneficial.

## 7. Experiment C: Matched ToolSandbox ablation

### 7.1 Purpose

Isolate which mechanism matters on the ToolSandbox mechanism slice by comparing:

- `tc_full`
- `tc_no_repair`
- `tc_no_fallback`
- `tc_no_reuse`
- `tc_planner_only`

### 7.2 Entry

- Runner: [scripts/run_toolsandbox_matched_ablation.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_toolsandbox_matched_ablation.py)
- Delegated benchmark runner: [scripts/run_toolsandbox_bench.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_toolsandbox_bench.py)

### 7.3 Inputs and outputs

- Source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/remote/toolsandbox_matched_20260406_094138`
- Report: [outputs/remote/toolsandbox_matched_20260406_094138/report.md](/Users/cherry/.codex/worktrees/1bba/ToolClaw/outputs/remote/toolsandbox_matched_20260406_094138/report.md)
- Manifest: [outputs/remote/toolsandbox_matched_20260406_094138/experiment_manifest.json](/Users/cherry/.codex/worktrees/1bba/ToolClaw/outputs/remote/toolsandbox_matched_20260406_094138/experiment_manifest.json)

### 7.4 Final results

| system | mean_success_rate | pass@k | consistency |
| --- | ---: | ---: | ---: |
| `tc_full` | 1.000 | 1.000 | 1.000 |
| `tc_no_repair` | 0.700 | 0.700 | 1.000 |
| `tc_no_fallback` | 1.000 | 1.000 | 1.000 |
| `tc_no_reuse` | 1.000 | 1.000 | 1.000 |
| `tc_planner_only` | 0.700 | 0.700 | 1.000 |

Key category signals:

- `tc_no_repair`
  - `insufficient_information = 0.000`
  - `multiple_user_turn = 0.333`
  - `single_user_turn = 0.500`
- `tc_planner_only`
  - `insufficient_information = 0.500`
  - `multiple_user_turn = 0.000`
  - `state_dependency = 0.750`
- `tc_no_fallback = 1.000`
- `tc_no_reuse = 1.000`

### 7.5 Conclusion

This remains the strongest mechanism-isolation result on the ToolSandbox core slice.

Supported conclusions:

- repair matters
- planner-only is insufficient
- fallback does not matter on this slice
- reuse does not matter on this slice

## 8. Experiment D: ToolSandbox reuse split train/eval

### 8.1 Purpose

Test reuse under an explicit train/eval split instead of only within one mixed benchmark run.

### 8.2 Entry

- Runner: [scripts/run_reuse_split_experiment.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_reuse_split_experiment.py)

### 8.3 Inputs and outputs

Train:

- Source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.train.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/exp/toolsandbox_split_train`
- Report: [outputs/exp/toolsandbox_split_train/report.md](/Users/cherry/.codex/worktrees/1bba/ToolClaw/outputs/exp/toolsandbox_split_train/report.md)

Eval:

- Source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.eval.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/exp/toolsandbox_split_eval`
- Report: [outputs/exp/toolsandbox_split_eval/report.md](/Users/cherry/.codex/worktrees/1bba/ToolClaw/outputs/exp/toolsandbox_split_eval/report.md)

### 8.4 Final results

Train:

| system | mean_success_rate | pass@k | consistency |
| --- | ---: | ---: | ---: |
| `a4_reuse` | 1.000 | 1.000 | 1.000 |

Eval:

| system | mean_success_rate | pass@k | consistency |
| --- | ---: | ---: | ---: |
| `a3_interaction` | 1.000 | 1.000 | 1.000 |
| `a4_reuse` | 1.000 | 1.000 | 1.000 |

### 8.5 Conclusion

This split does not show a held-out success-rate advantage for reuse.

Supported conclusion:

- reuse does not hurt held-out evaluation, but the eval split is saturated and therefore cannot support a strong positive reuse claim.

## 9. Experiment E: Tau2 approval / recovery stress tests

### 9.1 Purpose

Use Tau2 to separate failure modes that ToolSandbox alone cannot isolate cleanly:

- approval accounting
- approval semantics
- pure approval recovery
- compound approval + repair recovery

### 9.2 Detailed report

- [docs/tau2_claim_experiments_report.md](/Users/cherry/.codex/worktrees/1bba/ToolClaw/docs/tau2_claim_experiments_report.md)

### 9.3 Inputs and outputs

#### E1. Full Tau2 after `a2` fix

- Source: `/cephfs/qiuyn/ToolClaw/data/tau2_bench.formal.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter`

#### E2. Approval-only Tau2 slice

- Source: `/cephfs/qiuyn/ToolClaw/data/tau2_bench.approval_only.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter`

#### E3. Isolated repeated `binding_plus_approval`

- Source: `/cephfs/qiuyn/ToolClaw/data/tau2_bench.binding_plus_approval_only.json`
- Outdir: `/cephfs/qiuyn/ToolClaw/outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter`

### 9.4 Final results

E1:

| system | mean_success_rate |
| --- | ---: |
| `a0_baseline` | 0.0000 |
| `a1_recovery` | 0.5000 |
| `a2_planner` | 0.5000 |
| `a3_interaction` | 0.7500 |
| `a4_reuse` | 0.8333 |

E2:

| system | mean_success_rate |
| --- | ---: |
| `a0_baseline` | 0.0000 |
| `a3_interaction` | 0.6667 |
| `a4_reuse` | 1.0000 |

E2 key sample-level results:

- `tau2_approval_gate_001`
  - `a3=1.0`
  - `a4=1.0`
- `tau2_dual_control_001`
  - `a3=1.0`
  - `a4=1.0`
- `tau2_binding_plus_approval_001`
  - `a3=0.0`
  - `a4=1.0`

E3:

| system | mean_success_rate | consistency |
| --- | ---: | ---: |
| `a3_interaction` | 0.0000 | 1.0000 |
| `a4_reuse` | 0.0000 | 1.0000 |

For both systems in E3, all 10 runs had:

- `stop_reason = max_user_turns_exceeded`
- `approval_following = 1.0`
- `repair_triggered = 2`
- `reused_artifact = False`

### 9.5 Conclusion

Supported conclusions:

- the approval semantic fix was necessary and effective
- `a3` and `a4` both solve pure approval-gated tasks
- after the `a2` fix, `a2` matches `a1` on the full Tau2 benchmark
- `a1` and `a2` still fail valid approval request/response behavior under Tau2 scoring

Not supported:

- a stable claim that `a4` solves compound approval + repair from cold start

## 10. Overall conclusions

### 10.1 Strongly supported

1. **Interaction is the main ToolClaw performance driver.**
   - Official ToolSandbox: `a3=1.0`, `a4=1.0`, `a1=a2=0.693`, `a0=0.659`

2. **The official ToolSandbox benchmark now provides a provenance-clean headline result.**
   - 88 samples
   - 3 runs
   - consistency check passed

3. **The bundled core slice provides mechanism evidence.**
   - `a3=0.929`, `a4=0.857`, `a2=0.429`, `a1=0.214`
   - this slice sharpens recovery differences more than the official benchmark
   - it also shows that planner-on-top-of-recovery helps, but does not dominate interaction

4. **Repair matters on the mechanism slice.**
   - matched ablation: `tc_full=1.0`, `tc_no_repair=0.7`

5. **Fallback and reuse do not improve success on the current ToolSandbox mechanism slice.**
   - `tc_no_fallback=1.0`
   - `tc_no_reuse=1.0`

6. **The reuse split does not currently show held-out success gains.**
   - `a3=1.0`, `a4=1.0` on eval

7. **Tau2 supports approval-semantic claims but not compound cold-start approval+repair claims.**

8. **The `a0-a4` ladder is now implementation-correct from `a1` onward, but not numerically monotonic on every slice.**
   - `a2 = a1 + planner`
   - `a3 = a2 + interaction`
   - `a4 = a3 + reuse/compiler`
   - `a4` is below `a3` on the bundled core slice, so the paper should claim incremental mechanism addition, not guaranteed monotonic improvement on every benchmark slice

### 10.2 Not supported

1. A strong claim that reuse improves success on the official ToolSandbox benchmark
2. A strong claim that reuse improves success on the explicit 14-sample core slice
3. A strong claim that reuse improves held-out ToolSandbox success under the current split
4. A strong claim that reuse robustly solves compound Tau2 approval + repair from cold start
5. A strong claim that every layer in `a0-a4` strictly outperforms the previous layer on every benchmark slice

## 11. Excluded experiments

The following are intentionally excluded from the main evidence:

### 11.1 Tiny or non-representative ToolSandbox runs

- `outputs/toolsandbox_full_official`
  - only 3 samples, saturated
- `outputs/toolsandbox_bench_official_formal`
  - only 1 sample, not claim-bearing

### 11.2 Superseded provenance-ambiguous or control-only ToolSandbox runs

- `outputs/toolsandbox_core_r3`
  - superseded by the explicit-source rerun and the restored official benchmark
- `outputs/remote/toolsandbox_core_r3_control`
- `outputs/remote/toolsandbox_core_r3_persist_pass1`
- `outputs/remote/toolsandbox_core_r3_persist_pass2`

### 11.3 Derived `bench_slices` outputs

- `data/bench_slices/*`
- outputs generated only from those derived slices

Reason for exclusion:

- these slices are created by [scripts/derive_toolsandbox_formal_slices.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/derive_toolsandbox_formal_slices.py)
- they are structurally checked by [scripts/verify_toolsandbox_slices.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/verify_toolsandbox_slices.py)
- they are not needed in the final paper path because:
  - [scripts/run_toolsandbox_bench.py](/Users/cherry/.codex/worktrees/1bba/ToolClaw/scripts/run_toolsandbox_bench.py) already emits focused category summaries for the high-value paper slices
  - the explicit bundled core slice is a cleaner mechanism-analysis set
  - matched ablation isolates repair/fallback/reuse effects more directly than many tiny derived slices
  - adding both would increase provenance and multiplicity complexity without changing the main conclusions

### 11.4 Saturated or stale transfer runs

- `outputs/tau_bench_full_a0a4`

Reason for exclusion:

- it was not rerun after the `a2` implementation fix
- it is saturated and therefore not claim-bearing
- if the paper wants to show a Tau-bench `a0-a4` table, it should be rerun; otherwise it is safer to omit

### 11.5 Superseded Tau2 debug runs

- `exp05_tau2_approvalfix_r3_openrouter`
- `exp05_tau2_approvalfix_focus4_r3_openrouter`
- `exp06_tau2_step_local_approval_focus4_r3_openrouter`
- `exp06_tau2_step_local_approval_r3_openrouter`
  - superseded by `exp09_tau2_a2fix_r3_openrouter` for any claim involving `a2`

## 12. Recommended paper structure

The safest current paper-facing structure is:

1. Use the restored **ToolSandbox official frozen benchmark** as the headline benchmark result.
2. Use the explicit `toolsandbox.formal.json` rerun plus the matched ablation as the mechanism section.
3. Use the split experiment only as a sanity check, not as positive reuse evidence.
4. Omit Tau-bench unless it is rerun post-`a2` fix.
5. Use Tau2 for approval-specific claims:
   - positive on pure approval recovery
   - negative / unresolved on compound cold-start approval+repair
