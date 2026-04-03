# τ-bench 在 ToolClaw 中的接入说明

本文档基于当前仓库实现，说明你在跑 τ-bench 前需要准备什么、数据从哪里接、以及如何执行。

## 1) 你需要补充哪些数据

当前代码不会自动下载 τ-bench 数据；`scripts/run_tau_bench.py` 要求你通过 `--source` 传入一个本地 JSON/JSONL 文件。可接受格式是：

- JSON 数组（`[ {...}, {...} ]`）
- JSON 对象且包含 `samples` 列表（`{ "samples": [ ... ] }`）
- JSONL（每行一个样本）

每条样本最少建议包含：

- `sample_id`（可选，但强烈建议；否则会自动生成）
- `scenario`（可选，默认 `success`）
- `query` / `user_goal` / `instruction` / `prompt`（四选一，至少提供一个）

另外建议补充（用于更真实评测）：

- `target_path`：结果文件输出路径
- `constraints`：约束信息
  - `requires_user_approval`
  - `forbidden_actions`
  - `budget_limit`
  - `time_limit`
  - `risk_level` (`low|medium|high`)
- `simulated_policy`：交互/恢复相关策略（如 cooperative 模式）
- `candidate_tools`：候选工具列表
- `backup_tool_map`：主工具失败时的备选映射
- `metadata`：额外标注（例如 `requires_approval`）

## 2) τ-bench 数据从哪来

就当前仓库而言：

- **仓库内没有内置 τ-bench 正式数据集**。
- 代码只负责**读取你给的 source 文件**并做标准化转换。

因此你需要自行准备或导出 τ-bench 样本，再保存成本地 JSON/JSONL，传给 `--source`。

## 3) 你应该如何利用 τ-bench（在这个项目里）

推荐流程：

1. 准备原始样本（JSON/JSONL）。
2. 先跑 smoke：
   - `scripts/run_tau_bench_remote.sh <source> <outdir> planner baseline,toolclaw_lite smoke 1`
3. 再跑 full + 多次重复：
   - `python3 scripts/run_tau_bench.py --source <source> --outdir <outdir> --mode planner --systems baseline,toolclaw_lite --num-runs 5`
4. 重点看输出：
   - `scoreboard.json`（核心汇总）
   - `per_system_summary.json/.md`（系统级指标）
   - `comparison.csv`、`report.md`（run_eval 的基础对比）

## 4) 结果怎么解读

当前脚本会汇总以下维度：

- `mean_success_rate`：平均成功率
- `pass_at_k`：多次运行下是否至少成功一次
- `consistency`：同一样本多次运行结果一致性
- `rule_following`：审批/禁用动作等规则遵循
- `interaction_quality`：交互行为质量
- `tool_efficiency`：工具调用效率（调用越多可能越低）
- `repair_overhead`：恢复开销

## 5) 最小样例

```json
[
  {
    "sample_id": "tau_demo_001",
    "scenario": "success",
    "query": "Summarize target document and write report",
    "target_path": "outputs/tau_bench/reports/tau_demo_001.txt",
    "constraints": {
      "requires_user_approval": false,
      "forbidden_actions": ["delete_tool"],
      "risk_level": "low"
    },
    "candidate_tools": ["search_tool", "write_tool", "backup_write_tool"]
  }
]
```


## 6) 一键下载并对齐到 ToolClaw 接口（新增）

如果你希望直接在本地生成可被 `scripts/run_tau_bench.py --source` 消费的数据，可以用：

```bash
python3 scripts/prepare_tau_bench_source.py \
  --tau-repo-dir data/external/tau-bench \
  --out data/tau_bench/tau_bench.aligned.jsonl \
  --download-if-missing
```

说明：

- 脚本会在 `--tau-repo-dir` 不存在时自动从官方仓库下载 zip。
- 脚本会读取 `retail/airline` 的 `train/test` 任务文件，并转换成 ToolClaw `TauBenchAdapter` 可直接加载的 JSONL（每行一条样本）。
- 生成后即可直接运行：

```bash
scripts/run_tau_bench_remote.sh data/tau_bench/tau_bench.aligned.jsonl outputs/tau_bench_remote planner baseline,toolclaw_lite smoke 1
```

