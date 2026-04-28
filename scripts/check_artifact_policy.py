#!/usr/bin/env python3
"""Guard against adding bulky benchmark artifacts to the repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath


SUMMARY_FILENAMES = {
    "artifact_index.json",
    "audit_summary.json",
    "claim_summary.json",
    "experiment_manifest.json",
    "latest_run_report.md",
    "manifest.json",
    "per_system_summary.json",
    "report.md",
    "scoreboard.json",
}

OUTPUT_SUMMARY_SUFFIXES = (
    "per_category_summary.json",
    "per_category_summary.md",
    "per_failure_type_summary.json",
    "per_failure_type_summary.md",
    "planner_sensitive_summary.json",
    "planner_sensitive_summary.md",
    "reuse_effect_summary.json",
    "slice_summary.json",
)

REJECTED_OUTPUT_PARTS = {"archive", "prepared", "raw", "runs", "traces"}
REJECTED_DATA_EXTERNAL_FILENAMES = {".DS_Store", "._.DS_Store"}


@dataclass(frozen=True)
class ArtifactPolicyResult:
    path: str
    allowed: bool
    reason: str


def _normalize_path(path: str) -> PurePosixPath:
    return PurePosixPath(path.replace("\\", "/"))


def _is_summary_file(path: PurePosixPath) -> bool:
    return path.name in SUMMARY_FILENAMES or path.name in OUTPUT_SUMMARY_SUFFIXES


def classify_artifact_path(path: str) -> ArtifactPolicyResult:
    normalized = _normalize_path(path)
    parts = normalized.parts
    path_s = normalized.as_posix()

    if normalized.name.startswith("._") or normalized.name == ".DS_Store":
        return ArtifactPolicyResult(path_s, False, "macos_metadata")
    if "__pycache__" in parts or normalized.suffix == ".pyc":
        return ArtifactPolicyResult(path_s, False, "python_cache")
    if not parts:
        return ArtifactPolicyResult(path_s, True, "non_artifact")

    if parts[0] == "logs":
        return ArtifactPolicyResult(path_s, False, "logs_must_stay_external")

    if parts[0] == "outputs":
        lowered_parts = {part.lower() for part in parts}
        if lowered_parts & REJECTED_OUTPUT_PARTS:
            return ArtifactPolicyResult(path_s, False, "bulky_output_subtree")
        if normalized.name.lower().startswith(("trace", "tool_trace", "messages")):
            return ArtifactPolicyResult(path_s, False, "trace_artifact_must_stay_external")
        if _is_summary_file(normalized):
            return ArtifactPolicyResult(path_s, True, "release_summary")
        return ArtifactPolicyResult(path_s, False, "output_artifact_requires_summary_allowlist")

    if len(parts) >= 2 and parts[0] == "data" and parts[1] in {"cache", "tmp"}:
        return ArtifactPolicyResult(path_s, False, "local_data_cache")

    if len(parts) >= 2 and parts[0] == "data" and parts[1] == "external":
        if normalized.name in REJECTED_DATA_EXTERNAL_FILENAMES:
            return ArtifactPolicyResult(path_s, False, "external_metadata_noise")
        if normalized.name in {"README.md", "manifest.json", ".gitkeep"}:
            return ArtifactPolicyResult(path_s, True, "external_manifest")
        return ArtifactPolicyResult(path_s, False, "external_benchmark_artifact")

    return ArtifactPolicyResult(path_s, True, "non_artifact")


def staged_added_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Paths to check when --staged is not set.")
    parser.add_argument("--staged", action="store_true", help="Check newly staged files.")
    args = parser.parse_args(argv)

    paths = staged_added_paths() if args.staged else args.paths
    violations = [result for result in map(classify_artifact_path, paths) if not result.allowed]
    if not violations:
        return 0

    print("Artifact policy rejected these paths:", file=sys.stderr)
    for result in violations:
        print(f"- {result.path}: {result.reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
