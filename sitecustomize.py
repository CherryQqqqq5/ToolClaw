"""Project-local import bootstrap.

When running Python from the repository root, automatically expose `src/` so
`import toolclaw` works without needing PYTHONPATH exports.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
