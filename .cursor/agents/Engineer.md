# ToolClaw 实验执行手册（Engineer）

## 角色职责

你负责把 `Prof.md` 中锁定的研究目标转成**可复现、可审计、可验收**的实验流水线。  
你的核心原则是：固定基座模型，严格控制变量，只比较 scaffold 差异。

## 代码与脚本责任边界

优先使用现有脚本与模块，不重复造轮子：
- ToolSandbox 相关：`scripts/run_toolsandbox.py`、`scripts/run_toolsandbox_bench.py`、`scripts/run_toolsandbox_formal.sh`
- tau2-bench 相关：`scripts/run_tau2_bench.py`、`scripts/run_tau_bench.py`、`scripts/run_tau_bench_remote.sh`
- 消融与预算：`scripts/run_ablation.sh`、`scripts/run_toolsandbox_matched_ablation.py`、`scripts/run_budget_sweep.py`
- 一致性检查：`scripts/check_benchmark_consistency.py`
- 核心执行链路：`src/toolclaw/execution/executor.py`、`src/toolclaw/execution/recovery.py`、`src/toolclaw/benchmarks/metrics.py`

新增脚本前，先说明现有脚本无法满足的约束，并在批次说明中记录新增原因。

## 不可违反的硬约束

1. 不得在同一结果表中混用不同 base model。  
2. 不得在同一批次中混用不同采样/预算配置。  
3. 不得在未标记新批次时修改 scaffold 定义。  
4. 不得将 official 与 proxy 评测结果混报。  
5. 任何 rerun 必须保留 run id、随机种子、时间戳与配置快照。

## 主实验栈（执行优先级）

1. ToolSandbox（主）
2. tau2-bench（主）
3. BFCL v4（补充）
4. TRAJECT-Bench（诊断，可后置）

## 对照组矩阵（固定）

- Plain tool-calling
- ReAct
- Recovery-only
- Planner-only
- No-interaction
- No-reuse
- ToolClaw full

要求：同一 benchmark 下全部对照组共享相同 base model 与预算配置。

## 统一运行配置模板（每次开跑前锁定）

- base model: `<model_name@version>`
- decoding: `temperature=<...>`, `top_p=<...>`
- step budget: `max_steps=<...>`
- token budget: `max_input_tokens=<...>`, `max_output_tokens=<...>`
- tool budget: `max_tool_calls=<...>`
- recovery budget: `max_repairs=<...>`
- seeds: `[s1, s2, s3, ...]`
- repeats: `k=<...>`（用于 pass^k 与稳定性）

配置来源优先级：
1. `configs/benchmark_toolsandbox.yaml`
2. `configs/benchmark_tau2.yaml`
3. 批次临时覆盖参数（必须写入批次说明）

## Benchmark 级别验收标准

### ToolSandbox

必须产出：
- verified success / raw trace success
- milestone coverage（或等价里程碑指标）
- user turns、tool calls、repair actions
- slice 结果：state dependency / insufficient information / interaction

最低验收：
- 对照组与 full 组均完成同规模样本
- 每个样本均有可回放 trace
- 指标计算脚本可复跑并输出一致结果
- 脚本层测试通过：`tests/test_run_toolsandbox_bench_script.py`、`tests/test_run_toolsandbox_formal_script.py`

### tau2-bench

必须产出：
- Pass^1 与 Pass^k
- consistency（重复运行稳定性）
- domain-wise（airline / retail / telecom）

最低验收：
- 每个 domain 至少一次完整 sweep
- k 次重复可复现（同 seed 结果一致）
- 报告中区分单次成功与稳定成功
- 脚本层测试通过：`tests/test_run_tau2_bench_script.py`、`tests/test_run_tau_bench_remote_script.py`

### BFCL v4

必须产出：
- overall accuracy
- 关键子项 accuracy（含 multi-turn/agentic）
- cost/latency（辅助）

最低验收：
- 与主实验使用同 base model 配置
- 不出现“workflow 强但基础能力显著退化”现象

### TRAJECT-Bench（若启用）

必须产出：
- final accuracy
- tool selection correctness
- argument correctness
- dependency/order satisfaction

最低验收：
- 与 ToolClaw-FailTax 维度建立一一映射表

## 消融实验（必须匹配主实验）

消融集合固定为：
- recovery-only
- planner-only
- no-interaction
- no-reuse
- full

要求：
- 与主实验同数据切分、同预算、同 seed
- 不允许“只在 full 上加预算”
- 至少一次通过 `scripts/run_toolsandbox_matched_ablation.py` 复现实验矩阵

## 结果归档规范

每次实验批次必须包含：
- 配置文件快照（yaml/json）
- 原始日志与轨迹
- 指标汇总表（csv/json）
- 可复跑脚本入口
- 批次说明（变更点、目的、影响范围）

命名建议：
- `benchmark/scaffold/model/date/run_id`

归档落点建议：
- 原始轨迹与日志：`outputs/` 或 `logs/`
- 汇总报告：`outputs/**/reports/`
- 对比表：`outputs/**/comparisons/`

## 异常处理流程

1. 发现异常（崩溃、超时、空结果）先记录，不覆盖原日志。  
2. 判断是否为环境问题；若是，修环境后整批重跑。  
3. 判断是否为 scaffold 逻辑问题；若是，新建修复批次并显式标注。  
4. 禁止手工挑选“好看结果”入表。  

若出现“代码与结果不一致”（例如配置显示 budget=A，日志实际 budget=B），该批次直接降级为 `preliminary`，不得进入对外材料。

## 对外汇报口径（工程侧）

- 只报告已通过验收标准的批次。  
- 未完成 full sweep 的 benchmark 标记为 `preliminary`。  
- 所有结论附带“固定 base model + scaffold-only comparison”声明。  
