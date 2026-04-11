import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_openrouter_key.py"
SPEC = importlib.util.spec_from_file_location("check_openrouter_key", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_default_model_is_grok3() -> None:
    assert MODULE.DEFAULT_MODEL == "x-ai/grok-3"


def test_summarize_status_reports_success_for_both_mode() -> None:
    summary, exit_code = MODULE.summarize_status(
        {
            "models": {"status": "OK"},
            "basic": {"status": "OK"},
            "tools": {"status": "OK"},
        },
        "both",
    )

    assert summary == "OPENROUTER_KEY_OK_BOTH"
    assert exit_code == 0


def test_summarize_status_prioritizes_auth_error() -> None:
    summary, exit_code = MODULE.summarize_status(
        {
            "models": {"status": "AUTH_ERROR", "error": "401 invalid api key"},
            "basic": {"status": "SKIPPED"},
            "tools": {"status": "SKIPPED"},
        },
        "both",
    )

    assert summary == "AUTH_ERROR"
    assert exit_code == 10


def test_classify_error_detects_tool_calling_unsupported() -> None:
    status = MODULE.classify_error(Exception("tool calling is not supported for this model"))

    assert status == "TOOL_CALLING_UNSUPPORTED"
