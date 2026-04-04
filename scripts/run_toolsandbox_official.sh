#!/usr/bin/env bash
# Bootstrap and run the official ToolSandbox CLI from the vendored repo.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLSANDBOX_DIR="${TOOLSANDBOX_DIR:-$ROOT_DIR/data/external/ToolSandbox}"
VENV_DIR="${TOOLSANDBOX_VENV_DIR:-$TOOLSANDBOX_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ONLY=0

usage() {
  cat >&2 <<'EOF'
usage: scripts/run_toolsandbox_official.sh [--install-only] [official-tool-sandbox-args...]

This wrapper bootstraps the vendored official ToolSandbox repo under:
  data/external/ToolSandbox

Examples:
  scripts/run_toolsandbox_official.sh --test_mode
  OPENAI_API_KEY=... RAPID_API_KEY=... scripts/run_toolsandbox_official.sh --agent GPT_4_o_2024_05_13 --user GPT_4_o_2024_05_13
  OPENAI_API_KEY=... scripts/run_toolsandbox_official.sh --agent GPT_4_o_2024_05_13 --user GPT_4_o_2024_05_13 --scenarios wifi_off

Notes:
  - The first run creates .venv under the official ToolSandbox repo and installs dependencies.
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

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "creating ToolSandbox virtualenv at: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [[ ! -x "$VENV_DIR/bin/tool_sandbox" ]]; then
  echo "installing official ToolSandbox dependencies into: $VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  (
    cd "$TOOLSANDBOX_DIR"
    "$VENV_DIR/bin/pip" install -e '.[dev]'
  )
fi

if [[ "$INSTALL_ONLY" -eq 1 ]]; then
  echo "ToolSandbox environment is ready:"
  echo "  repo: $TOOLSANDBOX_DIR"
  echo "  venv: $VENV_DIR"
  exit 0
fi

if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(--test_mode)
fi

exec "$VENV_DIR/bin/tool_sandbox" "${ARGS[@]}"
