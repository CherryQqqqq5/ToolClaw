from toolclaw.benchmarks.proxy_env import benchmark_proxy_env


def test_benchmark_proxy_defaults_to_novacode() -> None:
    env = benchmark_proxy_env({})
    assert env["TOOLCLAW_BENCHMARK_PROXY_ACTIVE"] == "novacode"
    assert env["OPENAI_BASE_URL"] == "https://ai.novacode.top/v1"
    assert env["OPENAI_API_BASE"] == "https://ai.novacode.top/v1"
    assert env["TOOLSANDBOX_OPENAI_MODEL"] == "gpt-5.4"
    assert env["TOOLSANDBOX_NOVACODE_MODEL"] == "gpt-5.4"


def test_benchmark_proxy_supports_openrouter_provider() -> None:
    env = benchmark_proxy_env({"TOOLCLAW_BENCHMARK_PROXY_PROVIDER": "openrouter"})
    assert env["TOOLCLAW_BENCHMARK_PROXY_ACTIVE"] == "openrouter"
    assert env["OPENAI_BASE_URL"] == "https://openrouter.ai/api/v1"
    assert env["TOOLSANDBOX_OPENAI_MODEL"] == "x-ai/grok-3"
    assert env["TOOLSANDBOX_OPENROUTER_MODEL"] == "x-ai/grok-3"


def test_benchmark_proxy_respects_explicit_openai_base_url() -> None:
    env = benchmark_proxy_env(
        {
            "TOOLCLAW_BENCHMARK_PROXY_PROVIDER": "novacode",
            "OPENAI_BASE_URL": "https://custom.example/v1",
        }
    )
    assert env["OPENAI_BASE_URL"] == "https://custom.example/v1"
    assert env["OPENAI_API_BASE"] == "https://custom.example/v1"


def test_benchmark_proxy_allows_direct_mode() -> None:
    env = benchmark_proxy_env({"TOOLCLAW_BENCHMARK_PROXY_PROVIDER": "direct"})
    assert env["TOOLCLAW_BENCHMARK_PROXY_ACTIVE"] == "direct"
    assert "OPENAI_BASE_URL" not in env
    assert "OPENAI_API_BASE" not in env


def test_benchmark_proxy_force_overrides_explicit_openai_base() -> None:
    env = benchmark_proxy_env(
        {
            "TOOLCLAW_BENCHMARK_PROXY_PROVIDER": "novacode",
            "TOOLCLAW_BENCHMARK_PROXY_FORCE": "1",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_API_BASE": "https://api.openai.com/v1",
        }
    )
    assert env["TOOLCLAW_BENCHMARK_PROXY_ACTIVE"] == "novacode"
    assert env["OPENAI_BASE_URL"] == "https://ai.novacode.top/v1"
    assert env["OPENAI_API_BASE"] == "https://ai.novacode.top/v1"
