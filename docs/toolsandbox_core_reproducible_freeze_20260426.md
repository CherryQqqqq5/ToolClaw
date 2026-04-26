# ToolSandbox Core Reproducible Freeze - 2026-04-26

## Verdict

This is the first executed core-reproducible ToolSandbox frozen export. It supersedes the legacy 88-row frozen export as the source for future ToolSandbox headline experiments, but it does not itself contain a0-a4 benchmark results.

BFCL, reuse v3, paper headline wording, and claim matrix status are unchanged by this freeze.

## Source Inventory

- Official scenario inventory entries: 1032
- Core reproducible candidates: 405
- Core candidate policy: Python-native scenarios with tool allow lists, milestones, no external API requirement, and resolvable official scenario names
- Multi-label excluded reason counts:
  - `requires_external_api`: 523
  - `not_python_native`: 523
  - `missing_milestones`: 208
- Primary excluded reason counts:
  - `requires_external_api`: 523
  - `missing_milestones`: 104
- Excluded reason counting: multi-label non-exclusive
- ToolClaw commit: `9699bf630a01b00eeea94103cae9b8c77505f4c5`
- Official ToolSandbox commit: `165848b9a78cead7ca7fe7c89c688b58e6501219`
- ToolSandbox execution source includes a local OpenRouter client patch in `data/external/ToolSandbox` to honor `OPENAI_BASE_URL` / `OPENAI_API_BASE` and `TOOLSANDBOX_OPENAI_MODEL`.

## Execution

- Dataset status: `executed_core_export`
- Attempted scenarios: 405
- Result-summary scenarios: 405
- Trajectory count: 405
- Export rows: 405
- Failed scenarios: 0
- Failure reason counts: `{}`
- Limit applied: false
- Dry run: false
- `core_export_is_evidence`: true
- `result_summary.json`: present
- `trajectories/`: present

## Runtime Visibility

- Runtime visibility policy: `runtime_messages_only; full official transcript is scorer/provenance-only`
- `full_trajectory_messages_runtime_visible`: false
- `scorer_gold_runtime_visible`: false, as enforced by the strict core export validator
- `runtime_messages` are the runner/adapter-visible messages.
- Full official conversations are retained as scorer/provenance-only material and are not planner-visible.

## Environment

- ToolSandbox bootstrap Python: `/cephfs/qiuyn/venvs/toolsandbox-py310/bin/python`
- ToolSandbox bootstrap Python version: `3.10.20`
- ToolSandbox runtime Python: `/cephfs/qiuyn/venvs/toolsandbox-official-py310/bin/python`
- ToolSandbox runtime Python version: `3.10.20`
- ToolClaw Python: `/usr/bin/python3`
- ToolClaw Python version: `3.8.10`
- `networkx` version: `3.2.1`
- Execution provider: OpenRouter-compatible OpenAI endpoint
- Model: `x-ai/grok-3`
- OpenAI-compatible base URL configured: true
- API key recorded in artifacts: false
- Pip freeze: `data/toolsandbox.official_core_reproducible.frozen.execution_pip_freeze.txt`

## Validation

Strict validator command:

```bash
PYTHONPATH=src python3 scripts/validate_toolsandbox_core_export.py \
  --export data/toolsandbox.official_core_reproducible.frozen.json \
  --manifest data/toolsandbox.official_core_reproducible.frozen.manifest.json
```

Validator result:

- `freeze_ready`: true
- `pipeline_valid`: true
- `error_count`: 0
- `warning_count`: 0

## Files

- Frozen export: `data/toolsandbox.official_core_reproducible.frozen.json`
- Frozen manifest: `data/toolsandbox.official_core_reproducible.frozen.manifest.json`
- Core filter: `data/toolsandbox.official_core_reproducible.frozen.core_filter.json`
- Pip freeze: `data/toolsandbox.official_core_reproducible.frozen.execution_pip_freeze.txt`
- Official run directory: `outputs/toolsandbox_core_reproducible_official_runs/agent_gpt-4o-2024-05-13_user_gpt-4o-2024-05-13_04_26_2026_18_51_29`
- Result summary: `outputs/toolsandbox_core_reproducible_official_runs/agent_gpt-4o-2024-05-13_user_gpt-4o-2024-05-13_04_26_2026_18_51_29/result_summary.json`
- Trajectory root: `outputs/toolsandbox_core_reproducible_official_runs/agent_gpt-4o-2024-05-13_user_gpt-4o-2024-05-13_04_26_2026_18_51_29/trajectories`
- Execution log: `outputs/toolclaw_logs/toolsandbox_core_reproducible_frozen_20260426T105022Z.log`

## Boundary

This frozen export is a core reproducible ToolSandbox subset, not the complete ToolSandbox scenario inventory. RapidAPI/external scenarios are excluded for reproducibility and tracked separately by the inventory and coverage audit.

This freeze establishes a valid source for future ToolSandbox core a0-a4 experiments. It does not report a0-a4 results, does not promote any paper claim, and does not change the status of reuse v3 or BFCL.
