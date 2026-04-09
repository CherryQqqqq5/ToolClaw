#!/usr/bin/env bash
# Bootstrap and run the official ToolSandbox CLI from the vendored repo.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLSANDBOX_DIR="${TOOLSANDBOX_DIR:-$ROOT_DIR/data/external/ToolSandbox}"
VENV_DIR="${TOOLSANDBOX_VENV_DIR:-$TOOLSANDBOX_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ONLY=0
USE_ACTIVE_ENV="${TOOLSANDBOX_USE_ACTIVE_ENV:-0}"
FORCE_REINSTALL="${TOOLSANDBOX_FORCE_REINSTALL:-0}"
PIP_MAX_RETRIES="${TOOLSANDBOX_PIP_MAX_RETRIES:-3}"
PIP_RETRY_DELAY_SECONDS="${TOOLSANDBOX_PIP_RETRY_DELAY_SECONDS:-3}"
INSTALL_TARGET="${TOOLSANDBOX_INSTALL_TARGET:-.}"

usage() {
  cat >&2 <<'EOF'
usage: scripts/run_toolsandbox_official.sh [--install-only] [--use-active-env] [--force-reinstall] [official-tool-sandbox-args...]

This wrapper bootstraps the vendored official ToolSandbox repo under:
  data/external/ToolSandbox

Examples:
  scripts/run_toolsandbox_official.sh --test_mode
  conda activate tooluse && scripts/run_toolsandbox_official.sh --use-active-env --install-only
  OPENAI_API_KEY=... RAPID_API_KEY=... scripts/run_toolsandbox_official.sh --agent GPT_4_o_2024_05_13 --user GPT_4_o_2024_05_13
  OPENAI_API_KEY=... scripts/run_toolsandbox_official.sh --agent GPT_4_o_2024_05_13 --user GPT_4_o_2024_05_13 --scenarios wifi_off

Notes:
  - By default the first run creates .venv under the official ToolSandbox repo and installs dependencies.
  - Default installs runtime dependencies only. Set TOOLSANDBOX_INSTALL_TARGET='.[dev]' to include upstream dev extras.
  - --use-active-env installs into the currently active Python/conda environment instead of creating a venv.
  - If python -m venv fails, the script falls back to python -m virtualenv when possible.
  - API keys still need to be provided via environment variables as required by the selected agent/user roles.
EOF
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --install-only)
      INSTALL_ONLY=1
      shift
      ;;
    --use-active-env)
      USE_ACTIVE_ENV=1
      shift
      ;;
    --force-reinstall)
      FORCE_REINSTALL=1
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ! -d "$TOOLSANDBOX_DIR" ]]; then
  echo "official ToolSandbox repo not found: $TOOLSANDBOX_DIR" >&2
  echo "expected clone location: data/external/ToolSandbox" >&2
  exit 1
fi

resolve_python_bin() {
  if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    printf '%s\n' "$PYTHON_BIN"
    return 0
  fi
  if [[ "$PYTHON_BIN" != "python" ]] && command -v python >/dev/null 2>&1; then
    printf '%s\n' "python"
    return 0
  fi
  echo "python executable not found: $PYTHON_BIN" >&2
  return 1
}

module_available() {
  local python_exec="$1"
  "$python_exec" - <<'PY' >/dev/null 2>&1
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("tool_sandbox.cli") else 1)
PY
}

install_into_python() {
  local python_exec="$1"
  echo "installing official ToolSandbox dependencies using: $python_exec"
  echo "install target: -e $INSTALL_TARGET"
  pip_install_with_retry "$python_exec" install --upgrade pip
  (
    cd "$TOOLSANDBOX_DIR"
    pip_install_with_retry "$python_exec" install -e "$INSTALL_TARGET"
  )
}

pip_install_with_retry() {
  local python_exec="$1"
  shift
  local attempt=1
  local exit_code=0

  while (( attempt <= PIP_MAX_RETRIES )); do
    if (( attempt > 1 )); then
      local wait_seconds=$(( PIP_RETRY_DELAY_SECONDS * (attempt - 1) ))
      echo "pip install retry ${attempt}/${PIP_MAX_RETRIES} in ${wait_seconds}s..." >&2
      sleep "$wait_seconds"
    fi

    if "$python_exec" -m pip --retries 10 --timeout 120 "$@"; then
      return 0
    fi

    exit_code=$?
    echo "pip command failed on attempt ${attempt}/${PIP_MAX_RETRIES} (exit=${exit_code})." >&2
    attempt=$((attempt + 1))
  done

  return "$exit_code"
}

create_venv() {
  local python_exec="$1"
  echo "creating ToolSandbox virtualenv at: $VENV_DIR"
  if "$python_exec" -m venv "$VENV_DIR"; then
    return 0
  fi
  echo "python -m venv failed; attempting virtualenv fallback" >&2
  pip_install_with_retry "$python_exec" install --upgrade pip
  pip_install_with_retry "$python_exec" install virtualenv
  "$python_exec" -m virtualenv "$VENV_DIR"
}

PYTHON_EXEC="$(resolve_python_bin)"
RUN_PYTHON=""
ENV_LABEL=""

if [[ "$USE_ACTIVE_ENV" == "1" ]]; then
  RUN_PYTHON="$PYTHON_EXEC"
  ENV_LABEL="${CONDA_PREFIX:-active_python_env}"
  if [[ "$FORCE_REINSTALL" == "1" ]] || ! module_available "$RUN_PYTHON"; then
    install_into_python "$RUN_PYTHON"
  fi
else
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    create_venv "$PYTHON_EXEC"
  fi
  RUN_PYTHON="$VENV_DIR/bin/python"
  ENV_LABEL="$VENV_DIR"
  if [[ "$FORCE_REINSTALL" == "1" ]] || ! module_available "$RUN_PYTHON"; then
    install_into_python "$RUN_PYTHON"
  fi
fi

if [[ "$INSTALL_ONLY" -eq 1 ]]; then
  echo "ToolSandbox environment is ready:"
  echo "  repo: $TOOLSANDBOX_DIR"
  if [[ "$USE_ACTIVE_ENV" == "1" ]]; then
    echo "  python_env: $ENV_LABEL"
  else
    echo "  venv: $ENV_LABEL"
  fi
  echo "  python: $RUN_PYTHON"
  exit 0
fi

if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(--test_mode)
fi

exec "$RUN_PYTHON" -c 'import sys; from tool_sandbox.cli import main; sys.argv = ["tool_sandbox", *sys.argv[1:]]; main()' "${ARGS[@]}"
