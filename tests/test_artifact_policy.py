from scripts.check_artifact_policy import classify_artifact_path


def assert_allowed(path: str) -> None:
    result = classify_artifact_path(path)
    assert result.allowed, result


def assert_rejected(path: str, reason: str) -> None:
    result = classify_artifact_path(path)
    assert result.allowed is False, result
    assert result.reason == reason


def test_artifact_policy_allows_release_summaries() -> None:
    assert_allowed("outputs/paper_freeze/manifest.json")
    assert_allowed("outputs/paper_freeze/scoreboard.json")
    assert_allowed("outputs/paper_freeze/report.md")
    assert_allowed("outputs/paper_freeze/planner_sensitive_summary.md")


def test_artifact_policy_rejects_output_traces_and_run_subtrees() -> None:
    assert_rejected("outputs/paper_freeze/trace.jsonl", "trace_artifact_must_stay_external")
    assert_rejected("outputs/paper_freeze/runs/run_001/messages.jsonl", "bulky_output_subtree")
    assert_rejected("outputs/paper_freeze/prepared/toolsandbox.normalized.json", "bulky_output_subtree")
    assert_rejected("outputs/paper_freeze/comparison.raw.csv", "output_artifact_requires_summary_allowlist")


def test_artifact_policy_rejects_logs_and_local_data_cache() -> None:
    assert_rejected("logs/run.log", "logs_must_stay_external")
    assert_rejected("data/tmp/toolsandbox.jsonl", "local_data_cache")
    assert_rejected("data/cache/bfcl.parquet", "local_data_cache")


def test_artifact_policy_rejects_new_external_benchmark_artifacts() -> None:
    assert_allowed("data/external/README.md")
    assert_allowed("data/external/manifest.json")
    assert_rejected("data/external/ToolSandbox/archive.tar.gz", "external_benchmark_artifact")


def test_artifact_policy_rejects_common_generated_noise() -> None:
    assert_rejected("src/toolclaw/__pycache__/admission.cpython-312.pyc", "python_cache")
    assert_rejected("outputs/paper_freeze/._manifest.json", "macos_metadata")
