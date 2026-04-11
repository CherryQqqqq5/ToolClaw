import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "find_openrouter_grok3_slug.py"
SPEC = importlib.util.spec_from_file_location("find_openrouter_grok3_slug", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_filter_grok3_candidates_prefers_tool_capable_slug() -> None:
    models = [
        {
            "id": "x-ai/grok-3-mini",
            "supported_parameters": ["tools", "max_tokens"],
            "architecture": {"input_modalities": ["text"]},
        },
        {
            "id": "x-ai/grok-2-vision",
            "supported_parameters": ["tools"],
            "architecture": {"input_modalities": ["text", "image"]},
        },
        {
            "id": "x-ai/grok-3-beta",
            "supported_parameters": ["max_tokens"],
            "architecture": {"input_modalities": ["text"]},
        },
    ]

    filtered = MODULE.filter_grok3_candidates(models)

    assert [item["id"] for item in filtered] == ["x-ai/grok-3-mini", "x-ai/grok-3-beta"]


def test_preferred_candidate_uses_successful_probe_before_first_candidate() -> None:
    candidates = [
        {"id": "x-ai/grok-3-fast"},
        {"id": "x-ai/grok-3"},
    ]
    probes = [
        {"model": "x-ai/grok-3-fast", "overall_status": "TOOL_CALLING_UNSUPPORTED", "tools": {"status": "TOOL_CALLING_UNSUPPORTED"}},
        {"model": "x-ai/grok-3", "overall_status": "OK", "tools": {"status": "OK"}},
    ]

    selected = MODULE.preferred_candidate(candidates, probes)

    assert selected == "x-ai/grok-3"
