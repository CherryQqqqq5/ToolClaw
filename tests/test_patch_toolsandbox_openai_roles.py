from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_patch_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "patch_toolsandbox_openai_roles.py"
    spec = importlib.util.spec_from_file_location("patch_toolsandbox_openai_roles", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


patch_role_content = _load_patch_module().patch_role_content


def test_patch_role_content_rewrites_openai_client_and_adds_import() -> None:
    original = """from openai import OpenAI

class Demo:
    def __init__(self) -> None:
        self.openai_client = OpenAI(base_url="https://api.openai.com/v1")
"""
    updated, changed = patch_role_content(original)

    assert changed is True
    assert "import os" in updated
    assert 'api_key=os.getenv("OPENAI_API_KEY")' in updated
    assert 'base_url=os.getenv("OPENAI_BASE_URL")' in updated
    assert 'or os.getenv("OPENAI_API_BASE")' in updated
    assert 'or "https://api.openai.com/v1"' in updated


def test_patch_role_content_is_idempotent() -> None:
    patched = """import os
from openai import OpenAI

class Demo:
    def __init__(self) -> None:
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1",
        )
"""
    updated, changed = patch_role_content(patched)
    assert changed is False
    assert updated == patched
