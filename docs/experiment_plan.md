# ToolClaw Phase-1 Experiment Plan

## 0. Scope Lock

This document fixes the **Phase-1 experimental claims** for ToolClaw and serves as the contract between research intent and implementation. Its purpose is to prevent code drift.

**Phase-1 is strictly training-free.**
We do **not** perform supervised fine-tuning, reinforcement learning, preference optimization, model editing, or any parameter updates.
All gains in Phase-1 must come from **system-level workflow intelligence** only:
- recovery
- dynamic planning
- interaction-driven correction
- reusable compilation

The current execution entry points are assumed to be:
- `scripts/run_phase1.sh`
- `scripts/run_eval.sh`
- `scripts/run_ablation.sh`

---

## 1. Phase-1 Goal

Phase-1 does **not** attempt to prove that ToolClaw is a better trained model.
Phase-1 only asks whether adding an explicit workflow intelligence layer on top of frozen tool-calling agents improves complex task execution.

The immediate goal is to validate whether the following components provide measurable benefit:

1. explicit recovery
2. dynamic planner
3. interaction-driven closed-loop correction
4. reusable compilation and second-run reuse

---

## 2. Research Questions

Phase-1 is organized around four fixed research questions.

### RQ1. Is recovery effective?

Can explicit recovery convert execution failures into successful task completion, without relying on retraining?

This question targets the claim that many complex tool-use failures are not irrecoverable reasoning failures, but **recoverable workflow failures** such as:
- binding failure
- environment failure
- missing asset
- permission-related interruption

**Primary expectation:** recovery improves success rate and reduces fail-stop rate.

---

### RQ2. Is the dynamic planner effective?

Does capability-level planning plus tool binding improve task execution over direct or weakly structured baseline tool calling?

This question targets the claim that failure in complex tasks is often caused by poor workflow organization rather than a single wrong tool call.

The planner is expected to help in:
- ordering multi-step actions
- satisfying dependencies
- choosing a better tool subset
- reducing brittle local decisions

**Primary expectation:** dynamic planning improves success rate on tasks with branching structure or dependency-sensitive execution.

---

### RQ3. Is the interaction loop effective?

Can user interaction function as a **closed-loop repair signal**, rather than passive feedback?

This question targets the claim that user participation should be treated as a workflow control primitive.
The interaction loop is expected to help when the system faces:
- ambiguous environment state
- missing asset/path/tool hint
- unresolved branch choice
- approval or confirmation requirements

**Primary expectation:** interaction improves success rate on must-interact tasks while keeping user turns moderate.

---

### RQ4. Does reusable compilation provide cross-task benefit?

Can compiling successful execution into reusable workflow/policy artifacts improve future runs on repeated or structurally similar tasks?

This question targets the claim that successful traces should not be discarded after one run.
Instead, they should be turned into reusable assets that help later tasks.

**Primary expectation:** second-run performance improves on repeated task families.

---

## 3. Experimental Groups

Phase-1 ablations are fixed to the following five systems.

### A0. Baseline

A plain baseline tool-calling system with no explicit ToolClaw workflow intelligence.

Included:
- direct tool execution
- minimal sequential logic
- no explicit recovery
- no dynamic planner
- no interaction loop
- no reusable compilation

Purpose:
- establish the reference level

---

### A1. Recovery-only

A0 plus explicit recovery.

Included:
- baseline execution
- error detection
- recovery mapping
- repair application

Excluded:
- dynamic planner
- interaction loop
- reusable compilation

Purpose:
- isolate the value of repair/recovery only

---

### A2. Dynamic Planner + A1

A1 plus dynamic planner.

Included:
- recovery
- capability graph construction
- capability-to-tool binding
- execution plan generation

Excluded:
- interaction loop
- reusable compilation

Purpose:
- test whether structured planning adds value beyond recovery alone

---

### A3. Interaction + A2

A2 plus interaction-driven closed-loop correction.

Included:
- recovery
- dynamic planner
- ask-user / user-reply loop
- repair/state update from user input

Excluded:
- reusable compilation

Purpose:
- test whether interaction acts as an effective repair/control signal

---

### A4. Compiler + A3

A3 plus reusable compilation.

Included:
- recovery
- dynamic planner
- interaction loop
- workflow/policy artifact export
- second-run reuse of compiled artifacts

Purpose:
- test whether reuse provides cross-task or second-run benefit

Operational note:
- default CLI runs use an in-memory asset registry, so A4 reuse is guaranteed only within the current invocation
- claims about reuse across repeated CLI launches or sessions require a file-backed registry such as `run_eval.py --asset-registry-root <path>`

