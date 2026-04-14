#!/usr/bin/env python3
"""Patch ToolSandbox OpenAI role files for proxy / OpenRouter runs.

- Replaces the hard-coded OpenAI client with ``OPENAI_API_KEY`` + ``OPENAI_BASE_URL`` /
  ``OPENAI_API_BASE`` (OpenAI-compatible gateways such as OpenRouter).
- Replaces ``model=self.model_name`` in ``chat.completions.create`` with an env override:
  ``TOOLSANDBOX_OPENAI_MODEL`` or ``OPENAI_MODEL``, falling back to the ToolSandbox class
  attribute (e.g. ``gpt-4o-2024-05-13`` for ``GPT_4_o_2024_05_13_Agent``).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

TARGET_FILES = (
    Path("tool_sandbox/roles/openai_api_agent.py"),
    Path("tool_sandbox/roles/openai_api_user.py"),
)

# Upstream Apple ToolSandbox uses an optional type annotation on the client field.
CLIENT_PATTERN = re.compile(
    r'^(?P<indent>\s*)self\.openai_client(?P<ann>:\s*OpenAI)?\s*=\s*OpenAI\(base_url="https://api\.openai\.com/v1"\)\s*$',
    flags=re.MULTILINE,
)

MODEL_PATTERN = re.compile(r"^(?P<indent>\s*)model=self\.model_name,\s*$", flags=re.MULTILINE)

MODEL_OVERRIDE_MARKER = 'os.getenv("TOOLSANDBOX_OPENAI_MODEL")'


def _ensure_import_os(content: str) -> str:
    if re.search(r"^import os$", content, flags=re.MULTILINE):
        return content

    import_block = list(re.finditer(r"^(?:from\s+\S+\s+import\s+.+|import\s+.+)$", content, flags=re.MULTILINE))
    if not import_block:
        return "import os\n" + content
    insert_at = import_block[-1].end()
    return content[:insert_at] + "\nimport os" + content[insert_at:]


def _repl_client(match: re.Match[str]) -> str:
    indent = match.group("indent")
    ann = match.group("ann") or ""
    return (
        f"{indent}self.openai_client{ann} = OpenAI(\n"
        f'{indent}    api_key=os.getenv("OPENAI_API_KEY"),\n'
        f'{indent}    base_url=os.getenv("OPENAI_BASE_URL")\n'
        f'{indent}    or os.getenv("OPENAI_API_BASE")\n'
        f'{indent}    or "https://api.openai.com/v1",\n'
        f"{indent})"
    )


def _repl_model(match: re.Match[str]) -> str:
    indent = match.group("indent")
    inner = indent + "    "
    return (
        f"{indent}model=(\n"
        f'{inner}os.getenv("TOOLSANDBOX_OPENAI_MODEL")\n'
        f'{inner}or os.getenv("OPENAI_MODEL")\n'
        f"{inner}or self.model_name\n"
        f"{indent}),\n"
    )


def patch_role_content(content: str) -> tuple[str, bool]:
    will_patch_client = CLIENT_PATTERN.search(content) is not None
    will_patch_model = MODEL_OVERRIDE_MARKER not in content and MODEL_PATTERN.search(content) is not None

    if not will_patch_client and not will_patch_model:
        return content, False

    updated = _ensure_import_os(content)
    if will_patch_client:
        updated, n = CLIENT_PATTERN.subn(_repl_client, updated, count=1)
        if n != 1:
            return content, False
    if will_patch_model:
        updated, n = MODEL_PATTERN.subn(_repl_model, updated)
        if n < 1:
            return content, False

    return updated, updated != content


def patch_role_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated, _ = patch_role_content(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Path to ToolSandbox repo root")
    args = parser.parse_args()

    changed_files = 0
    for relpath in TARGET_FILES:
        path = args.root / relpath
        if not path.exists():
            print(f"skip (missing): {path}")
            continue
        if patch_role_file(path):
            changed_files += 1
            print(f"patched: {path}")
        else:
            print(f"ok (already patched or pattern missing): {path}")

    print(f"ToolSandbox role patch complete. changed_files={changed_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
