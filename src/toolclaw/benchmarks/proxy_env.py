"""Benchmark LLM proxy environment helpers.

Defaults benchmark-related OpenAI-compatible traffic to a relay endpoint so
runs do not hit the public OpenAI base URL directly.
"""

from __future__ import annotations

import os
from typing import Mapping

DEFAULT_NOVACODE_BASE_URL = "https://ai.novacode.top/v1"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_NOVACODE_MODEL = "gpt-5.4"
DEFAULT_OPENROUTER_MODEL = "x-ai/grok-3"


def _normalized_provider(value: str | None) -> str:
    raw = str(value or "novacode").strip().lower()
    aliases = {
        "nova": "novacode",
        "novacode": "novacode",
        "openrouter": "openrouter",
        "router": "openrouter",
        "custom": "custom",
        "direct": "direct",
        "openai": "direct",
    }
    return aliases.get(raw, "custom")


def benchmark_proxy_env(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return env with benchmark proxy defaults applied.

    Precedence:
      1) Explicit OPENAI_BASE_URL / OPENAI_API_BASE in current env.
      2) TOOLCLAW_BENCHMARK_PROXY_BASE_URL when provider=custom.
      3) Provider defaults (novacode/openrouter).
    """

    env = dict(os.environ if base_env is None else base_env)
    provider = _normalized_provider(env.get("TOOLCLAW_BENCHMARK_PROXY_PROVIDER"))
    force_proxy = str(env.get("TOOLCLAW_BENCHMARK_PROXY_FORCE", "")).strip().lower() in {"1", "true", "yes", "on"}

    if provider == "direct":
        env["TOOLCLAW_BENCHMARK_PROXY_ACTIVE"] = "direct"
        return env

    chosen_base_url = env.get("TOOLCLAW_BENCHMARK_PROXY_BASE_URL", "").strip()
    if provider == "novacode":
        chosen_base_url = chosen_base_url or env.get("TOOLCLAW_BENCHMARK_NOVACODE_BASE_URL", DEFAULT_NOVACODE_BASE_URL)
        env.setdefault("TOOLSANDBOX_OPENAI_MODEL", env.get("TOOLSANDBOX_NOVACODE_MODEL", DEFAULT_NOVACODE_MODEL))
        env.setdefault("TOOLSANDBOX_NOVACODE_MODEL", DEFAULT_NOVACODE_MODEL)
    elif provider == "openrouter":
        chosen_base_url = chosen_base_url or env.get("TOOLCLAW_BENCHMARK_OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)
        env.setdefault("TOOLSANDBOX_OPENAI_MODEL", env.get("TOOLSANDBOX_OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL))
        env.setdefault("TOOLSANDBOX_OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)

    chosen_base_url = chosen_base_url.strip()
    openai_base_url = env.get("OPENAI_BASE_URL", "").strip()
    openai_api_base = env.get("OPENAI_API_BASE", "").strip()

    if force_proxy and chosen_base_url:
        env["OPENAI_BASE_URL"] = chosen_base_url
        env["OPENAI_API_BASE"] = chosen_base_url
    elif openai_base_url and not openai_api_base:
        env["OPENAI_API_BASE"] = openai_base_url
    elif openai_api_base and not openai_base_url:
        env["OPENAI_BASE_URL"] = openai_api_base
    elif chosen_base_url:
        env.setdefault("OPENAI_BASE_URL", chosen_base_url)
        env.setdefault("OPENAI_API_BASE", chosen_base_url)

    env["TOOLCLAW_BENCHMARK_PROXY_ACTIVE"] = provider
    active_base_url = env.get("OPENAI_BASE_URL") or env.get("OPENAI_API_BASE") or chosen_base_url
    if active_base_url:
        env["TOOLCLAW_BENCHMARK_PROXY_BASE_URL_ACTIVE"] = active_base_url
    return env
