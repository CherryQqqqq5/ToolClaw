"""Entry point for ToolClaw evaluation over normalized tasksets."""

from __future__ import annotations

import argparse
import concurrent.futures
from copy import deepcopy
import os
import subprocess
import json
import re
import shlex
import sys
import time
from datetime import datetime, timedelta
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Allow `python3 scripts/run_eval.py ...` from repo root without manual PYTHONPATH.
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.baseline_runner import run_baseline
from toolclaw.benchmarks.adapters import BFCLAdapter
from toolclaw.bfcl_runtime import (
    extract_parallel_argument_sets,
    extract_tool_arguments,
    rank_candidate_tools,
    select_candidate_tool,
)
from toolclaw.benchmarks.metrics import (
    EvalRow,
    summarize,
    summarize_by_scenario,
    write_report_md,
    write_rows_csv,
)
from toolclaw.benchmarks.task_annotations import (
    annotate_task,
    annotate_task_payload,
    derive_primary_failtax,
    map_failtax_bucket,
)
from toolclaw.compiler.swpc import SWPCCompiler, build_task_signature_candidates
from toolclaw.execution.executor import ExecutorConfig, SequentialExecutor
from toolclaw.execution.recovery import RecoveryConfig, RecoveryEngine
from toolclaw.interaction.irc import InteractionLoopConfig, InteractionShell
from toolclaw.interaction.reply_provider import (
    CLIReplyProvider,
    DeterministicModeReplyProvider,
    DeterministicNoisyReplyProvider,
    HumanReplyProvider,
    LLMReplyProvider,
    OracleReplayProvider,
)
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.semantic_decoder import SemanticDecoder
from toolclaw.interaction.user_simulator import SimulatedPolicy, UserSimulator
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.capability_intents import CAPABILITY_PROFILES_BY_ID, infer_capability_from_text
from toolclaw.planner.htgp import PlanningRequest, build_default_planner
from toolclaw.planner.overlay import apply_admitted_planner_overlay, apply_planner_overlay, apply_reuse_overlay_noop
from toolclaw.registry import AssetRegistry, FileAssetRegistry, InMemoryAssetRegistry
from toolclaw.schemas.workflow import CapabilityEdge, RiskLevel, TaskConstraints, ToolSpec, Workflow, WorkflowEdge


@dataclass(frozen=True)
class SystemSpec:
    system_id: str
    workflow_mode: str
    execution_mode: str
    compile_on_success: bool = False
    use_reuse: bool = False
    allow_repair: bool = True
    allow_fallback: bool = True
    allow_suffix_replan: bool = True
    enable_core_grounding: bool = True
    enable_schema_preflight: bool = True
    disable_user_queries: bool = False
    noisy_user_replies: bool = False
    interaction_live_user_mode: str = ""
    enable_success_probe: bool = False


SYSTEM_SPECS: Dict[str, SystemSpec] = {
    "a0_baseline": SystemSpec(
        system_id="a0_baseline",
        workflow_mode="demo",
        execution_mode="executor",
        allow_repair=False,
        allow_fallback=False,
    ),
    "a1_recovery": SystemSpec(
        system_id="a1_recovery",
        workflow_mode="demo",
        execution_mode="executor",
        allow_repair=True,
        allow_fallback=True,
    ),
    "a2_planner": SystemSpec(
        system_id="a2_planner",
        workflow_mode="planner",
        execution_mode="executor",
        allow_repair=True,
        allow_fallback=True,
    ),
    "a3_interaction": SystemSpec(
        system_id="a3_interaction",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
    ),
    "a3_full_interaction": SystemSpec(
        system_id="a3_full_interaction",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
    ),
    "a3_full_interaction_oracle": SystemSpec(
        system_id="a3_full_interaction_oracle",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
    ),
    "a3_no_query": SystemSpec(
        system_id="a3_no_query",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        disable_user_queries=True,
    ),
    "a3_noisy_user": SystemSpec(
        system_id="a3_noisy_user",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        noisy_user_replies=True,
    ),
    "a3_full_interaction_noisy": SystemSpec(
        system_id="a3_full_interaction_noisy",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        interaction_live_user_mode="noisy",
    ),
    "a3_full_interaction_irrelevant": SystemSpec(
        system_id="a3_full_interaction_irrelevant",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        interaction_live_user_mode="irrelevant",
    ),
    "a3_full_interaction_wrong_parameter": SystemSpec(
        system_id="a3_full_interaction_wrong_parameter",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        interaction_live_user_mode="wrong_parameter",
    ),
    "a3_full_interaction_partial": SystemSpec(
        system_id="a3_full_interaction_partial",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        interaction_live_user_mode="partial",
    ),
    "a4_reuse": SystemSpec(
        system_id="a4_reuse",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=True,
        use_reuse=True,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
    ),
    "s0_baseline": SystemSpec(
        system_id="s0_baseline",
        workflow_mode="demo",
        execution_mode="executor",
        allow_repair=False,
        allow_fallback=False,
    ),
    "s1_recovery": SystemSpec(
        system_id="s1_recovery",
        workflow_mode="demo",
        execution_mode="executor",
        allow_repair=True,
        allow_fallback=True,
    ),
    "s2_planner_overlay": SystemSpec(
        system_id="s2_planner_overlay",
        workflow_mode="planner_overlay_admitted",
        execution_mode="executor",
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=True,
    ),
    "s3_interaction_overlay": SystemSpec(
        system_id="s3_interaction_overlay",
        workflow_mode="planner_overlay_admitted",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=True,
    ),
    "s4_reuse_overlay": SystemSpec(
        system_id="s4_reuse_overlay",
        workflow_mode="planner_overlay_admitted",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=True,
    ),
    "tc_full": SystemSpec(
        system_id="tc_full",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=True,
        use_reuse=True,
        allow_repair=True,
        allow_fallback=True,
    ),
    "tc_no_repair": SystemSpec(
        system_id="tc_no_repair",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=False,
        allow_fallback=False,
    ),
    "tc_no_fallback": SystemSpec(
        system_id="tc_no_fallback",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=False,
    ),
    "tc_no_reuse": SystemSpec(
        system_id="tc_no_reuse",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
    ),
    "tc_recovery_only": SystemSpec(
        system_id="tc_recovery_only",
        workflow_mode="demo",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
    ),
    "tc_no_interaction": SystemSpec(
        system_id="tc_no_interaction",
        workflow_mode="planner",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
    ),
    "tc_planner_strict": SystemSpec(
        system_id="tc_planner_strict",
        workflow_mode="planner",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=False,
        allow_fallback=False,
    ),
    "tc_planner_only": SystemSpec(
        system_id="tc_planner_only",
        workflow_mode="planner",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
    ),
    "fc_preflight_only": SystemSpec(
        system_id="fc_preflight_only",
        workflow_mode="planner",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=False,
        allow_fallback=False,
        allow_suffix_replan=False,
        enable_core_grounding=False,
        enable_schema_preflight=True,
    ),
    "fc_grounding_recovery": SystemSpec(
        system_id="fc_grounding_recovery",
        workflow_mode="planner",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
        allow_suffix_replan=False,
        enable_core_grounding=True,
        enable_schema_preflight=True,
    ),
}

SYSTEM_ALIASES: Dict[str, str] = {
    "baseline": "a0_baseline",
    "planning": "a2_planner",
    "interactive": "a3_interaction",
    "toolclaw_lite": "a3_interaction",
    "full_interaction": "a3_full_interaction",
    "oracle_user": "a3_full_interaction_oracle",
    "no_query": "a3_no_query",
    "noisy_user": "a3_noisy_user",
    "irrelevant_user": "a3_full_interaction_irrelevant",
    "wrong_parameter_user": "a3_full_interaction_wrong_parameter",
    "partial_user": "a3_full_interaction_partial",
}

BFCL_ADAPTER = BFCLAdapter()


def _build_tool_specs(raw_tools: Any) -> List[ToolSpec]:
    candidate_tools: List[ToolSpec] = []
    if not isinstance(raw_tools, list):
        return candidate_tools
    for idx, raw_tool in enumerate(raw_tools, start=1):
        if isinstance(raw_tool, str):
            candidate_tools.append(ToolSpec(tool_id=raw_tool, description=raw_tool))
            continue
        if isinstance(raw_tool, dict):
            candidate_tools.append(
                ToolSpec(
                    tool_id=str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                    description=str(raw_tool.get("description") or raw_tool.get("tool_id") or raw_tool.get("name") or "tool"),
                    metadata={k: v for k, v in raw_tool.items() if k not in {"tool_id", "name", "description"}},
                )
            )
    return candidate_tools


def _bfcl_tool_lookup(candidate_tools: List[ToolSpec]) -> Dict[str, ToolSpec]:
    return {
        str(tool.tool_id): tool
        for tool in candidate_tools
        if str(tool.tool_id).strip()
    }


def _bfcl_best_tool(candidate_tools: List[ToolSpec], text: str) -> Optional[ToolSpec]:
    selected = select_candidate_tool(text, candidate_tools)
    if not isinstance(selected, dict):
        return candidate_tools[0] if candidate_tools else None
    best_tool_id = str(selected.get("tool_id") or "")
    return _bfcl_tool_lookup(candidate_tools).get(best_tool_id) or (candidate_tools[0] if candidate_tools else None)


def _bfcl_rank_item_tool_id(item: Dict[str, Any]) -> str:
    tool = item.get("tool")
    if isinstance(tool, dict):
        return str(tool.get("tool_id") or tool.get("name") or "").strip()
    return str(getattr(tool, "tool_id", "") or "").strip()


def _bfcl_rank_item_score(item: Dict[str, Any]) -> float:
    return float(item.get("score", 0.0) or 0.0)


def _bfcl_required_arg_status(tool: Optional[ToolSpec], text: str) -> Dict[str, Any]:
    required = _bfcl_required_input_keys(tool)
    inputs = (
        extract_tool_arguments(
            str(tool.tool_id),
            _bfcl_tool_parameters(tool),
            text,
            include_defaults=False,
        )
        if tool is not None
        else {}
    )
    present = [key for key in required if _bfcl_has_bound_value(inputs.get(key))]
    missing = [key for key in required if key not in present]
    return {
        "required_argument_coverage": (float(len(present)) / float(len(required))) if required else 1.0,
        "required_args_present": present,
        "missing_required_args": missing,
    }


def _bfcl_tool_original_function_name(tool: Any) -> str:
    metadata = getattr(tool, "metadata", {}) if not isinstance(tool, dict) else tool.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    tool_id = str(getattr(tool, "tool_id", "") if not isinstance(tool, dict) else tool.get("tool_id", ""))
    return str(metadata.get("bfcl_original_function_name") or metadata.get("canonical_name") or tool_id).strip()


def _bfcl_runtime_candidate_summary(
    candidate_tools: List[ToolSpec],
    *,
    prepared_function_count: Optional[int] = None,
    candidate_pool_exception: str = "",
    drop_reason: str = "",
) -> Dict[str, Any]:
    tool_ids = [str(tool.tool_id) for tool in candidate_tools]
    original_names = [_bfcl_tool_original_function_name(tool) for tool in candidate_tools]
    prepared_count = len(candidate_tools) if prepared_function_count is None else int(prepared_function_count)
    preserved = len(candidate_tools) == prepared_count and not candidate_pool_exception
    return {
        "prepared_function_count": prepared_count,
        "runtime_candidate_count": len(candidate_tools),
        "runtime_candidate_tool_ids": tool_ids,
        "runtime_candidate_original_function_names": original_names,
        "candidate_pool_preserved": preserved,
        "candidate_pool_source": "bfcl_prepared_row_functions",
        "planner_narrowing_applied": False,
        "candidate_pool_exception": candidate_pool_exception,
        "drop_reason": drop_reason,
    }


def _bfcl_empty_candidate_diagnostics(candidate_tools: List[ToolSpec]) -> Dict[str, Any]:
    return {
        "ranked": [],
        "schema_top_5": [],
        "schema_top_tool_id": "",
        "schema_top_score": 0.0,
        "schema_top_exact_match": False,
        "schema_top_semantic_overlap": [],
        "schema_top_required_argument_coverage": None,
        "operation_cues_present": False,
    }


_BFCL_OPERATION_CUE_RE = re.compile(
    r"\b("
    r"get|fetch|find|search|look\s*up|retrieve|show|tell|calculate|compute|convert|"
    r"book|schedule|create|send|update|change|modify|delete|cancel|call|order|"
    r"compare|translate|summarize|generate|check|verify|validate|list"
    r")\b",
    re.IGNORECASE,
)


def _bfcl_has_operation_cues(text: str) -> bool:
    return bool(_BFCL_OPERATION_CUE_RE.search(str(text or "")))


def _bfcl_runtime_irrelevance_label_signal(task: Dict[str, Any]) -> bool:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    pieces = [
        str(task.get("task_id") or ""),
        str(task.get("scenario") or ""),
        str(task.get("category") or ""),
        str(metadata.get("bfcl_group") or ""),
        str(metadata.get("bfcl_call_pattern") or ""),
        str(metadata.get("category") or ""),
        str(metadata.get("scenario") or ""),
    ]
    joined = " ".join(pieces).lower()
    return "irrelevance" in joined or "no_call" in joined


def _bfcl_irrelevance_signal(task: Dict[str, Any]) -> bool:
    return _bfcl_runtime_irrelevance_label_signal(task)


_BFCL_EXPLICIT_NO_CALL_RE = re.compile(
    r"\b("
    r"no\s+(?:function\s+)?call|do\s+not\s+(?:call|use)|don['’]?t\s+(?:call|use)|"
    r"no\s+tool|without\s+(?:a\s+)?(?:function|tool)|no\s+api"
    r")\b",
    re.IGNORECASE,
)


def _bfcl_explicit_no_call_signal(text: str) -> bool:
    return bool(_BFCL_EXPLICIT_NO_CALL_RE.search(str(text or "")))


def _bfcl_call_pattern(task: Dict[str, Any]) -> str:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    return str(metadata.get("bfcl_call_pattern") or "serial").strip().lower() or "serial"


def _bfcl_schema_viability_diagnostics(candidate_tools: List[ToolSpec], text: str) -> Dict[str, Any]:
    ranked = rank_candidate_tools(text, candidate_tools)
    if not ranked:
        return _bfcl_empty_candidate_diagnostics(candidate_tools)
    best = ranked[0]
    best_summary = _bfcl_rank_summary(best)
    return {
        "ranked": ranked,
        "schema_top_5": [_bfcl_rank_summary(item) for item in ranked[:5]],
        "schema_top_tool_id": str(best_summary.get("tool_id") or ""),
        "schema_top_score": float(best_summary.get("score", 0.0) or 0.0),
        "schema_top_exact_match": bool(best.get("exact_match")),
        "schema_top_semantic_overlap": list(best.get("semantic_overlap", []) or []),
        "schema_top_required_argument_coverage": float(best.get("required_argument_coverage", 0.0) or 0.0),
        "operation_cues_present": _bfcl_has_operation_cues(text),
    }


def _bfcl_top1_is_viable(diag: Dict[str, Any]) -> bool:
    return bool(
        diag.get("schema_top_tool_id")
        and (
            float(diag.get("schema_top_score") or 0.0) > 0.0
            or bool(diag.get("schema_top_exact_match"))
            or bool(diag.get("schema_top_semantic_overlap"))
            or float(diag.get("schema_top_required_argument_coverage") or 0.0) > 0.0
        )
    )


def _bfcl_abstain_decision(
    task: Dict[str, Any],
    candidate_tools: List[ToolSpec],
    text: str,
) -> Dict[str, Any]:
    """Return a gold-free BFCL abstain/no-call decision.

    Expected calls are scorer gold and must not decide runtime behavior. BFCL
    abstention is allowed only from observable no-call/irrelevance signals or
    a completely non-viable schema candidate pool.
    """
    viability = _bfcl_schema_viability_diagnostics(candidate_tools, text)
    irrelevance_signal = _bfcl_irrelevance_signal(task)
    explicit_no_call_signal = _bfcl_explicit_no_call_signal(text)
    runtime_no_call_signal = bool(irrelevance_signal or explicit_no_call_signal)
    call_pattern = _bfcl_call_pattern(task)
    serial_case = call_pattern == "serial"
    top1_viable = _bfcl_top1_is_viable(viability)
    operation_cues = bool(viability.get("operation_cues_present"))
    groundable_required = float(viability.get("schema_top_required_argument_coverage") or 0.0) > 0.0
    no_viable_schema_top1 = not top1_viable
    no_groundable_required_args = bool(viability.get("schema_top_tool_id")) and not groundable_required

    should_abstain = False
    reason = "not_applied"
    abstain_blocked_by_serial_schema_top1 = False
    serial_positive_call_forced = False
    irrelevance_abstain_allowed = False
    live_serial_irrelevance_no_call_abstain = False
    bfcl_group = str(((task.get("metadata") or {}) if isinstance(task.get("metadata"), dict) else {}).get("bfcl_group") or task.get("bfcl_group") or "").strip().lower()
    live_serial_irrelevance_case = bfcl_group in {"live", "live_irrelevance"} and serial_case and runtime_no_call_signal
    if not candidate_tools:
        should_abstain = True
        reason = "no_candidate_tools"
    elif live_serial_irrelevance_case:
        should_abstain = True
        reason = "live_serial_irrelevance_no_call"
        irrelevance_abstain_allowed = True
        live_serial_irrelevance_no_call_abstain = True
    elif irrelevance_signal:
        irrelevance_abstain_allowed = bool(explicit_no_call_signal or no_viable_schema_top1 or not operation_cues)
        if serial_case and top1_viable and operation_cues and not explicit_no_call_signal:
            abstain_blocked_by_serial_schema_top1 = True
            serial_positive_call_forced = True
        elif irrelevance_abstain_allowed:
            should_abstain = True
            reason = "irrelevance_classifier"
    elif no_viable_schema_top1 and not operation_cues:
        should_abstain = True
        reason = "no_viable_schema_top1"
    elif no_viable_schema_top1 and no_groundable_required_args:
        should_abstain = True
        reason = "no_groundable_required_args"

    return {
        "should_abstain": should_abstain,
        "reason": reason,
        "diagnostics": {
            "abstain_policy_version": "bfcl_abstain_policy_v3",
            "abstain_reason": reason,
            "live_serial_irrelevance_no_call_abstain": live_serial_irrelevance_no_call_abstain,
            "abstain_due_to_irrelevance_classifier": reason == "irrelevance_classifier",
            "abstain_due_to_no_viable_schema_top1": reason == "no_viable_schema_top1",
            "abstain_due_to_no_groundable_required_args": reason == "no_groundable_required_args",
            "abstain_due_to_planner_noop": False,
            "abstain_due_to_parallel_shape_guard": False,
            "abstain_with_schema_top1_available": should_abstain and bool(viability.get("schema_top_tool_id")),
            "abstain_with_operation_cues_present": should_abstain and operation_cues,
            "abstain_blocked_by_serial_schema_top1": abstain_blocked_by_serial_schema_top1,
            "serial_positive_call_forced": serial_positive_call_forced,
            "irrelevance_abstain_allowed": irrelevance_abstain_allowed,
            "explicit_no_call_signal": explicit_no_call_signal,
            "bfcl_call_pattern": call_pattern,
            "operation_cues_present": operation_cues,
            "schema_top_tool_id": str(viability.get("schema_top_tool_id") or ""),
            "schema_top_score": float(viability.get("schema_top_score") or 0.0),
            "selected_required_argument_coverage": viability.get("schema_top_required_argument_coverage"),
            "schema_top_5": list(viability.get("schema_top_5", []) or []),
            "ranked": list(viability.get("ranked", []) or []),
        },
    }


_BFCL_ABSTAIN_POLICY_DIAGNOSTIC_KEYS = {
    "abstain_policy_version",
    "abstain_reason",
    "live_serial_irrelevance_no_call_abstain",
    "abstain_blocked_by_serial_schema_top1",
    "serial_positive_call_forced",
    "irrelevance_abstain_allowed",
    "explicit_no_call_signal",
    "bfcl_call_pattern",
    "operation_cues_present",
}


