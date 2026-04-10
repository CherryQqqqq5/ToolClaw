# ToolClaw Method Contract

This document defines the current phase-1 contract for ToolClaw. It is intentionally narrower than the README claims and should be treated as the authoritative implementation-level reference.

## Scope

Phase-1 targets workflow intelligence under controlled tool execution. The system currently supports:

- HTGP planning with rule-based capability selection and tool binding
- recovery, interaction, and reuse loops over a shared execution trace
- mock and semantic-mock execution backends
- heuristic artifact promotion with explicit contamination guards

Phase-1 does not yet claim:

- full real ToolSandbox execution
- verifier-backed promotion with rollback/version governance
- external LLM interaction orchestration as a production service

## Execution Backends

Tool execution is routed through a backend contract instead of hard-coding `mock_tools.py`.

- `mock`: fixed toy tools used for regression coverage
- `semantic_mock`: generic description/metadata-driven execution for benchmark tools beyond the toy registry
- `hybrid`: try fixed mock first, then semantic fallback

`toolsandbox` tasks default to `semantic_mock`. This improves benchmark realism without claiming parity with the official ToolSandbox runtime.

## Planner Binding

`ToolBinder` now uses three signal classes:

- lexical overlap between capability text and tool id/description
- semantic hints from tool descriptions
- metadata hints such as `affordances`, `preferred_capabilities`, `disallowed_capabilities`, and `failure_priors`

This is still a lightweight semantic binder, not a learned retrieval model.

## Interaction Backends

Interaction shells support:

- `simulator`
- `human`
- `llm`

The `llm` backend is currently a configured completion contract, not a networked provider implementation. It accepts scripted payloads and environment-driven payload injection so the interaction layer can be exercised without a placeholder error path.

## Reuse Promotion

SWPC promotion is currently heuristic-first.

- compile gate uses success plus efficiency heuristics
- artifacts carry `promotion_status`, `promotion_mode`, and `verifier_backed`
- held-out / eval split tasks can block compile via contamination guard metadata

This should be reported as heuristic promotion, not verifier-backed promotion.

## Benchmark Interpretation

ToolSandbox smoke runs are valid for workflow plumbing and layer activation checks only when:

- source tasks contain real messages, tools, and verification signals
- smoke slices include state, interaction, recovery, planner distractor, exact reuse, and transfer-style reuse coverage
- reports distinguish raw execution from scored evaluation

They are not evidence of full ToolSandbox execution fidelity unless the runtime is connected to the official tool environment.
