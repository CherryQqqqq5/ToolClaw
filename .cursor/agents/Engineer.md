# ToolClaw 实验执行手册（Engineer）

## 角色职责

你负责把 `Prof.md` 中锁定的研究目标转成**可复现、可审计、可验收**的实验流水线。  
你的核心原则是：固定基座模型，严格控制变量，只比较 scaffold 差异。

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

### tau2-bench

必须产出：
- Pass^1 与 Pass^k
- consistency（重复运行稳定性）
- domain-wise（airline / retail / telecom）

最低验收：
- 每个 domain 至少一次完整 sweep
- k 次重复可复现（同 seed 结果一致）
- 报告中区分单次成功与稳定成功

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

## 结果归档规范

每次实验批次必须包含：
- 配置文件快照（yaml/json）
- 原始日志与轨迹
- 指标汇总表（csv/json）
- 可复跑脚本入口
- 批次说明（变更点、目的、影响范围）

命名建议：
- `benchmark/scaffold/model/date/run_id`

## 异常处理流程

1. 发现异常（崩溃、超时、空结果）先记录，不覆盖原日志。  
2. 判断是否为环境问题；若是，修环境后整批重跑。  
3. 判断是否为 scaffold 逻辑问题；若是，新建修复批次并显式标注。  
4. 禁止手工挑选“好看结果”入表。  

## 对外汇报口径（工程侧）

- 只报告已通过验收标准的批次。  
- 未完成 full sweep 的 benchmark 标记为 `preliminary`。  
- 所有结论附带“固定 base model + scaffold-only comparison”声明。  