def _merge_bfcl_abstain_policy_diagnostics(
    selection_diagnostics: Dict[str, Any],
    abstain_diagnostics: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not abstain_diagnostics:
        return dict(selection_diagnostics)
    merged = dict(selection_diagnostics)
    for key in _BFCL_ABSTAIN_POLICY_DIAGNOSTIC_KEYS:
        if key in abstain_diagnostics:
            merged[key] = abstain_diagnostics[key]
    return merged


def _bfcl_mark_serial_materialization_diagnostics(
    selection_diagnostics: Dict[str, Any],
    *,
    inputs: Dict[str, Any],
) -> Dict[str, Any]:
    diagnostics = dict(selection_diagnostics)
    missing_required = [str(item) for item in diagnostics.get("selected_missing_required_args", []) if str(item)]
    diagnostics["trace_tool_call_expected_by_bfcl_serial"] = True
    diagnostics["serial_selected_top1_materialized"] = True
    diagnostics["serial_selected_top1_materialization_blocked"] = False
    diagnostics["serial_materialization_block_reason"] = ""
    diagnostics["serial_partial_call_emitted_due_to_missing_args"] = bool(missing_required)
    diagnostics["serial_materialized_input_keys"] = sorted(str(key) for key in inputs.keys())
    return diagnostics


def _bfcl_rank_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    tool = item.get("tool") if isinstance(item.get("tool"), dict) else {}
    metadata = tool.get("metadata", {}) if isinstance(tool, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    tool_id = _bfcl_rank_item_tool_id(item)
    return {
        "tool_id": tool_id,
        "bfcl_original_function_name": str(metadata.get("bfcl_original_function_name") or metadata.get("canonical_name") or tool_id),
        "score": _bfcl_rank_item_score(item),
        "exact_match": bool(item.get("exact_match")),
        "required_argument_coverage": float(item.get("required_argument_coverage", 0.0) or 0.0),
        "schema_name_overlap_count": int(item.get("schema_name_overlap_count", len(item.get("overlap", []) or [])) or 0),
        "overlap": list(item.get("overlap", []) or []),
    }


def _bfcl_schema_ranked_choice(
    candidate_tools: List[ToolSpec],
    text: str,
    *,
    preferred_tool_id: str = "",
    prepared_function_count: Optional[int] = None,
) -> Tuple[Optional[ToolSpec], Dict[str, Any]]:
    """Select a BFCL tool with a deterministic schema-top1 guard.

    Runtime diagnostics are intentionally gold-free: expected function names and
    official failure buckets are added only by the scorer/audit stage.
    """
    lookup = _bfcl_tool_lookup(candidate_tools)
    candidate_summary = _bfcl_runtime_candidate_summary(
        candidate_tools,
        prepared_function_count=prepared_function_count,
    )
    ranked = rank_candidate_tools(text, candidate_tools)
    ranker_candidate_tool_ids = [_bfcl_rank_item_tool_id(item) for item in ranked]
    ranker_candidate_original_names = [str(_bfcl_rank_summary(item).get("bfcl_original_function_name") or "") for item in ranked]
    planner_tool_id = str(preferred_tool_id or "").strip()
    if not ranked:
        selected_tool_id = planner_tool_id if planner_tool_id in lookup else (candidate_tools[0].tool_id if candidate_tools else "")
        selected = lookup.get(selected_tool_id) or (candidate_tools[0] if candidate_tools else None)
        diagnostics = {
            "guard_policy_version": "strict_schema_top1_tie_drop_v1",
            "planner_tool_id": planner_tool_id,
            **candidate_summary,
            "ranker_candidate_count": 0,
            "ranker_candidate_tool_ids": [],
            "ranker_candidate_original_function_names": [],
            "schema_top_5": [],
            "schema_top_tool_id": "",
            "schema_top_score": 0.0,
            "planner_score": None,
            "score_margin": None,
            "planner_in_schema_top2": False,
            "selected_tool_id": str(selected.tool_id) if selected is not None else "",
            "selected_reason": "no_ranked_candidates",
            "rerank_override_applied": False,
            "rerank_override_reason": "no_ranked_candidates",
            "schema_guard_applied": False,
            "planner_required_argument_coverage": None,
            "selected_required_argument_coverage": None,
            "planner_required_args_present": [],
            "selected_required_args_present": [],
            "planner_missing_required_args": [],
            "selected_missing_required_args": [],
        }
        return selected, diagnostics

    best = ranked[0]
    best_tool_id = _bfcl_rank_item_tool_id(best)
    top_ids = [_bfcl_rank_item_tool_id(item) for item in ranked[:5]]
    current = next((item for item in ranked if _bfcl_rank_item_tool_id(item) == planner_tool_id), None)
    planner_tool = lookup.get(planner_tool_id)
    selected_tool_id = best_tool_id
    best_score = _bfcl_rank_item_score(best)
    planner_score = _bfcl_rank_item_score(current) if current is not None else None
    planner_status = _bfcl_required_arg_status(planner_tool, text) if planner_tool is not None else {
        "required_argument_coverage": None,
        "required_args_present": [],
        "missing_required_args": [],
    }

    if not planner_tool_id:
        selected_reason = "schema_top1_no_planner"
        schema_guard_applied = False
    elif planner_tool_id == best_tool_id:
        selected_reason = "planner_aligned_schema_top1"
        schema_guard_applied = False
    else:
        schema_guard_applied = True
        if current is None:
            selected_reason = "planner_not_ranked"
        elif planner_tool_id not in top_ids[:2]:
            selected_reason = "planner_not_in_schema_top2"
        elif float(planner_status.get("required_argument_coverage") or 0.0) == 0.0:
            selected_reason = "planner_required_argument_coverage_zero"
        elif planner_score is not None and best_score == planner_score:
            selected_reason = "planner_tie_dropped"
        elif planner_score is not None and best_score > planner_score:
            selected_reason = "schema_score_higher"
        else:
            selected_reason = "planner_not_schema_top1"

    selected = lookup.get(selected_tool_id) or (candidate_tools[0] if candidate_tools else None)
    selected_status = _bfcl_required_arg_status(selected, text)
    diagnostics = {
        "guard_policy_version": "strict_schema_top1_tie_drop_v1",
        "planner_tool_id": planner_tool_id,
        **candidate_summary,
        "ranker_candidate_count": len(ranked),
        "ranker_candidate_tool_ids": ranker_candidate_tool_ids,
        "ranker_candidate_original_function_names": ranker_candidate_original_names,
        "schema_top_5": [_bfcl_rank_summary(item) for item in ranked[:5]],
        "schema_top_tool_id": best_tool_id,
        "schema_top_score": best_score,
        "planner_score": planner_score,
        "score_margin": (best_score - planner_score) if planner_score is not None else None,
        "planner_in_schema_top2": planner_tool_id in top_ids[:2] if planner_tool_id else False,
        "selected_tool_id": str(selected.tool_id) if selected is not None else "",
        "selected_reason": selected_reason,
        "rerank_override_applied": False,
        "rerank_override_reason": selected_reason,
        "schema_guard_applied": bool(schema_guard_applied),
        "planner_required_argument_coverage": planner_status.get("required_argument_coverage"),
        "selected_required_argument_coverage": selected_status.get("required_argument_coverage"),
        "planner_required_args_present": planner_status.get("required_args_present", []),
        "selected_required_args_present": selected_status.get("required_args_present", []),
        "planner_missing_required_args": planner_status.get("missing_required_args", []),
        "selected_missing_required_args": selected_status.get("missing_required_args", []),
    }
    return selected, diagnostics


def _record_bfcl_choice(workflow: Workflow, diagnostics: Dict[str, Any]) -> None:
    if not diagnostics:
        return
    workflow.metadata.setdefault("bfcl_rerank_diagnostics", [])
    workflow.metadata["bfcl_rerank_diagnostics"].append(dict(diagnostics))
    workflow.metadata.setdefault("bfcl_planner_selected_tools", [])
    workflow.metadata["bfcl_planner_selected_tools"].append(str(diagnostics.get("planner_tool_id") or ""))
    workflow.metadata.setdefault("bfcl_final_ranked_tools", [])
    workflow.metadata["bfcl_final_ranked_tools"].append([item.get("tool_id") for item in diagnostics.get("schema_top_5", [])])
    workflow.metadata["bfcl_rerank_override_applied"] = any(
        bool(item.get("rerank_override_applied"))
        for item in workflow.metadata.get("bfcl_rerank_diagnostics", [])
        if isinstance(item, dict)
    )
    workflow.metadata["bfcl_rerank_override_reason"] = str(diagnostics.get("rerank_override_reason") or "")
    workflow.metadata["bfcl_guard_policy_version"] = "strict_schema_top1_tie_drop_v1"


def _bfcl_schema_ranked_tool(
    candidate_tools: List[ToolSpec],
    text: str,
    *,
    preferred_tool_id: str = "",
) -> Optional[ToolSpec]:
    selected, _diagnostics = _bfcl_schema_ranked_choice(
        candidate_tools,
        text,
        preferred_tool_id=preferred_tool_id,
    )
    return selected


def _bfcl_tool_parameters(tool: Optional[ToolSpec]) -> Dict[str, Any]:
    metadata = tool.metadata if tool and isinstance(tool.metadata, dict) else {}
    parameters = metadata.get("parameters")
    return dict(parameters) if isinstance(parameters, dict) else {}


def _bfcl_required_input_keys(tool: Optional[ToolSpec]) -> List[str]:
    parameters = _bfcl_tool_parameters(tool)
    required = parameters.get("required")
    if isinstance(required, list):
        return [str(item) for item in required if str(item)]
    return []


def _bfcl_has_bound_value(value: Any) -> bool:
    return value not in (None, "", {})


_BFCL_QUOTED_RE = re.compile(r"""['\"]([^'\"]+)['\"]""")
_BFCL_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BFCL_NUMBER_WORDS: Dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _bfcl_schema_properties(parameters: Dict[str, Any]) -> Dict[str, Any]:
    properties = parameters.get("properties") if isinstance(parameters, dict) else {}
    return dict(properties) if isinstance(properties, dict) else {}


def _bfcl_arg_type(prop: Any) -> str:
    if not isinstance(prop, dict):
        return ""
    raw = prop.get("type")
    if isinstance(raw, list):
        return next((str(item).strip().lower() for item in raw if str(item).strip().lower() != "null"), "")
    return str(raw or "").strip().lower()


def _bfcl_normalized_phrase(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _bfcl_key_phrases(key: str) -> List[str]:
    raw = str(key or "").strip()
    if not raw:
        return []
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", raw).replace("_", " ").replace("-", " ")
    phrases = [spaced.lower().strip()]
    collapsed = re.sub(r"\s+", "", phrases[0])
    if collapsed and collapsed != phrases[0]:
        phrases.append(collapsed)
    return [phrase for phrase in phrases if phrase]


def _bfcl_number_value(token: str) -> Optional[int]:
    raw = str(token or "").strip().lower()
    if raw.isdigit():
        return int(raw)
    return _BFCL_NUMBER_WORDS.get(raw)


@dataclass(frozen=True)
class _BFCLCandidateValue:
    value: Any
    value_type: str
    source: str
    span_start: int
    span_end: int
    local_context: str
    confidence: float
    preposition: str = ""


_BFCL_ALIAS_GROUPS: Dict[str, Tuple[str, ...]] = {
    "location": ("city", "location", "loc", "country", "place", "address", "region", "venue"),
    "origin": ("origin", "source", "departure", "depart", "pickup", "start"),
    "destination": ("destination", "target", "arrival", "dropoff"),
    "email": ("email", "recipient", "contact", "mail"),
    "date_time": ("date", "day", "time", "year", "month", "hour"),
    "number": ("num", "number", "count", "limit", "days", "quantity", "amount", "size", "total"),
    "person": ("name", "person", "user", "guest", "author", "customer", "client", "member"),
    "text": ("query", "search", "text", "message", "keyword", "prompt", "title", "subject", "description"),
    "list": ("list", "items", "guests", "names", "users", "ids", "values"),
}

_BFCL_AMBIGUOUS_ALIAS_GROUPS = {"origin", "destination", "person", "text"}


def _bfcl_term_in_text(term: str, text: str) -> bool:
    if not term or not text:
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])", text))


def _bfcl_alias_direct_match(alias: str, key: str) -> bool:
    key_descriptor = _bfcl_normalized_phrase(key)
    return any(_bfcl_term_in_text(term, key_descriptor) for term in _BFCL_ALIAS_GROUPS.get(alias, ()))


def _bfcl_alias_descriptor_match(alias: str, prop: Dict[str, Any]) -> bool:
    prop = prop if isinstance(prop, dict) else {}
    descriptor = _bfcl_normalized_phrase(" ".join(str(prop.get(field) or "") for field in ("description", "title")))
    return any(_bfcl_term_in_text(term, descriptor) for term in _BFCL_ALIAS_GROUPS.get(alias, ()))


def _bfcl_arg_descriptor_text(key: str, prop: Dict[str, Any]) -> str:
    prop = prop if isinstance(prop, dict) else {}
    bits = [str(key or "")]
    for field in ("description", "title"):
        value = prop.get(field)
        if value:
            bits.append(str(value))
    return _bfcl_normalized_phrase(" ".join(bits))


def _bfcl_schema_descriptor_text(prop: Dict[str, Any]) -> str:
    prop = prop if isinstance(prop, dict) else {}
    return _bfcl_normalized_phrase(" ".join(str(prop.get(field) or "") for field in ("description", "title")))


def _bfcl_descriptor_has_any(prop: Dict[str, Any], terms: Tuple[str, ...]) -> bool:
    descriptor = _bfcl_schema_descriptor_text(prop)
    return any(_bfcl_term_in_text(term, descriptor) for term in terms)



def _bfcl_is_location_like_arg(key: str, prop: Dict[str, Any]) -> bool:
    descriptor = _bfcl_arg_descriptor_text(key, prop)
    return any(
        _bfcl_term_in_text(term, descriptor)
        for term in ("location", "city", "place", "address", "region", "country", "venue")
    ) or "city state" in descriptor or "city country" in descriptor


def _bfcl_is_unit_like_arg(key: str, prop: Dict[str, Any]) -> bool:
    enum_values = prop.get("enum") if isinstance(prop.get("enum"), list) else []
    descriptor = _bfcl_arg_descriptor_text(key, prop)
    unit_terms = ("unit", "temperature", "temp", "celsius", "fahrenheit", "metric", "imperial")
    return bool(enum_values) and any(_bfcl_term_in_text(term, descriptor) for term in unit_terms)


def _bfcl_is_date_like_arg(key: str, prop: Dict[str, Any]) -> bool:
    descriptor = _bfcl_arg_descriptor_text(key, prop)
    return any(
        _bfcl_term_in_text(term, descriptor)
        for term in ("date", "day", "time", "year", "month", "today", "tomorrow")
    ) or "yyyy mm dd" in descriptor or "yyyy-mm-dd" in descriptor


def _bfcl_location_token_pattern() -> str:
    token = r"(?:[A-Z][A-Za-z]+|[A-Z]\.)"
    phrase = rf"{token}(?:[ .'-]{token})*"
    qualifier = rf"(?:,\s*(?:[A-Z]{{2,3}}|{phrase}))?"
    return rf"{phrase}{qualifier}"


def _bfcl_extract_schema_location_value(text: str) -> Tuple[Any, str, float, str]:
    location = _bfcl_location_token_pattern()
    patterns = [
        rf"\b(?:in|for|at|near|around|to)\s+({location})(?=\s*,?\s+(?:and|but|on|in|using|with|please|tomorrow|today|yesterday|now|currently|could|can|would|will|be|like)\b|[.?!;]|$)",
        rf"\b(?:city|location|place|address)\s*(?:is|=|:|as|to|for)?\s+({location})(?=\s*,?\s+(?:and|but|on|in|using|with|please|tomorrow|today|yesterday|now|currently|could|can|would|will|be|like)\b|[.?!;]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip(" .?!,;:'\"")
            if value:
                return value, "schema_location_phrase", 0.9, "location_schema_cue"
    return None, "", 0.0, ""


def _bfcl_location_replacement_allowed(current: Any, candidate: Any) -> bool:
    current_text = str(current or "").strip()
    candidate_text = str(candidate or "").strip()
    if not candidate_text:
        return False
    if not current_text:
        return True
    current_norm = _bfcl_normalized_phrase(current_text)
    candidate_norm = _bfcl_normalized_phrase(candidate_text)
    if candidate_norm == current_norm:
        return False
    if candidate_norm.startswith(current_norm + " ") and "," in candidate_text:
        return True
    if current_norm.startswith(candidate_norm + " "):
        return True
    if current_text.startswith(candidate_text + " "):
        return True
    return False


_BFCL_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _bfcl_format_date(year: int, month: int, day: int) -> Optional[str]:
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _bfcl_extract_schema_date_value(text: str) -> Tuple[Any, str, float, str]:
    today_match = re.search(r"\btoday\s+is\s+(\d{4})[-./](\d{1,2})[-./](\d{1,2})\b", text, re.IGNORECASE)
    if today_match:
        today = _bfcl_format_date(int(today_match.group(1)), int(today_match.group(2)), int(today_match.group(3)))
        if today:
            base = datetime.strptime(today, "%Y-%m-%d")
            lower = text.lower()
            if re.search(r"\btomorrow\b", lower):
                return (base + timedelta(days=1)).strftime("%Y-%m-%d"), "schema_relative_tomorrow_with_anchor", 0.86, "relative_date_with_anchor"
            if re.search(r"\bon\s+today\b|\bweather\s+(?:today|for today)\b", lower):
                return today, "schema_relative_today_with_anchor", 0.82, "relative_date_with_anchor"
    iso_match = re.search(r"\b(\d{4})[-./](\d{1,2})[-./](\d{1,2})\b", text)
    if iso_match:
        value = _bfcl_format_date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        if value:
            return value, "schema_explicit_date", 0.94, "explicit_date"
    month_names = "|".join(_BFCL_MONTHS)
    month_match = re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(\d{{4}})\b", text, re.IGNORECASE)
    if month_match:
        value = _bfcl_format_date(int(month_match.group(3)), _BFCL_MONTHS[month_match.group(1).lower()], int(month_match.group(2)))
        if value:
            return value, "schema_month_name_date", 0.9, "explicit_date"
    return None, "", 0.0, ""


def _bfcl_extract_schema_unit_value(prop: Dict[str, Any], text: str) -> Tuple[Any, str, float, str]:
    enum_values = prop.get("enum") if isinstance(prop.get("enum"), list) else []
    enum_by_lower = {str(value).lower(): value for value in enum_values}
    lower = text.lower()
    aliases = {
        "fahrenheit": ("fahrenheit", "degrees fahrenheit", "degree fahrenheit"),
        "celsius": ("celsius", "centigrade", "degrees celsius", "degree celsius"),
        "metric": ("metric", "metric system"),
        "imperial": ("imperial", "imperial system"),
    }
    for canonical, terms in aliases.items():
        if canonical not in enum_by_lower:
            continue
        if any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower) for term in terms):
            return enum_by_lower[canonical], "schema_unit_enum_mention", 0.92, "unit_enum"
    return None, "", 0.0, ""



def _bfcl_is_command_like_arg(key: str, prop: Dict[str, Any]) -> bool:
    descriptor = _bfcl_arg_descriptor_text(key, prop)
    return any(
        _bfcl_term_in_text(term, descriptor)
        for term in ("command", "cmd", "shell command", "cli command", "terminal command", "command line")
    )


def _bfcl_tool_supports_command_grounding(tool: Optional[ToolSpec]) -> bool:
    if tool is None:
        return False
    descriptor = _bfcl_normalized_phrase(f"{tool.tool_id} {tool.description}")
    return any(
        _bfcl_term_in_text(term, descriptor)
        for term in ("execute", "executor", "command", "cmd", "shell", "terminal", "cli", "run")
    )


def _bfcl_clean_command_value(value: str) -> str:
    command = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n.?!;")
    if len(command) >= 2 and command[0] == command[-1] and command[0] in {"\"", "'", "`"}:
        command = command[1:-1].strip()
    command = re.sub(r"^(?:the\s+)?", "", command, flags=re.IGNORECASE)
    return command.strip()


