# Paper Claim Freeze Plan

## Update Note (2026-04-19)

The benchmark-portfolio guidance in this file is now superseded by:

- [docs/paper_benchmark_portfolio.md](docs/paper_benchmark_portfolio.md)
- [configs/paper_claim_matrix.yaml](configs/paper_claim_matrix.yaml)

Keep using this document as a record of the frozen archived results, but use the newer portfolio and claim-matrix files for current paper-planning decisions.

## 1. Purpose

This document freezes the current paper-facing experimental scope for ToolClaw after the `a2_planner` system-definition fix.

Its purpose is to prevent further drift in:

- benchmark scope
- claim wording
- table selection
- interpretation of `a0` through `a4`
- what counts as main evidence versus supporting or excluded evidence

This document should be treated as a writing-time guardrail, not as a speculative wishlist.

## 2. Decision: freeze the current main experiments

The current recommendation is:

1. **Freeze the current main experiment set**
2. **Do not add new benchmark families now**
3. **Do not add Tau-Bench to the main paper path**
4. **Do not make further algorithmic changes before drafting the paper**

Reasoning:

- the current ToolSandbox official benchmark already provides strong headline evidence
- the current ToolSandbox bundled core slice plus matched ablation already explain the mechanism
- the current Tau2 suite already covers interaction and approval semantics stress cases
- additional benchmark expansion would increase scope and provenance complexity more than it would increase credibility

## 3. Final benchmark package

The final benchmark package for the paper should be:

### 3.1 Main evidence

1. **ToolSandbox official frozen benchmark**
   - outdir: `outputs/paper_clean_v1/exp_toolsandbox_true_official_r3_openrouter_a2fix`
   - role: main performance table

2. **ToolSandbox bundled core slice**
   - outdir: `outputs/paper_clean_v1/exp_toolsandbox_core_explicit_formaljson_r3_openrouter_a2fix`
   - role: mechanism analysis

3. **Matched ToolSandbox ablation**
   - outdir: `outputs/remote/toolsandbox_matched_20260406_094138`
   - role: mechanism isolation

4. **Tau2 full benchmark after `a2` fix**
   - outdir: `outputs/paper_clean_v1/exp09_tau2_a2fix_r3_openrouter`
   - role: interaction / approval stress validation

### 3.2 Supporting evidence

1. **Tau2 approval-only slice**
   - outdir: `outputs/paper_clean_v1/exp07_tau2_approval_only_r3_openrouter`
   - role: pure approval behavior

2. **Tau2 isolated repeated `binding_plus_approval` stress**
   - outdir: `outputs/paper_clean_v1/exp08_tau2_binding_plus_approval_a3_a4_r10_openrouter`
   - role: negative evidence limiting reuse claims

3. **ToolSandbox reuse split train/eval**
   - outdirs:
     - `outputs/exp/toolsandbox_split_train`
     - `outputs/exp/toolsandbox_split_eval`
   - role: boundary result showing no held-out success advantage for reuse

### 3.3 Excluded from the main paper path

1. **Tau-Bench**
   - reason: not rerun after the `a2` fix; previously saturated and low-value for the main argument

2. **Derived ToolSandbox `bench_slices`**
   - reason: redundant with official focused summaries, bundled core slice, and matched ablation

3. **Old pre-`a2`-fix runs**
   - reason: stale system definition for `a2`

4. **Debug-stage approval-fix runs**
   - reason: useful during debugging, but superseded by final `a2fix` results

## 4. Current system ladder

The paper should use the following interpretation of the five main systems:

- `a0_baseline`: baseline anchor
- `a1_recovery`: recovery-enabled execution without planner
- `a2_planner`: `a1_recovery + planner`
- `a3_interaction`: `a2_planner + interaction`
- `a4_reuse`: `a3_interaction + reuse/compiler`

Important caveat:

- from `a1` onward, the ladder is a clean incremental mechanism stack
- `a0 -> a1` is **not** a perfect single-switch increment
- therefore the paper should not claim that `a0-a4` is a perfectly symmetric one-knob ladder

Paper-safe wording:

- "`a1` through `a4` form the primary incremental system ladder"
- "`a0` serves as the baseline anchor"

Avoid saying:

- "every layer differs by exactly one mechanism from the immediately previous layer"

That sentence is too strong for `a0 -> a1`.

## 5. Claims currently supported

The current experimental package supports the following claims.

### 5.1 C1-style main effectiveness claim

Supported:

- ToolClaw's interaction-enabled variants substantially outperform non-interaction variants on the restored official ToolSandbox frozen benchmark.

Main evidence:

- official ToolSandbox a2fix benchmark

Paper-safe summary:

- `a3_interaction` and `a4_reuse` reach `1.000` mean success on the official ToolSandbox benchmark, while non-interaction variants remain in the `0.659` to `0.693` range.

### 5.2 Planner claim

Supported:

- planner helps on failure-heavy mechanism slices, but planner is not the dominant source of gains

Main evidence:

- `a2 = a1` on official ToolSandbox
- `a2 > a1` on bundled core slice
- matched ablation shows planner-only is insufficient without repair/interaction

Paper-safe summary:

- planner is beneficial on harder slices, but it is not the primary driver of the large gains seen in the full system

### 5.3 Interaction claim

