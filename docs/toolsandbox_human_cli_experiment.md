# ToolSandbox 真人 CLI 交互实验设计（Small-Scale）

本方案用于补充 simulator 证据，验证 ToolClaw 在**真实用户交互**场景中的有效性与可用性。  
目标不是扩大 benchmark 数量，而是用小规模高价值样本回答一个明确问题：

> 在固定模型与固定任务下，真实用户参与时，ToolClaw 的交互式纠偏是否显著优于 plain/no-interaction scaffold？

---

## 1. 实验目标与边界

### 1.1 目标

- 验证 ToolClaw 在真人交互下的任务完成能力与交互质量。
- 对比 simulator 路径与真人路径在关键交互指标上的差异。
- 为论文提供“用户友好性”证据，而不仅是自动评分分数。

### 1.2 边界

- 这是小型协议：`10–20` 场景，不直接上 `30+`。
- 固定 base model、固定预算、固定任务集。
- 仅改变 scaffold（和交互对象），不改变模型本身。

---

## 2. 场景选择（首批 12，建议）

优先从已验证的 safe subset 中抽样，覆盖三类切片：

1. **Insufficient information**（4–6 个）  
   - 重点看 clarification 是否自然、是否减少弯路。
2. **State dependency / blocked state**（4–6 个）  
   - 重点看 interaction + repair 是否真正降低卡死率。
3. **Approval / ambiguity / missing argument**（4–6 个）  
   - 重点看真人回复相对 simulator 的差异。

建议首批规模：`12`（每类 `4`）；若首批稳定，再扩展到 `16` 或 `20`。

---

## 3. 对照组设计

最小可发表版本（2 组）：

- `a0_baseline`（plain scaffold）
- `tc_full`（ToolClaw full）

推荐增强版本（3 组）：

- `a0_baseline`
- `tc_full`
- `tc_no_reuse` 或 `tc_recovery_only`（二选一）

说明：三组设计可更直接定位“提升来自哪一层能力”，优于仅二组差分。

---

## 4. 指标体系（必须同时记录）

## 4.1 客观指标

- `task_success`（任务是否成功）
- `time_to_completion_sec`
- `user_extra_turns`（超出理想轮次的用户轮数）
- `clarification_turns`
- `repeat_question_count`（重复问同一信息）
- `repair_actions`
- `tool_calls`

## 4.2 主观指标（用户评分，5 分量表）

- `naturalness_score`（交互自然度）
- `burden_score`（负担感，分数越高负担越低）
- `satisfaction_score`
- `confusion_flag`（是否出现明显困惑/被打断，0/1）

建议每个任务后立即打分，避免回忆偏差。

---

## 5. 实验协议

### 5.1 固定配置

- 固定 base model（含版本）
- 固定 decoding（temperature/top_p）
- 固定预算（max_steps / token / max_tool_calls）
- 固定任务集（同一 `sample_id` 列表）

### 5.2 运行顺序

为避免学习效应和疲劳效应，采用**拉丁方或随机平衡顺序**：

- 参与者 A: `a0 -> tc_full -> tc_no_reuse`
- 参与者 B: `tc_full -> tc_no_reuse -> a0`
- 参与者 C: `tc_no_reuse -> a0 -> tc_full`

每名参与者执行同一任务集，但系统顺序不同。

### 5.3 样本量建议

- 参与者：`5–8` 人（内部用户即可）
- 每人任务：`12` 个
- 总交互样本：`60–96` 条任务轨迹

该规模足以支持初版统计显著性检验与定性分析。

---

## 6. 执行命令（当前仓库可直接用）

### 6.1 先准备真人实验任务子集

建议先固化一个子集文件，例如：

- `data/toolsandbox.human_cli.slice.json`

其中仅保留本实验选定的 `10–20` 个样本。

### 6.2 真人 CLI 入口（新增入口）

```bash
python3 scripts/run_toolsandbox_cli.py \
  --source data/toolsandbox.human_cli.slice.json \
  --outdir outputs/toolsandbox_human_cli \
  --mode planner \
  --systems a0_baseline,tc_full,tc_no_reuse \
  --num-runs 1 \
  --cli-prompt-prefix "human-study"
```

说明：

- `run_toolsandbox_cli.py` 默认将交互对象设为真实用户 CLI。
- simulator 通道仍保留，可继续用 `run_toolsandbox_bench.py` 默认模式。

### 6.3 simulator 对照（同任务集）

```bash
python3 scripts/run_toolsandbox_bench.py \
  --source data/toolsandbox.human_cli.slice.json \
  --outdir outputs/toolsandbox_simulator_matched \
  --mode planner \
  --systems a0_baseline,tc_full,tc_no_reuse \
  --num-runs 1
```

---

## 7. 数据记录模板（建议 CSV）

建议新增人工标注表（例如 `outputs/toolsandbox_human_cli/human_ratings.csv`），字段：

- `participant_id`
- `task_id`
- `system`
- `success`
- `time_to_completion_sec`
- `clarification_turns`
- `user_extra_turns`
- `repeat_question_count`
- `confusion_flag`
- `naturalness_score`
- `burden_score`
- `satisfaction_score`
- `notes`

---

## 8. 分析与统计

### 8.1 主比较

- `tc_full` vs `a0_baseline`（核心）
- `tc_full` vs `tc_no_reuse`/`tc_recovery_only`（层贡献）

### 8.2 统计方法（小样本稳健）

- 成功率：McNemar 或配对 bootstrap
- 连续指标（时间/轮次）：Wilcoxon signed-rank
- 主观分：Wilcoxon signed-rank + 效应量（Cliff's delta）

报告格式建议：

- 均值/中位数 + 95% CI
- p 值 + 效应量
- 三类场景分 slice 结果

---

## 9. 通过门槛（建议）

满足以下条件可进入论文主文：

1. `tc_full` 在总体 `task_success` 上优于 `a0_baseline`
2. `tc_full` 在至少两类关键切片上显著降低 `time_to_completion` 或 `user_extra_turns`
3. `naturalness` 与 `satisfaction` 不低于 baseline，且 `burden` 不升高
4. 无大规模“重复提问/用户困惑”退化现象

否则作为附录或负例分析，不做主结论。

---

## 10. 风险控制

- 禁止中途替换任务集（若替换，必须新批次）
- 禁止只保留“好看样本”
- 每条轨迹保留 trace 与人工评分原始记录
- 明确标注：真人 CLI 研究是 ToolClaw proxy evaluation 的可用性补充证据，不替代 official ToolSandbox full execution
