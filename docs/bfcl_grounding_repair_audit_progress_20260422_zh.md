# BFCL Grounding 修复进展（2026-04-22，汇报版）

## 当前结论

当前 BFCL grounding 线的状态可以概括成一句话：

**核心 grounding 机制已经成立，当前增益主要来自更强的 extraction，而不是 repair 已经形成闭环。**

也就是说：

- `fc_preflight_only` 仍然会在 required-arg-sensitive 样本上明显塌缩；
- `fc_grounding_recovery / a4_reuse` 已经可以把这类 selection-to-execution gap 拉回到 baseline-level；
- 但 `repair_success_count` 仍然是 `0`，说明当前提升还不是 repair 真正闭环带来的 headline gain。

## 为什么会继续做 audit，而不是直接 full rerun

之前 larger frozen slice 的结论已经很清楚：

- grounding 不再比 baseline 差；
- 但也没有稳定超过 baseline。

所以继续直接跑 full BFCL 的价值不高。更合理的路径是：

1. 先把 **曾经触发过 repair 的样本** 单独抽出来；
2. 看清楚到底是：
   - repair 已执行但没转成 official success；
   - 还是根本拿不到 concrete repair candidate；
3. 再决定下一步该补 recovery，还是补 adapter/runtime extraction。

## 审计切片

这次用了一个版本化的小切片：

- [grounding_repair_applied_audit_v1.jsonl](/Users/cherry/mnt/ToolClaw/data/bfcl_slices/grounding_repair_applied_audit_v1.jsonl)

组成：

- 58 条在 frozen larger slice 中 `fc_grounding_recovery` 曾经出现过 `repair_applied` 的样本
- 8 条 `irrelevance / live_irrelevance` guard

总计：

- `66` 条样本
- 四臂都跑：
  - `a0_baseline`
  - `fc_preflight_only`
  - `fc_grounding_recovery`
  - `a4_reuse`

## v1：先把坏 repair 切掉

### 代码修复

这一步先不增强 extraction，只先修 recovery 的坏行为：

- `missing_required_input` 只 patch 缺失 key；
- 不再把无关已有输入整包带回；
- required key 只有 concrete value 才允许写回；
- 同时修掉 `uncertainty_detector` 对 list/dict 值的结构化判断 bug。

相关文件：

- [recovery.py](/Users/cherry/mnt/ToolClaw/src/toolclaw/execution/recovery.py)
- [uncertainty_detector.py](/Users/cherry/mnt/ToolClaw/src/toolclaw/interaction/uncertainty_detector.py)
- [test_recovery.py](/Users/cherry/mnt/ToolClaw/tests/test_recovery.py)
- [test_uncertainty_detector.py](/Users/cherry/mnt/ToolClaw/tests/test_uncertainty_detector.py)

### v1 结果

结果文件：

- [official_scoreboard.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v1/official_scoreboard.json)
- [toolclaw_diagnostics.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v1/toolclaw_diagnostics.json)

official success：

- `a0_baseline = 0.1212`
- `fc_preflight_only = 0.1212`
- `fc_grounding_recovery = 0.1212`
- `a4_reuse = 0.1212`

最重要的诊断：

- `fc_grounding_recovery`
  - `repair_applied_count = 0.0`
  - `repair_success_count = 0.0`
  - `missing_required_arg_rate = 0.5657`
  - `preflight_interception_rate = 0.8788`

这一步的意义不是提分，而是把问题收窄：

**一旦不允许乱 patch，grounding 路径就暴露出它经常拿不到 concrete repair value。**

也就是说，主问题不再是：

- recovery 乱补值

而是：

- BFCL adapter/runtime 的 second-pass extraction 还不够强。

## v2：第一次补 adapter-side extraction

### 代码修复

开始把修复重点转回 BFCL adapter/runtime，仍然不动 shared executor 语义。

这一步加入了几类更通用的 extraction：

- email / string-array extraction
- `columns / fields` 的常见 schema alias
- string identifier 抽取（如 host agent id）

相关文件：

- [bfcl_runtime.py](/Users/cherry/mnt/ToolClaw/src/toolclaw/bfcl_runtime.py)
- [test_bfcl_scripts.py](/Users/cherry/mnt/ToolClaw/tests/test_bfcl_scripts.py)

### v2 结果

结果文件：

- [official_scoreboard.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v2/official_scoreboard.json)
- [toolclaw_diagnostics.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v2/toolclaw_diagnostics.json)

official success：

- `a0_baseline = 0.1364`
- `fc_preflight_only = 0.1212`
- `fc_grounding_recovery = 0.1364`
- `a4_reuse = 0.1364`

相对 `v1`：

- `a0 / grounding / a4` 都提升了 `+0.0152`
- `fc_preflight_only` 不变

`fc_grounding_recovery` diagnostics：

