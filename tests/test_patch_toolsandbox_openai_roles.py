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

    def model_inference(self, openai_messages, openai_tools):
        with all_logging_disabled():
            return self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                tools=openai_tools,
            )
"""
    updated, changed = patch_role_content(original)

    assert changed is True
    assert "import os" in updated
    assert 'api_key=os.getenv("OPENAI_API_KEY")' in updated
    assert 'base_url=os.getenv("OPENAI_BASE_URL")' in updated
    assert 'or os.getenv("OPENAI_API_BASE")' in updated
    assert 'or "https://api.openai.com/v1"' in updated
    assert 'os.getenv("TOOLSANDBOX_OPENAI_MODEL")' in updated
    assert "or os.getenv(\"OPENAI_MODEL\")" in updated
    assert "or self.model_name" in updated
    assert "\n                model=self.model_name,\n" not in updated


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

    def model_inference(self, openai_messages, openai_tools):
        with all_logging_disabled():
            return self.openai_client.chat.completions.create(
                model=(
                    os.getenv("TOOLSANDBOX_OPENAI_MODEL")
                    or os.getenv("OPENAI_MODEL")
                    or self.model_name
                ),
                messages=openai_messages,
                tools=openai_tools,
            )
"""
    updated, changed = patch_role_content(patched)
    assert changed is False
    assert updated == patched


def test_patch_role_content_handles_typed_openai_client_field() -> None:
    original = """from openai import OpenAI

class Demo:
    def __init__(self) -> None:
        self.openai_client: OpenAI = OpenAI(base_url="https://api.openai.com/v1")

    def model_inference(self, openai_messages, openai_tools):
        return self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            tools=openai_tools,
        )
"""
    updated, changed = patch_role_content(original)
    assert changed is True
    assert "self.openai_client: OpenAI = OpenAI(" in updated
    assert 'os.getenv("TOOLSANDBOX_OPENAI_MODEL")' in updated


def test_patch_role_content_adds_model_override_when_client_already_patched() -> None:
    client_only = """import os
from openai import OpenAI

class Demo:
    def __init__(self) -> None:
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1",
        )

    def model_inference(self, openai_messages, openai_tools):
        return self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            tools=openai_tools,
        )
"""
    updated, changed = patch_role_content(client_only)
    assert changed is True
    assert 'os.getenv("TOOLSANDBOX_OPENAI_MODEL")' in updated
    assert "model=self.model_name," not in updated
