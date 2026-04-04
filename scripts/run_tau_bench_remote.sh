#!/usr/bin/env bash
# Remote-friendly wrapper for tau-bench runs with smoke/full presets and logging.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:-}"
OUTDIR="${2:-$ROOT_DIR/outputs/tau_bench_remote}"
MODE="${3:-planner}"
SYSTEMS="${4:-a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse}"
RUN_KIND="${5:-smoke}" # smoke | full
NUM_RUNS="${6:-1}"

if [[ -z "$SOURCE" ]]; then
  echo "usage: scripts/run_tau_bench_remote.sh <tau_bench_source.json|jsonl> [outdir] [mode] [systems] [smoke|full] [num_runs]" >&2
  exit 1
fi

mkdir -p "$OUTDIR/logs" "$OUTDIR/prepared"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
export TOOLCLAW_REMOTE_RUN=1

LIMIT_ARGS=()
if [[ "$RUN_KIND" == "smoke" ]]; then
  LIMIT_ARGS+=(--smoke --limit 10)
fi

set -x
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_tau_bench.py" \
  --source "$SOURCE" \
  --outdir "$OUTDIR" \
  --mode "$MODE" \
  --systems "$SYSTEMS" \
  --num-runs "$NUM_RUNS" \
  "${LIMIT_ARGS[@]}" \
  2>&1 | tee "$OUTDIR/logs/run_tau_bench_remote.log"
set +x

echo "tau-bench remote run finished"
echo "comparison: $OUTDIR/comparison.csv"
echo "report: $OUTDIR/report.md"
echo "scoreboard: $OUTDIR/scoreboard.json"
echo "per-system summary: $OUTDIR/per_system_summary.json"