Supported:

- interaction/repair workflow control is the dominant source of performance improvement

Main evidence:

- official ToolSandbox
- bundled core slice
- matched ablation
- Tau2 full benchmark

Paper-safe summary:

- the main performance jump occurs when moving from non-interaction systems to interaction-enabled systems

### 5.4 Approval / interaction semantics claim

Supported:

- after the approval fixes, interaction-enabled systems reliably solve pure approval-gated Tau2 tasks

Main evidence:

- Tau2 full benchmark
- Tau2 approval-only slice

### 5.5 Explainability claim

Supported:

- ToolClaw's gains can be explained via failure-mode-sensitive slices and ablations, not only aggregate benchmark numbers

Main evidence:

- bundled core slice
- matched ablation
- Tau2 stress tests

## 6. Claims not currently supported

The paper should **not** make the following claims.

### 6.1 Strong reuse claim

Not supported:

- "`a4_reuse` consistently outperforms `a3_interaction`"
- "`reuse` provides a stable held-out generalization gain"

Reason:

- on the bundled core slice, `a4 < a3`
- the reuse split is saturated and shows no held-out success gain
- isolated Tau2 stress (`exp08`) falsifies a strong compound approval+repair reuse claim

### 6.2 Strict monotonic ladder claim

Not supported:

- "each system strictly improves over the previous one on every benchmark"

Reason:

- official ToolSandbox: `a1 = a2`, `a3 = a4`
- bundled core slice: `a4 < a3`

### 6.3 Strong cross-benchmark generalization claim

Not supported in the frozen paper path:

- "ToolClaw improvements transfer robustly across another independent benchmark family"

Reason:

- Tau-Bench was not retained as final main evidence after the `a2` fix
- current final package relies on ToolSandbox + Tau2, not a broad multi-family benchmark suite

Paper-safe alternative:

- describe Tau2 as a stress-test benchmark family validating interaction and approval behavior
- avoid claiming broad cross-benchmark generalization

## 7. Table plan for the paper

The paper should use a small number of high-signal tables.

### 7.1 Main table

Use:

- official ToolSandbox a2fix benchmark

Columns:

- `a0_baseline`
- `a1_recovery`
- `a2_planner`
- `a3_interaction`
- `a4_reuse`

Rows:

- overall success rate
- optional failtax summary
- optional interaction / efficiency controls

### 7.2 Mechanism table

Use:

- bundled core slice a2fix benchmark
- matched ablation

Purpose:

- show that planner helps somewhat
- show that interaction/repair is the main gain
- show that reuse is not the dominant factor on this slice

### 7.3 Stress / boundary table

Use:

- Tau2 full benchmark a2fix

Purpose:

- show approval and interaction stress behavior
- show `a3/a4` gains over `a1/a2`
- show that `a2` no longer underperforms `a1`

### 7.4 Appendix-only tables

Use:

- Tau2 approval-only slice
- isolated `binding_plus_approval` stress
- reuse split

Purpose:

- bound the claim surface
- include negative evidence cleanly

## 8. Section plan for the paper

Recommended paper-facing structure:

### 8.1 Experimental setup

Include:

- base model and fixed runtime setup
- dataset distinction:
  - official frozen ToolSandbox benchmark
  - bundled core/fallback slice
- system definitions for `a0-a4`
- explanation that `a0` is baseline anchor and `a1-a4` are the main incremental ladder

### 8.2 Main results

Use:

- official ToolSandbox a2fix benchmark

Main message:

- interaction-enabled ToolClaw variants dominate the benchmark

### 8.3 Layer-wise mechanism analysis

Use:

- bundled core slice
- matched ablation

Main message:

- interaction/repair is the dominant mechanism
- planner helps but is secondary
- reuse is not a universally beneficial mechanism

### 8.4 Interaction and approval stress tests

Use:

- Tau2 full benchmark
- selected appendix references to approval-only and isolated stress

Main message:

- approval semantics matter
- interaction solves pure approval tasks
- compound approval+repair remains a limitation

### 8.5 Limitations

Include explicitly:

- no strong held-out reuse gain
- no strong cross-benchmark generalization claim
- no claim of strict monotonic improvements at every layer

## 9. What not to do next

To prevent drift, do **not** do the following before drafting:

1. Do not add new benchmark families.
2. Do not reintroduce derived `bench_slices` into the main evidence path.
3. Do not make new core algorithm changes.
4. Do not rewrite the system ladder into a stronger monotonic claim than the data supports.
5. Do not promote Tau-Bench back into the main paper path unless it is rerun and needed for a conscious C6-style claim.

## 10. What is still acceptable before submission

The following limited actions are still acceptable:

1. Reformat tables and summaries.
2. Tighten benchmark provenance wording.
3. Clean old stale output directories.
4. Add appendix-only negative-result summaries.
5. If absolutely necessary, rerun Tau-Bench **only** as a deliberate decision to restore a cross-benchmark claim.

## 11. Final freeze decision

Current freeze decision:

- **freeze the main benchmark package now**
- **do not expand to new benchmark families**
- **do not rely on Tau-Bench for the main paper**
- **center the paper on ToolSandbox official + ToolSandbox core/matched + Tau2**

This is the most credible and lowest-drift path from the current evidence state to a defensible paper.
