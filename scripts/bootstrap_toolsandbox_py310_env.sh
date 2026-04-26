#!/usr/bin/env bash
# Prepare an isolated Python 3.10+ runtime for official ToolSandbox execution.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_ENV_PREFIX="${TOOLSANDBOX_PY310_PREFIX:-/cephfs/qiuyn/venvs/toolsandbox-py310}"
OFFICIAL_VENV_DIR="${TOOLSANDBOX_OFFICIAL_VENV_DIR:-/cephfs/qiuyn/venvs/toolsandbox-official-py310}"
MICROMAMBA_HOME="${TOOLSANDBOX_MICROMAMBA_HOME:-/cephfs/qiuyn/micromamba}"
MAMBA_ROOT_PREFIX="${TOOLSANDBOX_MAMBA_ROOT_PREFIX:-$MICROMAMBA_HOME/root}"
MICROMAMBA_URL="${TOOLSANDBOX_MICROMAMBA_URL:-https://micro.mamba.pm/api/micromamba/linux-64/latest}"
LOCAL_IO_ROOT="${TOOLCLAW_LOCAL_IO_ROOT:-/tmp/toolclaw_toolsandbox_py310}"

python_is_compatible() {
  local python_bin="$1"
  [[ -x "$python_bin" || -n "$(command -v "$python_bin" 2>/dev/null || true)" ]] || return 1
  "$python_bin" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

resolve_python() {
  local candidate
  for candidate in \
    "${TOOLSANDBOX_PYTHON_BIN:-}" \
    "$PY_ENV_PREFIX/bin/python" \
    "/cephfs/qiuyn/python311/bin/python" \
    "/cephfs/qiuyn/python310/bin/python" \
    "python3.11" \
    "python3.10"; do
    [[ -n "$candidate" ]] || continue
    if python_is_compatible "$candidate"; then
      command -v "$candidate" 2>/dev/null || printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

ensure_micromamba() {
  if command -v micromamba >/dev/null 2>&1; then
    command -v micromamba
    return 0
  fi
  if [[ -x "$MICROMAMBA_HOME/bin/micromamba" ]]; then
    printf '%s\n' "$MICROMAMBA_HOME/bin/micromamba"
    return 0
  fi
  mkdir -p "$MICROMAMBA_HOME"
  local tmp_archive
  tmp_archive="$(mktemp /tmp/toolclaw_micromamba.XXXXXX.tar.bz2)"
  echo "[bootstrap] downloading micromamba to $MICROMAMBA_HOME" >&2
  curl -L --fail --retry 3 --connect-timeout 20 "$MICROMAMBA_URL" -o "$tmp_archive"
  tar -xjf "$tmp_archive" -C "$MICROMAMBA_HOME" bin/micromamba
  rm -f "$tmp_archive"
  printf '%s\n' "$MICROMAMBA_HOME/bin/micromamba"
}

ensure_python310_env() {
  if python_is_compatible "$PY_ENV_PREFIX/bin/python"; then
    printf '%s\n' "$PY_ENV_PREFIX/bin/python"
    return 0
  fi
  local micromamba_bin
  micromamba_bin="$(ensure_micromamba)"
  mkdir -p "$(dirname "$PY_ENV_PREFIX")" "$MAMBA_ROOT_PREFIX"
  echo "[bootstrap] creating Python 3.10 environment at $PY_ENV_PREFIX" >&2
  MAMBA_ROOT_PREFIX="$MAMBA_ROOT_PREFIX" "$micromamba_bin" create -y -p "$PY_ENV_PREFIX" python=3.10 pip >&2
  printf '%s\n' "$PY_ENV_PREFIX/bin/python"
}

main() {
  local python_bin
  if ! python_bin="$(resolve_python)"; then
    python_bin="$(ensure_python310_env)"
  fi
  if ! python_is_compatible "$python_bin"; then
    echo "resolved Python is not >=3.10: $python_bin" >&2
    exit 2
  fi

  echo "[bootstrap] ToolClaw repo: $ROOT_DIR"
  echo "[bootstrap] ToolClaw commit: $(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"
  echo "[bootstrap] ToolSandbox commit: $(git -C "$ROOT_DIR/data/external/ToolSandbox" rev-parse HEAD 2>/dev/null || true)"
  echo "[bootstrap] Python: $python_bin ($($python_bin -V 2>&1))"
  echo "[bootstrap] Official ToolSandbox venv: $OFFICIAL_VENV_DIR"

  PYTHON_BIN="$python_bin" \
  TOOLSANDBOX_VENV_DIR="$OFFICIAL_VENV_DIR" \
  TOOLCLAW_LOCAL_IO_ROOT="$LOCAL_IO_ROOT" \
  "$ROOT_DIR/scripts/run_toolsandbox_official.sh" --install-only
}

main "$@"
