#!/usr/bin/env python3
"""Inventory official ToolSandbox scenarios and audit frozen export coverage.

This script builds provenance artifacts only. The official scenario inventory is a
candidate-space inventory, not experimental evidence; only actual ToolSandbox runs
and exported trajectories can support official-run claims.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
OFFICIAL_ROOT = ROOT_DIR / "data" / "external" / "ToolSandbox"
DEFAULT_FROZEN_EXPORT = ROOT_DIR / "data" / "toolsandbox.formal.official.json"
DEFAULT_INVENTORY = ROOT_DIR / "data" / "toolsandbox_official_scenario_inventory.json"
DEFAULT_INVENTORY_MANIFEST = ROOT_DIR / "data" / "toolsandbox_official_scenario_inventory.manifest.json"
DEFAULT_LEDGER = ROOT_DIR / "data" / "toolsandbox_run_coverage_ledger.json"
DEFAULT_DOC = ROOT_DIR / "docs" / "toolsandbox_data_coverage_audit_20260426.md"

LAYER_POLICY = {
    "layer_1_official_inventory": "scenario source inventory only; not experimental evidence",
    "layer_2_official_run_export": "actual ToolSandbox run/export evidence with trajectories and result summaries",
    "layer_3_derived_mechanism_suites": "targeted ToolSandbox-derived mechanism evaluations with explicit provenance",
}


def _git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _normalize_category(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "_").replace("-", "_")


def _runtime_query_from_sandbox_rows(rows: Any) -> str:
    if not isinstance(rows, list):
        return ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        sender = str(row.get("sender") or "").upper()
        recipient = str(row.get("recipient") or "").upper()
        content = row.get("content")
        if sender == "USER" and recipient in {"AGENT", "UNKNOWN", ""} and content:
            return str(content)
    return ""


def _tool_module_index(official_root: Path) -> Dict[str, str]:
    tools_dir = official_root / "tool_sandbox" / "tools"
    index: Dict[str, str] = {}
    for path in sorted(tools_dir.glob("*.py")):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                index[node.name] = str(path.relative_to(official_root))
    return index


def _rapidapi_tool_names(official_root: Path) -> set[str]:
    rapid_path = official_root / "tool_sandbox" / "tools" / "rapid_api_search_tools.py"
    if not rapid_path.exists():
        return set()
    rapid_tools: set[str] = set()
    try:
        module = ast.parse(rapid_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return rapid_tools
    helper_names = {"rapid_api_get_request", "maybe_get_current_lat_lon"}
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name not in helper_names:
            rapid_tools.add(node.name)
    return rapid_tools


AUGMENTATION_SUFFIXES = (
    "_arg_description_scrambled",
    "_arg_type_scrambled",
    "_tool_description_scrambled",
    "_tool_name_scrambled",
    "_3_distraction_tools",
    "_10_distraction_tools",
    "_all_tools",
)


def _base_scenario_name(name: str) -> str:
    base = name
    changed = True
    while changed:
        changed = False
        for suffix in AUGMENTATION_SUFFIXES:
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                changed = True
    return base


def _scenario_source_index(official_root: Path, scenario_names: Iterable[str]) -> Dict[str, str]:
    scenario_root = official_root / "tool_sandbox" / "scenarios"
    names = set(scenario_names)
    base_names = {_base_scenario_name(name) for name in names}
    base_found: Dict[str, str] = {}
    for path in sorted(scenario_root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name in base_names - set(base_found):
            if f'name="{name}"' in text or f"name='{name}'" in text:
                base_found[name] = str(path.relative_to(official_root))
    return {name: base_found.get(_base_scenario_name(name), "") for name in names}


def _external_dependency(tool_allow_list: List[str], tool_modules: Mapping[str, str], rapidapi_tools: set[str]) -> Tuple[bool, str, List[str], List[str]]:
    rapid_tools = sorted(tool for tool in tool_allow_list if tool in rapidapi_tools)
    unknown_tools = sorted(
        tool for tool in tool_allow_list
        if tool not in tool_modules and tool not in {"end_conversation"}
    )
    if rapid_tools:
        return True, "rapidapi_backed_tools:" + ",".join(rapid_tools), rapid_tools, unknown_tools
    if unknown_tools:
        return True, "unknown_external_dependency:" + ",".join(unknown_tools), rapid_tools, unknown_tools
    return False, "python_native_or_local_tools", rapid_tools, unknown_tools


def _official_inventory_payload(official_root: Path) -> Dict[str, Any]:
    python_bin = official_root / ".venv" / "bin" / "python"
    if not python_bin.exists():
        raise FileNotFoundError(f"official ToolSandbox python not found: {python_bin}")
    code = r'''
import json
from tool_sandbox.common.execution_context import DatabaseNamespace
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.scenarios import named_scenarios

scenarios = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)
rows = []
for name, scenario in sorted(scenarios.items()):
    context = scenario.starting_context
    sandbox_rows = []
    try:
        sandbox_rows = context.get_database(DatabaseNamespace.SANDBOX).to_dicts()
    except Exception:
        sandbox_rows = []
    rows.append({
        "scenario_name": name,
        "name": name,
        "categories": [getattr(cat, "name", str(cat)) for cat in scenario.categories],
        "tool_allow_list": list(context.tool_allow_list or []),
        "tool_augmentation_list": [getattr(item, "name", str(item)) for item in (context.tool_augmentation_list or [])],
        "milestone_count": len(scenario.evaluation.milestone_matcher.milestones),
        "minefield_count": len(scenario.evaluation.minefield_matcher.milestones),
        "max_messages": scenario.max_messages,
        "initial_sandbox_messages": sandbox_rows,
    })
print(json.dumps({"scenario_count": len(rows), "scenarios": rows}, sort_keys=True))
'''
    completed = subprocess.run(
        [str(python_bin), "-c", code],
        cwd=str(official_root),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def build_inventory(official_root: Path = OFFICIAL_ROOT) -> Dict[str, Any]:
    payload = _official_inventory_payload(official_root)
    tool_modules = _tool_module_index(official_root)
    rapidapi_tools = _rapidapi_tool_names(official_root)
    source_files = _scenario_source_index(official_root, [row["scenario_name"] for row in payload["scenarios"]])

    enriched: List[Dict[str, Any]] = []
    for row in payload["scenarios"]:
        tools = list(row.get("tool_allow_list") or [])
        requires_external, reason, rapid_tools, unknown_tools = _external_dependency(tools, tool_modules, rapidapi_tools)
        sandbox_rows = row.pop("initial_sandbox_messages", [])
        scenario_name = str(row.get("scenario_name") or row.get("name"))
        enriched.append({
            **row,
            "scenario_name": scenario_name,
            "normalized_categories": [_normalize_category(cat).lower() for cat in row.get("categories", [])],
            "initial_user_query": _runtime_query_from_sandbox_rows(sandbox_rows),
            "scenario_source_file": source_files.get(scenario_name, ""),
            "requires_external_api": requires_external,
            "external_dependency_status": "rapidapi" if rapid_tools else ("unknown_external_dependency" if unknown_tools else "python_native"),
            "rapidapi_or_external_api_reason": reason,
            "rapidapi_tools": rapid_tools,
            "unknown_tool_modules": unknown_tools,
            "tool_modules": {tool: tool_modules.get(tool, "") for tool in tools},
        })

    category_counts = Counter(cat for row in enriched for cat in row.get("categories", []))
    tool_counts = Counter(tool for row in enriched for tool in row.get("tool_allow_list", []))
    augmentation_counts = Counter(aug for row in enriched for aug in row.get("tool_augmentation_list", []))
    requires_external_count = sum(1 for row in enriched if row["requires_external_api"])
    rapidapi_count = sum(1 for row in enriched if row["external_dependency_status"] == "rapidapi")
    unknown_count = sum(1 for row in enriched if row["external_dependency_status"] == "unknown_external_dependency")
    return {
        "inventory_is_evidence": False,
        "source": str(official_root),
        "source_commit": _git_commit(official_root),
        "scenario_count": len(enriched),
        "category_counts": dict(sorted(category_counts.items())),
        "tool_counts": dict(sorted(tool_counts.items())),
        "tool_augmentation_counts": dict(sorted(augmentation_counts.items())),
        "requires_external_api_count": requires_external_count,
        "rapidapi_backed_scenario_count": rapidapi_count,
        "unknown_external_dependency_count": unknown_count,
        "python_native_scenario_count": len(enriched) - requires_external_count,
        "rapidapi_tool_names": sorted(rapidapi_tools),
        "layer_policy": dict(LAYER_POLICY),
        "scenarios": enriched,
    }


def build_inventory_manifest(inventory: Mapping[str, Any], *, frozen_export_path: Path = DEFAULT_FROZEN_EXPORT) -> Dict[str, Any]:
    frozen_count = 0
    if frozen_export_path.exists():
        frozen = _read_json(frozen_export_path)
        if isinstance(frozen, list):
            frozen_count = len(frozen)
    return {
        "artifact": str(DEFAULT_INVENTORY.relative_to(ROOT_DIR)),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toolclaw_commit": _git_commit(ROOT_DIR),
        "official_toolsandbox_source": inventory.get("source"),
        "official_toolsandbox_commit": inventory.get("source_commit"),
        "inventory_is_evidence": False,
        "inventory_count": inventory.get("scenario_count", 0),
        "frozen_export_count": frozen_count,
        "category_counts": inventory.get("category_counts", {}),
        "tool_counts": inventory.get("tool_counts", {}),
        "tool_augmentation_counts": inventory.get("tool_augmentation_counts", {}),
        "requires_external_api_count": inventory.get("requires_external_api_count", 0),
        "rapidapi_backed_scenario_count": inventory.get("rapidapi_backed_scenario_count", 0),
        "unknown_external_dependency_count": inventory.get("unknown_external_dependency_count", 0),
        "python_native_scenario_count": inventory.get("python_native_scenario_count", 0),
        "layer_policy": dict(LAYER_POLICY),
        "notes": [
            "Inventory rows are not experimental evidence.",
            "Official-run claims require actual result summaries and trajectories.",
            "Current frozen export coverage is audited separately in toolsandbox_run_coverage_ledger.json.",
        ],
    }


def _frozen_name(row: Mapping[str, Any]) -> str:
    return str(row.get("name") or row.get("scenario_name") or row.get("task_id") or "")


def _frozen_successfully_ran(row: Mapping[str, Any]) -> bool:
    result_summary = row.get("result_summary") if isinstance(row.get("result_summary"), dict) else {}
    traceback = row.get("official_traceback") or result_summary.get("traceback")
    exception_type = row.get("official_exception_type") or result_summary.get("exception_type")
    return not traceback and not exception_type


def build_coverage_ledger(inventory: Mapping[str, Any], frozen_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    frozen_by_name: Dict[str, List[Dict[str, Any]]] = {}
    for row in frozen_rows:
        frozen_by_name.setdefault(_frozen_name(row), []).append(row)
    inventory_names = {str(row.get("scenario_name") or row.get("name")) for row in inventory.get("scenarios", [])}
    scenarios: List[Dict[str, Any]] = []
    for row in inventory.get("scenarios", []):
        scenario_name = str(row.get("scenario_name") or row.get("name"))
        matched = frozen_by_name.get(scenario_name, [])
        frozen = matched[0] if matched else {}
        metadata = frozen.get("metadata") if isinstance(frozen.get("metadata"), dict) else {}
        included = bool(matched)
        scenarios.append({
            "scenario_name": scenario_name,
            "in_official_inventory": True,
            "included_in_frozen_export": included,
            "frozen_export_row_count": len(matched),
            "requires_external_api": bool(row.get("requires_external_api")),
            "rapidapi_available": None,
            "rapidapi_or_external_api_reason": row.get("rapidapi_or_external_api_reason") or "",
            "external_dependency_status": row.get("external_dependency_status") or "",
            "run_successfully": _frozen_successfully_ran(frozen) if included else False,
            "trajectory_path": metadata.get("trajectory_dir", ""),
            "result_summary_path": metadata.get("result_summary_path", ""),
            "exported_to_normalized_json": included,
            "excluded_reason": "" if included else ("external_api_or_not_in_legacy_frozen_export" if row.get("requires_external_api") else "not_in_legacy_frozen_export"),
            "categories": row.get("categories", []),
            "tool_allow_list": row.get("tool_allow_list", []),
            "tool_augmentation_list": row.get("tool_augmentation_list", []),
        })
    unmatched = [
        {
            "name": _frozen_name(row),
            "metadata": row.get("metadata", {}),
            "categories": row.get("categories", []),
        }
        for row in frozen_rows
        if _frozen_name(row) not in inventory_names
    ]
    included_count = sum(1 for row in scenarios if row["included_in_frozen_export"])
    excluded_count = len(scenarios) - included_count
    external_count = sum(1 for row in scenarios if row["requires_external_api"])
    coverage_rate = included_count / len(scenarios) if scenarios else 0.0
    return {
        "manifest": {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "toolclaw_commit": _git_commit(ROOT_DIR),
            "official_toolsandbox_commit": inventory.get("source_commit"),
            "inventory_count": len(scenarios),
            "frozen_export_count": len(frozen_rows),
            "included_in_frozen_export_count": included_count,
            "excluded_from_frozen_export_count": excluded_count,
            "coverage_rate": coverage_rate,
            "requires_external_api_count": external_count,
            "rapidapi_backed_scenario_count": sum(1 for row in scenarios if row["external_dependency_status"] == "rapidapi"),
            "unknown_external_dependency_count": sum(1 for row in scenarios if row["external_dependency_status"] == "unknown_external_dependency"),
            "unmatched_frozen_export_row_count": len(unmatched),
            "coverage_ledger_is_evidence": False,
            "legacy_export_label": "toolsandbox_legacy_frozen_official_run_subset",
            "layer_policy": dict(LAYER_POLICY),
            "safe_wording": "frozen ToolSandbox official-run export subset; not a complete official ToolSandbox benchmark unless coverage reaches the official inventory under documented API configuration",
        },
        "scenarios": scenarios,
        "unmatched_frozen_export_rows": unmatched,
    }


def _top_items(counter: Counter, n: int = 12) -> List[Tuple[str, int]]:
    return counter.most_common(n)


def render_coverage_doc(inventory: Mapping[str, Any], ledger: Mapping[str, Any]) -> str:
    manifest = ledger.get("manifest", {})
    scenarios = ledger.get("scenarios", [])
    missing = [row for row in scenarios if not row.get("included_in_frozen_export")]
    external_missing = [row for row in missing if row.get("requires_external_api")]
    category_counts = Counter(cat for row in scenarios for cat in row.get("categories", []))
    missing_category_counts = Counter(cat for row in missing for cat in row.get("categories", []))
    external_reason_counts = Counter(row.get("rapidapi_or_external_api_reason") or "" for row in scenarios if row.get("requires_external_api"))
    lines = [
        "# ToolSandbox Data Coverage Audit (2026-04-26)",
        "",
        "## Summary",
        "",
        "This audit separates the official ToolSandbox scenario inventory from the repository's current frozen official-run export. The inventory is candidate-space provenance only; it is not experimental evidence.",
        "",
        f"- official inventory scenarios: `{manifest.get('inventory_count', 0)}`",
        f"- current frozen export rows: `{manifest.get('frozen_export_count', 0)}`",
        f"- inventory scenarios included in frozen export: `{manifest.get('included_in_frozen_export_count', 0)}`",
        f"- inventory scenarios not included in frozen export: `{manifest.get('excluded_from_frozen_export_count', 0)}`",
        f"- coverage rate: `{manifest.get('coverage_rate', 0.0):.4f}`",
        f"- rapidapi/external-api scenarios: `{manifest.get('requires_external_api_count', 0)}`",
        f"- unmatched frozen export rows: `{manifest.get('unmatched_frozen_export_row_count', 0)}`",
        "",
        "Safe wording: evaluate on a frozen ToolSandbox official-run export subset, with coverage audited against the official scenario inventory. Do not call the current frozen export a complete official ToolSandbox benchmark.",
        "",
        "## Three-Layer Evidence Model",
        "",
        "1. Layer 1: official scenario inventory. Scenario source coverage only; not evidence.",
        "2. Layer 2: official-run export. Actual ToolSandbox result summaries and trajectories; can support official-run claims within documented coverage.",
        "3. Layer 3: derived mechanism suites. Targeted ToolSandbox-derived evaluations such as semantic repair, planner-sensitive, and reuse suites.",
        "",
        "## Category Coverage",
        "",
        "| category | inventory count | missing from frozen export |",
        "| --- | ---: | ---: |",
    ]
    for category, count in _top_items(category_counts, 20):
        lines.append(f"| `{category}` | {count} | {missing_category_counts.get(category, 0)} |")
    lines.extend([
        "",
        "## External API / RapidAPI Risk",
        "",
        "| dependency reason | scenario count |",
        "| --- | ---: |",
    ])
    for reason, count in _top_items(external_reason_counts, 20):
        lines.append(f"| `{reason}` | {count} |")
    lines.extend([
        "",
        "## Legacy Frozen Export Boundary",
        "",
        "`data/toolsandbox.formal.official.json` remains useful as a legacy frozen official-run subset, but it should not be described as the complete official ToolSandbox scenario space. Future official claims should either use a core reproducible export with documented exclusions or a full available export with API configuration and coverage ledger.",
        "",
        "## Claim Impact",
        "",
        "- No ToolSandbox claim is promoted by this audit.",
        "- Existing derived mechanism suites keep their own provenance and should not be described as complete official ToolSandbox benchmark results.",
        "- Reuse v3, semantic repair v2, and any future official core/full rerun should consume this coverage ledger before formal evidence is claimed.",
    ])
    if external_missing:
        lines.extend([
            "",
            "## External/API Missing Examples",
            "",
            "| scenario | reason |",
            "| --- | --- |",
        ])
        for row in external_missing[:20]:
            lines.append(f"| `{row.get('scenario_name')}` | `{row.get('rapidapi_or_external_api_reason')}` |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory official ToolSandbox scenarios and audit frozen export coverage")
    parser.add_argument("--official-root", default=str(OFFICIAL_ROOT))
    parser.add_argument("--frozen-export", default=str(DEFAULT_FROZEN_EXPORT))
    parser.add_argument("--inventory-out", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--inventory-manifest-out", default=str(DEFAULT_INVENTORY_MANIFEST))
    parser.add_argument("--ledger-out", default=str(DEFAULT_LEDGER))
    parser.add_argument("--doc-out", default=str(DEFAULT_DOC))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    official_root = Path(args.official_root)
    frozen_export = Path(args.frozen_export)
    inventory = build_inventory(official_root)
    frozen_rows = _read_json(frozen_export) if frozen_export.exists() else []
    if not isinstance(frozen_rows, list):
        raise ValueError(f"expected list frozen export: {frozen_export}")
    manifest = build_inventory_manifest(inventory, frozen_export_path=frozen_export)
    ledger = build_coverage_ledger(inventory, frozen_rows)
    _write_json(Path(args.inventory_out), inventory)
    _write_json(Path(args.inventory_manifest_out), manifest)
    _write_json(Path(args.ledger_out), ledger)
    Path(args.doc_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.doc_out).write_text(render_coverage_doc(inventory, ledger), encoding="utf-8")
    print(f"wrote: {args.inventory_out}")
    print(f"wrote: {args.inventory_manifest_out}")
    print(f"wrote: {args.ledger_out}")
    print(f"wrote: {args.doc_out}")


if __name__ == "__main__":
    main()