---

## 4. Fixed Comparison Structure

The experimental logic is fixed as follows:

- **A0 vs A1**: tests RQ1 (recovery effectiveness)
- **A1 vs A2**: tests RQ2 (dynamic planner effectiveness)
- **A2 vs A3**: tests RQ3 (interaction-loop effectiveness)
- **A3 vs A4**: tests RQ4 (reuse/compilation effectiveness)
- **A0 vs A4**: end-to-end Phase-1 gain

No other ablation order should be treated as primary unless explicitly added later.

---

## 5. Metrics

The following metrics are mandatory in Phase-1.

### 5.1 Success rate

Definition:
- fraction of tasks completed successfully under benchmark/task-family criteria

Role:
- primary reliability metric
- always reported first

---

### 5.2 Repair success rate

Definition:
- among runs that triggered at least one repair, the fraction where repair led to eventual successful completion

Role:
- primary metric for RQ1
- distinguishes “repair exists” from “repair actually helps”

---

### 5.3 Average tool calls

Definition:
- mean number of tool calls per run

Role:
- measures execution overhead
- ensures gains are not simply bought by excessive retrying

---

### 5.4 Average user turns

Definition:
- mean number of user-query / user-reply turns per run

Role:
- primary control metric for RQ3
- interaction should help, but should not explode user burden

---

### 5.5 Fail-stop rate

Definition:
- fraction of runs that terminate in an unrecovered stop/failure state

Role:
- directly measures brittleness
- especially important for A0 vs A1 and A2 vs A3

---

### 5.6 Second-run improvement

Definition:
- performance delta between first run and second run on repeated or structurally similar tasks

Possible forms:
- success rate improvement
- reduced tool calls
- reduced user turns
- reduced fail-stop rate

Role:
- primary metric for RQ4

---

## 6. Optional Supporting Metrics

These are secondary metrics and should not replace the mandatory metrics.

- average total steps
- average rollback count
- average repair count
- stop-reason distribution
- failure-type distribution
- planner overhead latency
- trace completeness

---

## 7. Task Families

Phase-1 task design is fixed into four task families. All benchmark tasks or synthetic tasks should be mapped into one of these families.

### T1. Static Recovery Tasks

Definition:
Tasks where the correct high-level path is mostly clear, but execution may fail due to local recoverable issues.

Examples:
- missing argument
- incorrect binding
- unavailable default tool
- missing asset/path
- transient environment error

Primary target:
- RQ1

Expected best contrast:
- A0 vs A1

---

### T2. Dynamic Branching Tasks

Definition:
Tasks where success depends on selecting the right branch, ordering, or tool subset.

Examples:
- branch on intermediate result
- choose between tools with different affordances
- reorder dependent steps
- insert/check checkpoint before risky action

Primary target:
- RQ2

Expected best contrast:
- A1 vs A2

---

### T3. Must-Interact Tasks

Definition:
Tasks that cannot be completed reliably without user clarification, approval, or environment hints.

Examples:
- ambiguous target path
- approval-required action
- unresolved branch preference
- missing information only user can provide

Primary target:
- RQ3

Expected best contrast:
- A2 vs A3

---

### T4. Repeated / Reusable Tasks

Definition:
Tasks that repeat exactly or recur with similar structure, allowing reuse of compiled workflow/policy artifacts.

Examples:
- same workflow with changed parameters
- same task template over different files
- repeated task family with minor environment variation

Primary target:
- RQ4

Expected best contrast:
- A3 vs A4

---

## 8. Minimum Evaluation Matrix

Phase-1 should cover at least the following mapping.

| Task family | Primary RQ | Most important comparison |
|---|---|---|
| T1 Static Recovery | RQ1 | A0 vs A1 |
| T2 Dynamic Branching | RQ2 | A1 vs A2 |
| T3 Must-Interact | RQ3 | A2 vs A3 |
| T4 Repeated / Reusable | RQ4 | A3 vs A4 |

Additionally, every family should eventually support:
- A0 baseline run
- A4 full ToolClaw-lite run

---

## 9. Concrete Claims to Validate

The following claims are fixed for Phase-1 and should be reflected in implementation and reporting.

### Claim C1: Recovery reduces brittle fail-stop behavior

Expected evidence:
- A1 > A0 on success rate for T1
- A1 < A0 on fail-stop rate for T1
- non-trivial repair success rate

---

### Claim C2: Dynamic planning improves workflow organization

Expected evidence:
- A2 > A1 on success rate for T2
- no large explosion in average tool calls
- fewer branch/order related failures

---

### Claim C3: Interaction is a useful control signal

