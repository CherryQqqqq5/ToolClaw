#!/usr/bin/env python3
"""Audit paper-facing docs for claim consistency against the claim matrix.

This gate is audit-only: it reads the paper claim matrix and scans markdown
files for stale or forbidden paper-facing claims. It does not modify docs,
runtime, runner, planner, scorer, or benchmark artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ClaimRule:
    rule_id: str
    severity: str
    description: str
    pattern: re.Pattern[str]
    message: str


BLOCKER_RULES: tuple[ClaimRule, ...] = (
    ClaimRule(
        rule_id="toolsandbox_s3_strict_one",
        severity="blocker",
        description="ToolSandbox s3 strict/success headline must not be reported as 1.000000.",
        pattern=re.compile(r"\bs3(?:_interaction_overlay)?\b\s*(?:=|:|\|)\s*`?1\.000000`?\b", re.IGNORECASE),
        message="stale ToolSandbox s3=1.000000 style claim",
    ),
    ClaimRule(
        rule_id="toolsandbox_s4_strict_one",
        severity="blocker",
        description="ToolSandbox s4 strict/success headline must not be reported as 1.000000.",
        pattern=re.compile(r"\bs4(?:_reuse_overlay)?\b\s*(?:=|:|\|)\s*`?1\.000000`?\b", re.IGNORECASE),
        message="stale ToolSandbox s4=1.000000 style claim",
    ),
    ClaimRule(
        rule_id="toolsandbox_interaction_360_0_855",
        severity="blocker",
        description="Legacy full-core interaction paired wins/losses/ties 360/0/855 is no longer paper-safe headline evidence.",
        pattern=re.compile(r"\b360\s*/\s*0\s*/\s*855\b"),
        message="stale ToolSandbox interaction paired 360/0/855 claim",
    ),
    ClaimRule(
        rule_id="toolsandbox_s3_minus_s2_0296296",
        severity="blocker",
        description="Legacy s3-s2=+0.296296 full-core interaction delta is no longer paper-safe headline evidence.",
        pattern=re.compile(r"\bs3\s*[-\u2212]\s*s2\s*=\s*\+?0\.296296\b", re.IGNORECASE),
        message="stale ToolSandbox s3-s2=+0.296296 claim",
    ),
    ClaimRule(
        rule_id="interaction_semantic_current_positive",
        severity="blocker",
        description="interaction_semantic_usefulness_mechanism is currently bounded/unsupported for full405, not current primary evidence.",
        pattern=re.compile(
            r"interaction_semantic_usefulness_mechanism[^\n]*(?:mechanism_primary|supported_current_evidence|current\s+claim)",
            re.IGNORECASE,
        ),
        message="interaction semantic usefulness claim is framed as current positive/primary evidence",
    ),
    ClaimRule(
        rule_id="reuse_s4_over_s3_lift",
        severity="blocker",
        description="Reuse s4 must not be framed as a strict-success lift over s3.",
        pattern=re.compile(
            r"(?:\bs4\b[^\n]{0,80}(?:>|greater\s+than|beats?|improves?|lifts?|gains?)[^\n]{0,80}\bs3\b|\breuse\b[^\n]{0,80}(?:success\s+)?(?:lift|gain|improvement)[^\n]{0,80}\bs[34]\b)",
            re.IGNORECASE,
        ),
        message="reuse/s4 is framed as strict-success lift over s3",
    ),
)

WARNING_RULES: tuple[ClaimRule, ...] = (
    ClaimRule(
        rule_id="bfcl_toolsandbox_headline_mixed",
        severity="warning",
        description="BFCL should remain a boundary/negative-transfer line and not be mixed into ToolSandbox headline framing.",
        pattern=re.compile(r"\bBFCL\b[^\n]{0,160}\bToolSandbox\b[^\n]{0,160}\bheadline\b|\bToolSandbox\b[^\n]{0,160}\bheadline\b[^\n]{0,160}\bBFCL\b", re.IGNORECASE),
        message="review BFCL mixed with ToolSandbox headline framing",
    ),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check paper-facing claim consistency in README/docs")
    parser.add_argument("--claim-matrix", default="configs/paper_claim_matrix.yaml", help="Source-of-truth claim matrix path")
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Files or glob patterns to scan. Defaults to README.md and docs/*.md.",
    )
    parser.add_argument("--out-json", help="Optional JSON report path")
    parser.add_argument("--out-md", help="Optional Markdown report path")
    parser.add_argument(
        "--warnings-as-blockers",
        action="store_true",
        help="Return nonzero when warnings are present even if no blockers are found.",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Print a compact text report to stdout. Enabled automatically when no output path is provided.",
    )
    return parser.parse_args(argv)


def _rooted(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT_DIR / value


def _load_claim_matrix(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Claim matrix must be JSON-compatible for this release gate: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Claim matrix root must be an object: {path}")
    return payload


def _claim(matrix: Mapping[str, Any], claim_id: str) -> Dict[str, Any]:
    claims = matrix.get("claims")
    if isinstance(claims, Mapping) and isinstance(claims.get(claim_id), Mapping):
        return dict(claims[claim_id])
    return {}


def _suite(matrix: Mapping[str, Any], suite_id: str) -> Dict[str, Any]:
    for key in ("suites", "benchmark_suites"):
        suites = matrix.get(key)
        if isinstance(suites, Mapping) and isinstance(suites.get(suite_id), Mapping):
            return dict(suites[suite_id])
    raw = matrix.get(suite_id)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _source_truth_snapshot(matrix: Mapping[str, Any]) -> Dict[str, Any]:
    interaction = _claim(matrix, "interaction_semantic_usefulness_mechanism")
    strict = _claim(matrix, "strict_layer_monotonicity")
    bfcl = _suite(matrix, "bfcl_fc_core")
    return {
        "interaction_semantic_usefulness_mechanism": {
            "status": interaction.get("status"),
            "claim_strength": interaction.get("claim_strength"),
            "boundary": interaction.get("boundary"),
        },
        "strict_layer_monotonicity": {
            "status": strict.get("status"),
            "claim_strength": strict.get("claim_strength"),
            "boundary": strict.get("boundary"),
        },
        "bfcl_fc_core": {
            "status": bfcl.get("status"),
            "claim_strength": bfcl.get("claim_strength"),
            "paper_role": bfcl.get("paper_role"),
            "reuse_claim_enabled_for_bfcl": bfcl.get("reuse_claim_enabled_for_bfcl"),
        },
    }


def _default_paths() -> List[Path]:
    paths = []
    readme = ROOT_DIR / "README.md"
    if readme.exists():
        paths.append(readme)
    docs_dir = ROOT_DIR / "docs"
    if docs_dir.exists():
        paths.extend(sorted(docs_dir.glob("*.md")))
    return paths


def resolve_scan_paths(raw_paths: Sequence[str] | None) -> List[Path]:
    if not raw_paths:
        return _default_paths()
    resolved: List[Path] = []
    for raw in raw_paths:
        pattern = _rooted(raw)
        matches = sorted(pattern.parent.glob(pattern.name)) if any(ch in str(pattern) for ch in "*?[") else []
        if matches:
            resolved.extend(path for path in matches if path.is_file())
        else:
            path = pattern
            if path.is_file():
                resolved.append(path)
    deduped: List[Path] = []
    seen: set[Path] = set()
    for path in resolved:
        canonical = path.resolve()
        if canonical not in seen:
            seen.add(canonical)
            deduped.append(path)
    return deduped


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _is_boundary_negation(line: str) -> bool:
    lowered = line.lower()
    return any(
        marker in lowered
        for marker in (
            "do not",
            "does not",
            "must not",
            "should not",
            "not claim",
            "not support",
            "no ",
            "boundary",
            "limitation",
            "negative-transfer",
        )
    )


def _scan_line(path: Path, line_number: int, line: str, rules: Iterable[ClaimRule]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for rule in rules:
        if not rule.pattern.search(line):
            continue
        if rule.rule_id in {"reuse_s4_over_s3_lift", "bfcl_toolsandbox_headline_mixed"} and _is_boundary_negation(line):
            continue
        issues.append(
            {
                "severity": rule.severity,
                "rule_id": rule.rule_id,
                "path": _rel(path),
                "line": line_number,
                "message": rule.message,
                "evidence": line.strip(),
            }
        )
    return issues


def scan_paths(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    rules = (*BLOCKER_RULES, *WARNING_RULES)
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            issues.extend(_scan_line(path, line_number, line, rules))
    return issues


def build_report(claim_matrix_path: Path, scan_paths_input: Sequence[Path]) -> Dict[str, Any]:
    matrix = _load_claim_matrix(claim_matrix_path)
    issues = scan_paths(scan_paths_input)
    blocker_count = sum(1 for issue in issues if issue["severity"] == "blocker")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    return {
        "audit_only": True,
        "claim_matrix_path": _rel(claim_matrix_path),
        "source_truth": _source_truth_snapshot(matrix),
        "scanned_paths": [_rel(path) for path in scan_paths_input],
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "issue_count": len(issues),
        "issues": issues,
        "rules": [
            {
                "rule_id": rule.rule_id,
                "severity": rule.severity,
                "description": rule.description,
            }
            for rule in (*BLOCKER_RULES, *WARNING_RULES)
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Claim Consistency Check",
        "",
        f"Audit only: `{str(report.get('audit_only')).lower()}`",
        f"Claim matrix: `{report.get('claim_matrix_path')}`",
        f"Scanned files: `{len(report.get('scanned_paths', []))}`",
        f"Blockers: `{report.get('blocker_count')}`",
        f"Warnings: `{report.get('warning_count')}`",
        "",
        "## Source of Truth Snapshot",
        "",
        "```json",
        json.dumps(report.get("source_truth", {}), indent=2, sort_keys=True),
        "```",
        "",
        "## Issues",
        "",
    ]
    issues = list(report.get("issues", []))
    if not issues:
        lines.append("No blockers or warnings found.")
    else:
        lines.extend(["| Severity | Rule | Location | Evidence |", "| --- | --- | --- | --- |"])
        for issue in issues:
            evidence = str(issue.get("evidence", "")).replace("|", "\\|")
            if len(evidence) > 180:
                evidence = evidence[:177] + "..."
            lines.append(
                f"| {issue.get('severity')} | `{issue.get('rule_id')}` | `{issue.get('path')}:{issue.get('line')}` | {evidence} |"
            )
    lines.append("")
    return "\n".join(lines)


def render_text(report: Mapping[str, Any]) -> str:
    lines = [
        "claim consistency check",
        f"claim_matrix={report.get('claim_matrix_path')}",
        f"scanned_paths={len(report.get('scanned_paths', []))}",
        f"blockers={report.get('blocker_count')} warnings={report.get('warning_count')}",
    ]
    for issue in report.get("issues", []):
        lines.append(
            f"{issue.get('severity')} {issue.get('rule_id')} {issue.get('path')}:{issue.get('line')} {issue.get('message')}"
        )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    claim_matrix = _rooted(args.claim_matrix)
    paths = resolve_scan_paths(args.paths)
    report = build_report(claim_matrix, paths)

    if args.out_json:
        out_json = _rooted(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        out_md = _rooted(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(render_markdown(report), encoding="utf-8")
    if args.text or not args.out_json and not args.out_md:
        sys.stdout.write(render_text(report))

    if report["blocker_count"] > 0:
        return 1
    if args.warnings_as_blockers and report["warning_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
