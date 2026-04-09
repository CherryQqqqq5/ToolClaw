# ToolClaw

ToolClaw is a **training-free workflow intelligence layer** for tool-calling agents.

This repository now tracks two milestones:
- `Phase-1 completed`: baseline vs recovery/planning/interaction/reuse scaffolding is implemented and reproducible.
- `Phase-2 in progress`: failure-taxonomy coverage, budget-aware policy, interaction efficiency, and second-run reuse are the active evaluation targets.

---


## Status

- ✅ Phase-1 completed: training-free prototype, core schemas, baseline/toolclaw harness, blocked-interaction resume loop, artifact compilation
- 🚧 Phase-2 in progress: FailTax-first benchmark slicing, state-failure coverage, modular interaction backends, budget sweeps, second-run reuse evaluation

---

## Repository Structure

```text
ToolClaw/
├── src/toolclaw/
│   ├── planner/              # HTGP planner, binder, capability graph builder
│   ├── execution/            # Sequential executor + recovery application
│   ├── interaction/          # Interaction shell, repair updater, user simulator
│   ├── compiler/             # SWPC compiler (trace -> reusable artifacts)
│   ├── benchmarks/           # baseline/toolclaw runners + metrics/report
│   ├── schemas/              # Python dataclass schemas
│   ├── tools/                # Mock tools and adapters
│   ├── registry.py           # In-memory asset registry
│   └── main.py               # ToolClawRuntime façade
├── docs/schemas/             # YAML schema docs
├── scripts/
│   ├── run_eval.py           # Main eval entrypoint (demo/planner modes)
│   ├── run_phase1.sh         # Phase-1 experiment entry
│   └── run_ablation.sh       # A3/A4 ablation entry
├── data/eval_tasks.sample.json
└── tests/
```

---

## Core Runtime Flow

### ToolClaw-lite path

1. **Planner** builds workflow from task/context (`HTGPPlanner.plan`).
2. **Executor** runs sequentially (`run_until_blocked`) and writes trace.
3. If recovery asks user, execution returns `blocked=True` with pending interaction.
4. **Interaction shell** builds query, gets reply from a configured backend (simulator / human / LLM), and resumes execution.
5. On success, **SWPC compiler** extracts reusable snippets and writes them to registry.

### Baseline path

- Runs the same workflow without recovery loop (first unrecoverable failure stops run).

---

## Quick Start

### 1) Run tests

```bash
pytest -q
```

### 2) Run one evaluation

```bash
scripts/run_phase1.sh data/eval_tasks.sample.json outputs/phase1 planner
```

Outputs:
- `outputs/phase1/comparison.csv`
- `outputs/phase1/report.md`
- `outputs/phase1/traces/*.json`

### 3) Run ablations (A3/A4)

```bash
scripts/run_ablation.sh data/eval_tasks.sample.json outputs/ablation
```

Outputs:
- `outputs/ablation/a3_demo_mode/*`
- `outputs/ablation/a4_planner_mode/*`

---

## Evaluation CLI

Main entrypoint:

```bash
python3 scripts/run_eval.py --taskset <path> --outdir <dir> [--mode demo|planner]
```

Arguments:
- `--taskset`: JSON list of task objects
- `--outdir`: output folder for traces/CSV/report
- `--mode`:
  - `planner` (default): planner-generated workflow path
  - `demo`: fixed `Workflow.demo()` path

---

## Taskset Format (sample)

`data/eval_tasks.sample.json` uses this shape:

```json
[
  {
    "task_id": "task_success_001",
    "scenario": "success",
    "query": "target document summary",
    "target_path": "outputs/reports/task_success_001.txt"
  },
  {
    "task_id": "task_env_001",
    "scenario": "environment_failure",
    "simulated_policy": {
      "mode": "cooperative",
      "missing_arg_values": {"target_path": "outputs/reports/recovered.txt"}
    }
  }
]
```

---

## Schemas

Schema docs are under `docs/schemas/`:
- `workflow.schema.yaml`
- `trace.schema.yaml`
- `error.schema.yaml`
- `repair.schema.yaml`

Python schema implementations are under `src/toolclaw/schemas/`.

---

## Current Status / Limits

Current emphasis:

- `Phase-1`: completed reduced claim on controlled tasksets
- `Phase-2`: expanding to selection / ordering / state / recovery coverage, stronger reply-to-patch compilation, budget-aware planning, and real interaction backends

---

## Development Notes

- Import path support:
  - tests use `tests/conftest.py` to expose `src/`
  - root-level convenience shim exists in `toolclaw/__init__.py`
- If you run scripts directly, prefer `PYTHONPATH=src` or shell scripts in `scripts/`.
