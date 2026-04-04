#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKSET="${1:-$ROOT_DIR/data/eval_tasks.sample.json}"
OUTDIR="${2:-$ROOT_DIR/outputs/eval}"
SYSTEMS="${3:-a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse}"
MODE="${4:-planner}"

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT_DIR/scripts/run_eval.py" \
  --taskset "$TASKSET" \
  --outdir "$OUTDIR" \
  --systems "$SYSTEMS" \
  --mode "$MODE"
