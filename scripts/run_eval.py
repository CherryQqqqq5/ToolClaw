"""Entry point for ToolClaw evaluation over normalized tasksets."""

from __future__ import annotations

import argparse
import os
import subprocess
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow `python3 scripts/run_eval.py ...` from repo root without manual PYTHONPATH.
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.baseline_runner import run_baseline
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
from toolclaw.interaction.reply_provider import HumanReplyProvider, LLMReplyProvider
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.user_simulator import SimulatedPolicy
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.capability_intents import CAPABILITY_PROFILES_BY_ID, infer_capability_from_text
from toolclaw.planner.htgp import PlanningRequest, build_default_planner
from toolclaw.registry import AssetRegistry, FileAssetRegistry, InMemoryAssetRegistry
from toolclaw.schemas.workflow import RiskLevel, TaskConstraints, ToolSpec, Workflow


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


SYSTEM_SPECS: Dict[str, SystemSpec] = {
    "a0_baseline": SystemSpec(system_id="a0_baseline", workflow_mode="demo", execution_mode="baseline"),
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
    ),
    "a4_reuse": SystemSpec(
        system_id="a4_reuse",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=True,
        use_reuse=True,
        allow_repair=True,
        allow_fallback=True,
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
}

SYSTEM_ALIASES: Dict[str, str] = {
    "baseline": "a0_baseline",
    "planning": "a2_planner",
    "interactive": "a3_interaction",
    "toolclaw_lite": "a3_interaction",
}


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
    inferred = infer_capability_from_text(f"{tool.tool_id} {tool.description}")
    return str(inferred or default)


def _select_seed_tool(
    candidate_tools: List[ToolSpec],
    capability_id: str,
    *,
    prefer_primary_write: bool = False,
) -> Optional[ToolSpec]:
    matches = [tool for tool in candidate_tools if _seed_capability_for_tool(tool, default="") == capability_id]
    if not matches:
        return None
    if prefer_primary_write and capability_id == "cap_write":
        non_backup = [tool for tool in matches if "backup" not in tool.tool_id.lower()]
        if non_backup:
            return non_backup[0]
    return matches[0]


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


def _build_seed_workflow(task: Dict[str, Any], candidate_tools: List[ToolSpec], user_goal: str) -> Workflow:
    workflow = Workflow.demo()
    workflow.workflow_id = f"wf_{canonical_task_id(task)}"
    workflow.task.task_id = canonical_task_id(task)
    workflow.task.user_goal = user_goal
    if candidate_tools:
        workflow.context.candidate_tools = list(candidate_tools)

    allow_list = list(task.get("tool_allow_list", [])) if isinstance(task.get("tool_allow_list"), list) else []
    scenario = str(task.get("scenario", "success"))
    low_branching = (
        len(candidate_tools) <= 1
        or len(allow_list) == 1
        or scenario in {"single_tool", "single_user_turn"}
        or task.get("ideal_tool_calls") == 1
    )

    retrieve_tool = _select_seed_tool(candidate_tools, "cap_retrieve")
    write_tool = _select_seed_tool(candidate_tools, "cap_write", prefer_primary_write=True)

    if low_branching:
        selected_tool = write_tool or retrieve_tool or (candidate_tools[0] if candidate_tools else None)
        if selected_tool is None:
            return workflow
        capability_id = _seed_capability_for_tool(
            selected_tool,
            default="cap_write" if task.get("target_path") is not None else "cap_retrieve",
        )
        step_inputs = {"target_path": task.get("target_path")} if capability_id == "cap_write" else {"query": str(task.get("query") or user_goal)}
        expected_output = "report_artifact" if capability_id == "cap_write" else "retrieved_info"
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
            inputs={"target_path": task.get("target_path")},
            expected_output="report_artifact",
        )
    if not write_tool and retrieve_tool:
        return _configure_seed_single_step_workflow(
            workflow,
            capability_id="cap_retrieve",
            tool_id=retrieve_tool.tool_id,
            inputs={"query": str(task.get("query") or user_goal)},
            expected_output="retrieved_info",
        )

    if retrieve_tool is not None:
        workflow.tool_bindings[0].primary_tool = retrieve_tool.tool_id
        workflow.execution_plan[0].tool_id = retrieve_tool.tool_id
        workflow.workflow_graph.nodes[0].selected_tool = retrieve_tool.tool_id
        workflow.workflow_graph.nodes[0].tool_candidates = [retrieve_tool.tool_id]
    if write_tool is not None:
        workflow.tool_bindings[1].primary_tool = write_tool.tool_id
        workflow.execution_plan[1].tool_id = write_tool.tool_id
        workflow.workflow_graph.nodes[1].selected_tool = write_tool.tool_id
        workflow.workflow_graph.nodes[1].tool_candidates = [write_tool.tool_id]
    workflow.metadata["planner_mode"] = "recovery_seed"
    return workflow


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