- `missing_required_arg_rate: 0.5657 -> 0.5240`
- `preflight_interception_rate: 0.8788 -> 0.8333`
- `exec_verified: 0.1212 -> 0.1667`
- `repair_applied_count: 0.0`
- `repair_success_count: 0.0`

这一步说明：

**更强的 extraction 确实能转化成更多可执行、可验证成功的样本。**

但同时也说明：

- 提升并不是 repair 成功带来的；
- repair 仍然没有真正闭环。

## v3：继续补通用 slot extraction

### 代码修复

在 `v2` 的基础上，又补了一轮不丢泛化性的 extractor：

- `camelCase/snake_case` key 归一化
- `weight / distance / perPage / days` 这类常见 numeric slot
- `where_to / city / country / ticker` 这类常见 string slot
- `nodeId / podId` 这类常见 ID slot

相关文件：

- [bfcl_runtime.py](/Users/cherry/mnt/ToolClaw/src/toolclaw/bfcl_runtime.py)
- [test_bfcl_scripts.py](/Users/cherry/mnt/ToolClaw/tests/test_bfcl_scripts.py)

### v3 结果

结果文件：

- [official_scoreboard.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v3/official_scoreboard.json)
- [toolclaw_diagnostics.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v3/toolclaw_diagnostics.json)
- [claim_summary.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_repair_audit_v3/claim_summary.json)

official success：

- `a0_baseline = 0.2121`
- `fc_preflight_only = 0.1212`
- `fc_grounding_recovery = 0.2121`
- `a4_reuse = 0.2121`

相对 `v2`：

- `a0 / grounding / a4` 再次一起提升
- `fc_preflight_only` 仍然不变

`fc_grounding_recovery` diagnostics：

- `missing_required_arg_rate: 0.5240 -> 0.4134`
- `preflight_interception_rate: 0.8333 -> 0.6667`
- `exec_verified: 0.1667 -> 0.3333`
- `tool_selection_correctness: 0.1717 -> 0.3157`
- `structure_correctness: 0.1667 -> 0.3030`
- `repair_applied_count = 0.0`
- `repair_success_count = 0.0`

### 哪些样本被翻正了

这轮一共多翻正了 5 个共享残差样本：

- `live_multiple_138-53-0`
- `live_simple_126-82-0`
- `live_simple_127-82-1`
- `multiple_116`
- `simple_python_107`

这几个样本的共同特点是：

- 以前会在 grounded 路径上卡在 `awaiting_user_interaction`
- 现在因为 extraction 更强，直接变成 `success_criteria_satisfied`

## 这三轮说明了什么

### 已经成立的结论

1. **preflight-only 依然是干净的反事实对照**
   - 它在三轮里都显著低于其他三臂
   - 说明 selection-to-execution gap 依然存在，而且可观测

2. **grounding 路径的当前收益主要来自更强的 extraction**
   - 不是来自 repair 记账上的成功闭环
   - 而是更多样本在 preflight 前就被补成了可执行 action

3. **这条线没有丢泛化性**
   - 修复都留在 BFCL adapter/runtime
   - shared executor 没有被塞入 BFCL field heuristic

### 还没有成立的结论

1. **repair 还不能算主增益来源**
   - `repair_success_count` 仍然是 `0`
   - 所以不能把当前结果表述成“repair 已经形成 headline gain”

2. **grounding 还没有在这个 66 条 audit slice 上超过 baseline**
   - 目前只是和 baseline 一起涨
   - 这说明很多提升是 shared residual 被更强 extraction 一起修正了

## 当前最准确的论文/汇报表述

现在最稳的写法是：

> 在 BFCL required-arg-sensitive 审计切片上，`fc_preflight_only` 持续显著塌缩，而 grounding 路径通过更强的 adapter-side extraction 将更多样本提前转化为 schema-complete executable actions，使 `fc_grounding_recovery / a4_reuse` 恢复到与 baseline 对齐的 success，并显著改善 `exec_verified`、tool-selection 和 structure 指标。当前增益主要来自 extraction strengthening，而不是 repair 已经形成闭环。

不建议写成：

> repair 已经明显带来了 headline success lift

因为当前数据还不支持这句话。

## 下一步建议

如果明天汇报优先，当前最合理的策略是：

1. **先停在这里，不再继续扩实验面**
   - 因为 `v3` 已经把问题解释清楚了
   - 再烧更大实验，短期内也很难把 `repair_success_count` 从 `0` 直接拉成 headline gain

2. **在汇报里把 BFCL 部分定位成 mechanism evidence**
   - `fc_preflight_only` 明显失败
   - stronger grounding/extraction 恢复更多 executable success
   - 但 repair 本身还未成为主增益来源

3. **后续真正要继续推进时**
   - 应该优先打 `repair_default_inputs / simulated_missing_arg_values` 的 concrete candidate 质量
   - 而不是继续改 recovery 框架本身
