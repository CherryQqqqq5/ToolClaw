# ToolClaw Method Contract

This document defines the current repository-supported method contract for ToolClaw. It is narrower than an aspirational production claim and should be treated as the authoritative implementation-level reference.

## 1. Scope

ToolClaw currently targets workflow intelligence under controlled tool execution backends.

The repository currently supports:

- HTGP planning with rule-based capability selection
- binder scoring that incorporates lexical signals, metadata hints, state preconditions, ordering sensitivity, and planner-visible backup tool ranking
- recovery, interaction, and reuse loops over a shared execution trace
- mock, semantic-mock, and hybrid tool execution backends
- heuristic artifact promotion with contamination guards
- stricter reuse admission, reuse provenance tracking, and runtime rollback from reuse to `a3_interaction` behavior

The repository does not currently support a stronger claim of:

- full real ToolSandbox execution fidelity
- verifier-backed promotion with version governance and artifact lifecycle control
- a production-grade external LLM orchestration service
- stable benchmark-level gains from reuse over interaction

## 2. System Ladder

The implemented system ladder is defined in [scripts/run_eval.py](../scripts/run_eval.py).

- `a0_baseline`: baseline execution over the demo workflow
- `a1_recovery`: recovery-only execution over the demo workflow
- `a2_planner`: planner + recovery
- `a3_interaction`: planner + recovery + interaction
- `a4_reuse`: `a3_interaction` + reuse compilation / retrieval

This ladder is a mechanism-addition contract, not a monotonic-performance contract.

## 3. Execution Backends

Tool execution is routed through a backend contract rather than hard-coded to a single toy environment.

- `mock`: fixed toy tools used for regression coverage
- `semantic_mock`: generic description/metadata-driven execution for benchmark tools beyond the toy registry
- `hybrid`: fixed mock first, semantic fallback second

`toolsandbox` tasks default to `semantic_mock`. This improves benchmark realism without claiming parity with the official ToolSandbox runtime.

## 4. Planner and Binder Contract

### Planner

The planner currently supports:

- capability-seeded workflow construction
- state-slot and dependency-edge aware step shaping
- ordering-sensitive checkpoint and fallback metadata
- planner-visible rollback / preflight requirement hints

### Binder

The binder is still heuristic, but it is no longer only lexical.

Current binder signals include:

- lexical overlap between capability text and tool id/description
- semantic hints from tool descriptions
- metadata hints such as `affordances`, `preferred_capabilities`, `disallowed_capabilities`, and `failure_priors`
- state preconditions and required state slots
- backup tool hints promoted into planner-time candidate ranking

This remains a lightweight heuristic binder, not a learned retrieval model.

## 5. Interaction Contract

ToolClaw interaction is not an end-to-end LLM agent loop.

The implemented interaction stack is:

1. rule-based uncertainty detection
2. rule-based query planning
3. configurable reply provider
4. rule-based semantic decoding
5. repair updater / workflow resume

### Supported interaction backends

Interaction shells currently support:

- `simulator`
- `human`
- `cli`
- `llm`

The `llm` backend is implemented as an injected reply-generation contract. In benchmark runners, this can be wired to OpenRouter-backed chat completions, but:

- query planning is still rule-based
- semantic decoding is still rule-based
- the interaction layer should therefore be reported as rule-based control with optional LLM-backed reply generation

### Compound approval + repair

The interaction stack now supports single-turn compound handling for:

- approval + missing state slot patch
- approval + target path patch
- approval + tool switch / fallback path

This support should be reported as implemented and benchmarked on targeted slices, not as a blanket production guarantee over arbitrary user dialogue.

## 6. Reuse Contract

Reuse is currently heuristic-first and guarded.

### Promotion

SWPC promotion currently uses:

- success and efficiency heuristics
- contamination guard metadata
- artifact metadata including task family, capability skeleton, failure context, and state slot requirements

This should still be reported as heuristic promotion, not verifier-backed promotion.

### Admission

The current reuse admission logic is stricter than the earlier repo state.

It now checks compatibility across:

- task signature / family
- capability skeleton
- failure context
- required state slots

It also distinguishes:

- exact reuse
- transfer reuse
- continuation replay attached to matched recovery suffixes

### Safety behavior

Reuse is now designed to avoid premature injection into repair-sensitive holes.

Current safety behaviors include:

- suppressing early reuse of repair-sensitive missing inputs
- separating exact and transfer-style reuse scoring
- rolling back to `a3_interaction` behavior when reuse causes early deviation or repair-overflow signals

Current evidence supports:

- safer reuse than before
- narrow exact-match reuse gains on some high-headroom recovery cases

Current evidence does not support:

- stable gains from reuse over `a3_interaction` at benchmark headline level
- broad transfer-reuse gains
- stable interaction-turn reduction from reuse on approval-heavy exact-match cases

## 7. Benchmark Interpretation

### Official ToolSandbox benchmark

The current repository headline benchmark remains the archived 88-sample official frozen ToolSandbox report.

Supported interpretation:

- interaction is the dominant capability jump
- planner does not yet show a headline lift over recovery-only on the official benchmark
- reuse matches interaction on the official benchmark but does not exceed it

### Historical core-slice evidence

The earlier bundled core slice showed a reuse regression (`a4 < a3`) and motivated the stricter reuse gate.

That historical result should not be erased, but it should now be interpreted as:

- evidence of the earlier reuse-timing flaw
- not the final statement about the current post-fix code path

### Post-fix targeted follow-up

The 2026-04-19 targeted follow-up bench on `outputs/remote/toolsandbox_core_r3_gatefix_bench` shows:

- `30` paired `a3` vs `a4` cases
- `0` reuse-specific regression cases
- transfer-style reuse firing without benchmark-level gain or harm

Supported interpretation:

- the specific reuse-timing regression appears fixed on the targeted follow-up slice
- the repository still does not support a paper claim that reuse improves over `a3_interaction` at benchmark headline level

### Exact-match continuation follow-up

The later Tau2 exact-match continuation follow-up on `outputs/remote/reuse_strata_tau2_auto_replay_v4` shows:

- `exact_match_reuse` with `5` paired cases
- `delta_tool_calls = -0.4`
- `delta_repair_actions = -0.4`
- `delta_user_turns = 0.0`

The gain is concentrated in exact-match recovery cases whose baseline `a3` path still incurred repair cost, especially:

- `binding_failure -> clarify_then_patch_then_retry`
- `environment_failure -> clarify_or_switch_then_retry`

Supported interpretation:

- reuse can act as a cost-reducing continuation prior under matched task signatures on some high-headroom recovery cases
- this is narrower than a general reuse claim and should not be generalized to transfer reuse or approval-heavy interaction compression

## 8. Reporting Guidance

Paper-safe wording:

- "training-free workflow intelligence layer"
- "rule-based interaction control with optional LLM-backed reply generation"
- "heuristic reusable execution prior"
- "safe reusable execution prior under matched task signatures"
- "exact-match reuse can reduce downstream repair/tool cost on some high-headroom recovery cases"
- "reuse safety improved on targeted follow-up slices"

Paper-unsafe wording at current repo state:

- "full real ToolSandbox execution"
- "verifier-backed reuse promotion"
- "production-grade LLM interaction orchestration"
- "`a4` surpasses `a3` on ToolSandbox"
- "transfer reuse yields stable held-out gains"
- "reuse broadly reduces interaction turns"
