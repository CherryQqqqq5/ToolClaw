"""Compatibility package shim.

Allows `import toolclaw` from repository root without setting PYTHONPATH by
including `src/toolclaw` in package search path.
"""

from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_src_pkg = _pkg_dir.parent / "src" / "toolclaw"

if _src_pkg.exists():
    __path__.append(str(_src_pkg))