def build_workflow_from_task(task: Dict[str, Any], mode: str = "demo") -> Workflow:
    task = annotate_task_payload(task)
    raw_metadata = task.get("metadata")
    toolsandbox_metadata = raw_metadata if isinstance(raw_metadata, dict) and raw_metadata.get("benchmark") == "toolsandbox" else {}
    raw_tools = task.get("candidate_tools")
    if raw_tools is None and isinstance(task.get("tool_allow_list"), list):
        raw_tools = list(task.get("tool_allow_list", []))
    candidate_tools = _build_tool_specs(raw_tools)
    raw_query = str(task.get("query") or "").strip()
    planner_goal = _planner_goal_from_task(task, raw_query or Workflow.demo().task.user_goal)
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
        request.hints.user_style["tool_allow_list"] = list(task.get("tool_allow_list", []))
        request.hints.user_style["categories"] = list(
            (raw_metadata or {}).get("toolsandbox_categories", [])
            if isinstance(raw_metadata, dict)
            else []
        )
        request.hints.user_style["messages"] = list(task.get("messages", []))
        request.hints.user_style["milestones"] = list(task.get("milestones", []))
        request.hints.user_style["branch_options"] = list(task.get("branch_options", []))
        request.hints.user_style["primary_failtax"] = task.get("primary_failtax")
        request.hints.user_style["failtaxes"] = list(task.get("failtaxes", []))
        request.hints.user_style["failure_step"] = task.get("failure_step")
        request.hints.user_style["expected_recovery_path"] = task.get("expected_recovery_path")
        request.hints.user_style["gold_tool"] = task.get("gold_tool")
        request.hints.user_style["state_slots"] = list(task.get("state_slots", []))
        request.hints.user_style["dependency_edges"] = list(task.get("dependency_edges", []))
        request.hints.user_style["ideal_turn_count"] = task.get("ideal_turn_count")
        request.hints.user_style["ideal_tool_calls"] = task.get("ideal_tool_calls")
        request.hints.user_style["tool_execution_backend"] = (
            str(task.get("tool_execution_backend") or (raw_metadata or {}).get("tool_execution_backend") or ("semantic_mock" if toolsandbox_metadata else "mock"))
        )
        workflow = planner.plan(request).workflow
    elif mode == "seed":
        workflow = _build_seed_workflow(task, candidate_tools, planner_goal)
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
    if retrieve_query and mode != "planner":
        workflow.execution_plan[0].inputs["query"] = retrieve_query

    if task.get("target_path") is not None:
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
        workflow.context.candidate_tools = candidate_tools
    if toolsandbox_metadata and not workflow.context.candidate_tools:
        raise ValueError(
            f"ToolSandbox task '{workflow.task.task_id}' has empty candidate_tools/tool_allow_list; refusing to fall back to demo tools."
        )

    if isinstance(raw_metadata, dict):
        workflow.metadata.update(raw_metadata)
    configured_tool_backend = None
    if isinstance(raw_metadata, dict):
        configured_tool_backend = raw_metadata.get("tool_execution_backend") or raw_metadata.get("tool_backend")
    if configured_tool_backend is None:
        configured_tool_backend = task.get("tool_execution_backend") or task.get("tool_backend")
    if configured_tool_backend is None and toolsandbox_metadata:
        configured_tool_backend = "semantic_mock"
    workflow.metadata["tool_execution_backend"] = str(configured_tool_backend or "mock")
    workflow.metadata.update(annotate_task(task))
    workflow.metadata["task_family"] = derive_task_family(task, scenario=str(task.get("scenario", "success")), task_id=workflow.task.task_id)
    workflow.metadata["failure_type"] = derive_failure_type(task, scenario=str(task.get("scenario", "success")))
    workflow.metadata["scenario"] = str(task.get("scenario", "success"))
    workflow.metadata.setdefault("planner_mode", "recovery_seed" if mode == "seed" else "demo")
    if isinstance(task.get("budget_profile"), dict):
        workflow.metadata["budget_profile"] = dict(task.get("budget_profile", {}))
    if isinstance(task.get("simulated_policy"), dict):
        workflow.metadata["simulated_policy"] = dict(task.get("simulated_policy", {}))
    if isinstance(task.get("reuse_override_inputs"), dict):
        workflow.metadata["reuse_override_inputs"] = dict(task.get("reuse_override_inputs", {}))
    if task.get("messages") is not None:
        workflow.metadata["messages"] = list(task.get("messages", []))
    if task.get("milestones") is not None:
        workflow.metadata["milestones"] = list(task.get("milestones", []))
    if task.get("tool_allow_list") is not None:
        workflow.metadata["tool_allow_list"] = list(task.get("tool_allow_list", []))
    if task.get("branch_options") is not None:
        workflow.metadata["branch_options"] = list(task.get("branch_options", []))
    if task.get("reference_result_summary") is not None:
        workflow.metadata["toolsandbox_reference_result"] = dict(task.get("reference_result_summary", {}))
    if task.get("ideal_turn_count") is not None:
        workflow.metadata["ideal_turn_count"] = task.get("ideal_turn_count")
    if task.get("ideal_tool_calls") is not None:
        workflow.metadata["ideal_tool_calls"] = task.get("ideal_tool_calls")

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
                selected_tool = str(allow_list[0])
                workflow.execution_plan[0].tool_id = selected_tool
                if workflow.tool_bindings:
                    workflow.tool_bindings[0].primary_tool = selected_tool
                if workflow.workflow_graph.nodes:
                    workflow.workflow_graph.nodes[0].selected_tool = selected_tool
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
            "a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse. "
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
            config=ExecutorConfig(allow_repair=spec.allow_repair),
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


