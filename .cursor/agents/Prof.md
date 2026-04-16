# ToolClaw 论文实验目标锁定（防漂移版）

## 可行性结论

结论：**可行**。  
原因：目标基于已公开且可复现的评测体系（ToolSandbox、tau2-bench、BFCL v4），并采用“固定基座模型、仅比较 scaffold”的设计，能够隔离 ToolClaw workflow intelligence layer 的真实增益。

## 代码锚点（研究口径必须对齐）

研究主张必须能映射到仓库内可执行代码，不允许脱离实现口径：
- 主运行入口：`scripts/run_toolsandbox.py`、`scripts/run_tau2_bench.py`、`scripts/run_eval.py`
- 基线/评测执行：`src/toolclaw/benchmarks/baseline_runner.py`、`src/toolclaw/benchmarks/tau2_runner.py`、`src/toolclaw/benchmarks/metrics.py`
- workflow 核心：`src/toolclaw/execution/executor.py`、`src/toolclaw/execution/recovery.py`、`src/toolclaw/planner/htgp.py`、`src/toolclaw/interaction/irc.py`
- 风险与预算控制：`src/toolclaw/policy/policy_engine.py`、`src/toolclaw/policy/budget_guard.py`、`src/toolclaw/policy/risk_control.py`
- 失败分类：`src/toolclaw/execution/failtax.py`

任何论文陈述若无法在以上文件中定位到对应机制或指标实现，默认不成立。

## 论文主张（锁定版）

在固定基座模型下，ToolClaw 作为上层 workflow intelligence layer，在 stateful、interactive、multi-step tool-use benchmark 上达到 **scaffold-level SOTA 或 SOTA-competitive**，并在标准 function-calling benchmark 上保持竞争力。

> 口径约束：不宣称“模型 SOTA”，只宣称“同模型条件下的 scaffold-level 提升”。

## Benchmark 组合（锁定版）

### 主 benchmark
1. **ToolSandbox**（stateful / conversational / interactive）
2. **tau2-bench**（Pass^k、一致性、跨 domain 规则）

### 补充 benchmark
3. **BFCL v4**（标准 function-calling competence）

### 诊断 benchmark（可选增强）
4. **TRAJECT-Bench**（trajectory-aware failure diagnosis，优先于 FuncBenchGen）

## 对照系统（锁定版）

同一基座模型下，至少包含以下 scaffold：
- Plain tool-calling
- ReAct
- Recovery-only
- Planner-only
- No-interaction
- No-reuse
- ToolClaw full

### 对照实现约束

- 对照组必须由同一 runner 体系触发（优先 `src/toolclaw/benchmarks/baseline_runner.py`），禁止人工拼接结果表。
- 对照差异仅允许体现在 scaffold 组件开关，不允许隐式改变模型、预算、评测子集。

## 指标（锁定版）

### ToolSandbox
- verified success
- raw trace success
- milestone similarity / coverage
- user turns, tool calls
- repair actions, recovery budget
- 分 slice 成功率（state dependency / insufficient information / interaction）

说明：指标计算逻辑须可在 `src/toolclaw/benchmarks/metrics.py` 或等价脚本中复现，禁止“表格手算”。

### tau2-bench
- Pass^1
- Pass^k
- consistency / repeated-run stability
- domain-wise success（airline / retail / telecom）

说明：Pass^k 与 consistency 需由重复运行产生，不允许从单次轨迹外推。

### BFCL v4
- overall accuracy
- 子项 accuracy
- agentic / multi-turn 子项
- cost / latency（附属指标）

### TRAJECT-Bench（若启用）
- final accuracy
- tool selection correctness
- argument correctness
- dependency/order satisfaction

## 结果宣称边界（锁定版）

- **ToolSandbox**：宣称“固定模型下 strongest reproducible scaffold result”，不宣称公共榜单第一。
- **tau2-bench**：可宣称“冲击 scaffold-level SOTA / verified leaderboard band”。
- **BFCL v4**：目标为“SOTA-competitive，不拖后腿”，不强求绝对第一。

## 实验章节结构（锁定版）

1. Experimental Setup  
2. Main Results on Stateful & Interactive Tool Use（ToolSandbox + tau2-bench）  
3. Ablation: Which Layer Matters?  
4. Efficiency and Stability  
5. Standard Function-Calling Competence（BFCL v4）  
6. Failure Taxonomy Validation（TRAJECT-Bench 或 fail taxonomy 对照）  
7. Official ToolSandbox Filtered Subset Validation（按当前 API 可用性）

## 执行顺序（锁定版）

1. 先完成 ToolSandbox + tau2-bench 最终版。  
2. 再补 BFCL v4，验证基础 function-calling 不退化。  
3. 最后补 TRAJECT-Bench，用于 failure taxonomy 诊断增强。

## 防漂移约束（必须遵守）

在进入大规模跑分前，以下配置一次性锁死并写入实验配置：
- base model（版本、上下文窗口）
- sampling（temperature/top_p）
- 推理预算（max steps / token budget）
- 工具预算（最大 tool calls / recovery budget）
- 对照 scaffold 定义与实现版本
- official vs proxy evaluation mode 的边界

若后续变更任一项，必须在实验记录中标注为新试验批次，禁止与既有结果混报。

## 变更审批机制（新增）

以下事件必须由 Prof 明确批准后才能进入新批次：
- 新增或移除 benchmark
- 修改主结论措辞层级（例如从 competitive 提升到 SOTA-competitive）
- 更换主对照矩阵
- 改动 `configs/benchmark_toolsandbox.yaml` 或 `configs/benchmark_tau2.yaml` 的关键预算字段
