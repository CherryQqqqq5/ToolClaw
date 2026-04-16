# ToolClaw 科研队伍运行手册

本目录定义三角色协作机制，用于将 ToolClaw 实验稳定推进到可发表状态，并防止实验与写作口径漂移。

## 队伍成员

- `Prof.md`：定义研究主张、benchmark 组合、对照体系、宣称边界、防漂移硬约束
- `Engineer.md`：负责实验落地、批次管理、验收标准、结果归档与异常处理
- `Author.md`：负责论文叙事、章节组织、结论边界、过度宣称自检

## 现实代码映射（统一口径）

本队伍所有决策需绑定以下代码层事实：
- 运行脚本集中在 `scripts/`
- 配置集中在 `configs/`
- 核心机制集中在 `src/toolclaw/`
- 回归验证集中在 `tests/`

若文档要求与上述实现冲突，优先修正文档，不允许“文档口径覆盖代码事实”。

## 标准协作流程

### Step 1: 立项锁定（Prof）

输入：
- 研究问题与目标
- 候选 benchmark 与对照系统

输出（必须）：
- 锁定版主张
- 锁定版 benchmark 组合
- 锁定版宣称边界
- 防漂移约束清单

进入下一步条件：
- `Prof.md` 已更新且通过团队确认

### Step 2: 实验执行（Engineer）

输入：
- `Prof.md` 锁定约束

输出（每个 benchmark 批次必须具备）：
- 配置快照（模型、采样、预算、seed、repeats）
- 原始轨迹/日志
- 指标汇总（可复跑）
- 批次标签（final/provisional/preliminary）

进入下一步条件：
- 主结论依赖的批次均为 `final`

### Step 3: 论文成文（Author）

输入：
- `Engineer.md` 产出的 final 批次结果
- `Prof.md` 规定的结论边界

输出：
- 实验章节草稿
- 主表/主图与结论一一对应
- 宣称边界合规检查记录

结束条件：
- 所有主结论均可追溯到 final 批次

## “可写入主结论”判定门槛

仅当以下条件同时满足，结果才能写入论文主文结论：

1. 固定 base model（未混模）
2. 对照 scaffold 同预算、同采样、同数据切分
3. 指标可复跑并与归档一致
4. 结果状态为 `final`
5. 叙事未超出对应 benchmark 宣称边界

任一条件不满足，只能作为附录或内部分析，不得进入主结论。

## 结果状态定义（统一）

- `final`：满足全部验收标准，可进入主文结论
- `provisional`：部分满足，仅可用于附录或趋势讨论
- `preliminary`：调试阶段结果，不得对外宣称

## 变更控制（防漂移）

以下任意项发生变化，必须新建实验批次，禁止与历史结果混报：

- base model / 版本
- 采样参数（temperature/top_p）
- 推理预算（steps/tokens）
- 工具与恢复预算
- scaffold 定义
- 评测模式（official/proxy）

## 推荐执行节奏

1. ToolSandbox + tau2-bench（主证据）  
2. BFCL v4（标准能力补充）  
3. TRAJECT-Bench（诊断增强）  

每完成一个阶段，先由 Engineer 给出 final 批次，再由 Author 固化对应章节，避免“先写后补证据”。
