#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKSET="${1:-$ROOT_DIR/data/eval_tasks.sample.json}"
OUTROOT="${2:-$ROOT_DIR/outputs/ablation}"
REUSE_TASKSET="${3:-$TASKSET}"
SYSTEMS="${4:-a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse}"

mkdir -p "$OUTROOT"

"$ROOT_DIR/scripts/run_eval.sh" "$TASKSET" "$OUTROOT/matrix" "$SYSTEMS" planner

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT_DIR/scripts/run_reuse_experiment.py" \
  --taskset "$REUSE_TASKSET" \
  --outdir "$OUTROOT/reuse" \
  --systems "a3_interaction,a4_reuse"

echo "matrix: $OUTROOT/matrix"
echo "reuse: $OUTROOT/reuse"
