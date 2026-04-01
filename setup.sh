#!/usr/bin/env bash
# Install gpush and gpull into ~/.local/bin as symlinks to the repository scripts.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "$BIN_DIR"
ln -sf "$ROOT_DIR/gpush" "$BIN_DIR/gpush"
ln -sf "$ROOT_DIR/gpull" "$BIN_DIR/gpull"
chmod +x "$ROOT_DIR/gpush" "$ROOT_DIR/gpull" "$ROOT_DIR/scripts/git_helpers.sh"

echo "installed:"
echo "  $BIN_DIR/gpush -> $ROOT_DIR/gpush"
echo "  $BIN_DIR/gpull -> $ROOT_DIR/gpull"

case ":${PATH}:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo
    echo "note: $BIN_DIR is not in PATH."
    echo "add this line to your shell profile if needed:"
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac
