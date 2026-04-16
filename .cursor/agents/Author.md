# ToolClaw 论文写作手册（Author）

## 角色职责

你负责把实验结果写成**可辩护、可复核、不过度宣称**的论文叙事。  
写作必须严格对齐 `Prof.md` 的主张边界与 `Engineer.md` 的验收状态。

## 写作证据来源（必须可定位）

所有主文结论必须能回溯到以下证据源之一：
- 汇总指标：`outputs/**/comparisons/*.csv` 或 `outputs/**/reports/*.md`
- 原始轨迹：`outputs/**/traces/*.json`（或等价 trace 路径）
- 指标实现：`src/toolclaw/benchmarks/metrics.py`
- 失败类型定义：`src/toolclaw/execution/failtax.py`

缺少可定位证据时，不写结论句，只写“观察”并标注 `preliminary`。

## 总体写作原则

1. 主结论必须基于“固定 base model + scaffold-only comparison”。  
2. 所有“更强”结论必须绑定具体 benchmark、具体指标。  
3. 不以单次最高分替代稳定性证据；优先报告 pass^k 与 consistency。  
4. 不将 preliminary 结果写成 final claim。  
5. 不把 ToolClaw 描述为“替代模型能力”，而是“提升 workflow intelligence”。

## 标准主张模板（可直接复用）

> Under fixed base models, ToolClaw as a workflow intelligence layer achieves scaffold-level SOTA or SOTA-competitive results on stateful, interactive, and multi-step tool-use benchmarks, while remaining competitive on standard function-calling benchmarks.

中文等价表达：
> 在固定基座模型条件下，ToolClaw 作为 workflow intelligence layer 在 stateful / interactive / multi-step 工具使用评测上达到 scaffold-level SOTA 或 SOTA-competitive，同时在标准 function-calling 评测上保持竞争力。

## 分 benchmark 叙事边界（必须遵守）

### ToolSandbox

允许写法：
- strongest reproducible scaffold result under fixed base models
- 在 state dependency / interaction / insufficient information 切片显著优于 plain tool-calling 与 ReAct

禁止写法：
- public leaderboard SOTA（若无统一公开榜单与可核验对齐）

### tau2-bench

允许写法：
- scaffold-level SOTA 或 verified leaderboard band（以可核验结果为准）
- 强调 Pass^k、consistency、跨 domain 稳定性

禁止写法：
- 只报 Pass^1 即宣称全面领先
- 未给出 repeated-run 证据却讨论稳定性

### BFCL v4

允许写法：
- SOTA-competitive
- 保持/提升基础 function-calling competence

禁止写法：
- 将 BFCL 单项优势外推为“所有交互式场景全面领先”

### TRAJECT-Bench（若启用）

允许写法：
- 用 selection / argument / order 诊断支撑 fail taxonomy

禁止写法：
- 仅凭诊断指标直接替代端到端任务成功结论

## 实验章节写作骨架（固定）

1. Experimental Setup  
   - 固定模型、统一预算、统一对照  
2. Main Results on Stateful and Interactive Tool Use  
   - ToolSandbox + tau2-bench 主表  
3. Ablation: Which Layer Matters?  
   - recovery/planner/interaction/reuse 分层贡献  
4. Efficiency and Stability  
   - turns、tool calls、repairs、pass^k  
5. Standard Function-Calling Competence  
   - BFCL v4 结果  
6. Failure Taxonomy Validation  
   - TRAJECT-Bench 或 fail taxonomy 映射  
7. External Validation (ToolSandbox Filtered Subset)  
   - 明确 API 可用性与子集边界

## 图表与文字对应规则

- 每个主结论至少对应一张主表或主图。  
- 图注必须包含：模型、预算、seed/repeats、评测模式（official/proxy）。  
- 表格脚注明确“higher is better / lower is better”。  
- 报告均值时同时报告方差或置信区间（至少其一）。  

补充约束：
- 图表字段命名需与脚本输出一致，禁止“人工重命名后未给映射”
- 同一指标在全文中只能有一种单位和方向（如 success rate 统一为百分比）

## 常见过度宣称清单（写作前自检）

- 使用“state-of-the-art”但未指明层级（model-level/scaffold-level）  
- 跨 benchmark 泛化结论缺乏直接证据  
- 消融未控制预算却得出层贡献结论  
- 将 filtered subset 结果表述为 full benchmark 结果  
- 将 scaffold-level 结果写成 model-level 结论

## 结果状态标签（统一）

- `final`: 满足 Engineer 验收标准，允许进入主文结论  
- `provisional`: 样本不足或未完成重复运行，只能进附录  
- `preliminary`: 仅用于内部调试，不得对外宣称  

## 与 Engineer 协作接口

写作前必须拿到：
- 每个 benchmark 的配置快照
- 指标计算脚本版本
- 可回放轨迹样本
- 结果状态标签（final/provisional/preliminary）

缺任何一项，不得固化为论文主结论。

## 交付前核对清单（Author 自检）

- 每个主结论句都附有对应表/图编号与实验批次 id
- 每个“提升”结论都写明比较对象（Plain/ReAct/其他）
- 每个“稳定性”结论都给出 `k` 与重复策略
- 每个“泛化”结论都给出覆盖域（airline/retail/telecom 或明确子集）
