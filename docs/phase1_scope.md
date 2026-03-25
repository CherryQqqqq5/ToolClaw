# Phase-1 Scope

## Scope statement

Phase-1 is strictly limited to a **training-free ToolClaw prototype**.

In this phase, we do **not** perform any of the following:
- supervised fine-tuning
- reinforcement learning
- preference optimization
- model editing
- parameter updates of any kind
- automatic skill evolution or self-improving training loops

All Phase-1 improvements must come purely from **system-level workflow intelligence** on top of frozen base models and existing tools.

## What Phase-1 focuses on

Phase-1 only evaluates whether an explicit workflow intelligence layer can improve tool-use reliability in complex tasks through:
- structured workflow planning
- capability-to-tool binding
- policy-aware execution control
- interaction-driven correction
- runtime recovery
- traceable execution and reusable artifact extraction

## What Phase-1 does not claim

Phase-1 does not claim:
- better intrinsic model reasoning
- better tool-use due to training
- better performance due to model adaptation
- autonomous skill evolution
- end-to-end learned workflow policies

Instead, Phase-1 isolates the contribution of **ToolClaw as a workflow intelligence layer**.

## Deliverables

The expected deliverables of Phase-1 are:
1. a runnable training-free prototype
2. a unified workflow / trace / error / repair schema
3. baseline-vs-ToolClaw evaluation on selected benchmarks
4. execution traces and failure/recovery reports
5. a clear decision on whether Phase-2 training is necessary

## One-line repo disclaimer

**Phase-1 only: training-free prototype. No fine-tuning, RL, or parameter updates are included.**