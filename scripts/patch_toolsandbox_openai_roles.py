#!/usr/bin/env python3
"""Patch ToolSandbox OpenAI role files to respect env-configured base URLs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

TARGET_FILES = (
    Path("tool_sandbox/roles/openai_api_agent.py"),
    Path("tool_sandbox/roles/openai_api_user.py"),
)

OLD_CLIENT_LINE = 'self.openai_client = OpenAI(base_url="https://api.openai.com/v1")'


def _ensure_import_os(content: str) -> str:
    if re.search(r"^import os$", content, flags=re.MULTILINE):
        return content

    import_block = list(re.finditer(r"^(?:from\s+\S+\s+import\s+.+|import\s+.+)$", content, flags=re.MULTILINE))
    if not import_block:
        return "import os\n" + content
    insert_at = import_block[-1].end()
    return content[:insert_at] + "\nimport os" + content[insert_at:]


def patch_role_content(content: str) -> tuple[str, bool]:
    if "os.getenv(\"OPENAI_BASE_URL\")" in content and "os.getenv(\"OPENAI_API_BASE\")" in content:
        return content, False

    content = _ensure_import_os(content)

    pattern = re.compile(
        r'^(?P<indent>\s*)self\.openai_client = OpenAI\(base_url="https://api\.openai\.com/v1"\)\s*$',
        flags=re.MULTILINE,
    )

    def repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        return (
            f'{indent}self.openai_client = OpenAI(\n'
            f'{indent}    api_key=os.getenv("OPENAI_API_KEY"),\n'
            f'{indent}    base_url=os.getenv("OPENAI_BASE_URL")\n'
            f'{indent}    or os.getenv("OPENAI_API_BASE")\n'
            f'{indent}    or "https://api.openai.com/v1",\n'
            f"{indent})"
        )

    updated, count = pattern.subn(repl, content, count=1)
    return updated, count > 0


def patch_role_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated, changed = patch_role_content(original)
    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed


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
