#!/usr/bin/env bash
# Run a limited ToolSandbox core reproducible smoke via OpenRouter/Grok-3.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_PATH="${TOOLCLAW_PROFILE_PATH:-/cephfs/qiuyn/.profile}"
SMOKE_LIMIT="${TOOLSANDBOX_CORE_SMOKE_LIMIT:-10}"
OUT_PREFIX="${TOOLSANDBOX_CORE_SMOKE_OUT_PREFIX:-/tmp/toolclaw_toolsandbox_core_smoke/toolsandbox.official_core_reproducible.smoke}"
PY310_PREFIX="${TOOLSANDBOX_PY310_PREFIX:-/cephfs/qiuyn/venvs/toolsandbox-py310}"
OFFICIAL_VENV_DIR="${TOOLSANDBOX_OFFICIAL_VENV_DIR:-/cephfs/qiuyn/venvs/toolsandbox-official-py310}"
MODEL="${TOOLSANDBOX_OPENAI_MODEL:-x-ai/grok-3}"
BASE_URL="${OPENAI_BASE_URL:-https://openrouter.ai/api/v1}"

extract_openrouter_key() {
  python3 - "$PROFILE_PATH" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
for line in path.read_text(errors="ignore").splitlines():
    stripped = line.strip()
    if stripped.startswith("export OPENROUTER_API_KEY=") or stripped.startswith("OPENROUTER_API_KEY="):
        value = stripped.split("=", 1)[1].strip().strip("'\"")
        if value:
            print(value)
            raise SystemExit(0)
raise SystemExit(1)
PY
}

resolve_python_bin() {
  if [[ -n "${TOOLSANDBOX_PYTHON_BIN:-}" && -x "${TOOLSANDBOX_PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$TOOLSANDBOX_PYTHON_BIN"
  elif [[ -x "$PY310_PREFIX/bin/python" ]]; then
    printf '%s\n' "$PY310_PREFIX/bin/python"
  else
    printf '%s\n' "$PY310_PREFIX/bin/python"
  fi
}

main() {
  if [[ "${TOOLSANDBOX_SKIP_BOOTSTRAP:-0}" != "1" ]]; then
    "$ROOT_DIR/scripts/bootstrap_toolsandbox_py310_env.sh"
  fi

  local key
  if ! key="$(extract_openrouter_key)"; then
    echo "OPENROUTER_API_KEY not found in $PROFILE_PATH" >&2
    exit 2
  fi

  local python_bin
  python_bin="$(resolve_python_bin)"
  mkdir -p "$(dirname "$OUT_PREFIX")"

  echo "[smoke] ToolClaw commit: $(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"
  echo "[smoke] ToolSandbox commit: $(git -C "$ROOT_DIR/data/external/ToolSandbox" rev-parse HEAD 2>/dev/null || true)"
  echo "[smoke] Python: $python_bin ($($python_bin -V 2>&1))"
  echo "[smoke] OpenRouter-compatible endpoint: $BASE_URL"
  echo "[smoke] Model: $MODEL"
  echo "[smoke] Out prefix: $OUT_PREFIX"
  echo "[smoke] Limit: $SMOKE_LIMIT"

  OPENAI_API_KEY="$key" \
  OPENAI_BASE_URL="$BASE_URL" \
  OPENAI_API_BASE="$BASE_URL" \
  TOOLCLAW_BENCHMARK_PROXY_PROVIDER="openrouter" \
  TOOLCLAW_BENCHMARK_PROXY_FORCE="1" \
  TOOLSANDBOX_OPENAI_MODEL="$MODEL" \
  PYTHON_BIN="$python_bin" \
  TOOLSANDBOX_VENV_DIR="$OFFICIAL_VENV_DIR" \
  PYTHONPATH=src \
  python3 "$ROOT_DIR/scripts/export_toolsandbox_core_reproducible.py" \
    --execute \
    --limit "$SMOKE_LIMIT" \
    --out-prefix "$OUT_PREFIX"

  PYTHONPATH=src python3 "$ROOT_DIR/scripts/validate_toolsandbox_core_export.py" \
    --export "$OUT_PREFIX.json" \
    --manifest "$OUT_PREFIX.manifest.json" \
    --allow-smoke
}

main "$@"