def build_planning_request(workflow: Workflow, *, allow_reuse: bool) -> PlanningRequest:
    request = PlanningRequest(
        task=workflow.task,
        context=workflow.context,
        policy=workflow.policy,
        workflow_overrides={
            "steps": {
                step.step_id: {
                    "inputs": dict(step.inputs),
                    "tool_id": step.tool_id,
                    "metadata": dict(step.metadata),
                }
                for step in workflow.execution_plan
            }
        },
    )
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
    request.hints.user_style["reuse_override_inputs"] = dict(workflow.metadata.get("reuse_override_inputs", {}))
    request.hints.user_style["tool_execution_backend"] = workflow.metadata.get("tool_execution_backend")
    if not allow_reuse:
        request.hints.reusable_asset_ids = []
    return request


def build_shell(runtime: ToolClawRuntime, task: Dict[str, Any]) -> InteractionShell:
    policy_cfg = task.get("simulated_policy", {})
    raw_backend_cfg = task.get("interaction_backend", {})
    backend_cfg = dict(raw_backend_cfg) if isinstance(raw_backend_cfg, dict) else {}
    backend = str((backend_cfg.get("type") if backend_cfg else raw_backend_cfg) or task.get("interaction_backend_type") or "simulator")
    reply_provider = None
    if backend == "human":
        reply_provider = HumanReplyProvider(prompt_prefix=str(backend_cfg.get("prompt_prefix", "toolclaw")))
    elif backend == "llm":
        reply_provider = LLMReplyProvider(
            completion_fn=_llm_backend_completion(backend_cfg, policy_cfg),
            provider_name=str(backend_cfg.get("provider_name", "llm")),
        )
    return InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            simulator_policy=SimulatedPolicy(
                mode=policy_cfg.get("mode", "cooperative"),
                missing_arg_values=policy_cfg.get("missing_arg_values", {}),
                backup_tool_preferences=policy_cfg.get("backup_tool_preferences", {}),
                approval_responses=policy_cfg.get("approval_responses", {}),
                constraint_overrides=policy_cfg.get("constraint_overrides", {}),
                tool_switch_hints=policy_cfg.get("tool_switch_hints", {}),
            )
        ),
        reply_provider=reply_provider,
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
        success=bool(metrics.get("success")),
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
) -> EvalRow:
    task_id = canonical_task_id(task)
    task = annotate_task_payload(task)
    scenario = str(task.get("scenario", "success"))
    trace_path = traces_dir / f"{task_index:03d}_{task_id}_{spec.system_id}.json"
    backup_tool_map = task.get("backup_tool_map", {})
    task_family = derive_task_family(task, scenario, task_id)
    failure_type = derive_failure_type(task, scenario)
    reused_artifact = False
    if spec.use_reuse and runtime is not None:
        query = str(task.get("query") or "")
        if query:
            signature_candidates = task_signature_candidates(
                query=query,
                task_family=task_family,
                failure_type=failure_type,
            )
            reused_artifact = any(runtime.asset_registry.query(signature) for signature in signature_candidates)

    if spec.execution_mode == "baseline":
        workflow = build_workflow_from_task(task, mode=spec.workflow_mode)
        baseline_trace, baseline_stop = run_baseline(
            workflow=workflow,
            run_id=f"{spec.system_id}_{task_id}",
            output_path=trace_path,
        )
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
            success=bool(baseline_trace.metrics.success),
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
        workflow = build_workflow_from_task(task, mode=spec.workflow_mode)
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

    seed_workflow = build_workflow_from_task(task, mode="planner")
    if spec.use_reuse and runtime is not None and not reused_artifact:
        signature_candidates = task_signature_candidates(
            query=seed_workflow.task.user_goal,
            task_family=str(seed_workflow.metadata.get("task_family", task_family)),
            failure_type=str(seed_workflow.metadata.get("failure_type", failure_type)),
            capability_skeleton=[step.capability_id for step in seed_workflow.execution_plan],
        )
        reused_artifact = any(runtime.asset_registry.query(signature) for signature in signature_candidates)
    request = build_planning_request(seed_workflow, allow_reuse=spec.use_reuse)
    build_shell(runtime, task).run(
        request=request,
        run_id=f"{spec.system_id}_{task_id}",
        output_path=str(trace_path),
        backup_tool_map=backup_tool_map,
        use_reuse=spec.use_reuse,
        compile_on_success=spec.compile_on_success,
    )
    if spec.use_reuse:
        reused_artifact = reused_artifact or bool(request.hints.reusable_asset_ids)
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