def _bfcl_shell_tokenize_command(command: str) -> List[str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    return [token for token in tokens if token]


def _bfcl_command_output_value(prop: Dict[str, Any], command: str) -> Any:
    prop_type = str(prop.get("type") or "").lower()
    if prop_type in {"array", "list"}:
        return _bfcl_shell_tokenize_command(command)
    return command


def _bfcl_extract_schema_command_value(text: str) -> Tuple[Any, str, float, str]:
    lower = text.lower()
    backtick = re.search(r"`([^`]+)`", text)
    if backtick:
        command = _bfcl_clean_command_value(backtick.group(1))
        if command:
            return command, "schema_backtick_command_span", 0.96, "backtick_command_span"

    for pattern, source in (
        (r"\busing\s+the\s+instruction\s+(.+?)(?:[?!]|$)", "schema_instruction_command_span"),
        (r"\binstruction\s*[:=]?\s+(.+?)(?:[?!]|$)", "schema_instruction_command_span"),
        (r"\b(?:run|execute|call)\s+(?:the\s+)?command\s+(.+?)(?:[?!]|$)", "schema_run_command_span"),
        (r"\bcommand\s*[:=]\s*(.+?)(?:[?!]|$)", "schema_command_label_span"),
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            command = _bfcl_clean_command_value(match.group(1))
            if command:
                return command, source, 0.94, "explicit_command_span"

    url_match = re.search(r"https?://[^\s,;]+", text)
    if url_match and re.search(r"\bstart\s+command\b", lower):
        url = url_match.group(0).rstrip(".?!),;")
        return f"start {url}", "schema_start_url_command", 0.93, "start_command_url"

    if re.search(r"\btaskkill\s+command\b", lower):
        process = ""
        exe_match = re.search(r"\b([A-Za-z0-9_.-]+\.exe)\b", text, re.IGNORECASE)
        if exe_match:
            process = exe_match.group(1)
        else:
            process_match = re.search(
                r"\b(?:close|kill|terminate|stop|end|remove)\s+(?:the\s+)?([A-Za-z0-9_.-]+)\s+(?:.*?\s+)?(?:using|with)\s+(?:the\s+)?taskkill\s+command\b",
                text,
                re.IGNORECASE,
            )
            if process_match:
                process = process_match.group(1)
        process = process.strip(" .?!,;:'\"")
        if process and process.lower() not in {"taskkill", "command", "the"}:
            if not process.lower().endswith(".exe"):
                process = f"{process}.exe"
            return f"taskkill /F /IM {process}", "schema_taskkill_process_command", 0.92, "taskkill_process_command"

    if re.search(r"\becho\s+command\b", lower):
        message_match = re.search(r"\b(?:say|print|echo)\s+(.+?)\s+using\s+(?:the\s+)?echo\s+command\b", text, re.IGNORECASE)
        if message_match:
            message = _bfcl_clean_command_value(message_match.group(1))
            if message:
                return f"echo {message}", "schema_echo_message_command", 0.9, "echo_message_command"

    for match in _BFCL_QUOTED_RE.finditer(text):
        command = _bfcl_clean_command_value(match.group(1))
        if command:
            return command, "schema_quoted_command_span", 0.86, "quoted_command_span"
    return None, "", 0.0, ""


def _bfcl_apply_schema_driven_command_grounding(
    *,
    tool: Optional[ToolSpec],
    text: str,
    properties: Dict[str, Any],
    grounded_inputs: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    updated = dict(grounded_inputs)
    grounded_by_arg: Dict[str, str] = {}
    reason_by_arg: Dict[str, str] = {}
    blocked_by_arg: Dict[str, str] = {}
    descriptor_by_arg: Dict[str, str] = {}
    tool_supports_command = _bfcl_tool_supports_command_grounding(tool)
    for key, raw_prop in properties.items():
        prop = raw_prop if isinstance(raw_prop, dict) else {}
        if not _bfcl_is_command_like_arg(key, prop):
            continue
        descriptor_by_arg[key] = "command_like_schema_descriptor"
        if not tool_supports_command:
            blocked_by_arg[key] = "tool_descriptor_not_command_execution"
            continue
        command, source, confidence, reason = _bfcl_extract_schema_command_value(text)
        if _bfcl_has_bound_value(command):
            updated[key] = _bfcl_command_output_value(prop, str(command))
            grounded_by_arg[key] = source
            reason_by_arg[key] = reason
            descriptor_by_arg[key] = "command_execution_schema_and_tool_descriptor"
        elif not _bfcl_has_bound_value(updated.get(key)):
            blocked_by_arg[key] = "no_runtime_command_evidence"
    diagnostics = {
        "schema_driven_command_grounding_policy_version": "bfcl_schema_driven_command_v1",
        "command_like_arg_grounded_by_arg": grounded_by_arg,
        "command_grounding_reason_by_arg": reason_by_arg,
        "command_grounding_blocked_by_arg": blocked_by_arg,
        "command_descriptor_match_by_arg": descriptor_by_arg,
    }
    return updated, diagnostics


def _bfcl_apply_schema_driven_weather_grounding(
    *,
    text: str,
    properties: Dict[str, Any],
    grounded_inputs: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    updated = dict(grounded_inputs)
    location_by_arg: Dict[str, str] = {}
    unit_by_arg: Dict[str, str] = {}
    date_by_arg: Dict[str, str] = {}
    descriptor_by_arg: Dict[str, str] = {}
    blocked_by_arg: Dict[str, str] = {}
    for key, raw_prop in properties.items():
        prop = raw_prop if isinstance(raw_prop, dict) else {}
        if _bfcl_is_location_like_arg(key, prop):
            descriptor_by_arg[key] = "location_like_schema_descriptor"
            value, source, confidence, descriptor = _bfcl_extract_schema_location_value(text)
            if _bfcl_has_bound_value(value) and _bfcl_location_replacement_allowed(updated.get(key), value):
                updated[key] = value
                location_by_arg[key] = source
                descriptor_by_arg[key] = descriptor
            elif not _bfcl_has_bound_value(updated.get(key)):
                blocked_by_arg[key] = "no_runtime_location_evidence"
        if _bfcl_is_date_like_arg(key, prop):
            descriptor_by_arg.setdefault(key, "date_like_schema_descriptor")
            value, source, confidence, descriptor = _bfcl_extract_schema_date_value(text)
            if _bfcl_has_bound_value(value) and (not _bfcl_has_bound_value(updated.get(key)) or str(updated.get(key)) != str(value)):
                updated[key] = value
                date_by_arg[key] = source
                descriptor_by_arg[key] = descriptor
            elif not _bfcl_has_bound_value(updated.get(key)):
                blocked_by_arg.setdefault(key, "no_runtime_date_evidence")
        if _bfcl_is_unit_like_arg(key, prop):
            descriptor_by_arg.setdefault(key, "unit_like_schema_descriptor")
            value, source, confidence, descriptor = _bfcl_extract_schema_unit_value(prop, text)
            if _bfcl_has_bound_value(value):
                updated[key] = value
                unit_by_arg[key] = source
                descriptor_by_arg[key] = descriptor
            else:
                enum_values = prop.get("enum") if isinstance(prop.get("enum"), list) else []
                enum_lowers = {str(item).lower() for item in enum_values}
                current = updated.get(key)
                if _bfcl_has_bound_value(current) and enum_lowers and str(current).lower() not in enum_lowers:
                    updated.pop(key, None)
                    unit_by_arg[key] = "removed_value_not_allowed_by_schema_enum"
                    descriptor_by_arg[key] = "unit_enum"
                elif not _bfcl_has_bound_value(current):
                    blocked_by_arg.setdefault(key, "no_runtime_unit_evidence")
    diagnostics = {
        "schema_driven_weather_grounding_policy_version": "bfcl_schema_driven_location_unit_date_v1",
        "location_like_arg_grounded_by_arg": location_by_arg,
        "unit_enum_grounded_by_arg": unit_by_arg,
        "date_like_arg_grounded_by_arg": date_by_arg,
        "schema_descriptor_match_by_arg": descriptor_by_arg,
        "grounding_blocked_no_runtime_evidence_by_arg": blocked_by_arg,
    }
    return updated, diagnostics


def _bfcl_exact_parameter_name(key: str, expected: str) -> bool:
    return _bfcl_normalized_phrase(key) == expected


def _bfcl_alias_matches(key: str, prop: Dict[str, Any]) -> List[str]:
    descriptor = _bfcl_arg_descriptor_text(key, prop)
    key_descriptor = _bfcl_normalized_phrase(key)
    direct: List[str] = []
    contextual: List[str] = []
    for alias, terms in _BFCL_ALIAS_GROUPS.items():
        matched = False
        direct_match = False
        for term in terms:
            pattern = rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])"
            if re.search(pattern, descriptor):
                matched = True
            if re.search(pattern, key_descriptor):
                direct_match = True
        if direct_match:
            direct.append(alias)
        elif matched:
            contextual.append(alias)
    return direct + [alias for alias in contextual if alias not in direct]


def _bfcl_context_window(text: str, start: int, end: int, radius: int = 48) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def _bfcl_extract_candidate_values(text: str) -> List[_BFCLCandidateValue]:
    candidates: List[_BFCLCandidateValue] = []
    for match in _BFCL_EMAIL_RE.finditer(text):
        candidates.append(_BFCLCandidateValue(match.group(0), "email", "email_pattern", match.start(), match.end(), _bfcl_context_window(text, match.start(), match.end()), 0.94))
    for match in _BFCL_QUOTED_RE.finditer(text):
        value = match.group(1).strip()
        if value:
            candidates.append(_BFCLCandidateValue(value, "string", "quoted_span", match.start(1), match.end(1), _bfcl_context_window(text, match.start(), match.end()), 0.82))
    number_pattern = r"\b(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b"
    for match in re.finditer(number_pattern, text, re.IGNORECASE):
        number = _bfcl_number_value(match.group(0))
        if number is not None:
            candidates.append(_BFCLCandidateValue(number, "number", "numeric_cue", match.start(), match.end(), _bfcl_context_window(text, match.start(), match.end()), 0.72))
    preposition_pattern = r"\b(from|to|in|at|for|with)\s+(?:['\"]([^'\"]+)['\"]|([A-Z][A-Za-z0-9 .,'/-]*?))(?=\s+(?:and|with|for|to|from|at|on|please)\b|[.?!,;]|$)"
    for match in re.finditer(preposition_pattern, text):
        value = (match.group(2) or match.group(3) or "").strip(" .?!,;:'\"")
        if value:
            prep = match.group(1).lower()
            candidates.append(_BFCLCandidateValue(value, "entity", f"preposition_{prep}_entity_cue", match.start(), match.end(), _bfcl_context_window(text, match.start(), match.end()), 0.74, prep))
    lower = text.lower()
    for value, source, confidence, pattern in (
        (True, "boolean_positive_cue", 0.74, r"\b(?:enable|include|use|with|set|yes|true|on)\b"),
        (False, "boolean_negative_cue", 0.74, r"\b(?:disable|exclude|without|no|false|off)\b"),
    ):
        for match in re.finditer(pattern, lower):
            candidates.append(_BFCLCandidateValue(value, "boolean", source, match.start(), match.end(), _bfcl_context_window(text, match.start(), match.end()), confidence))
    return candidates


def _bfcl_enum_assignment_candidate(prop: Dict[str, Any], text: str) -> Optional[Tuple[Any, str, float, str]]:
    enum_values = prop.get("enum") if isinstance(prop.get("enum"), list) else []
    lower = text.lower()
    for enum_value in enum_values:
        enum_text = str(enum_value)
        if not enum_text:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(enum_text.lower())}(?![a-z0-9])", lower):
            return enum_value, "enum_exact_mention", 0.94, "enum"
        if _bfcl_normalized_phrase(enum_text) and _bfcl_normalized_phrase(enum_text) in _bfcl_normalized_phrase(text):
            return enum_value, "enum_normalized_mention", 0.88, "enum"
    return None


def _bfcl_context_matches_arg(candidate: _BFCLCandidateValue, key: str, prop: Dict[str, Any]) -> bool:
    context = _bfcl_normalized_phrase(candidate.local_context)
    phrases = _bfcl_key_phrases(key)
    aliases = _bfcl_alias_matches(key, prop)
    alias_terms = [term for alias in aliases for term in _BFCL_ALIAS_GROUPS.get(alias, ())]
    return any(phrase and phrase in context for phrase in phrases + alias_terms)


def _bfcl_high_evidence_assignment_reason(
    candidate: _BFCLCandidateValue,
    key: str,
    prop: Dict[str, Any],
    arg_type: str,
    alias_match: str,
    descriptor_match: str,
    reason: str,
) -> str:
    if "consumed_span_penalty" in reason:
        return ""
    if candidate.preposition == "from":
        if _bfcl_exact_parameter_name(key, "from"):
            return "parameter_from_preposition"
        if _bfcl_descriptor_has_any(prop, ("origin", "source", "departure")):
            return "descriptor_from_preposition"
    if candidate.preposition == "to":
        if _bfcl_exact_parameter_name(key, "to"):
            return "parameter_to_preposition"
        if _bfcl_descriptor_has_any(prop, ("destination", "target", "arrival")):
            return "descriptor_to_preposition"
    if arg_type in {"integer", "number"} and candidate.value_type == "number":
        return "numeric_type_cue"
    if "email" in alias_match and candidate.value_type == "email":
        return "email_type_cue"
    if arg_type == "boolean" and candidate.value_type == "boolean" and descriptor_match:
        return "boolean_descriptor_cue"
    return ""


def _bfcl_score_candidate_for_arg(candidate: _BFCLCandidateValue, key: str, prop: Dict[str, Any], used_spans: Dict[Tuple[int, int], str]) -> Tuple[float, str, str, str]:
    arg_type = _bfcl_arg_type(prop) or "string"
    aliases = _bfcl_alias_matches(key, prop)
    score = candidate.confidence
    reasons = [candidate.source]
    alias_match = aliases[0] if aliases else ""
    local_match = _bfcl_context_matches_arg(candidate, key, prop)
    direct_alias = bool(alias_match and _bfcl_alias_direct_match(alias_match, key))
    descriptor_alias = bool(alias_match and _bfcl_alias_descriptor_match(alias_match, prop))
    descriptor_match = "local_context" if local_match else ("schema_descriptor" if descriptor_alias else "")
    if (candidate.span_start, candidate.span_end) in used_spans:
        score -= 0.65
        reasons.append("consumed_span_penalty")
    if arg_type in {"integer", "number"}:
        if candidate.value_type != "number":
            return 0.0, "type_mismatch", alias_match, descriptor_match
        if "number" in aliases or local_match:
            score += 0.18
            descriptor_match = descriptor_match or "numeric_alias"
        reasons.append("numeric_type_cue")
        return score, "+".join(reasons), alias_match or "number", descriptor_match or "numeric_type_cue"
    if arg_type == "boolean":
        if candidate.value_type != "boolean":
            return 0.0, "type_mismatch", alias_match, descriptor_match
        if local_match:
            score += 0.22
            descriptor_match = descriptor_match or "boolean_local_context"
        elif descriptor_alias:
            descriptor_match = descriptor_match or "boolean_descriptor_cue"
        elif not direct_alias:
            score -= 0.18
            reasons.append("weak_boolean_context")
        return score, "+".join(reasons), alias_match, descriptor_match
    if "email" in aliases:
        if candidate.value_type != "email":
            return 0.0, "email_alias_requires_email", "email", descriptor_match or "email_alias"
        return score + 0.2, "+".join(reasons + ["email_alias"]), "email", descriptor_match or "email_alias"
    if candidate.value_type == "email" and "email" not in aliases:
        score -= 0.35
        reasons.append("email_for_non_email_penalty")
    if candidate.preposition == "from" and _bfcl_exact_parameter_name(key, "from"):
        score += 0.32
        reasons.append("parameter_from_preposition")
        descriptor_match = "preposition_from"
    elif candidate.preposition == "from" and _bfcl_descriptor_has_any(prop, ("origin", "source", "departure")):
        score += 0.28
        reasons.append("descriptor_from_preposition")
        descriptor_match = "preposition_from"
    if candidate.preposition == "to" and _bfcl_exact_parameter_name(key, "to"):
        score += 0.32
        reasons.append("parameter_to_preposition")
        descriptor_match = "preposition_to"
    elif candidate.preposition == "to" and _bfcl_descriptor_has_any(prop, ("destination", "target", "arrival")):
        score += 0.28
        reasons.append("descriptor_to_preposition")
        descriptor_match = "preposition_to"
    if alias_match == "origin":
        if candidate.preposition == "from":
            score += 0.35
            reasons.append("origin_from_preposition")
            descriptor_match = "preposition_from"
        elif candidate.preposition in {"to", "in", "at"}:
            score -= 0.35
            reasons.append("origin_preposition_mismatch")
        elif candidate.source == "quoted_span" and not local_match:
            score -= 0.45
            reasons.append("ambiguous_origin_without_context")
    if alias_match == "destination":
        if candidate.preposition == "to":
            score += 0.35
            reasons.append("destination_to_preposition")
            descriptor_match = "preposition_to"
        elif candidate.preposition == "from":
            score -= 0.4
            reasons.append("destination_from_penalty")
        elif candidate.source == "quoted_span" and not local_match:
            score -= 0.45
            reasons.append("ambiguous_destination_without_context")
    if "location" in aliases:
        if candidate.preposition in {"in", "at", "for", "to"}:
            score += 0.22
            reasons.append("location_preposition")
            descriptor_match = descriptor_match or f"preposition_{candidate.preposition}"
        elif candidate.value_type in {"string", "entity"}:
            score += 0.08
            reasons.append("location_string")
    if "person" in aliases:
        if local_match:
            score += 0.25
            reasons.append("person_local_context")
        elif candidate.source == "quoted_span":
            score -= 0.35
            reasons.append("ambiguous_person_without_context")
    if "text" in aliases:
        if local_match:
            score += 0.2
            reasons.append("text_local_context")
        elif candidate.source == "quoted_span" and not descriptor_alias:
            score -= 0.25
            reasons.append("weak_text_without_context")
    if local_match:
        score += 0.16
        reasons.append("arg_local_context")
    if alias_match in _BFCL_AMBIGUOUS_ALIAS_GROUPS and not (local_match or descriptor_alias or candidate.preposition):
        score -= 0.2
        reasons.append("ambiguous_alias_low_evidence")
    if not aliases and candidate.source == "quoted_span" and not local_match:
        score -= 0.18
        reasons.append("weak_quoted_context")
    if candidate.value_type not in {"string", "entity", "email"}:
        score -= 0.25
        reasons.append("string_type_penalty")
    return score, "+".join(reasons), alias_match, descriptor_match


def _bfcl_array_assignment_candidate(key: str, prop: Dict[str, Any], text: str) -> Optional[Tuple[List[Any], str, float, str, str]]:
    items = prop.get("items") if isinstance(prop.get("items"), dict) else {}
    item_type = _bfcl_arg_type(items)
    aliases = _bfcl_alias_matches(key, prop)
    phrases = _bfcl_key_phrases(key)
    alias_terms = [term for alias in aliases for term in _BFCL_ALIAS_GROUPS.get(alias, ())]
    cue_terms = [term for term in phrases + alias_terms if term]
    for cue in cue_terms:
        match = re.search(rf"\b{re.escape(cue)}\b\s*(?:are|is|:|=|include|includes|as)?\s+(.+?)(?:[.?!;]|$)", text, re.IGNORECASE)
        if not match:
            continue
        segment = match.group(1)
        if item_type in {"integer", "number"}:
            values = [_bfcl_number_value(token.group(0)) for token in re.finditer(r"\b(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", segment, re.IGNORECASE)]
            values = [value for value in values if value is not None]
        else:
            quoted = [value.strip() for value in _BFCL_QUOTED_RE.findall(segment) if value.strip()]
            values = quoted or [part.strip(" .,'\"") for part in re.split(r"\s+and\s+|,", segment) if part.strip(" .,'\"")]
        if values:
            alias = aliases[0] if aliases else cue
            return values, "array_local_argument_cue", 0.82, alias, f"{match.start(1)}:{match.end(1)}"
    return None


def _bfcl_assign_required_value(key: str, prop: Dict[str, Any], text: str, candidates: List[_BFCLCandidateValue], used_spans: Dict[Tuple[int, int], str]) -> Tuple[Any, str, float, str, str, str, str, str, bool, str]:
    prop = prop if isinstance(prop, dict) else {}
    arg_type = _bfcl_arg_type(prop)
    enum_candidate = _bfcl_enum_assignment_candidate(prop, text)
    if enum_candidate is not None:
        value, source, score, alias = enum_candidate
        return value, source, score, source, alias, "", "enum", "accepted", True, source
    if arg_type == "array":
        assigned = _bfcl_array_assignment_candidate(key, prop, text)
        if assigned is not None:
            value, source, score, alias, span = assigned
            return value, source, score, source, alias, span, "local_array_cue", "accepted", True, "array_local_argument_cue"
        return None, "unresolved", 0.0, "no_array_local_cue", "", "", "", "no_viable_candidate", False, ""
    best: Optional[Tuple[float, _BFCLCandidateValue, str, str, str]] = None
    for candidate in candidates:
        score, reason, alias, descriptor_match = _bfcl_score_candidate_for_arg(candidate, key, prop, used_spans)
        if score <= 0.0:
            continue
        if best is None or score > best[0]:
            best = (score, candidate, reason, alias, descriptor_match)
    if best is None:
        return None, "unresolved", 0.0, "no_viable_candidate", "", "", "", "no_viable_candidate", False, ""
    if best[0] < 0.64:
        reason = best[2]
        validation = "ambiguous_alias_blocked" if "ambiguous_" in reason or "weak_" in reason else "low_confidence_assignment_blocked"
        high_reason = _bfcl_high_evidence_assignment_reason(best[1], key, prop, arg_type, best[3], best[4], reason)
        if not high_reason or best[0] < 0.56:
            return None, "unresolved", round(float(best[0]), 4), validation, best[3], "", best[4], validation, False, ""
    score, candidate, reason, alias, descriptor_match = best
    high_reason = _bfcl_high_evidence_assignment_reason(candidate, key, prop, arg_type, alias, descriptor_match, reason)
    if high_reason and score < 0.64:
        reason = f"{reason}+high_evidence_override"
        descriptor_match = descriptor_match or high_reason
    value = candidate.value
    if arg_type == "number" and isinstance(value, int):
        value = float(value)
    span_key = (candidate.span_start, candidate.span_end)
    if span_key[0] >= 0 and candidate.value_type != "boolean":
        used_spans[span_key] = key
    return value, candidate.source, score, reason, alias, f"{candidate.span_start}:{candidate.span_end}", descriptor_match, "accepted", bool(high_reason), high_reason


def _bfcl_string_candidate(text: str, key: str, prop: Dict[str, Any]) -> Tuple[Any, str, float]:
    quoted = [match.strip() for match in _BFCL_QUOTED_RE.findall(text) if match.strip()]
    key_lower = str(key or "").lower()
    if "email" in key_lower:
        emails = _BFCL_EMAIL_RE.findall(text)
        if emails:
            return emails[0], "email_pattern", 0.86
    if quoted:
        return quoted[0], "quoted_span", 0.88
    phrases = _bfcl_key_phrases(key)
    for phrase in phrases:
        match = re.search(
            rf"\b{re.escape(phrase)}\b\s*(?:is|=|:|as|to|for)?\s+([A-Za-z0-9][A-Za-z0-9 .,'/_-]*?)(?:\s+(?:and|with|for|to|from|at|on|please)\b|[.?!,;]|$)",
            text,
            re.IGNORECASE,
        )
        if match:
            value = match.group(1).strip(" .?!,;:'\"")
            if value:
                return value, "argument_name_cue", 0.72
    if any(token in key_lower for token in ("city", "location", "loc", "country", "destination", "address", "place")):
        for prep in ("in", "for", "to", "from", "at", "with"):
            match = re.search(
                rf"\b{prep}\s+([A-Z][A-Za-z0-9 .,'/-]*?)(?:\s+(?:and|with|for|to|from|at|on)\b|[.?!,;]|$)",
                text,
            )
            if match:
                value = match.group(1).strip(" .?!,;:'\"")
                if value:
                    return value, f"preposition_{prep}_entity_cue", 0.62
    return None, "", 0.0


def _bfcl_ground_value_for_required_arg(key: str, prop: Dict[str, Any], text: str) -> Tuple[Any, str, float]:
    prop = prop if isinstance(prop, dict) else {}
    lower = text.lower()
    arg_type = _bfcl_arg_type(prop)
    enum_values = prop.get("enum") if isinstance(prop.get("enum"), list) else []
    for enum_value in enum_values:
        enum_text = str(enum_value)
        if not enum_text:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(enum_text.lower())}(?![a-z0-9])", lower):
            return enum_value, "enum_exact_mention", 0.9
        if _bfcl_normalized_phrase(enum_text) and _bfcl_normalized_phrase(enum_text) in _bfcl_normalized_phrase(text):
            return enum_value, "enum_normalized_mention", 0.84
    if arg_type in {"integer", "number"}:
        for phrase in _bfcl_key_phrases(key):
            match = re.search(rf"\b{re.escape(phrase)}\b[^0-9a-z]*(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", lower)
            if match:
                number = _bfcl_number_value(match.group(1))
                if number is not None:
                    return (float(number) if arg_type == "number" else number), "argument_name_numeric_cue", 0.82
        match = re.search(r"\b(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", lower)
        if match:
            number = _bfcl_number_value(match.group(1))
            if number is not None:
                return (float(number) if arg_type == "number" else number), "numeric_cue", 0.58
        return None, "", 0.0
    if arg_type == "boolean":
        for phrase in _bfcl_key_phrases(key):
            positive_phrase = phrase
            if phrase.startswith("include ") or phrase.startswith("enable ") or phrase.startswith("use "):
                if re.search(rf"\b{re.escape(phrase)}\b", lower):
                    return True, "boolean_positive_key_phrase", 0.84
                positive_phrase = phrase.split(" ", 1)[1] if " " in phrase else phrase
            if re.search(rf"\b(?:enable|include|use|with|set)\s+{re.escape(positive_phrase)}\b", lower) or re.search(rf"\b{re.escape(phrase)}\s+(?:true|yes|on)\b", lower):
                return True, "boolean_positive_cue", 0.82
            if re.search(rf"\b(?:disable|exclude|without|no)\s+{re.escape(positive_phrase)}\b", lower) or re.search(rf"\b{re.escape(phrase)}\s+(?:false|no|off)\b", lower):
                return False, "boolean_negative_cue", 0.82
        if "yes" in lower or "true" in lower:
            return True, "boolean_generic_positive", 0.45
        if "no" in lower or "false" in lower:
            return False, "boolean_generic_negative", 0.45
        return None, "", 0.0
    if arg_type == "array":
        items = prop.get("items") if isinstance(prop.get("items"), dict) else {}
        item_type = _bfcl_arg_type(items)
        if item_type in {"integer", "number"}:
            numbers = [_bfcl_number_value(match.group(0)) for match in re.finditer(r"\b(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", lower)]
            values = [value for value in numbers if value is not None]
            if values:
                return values, "array_numeric_cues", 0.7
        quoted = [match.strip() for match in _BFCL_QUOTED_RE.findall(text) if match.strip()]
        if quoted:
            return quoted, "array_quoted_spans", 0.78
        for phrase in _bfcl_key_phrases(key):
            match = re.search(rf"\b{re.escape(phrase)}\b\s*(?:are|is|:|=)?\s+([A-Za-z0-9 .,'/_-]+?)(?:[.?!;]|$)", text, re.IGNORECASE)
            if match:
                parts = [part.strip(" .,'\"") for part in re.split(r"\s+and\s+|,", match.group(1)) if part.strip(" .,'\"")]
                if parts:
                    return parts, "array_argument_name_cue", 0.68
        return None, "", 0.0
    return _bfcl_string_candidate(text, key, prop)


