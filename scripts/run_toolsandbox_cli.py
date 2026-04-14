#!/usr/bin/env python3
"""ToolSandbox entrypoint that routes interaction to user CLI."""

from __future__ import annotations

import sys

from run_toolsandbox_bench import main


def _ensure_cli_interaction_target(argv: list[str]) -> list[str]:
    has_target = any(arg.startswith("--interaction-target") for arg in argv)
    if has_target:
        return argv
    return [*argv, "--interaction-target", "user_cli"]


if __name__ == "__main__":
    sys.argv = _ensure_cli_interaction_target(sys.argv)
    main()