Expected evidence:
- A3 > A2 on success rate for T3
- moderate average user turns
- lower fail-stop rate on ambiguity-driven tasks

---

### Claim C4: Reuse improves future execution

Expected evidence:
- A4 shows positive second-run improvement on T4
- repeated tasks require fewer repairs, fewer user turns, or fewer tool calls

Interpretation constraint:
- if the evidence comes from multiple passes inside one process, the default in-memory registry is sufficient
- if the evidence comes from separate commands or sessions, the experiment must use a persistent file-backed registry

---

## 10. Reporting Requirements

Every evaluation report in Phase-1 should contain the following sections.

### 10.1 Aggregate comparison table

Required fields:
- system
- tasks
- success_rate
- repair_success_rate
- avg_tool_calls
- avg_user_turns
- fail_stop_rate
- second_run_improvement

---

### 10.2 Per-task result table

Required fields:
- task_id
- task_family
- system
- success
- tool_calls
- repair_actions
- user_turns
- stop_reason
- failure_type
- reused_artifact (yes/no)

---

### 10.3 Family-wise breakdown

At minimum:
- T1 results
- T2 results
- T3 results
- T4 results

---

### 10.4 Ablation interpretation

The report must explicitly interpret:
- A0 vs A1
- A1 vs A2
- A2 vs A3
- A3 vs A4

Do not only show a final full-system result.

For ToolSandbox-specific reporting, the report must also state:
- whether the dataset came from an official ToolSandbox run or from a bundled fallback dataset
- whether augmentations were included or excluded
- the exact `num_runs` used for pass@k / consistency reporting
- whether A4 reuse was in-memory only or backed by a persistent registry

---

## 11. Implementation Mapping to Code

This experiment plan should directly constrain implementation.

### Baseline and ablations
- `src/toolclaw/benchmarks/baseline_runner.py`
- `src/toolclaw/benchmarks/tau_runner.py`
- `src/toolclaw/benchmarks/tau2_runner.py`
- `src/toolclaw/benchmarks/mcp_radar_runner.py`

### Recovery
- `src/toolclaw/execution/recovery.py`
- `src/toolclaw/execution/failtax.py`

### Dynamic planner
- `src/toolclaw/planner/htgp.py`
- `src/toolclaw/planner/capability_graph.py`
- `src/toolclaw/planner/binder.py`

### Interaction loop
- `src/toolclaw/interaction/irc.py`
- `src/toolclaw/interaction/query_policy.py`
- `src/toolclaw/interaction/repair_updater.py`
- `src/toolclaw/interaction/uncertainty_detector.py`

### Reusable compilation
- `src/toolclaw/compiler/swpc.py`
- `src/toolclaw/compiler/workflow_compiler.py`
- `src/toolclaw/compiler/policy_compiler.py`
- `src/toolclaw/compiler/skill_compiler.py`

### Metrics and output
- `src/toolclaw/benchmarks/metrics.py`
- `outputs/traces/`
- `outputs/reports/`

---

## 12. Execution Order

The development and evaluation order for Phase-1 is fixed as:

1. A0 baseline
2. A1 recovery-only
3. A2 dynamic-planner + A1
4. A3 interaction + A2
5. A4 compiler + A3

This order should also be reflected in:
- `scripts/run_phase1.sh`
- `scripts/run_eval.sh`
- `scripts/run_ablation.sh`

For the ToolSandbox branch of `scripts/run_ablation.sh`, current experiment-oriented defaults are:
- `--refresh`
- `--include-augmented`
- `--num-runs 3`

If official ToolSandbox data is required for a given writeup, the run must additionally set:
- `TOOLSANDBOX_ABLATION_REQUIRE_OFFICIAL=1`

---

## 13. What Phase-1 Should Not Drift Into

The following are explicitly out of scope for this document and should not drive implementation:

- model training
- SFT/RL experiments
- full MCP ecosystem integration
- skill marketplace design
- large-scale autonomous skill evolution
- multi-agent orchestration
- benchmark sprawl without task-family mapping

If a code path does not support one of the fixed RQs, ablation groups, metrics, or task families in this document, it should be considered lower priority.

---

## 14. Final Phase-1 Decision Rule

Phase-1 is considered successful if it establishes all of the following:

1. **Recovery helps** on static recovery tasks
2. **Dynamic planning helps** on branching tasks
3. **Interaction helps** on must-interact tasks
4. **Compilation/reuse helps** on repeated tasks
5. These gains are obtained **without training**

If these conditions are not met, Phase-2 training should not be started yet.
If these conditions are met, Phase-2 can be justified as an extension rather than a substitute for missing system design.