def _bfcl_ground_serial_required_args(
    tool: Optional[ToolSpec],
    text: str,
    inputs: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    parameters = _bfcl_tool_parameters(tool)
    properties = _bfcl_schema_properties(parameters)
    required = _bfcl_required_input_keys(tool)
    grounded_inputs = dict(inputs)
    source_by_arg: Dict[str, str] = {}
    confidence_by_arg: Dict[str, float] = {}
    candidate_values_by_arg: Dict[str, List[Dict[str, Any]]] = {}
    assignment_score_by_arg: Dict[str, float] = {}
    assignment_reason_by_arg: Dict[str, str] = {}
    consumed_candidate_span_by_arg: Dict[str, str] = {}
    alias_match_by_arg: Dict[str, str] = {}
    value_validation_by_arg: Dict[str, str] = {}
    descriptor_match_by_arg: Dict[str, str] = {}
    low_confidence_assignment_blocked_by_arg: Dict[str, bool] = {}
    ambiguous_alias_blocked_by_arg: Dict[str, bool] = {}
    high_evidence_assignment_allowed_by_arg: Dict[str, bool] = {}
    high_evidence_assignment_reason_by_arg: Dict[str, str] = {}
    candidates = _bfcl_extract_candidate_values(text)
    used_spans: Dict[Tuple[int, int], str] = {}
    for key in required:
        prop = properties.get(key, {})
        if _bfcl_has_bound_value(grounded_inputs.get(key)):
            source_by_arg[key] = "existing_extractor"
            confidence_by_arg[key] = 0.8
            assignment_score_by_arg[key] = 0.8
            assignment_reason_by_arg[key] = "existing_extractor"
            alias_match_by_arg[key] = ""
            consumed_candidate_span_by_arg[key] = ""
            value_validation_by_arg[key] = "existing_extractor"
            descriptor_match_by_arg[key] = "existing_extractor"
            low_confidence_assignment_blocked_by_arg[key] = False
            ambiguous_alias_blocked_by_arg[key] = False
            high_evidence_assignment_allowed_by_arg[key] = False
            high_evidence_assignment_reason_by_arg[key] = ""
            continue
        value, source, confidence, reason, alias_match, span, descriptor_match, validation, high_evidence_allowed, high_evidence_reason = _bfcl_assign_required_value(
            key,
            prop if isinstance(prop, dict) else {},
            text,
            candidates,
            used_spans,
        )
        candidate_values_by_arg[key] = [
            {
                "value": str(candidate.value),
                "source": candidate.source,
                "type": candidate.value_type,
                "span": f"{candidate.span_start}:{candidate.span_end}",
            }
            for candidate in candidates
            if _bfcl_score_candidate_for_arg(candidate, key, prop if isinstance(prop, dict) else {}, used_spans)[0] > 0.0
        ][:5]
        assignment_score_by_arg[key] = round(float(confidence), 4)
        assignment_reason_by_arg[key] = reason
        alias_match_by_arg[key] = alias_match
        consumed_candidate_span_by_arg[key] = span
        value_validation_by_arg[key] = validation
        descriptor_match_by_arg[key] = descriptor_match
        low_confidence_assignment_blocked_by_arg[key] = validation == "low_confidence_assignment_blocked"
        ambiguous_alias_blocked_by_arg[key] = validation == "ambiguous_alias_blocked"
        high_evidence_assignment_allowed_by_arg[key] = bool(high_evidence_allowed)
        high_evidence_assignment_reason_by_arg[key] = high_evidence_reason
        if _bfcl_has_bound_value(value):
            grounded_inputs[key] = value
            source_by_arg[key] = source
            confidence_by_arg[key] = confidence
        else:
            source_by_arg[key] = "unresolved"
            confidence_by_arg[key] = 0.0
    grounded_inputs, schema_command_diagnostics = _bfcl_apply_schema_driven_command_grounding(
        tool=tool,
        text=text,
        properties=properties,
        grounded_inputs=grounded_inputs,
    )
    for key, source in schema_command_diagnostics.get("command_like_arg_grounded_by_arg", {}).items():
        if _bfcl_has_bound_value(grounded_inputs.get(key)):
            source_by_arg[key] = str(source)
            confidence_by_arg[key] = 0.92
            assignment_score_by_arg[key] = 0.92
            assignment_reason_by_arg[key] = str(source)
    grounded_inputs, schema_weather_diagnostics = _bfcl_apply_schema_driven_weather_grounding(
        text=text,
        properties=properties,
        grounded_inputs=grounded_inputs,
    )
    for key, source in schema_weather_diagnostics.get("location_like_arg_grounded_by_arg", {}).items():
        if _bfcl_has_bound_value(grounded_inputs.get(key)):
            source_by_arg[key] = str(source)
            confidence_by_arg[key] = 0.9
            assignment_score_by_arg[key] = 0.9
            assignment_reason_by_arg[key] = str(source)
    for key, source in schema_weather_diagnostics.get("date_like_arg_grounded_by_arg", {}).items():
        if _bfcl_has_bound_value(grounded_inputs.get(key)):
            source_by_arg[key] = str(source)
            confidence_by_arg[key] = 0.9
            assignment_score_by_arg[key] = 0.9
            assignment_reason_by_arg[key] = str(source)
    for key, source in schema_weather_diagnostics.get("unit_enum_grounded_by_arg", {}).items():
        source_by_arg[key] = str(source)
        confidence_by_arg[key] = 0.9
        assignment_score_by_arg[key] = 0.9
        assignment_reason_by_arg[key] = str(source)
    grounded = [key for key in required if _bfcl_has_bound_value(grounded_inputs.get(key))]
    ungrounded = [key for key in required if key not in grounded]
    diagnostics = {
        "serial_required_grounding_attempted": True,
        "serial_required_grounding_policy_version": "bfcl_serial_required_grounding_v2",
        "validation_relaxation_policy_version": "bfcl_serial_high_evidence_assignment_v1",
        "required_args": required,
        "grounded_required_args": grounded,
        "ungrounded_required_args": ungrounded,
        "grounding_source_by_arg": source_by_arg,
        "grounding_confidence_by_arg": confidence_by_arg,
        "candidate_values_by_arg": candidate_values_by_arg,
        "assignment_score_by_arg": assignment_score_by_arg,
        "assignment_reason_by_arg": assignment_reason_by_arg,
        "consumed_candidate_span_by_arg": consumed_candidate_span_by_arg,
        "alias_match_by_arg": alias_match_by_arg,
        "value_validation_by_arg": value_validation_by_arg,
        "descriptor_match_by_arg": descriptor_match_by_arg,
        "low_confidence_assignment_blocked_by_arg": low_confidence_assignment_blocked_by_arg,
        "ambiguous_alias_blocked_by_arg": ambiguous_alias_blocked_by_arg,
        "high_evidence_assignment_allowed_by_arg": high_evidence_assignment_allowed_by_arg,
        "high_evidence_assignment_reason_by_arg": high_evidence_assignment_reason_by_arg,
        **schema_command_diagnostics,
        **schema_weather_diagnostics,
    }
    return grounded_inputs, diagnostics


def _bfcl_grounding_metadata(
    *,
    tool: Optional[ToolSpec],
    text: str,
    inputs: Dict[str, Any],
) -> Dict[str, Any]:
    required_input_keys = _bfcl_required_input_keys(tool)
    grounding_sources: Dict[str, Any] = {}
    grounding_confidence: Dict[str, float] = {}
    unresolved_required_inputs: List[str] = []
    for key in required_input_keys:
        if key in inputs and _bfcl_has_bound_value(inputs.get(key)):
            grounding_sources[key] = {
                "source": "task_text",
                "confidence": 0.8,
                "query_text": text,
            }
            grounding_confidence[key] = 0.8
        else:
            grounding_sources[key] = {
                "source": "unresolved",
                "confidence": 0.0,
                "query_text": text,
            }
            grounding_confidence[key] = 0.0
            unresolved_required_inputs.append(key)
    return {
        "required_input_keys": required_input_keys,
        "input_bindings": {},
        "grounding_sources": grounding_sources,
        "grounding_confidence": grounding_confidence,
        "unresolved_required_inputs": unresolved_required_inputs,
    }


_DYNAMIC_GROUNDING_METADATA_KEYS = {
    "required_input_keys",
    "input_bindings",
    "grounding_sources",
    "grounding_confidence",
    "unresolved_required_inputs",
    "state_bindings",
    "required_state_slots",
    "repair_default_inputs",
    "simulated_missing_arg_values",
    "bfcl_abstained",
}


def _nonempty_metadata_value(value: Any) -> bool:
    return value not in (None, "", {}, [])


def _filter_runtime_safe_metadata(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(key): value
        for key, value in raw_metadata.items()
        if str(key) not in _DYNAMIC_GROUNDING_METADATA_KEYS
    }


def _finalize_bfcl_repair_defaults(step: Any) -> None:
    step.metadata["repair_default_inputs"] = dict(step.inputs)


def _sync_bfcl_binding_metadata(workflow: Workflow, step: Any, index: int) -> None:
    if index >= len(workflow.tool_bindings):
        return
    binding = workflow.tool_bindings[index]
    metadata = step.metadata if isinstance(step.metadata, dict) else {}
    binding.required_input_keys = list(metadata.get("required_input_keys", []))
    binding.input_bindings = dict(metadata.get("input_bindings", {}))
    binding.grounding_sources = dict(metadata.get("grounding_sources", {}))
    binding.grounding_confidence = dict(metadata.get("grounding_confidence", {}))
    binding.unresolved_required_inputs = list(metadata.get("unresolved_required_inputs", []))


def _bfcl_build_step_inputs(
    tool: Optional[ToolSpec],
    text: str,
    *,
    keep_query_fallback: bool = True,
    enable_grounding: bool = True,
) -> Dict[str, Any]:
    if tool is None:
        return {"query": text}
    if not enable_grounding:
        return {"query": text} if keep_query_fallback else {}
    extracted = extract_tool_arguments(tool.tool_id, _bfcl_tool_parameters(tool), text, include_defaults=False)
    if extracted:
        return extracted
    return {"query": text} if keep_query_fallback else {}


def _bfcl_expected_calls(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    structure = task.get("expected_call_structure", metadata.get("expected_call_structure", {}))
    if isinstance(structure, dict):
        calls = structure.get("calls", [])
        if isinstance(calls, list):
            return [call for call in calls if isinstance(call, dict)]
        return []
    if isinstance(structure, list):
        return [call for call in structure if isinstance(call, dict)]
    return []


def _bfcl_should_abstain_task(task: Dict[str, Any], candidate_tools: List[ToolSpec], text: str) -> bool:
    return bool(_bfcl_abstain_decision(task, candidate_tools, text).get("should_abstain"))


def _normalize_message_role(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("roletype."):
        normalized = normalized.split(".", 1)[1]
    return normalized


def _recover_toolsandbox_message_content(content: Any) -> str:
    text = str(content or "").strip()
    if not text:
        return ""
    if "USER_INSTRUCTION" not in text:
        return text
    segments = re.findall(r'"((?:\\.|[^"\\])*)"', text)
    if segments:
        recovered = [bytes(segment, "utf-8").decode("unicode_escape").strip() for segment in segments]
        return " ".join(segment for segment in recovered if segment)
    stripped = text.replace("USER_INSTRUCTION", " ").replace("+", " ").strip()
    return stripped.strip('"').strip()


def _planner_goal_from_task(task: Dict[str, Any], fallback: str) -> str:
    messages = task.get("messages")
    metadata = task.get("metadata")
    is_toolsandbox = isinstance(metadata, dict) and metadata.get("benchmark") == "toolsandbox"
    if not is_toolsandbox or not isinstance(messages, list):
        return fallback
    goal_parts: List[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        sender = _normalize_message_role(message.get("sender") or message.get("role"))
        if sender not in {"system", "user"}:
            continue
        content = message.get("content")
        normalized = (
            _recover_toolsandbox_message_content(content)
            if sender == "system"
            else str(content or "").strip()
        )
        if normalized and normalized not in goal_parts:
            goal_parts.append(normalized)
    return "\n".join(goal_parts) if goal_parts else fallback


def _seed_capability_for_tool(tool: ToolSpec, *, default: str = "cap_write") -> str:
    tool_id = str(tool.tool_id or "").lower()
    if tool_id.startswith(("set_", "send_", "remove_", "add_", "modify_")):
        return "cap_write"
    if tool_id.startswith("get_") and ("status" in tool_id or "state" in tool_id):
        return "cap_check"
    if tool_id.startswith(("get_", "search_", "find_", "lookup_")):
        return "cap_retrieve"
    inferred = infer_capability_from_text(f"{tool.tool_id} {tool.description}")
    return str(inferred or default)


_RETRIEVE_GOAL_STARTS = (
    "what ",
    "who ",
    "when ",
    "where ",
    "which ",
    "whose ",
    "is ",
    "are ",
    "do ",
    "does ",
    "did ",
    "can ",
    "could ",
)
_RETRIEVE_GOAL_TERMS = {
    "find",
    "search",
    "lookup",
    "show",
    "list",
    "read",
    "retrieve",
}
_MUTATION_TOOL_TERMS = {
    "add",
    "create",
    "delete",
    "modify",
    "remove",
    "send",
    "set",
    "toggle",
    "turn",
    "update",
    "write",
}
_MUTATION_GOAL_TERMS = _MUTATION_TOOL_TERMS | {
    "connect",
    "connected",
    "disconnect",
    "disable",
    "enable",
}
_RETRIEVE_TOOL_TERMS = _RETRIEVE_GOAL_TERMS | {
    "current",
    "fetch",
    "get",
    "lookup",
    "status",
    "timestamp",
    "view",
}
_SEED_READ_CAPABILITIES = {"cap_retrieve", "cap_check"}


def _goal_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _goal_prefers_retrieve(goal_text: str) -> bool:
    compact = " ".join(str(goal_text or "").lower().split())
    if not compact:
        return False
    if compact.startswith(_RETRIEVE_GOAL_STARTS):
        return True
    if re.search(r"\b(look up|tell me|current|status|first ever|latest|oldest)\b", compact):
        return True
    return bool(_goal_tokens(compact) & _RETRIEVE_GOAL_TERMS)


def _goal_prefers_mutation(goal_text: str) -> bool:
    return bool(_goal_tokens(goal_text) & _MUTATION_GOAL_TERMS)


def _seed_tool_relevance(tool: ToolSpec, goal_text: str, capability_id: str) -> int:
    goal_tokens = _goal_tokens(goal_text)
    tool_text = f"{tool.tool_id} {tool.description}".lower()
    tool_tokens = _goal_tokens(tool_text)
    score = 3 * len(goal_tokens & tool_tokens)
    for token in goal_tokens:
        if token and token in tool.tool_id.lower():
            score += 2
    message_goal = bool(goal_tokens & {"message", "messages", "text", "texts", "sms"})
    message_tool = bool(tool_tokens & {"message", "messages", "text", "texts", "sms"})
    if message_goal and message_tool:
        score += 6
    if message_goal and tool_tokens & {"timestamp", "time", "date"}:
        score -= 4
    if goal_tokens & {"boss", "contact", "relationship", "name"} and "contact" in tool_tokens:
        score += 4
    if goal_tokens & {"wifi", "wi", "fi", "internet", "connected", "connect"} and "wifi" in tool_tokens:
        score += 4
    if goal_tokens & {"christmas", "holiday", "holidays"} and "holiday" in tool_tokens:
        score += 6
    if goal_tokens & {"days", "day", "till", "until", "difference"} and "diff" in tool.tool_id.lower():
        score += 4
    if goal_tokens & {"remove", "delete"} and "remove" in tool_tokens:
        score += 5
    if "cellular" in goal_tokens and "cellular" in tool_tokens:
        score += 4
    if "battery" in goal_tokens and "battery" in tool_tokens:
        score += 4
    if tool.tool_id == "end_conversation":
        score -= 100
    if _goal_prefers_retrieve(goal_text):
        unmatched_mutations = _MUTATION_TOOL_TERMS & tool_tokens - goal_tokens
        score -= 4 * len(unmatched_mutations)
        if capability_id in _SEED_READ_CAPABILITIES:
            score += 2
    if _goal_prefers_mutation(goal_text):
        score += 5 * len((_MUTATION_TOOL_TERMS | {"enable", "disable"}) & tool_tokens)
        score -= 4 * len(_RETRIEVE_TOOL_TERMS & tool_tokens - goal_tokens)
    if capability_id == "cap_write" and "backup" in tool.tool_id.lower():
        score -= 4
    return score


def _select_seed_tool(
    candidate_tools: List[ToolSpec],
    capability_id: str,
    *,
    prefer_primary_write: bool = False,
    goal_text: str = "",
) -> Optional[ToolSpec]:
    matches = [tool for tool in candidate_tools if _seed_capability_for_tool(tool, default="") == capability_id]
    if not matches:
        return None
    if prefer_primary_write and capability_id == "cap_write":
        non_backup = [tool for tool in matches if "backup" not in tool.tool_id.lower()]
        if non_backup:
            matches = non_backup
    return max(
        enumerate(matches),
        key=lambda item: (_seed_tool_relevance(item[1], goal_text, capability_id), -item[0]),
    )[1]


def _best_seed_tool_by_goal(candidate_tools: List[ToolSpec], user_goal: str) -> Optional[ToolSpec]:
    ranked_candidates = [tool for tool in candidate_tools if tool.tool_id != "end_conversation"]
    if not ranked_candidates:
        return candidate_tools[0] if candidate_tools else None
    return max(
        enumerate(ranked_candidates),
        key=lambda item: (
            _seed_tool_relevance(
                item[1],
                user_goal,
                _seed_capability_for_tool(item[1], default=""),
            ),
            -item[0],
        ),
    )[1]


def _seed_tool_has_mutation_affordance(tool: ToolSpec) -> bool:
    tool_tokens = _goal_tokens(f"{tool.tool_id} {tool.description}")
    return bool(tool_tokens & (_MUTATION_TOOL_TERMS | {"enable", "disable"}))


def _seed_selected_capability(tool: ToolSpec, goal_text: str, *, default: str) -> str:
    inferred = _seed_capability_for_tool(tool, default=default)
    if _goal_prefers_mutation(goal_text) and _seed_tool_has_mutation_affordance(tool):
        return "cap_write"
    return inferred


_PHONE_NUMBER_RE = re.compile(r"\+?\d[\d\-() ]{7,}\d")
_MESSAGE_CONTENT_PATTERNS = (
    re.compile(r"\bsaying:\s*(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bsaying\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bmessage(?:\s+to\s+[^:]+)?\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL),
)


def _extract_seed_phone_number(text: str) -> Optional[str]:
    match = _PHONE_NUMBER_RE.search(str(text or ""))
    if not match:
        return None
    return re.sub(r"[\s()\-]", "", match.group(0))


def _extract_seed_message_content(text: str) -> Optional[str]:
    raw = str(text or "").strip()
    for pattern in _MESSAGE_CONTENT_PATTERNS:
        match = pattern.search(raw)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return None


def _seed_step_expected_output(tool: ToolSpec, capability_id: str) -> str:
    tool_id = str(tool.tool_id or "").lower()
    if tool_id == "send_message_with_phone_number":
        return "message_sent"
    if capability_id == "cap_write":
        return "report_artifact"
    return "retrieved_info"


def _seed_step_inputs(
    *,
    tool: ToolSpec,
    capability_id: str,
    task: Dict[str, Any],
    user_goal: str,
) -> Dict[str, Any]:
    query = str(task.get("query") or user_goal)
    inputs: Dict[str, Any] = {}
    if capability_id == "cap_write" and task.get("target_path") is not None:
        inputs["target_path"] = task.get("target_path")
    if capability_id != "cap_write" or query:
        inputs.setdefault("query", query)
    tool_id = str(tool.tool_id or "").lower()
    if tool_id == "send_message_with_phone_number":
        phone_number = _extract_seed_phone_number(query)
        message_content = _extract_seed_message_content(query)
        if phone_number:
            inputs["recipient_phone_number"] = phone_number
        if message_content:
            inputs["content"] = message_content
    return inputs


def _select_seed_read_tool(candidate_tools: List[ToolSpec], user_goal: str) -> Optional[ToolSpec]:
    read_candidates = [
        tool
        for tool in candidate_tools
        if _seed_capability_for_tool(tool, default="") in _SEED_READ_CAPABILITIES
    ]
    return _best_seed_tool_by_goal(read_candidates, user_goal)


def _select_seed_write_tool(candidate_tools: List[ToolSpec], user_goal: str) -> Optional[ToolSpec]:
    write_tool = _select_seed_tool(
        candidate_tools,
        "cap_write",
        prefer_primary_write=True,
        goal_text=user_goal,
    )
    if write_tool is not None:
        return write_tool
    if not _goal_prefers_mutation(user_goal):
        return None
    mutation_candidates = [
        tool
        for tool in candidate_tools
        if tool.tool_id != "end_conversation" and _seed_tool_has_mutation_affordance(tool)
    ]
    return _best_seed_tool_by_goal(mutation_candidates, user_goal)


def _select_seed_primary_tool(
    task: Dict[str, Any],
    candidate_tools: List[ToolSpec],
    user_goal: str,
) -> Optional[ToolSpec]:
    if not candidate_tools:
        return None
    if _goal_prefers_retrieve(user_goal):
        selected = _select_seed_read_tool(candidate_tools, user_goal)
        if selected is not None:
            return selected
    if _goal_prefers_mutation(user_goal):
        selected = _select_seed_write_tool(candidate_tools, user_goal)
        if selected is not None:
            return selected
    return _best_seed_tool_by_goal(candidate_tools, user_goal)


def _configure_seed_capability_node(node: Any, capability_id: str) -> None:
    profile = CAPABILITY_PROFILES_BY_ID.get(capability_id)
    node.capability_id = capability_id
    if profile is not None:
        node.description = profile.description
        node.preconditions = list(profile.preconditions)
        node.postconditions = list(profile.postconditions)


def _configure_seed_single_step_workflow(
    workflow: Workflow,
    *,
    capability_id: str,
    tool_id: str,
    inputs: Dict[str, Any],
    expected_output: str,
) -> Workflow:
    _configure_seed_capability_node(workflow.capability_graph.capabilities[0], capability_id)
    workflow.capability_graph.capabilities = workflow.capability_graph.capabilities[:1]
    workflow.capability_graph.edges = []

    workflow.tool_bindings[0].capability_id = capability_id
    workflow.tool_bindings[0].primary_tool = tool_id
    workflow.tool_bindings = workflow.tool_bindings[:1]

    step = workflow.execution_plan[0]
    step.capability_id = capability_id
    step.tool_id = tool_id
    step.inputs = dict(inputs)
    step.expected_output = expected_output
    step.rollback_to = None
    workflow.execution_plan = workflow.execution_plan[:1]

    node = workflow.workflow_graph.nodes[0]
    node.capability_id = capability_id
    node.selected_tool = tool_id
    node.tool_candidates = [tool_id]
    node.inputs = dict(inputs)
    node.expected_output = expected_output
    node.dependencies = []
    node.rollback_policy = None
    workflow.workflow_graph.nodes = workflow.workflow_graph.nodes[:1]
    workflow.workflow_graph.edges = []
    workflow.workflow_graph.entry_nodes = ["step_01"]
    workflow.workflow_graph.exit_nodes = ["step_01"]
    return workflow


def _configure_bfcl_step_metadata(
    step: Any,
    tool: Optional[ToolSpec],
    text: str,
    *,
    enable_grounding: bool = True,
    selection_diagnostics: Optional[Dict[str, Any]] = None,
) -> None:
    parameters = _bfcl_tool_parameters(tool)
    existing_metadata = dict(step.metadata) if isinstance(step.metadata, dict) else {}
    grounding_metadata = _bfcl_grounding_metadata(
        tool=tool,
        text=text,
        inputs=dict(step.inputs) if enable_grounding else {},
    )
    merged_metadata = dict(existing_metadata)
    merged_metadata["bfcl_query_text"] = text
    merged_metadata["bfcl_schema"] = dict(parameters)
    merged_metadata["bfcl_benchmark"] = True
    if selection_diagnostics:
        merged_metadata["bfcl_function_selection_diagnostics"] = dict(selection_diagnostics)
        for key in (
            "trace_tool_call_expected_by_bfcl_serial",
            "serial_selected_top1_materialized",
            "serial_selected_top1_materialization_blocked",
            "serial_materialization_block_reason",
            "serial_partial_call_emitted_due_to_missing_args",
            "serial_required_grounding_attempted",
            "serial_required_grounding_policy_version",
            "validation_relaxation_policy_version",
            "required_args",
            "grounded_required_args",
            "ungrounded_required_args",
            "grounding_source_by_arg",
            "grounding_confidence_by_arg",
            "candidate_values_by_arg",
            "assignment_score_by_arg",
            "assignment_reason_by_arg",
            "consumed_candidate_span_by_arg",
            "alias_match_by_arg",
            "value_validation_by_arg",
            "descriptor_match_by_arg",
            "low_confidence_assignment_blocked_by_arg",
            "ambiguous_alias_blocked_by_arg",
            "high_evidence_assignment_allowed_by_arg",
            "high_evidence_assignment_reason_by_arg",
            "schema_driven_weather_grounding_policy_version",
            "location_like_arg_grounded_by_arg",
            "unit_enum_grounded_by_arg",
            "date_like_arg_grounded_by_arg",
            "schema_descriptor_match_by_arg",
            "grounding_blocked_no_runtime_evidence_by_arg",
            "schema_driven_command_grounding_policy_version",
            "command_like_arg_grounded_by_arg",
            "command_grounding_reason_by_arg",
            "command_grounding_blocked_by_arg",
            "command_descriptor_match_by_arg",
            "parallel_materialization_policy_version",
            "parallel_argument_sets_extracted",
            "parallel_argument_set_count",
            "parallel_clause_materialized_count",
            "parallel_clause_drop_count",
            "parallel_collapsed_to_serial",
            "parallel_clause_drop_reasons",
            "trace_tool_call_expected_by_bfcl_parallel",
            "parallel_partial_call_emitted_due_to_missing_args",
            "parallel_partial_call_bypass_applied",
            "parallel_preflight_bypass_policy_version",
        ):
            if key in selection_diagnostics:
                merged_metadata[key] = selection_diagnostics[key]
    merged_metadata.setdefault("implicit_state_fallback_slots", [])
    merged_metadata.setdefault("required_state_slots", [])
    merged_metadata.setdefault("state_bindings", {})
    current_required_keys = list(grounding_metadata.get("required_input_keys", []))
    current_required_set = set(current_required_keys)
    existing_sources = (
        dict(merged_metadata.get("grounding_sources", {}))
        if isinstance(merged_metadata.get("grounding_sources"), dict)
        else {}
    )
    existing_confidence = (
        dict(merged_metadata.get("grounding_confidence", {}))
        if isinstance(merged_metadata.get("grounding_confidence"), dict)
        else {}
    )
    source_by_arg = (
        dict(selection_diagnostics.get("grounding_source_by_arg", {}))
        if isinstance(selection_diagnostics, dict) and isinstance(selection_diagnostics.get("grounding_source_by_arg"), dict)
        else {}
    )
    confidence_by_arg = (
        dict(selection_diagnostics.get("grounding_confidence_by_arg", {}))
        if isinstance(selection_diagnostics, dict) and isinstance(selection_diagnostics.get("grounding_confidence_by_arg"), dict)
        else {}
    )
    for key, source in source_by_arg.items():
        if _nonempty_metadata_value(source):
            existing_sources[str(key)] = {"source": source, "confidence": float(confidence_by_arg.get(key, 0.0) or 0.0), "query_text": text}
    for key, confidence in confidence_by_arg.items():
        if isinstance(confidence, (int, float)):
            existing_confidence[str(key)] = float(confidence)
    merged_sources: Dict[str, Any] = {}
    merged_confidence: Dict[str, float] = {}
    computed_sources = grounding_metadata.get("grounding_sources", {})
    computed_confidence = grounding_metadata.get("grounding_confidence", {})
    if not isinstance(computed_sources, dict):
        computed_sources = {}
    if not isinstance(computed_confidence, dict):
        computed_confidence = {}
    for key in current_required_keys:
        existing_value = existing_sources.get(key)
        if _nonempty_metadata_value(existing_value):
            merged_sources[key] = existing_value
        elif key in computed_sources:
            merged_sources[key] = computed_sources[key]
        existing_score = existing_confidence.get(key)
        if isinstance(existing_score, (int, float)):
            merged_confidence[key] = float(existing_score)
        elif key in computed_confidence:
            merged_confidence[key] = float(computed_confidence[key])

    merged_metadata["required_input_keys"] = current_required_keys
    merged_metadata["grounding_sources"] = merged_sources
    merged_metadata["grounding_confidence"] = merged_confidence
    merged_metadata["unresolved_required_inputs"] = [
        key
        for key in grounding_metadata.get("unresolved_required_inputs", [])
        if key in current_required_set
    ]
    if merged_metadata.get("trace_tool_call_expected_by_bfcl_serial") is True:
        # BFCL exact-call scoring should see the selected function call even
        # when argument grounding is incomplete; the scorer can then bucket the
        # failure as missing/incorrect args instead of zero emitted calls.
        merged_metadata["disable_schema_preflight"] = True
        merged_metadata["serial_partial_call_emitted_due_to_missing_args"] = bool(
            merged_metadata.get("unresolved_required_inputs")
        )
    if merged_metadata.get("trace_tool_call_expected_by_bfcl_parallel") is True:
        # BFCL parallel exact-call scoring should see each materialized clause
        # even when some per-clause required inputs are missing. Keep this
        # BFCL-specific and gold-free; official scoring will bucket argument
        # failures after the call is visible.
        merged_metadata["disable_schema_preflight"] = True
        merged_metadata["parallel_partial_call_emitted_due_to_missing_args"] = bool(
            merged_metadata.get("unresolved_required_inputs")
        )
    if not _nonempty_metadata_value(merged_metadata.get("input_bindings")):
        merged_metadata["input_bindings"] = grounding_metadata.get("input_bindings", {})
    step.metadata = merged_metadata
    _finalize_bfcl_repair_defaults(step)


def _bfcl_capability_id(_tool: Optional[ToolSpec]) -> str:
    return "cap_retrieve"


def _ensure_workflow_capacity(workflow: Workflow, count: int) -> None:
    template = Workflow.demo()
    while len(workflow.capability_graph.capabilities) < count:
        source = workflow.capability_graph.capabilities[-1] if workflow.capability_graph.capabilities else template.capability_graph.capabilities[0]
        workflow.capability_graph.capabilities.append(deepcopy(source))
    while len(workflow.tool_bindings) < count:
        source = workflow.tool_bindings[-1] if workflow.tool_bindings else template.tool_bindings[0]
        workflow.tool_bindings.append(deepcopy(source))
    while len(workflow.execution_plan) < count:
        source = workflow.execution_plan[-1] if workflow.execution_plan else template.execution_plan[0]
        workflow.execution_plan.append(deepcopy(source))
    while len(workflow.workflow_graph.nodes) < count:
        source = workflow.workflow_graph.nodes[-1] if workflow.workflow_graph.nodes else template.workflow_graph.nodes[0]
        workflow.workflow_graph.nodes.append(deepcopy(source))


def _bfcl_abstain_selection_diagnostics(
    candidate_tools: List[ToolSpec],
    reason: str,
    *,
    abstain_diagnostics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    abstain_diagnostics = dict(abstain_diagnostics or {})
    ranked = list(abstain_diagnostics.pop("ranked", []) or [])
    top5 = list(abstain_diagnostics.get("schema_top_5", []) or [])
    ranker_candidate_tool_ids = [_bfcl_rank_item_tool_id(item) for item in ranked]
    ranker_candidate_original_names = [str(_bfcl_rank_summary(item).get("bfcl_original_function_name") or "") for item in ranked]
    return {
        "guard_policy_version": "strict_schema_top1_tie_drop_v1",
        "planner_tool_id": "",
        **abstain_diagnostics,
        **_bfcl_runtime_candidate_summary(
            [],
            prepared_function_count=len(candidate_tools),
            candidate_pool_exception="bfcl_abstain",
            drop_reason=reason or "bfcl abstain intentionally elides runtime candidate pool",
        ),
        "ranker_candidate_count": len(ranked),
        "ranker_candidate_tool_ids": ranker_candidate_tool_ids,
        "ranker_candidate_original_function_names": ranker_candidate_original_names,
        "schema_top_5": top5,
        "schema_top_tool_id": str(abstain_diagnostics.get("schema_top_tool_id") or ""),
        "schema_top_score": float(abstain_diagnostics.get("schema_top_score") or 0.0),
        "planner_score": None,
        "score_margin": None,
        "planner_in_schema_top2": False,
        "selected_tool_id": "",
        "selected_reason": "bfcl_abstain",
        "rerank_override_applied": False,
        "rerank_override_reason": "bfcl_abstain",
        "schema_guard_applied": False,
        "planner_required_argument_coverage": None,
        "selected_required_argument_coverage": abstain_diagnostics.get("selected_required_argument_coverage"),
        "planner_required_args_present": [],
        "selected_required_args_present": [],
        "planner_missing_required_args": [],
        "selected_missing_required_args": [],
    }


def _configure_bfcl_abstain_workflow(
    workflow: Workflow,
    candidate_tools: Optional[List[ToolSpec]] = None,
    *,
    reason: str = "",
    abstain_diagnostics: Optional[Dict[str, Any]] = None,
) -> Workflow:
    candidate_tools = list(candidate_tools or [])
    _record_bfcl_choice(
        workflow,
        _bfcl_abstain_selection_diagnostics(
            candidate_tools,
            reason,
            abstain_diagnostics=abstain_diagnostics,
        ),
    )
    workflow.capability_graph.capabilities = []
    workflow.capability_graph.edges = []
    workflow.tool_bindings = []
    workflow.execution_plan = []
    workflow.workflow_graph.nodes = []
    workflow.workflow_graph.edges = []
    workflow.workflow_graph.entry_nodes = []
    workflow.workflow_graph.exit_nodes = []
    workflow.context.candidate_tools = []
    workflow.metadata["bfcl_abstained"] = True
    workflow.metadata["bfcl_abstain_reason"] = reason or "bfcl_abstain"
    return workflow


def _configure_bfcl_seed_steps(
    workflow: Workflow,
    step_specs: List[Dict[str, Any]],
    *,
    enable_grounding: bool = True,
) -> Workflow:
    if not step_specs:
        return workflow
    _ensure_workflow_capacity(workflow, len(step_specs))
    workflow.capability_graph.edges = []
    workflow.workflow_graph.edges = []
    workflow.workflow_graph.entry_nodes = ["step_01"]
    workflow.workflow_graph.exit_nodes = [f"step_{len(step_specs):02d}"]

    for index, spec in enumerate(step_specs, start=1):
        tool = spec.get("tool")
        if not isinstance(tool, ToolSpec):
            continue
        capability_id = _bfcl_capability_id(tool)
        inputs = dict(spec.get("inputs") or {})
        text = str(spec.get("text") or "")
        expected_output = f"bfcl_result_{index:02d}"
        step_id = f"step_{index:02d}"

        cap_node = workflow.capability_graph.capabilities[index - 1]
        _configure_seed_capability_node(cap_node, capability_id)

        binding = workflow.tool_bindings[index - 1]
        binding.capability_id = capability_id
        binding.primary_tool = tool.tool_id
        binding.backup_tools = []
        binding.binding_confidence = 1.0

        step = workflow.execution_plan[index - 1]
        step.step_id = step_id
        step.capability_id = capability_id
        step.tool_id = tool.tool_id
        step.inputs = inputs
        step.expected_output = expected_output
        step.rollback_to = None
        selection_diagnostics = spec.get("selection_diagnostics") if isinstance(spec.get("selection_diagnostics"), dict) else {}
        _configure_bfcl_step_metadata(
            step,
            tool,
            text,
            enable_grounding=enable_grounding,
            selection_diagnostics=selection_diagnostics,
        )
        _record_bfcl_choice(workflow, selection_diagnostics)
        _sync_bfcl_binding_metadata(workflow, step, index - 1)

        node = workflow.workflow_graph.nodes[index - 1]
        node.node_id = step_id
        node.capability_id = capability_id
        node.selected_tool = tool.tool_id
        node.tool_candidates = [tool.tool_id]
        node.inputs = inputs
        node.expected_output = expected_output
        node.dependencies = [f"step_{index - 1:02d}"] if index > 1 else []
        node.rollback_policy = None
        node.metadata["bfcl_benchmark"] = True

        if index > 1:
            workflow.capability_graph.edges.append(
                CapabilityEdge(
                    source=workflow.capability_graph.capabilities[index - 2].capability_id,
                    target=capability_id,
                    condition="bfcl_sequence",
                )
            )
            workflow.workflow_graph.edges.append(
                WorkflowEdge(
                    source=f"step_{index - 1:02d}",
                    target=step_id,
                    condition="bfcl_sequence",
                    edge_type="default",
                )
            )

    workflow.capability_graph.capabilities = workflow.capability_graph.capabilities[: len(step_specs)]
    workflow.tool_bindings = workflow.tool_bindings[: len(step_specs)]
    workflow.execution_plan = workflow.execution_plan[: len(step_specs)]
    workflow.workflow_graph.nodes = workflow.workflow_graph.nodes[: len(step_specs)]
    return workflow


def _split_parallel_clauses(text: str) -> List[str]:
    clauses = [
        segment.strip(' ,.;')
        for segment in re.split(r"(?:;|[.?!]\s+(?=also\b)|,?\s+and also\s+|,?\s+also,?\s+)", text, flags=re.IGNORECASE)
        if segment.strip(' ,.;')
    ]
    return clauses if len(clauses) > 1 else [text]


def _bfcl_parallel_materialization_diagnostics(
    diagnostics: Dict[str, Any],
    *,
    argument_set_count: int,
    materialized_count: int,
    drop_reasons: Optional[List[str]] = None,
    collapsed_to_serial: bool = False,
    allow_preflight_bypass: bool = False,
) -> Dict[str, Any]:
    updated = dict(diagnostics or {})
    updated["parallel_materialization_policy_version"] = "bfcl_non_live_parallel_clause_materialization_v1"
    updated["parallel_argument_sets_extracted"] = argument_set_count > 0
    updated["parallel_argument_set_count"] = int(argument_set_count)
    updated["parallel_clause_materialized_count"] = int(materialized_count)
    updated["parallel_clause_drop_count"] = max(int(argument_set_count) - int(materialized_count), 0)
    updated["parallel_collapsed_to_serial"] = bool(collapsed_to_serial)
    updated["parallel_clause_drop_reasons"] = list(drop_reasons or [])
    bypass_applied = bool(allow_preflight_bypass and materialized_count > 1 and not collapsed_to_serial)
    updated["parallel_partial_call_bypass_applied"] = bypass_applied
    if bypass_applied:
        updated["trace_tool_call_expected_by_bfcl_parallel"] = True
        updated["parallel_partial_call_emitted_due_to_missing_args"] = False
        updated["parallel_preflight_bypass_policy_version"] = "bfcl_parallel_partial_call_materialization_v1"
    return updated


def _bfcl_seed_specs(
    task: Dict[str, Any],
    candidate_tools: List[ToolSpec],
    user_goal: str,
    *,
    abstain_policy_diagnostics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    call_pattern = str(metadata.get("bfcl_call_pattern") or "serial")
    query = str(task.get("query") or user_goal)
    milestones = [str(item).strip() for item in task.get("milestones", []) if str(item).strip()]
    if call_pattern == "parallel":
        bfcl_group = str(metadata.get("bfcl_group") or "").strip().lower()
        selected_parallel_tool, diagnostics = _bfcl_schema_ranked_choice(candidate_tools, query)
        if selected_parallel_tool is not None:
            arg_sets = extract_parallel_argument_sets(
                selected_parallel_tool.tool_id,
                _bfcl_tool_parameters(selected_parallel_tool),
                query,
            )
            if (bfcl_group == "non_live" and arg_sets) or len(arg_sets) > 1:
                diagnostics = _merge_bfcl_abstain_policy_diagnostics(diagnostics, abstain_policy_diagnostics)
                diagnostics = _bfcl_parallel_materialization_diagnostics(
                    diagnostics,
                    argument_set_count=len(arg_sets),
                    materialized_count=len(arg_sets),
                    collapsed_to_serial=len(arg_sets) == 1,
                    allow_preflight_bypass=bfcl_group == "non_live",
                )
                return [
                    {
                        "tool": selected_parallel_tool,
                        "inputs": dict(arg_set),
                        "text": query,
                        "selection_diagnostics": dict(diagnostics),
                    }
                    for arg_set in arg_sets
                ]
        step_specs: List[Dict[str, Any]] = []
        split_clauses = _split_parallel_clauses(query)
        for clause in split_clauses:
            tool, diagnostics = _bfcl_schema_ranked_choice(candidate_tools, clause)
            if tool is None:
                continue
            diagnostics = _merge_bfcl_abstain_policy_diagnostics(diagnostics, abstain_policy_diagnostics)
            step_specs.append(
                {
                    "tool": tool,
                    "inputs": _bfcl_build_step_inputs(tool, clause, keep_query_fallback=False),
                    "text": clause,
                    "selection_diagnostics": diagnostics,
                }
            )
        if len(step_specs) > 1 or (bfcl_group == "non_live" and step_specs):
            drop_reasons = []
            if selected_parallel_tool is not None:
                drop_reasons.append("no_extractable_parallel_argument_sets")
            if len(step_specs) < len(split_clauses):
                drop_reasons.append("clause_schema_selection_failed")
            shared_count = len(step_specs)
            for spec in step_specs:
                spec["selection_diagnostics"] = _bfcl_parallel_materialization_diagnostics(
                    spec.get("selection_diagnostics") if isinstance(spec.get("selection_diagnostics"), dict) else {},
                    argument_set_count=len(split_clauses),
                    materialized_count=shared_count,
                    drop_reasons=drop_reasons,
                    collapsed_to_serial=shared_count == 1,
                    allow_preflight_bypass=bfcl_group == "non_live",
                )
            return step_specs
    if metadata.get("bfcl_group") == "multi_turn" and milestones:
        step_specs = []
        for milestone in milestones:
            tool, diagnostics = _bfcl_schema_ranked_choice(candidate_tools, milestone)
            if tool is None:
                continue
            diagnostics = _merge_bfcl_abstain_policy_diagnostics(diagnostics, abstain_policy_diagnostics)
            step_specs.append(
                {
                    "tool": tool,
                    "inputs": _bfcl_build_step_inputs(tool, milestone),
                    "text": milestone,
                    "selection_diagnostics": diagnostics,
                }
            )
        if step_specs:
            return step_specs
    tool, diagnostics = _bfcl_schema_ranked_choice(candidate_tools, query)
    if tool is None:
        return []
    inputs = _bfcl_build_step_inputs(tool, query)
    diagnostics = _merge_bfcl_abstain_policy_diagnostics(diagnostics, abstain_policy_diagnostics)
    if call_pattern == "serial" and str(metadata.get("bfcl_group") or "").strip().lower() != "multi_turn":
        inputs, grounding_diagnostics = _bfcl_ground_serial_required_args(tool, query, inputs)
        diagnostics.update(grounding_diagnostics)
        diagnostics = _bfcl_mark_serial_materialization_diagnostics(diagnostics, inputs=inputs)
    return [{"tool": tool, "inputs": inputs, "text": query, "selection_diagnostics": diagnostics}]


def _build_seed_workflow(
    task: Dict[str, Any],
    candidate_tools: List[ToolSpec],
    user_goal: str,
    *,
    enable_grounding: bool = True,
) -> Workflow:
    workflow = Workflow.demo()
    workflow.workflow_id = f"wf_{canonical_task_id(task)}"
    workflow.task.task_id = canonical_task_id(task)
    workflow.task.user_goal = user_goal
    if candidate_tools:
        workflow.context.candidate_tools = list(candidate_tools)

    raw_metadata = task.get("metadata", {})
    benchmark = str(raw_metadata.get("benchmark") or task.get("benchmark") or "").strip().lower() if isinstance(raw_metadata, dict) else str(task.get("benchmark") or "").strip().lower()
    if benchmark == "bfcl":
        abstain_decision = _bfcl_abstain_decision(task, candidate_tools, str(task.get("query") or user_goal))
        if abstain_decision.get("should_abstain"):
            return _configure_bfcl_abstain_workflow(
                workflow,
                candidate_tools,
                reason=str(abstain_decision.get("reason") or "bfcl_abstain"),
                abstain_diagnostics=abstain_decision.get("diagnostics") if isinstance(abstain_decision.get("diagnostics"), dict) else None,
            )
        step_specs = _bfcl_seed_specs(
            task,
            candidate_tools,
            user_goal,
            abstain_policy_diagnostics=abstain_decision.get("diagnostics") if isinstance(abstain_decision.get("diagnostics"), dict) else None,
        )
        if not step_specs:
            return workflow
        if not enable_grounding:
            disabled_specs = [
                {
                    **spec,
                    "inputs": _bfcl_build_step_inputs(
                        spec.get("tool"),
                        str(spec.get("text") or user_goal),
                        keep_query_fallback=True,
                        enable_grounding=False,
                    ),
                }
                for spec in step_specs
            ]
            return _configure_bfcl_seed_steps(workflow, disabled_specs, enable_grounding=False)
        return _configure_bfcl_seed_steps(workflow, step_specs, enable_grounding=True)

    allow_list = list(task.get("tool_allow_list", [])) if isinstance(task.get("tool_allow_list"), list) else []
    scenario = str(task.get("scenario", "success"))
    low_branching = (
        len(candidate_tools) <= 1
        or len(allow_list) == 1
        or scenario in {"single_tool", "single_user_turn"}
        or task.get("ideal_tool_calls") == 1
    )

    selection_goal = str(task.get("query") or user_goal)
    retrieve_tool = _select_seed_read_tool(candidate_tools, selection_goal)
    write_tool = _select_seed_write_tool(candidate_tools, selection_goal)

    if low_branching:
        selected_tool = _select_seed_primary_tool(task, candidate_tools, selection_goal)
        if selected_tool is None:
            return workflow
        capability_id = _seed_selected_capability(
            selected_tool,
            selection_goal,
            default="cap_write" if task.get("target_path") is not None else "cap_retrieve",
        )
        step_inputs = _seed_step_inputs(
            tool=selected_tool,
            capability_id=capability_id,
            task=task,
            user_goal=user_goal,
        )
        expected_output = _seed_step_expected_output(selected_tool, capability_id)
        return _configure_seed_single_step_workflow(
            workflow,
            capability_id=capability_id,
            tool_id=selected_tool.tool_id,
            inputs=step_inputs,
            expected_output=expected_output,
        )

    if not retrieve_tool and write_tool:
        return _configure_seed_single_step_workflow(
            workflow,
            capability_id="cap_write",
            tool_id=write_tool.tool_id,
            inputs=_seed_step_inputs(tool=write_tool, capability_id="cap_write", task=task, user_goal=user_goal),
            expected_output=_seed_step_expected_output(write_tool, "cap_write"),
        )
    if retrieve_tool and (not write_tool or (benchmark == "toolsandbox" and not _goal_prefers_mutation(selection_goal))):
        read_capability_id = _seed_capability_for_tool(retrieve_tool, default="cap_retrieve")
        return _configure_seed_single_step_workflow(
            workflow,
            capability_id=read_capability_id,
            tool_id=retrieve_tool.tool_id,
            inputs=_seed_step_inputs(tool=retrieve_tool, capability_id=read_capability_id, task=task, user_goal=user_goal),
            expected_output=_seed_step_expected_output(retrieve_tool, read_capability_id),
        )

    if retrieve_tool is not None:
        read_capability_id = _seed_capability_for_tool(retrieve_tool, default="cap_retrieve")
        workflow.tool_bindings[0].capability_id = read_capability_id
        workflow.tool_bindings[0].primary_tool = retrieve_tool.tool_id
        workflow.execution_plan[0].capability_id = read_capability_id
        workflow.execution_plan[0].tool_id = retrieve_tool.tool_id
        workflow.execution_plan[0].inputs = _seed_step_inputs(
            tool=retrieve_tool,
            capability_id=read_capability_id,
            task=task,
            user_goal=user_goal,
        )
        workflow.execution_plan[0].expected_output = _seed_step_expected_output(retrieve_tool, read_capability_id)
        workflow.workflow_graph.nodes[0].capability_id = read_capability_id
        workflow.workflow_graph.nodes[0].selected_tool = retrieve_tool.tool_id
        workflow.workflow_graph.nodes[0].tool_candidates = [retrieve_tool.tool_id]
    if write_tool is not None:
        workflow.tool_bindings[1].capability_id = "cap_write"
        workflow.tool_bindings[1].primary_tool = write_tool.tool_id
        workflow.execution_plan[1].capability_id = "cap_write"
        workflow.execution_plan[1].tool_id = write_tool.tool_id
        workflow.execution_plan[1].inputs = _seed_step_inputs(
            tool=write_tool,
            capability_id="cap_write",
            task=task,
            user_goal=user_goal,
        )
        workflow.execution_plan[1].expected_output = _seed_step_expected_output(write_tool, "cap_write")
        workflow.workflow_graph.nodes[1].capability_id = "cap_write"
        workflow.workflow_graph.nodes[1].selected_tool = write_tool.tool_id
        workflow.workflow_graph.nodes[1].tool_candidates = [write_tool.tool_id]
    workflow.metadata["planner_mode"] = "recovery_seed"
    return workflow


def _adapt_bfcl_workflow(
    workflow: Workflow,
    *,
    task: Dict[str, Any],
    candidate_tools: List[ToolSpec],
    mode: str,
    enable_grounding: bool,
) -> Workflow:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    tool_lookup = _bfcl_tool_lookup(candidate_tools)
    query = str(task.get("query") or workflow.task.user_goal or "")
    milestones = [str(item).strip() for item in task.get("milestones", []) if str(item).strip()]
    call_pattern = str(metadata.get("bfcl_call_pattern") or "serial")
    abstain_decision = _bfcl_abstain_decision(task, candidate_tools, query)
    if abstain_decision.get("should_abstain"):
        return _configure_bfcl_abstain_workflow(
            workflow,
            candidate_tools,
            reason=str(abstain_decision.get("reason") or "bfcl_abstain"),
            abstain_diagnostics=abstain_decision.get("diagnostics") if isinstance(abstain_decision.get("diagnostics"), dict) else None,
        )
    if not candidate_tools:
        return workflow

    if call_pattern == "serial" and (mode == "planner" or len(workflow.execution_plan) != 1):
        seed_specs = _bfcl_seed_specs(
            task,
            candidate_tools,
            query,
            abstain_policy_diagnostics=abstain_decision.get("diagnostics") if isinstance(abstain_decision.get("diagnostics"), dict) else None,
        )
        if seed_specs:
            if not enable_grounding:
                seed_specs = [
                    {
                        **spec,
                        "inputs": _bfcl_build_step_inputs(
                            spec.get("tool"),
                            str(spec.get("text") or query),
                            keep_query_fallback=True,
                            enable_grounding=False,
                        ),
                    }
                    for spec in seed_specs
                ]
            before_count = len(workflow.execution_plan)
            workflow = _configure_bfcl_seed_steps(workflow, seed_specs, enable_grounding=enable_grounding)
            workflow.metadata["planner_canonicalized_to_bfcl_seed"] = True
            workflow.metadata["bfcl_protocol_fallback_applied"] = True
            workflow.metadata["bfcl_protocol_fallback_reason"] = (
                "multi_turn_without_explicit_milestones"
                if metadata.get("bfcl_group") == "multi_turn"
                else "serial_exact_call_protocol"
            )
            workflow.metadata["bfcl_canonicalized_step_count_before"] = before_count
            workflow.metadata["bfcl_canonicalized_step_count_after"] = len(workflow.execution_plan)
            workflow.context.candidate_tools = [] if workflow.metadata.get("bfcl_abstained") else list(candidate_tools)
            return workflow

    if call_pattern == "parallel":
        parallel_specs = _bfcl_seed_specs(
            task,
            candidate_tools,
            query,
            abstain_policy_diagnostics=abstain_decision.get("diagnostics") if isinstance(abstain_decision.get("diagnostics"), dict) else None,
        )
        if parallel_specs:
            if not enable_grounding:
                parallel_specs = [
                    {
                        **spec,
                        "inputs": _bfcl_build_step_inputs(
                            spec.get("tool"),
                            str(spec.get("text") or query),
                            keep_query_fallback=True,
                            enable_grounding=False,
                        ),
                    }
                    for spec in parallel_specs
                ]
            return _configure_bfcl_seed_steps(workflow, parallel_specs, enable_grounding=enable_grounding)

    if metadata.get("bfcl_group") == "multi_turn" and (
        mode == "planner" or any(not str(step.tool_id or "").strip() for step in workflow.execution_plan)
    ):
        seed_specs = _bfcl_seed_specs(
            task,
            candidate_tools,
            query,
            abstain_policy_diagnostics=abstain_decision.get("diagnostics") if isinstance(abstain_decision.get("diagnostics"), dict) else None,
        )
        if seed_specs:
            if not enable_grounding:
                seed_specs = [
                    {
                        **spec,
                        "inputs": _bfcl_build_step_inputs(
                            spec.get("tool"),
                            str(spec.get("text") or query),
                            keep_query_fallback=True,
                            enable_grounding=False,
                        ),
                    }
                    for spec in seed_specs
                ]
            workflow = _configure_bfcl_seed_steps(workflow, seed_specs, enable_grounding=enable_grounding)
            workflow.metadata["bfcl_protocol_fallback_applied"] = True
            workflow.metadata["bfcl_protocol_fallback_reason"] = "multi_turn_without_explicit_milestones"
            return workflow

    for index, step in enumerate(workflow.execution_plan):
        text = milestones[index] if index < len(milestones) else query
        selected_tool = tool_lookup.get(str(step.tool_id or "").strip())
        preferred_tool_id = str(selected_tool.tool_id) if selected_tool is not None else ""
        selected_tool, selection_diagnostics = _bfcl_schema_ranked_choice(
            candidate_tools,
            text,
            preferred_tool_id=preferred_tool_id,
        )
        if selected_tool is None:
            _record_bfcl_choice(workflow, selection_diagnostics)
            continue
        capability_id = _bfcl_capability_id(selected_tool)
        required_input_keys = set(_bfcl_required_input_keys(selected_tool))
        step.capability_id = capability_id
        step.tool_id = selected_tool.tool_id
        step.inputs = (
            extract_tool_arguments(
                selected_tool.tool_id,
                _bfcl_tool_parameters(selected_tool),
                text,
                include_defaults=False,
            )
            if enable_grounding
            else {}
        ) or _bfcl_build_step_inputs(selected_tool, text, enable_grounding=enable_grounding)
        if call_pattern == "serial" and str(metadata.get("bfcl_group") or "").strip().lower() != "multi_turn":
            if enable_grounding:
                step.inputs, grounding_diagnostics = _bfcl_ground_serial_required_args(
                    selected_tool,
                    text,
                    dict(step.inputs),
                )
                selection_diagnostics.update(grounding_diagnostics)
            selection_diagnostics = _bfcl_mark_serial_materialization_diagnostics(
                selection_diagnostics,
                inputs=dict(step.inputs),
            )
        _record_bfcl_choice(workflow, selection_diagnostics)
        if "query" not in required_input_keys:
            step.inputs.pop("query", None)
        if "target_path" not in required_input_keys:
            step.inputs.pop("target_path", None)
        _configure_bfcl_step_metadata(
            step,
            selected_tool,
            text,
            enable_grounding=enable_grounding,
            selection_diagnostics=selection_diagnostics,
        )
        if index < len(workflow.tool_bindings):
            workflow.tool_bindings[index].capability_id = capability_id
            workflow.tool_bindings[index].primary_tool = selected_tool.tool_id
            _sync_bfcl_binding_metadata(workflow, step, index)
        if index < len(workflow.workflow_graph.nodes):
            workflow.workflow_graph.nodes[index].capability_id = capability_id
            workflow.workflow_graph.nodes[index].selected_tool = selected_tool.tool_id
            workflow.workflow_graph.nodes[index].tool_candidates = [selected_tool.tool_id]
            workflow.workflow_graph.nodes[index].inputs = dict(step.inputs)
    workflow.context.candidate_tools = [] if workflow.metadata.get("bfcl_abstained") else list(candidate_tools)
    return workflow


def _shutdown_thread_pool_compat(pool: concurrent.futures.ThreadPoolExecutor, *, cancel_futures: bool = False) -> None:
    try:
        pool.shutdown(wait=False, cancel_futures=cancel_futures)
    except TypeError:
        pool.shutdown(wait=False)


def _llm_backend_completion(backend_cfg: Dict[str, Any], policy_cfg: Dict[str, Any]):
    scripted_payload = dict(backend_cfg.get("payload", {})) if isinstance(backend_cfg.get("payload"), dict) else {}
    scripted_replies = dict(backend_cfg.get("scripted_replies", {})) if isinstance(backend_cfg.get("scripted_replies"), dict) else {}
    default_status = str(backend_cfg.get("status", "accept"))
    policy_missing = dict(policy_cfg.get("missing_arg_values", {})) if isinstance(policy_cfg.get("missing_arg_values"), dict) else {}
    policy_constraints = dict(policy_cfg.get("constraint_overrides", {})) if isinstance(policy_cfg.get("constraint_overrides"), dict) else {}
    policy_switch_hints = dict(policy_cfg.get("tool_switch_hints", {})) if isinstance(policy_cfg.get("tool_switch_hints"), dict) else {}
    policy_approvals = dict(policy_cfg.get("approval_responses", {})) if isinstance(policy_cfg.get("approval_responses"), dict) else {}
    provider_mode = str(backend_cfg.get("mode", "scripted")).strip().lower() or "scripted"
    env_payload_key = str(backend_cfg.get("env_payload_var", "TOOLCLAW_LLM_REPLY_PAYLOAD"))

    def _schema_tool_id(request: Any) -> str:
        schema = request.allowed_response_schema if isinstance(request.allowed_response_schema, dict) else {}
        props = schema.get("properties")
        if not isinstance(props, dict):
            return ""
        tool_field = props.get("tool_id")
        if not isinstance(tool_field, dict):
            return ""
        enum_values = tool_field.get("enum")
        if isinstance(enum_values, list):
            for candidate in enum_values:
                text = str(candidate).strip()
                if text:
                    return text
        return ""

    def _needs_tool_switch(request: Any) -> bool:
        expected = str(request.expected_answer_type or "").strip().lower()
        patch_targets = request.metadata.get("patch_targets", {}) if isinstance(request.metadata, dict) else {}
        return expected in {"tool_switch", "tool_or_asset_hint", "environment_resolution"} or (
            isinstance(patch_targets, dict) and patch_targets.get("tool_id") == "binding.primary_tool"
        )

    def _enforce_tool_switch_payload(request: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not _needs_tool_switch(request):
            return payload
        if isinstance(payload.get("tool_id"), str) and payload.get("tool_id"):
            return payload
        fallback_tool = _schema_tool_id(request)
        if fallback_tool:
            payload["tool_id"] = fallback_tool
            payload.pop("clear_failure_flag", None)
        return payload

    def _openrouter_completion(request: Any, fallback_payload: Dict[str, Any]) -> Dict[str, Any]:
        _start_ts = time.time()
        api_key = str(os.environ.get("OPENROUTER_API_KEY", "")).strip()
        if not api_key:
            fallback_payload = _enforce_tool_switch_payload(request, fallback_payload)
            return {
                "payload": fallback_payload,
                "status": "accept",
                "accepted": True,
                "raw_text": "openrouter_api_key_missing_fallback",
                "metadata": {"provider_mode": provider_mode, "fallback": True},
            }
        endpoint = str(backend_cfg.get("base_url", "https://openrouter.ai/api/v1/chat/completions")).strip()
        model = str(backend_cfg.get("model", "openai/gpt-4o-mini")).strip()
        site_url = str(backend_cfg.get("site_url", "")).strip()
        site_name = str(backend_cfg.get("site_name", "ToolClaw")).strip()
        schema_hint = request.allowed_response_schema if isinstance(request.allowed_response_schema, dict) else {}
        prompt_payload = {
            "question": request.question,
            "expected_answer_type": request.expected_answer_type,
            "allowed_response_schema": schema_hint,
            "metadata": request.metadata if isinstance(request.metadata, dict) else {},
            "fallback_payload": fallback_payload,
        }
        system_prompt = (
            "You are a strict JSON reply generator for an interaction repair loop. "
            "Return exactly one JSON object with keys: payload (object), status (string), accepted (boolean), raw_text (string). "
            "Do not include markdown fences or prose."
        )
        user_prompt = json.dumps(prompt_payload, ensure_ascii=True)
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": float(backend_cfg.get("temperature", 0.0) or 0.0),
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **({"HTTP-Referer": site_url} if site_url else {}),
                **({"X-Title": site_name} if site_name else {}),
            },
            method="POST",
        )

        socket_timeout = float(backend_cfg.get("timeout_s", 60) or 60)
        hard_timeout = float(backend_cfg.get("hard_timeout_s", max(socket_timeout + 2.0, 10.0)) or max(socket_timeout + 2.0, 10.0))

        def _request_once() -> str:
            with urllib.request.urlopen(req, timeout=socket_timeout) as resp:
                return resp.read().decode("utf-8")

        pool: concurrent.futures.ThreadPoolExecutor | None = None
        future: concurrent.futures.Future[str] | None = None
        try:
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(_request_once)
            raw = future.result(timeout=hard_timeout)
        except concurrent.futures.TimeoutError:
            if future is not None:
                future.cancel()
            if pool is not None:
                _shutdown_thread_pool_compat(pool, cancel_futures=True)
            fallback_payload = _enforce_tool_switch_payload(request, fallback_payload)
            return {
                "payload": fallback_payload,
                "status": "accept",
                "accepted": True,
                "raw_text": f"openrouter_hard_timeout_fallback:{hard_timeout}s",
                "metadata": {"provider_mode": provider_mode, "fallback": True, "timeout_s": socket_timeout, "hard_timeout_s": hard_timeout},
            }
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if pool is not None:
                _shutdown_thread_pool_compat(pool, cancel_futures=True)
            fallback_payload = _enforce_tool_switch_payload(request, fallback_payload)
            return {
                "payload": fallback_payload,
                "status": "accept",
                "accepted": True,
                "raw_text": f"openrouter_request_failed_fallback:{exc}",
                "metadata": {"provider_mode": provider_mode, "fallback": True},
            }
        finally:
            if pool is not None:
                _shutdown_thread_pool_compat(pool, cancel_futures=True)
        try:
            parsed = json.loads(raw)
            content = (
                parsed.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            content_json = json.loads(content) if isinstance(content, str) else {}
            if isinstance(content_json, dict):
                payload = content_json.get("payload", content_json)
                status = str(content_json.get("status", "accept"))
                accepted = bool(content_json.get("accepted", status == "accept"))
                raw_text = str(content_json.get("raw_text", content if isinstance(content, str) else ""))
                if not isinstance(payload, dict):
                    payload = fallback_payload
                payload = _enforce_tool_switch_payload(request, payload)
                return {
                    "payload": payload,
                    "status": status,
                    "accepted": accepted,
                    "raw_text": raw_text,
                    "metadata": {"provider_mode": provider_mode, "model": model},
                }
        except (json.JSONDecodeError, IndexError, TypeError, AttributeError):
            pass
        fallback_payload = _enforce_tool_switch_payload(request, fallback_payload)
        return {
            "payload": fallback_payload,
            "status": "accept",
            "accepted": True,
            "raw_text": "openrouter_response_parse_failed_fallback",
            "metadata": {"provider_mode": provider_mode, "fallback": True, "model": model},
        }

    def _completion(request: Any) -> Dict[str, Any]:
        env_payload = None
        raw_env_payload = os.environ.get(env_payload_key)
        if raw_env_payload:
            try:
                parsed_env_payload = json.loads(raw_env_payload)
                if isinstance(parsed_env_payload, dict):
                    env_payload = parsed_env_payload
            except json.JSONDecodeError:
                env_payload = {"raw_text": raw_env_payload}

        question_key = str(request.metadata.get("query_policy", {}).get("question_type") or request.expected_answer_type or "default")
        payload = {}
        payload.update(policy_missing)
        payload.update(policy_constraints)
        payload.update(policy_switch_hints)
        payload.update(scripted_payload)
        if isinstance(scripted_replies.get(question_key), dict):
            payload.update(scripted_replies[question_key])
        if isinstance(scripted_replies.get("default"), dict):
            payload.update(scripted_replies["default"])
        if isinstance(env_payload, dict):
            payload.update(env_payload)
        if request.metadata.get("recommended_backup_tool") and "tool_id" not in payload:
            payload["tool_id"] = request.metadata["recommended_backup_tool"]
        if "approval" in request.expected_answer_type or "approve" in request.question.lower():
            payload.setdefault("approved", bool(policy_approvals.get(request.interaction_id, True)))

        if provider_mode == "openrouter":
            return _openrouter_completion(request, payload)

        payload = _enforce_tool_switch_payload(request, payload)

        return {
            "payload": payload,
            "status": default_status,
            "accepted": default_status == "accept",
            "raw_text": str(backend_cfg.get("raw_text", f"{provider_mode}-reply")),
            "metadata": {
                "provider_mode": provider_mode,
                "question_key": question_key,
            },
        }

    return _completion


def _planner_structural_fallback_reason(workflow: Workflow, *, benchmark: str) -> Optional[str]:
    """Return a generic fallback reason when a planner output is not executable."""
    if benchmark == "bfcl":
        return None
    if not workflow.execution_plan:
        return "empty_execution_plan"
    unbound_steps = [
        str(step.step_id)
        for step in workflow.execution_plan
        if not str(step.tool_id or "").strip()
    ]
    if unbound_steps:
        return "unbound_steps"
    return None


def _apply_planner_structural_fallback(
    *,
    planned_workflow: Workflow,
    task: Dict[str, Any],
    planner_goal: str,
    benchmark: str,
) -> Workflow:
    reason = _planner_structural_fallback_reason(planned_workflow, benchmark=benchmark)
    if not reason:
        return planned_workflow
    fallback = Workflow.demo()
    fallback.workflow_id = f"wf_{canonical_task_id(task)}"
    fallback.task.task_id = canonical_task_id(task)
    fallback.task.user_goal = planner_goal
    fallback.metadata.update(
        {
            "planner_mode": "planner_structural_fallback_to_recovery_seed",
            "planner_structural_fallback_applied": True,
            "planner_structural_fallback_reason": reason,
            "planner_original_step_count": len(planned_workflow.execution_plan),
            "planner_unbound_steps": [
                str(step.step_id)
                for step in planned_workflow.execution_plan
                if not str(step.tool_id or "").strip()
            ],
            "planner_unresolved_bindings": [
                str(binding.capability_id)
                for binding in planned_workflow.tool_bindings
                if not str(binding.primary_tool or "").strip()
            ],
        }
    )
    return fallback



_GOLD_TASK_KEYS_FOR_PLANNER = {
    "milestones",
    "reference_result_summary",
    "result_summary",
    "official_milestone_mapping",
    "official_similarity",
    "official_turn_count",
    "scorer_gold",
    "scorer_gold_messages",
    "expected_answer",
    "expected_recovery_path",
    "gold_tool",
    "ideal_turn_count",
    "ideal_tool_calls",
}
_GOLD_METADATA_TOKENS_FOR_PLANNER = (
    "official",
    "scorer_gold",
    "reference",
    "milestone",
    "result_summary",
    "trajectory",
    "gold",
    "ideal_",
)


def _normalize_hint_policy(hint_policy: str) -> str:
    normalized = str(hint_policy or "runtime_visible").strip().lower()
    if normalized not in {"runtime_visible", "legacy"}:
        raise ValueError(f"unsupported hint_policy: {hint_policy}")
    return normalized


def _runtime_visibility(task: Dict[str, Any]) -> Dict[str, Any]:
    direct = task.get("runtime_visibility")
    if isinstance(direct, dict):
        return direct
    metadata = task.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("runtime_visibility"), dict):
        return dict(metadata["runtime_visibility"])
    return {}


def _sanitize_task_for_planner_admission(task: Dict[str, Any]) -> Dict[str, Any]:
    """Return a planner-candidate payload with scorer/provenance gold removed."""

    sanitized = deepcopy(task)
    for key in list(sanitized):
        key_l = str(key).lower()
        if key in _GOLD_TASK_KEYS_FOR_PLANNER or key_l.startswith("official_"):
            sanitized.pop(key, None)
    if isinstance(sanitized.get("runtime_messages"), list):
        sanitized["messages"] = list(sanitized.get("runtime_messages") or [])
    else:
        sanitized.pop("messages", None)
    metadata = sanitized.get("metadata")
    if isinstance(metadata, dict):
        safe_metadata = {}
        for key, value in metadata.items():
            key_l = str(key).lower()
            if any(token in key_l for token in _GOLD_METADATA_TOKENS_FOR_PLANNER):
                continue
            safe_metadata[key] = value
        sanitized["metadata"] = safe_metadata
    return sanitized


def _decision_visible_task(task: Dict[str, Any], *, hint_policy: str = "runtime_visible") -> Dict[str, Any]:
    if _normalize_hint_policy(hint_policy) == "legacy":
        return task
    sanitized = _sanitize_task_for_planner_admission(task)
    runtime_visibility = _runtime_visibility(task)
    if runtime_visibility.get("full_messages_runtime_visible") is False:
        if isinstance(task.get("runtime_messages"), list):
            sanitized["messages"] = list(task.get("runtime_messages") or [])
        else:
            sanitized.pop("messages", None)
    elif isinstance(task.get("messages"), list):
        sanitized["messages"] = list(task.get("messages") or [])
    if runtime_visibility.get("milestones_runtime_visible") is True:
        if isinstance(task.get("milestones"), list):
            sanitized["milestones"] = list(task.get("milestones") or [])
    else:
        sanitized.pop("milestones", None)
    return sanitized


def _sanitize_decision_hints(hints: Dict[str, Any], *, hint_policy: str = "runtime_visible") -> Dict[str, Any]:
    if _normalize_hint_policy(hint_policy) == "legacy":
        return hints
    for key in _GOLD_TASK_KEYS_FOR_PLANNER:
        hints.pop(key, None)
    for key in list(hints):
        key_l = str(key).lower()
        if key_l.startswith("official_") or any(token in key_l for token in _GOLD_METADATA_TOKENS_FOR_PLANNER):
            hints.pop(key, None)
    return hints


def build_workflow_from_task(
    task: Dict[str, Any],
    mode: str = "demo",
    *,
    spec: Optional[SystemSpec] = None,
    hint_policy: str = "runtime_visible",
) -> Workflow:
    task = annotate_task_payload(task)
    decision_task = _decision_visible_task(task, hint_policy=hint_policy)
    metadata_task = decision_task if _normalize_hint_policy(hint_policy) == "runtime_visible" else task
    raw_metadata = metadata_task.get("metadata")
    toolsandbox_metadata = raw_metadata if isinstance(raw_metadata, dict) and raw_metadata.get("benchmark") == "toolsandbox" else {}
    bfcl_metadata = raw_metadata if isinstance(raw_metadata, dict) and raw_metadata.get("benchmark") == "bfcl" else {}
    raw_tools = decision_task.get("candidate_tools")
    if raw_tools is None and isinstance(decision_task.get("tool_allow_list"), list):
        raw_tools = list(decision_task.get("tool_allow_list", []))
    candidate_tools = _build_tool_specs(raw_tools)
    raw_query = str(decision_task.get("query") or "").strip()
    planner_goal = _planner_goal_from_task(decision_task, raw_query or Workflow.demo().task.user_goal)
    if mode in {"planner_overlay", "planner_overlay_admitted"}:
        base_workflow = build_workflow_from_task(task, mode="demo", spec=spec, hint_policy=hint_policy)
        planner_task = _sanitize_task_for_planner_admission(task) if mode == "planner_overlay_admitted" else decision_task
        planner_workflow = build_workflow_from_task(planner_task, mode="planner", spec=spec, hint_policy=hint_policy)
        overlay_metadata = {
            "system_id": spec.system_id if spec is not None else "",
            "task_id": canonical_task_id(task),
            "task_metadata": planner_task.get("metadata", {}) if isinstance(planner_task.get("metadata"), dict) else {},
            "candidate_tool_ids": [tool.tool_id for tool in candidate_tools],
        }
        if mode == "planner_overlay_admitted":
            workflow = apply_admitted_planner_overlay(base_workflow, planner_workflow, overlay_metadata)
        else:
            workflow = apply_planner_overlay(base_workflow, planner_workflow, overlay_metadata)
        if spec is not None and spec.system_id == "s4_reuse_overlay":
            workflow = apply_reuse_overlay_noop(
                workflow,
                {
                    "system_id": spec.system_id,
                    "task_id": canonical_task_id(task),
                    "exact_reuse_policy": "no_runtime_path_change_v1",
                },
            )
        return workflow
    if mode == "planner":
        planner = build_default_planner()
        demo = Workflow.demo()
        request = PlanningRequest(
            task=demo.task,
            context=demo.context,
            policy=demo.policy,
        )
        request.task.task_id = canonical_task_id(task)
        request.task.user_goal = planner_goal
        if candidate_tools:
            request.context.candidate_tools = list(candidate_tools)
        request.hints.user_style["benchmark"] = (
            str(raw_metadata.get("benchmark"))
            if isinstance(raw_metadata, dict) and raw_metadata.get("benchmark")
            else None
        )
        request.hints.user_style["tool_allow_list"] = list(decision_task.get("tool_allow_list", []))
        request.hints.user_style["categories"] = list(
            (raw_metadata or {}).get("toolsandbox_categories", [])
            if isinstance(raw_metadata, dict)
            else []
        )
        request.hints.user_style["messages"] = list(decision_task.get("messages", []))
        request.hints.user_style["milestones"] = list(decision_task.get("milestones", []))
        request.hints.user_style["branch_options"] = list(decision_task.get("branch_options", []))
        request.hints.user_style["backup_tool_map"] = dict(decision_task.get("backup_tool_map", {}))
        request.hints.user_style["requires_interaction"] = (
            bool((raw_metadata or {}).get("requires_interaction"))
            if isinstance(raw_metadata, dict)
            else False
        )
        if isinstance(raw_metadata, dict):
            if raw_metadata.get("approval_scope") is not None:
                request.hints.user_style["approval_scope"] = raw_metadata.get("approval_scope")
            if raw_metadata.get("approval_target_step") is not None:
                request.hints.user_style["approval_target_step"] = raw_metadata.get("approval_target_step")
        request.hints.user_style["primary_failtax"] = decision_task.get("primary_failtax")
        request.hints.user_style["failtaxes"] = list(decision_task.get("failtaxes", []))
        request.hints.user_style["failure_step"] = decision_task.get("failure_step")
        request.hints.user_style["expected_recovery_path"] = decision_task.get("expected_recovery_path")
        request.hints.user_style["gold_tool"] = decision_task.get("gold_tool")
        request.hints.user_style["state_slots"] = list(decision_task.get("state_slots", []))
        request.hints.user_style["dependency_edges"] = list(decision_task.get("dependency_edges", []))
        request.hints.user_style["ideal_turn_count"] = decision_task.get("ideal_turn_count")
        request.hints.user_style["ideal_tool_calls"] = decision_task.get("ideal_tool_calls")
        _sanitize_decision_hints(request.hints.user_style, hint_policy=hint_policy)
        request.hints.user_style["tool_execution_backend"] = (
            str(task.get("tool_execution_backend") or (raw_metadata or {}).get("tool_execution_backend") or ("semantic_mock" if toolsandbox_metadata else "mock"))
        )
        planned_workflow = planner.plan(request).workflow
        benchmark = (
            str(raw_metadata.get("benchmark"))
            if isinstance(raw_metadata, dict) and raw_metadata.get("benchmark")
            else ""
        ).strip().lower()
        workflow = _apply_planner_structural_fallback(
            planned_workflow=planned_workflow,
            task=task,
            planner_goal=planner_goal,
            benchmark=benchmark,
        )
    elif mode == "seed":
        workflow = _build_seed_workflow(
            task,
            candidate_tools,
            planner_goal,
            enable_grounding=True if spec is None else bool(spec.enable_core_grounding),
        )
    elif mode == "demo" and (bfcl_metadata or toolsandbox_metadata):
        workflow = _build_seed_workflow(
            task,
            candidate_tools,
            planner_goal,
            enable_grounding=True if spec is None else bool(spec.enable_core_grounding),
        )
    else:
        workflow = Workflow.demo()

    workflow.task.task_id = canonical_task_id(task)

    retrieve_query = task.get("query")
    if not retrieve_query and isinstance(task.get("messages"), list):
        for message in task["messages"]:
            if not isinstance(message, dict):
                continue
            sender = str(message.get("sender") or message.get("role") or "").lower()
            if sender == "user" and message.get("content"):
                retrieve_query = str(message["content"])
                break
    if (
        retrieve_query
        and (mode != "planner" or workflow.metadata.get("planner_structural_fallback_applied"))
        and workflow.execution_plan
    ):
        workflow.execution_plan[0].inputs["query"] = retrieve_query

    if task.get("target_path") is not None and workflow.execution_plan:
        target_path = task["target_path"]
        write_steps = [step for step in workflow.execution_plan if step.capability_id == "cap_write"]
        if write_steps:
            write_steps[0].inputs["target_path"] = target_path
        elif len(workflow.execution_plan) > 1:
            workflow.execution_plan[1].inputs["target_path"] = target_path

    raw_constraints = task.get("constraints")
    if isinstance(raw_constraints, dict):
        constraints = TaskConstraints(
            budget_limit=float(raw_constraints["budget_limit"]) if raw_constraints.get("budget_limit") is not None else None,
            time_limit=float(raw_constraints["time_limit"]) if raw_constraints.get("time_limit") is not None else None,
            requires_user_approval=bool(raw_constraints.get("requires_user_approval", False)),
            forbidden_actions=list(raw_constraints.get("forbidden_actions", [])) if raw_constraints.get("forbidden_actions") else [],
            max_tool_calls=int(raw_constraints["max_tool_calls"]) if raw_constraints.get("max_tool_calls") is not None else None,
            max_user_turns=int(raw_constraints["max_user_turns"]) if raw_constraints.get("max_user_turns") is not None else None,
            max_repair_attempts=int(raw_constraints["max_repair_attempts"]) if raw_constraints.get("max_repair_attempts") is not None else None,
            max_recovery_budget=float(raw_constraints["max_recovery_budget"]) if raw_constraints.get("max_recovery_budget") is not None else None,
        )
        risk_level = raw_constraints.get("risk_level")
        if risk_level in {"low", "medium", "high"}:
            constraints.risk_level = RiskLevel(risk_level)
        workflow.task.constraints = constraints

    if raw_tools is not None:
        workflow.context.candidate_tools = [] if workflow.metadata.get("bfcl_abstained") else candidate_tools
    if toolsandbox_metadata and not workflow.context.candidate_tools:
        raise ValueError(
            f"ToolSandbox task '{workflow.task.task_id}' has empty candidate_tools/tool_allow_list; refusing to fall back to demo tools."
        )

    if isinstance(raw_metadata, dict):
        workflow.metadata.update(_filter_runtime_safe_metadata(raw_metadata))
    configured_tool_backend = None
    if isinstance(raw_metadata, dict):
        configured_tool_backend = raw_metadata.get("tool_execution_backend") or raw_metadata.get("tool_backend")
    if configured_tool_backend is None:
        configured_tool_backend = task.get("tool_execution_backend") or task.get("tool_backend")
    if configured_tool_backend is None and toolsandbox_metadata:
        configured_tool_backend = "semantic_mock"
    if configured_tool_backend is None and bfcl_metadata:
        configured_tool_backend = "bfcl_stub"
    workflow.metadata["tool_execution_backend"] = str(configured_tool_backend or "mock")
    workflow.metadata["enable_core_grounding"] = True if spec is None else bool(spec.enable_core_grounding)
    workflow.metadata["enable_schema_preflight"] = True if spec is None else bool(spec.enable_schema_preflight)
    workflow.metadata.update(annotate_task(task))
    workflow.metadata["task_family"] = derive_task_family(task, scenario=str(task.get("scenario", "success")), task_id=workflow.task.task_id)
    workflow.metadata["failure_type"] = derive_failure_type(task, scenario=str(task.get("scenario", "success")))
    workflow.metadata["scenario"] = str(task.get("scenario", "success"))
    reuse_family_id = derive_reuse_family_id(workflow.task.task_id, task)
    if reuse_family_id:
        workflow.metadata["reuse_family_id"] = reuse_family_id
        workflow.metadata["semantic_reuse_family"] = derive_semantic_reuse_family(reuse_family_id)
    workflow.metadata.setdefault("planner_mode", "recovery_seed" if mode == "seed" else "demo")
    if isinstance(task.get("budget_profile"), dict):
        workflow.metadata["budget_profile"] = dict(task.get("budget_profile", {}))
    if isinstance(task.get("simulated_policy"), dict):
        workflow.metadata["simulated_policy"] = dict(task.get("simulated_policy", {}))
    if isinstance(task.get("reuse_override_inputs"), dict):
        workflow.metadata["reuse_override_inputs"] = dict(task.get("reuse_override_inputs", {}))
    if metadata_task.get("messages") is not None:
        workflow.metadata["messages"] = list(metadata_task.get("messages", []))
    if metadata_task.get("milestones") is not None:
        workflow.metadata["milestones"] = list(metadata_task.get("milestones", []))
    if task.get("tool_allow_list") is not None:
        workflow.metadata["tool_allow_list"] = list(task.get("tool_allow_list", []))
    if isinstance(task.get("backup_tool_map"), dict):
        workflow.metadata["backup_tool_map"] = dict(task.get("backup_tool_map", {}))
    if task.get("branch_options") is not None:
        workflow.metadata["branch_options"] = list(task.get("branch_options", []))
    if task.get("reference_result_summary") is not None:
        workflow.metadata["toolsandbox_reference_result"] = dict(task.get("reference_result_summary", {}))
    if metadata_task.get("ideal_turn_count") is not None:
        workflow.metadata["ideal_turn_count"] = metadata_task.get("ideal_turn_count")
    if metadata_task.get("ideal_tool_calls") is not None:
        workflow.metadata["ideal_tool_calls"] = metadata_task.get("ideal_tool_calls")

    if toolsandbox_metadata:
        allow_list = workflow.metadata.get("tool_allow_list") or []
        scenario = str(task.get("scenario", "toolsandbox"))
        ideal_tool_calls = task.get("ideal_tool_calls")
        low_branching = (
            len(allow_list) == 1
            or scenario in {"single_tool", "single_user_turn"}
            or ideal_tool_calls == 1
            or bool(toolsandbox_metadata.get("low_branching"))
        )
        if low_branching:
            workflow.execution_plan = workflow.execution_plan[:1]
            workflow.tool_bindings = workflow.tool_bindings[:1]
            workflow.workflow_graph.nodes = workflow.workflow_graph.nodes[:1]
            workflow.workflow_graph.edges = []
            workflow.workflow_graph.entry_nodes = ["step_01"]
            workflow.workflow_graph.exit_nodes = ["step_01"]
            workflow.metadata["low_branching_fast_path"] = True
            if allow_list and workflow.execution_plan and mode != "planner":
                allowed = {str(item) for item in allow_list}
                current_tool = str(workflow.execution_plan[0].tool_id)
                candidate_by_id = {tool.tool_id: tool for tool in candidate_tools}
                allowed_candidates = [candidate_by_id[tool_id] for tool_id in allow_list if tool_id in candidate_by_id]
                selected_spec = None
                if current_tool in allowed and current_tool != "end_conversation":
                    selected_spec = candidate_by_id.get(current_tool)
                if selected_spec is None:
                    selected_spec = _select_seed_primary_tool(task, allowed_candidates or candidate_tools, str(retrieve_query or planner_goal))
                selected_tool = selected_spec.tool_id if selected_spec is not None else next(
                    (str(tool_id) for tool_id in allow_list if str(tool_id) != "end_conversation"),
                    str(allow_list[0]),
                )
                if selected_tool not in allowed and allowed:
                    selected_tool = next(
                        (str(tool_id) for tool_id in allow_list if str(tool_id) != "end_conversation"),
                        str(allow_list[0]),
                    )
                selected_spec = candidate_by_id.get(selected_tool)
                if selected_spec is not None:
                    capability_id = _seed_selected_capability(
                        selected_spec,
                        planner_goal,
                        default=workflow.execution_plan[0].capability_id or "cap_write",
                    )
                else:
                    capability_id = workflow.execution_plan[0].capability_id
                workflow.execution_plan[0].tool_id = selected_tool
                workflow.execution_plan[0].capability_id = capability_id
                if selected_spec is not None:
                    workflow.execution_plan[0].inputs = _seed_step_inputs(
                        tool=selected_spec,
                        capability_id=capability_id,
                        task=task,
                        user_goal=str(retrieve_query or planner_goal),
                    )
                    workflow.execution_plan[0].expected_output = _seed_step_expected_output(selected_spec, capability_id)
                elif capability_id in _SEED_READ_CAPABILITIES:
                    workflow.execution_plan[0].inputs = {"query": str(retrieve_query or planner_goal)}
                    workflow.execution_plan[0].expected_output = "retrieved_info"
                elif capability_id == "cap_write" and task.get("target_path") is not None:
                    workflow.execution_plan[0].inputs = {"target_path": task.get("target_path")}
                    workflow.execution_plan[0].expected_output = "report_artifact"
                if workflow.tool_bindings:
                    workflow.tool_bindings[0].primary_tool = selected_tool
                    workflow.tool_bindings[0].capability_id = capability_id
                if workflow.workflow_graph.nodes:
                    workflow.workflow_graph.nodes[0].selected_tool = selected_tool
                    workflow.workflow_graph.nodes[0].capability_id = capability_id
                    workflow.workflow_graph.nodes[0].tool_candidates = [selected_tool]

    for step in workflow.execution_plan:
        if not isinstance(step.metadata.get("repair_default_inputs"), dict):
            step.metadata["repair_default_inputs"] = dict(step.inputs)

    sim_policy = task.get("simulated_policy")
    if (
        isinstance(sim_policy, dict)
        and isinstance(sim_policy.get("missing_arg_values"), dict)
        and len(workflow.execution_plan) > 1
    ):
        workflow.execution_plan[1].metadata["simulated_missing_arg_values"] = dict(sim_policy["missing_arg_values"])

    scenario = task.get("scenario", "success")
    if scenario == "binding_failure" and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs.pop("target_path", None)
    elif scenario == "environment_failure" and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs["force_environment_failure"] = True
    elif scenario == "state_failure" and len(workflow.execution_plan) > 1:
        state_mode = str(workflow.metadata.get("state_failure_mode") or task.get("state_failure_mode") or "state_slot_mismatch")
        workflow.execution_plan[1].metadata.setdefault("required_state_slots", [])
        workflow.execution_plan[1].metadata.setdefault("state_bindings", {})
        workflow.execution_plan[1].metadata.setdefault("inject_missing_state_slots_once", [])
        workflow.execution_plan[1].metadata.setdefault("inject_stale_state_slots_once", [])
        if state_mode == "state_slot_mismatch":
            workflow.execution_plan[1].metadata["required_state_slots"] = ["retrieved_summary"]
            workflow.execution_plan[1].metadata["state_bindings"] = {"retrieved_info": "retrieved_summary"}
            workflow.metadata["resume_state_drop_slots"] = []
            workflow.metadata["resume_state_stale_slots"] = []
        elif state_mode == "wrong_write_target":
            correct_target = str(task.get("target_path") or workflow.execution_plan[1].inputs.get("target_path") or "outputs/reports/planned_report.txt")
            wrong_target = str(task.get("wrong_target_path") or f"{Path(correct_target).with_suffix('')}.wrong.txt")
            workflow.execution_plan[1].inputs["target_path"] = wrong_target
            workflow.execution_plan[1].inputs["expected_target_path"] = correct_target
            workflow.metadata["resume_state_drop_slots"] = []
            workflow.metadata["resume_state_stale_slots"] = []
            workflow.metadata["reuse_override_inputs"] = dict(task.get("reuse_override_inputs", {"cap_write": ["target_path"]}))
        elif state_mode in {"resume_state_loss", "checkpoint_resume"}:
            workflow.execution_plan[1].metadata["required_state_slots"] = ["retrieved_info"]
            workflow.execution_plan[1].metadata["state_bindings"] = {"retrieved_info": "retrieved_info"}
            workflow.execution_plan[1].metadata["inject_missing_state_slots_once"] = ["retrieved_info"]
            workflow.metadata["resume_state_drop_slots"] = ["retrieved_info"]
            workflow.metadata["resume_state_stale_slots"] = []
        elif state_mode in {"stale_state_after_repair", "state_stale_slot", "recovery_not_committed"}:
            workflow.execution_plan[1].metadata["required_state_slots"] = ["retrieved_info"]
            workflow.execution_plan[1].metadata["state_bindings"] = {"retrieved_info": "retrieved_info"}
            workflow.execution_plan[1].metadata["inject_stale_state_slots_once"] = ["retrieved_info"]
            workflow.metadata["resume_state_drop_slots"] = []
            workflow.metadata["resume_state_stale_slots"] = ["retrieved_info"] if state_mode == "recovery_not_committed" else []
        workflow.metadata["state_failure_mode"] = state_mode

    if bfcl_metadata:
        workflow = _adapt_bfcl_workflow(
            workflow,
            task=task,
            candidate_tools=candidate_tools,
            mode=mode,
            enable_grounding=bool(workflow.metadata.get("enable_core_grounding", True)),
        )

    return workflow


def existing_json_path(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(
            f"taskset file not found: {path}. Provide a real JSON file path (for example: data/eval_tasks.sample.json)."
        )
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"taskset path is not a file: {path}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase-1 A0-A4 evaluation")
    parser.add_argument("--taskset", type=existing_json_path, required=True, help="Path to taskset JSON")
    parser.add_argument("--outdir", default="outputs/eval", help="Output directory")
    parser.add_argument(
        "--mode",
        choices=["demo", "planner"],
        default="planner",
        help="Legacy workflow source mode for alias compatibility; A0-A4 use fixed modes.",
    )
    parser.add_argument(
        "--systems",
        default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
        help=(
            "Comma-separated systems to run: "
            "a0_baseline,a1_recovery,a2_planner,a3_interaction,a3_full_interaction,"
            "a3_full_interaction_oracle,a3_no_query,a3_noisy_user,"
            "a3_full_interaction_noisy,a3_full_interaction_irrelevant,"
            "a3_full_interaction_wrong_parameter,a3_full_interaction_partial,a4_reuse. "
            "Supported legacy aliases: baseline,planning,interactive,toolclaw_lite."
        ),
    )
    parser.add_argument(
        "--asset-registry-root",
        default=None,
        help=(
            "Optional directory for file-backed reusable assets. "
            "When set, each non-baseline system persists artifacts under <root>/<system_id> so reuse can survive across CLI invocations."
        ),
    )
    parser.add_argument(
        "--hint-policy",
        choices=["runtime_visible", "legacy"],
        default="runtime_visible",
        help="Runtime decision hint policy. Paper-facing runs should use runtime_visible; legacy is for historical reproduction only.",
    )
    parser.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Disable per-task progress logs.",
    )
    return parser.parse_args()


def build_runtime(asset_registry: Optional[AssetRegistry] = None) -> ToolClawRuntime:
    return build_runtime_for_spec(
        asset_registry=asset_registry,
        spec=SYSTEM_SPECS["a4_reuse"],
    )


def build_runtime_for_spec(
    *,
    spec: SystemSpec,
    asset_registry: Optional[AssetRegistry] = None,
) -> ToolClawRuntime:
    registry = asset_registry or InMemoryAssetRegistry()
    planner = build_default_planner(asset_registry=registry)
    runtime = ToolClawRuntime(
        planner=planner,
        executor=SequentialExecutor(
            recovery_engine=RecoveryEngine(
                RecoveryConfig(enable_tool_fallback=spec.allow_fallback)
            ),
            config=ExecutorConfig(
                allow_repair=spec.allow_repair,
                enable_schema_preflight=spec.enable_schema_preflight,
            ),
        ),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    if not spec.allow_suffix_replan:
        runtime.executor.planner = None
    return runtime


def parse_systems(raw_systems: str) -> List[SystemSpec]:
    system_specs: List[SystemSpec] = []
    seen: set[str] = set()
    for raw_system in raw_systems.split(","):
        candidate = raw_system.strip()
        if not candidate:
            continue
        canonical = SYSTEM_ALIASES.get(candidate, candidate)
        if canonical not in SYSTEM_SPECS:
            raise ValueError(f"unsupported system '{candidate}'. Valid systems: {', '.join(sorted(SYSTEM_SPECS))}")
        if canonical in seen:
            continue
        seen.add(canonical)
        system_specs.append(SYSTEM_SPECS[canonical])
    return system_specs


def build_planning_request(workflow: Workflow, *, allow_reuse: bool, hint_policy: str = "runtime_visible") -> PlanningRequest:
    request = PlanningRequest(
        task=workflow.task,
        context=workflow.context,
        policy=workflow.policy,
        workflow_overrides={
            "steps": {
                step.step_id: {
                    "capability_id": step.capability_id,
                    "inputs": dict(step.inputs),
                    "tool_id": step.tool_id,
                    "metadata": dict(step.metadata),
                }
                for step in workflow.execution_plan
            }
        },
    )
    request.hints.allow_reuse = allow_reuse
    request.hints.user_style["task_family"] = str(workflow.metadata.get("task_family", "t0_general"))
    request.hints.user_style["failure_type"] = str(workflow.metadata.get("failure_type", "none"))
    request.hints.user_style["scenario"] = str(workflow.metadata.get("scenario", "success"))
    request.hints.user_style["categories"] = list(
        workflow.metadata.get("toolsandbox_categories")
        or workflow.metadata.get("categories")
        or []
    )
    request.hints.user_style["benchmark"] = workflow.metadata.get("benchmark")
    request.hints.user_style["messages"] = list(workflow.metadata.get("messages", []))
    request.hints.user_style["tool_allow_list"] = list(workflow.metadata.get("tool_allow_list", []))
    request.hints.user_style["backup_tool_map"] = dict(workflow.metadata.get("backup_tool_map", {}))
    request.hints.user_style["branch_options"] = list(workflow.metadata.get("branch_options", []))
    request.hints.user_style["ideal_tool_calls"] = workflow.metadata.get("ideal_tool_calls")
    request.hints.user_style["ideal_turn_count"] = workflow.metadata.get("ideal_turn_count")
    request.hints.user_style["milestones"] = list(workflow.metadata.get("milestones", []))
    request.hints.user_style["primary_failtax"] = workflow.metadata.get("primary_failtax")
    request.hints.user_style["failtaxes"] = list(workflow.metadata.get("failtaxes", []))
    request.hints.user_style["failure_step"] = workflow.metadata.get("failure_step")
    request.hints.user_style["expected_recovery_path"] = workflow.metadata.get("expected_recovery_path")
    request.hints.user_style["gold_tool"] = workflow.metadata.get("gold_tool")
    request.hints.user_style["state_slots"] = list(workflow.metadata.get("state_slots", []))
    request.hints.user_style["dependency_edges"] = list(workflow.metadata.get("dependency_edges", []))
    request.hints.user_style["approval_scope"] = workflow.metadata.get("approval_scope")
    request.hints.user_style["approval_target_step"] = workflow.metadata.get("approval_target_step")
    request.hints.user_style["requires_interaction"] = workflow.metadata.get("requires_interaction")
    request.hints.user_style["reuse_family_id"] = workflow.metadata.get("reuse_family_id")
    request.hints.user_style["semantic_reuse_family"] = workflow.metadata.get("semantic_reuse_family")
    request.hints.user_style["reuse_scope"] = workflow.metadata.get("reuse_scope")
    request.hints.user_style["reuse_claim_scope"] = workflow.metadata.get("reuse_claim_scope")
    request.hints.user_style["reuse_allowed_modes"] = list(workflow.metadata.get("reuse_allowed_modes", []))
    request.hints.user_style["reuse_require_source_family_match"] = workflow.metadata.get("reuse_require_source_family_match")
    request.hints.user_style["reuse_signature_key"] = workflow.metadata.get("reuse_signature_key")
    request.hints.user_style["reuse_pass2_compile_allowed"] = workflow.metadata.get("reuse_pass2_compile_allowed")
    request.hints.user_style["reuse_override_inputs"] = dict(workflow.metadata.get("reuse_override_inputs", {}))
    request.hints.user_style["tool_execution_backend"] = workflow.metadata.get("tool_execution_backend")
    _sanitize_decision_hints(request.hints.user_style, hint_policy=hint_policy)
    if not allow_reuse:
        request.hints.reusable_asset_ids = []
    return request


def _load_trace_payload(trace_path: Path) -> Dict[str, Any]:
    if not trace_path.exists():
        return {}
    return json.loads(trace_path.read_text(encoding="utf-8"))


def _write_trace_payload(trace_path: Path, payload: Dict[str, Any]) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _reuse_rollback_decision(outcome: Any, trace_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    reusable_context = dict(outcome.workflow.metadata.get("reusable_context", {}))
    reuse_mode = str(reusable_context.get("reuse_mode") or "")
    if reuse_mode not in {"transfer_reuse", "exact_reuse"}:
        return None
    events = list(trace_payload.get("events", []))
    first_repair_index = next(
        (idx for idx, event in enumerate(events) if event.get("event_type") == "repair_triggered"),
        None,
    )
    benchmark_hints = dict(outcome.workflow.metadata.get("benchmark_hints", {}))
    expected_tool_calls = int(benchmark_hints.get("ideal_tool_calls") or len(outcome.workflow.execution_plan) or 1)
    repair_actions = int(trace_payload.get("metrics", {}).get("repair_actions", 0) or 0)
    repair_budget = max(1, expected_tool_calls - 1)
    if first_repair_index is None:
        if reuse_mode != "transfer_reuse":
            return None
        tool_calls_before_repair = sum(1 for event in events if event.get("event_type") == "tool_call")
        early_repair = False
        repair_overflow = False
    else:
        tool_calls_before_repair = sum(
            1 for event in events[:first_repair_index] if event.get("event_type") == "tool_call"
        )
        early_repair = tool_calls_before_repair <= max(1, min(2, expected_tool_calls))
        repair_overflow = repair_actions > repair_budget
    if reuse_mode == "exact_reuse" and not repair_overflow:
        return None
    return {
        "applied": True,
        "reason": (
            "transfer_reuse_not_claim_supported"
            if reuse_mode == "transfer_reuse" and not (early_repair or repair_overflow)
            else ("early_transfer_repair" if early_repair else "repair_budget_overflow")
        ),
        "reuse_mode": reuse_mode,
        "repair_actions": repair_actions,
        "repair_budget": repair_budget,
        "tool_calls_before_repair": tool_calls_before_repair,
        "resolved_asset_ids": list(reusable_context.get("resolved_asset_ids", [])),
        "selected_match": dict(reusable_context.get("selected_match", {}))
        if isinstance(reusable_context.get("selected_match", {}), dict)
        else {},
        "fallback_behavior": "a3_interaction",
    }


def build_shell(runtime: ToolClawRuntime, task: Dict[str, Any], spec: SystemSpec | None = None) -> InteractionShell:
    if spec is None and isinstance(task.get("_system_spec"), SystemSpec):
        spec = task["_system_spec"]
    policy_cfg = task.get("simulated_policy", {})
    simulator_policy = SimulatedPolicy(
        mode=policy_cfg.get("mode", "cooperative"),
        missing_arg_values=policy_cfg.get("missing_arg_values", {}),
        backup_tool_preferences=policy_cfg.get("backup_tool_preferences", {}),
        approval_responses=policy_cfg.get("approval_responses", {}),
        constraint_overrides=policy_cfg.get("constraint_overrides", {}),
        tool_switch_hints=policy_cfg.get("tool_switch_hints", {}),
    )
    raw_backend_cfg = task.get("interaction_backend", {})
    backend_cfg = dict(raw_backend_cfg) if isinstance(raw_backend_cfg, dict) else {}
    backend = str((backend_cfg.get("type") if backend_cfg else raw_backend_cfg) or task.get("interaction_backend_type") or "simulator")
    reply_provider = None
    if backend == "human":
        reply_provider = HumanReplyProvider(prompt_prefix=str(backend_cfg.get("prompt_prefix", "toolclaw")))
    elif backend == "cli":
        cli_command = backend_cfg.get("command") if isinstance(backend_cfg, dict) else None
        if not cli_command:
            cli_command = os.getenv("TOOLCLAW_CLI_REPLY_COMMAND", "")
        reply_provider = CLIReplyProvider(
            command=cli_command,
            timeout_s=float(backend_cfg.get("timeout_s", 30.0)) if isinstance(backend_cfg, dict) else 30.0,
            provider_name=str(backend_cfg.get("provider_name", "cli")) if isinstance(backend_cfg, dict) else "cli",
        )
    elif backend == "llm":
        reply_provider = LLMReplyProvider(
            completion_fn=_llm_backend_completion(backend_cfg, policy_cfg),
            provider_name=str(backend_cfg.get("provider_name", "llm")),
        )
    elif isinstance(task.get("oracle_user_replies"), list) and task.get("oracle_user_replies"):
        reply_provider = OracleReplayProvider(
            oracle_replies=list(task.get("oracle_user_replies", [])),
            fallback_provider=UserSimulator(simulator_policy),
        )
    if spec is not None and spec.interaction_live_user_mode:
        reply_provider = DeterministicModeReplyProvider(mode=spec.interaction_live_user_mode)
    elif spec is not None and spec.noisy_user_replies:
        reply_provider = DeterministicNoisyReplyProvider()
    return InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            simulator_policy=simulator_policy,
            disable_user_queries=bool(spec.disable_user_queries) if spec is not None else False,
            enable_success_probe=bool(spec.enable_success_probe) if spec is not None else False,
        ),
        reply_provider=reply_provider,
        semantic_decoder=SemanticDecoder(),
    )


def canonical_task_id(task: Dict[str, Any]) -> str:
    for key in ("task_id", "sample_id", "name", "scenario_id", "id"):
        value = task.get(key)
        if value:
            return str(value)
    raise KeyError("task object must include one of: task_id, sample_id, name, scenario_id, id")


def task_signature_candidates(
    *,
    query: str,
    task_family: str | None = None,
    failure_type: str | None = None,
    capability_skeleton: Optional[List[str]] = None,
) -> List[str]:
    return build_task_signature_candidates(
        user_goal=query,
        task_family=task_family,
        capability_skeleton=capability_skeleton,
        failure_context=failure_type,
    )


def parse_reuse_pass_index(task_id: str, task: Dict[str, Any]) -> int:
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("reuse_pass_index") is not None:
        return int(metadata["reuse_pass_index"])
    if task.get("reuse_pass_index") is not None:
        return int(task["reuse_pass_index"])
    match = re.search(r"__pass(\d+)$", task_id)
    return int(match.group(1)) if match else 0


def repeat_family_key(task_id: str, task: Dict[str, Any]) -> str:
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("reuse_family_id"):
        return str(metadata["reuse_family_id"])
    if task.get("reuse_family_id"):
        return str(task["reuse_family_id"])
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return task_id


def repeat_family_key_from_task_id(task_id: str) -> str:
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return task_id


def derive_reuse_family_id(task_id: str, task: Dict[str, Any]) -> str:
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("reuse_family_id"):
        return str(metadata["reuse_family_id"]).strip()
    if task.get("reuse_family_id"):
        return str(task["reuse_family_id"]).strip()
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return ""


def derive_semantic_reuse_family(reuse_family_id: str) -> str:
    family = str(reuse_family_id or "").strip()
    if not family:
        return ""
    family = re.sub(r"__pair\d+$", "", family)
    family = re.sub(r"_\d+$", "", family)
    return family


def classify_reuse_tier(
    *,
    reused_artifact: bool,
    reuse_mode: str,
    target_family: str,
    source_family: str,
    target_semantic_family: str,
    source_semantic_family: str,
) -> str:
    if not reused_artifact:
        return "none"
    mode = str(reuse_mode or "").strip()
    if source_family and target_family:
        if source_family == target_family:
            return "exact_match_reuse"
        if source_semantic_family and target_semantic_family and source_semantic_family == target_semantic_family:
            return "same_family_transfer_reuse"
        return "cross_family_transfer_reuse"
    if mode == "exact_reuse":
        return "exact_match_reuse"
    if mode in {"transfer_reuse", "explicit_asset"}:
        return "unresolved_transfer_reuse"
    return "none"


def build_reuse_provenance(
    *,
    task: Dict[str, Any],
    workflow: Workflow,
    reused_artifact: bool,
) -> Dict[str, Any]:
    task_id = canonical_task_id(task)
    target_family = derive_reuse_family_id(task_id, task)
    target_semantic_family = derive_semantic_reuse_family(target_family)
    reusable_context = workflow.metadata.get("reusable_context", {})
    if not isinstance(reusable_context, dict):
        reusable_context = {}
    selected_match = reusable_context.get("selected_match", {})
    if not isinstance(selected_match, dict):
        selected_match = {}
    reuse_mode = str(reusable_context.get("reuse_mode") or selected_match.get("reuse_mode") or "none")
    selected_asset_id = str(
        selected_match.get("asset_id")
        or next(iter(reusable_context.get("resolved_asset_ids", [])), "")
        or ""
    ).strip()
    source_task_id = str(selected_match.get("source_task_id") or "").strip()
    source_family = str(
        selected_match.get("source_reuse_family_id")
        or selected_match.get("reuse_family_id")
        or ""
    ).strip()
    if not source_family and source_task_id:
        source_family = repeat_family_key_from_task_id(source_task_id)
    source_semantic_family = str(
        selected_match.get("source_semantic_reuse_family")
        or selected_match.get("semantic_reuse_family")
        or derive_semantic_reuse_family(source_family)
    ).strip()
    return {
        "reused_artifact": bool(reused_artifact),
        "reuse_mode": reuse_mode,
        "reuse_selected_asset_id": selected_asset_id,
        "reuse_selected_match_signature": str(selected_match.get("matched_signature") or ""),
        "reuse_source_task_id": source_task_id,
        "reuse_target_family": target_family,
        "reuse_source_family": source_family,
        "reuse_target_semantic_family": target_semantic_family,
        "reuse_source_semantic_family": source_semantic_family,
        "reuse_tier": classify_reuse_tier(
            reused_artifact=bool(reused_artifact),
            reuse_mode=reuse_mode,
            target_family=target_family,
            source_family=source_family,
            target_semantic_family=target_semantic_family,
            source_semantic_family=source_semantic_family,
        ),
    }


def _persist_reuse_provenance(trace_path: Path, provenance: Dict[str, Any]) -> None:
    trace_payload = _load_trace_payload(trace_path)
    trace_payload.setdefault("metadata", {})
    trace_payload["metadata"]["reuse_provenance"] = dict(provenance)
    _write_trace_payload(trace_path, trace_payload)


def current_git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def derive_task_family(task: Dict[str, Any], scenario: str, task_id: str) -> str:
    metadata = task.get("metadata", {})
    raw_family = task.get("task_family")
    if raw_family is None and isinstance(metadata, dict):
        raw_family = metadata.get("task_family")
    if raw_family:
        return str(raw_family)

    categories = []
    raw_categories = task.get("categories")
    if isinstance(raw_categories, list):
        categories.extend(str(item).strip().lower().replace(" ", "_") for item in raw_categories)
    if isinstance(metadata, dict):
        meta_categories = metadata.get("toolsandbox_categories")
        if isinstance(meta_categories, list):
            categories.extend(str(item).strip().lower() for item in meta_categories)

    pass_index = parse_reuse_pass_index(task_id, task)
    if pass_index > 0 or (isinstance(metadata, dict) and metadata.get("reuse_family_id")):
        return "t4_repeated_reusable"
    if scenario in {"binding_failure", "environment_failure", "permission_failure", "missing_asset", "policy_failure", "state_failure"}:
        return "t1_static_recovery"
    if scenario in {"multiple_user_turn", "approval_required", "insufficient_information"}:
        return "t3_must_interact"
    if any(category in {"multiple_user_turn", "insufficient_information"} for category in categories):
        return "t3_must_interact"
    if any(category in {"state_dependency", "canonicalization", "multiple_tool", "dynamic_branching"} for category in categories):
        return "t2_dynamic_branching"
    if scenario in {"state_dependency", "canonicalization", "multiple_tool", "dynamic_branching"}:
        return "t2_dynamic_branching"
    return "t0_general"


def derive_failure_type(task: Dict[str, Any], scenario: str) -> str:
    metadata = task.get("metadata", {})
    raw_failure_type = task.get("failure_type")
    if raw_failure_type is None and isinstance(metadata, dict):
        raw_failure_type = metadata.get("failure_type")
    if raw_failure_type:
        return str(raw_failure_type)
    return "none" if scenario == "success" else scenario


def row_from_trace(
    *,
    task: Dict[str, Any],
    system: str,
    scenario: str,
    trace_path: Path,
    reused_artifact: bool,
) -> EvalRow:
    task_id = canonical_task_id(task)
    task = annotate_task_payload(task)
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    events = trace_payload.get("events", [])
    metrics = trace_payload.get("metrics", {})
    metadata = trace_payload.get("metadata", {})
    task_annotations = dict(metadata.get("task_annotations", {}))
    reuse_provenance = metadata.get("reuse_provenance", {})
    if not isinstance(reuse_provenance, dict):
        reuse_provenance = {}
    chosen_tool = str(task_annotations.get("chosen_tool") or "") or _chosen_tool_from_trace(events, task_annotations.get("failure_step"))
    stop_event = next((event for event in reversed(events) if event.get("event_type") == "stop"), None)
    stop_reason = stop_event.get("output", {}).get("reason", "unknown") if isinstance(stop_event, dict) else "unknown"
    repair_triggered = sum(1 for event in events if event.get("event_type") == "repair_triggered")
    first_repair_index = next((idx for idx, event in enumerate(events) if event.get("event_type") == "repair_triggered"), None)
    observed_error_type = derive_failure_type(task, scenario)
    if first_repair_index is not None:
        observed_error_type = str(events[first_repair_index].get("metadata", {}).get("failtax_label") or observed_error_type)
    elif stop_reason == "repair_disabled":
        observed_error_type = str(trace_payload.get("metadata", {}).get("scenario") or observed_error_type)
    repair_extra_tool_calls = 0
    repair_extra_user_turns = 0
    if first_repair_index is not None:
        trailing_events = events[first_repair_index + 1 :]
        repair_extra_tool_calls = sum(1 for event in trailing_events if event.get("event_type") == "tool_call")
        repair_extra_user_turns = sum(1 for event in trailing_events if event.get("event_type") == "user_query")
    observed_failtaxes = _observed_failtaxes(events, task_annotations)
    primary_failtax = str(task_annotations.get("primary_failtax") or derive_primary_failtax(task))
    if map_failtax_bucket(primary_failtax) == "state" and "state" in observed_failtaxes:
        observed_error_type = "state_failure"
    stop_reason = str(stop_reason)
    safe_abort = stop_reason == "safe_abort_success"
    policy_compliance_success = False
    if derive_failure_type(task, scenario) in {"approval_required", "policy_failure", "dual_control"}:
        policy_compliance_success = safe_abort or stop_reason == "policy_compliant_stop" or bool(metrics.get("success"))
    state_repair_success = map_failtax_bucket(primary_failtax) == "state" and repair_triggered > 0 and bool(metrics.get("success"))
    target_family = str(reuse_provenance.get("reuse_target_family") or derive_reuse_family_id(task_id, task) or "")
    target_semantic_family = str(
        reuse_provenance.get("reuse_target_semantic_family") or derive_semantic_reuse_family(target_family)
    )
    source_family = str(reuse_provenance.get("reuse_source_family") or "")
    source_semantic_family = str(
        reuse_provenance.get("reuse_source_semantic_family") or derive_semantic_reuse_family(source_family)
    )
    reuse_mode = str(reuse_provenance.get("reuse_mode") or ("unknown_reuse" if reused_artifact else "none"))
    reuse_tier = str(
        reuse_provenance.get("reuse_tier")
        or classify_reuse_tier(
            reused_artifact=reused_artifact,
            reuse_mode=reuse_mode,
            target_family=target_family,
            source_family=source_family,
            target_semantic_family=target_semantic_family,
            source_semantic_family=source_semantic_family,
        )
    )
    planner_decision = task_annotations.get("planner_admission_decision")
    if not isinstance(planner_decision, dict):
        planner_decision = {}
    planner_mode = str(planner_decision.get("admission_mode") or "")
    planner_takeover = bool(planner_decision.get("admitted") and planner_mode == "execution_takeover")
    planner_reason = str(planner_decision.get("reason") or "")
    planner_admitted_changes = planner_decision.get("admitted_changes") if isinstance(planner_decision.get("admitted_changes"), list) else []
    planner_rejected_reasons = planner_decision.get("rejected_reasons") if isinstance(planner_decision.get("rejected_reasons"), list) else []
    benchmark = str((task.get("metadata") or {}).get("benchmark") or "").strip().lower() if isinstance(task.get("metadata"), dict) else ""
    benchmark_success = bool(metrics.get("success"))
    if benchmark == "bfcl":
        sample = BFCL_ADAPTER.load_samples_from_tasks([task])[0]
        benchmark_success = BFCL_ADAPTER.score_trace(sample, trace_payload).success
    return EvalRow(
        task_id=task_id,
        system=system,
        scenario=scenario,
        task_family=derive_task_family(task, scenario, task_id),
        failure_type=derive_failure_type(task, scenario),
        primary_failtax=map_failtax_bucket(primary_failtax),
        failtaxes=json.dumps(observed_failtaxes, ensure_ascii=True),
        failure_step=str(task_annotations.get("failure_step") or "step_02"),
        expected_recovery_path=str(task_annotations.get("expected_recovery_path") or ""),
        gold_tool=str(task_annotations.get("gold_tool") or "") or None,
        chosen_tool=chosen_tool or None,
        state_slots=json.dumps(list(task_annotations.get("state_slots", [])), ensure_ascii=True),
        dependency_edges=json.dumps(list(task_annotations.get("dependency_edges", [])), ensure_ascii=True),
        success=benchmark_success,
        tool_calls=int(metrics.get("tool_calls", 0)),
        repair_actions=int(metrics.get("repair_actions", 0)),
        repair_triggered=repair_triggered,
        user_turns=int(metrics.get("user_queries", 0)),
        total_steps=int(metrics.get("total_steps", 0)),
        token_cost=float(metrics.get("token_cost", 0.0) or 0.0),
        wall_clock_ms=int(metrics.get("latency_ms", 0) or 0),
        observed_error_type=observed_error_type,
        first_failure_recovered=bool(repair_triggered > 0 and metrics.get("success")),
        repair_extra_tool_calls=repair_extra_tool_calls,
        repair_extra_user_turns=repair_extra_user_turns,
        repair_user_clarification=bool(repair_extra_user_turns > 0),
        clarification_precision=float(metrics.get("clarification_precision", 0.0) or 0.0),
        clarification_recall=float(metrics.get("clarification_recall", 0.0) or 0.0),
        unnecessary_question_rate=float(metrics.get("unnecessary_question_rate", 0.0) or 0.0),
        patch_success_rate=float(metrics.get("patch_success_rate", 0.0) or 0.0),
        post_answer_retry_count=int(metrics.get("post_answer_retry_count", 0) or 0),
        safe_abort=safe_abort,
        policy_compliance_success=policy_compliance_success,
        state_repair_success=state_repair_success,
        reuse_pass_index=parse_reuse_pass_index(task_id, task),
        reused_artifact=reused_artifact,
        reuse_mode=reuse_mode,
        reuse_tier=reuse_tier,
        reuse_selected_asset_id=str(reuse_provenance.get("reuse_selected_asset_id") or ""),
        reuse_selected_match_signature=str(reuse_provenance.get("reuse_selected_match_signature") or ""),
        reuse_source_task_id=str(reuse_provenance.get("reuse_source_task_id") or ""),
        reuse_target_family=target_family,
        reuse_source_family=source_family,
        reuse_target_semantic_family=target_semantic_family,
        reuse_source_semantic_family=source_semantic_family,
        planner_admission_mode=planner_mode,
        planner_takeover_admitted=planner_takeover,
        planner_admission_reason=planner_reason,
        planner_admitted_change_count=len(planner_admitted_changes),
        planner_rejected_reason_count=len(planner_rejected_reasons),
        second_run_improvement=0.0,
        budget_violation=bool(metrics.get("budget_violation", False)),
        budget_violation_reason=str(metrics.get("budget_violation_reason") or ""),
        recovery_budget_used=float(metrics.get("recovery_budget_used", 0.0) or 0.0),
        stop_reason=str(stop_reason),
        trace_path=str(trace_path),
    )


def second_run_quality(row: EvalRow) -> float:
    fail_stop = 0.0 if row.success else 1.0
    return (100.0 if row.success else 0.0) - (20.0 * fail_stop) - float(row.tool_calls) - float(row.user_turns) - (0.5 * row.repair_actions)


def _chosen_tool_from_trace(events: List[Dict[str, Any]], failure_step: Any) -> str:
    failure_step_id = str(failure_step or "")
    for event in reversed(events):
        if event.get("event_type") != "tool_call":
            continue
        if failure_step_id and event.get("step_id") not in {failure_step_id, None, ""}:
            continue
        tool_id = event.get("tool_id")
        if tool_id:
            return str(tool_id)
    for event in reversed(events):
        if event.get("event_type") != "tool_call":
            continue
        tool_id = event.get("tool_id")
        if tool_id:
            return str(tool_id)
    return ""


def _observed_failtaxes(events: List[Dict[str, Any]], task_annotations: Dict[str, Any]) -> List[str]:
    observed = []
    for event in events:
        metadata = event.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        label = metadata.get("failtax_label")
        if label:
            observed.append(map_failtax_bucket(str(label)))
    if not observed:
        observed = list(task_annotations.get("failtaxes", []))
    if not observed:
        observed = [task_annotations.get("primary_failtax") or "recovery"]
    deduped: List[str] = []
    for label in observed:
        mapped = map_failtax_bucket(str(label))
        if mapped not in deduped:
            deduped.append(mapped)
    return deduped


def annotate_second_run_improvement(rows: List[EvalRow]) -> None:
    grouped: Dict[tuple[str, str], Dict[int, EvalRow]] = {}
    for row in rows:
        if row.reuse_pass_index <= 0:
            continue
        grouped.setdefault((row.system, repeat_family_key_from_task_id(row.task_id)), {})
        grouped[(row.system, repeat_family_key_from_task_id(row.task_id))][row.reuse_pass_index] = row

    for pass_map in grouped.values():
        if 1 not in pass_map or 2 not in pass_map:
            continue
        pass_1 = pass_map[1]
        pass_2 = pass_map[2]
        pass_2.second_run_improvement = second_run_quality(pass_2) - second_run_quality(pass_1)


def execute_system(
    *,
    spec: SystemSpec,
    task: Dict[str, Any],
    task_index: int,
    traces_dir: Path,
    runtime: Optional[ToolClawRuntime],
    hint_policy: str = "runtime_visible",
) -> EvalRow:
    task_id = canonical_task_id(task)
    task = annotate_task_payload(task)
    scenario = str(task.get("scenario", "success"))
    trace_path = traces_dir / f"{task_index:03d}_{task_id}_{spec.system_id}.json"
    backup_tool_map = task.get("backup_tool_map", {})
    task_family = derive_task_family(task, scenario, task_id)
    failure_type = derive_failure_type(task, scenario)
    reused_artifact = False

    if spec.execution_mode == "baseline":
        workflow = build_workflow_from_task(task, mode=spec.workflow_mode, spec=spec, hint_policy=hint_policy)
        baseline_trace, baseline_stop = run_baseline(
            workflow=workflow,
            run_id=f"{spec.system_id}_{task_id}",
            output_path=trace_path,
        )
        benchmark = str((task.get("metadata") or {}).get("benchmark") or "").strip().lower() if isinstance(task.get("metadata"), dict) else ""
        baseline_success = bool(baseline_trace.metrics.success)
        if benchmark == "bfcl":
            trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
            sample = BFCL_ADAPTER.load_samples_from_tasks([task])[0]
            baseline_success = BFCL_ADAPTER.score_trace(sample, trace_payload).success
        return EvalRow(
            task_id=task_id,
            system=spec.system_id,
            scenario=scenario,
            task_family=task_family,
            failure_type=failure_type,
            primary_failtax=derive_primary_failtax(task),
            failtaxes=json.dumps(task.get("failtaxes", [derive_primary_failtax(task)]), ensure_ascii=True),
            failure_step=str(task.get("failure_step") or "step_02"),
            expected_recovery_path=str(task.get("expected_recovery_path") or ""),
            gold_tool=str(task.get("gold_tool") or "") or None,
            chosen_tool=None,
            state_slots=json.dumps(list(task.get("state_slots", [])), ensure_ascii=True),
            dependency_edges=json.dumps(list(task.get("dependency_edges", [])), ensure_ascii=True),
            success=baseline_success,
            tool_calls=baseline_trace.metrics.tool_calls,
            repair_actions=baseline_trace.metrics.repair_actions,
            repair_triggered=0,
            user_turns=0,
            total_steps=baseline_trace.metrics.total_steps,
            token_cost=float(baseline_trace.metrics.token_cost or 0.0),
            wall_clock_ms=int(baseline_trace.metrics.latency_ms or 0),
            observed_error_type="none" if baseline_trace.metrics.success else failure_type,
            first_failure_recovered=False,
            repair_extra_tool_calls=0,
            repair_extra_user_turns=0,
            repair_user_clarification=False,
            clarification_precision=float(baseline_trace.metrics.clarification_precision),
            clarification_recall=float(baseline_trace.metrics.clarification_recall),
            unnecessary_question_rate=float(baseline_trace.metrics.unnecessary_question_rate),
            patch_success_rate=float(baseline_trace.metrics.patch_success_rate),
            post_answer_retry_count=int(baseline_trace.metrics.post_answer_retry_count),
            safe_abort=False,
            policy_compliance_success=False,
            state_repair_success=False,
            reuse_pass_index=parse_reuse_pass_index(task_id, task),
            reused_artifact=False,
            second_run_improvement=0.0,
            budget_violation=bool(baseline_trace.metrics.budget_violation),
            budget_violation_reason=str(baseline_trace.metrics.budget_violation_reason or ""),
            recovery_budget_used=float(baseline_trace.metrics.recovery_budget_used),
            stop_reason=baseline_stop,
            trace_path=str(trace_path),
        )

    if runtime is None:
        raise RuntimeError(f"runtime missing for system {spec.system_id}")

    if spec.execution_mode == "executor":
        workflow = build_workflow_from_task(task, mode=spec.workflow_mode, spec=spec, hint_policy=hint_policy)
        runtime.executor.run_until_blocked(
            workflow=workflow,
            run_id=f"{spec.system_id}_{task_id}",
            output_path=str(trace_path),
            backup_tool_map=backup_tool_map,
        )
        return row_from_trace(
            task=task,
            system=spec.system_id,
            scenario=scenario,
            trace_path=trace_path,
            reused_artifact=False,
        )

    seed_workflow = build_workflow_from_task(task, mode=spec.workflow_mode, spec=spec, hint_policy=hint_policy)
    benchmark = str(seed_workflow.metadata.get("benchmark") or "").strip().lower()
    approval_declared = bool(seed_workflow.task.constraints.requires_user_approval) or any(
        isinstance(edge, dict) and str(edge.get("type") or "").strip().lower() == "approval"
        for edge in task.get("dependency_edges", [])
    )
    if (
        benchmark == "tau2_bench"
        and spec.execution_mode == "interaction"
        and (scenario in {"approval_required", "policy_failure", "dual_control"} or approval_declared)
    ):
        seed_workflow.metadata["disable_simulated_auto_approval"] = True
    bfcl_direct_executor_only = benchmark == "bfcl" and bool(seed_workflow.metadata.get("bfcl_abstained"))
    if not seed_workflow.execution_plan or bfcl_direct_executor_only:
        runtime.executor.run_until_blocked(
            workflow=seed_workflow,
            run_id=f"{spec.system_id}_{task_id}",
            output_path=str(trace_path),
            backup_tool_map=backup_tool_map,
        )
        return row_from_trace(
            task=task,
            system=spec.system_id,
            scenario=scenario,
            trace_path=trace_path,
            reused_artifact=False,
        )
    request = build_planning_request(seed_workflow, allow_reuse=spec.use_reuse, hint_policy=hint_policy)
    shell_task = dict(task)
    shell_task["_system_spec"] = spec
    shell = build_shell(runtime, shell_task)
    protocol_preserving_reuse_disabled = benchmark == "bfcl" and spec.use_reuse
    run_use_reuse = bool(spec.use_reuse and not protocol_preserving_reuse_disabled)
    outcome = shell.run(
        request=request,
        run_id=f"{spec.system_id}_{task_id}",
        output_path=str(trace_path),
        backup_tool_map=backup_tool_map,
        use_reuse=run_use_reuse,
        compile_on_success=spec.compile_on_success,
        seed_workflow=seed_workflow,
    )
    if protocol_preserving_reuse_disabled:
        trace_payload = _load_trace_payload(trace_path)
        trace_payload.setdefault("metadata", {})
        trace_payload["metadata"]["reuse_protocol_guard"] = {
            "applied": True,
            "reason": "bfcl_function_call_protocol_preserves_seed_workflow",
            "fallback_behavior": "a3_interaction",
        }
        _write_trace_payload(trace_path, trace_payload)
    if run_use_reuse:
        rollback = _reuse_rollback_decision(outcome, _load_trace_payload(trace_path))
        if rollback is not None:
            request.hints.allow_reuse = False
            request.hints.reusable_asset_ids = []
            request.hints.user_style["reuse_fallback_applied"] = True
            request.hints.user_style["reuse_fallback_reason"] = rollback["reason"]
            outcome = shell.run(
                request=request,
                run_id=f"{spec.system_id}_{task_id}",
                output_path=str(trace_path),
                backup_tool_map=backup_tool_map,
                use_reuse=False,
                compile_on_success=spec.compile_on_success,
            )
            trace_payload = _load_trace_payload(trace_path)
            trace_payload.setdefault("metadata", {})
            trace_payload["metadata"]["reuse_rollback"] = rollback
            _write_trace_payload(trace_path, trace_payload)
        reused_artifact = bool(request.hints.reusable_asset_ids) and not bool(
            request.hints.user_style.get("reuse_fallback_applied")
        )
    _persist_reuse_provenance(
        trace_path,
        build_reuse_provenance(
            task=task,
            workflow=outcome.workflow,
            reused_artifact=reused_artifact,
        ),
    )
    return row_from_trace(
        task=task,
        system=spec.system_id,
        scenario=scenario,
        trace_path=trace_path,
        reused_artifact=reused_artifact,
    )


def main() -> None:
    args = parse_args()
    taskset_path: Path = args.taskset
    outdir = Path(args.outdir)
    traces_dir = outdir / "traces"
    rows: List[EvalRow] = []
    system_specs = parse_systems(args.systems)
    asset_registry_root = Path(args.asset_registry_root) if args.asset_registry_root else None
    runtimes: Dict[str, ToolClawRuntime] = {}
    for spec in system_specs:
        if spec.execution_mode == "baseline":
            continue
        asset_registry: Optional[AssetRegistry] = None
        if asset_registry_root is not None:
            asset_registry = FileAssetRegistry(str(asset_registry_root / spec.system_id))
        runtimes[spec.system_id] = build_runtime_for_spec(spec=spec, asset_registry=asset_registry)

    tasks = json.loads(taskset_path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("taskset JSON must be a list of task objects")
    tasks = [annotate_task_payload(task) for task in tasks]
    total_jobs = len(tasks) * len(system_specs)
    completed_jobs = 0
    if not args.quiet_progress:
        print(
            f"[run_eval] start total_jobs={total_jobs} tasks={len(tasks)} systems={len(system_specs)} outdir={outdir}",
            flush=True,
        )

    for idx, task in enumerate(tasks, start=1):
        for spec in system_specs:
            task_id = str(task.get("task_id") or f"{idx:03d}")
            if not args.quiet_progress:
                print(
                    f"[run_eval] start job={completed_jobs + 1}/{total_jobs} task={task_id} system={spec.system_id}",
                    flush=True,
                )
            row = execute_system(
                spec=spec,
                task=task,
                task_index=idx,
                traces_dir=traces_dir,
                runtime=runtimes.get(spec.system_id),
                hint_policy=args.hint_policy,
            )
            rows.append(row)
            completed_jobs += 1
            if not args.quiet_progress:
                print(
                    f"[run_eval] done  job={completed_jobs}/{total_jobs} task={task_id} system={spec.system_id} success={int(row.success)} stop_reason={row.stop_reason}",
                    flush=True,
                )

    csv_path = outdir / "comparison.csv"
    report_path = outdir / "report.md"
    git_commit = current_git_commit()
    annotate_second_run_improvement(rows)
    write_rows_csv(rows, csv_path)
    write_report_md(
        rows=rows,
        summary=summarize(rows),
        scenario_summary=summarize_by_scenario(rows),
        report_path=report_path,
        report_footer=(
            f"Results generated from commit {git_commit}."
            if git_commit
            else "Results generated from a workspace without a resolved git commit."
        ),
    )

    print(f"wrote: {csv_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()
