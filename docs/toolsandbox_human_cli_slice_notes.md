# ToolSandbox 真人 CLI 子集说明

本文件解释 `data/toolsandbox.human_cli.slice.json` 的来源与抽样逻辑，确保实验口径可追溯、可复现。

## 抽样来源

本次 12 样本子集来自两个已有数据文件：

- 主来源：`data/toolsandbox.formal.json`
- 补充来源：`data/toolsandbox.formal.eval.json`

具体地：

- 11 个样本来自 `toolsandbox.formal.json`
- 1 个样本（`toolsandbox_multi_turn_approval_002`）来自 `toolsandbox.formal.eval.json`

## 为什么这样抽

目标是构建一个 `10–20` 规模的真人交互首批验证集，优先覆盖最能体现 ToolClaw 交互价值的场景，而不是追求大规模跑分。

优先三类：

1. `insufficient_information`
2. `state_dependency / blocked state`
3. `approval / ambiguity / missing argument`

这三类最适合验证：

- clarification 是否自然
- interaction + repair 是否降低卡死
- 真人回复与 simulator 回复是否存在系统性差异

## 本批 12 样本清单

### A. Insufficient-information / missing-argument（6）

- `toolsandbox_env_backup_001`
- `toolsandbox_binding_repair_001`
- `toolsandbox_reuse_family_001__pass1`
- `toolsandbox_reuse_family_001__pass2`
- `toolsandbox_reuse_transfer_001__pass1`
- `toolsandbox_reuse_transfer_001__pass2`

### B. State-dependency / blocked-state（4）

- `toolsandbox_state_failure_resume_001`
- `toolsandbox_state_failure_target_001`
- `toolsandbox_planner_sensitive_001`
- `toolsandbox_planner_sensitive_004`

### C. Approval / multi-turn（2）

- `toolsandbox_approval_interaction_001`
- `toolsandbox_multi_turn_approval_002`

## 与实验设计文档的对应关系

该子集用于执行 `docs/toolsandbox_human_cli_experiment.md` 中定义的小规模真人 CLI 实验协议，默认用于以下对照：

- `a0_baseline`
- `tc_full`
- （可选）`tc_no_reuse` 或 `tc_recovery_only`

## 运行方式

真人 CLI：

```bash
python3 scripts/run_toolsandbox_cli.py \
  --source data/toolsandbox.human_cli.slice.json \
  --outdir outputs/toolsandbox_human_cli \
  --mode planner \
  --systems a0_baseline,tc_full,tc_no_reuse \
  --num-runs 1 \
  --cli-prompt-prefix "human-study"
```

simulator 对照：

```bash
python3 scripts/run_toolsandbox_bench.py \
  --source data/toolsandbox.human_cli.slice.json \
  --outdir outputs/toolsandbox_simulator_matched \
  --mode planner \
  --systems a0_baseline,tc_full,tc_no_reuse \
  --num-runs 1
```

## 变更规则（防漂移）

若后续替换样本或调整样本数，必须：

1. 新建子集文件（不要覆盖旧文件）
2. 在说明文档记录新增/删除样本与原因
3. 以新批次名输出结果，避免与旧结果混报
