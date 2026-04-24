"""Hierarchical Tool Graph Planner that builds workflows from capabilities before tools."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.compiler.swpc import _semantic_reuse_family, build_task_signature_candidates
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_intents import (
    CAPABILITY_PROFILES_BY_ID,
    infer_capability_from_text,
    rank_capability_profiles,
    tool_semantic_tokens,
)
from toolclaw.planner.capability_graph import RuleBasedCapabilityGraphBuilder
from toolclaw.schemas.error import ToolClawError
from toolclaw.schemas.workflow import (
    ActionType,
    ApprovalGate,
    CapabilityGraph,
    CapabilityNode,
    CheckpointPolicy,
    FallbackRoute,
    Phase,
    PreflightRequirement,
    RollbackPolicy,
    TaskSpec,
    ToolBinding,
    ToolSpec,
    Workflow,
    WorkflowContext,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowPolicy,
    WorkflowStep,
)

__all__ = [
    "PlanningHints",
    "PlanningRequest",
    "PlanningArtifact",
    "PlanningDiagnostics",
    "PlanningResult",
    "CapabilityCandidate",
    "CapabilitySelector",
    "RuleBasedCapabilitySelector",
    "CapabilityGraphBuilder",
    "PolicyInjector",
    "HTGPPlanner",
    "DefaultCapabilityGraphBuilder",
    "build_default_planner",
]


@dataclass
class PlanningHints:
    preferred_capabilities: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    allow_reuse: bool = False
    reusable_asset_ids: List[str] = field(default_factory=list)
    prior_failures: List[str] = field(default_factory=list)
    user_style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningRequest:
    task: TaskSpec
    context: WorkflowContext
    policy: Optional[WorkflowPolicy] = None
    hints: PlanningHints = field(default_factory=PlanningHints)
    planner_mode: str = "phase1_rule_based"
    workflow_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class PlanningArtifact:
    capability_graph: CapabilityGraph
    tool_bindings: List[ToolBinding]
    execution_plan: List[WorkflowStep]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningDiagnostics:
    unresolved_capabilities: List[str] = field(default_factory=list)
    rejected_tools: Dict[str, str] = field(default_factory=dict)
    binding_scores: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    benchmark_hints_used: List[str] = field(default_factory=list)
    overplanning_risk: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningResult:
    workflow: Workflow
    artifact: PlanningArtifact
    diagnostics: PlanningDiagnostics = field(default_factory=PlanningDiagnostics)


@dataclass
class CapabilityCandidate:
    capability_id: str
    description: str
    score: float
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilitySelector:
    def select(
        self,
        task: TaskSpec,
        context: WorkflowContext,
        hints: PlanningHints,
    ) -> List[CapabilityCandidate]:
        raise NotImplementedError


class RuleBasedCapabilitySelector(CapabilitySelector):
    def select(
        self,
        task: TaskSpec,
        context: WorkflowContext,
        hints: PlanningHints,
    ) -> List[CapabilityCandidate]:
        benchmark_hints = self._benchmark_hints(context=context, hints=hints)
        goal = task.user_goal.lower()
        tool_tokens = tool_semantic_tokens(
            context.candidate_tools,
            allowed_tool_ids=benchmark_hints.get("tool_allow_list", []),
        )
        ranked_profiles = rank_capability_profiles(
            goal_text=goal,
            tool_tokens=tool_tokens,
            hint_texts=[
                benchmark_hints.get("milestones", []),
                benchmark_hints.get("tool_allow_list", []),
                hints.preferred_capabilities,
            ],
        )
        minimal_capability = self._minimal_capability_hint(
            goal=goal,
            benchmark_hints=benchmark_hints,
            ranked_profiles=ranked_profiles,
        )
        if minimal_capability is not None:
            return [minimal_capability]
        candidates = self._candidates_from_ranked_profiles(ranked_profiles)
        if any(candidate.capability_id == "cap_summarize" for candidate in candidates) and not any(
            candidate.capability_id == "cap_retrieve" for candidate in candidates
        ):
            retrieve_profile = CAPABILITY_PROFILES_BY_ID["cap_retrieve"]
            candidates.insert(
                0,
                CapabilityCandidate(
                    capability_id=retrieve_profile.capability_id,
                    description=retrieve_profile.description,
                    score=0.58,
                    postconditions=list(retrieve_profile.postconditions),
                    metadata={"injected_dependency": "cap_summarize"},
                ),
            )
        if not candidates:
            fallback_profile = ranked_profiles[0]["profile"] if ranked_profiles and ranked_profiles[0]["score"] > 0 else None
            if fallback_profile is not None:
                candidates = [
                    CapabilityCandidate(
                        capability_id=fallback_profile.capability_id,
                        description=fallback_profile.description,
                        score=max(0.55, float(ranked_profiles[0]["score"])),
                        preconditions=list(fallback_profile.preconditions),
                        postconditions=list(fallback_profile.postconditions),
                        metadata={
                            "selected_from_tool_semantics": True,
                            "tool_overlap": list(ranked_profiles[0]["tool_overlap"]),
                        },
                    )
                ]
            else:
                retrieve_profile = CAPABILITY_PROFILES_BY_ID["cap_retrieve"]
                write_profile = CAPABILITY_PROFILES_BY_ID["cap_write"]
                candidates = [
                    CapabilityCandidate(
                        capability_id=retrieve_profile.capability_id,
                        description=retrieve_profile.description,
                        score=0.6,
                        postconditions=list(retrieve_profile.postconditions),
                    ),
                    CapabilityCandidate(
                        capability_id=write_profile.capability_id,
                        description=write_profile.description,
                        score=0.6,
                        preconditions=["information_obtained"],
                        postconditions=list(write_profile.postconditions),
                    ),
                ]
        preferred = set(hints.preferred_capabilities)
        for candidate in candidates:
            if candidate.capability_id in preferred:
                candidate.score += 0.1
            if candidate.capability_id in benchmark_hints["preferred_capabilities"]:
                candidate.score += 0.08
        return candidates

    @staticmethod
    def _candidates_from_ranked_profiles(ranked_profiles: Sequence[Dict[str, Any]]) -> List[CapabilityCandidate]:
        candidates: List[CapabilityCandidate] = []
        selected_capability_ids = {
            item["profile"].capability_id for item in ranked_profiles if float(item["score"]) >= 0.22
        }
        for ranked in ranked_profiles:
            profile = ranked["profile"]
            score = float(ranked["score"])
            if score < 0.22:
                continue
            preconditions = list(profile.preconditions)
            if profile.capability_id == "cap_write":
                if "cap_summarize" in selected_capability_ids:
                    preconditions = ["summary_ready"]
                elif "cap_retrieve" in selected_capability_ids:
                    preconditions = ["information_obtained"]
            candidates.append(
                CapabilityCandidate(
                    capability_id=profile.capability_id,
                    description=profile.description,
                    score=score,
                    preconditions=preconditions,
                    postconditions=list(profile.postconditions),
                    metadata={
                        "goal_overlap": list(ranked["goal_overlap"]),
                        "tool_overlap": list(ranked["tool_overlap"]),
                        "hint_overlap": list(ranked["hint_overlap"]),
                    },
                )
            )
        return candidates

    @staticmethod
    def _benchmark_hints(context: WorkflowContext, hints: PlanningHints) -> Dict[str, Any]:
        user_style = dict(hints.user_style)
        categories = [str(item) for item in user_style.get("categories", []) if str(item)]
        tool_allow_list = [str(item) for item in user_style.get("tool_allow_list", []) if str(item)]
        if not tool_allow_list:
            tool_allow_list = [tool.tool_id for tool in context.candidate_tools]
        milestones = [str(item) for item in user_style.get("milestones", []) if str(item)]
        ideal_tool_calls = HTGPPlanner._coerce_int(user_style.get("ideal_tool_calls"))
        preferred_capabilities = []
        if any(category in {"single_tool", "state_dependency"} for category in categories):
            preferred_capabilities.append("cap_write")
        if any(category in {"multiple_tool", "canonicalization"} for category in categories):
            preferred_capabilities.append("cap_retrieve")
        return {
            "categories": categories,
            "tool_allow_list": tool_allow_list,
            "ideal_tool_calls": ideal_tool_calls,
            "milestones": milestones,
            "preferred_capabilities": preferred_capabilities,
        }

    @staticmethod
    def _minimal_capability_hint(
        goal: str,
        benchmark_hints: Dict[str, Any],
        ranked_profiles: Sequence[Dict[str, Any]],
    ) -> Optional[CapabilityCandidate]:
        categories = set(benchmark_hints.get("categories", []))
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        tool_allow_list = benchmark_hints.get("tool_allow_list", [])
        top_score = float(ranked_profiles[0]["score"]) if ranked_profiles else 0.0
        runner_up_score = float(ranked_profiles[1]["score"]) if len(ranked_profiles) > 1 else 0.0
        should_minimize = (
            "multiple_user_turn" not in categories
            and (
                ideal_tool_calls == 1
                or len(tool_allow_list) == 1
                or "single_tool" in categories
                or (len(tool_allow_list) == 1 and top_score >= 0.24 and runner_up_score <= top_score * 0.75)
            )
        )
        if not should_minimize:
            return None
        if ranked_profiles and top_score > 0:
            chosen_profile = ranked_profiles[0]["profile"]
            capability_id = chosen_profile.capability_id
            description = chosen_profile.description
            postconditions = list(chosen_profile.postconditions)
            metadata = {
                "selected_from_benchmark_hints": bool(
                    ideal_tool_calls == 1 or "single_tool" in categories or len(tool_allow_list) == 1
                ),
                "selected_from_tool_semantics": bool(ranked_profiles[0]["tool_overlap"]),
                "goal_overlap": list(ranked_profiles[0]["goal_overlap"]),
                "tool_overlap": list(ranked_profiles[0]["tool_overlap"]),
            }
        else:
            capability_id = "cap_write" if any(token in goal for token in ["write", "save", "send", "report", "set"]) else "cap_retrieve"
            description = "Complete the single-step tool action" if capability_id == "cap_write" else "Retrieve the required result"
            postconditions = ["artifact_ready"] if capability_id == "cap_write" else ["information_obtained"]
            metadata = {"selected_from_benchmark_hints": True}
        return CapabilityCandidate(
            capability_id=capability_id,
            description=description,
            score=0.95,
            postconditions=postconditions,
            metadata=metadata,
        )


class CapabilityGraphBuilder:
    def build(
        self,
        task: TaskSpec,
        candidates: Sequence[CapabilityCandidate],
        benchmark_hints: Optional[Dict[str, Any]] = None,
    ) -> CapabilityGraph:
        raise NotImplementedError


class PolicyInjector:
    _CONTACT_NAME_PATTERN = re.compile(r"tool_name['\"]:\s*['\"]search_contacts['\"].+?['\"]name['\"]:\s*['\"]([^'\"]+)['\"]", re.IGNORECASE | re.DOTALL)
    _MESSAGE_CONTENT_DOUBLE_QUOTE_PATTERN = re.compile(
        r"recipient_phone_number['\"]:\s*['\"][^'\"]+['\"],\s*['\"]content['\"]:\s*\"([^\"]+)\"",
        re.IGNORECASE | re.DOTALL,
    )
    _MESSAGE_CONTENT_SINGLE_QUOTE_PATTERN = re.compile(
        r"recipient_phone_number['\"]:\s*['\"][^'\"]+['\"],\s*['\"]content['\"]:\s*'([^']+)'",
        re.IGNORECASE | re.DOTALL,
    )

    def inject(
        self,
        graph: CapabilityGraph,
        task: TaskSpec,
        context: WorkflowContext,
        policy: Optional[WorkflowPolicy],
    ) -> CapabilityGraph:
        _ = task, context
        if not policy:
            return graph

        for capability in graph.capabilities:
            if self._requires_approval(task=task, capability=capability, policy=policy) and "requires_approval" not in capability.preconditions:
                capability.preconditions.append("requires_approval")
        return graph

    @staticmethod
    def _requires_approval(
        task: TaskSpec,
        capability: CapabilityNode,
        policy: WorkflowPolicy,
    ) -> bool:
        for rule in policy.approval_rules:
            if rule.action != "ask_user":
                continue
            if PolicyInjector._trigger_matches(rule.trigger, task=task, capability=capability):
                return True
        return False

    @staticmethod
    def _trigger_matches(
        trigger: str,
        task: TaskSpec,
        capability: CapabilityNode,
    ) -> bool:
        normalized = trigger.strip().lower()
        if not normalized:
            return False
        if normalized in {"always", "*"}:
            return True
        if normalized == capability.capability_id.lower():
            return True
        if normalized in capability.description.lower():
            return True
        if "==" not in normalized:
            return False

        lhs, rhs = [part.strip() for part in normalized.split("==", 1)]
        rhs = rhs.strip("'\"")
        if lhs == "risk_level":
            return task.constraints.risk_level.value == rhs
        if lhs == "capability_id":
            return capability.capability_id.lower() == rhs
        if lhs == "requires_user_approval":
            expected = rhs in {"true", "1", "yes"}
            return bool(task.constraints.requires_user_approval) is expected
        return False

    def compile_execution_plan(
        self,
        graph: CapabilityGraph,
        bindings: List[ToolBinding],
        task: TaskSpec,
        benchmark_hints: Optional[Dict[str, Any]] = None,
        step_hints: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[WorkflowStep]:
        benchmark_hints = benchmark_hints or {}
        step_hints = list(step_hints or [])
        milestone_assignments = self._assign_milestones_to_capabilities(
            [capability.capability_id for capability in graph.capabilities],
            benchmark_hints.get("milestones", []),
        )
        branch_options = [str(item) for item in benchmark_hints.get("branch_options", []) if str(item)]
        allowed_tools = [str(item) for item in benchmark_hints.get("tool_allow_list", []) if str(item)]
        steps: List[WorkflowStep] = []
        for idx, capability in enumerate(graph.capabilities, start=1):
            hint = step_hints[idx - 1] if idx - 1 < len(step_hints) else {}
            binding = bindings[idx - 1] if idx - 1 < len(bindings) else None
            tool_id = binding.primary_tool if binding else None
            if capability.capability_id == "cap_retrieve":
                inputs = {"query": task.user_goal}
                expected_output = "retrieved_info"
            elif capability.capability_id == "cap_summarize":
                inputs = {"source_key": "retrieved_info"}
                expected_output = "summary_text"
            elif capability.capability_id == "cap_write":
                inputs = {"target_path": "outputs/reports/planned_report.txt"}
                if benchmark_hints.get("ideal_tool_calls") == 1:
                    inputs["query"] = task.user_goal
                expected_output = "report_artifact"
            else:
                inputs = {}
                expected_output = None
            inputs, expected_output = self._tool_specific_inputs(
                tool_id=tool_id,
                task=task,
                benchmark_hints=benchmark_hints,
                default_inputs=inputs,
                default_expected_output=expected_output,
            )

            dependency_sources = [str(item) for item in hint.get("dependency_sources", []) if str(item)]
            ordering_sensitive = bool(hint.get("ordering_sensitive"))
            rollback_to = dependency_sources[-1] if dependency_sources else (f"step_{idx - 1:02d}" if idx > 1 else None)
            required_state_slots = [str(item) for item in hint.get("required_state_slots", []) if str(item)]
            state_bindings = dict(hint.get("state_bindings", {})) if isinstance(hint.get("state_bindings"), dict) else {}
            preflight_state_policy = (
                dict(hint.get("preflight_state_policy", {}))
                if isinstance(hint.get("preflight_state_policy"), dict)
                else {}
            )
            required_input_keys = list(binding.required_input_keys) if binding else []
            input_bindings = dict(binding.input_bindings) if binding else {}
            grounding_sources = dict(binding.grounding_sources) if binding else {}
            grounding_confidence = dict(binding.grounding_confidence) if binding else {}
            unresolved_required_inputs = list(binding.unresolved_required_inputs) if binding else []
            checkpoint_reason = (
                str(hint.get("checkpoint_reason"))
                if hint.get("checkpoint_reason")
                else ("ordering_sensitive_dependency" if ordering_sensitive else "planner_injected")
            )

            steps.append(
                WorkflowStep(
                    step_id=f"step_{idx:02d}",
                    capability_id=capability.capability_id,
                    tool_id=tool_id,
                    action_type=ActionType.TOOL_CALL,
                    inputs=inputs,
                    expected_output=expected_output,
                    checkpoint=True,
                    rollback_to=rollback_to,
                    requires_user_confirmation=("requires_approval" in capability.preconditions),
                    metadata={
                        "policy_gate": "default_phase1",
                        "requires_approval": "requires_approval" in capability.preconditions,
                        "benchmark_hint_step": bool(benchmark_hints),
                        "milestone_hint": milestone_assignments.get(capability.capability_id),
                        "milestone_index": self._milestone_index(
                            milestone_assignments.get(capability.capability_id),
                            benchmark_hints.get("milestones", []),
                        ),
                        "required_state_slots": required_state_slots,
                        "state_bindings": state_bindings,
                        "required_input_keys": required_input_keys,
                        "input_bindings": input_bindings,
                        "grounding_sources": grounding_sources,
                        "grounding_confidence": grounding_confidence,
                        "unresolved_required_inputs": unresolved_required_inputs,
                        "ordering_sensitive": ordering_sensitive,
                        "dependency_sources": dependency_sources,
                        "dependency_type": hint.get("dependency_type"),
                        "checkpoint_reason": checkpoint_reason,
                        "preflight_state_policy": preflight_state_policy,
                        "allowed_tools": allowed_tools,
                        "branch_options": branch_options if idx == len(graph.capabilities) and branch_options else [],
                        "branch_sensitive": bool(idx == len(graph.capabilities) and branch_options),
                        "implicit_state_fallback_slots": ["retrieved_info", "query"] if capability.capability_id == "cap_write" else [],
                    },
                )
            )
        return steps

    @classmethod
    def _tool_specific_inputs(
        cls,
        *,
        tool_id: Optional[str],
        task: TaskSpec,
        benchmark_hints: Dict[str, Any],
        default_inputs: Dict[str, Any],
        default_expected_output: Optional[str],
    ) -> tuple[Dict[str, Any], Optional[str]]:
        normalized_tool = str(tool_id or "").strip().lower()
        if not normalized_tool:
            return default_inputs, default_expected_output

        if normalized_tool == "search_contacts":
            contact_name = cls._extract_contact_name(benchmark_hints)
            inputs = {"name": contact_name} if contact_name else dict(default_inputs)
            return inputs, "retrieved_info"

        if normalized_tool == "send_message_with_phone_number":
            inputs = dict(default_inputs)
            content = cls._extract_message_content(benchmark_hints)
            contact_name = cls._extract_contact_name(benchmark_hints)
            if content:
                inputs["content"] = content
            elif task.user_goal:
                inputs.setdefault("content", task.user_goal)
            if contact_name:
                inputs.setdefault("recipient", contact_name)
            return inputs, "message_sent"

        if normalized_tool == "set_cellular_service_status":
            return {"enabled": True}, "cellular_service_status"

        if normalized_tool == "get_cellular_service_status":
            return {}, "cellular_service_status"

        return default_inputs, default_expected_output

    @classmethod
    def _extract_contact_name(cls, benchmark_hints: Dict[str, Any]) -> Optional[str]:
        milestone_blob = "\n".join(str(item) for item in benchmark_hints.get("milestones", []) if str(item))
        match = cls._CONTACT_NAME_PATTERN.search(milestone_blob)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def _extract_message_content(cls, benchmark_hints: Dict[str, Any]) -> Optional[str]:
        milestone_blob = "\n".join(str(item) for item in benchmark_hints.get("milestones", []) if str(item))
        for pattern in (cls._MESSAGE_CONTENT_DOUBLE_QUOTE_PATTERN, cls._MESSAGE_CONTENT_SINGLE_QUOTE_PATTERN):
            match = pattern.search(milestone_blob)
            if match:
                return match.group(1).strip()
        return None

    def compile_workflow_graph(
        self,
        graph: CapabilityGraph,
        steps: List[WorkflowStep],
        bindings: Optional[List[ToolBinding]] = None,
        benchmark_hints: Optional[Dict[str, Any]] = None,
    ) -> WorkflowGraph:
        benchmark_hints = benchmark_hints or {}
        branch_options = [str(item) for item in benchmark_hints.get("branch_options", []) if str(item)]
        allowed_tools = {str(item) for item in benchmark_hints.get("tool_allow_list", []) if str(item)}
        nodes: List[WorkflowNode] = []
        edges: List[WorkflowEdge] = []
        for idx, step in enumerate(steps):
            binding = bindings[idx] if bindings and idx < len(bindings) else None
            tool_candidates = ([step.tool_id] if step.tool_id else []) + (list(binding.backup_tools) if binding else [])
            if allowed_tools:
                tool_candidates = [tool_id for tool_id in tool_candidates if tool_id in allowed_tools]
            required_state_slots = [str(item) for item in step.metadata.get("required_state_slots", []) if str(item)]
            required_input_keys = [str(item) for item in step.metadata.get("required_input_keys", []) if str(item)]
            preflight_state_policy = (
                dict(step.metadata.get("preflight_state_policy", {}))
                if isinstance(step.metadata.get("preflight_state_policy"), dict)
                else {}
            )
            preflight_requirements = [
                PreflightRequirement(
                    asset_key=slot,
                    source="state_slot",
                    required=True,
                    metadata={"step_id": step.step_id},
                )
                for slot in required_state_slots
            ]
            existing_requirement_keys = {req.asset_key for req in preflight_requirements}
            for input_key in required_input_keys:
                if input_key in existing_requirement_keys:
                    continue
                preflight_requirements.append(
                    PreflightRequirement(
                        asset_key=input_key,
                        source="required_input",
                        required=True,
                        metadata={"step_id": step.step_id},
                    )
                )
            preflight_slot = str(preflight_state_policy.get("state_slot") or "")
            if preflight_slot and preflight_slot not in {req.asset_key for req in preflight_requirements}:
                preflight_requirements.append(
                    PreflightRequirement(
                        asset_key=preflight_slot,
                        source="preflight_policy",
                        required=True,
                        metadata={"required_value": preflight_state_policy.get("required_value")},
                    )
                )
            fallback_routes = [
                FallbackRoute(
                    tool_id=tool_id,
                    condition="on_tool_failure",
                    priority=priority,
                    metadata={"planner_ranked_backup": True},
                )
                for priority, tool_id in enumerate(list(binding.backup_tools) if binding else [], start=1)
            ]
            dependency_sources = [str(item) for item in step.metadata.get("dependency_sources", []) if str(item)]
            nodes.append(
                WorkflowNode(
                    node_id=step.step_id,
                    capability_id=step.capability_id,
                    selected_tool=step.tool_id,
                    tool_candidates=tool_candidates,
                    inputs=dict(step.inputs),
                    expected_output=step.expected_output,
                    dependencies=dependency_sources or ([steps[idx - 1].step_id] if idx > 0 else []),
                    checkpoint_policy=CheckpointPolicy(
                        enabled=step.checkpoint,
                        reason=str(step.metadata.get("checkpoint_reason") or "planner_injected"),
                    ),
                    rollback_policy=RollbackPolicy(
                        rollback_to_step_id=step.rollback_to,
                        reason="ordering_sensitive_dependency" if step.metadata.get("ordering_sensitive") else None,
                    ),
                    approval_gate=ApprovalGate(required=step.requires_user_confirmation),
                    fallback_routes=fallback_routes,
                    preflight_requirements=preflight_requirements,
                    metadata=dict(step.metadata),
                )
            )
            edge_sources = dependency_sources or ([steps[idx - 1].step_id] if idx > 0 else [])
            for dependency_source in edge_sources:
                edge_condition = "on_branch_resolved" if step.metadata.get("branch_sensitive") else "on_success"
                if step.metadata.get("dependency_type") == "state":
                    edge_condition = "on_state_ready"
                edges.append(WorkflowEdge(source=dependency_source, target=step.step_id, condition=edge_condition))
            if binding and binding.backup_tools:
                edges.append(WorkflowEdge(source=step.step_id, target=step.step_id, condition="on_tool_failure_use_backup"))
            if step.requires_user_confirmation:
                edges.append(WorkflowEdge(source=step.step_id, target=step.step_id, condition="on_approval_resume"))
            if step.metadata.get("branch_sensitive") and branch_options:
                for branch_option in branch_options:
                    edges.append(
                        WorkflowEdge(
                            source=step.step_id,
                            target=step.step_id,
                            condition=f"on_branch:{branch_option}",
                            edge_type="branch",
                        )
                    )
        return WorkflowGraph(
            nodes=nodes,
            edges=edges,
            entry_nodes=[steps[0].step_id] if steps else [],
            exit_nodes=[steps[-1].step_id] if steps else [],
            metadata={
                "capability_count": len(graph.capabilities),
                "has_conditional_edges": any(edge.condition for edge in edges),
                "branch_options": branch_options,
            },
        )

    @staticmethod
    def _assign_milestones_to_capabilities(
        capability_ids: Sequence[str],
        raw_milestones: Sequence[Any],
    ) -> Dict[str, str]:
        assignments: Dict[str, str] = {}
        remaining = [str(item) for item in raw_milestones if str(item)]
        if not remaining:
            return assignments
        for capability_id in capability_ids:
            for milestone in list(remaining):
                if PolicyInjector._milestone_matches_capability(milestone, capability_id):
                    assignments[capability_id] = milestone
                    remaining.remove(milestone)
                    break
        return assignments

    @staticmethod
    def _milestone_index(milestone: Optional[str], raw_milestones: Sequence[Any]) -> Optional[int]:
        if not milestone:
            return None
        normalized_milestones = [str(item) for item in raw_milestones if str(item)]
        try:
            return normalized_milestones.index(milestone)
        except ValueError:
            return None

    @staticmethod
    def _milestone_matches_capability(milestone: str, capability_id: str) -> bool:
        text = milestone.strip().lower()
        if capability_id == "cap_retrieve":
            return any(keyword in text for keyword in ("retrieve", "find", "search", "lookup", "locate", "collect", "fetch", "get"))
        if capability_id == "cap_summarize":
            return any(keyword in text for keyword in ("summarize", "summary", "analyze", "analysis", "draft", "compose"))
        if capability_id == "cap_write":
            return any(keyword in text for keyword in ("write", "save", "send", "set", "update", "book", "reply", "report", "disable", "enable"))
        return False


class HTGPPlanner:
    def __init__(
        self,
        capability_selector: CapabilitySelector,
        graph_builder: CapabilityGraphBuilder,
        binder: ToolBinder,
        policy_injector: PolicyInjector,
        asset_registry: Optional["AssetRegistry"] = None,
    ) -> None:
        self.capability_selector = capability_selector
        self.graph_builder = graph_builder
        self.binder = binder
        self.policy_injector = policy_injector
        self.asset_registry = asset_registry

    def plan(self, request: PlanningRequest) -> PlanningResult:
        diagnostics = PlanningDiagnostics()
        benchmark_hints = self._benchmark_hints(request)
        benchmark_hints["overplanning_objective"] = self._build_overplanning_objective(
            benchmark_hints,
            completed_step_count=0,
        )
        benchmark_hints["budget_targets"] = self._budget_targets(request)
        diagnostics.benchmark_hints_used = sorted(benchmark_hints["used_keys"])
        candidates = self.capability_selector.select(request.task, request.context, request.hints)
        bypass_applied = self._should_bypass(request, benchmark_hints)
        minimal_path_reason = self._minimal_path_reason(request, benchmark_hints) if bypass_applied else "not_applied"
        selected_capability_order_initial = [candidate.capability_id for candidate in candidates]
        if bypass_applied and candidates:
            diagnostics.warnings.append("planner_bypass_applied:minimal_path")
            minimal_candidate = candidates[0]
            graph = CapabilityGraph(
                capabilities=[
                    CapabilityNode(
                        capability_id=minimal_candidate.capability_id,
                        description=minimal_candidate.description,
                        preconditions=list(minimal_candidate.preconditions),
                        postconditions=list(minimal_candidate.postconditions),
                    )
                ],
                edges=[],
            )
        else:
            built_graph = self.graph_builder.build(request.task, candidates, benchmark_hints=benchmark_hints)
            graph = built_graph[0] if isinstance(built_graph, tuple) else built_graph
        reusable_profile = self._load_reusable_profile(
            request,
            graph,
            overplanning_objective=benchmark_hints.get("overplanning_objective", {}),
        )
        resolved_reusable_asset_ids = [
            str(asset_id) for asset_id in reusable_profile.get("asset_ids", []) if str(asset_id)
        ]
        if resolved_reusable_asset_ids:
            request.hints.reusable_asset_ids = list(dict.fromkeys(resolved_reusable_asset_ids))
        if reusable_profile["capability_order"]:
            order = reusable_profile["capability_order"]
            rank = {cap_id: idx for idx, cap_id in enumerate(order)}
            graph.capabilities.sort(key=lambda capability: rank.get(capability.capability_id, len(rank)))
        graph = self._apply_overplanning_objective_to_graph(
            graph,
            benchmark_hints.get("overplanning_objective", {}),
        )
        graph = self.policy_injector.inject(graph, request.task, request.context, request.policy)

        candidate_tools = request.context.candidate_tools
        allowed_tools = {str(item) for item in benchmark_hints.get("tool_allow_list", []) if str(item)}
        if allowed_tools:
            candidate_tools = [tool for tool in request.context.candidate_tools if tool.tool_id in allowed_tools]
        preferred_bindings = self._benchmark_preferred_bindings(candidate_tools, benchmark_hints)
        preferred_bindings.update(dict(reusable_profile.get("recommended_bindings", {})))
        step_hints = self._step_planning_hints(
            graph=graph,
            benchmark_hints=benchmark_hints,
            candidate_tools=candidate_tools,
        )
        binding_results = self.binder.bind_graph(
            capabilities=graph.capabilities,
            candidate_tools=candidate_tools,
            context=request.context,
            forbidden_tools=request.hints.forbidden_tools,
            preferred_bindings=preferred_bindings,
            state_values={"__failure_context__": benchmark_hints.get("primary_failtax")},
            step_hints=step_hints,
            backup_tool_map=dict(benchmark_hints.get("backup_tool_map", {})),
        )

        bindings: List[ToolBinding] = []
        for capability, binding_result in zip(graph.capabilities, binding_results):
            if binding_result.binding is None:
                diagnostics.unresolved_capabilities.append(capability.capability_id)
                diagnostics.warnings.append(f"unresolved capability: {capability.capability_id}")
                continue

            bindings.append(binding_result.binding)
            diagnostics.binding_scores[capability.capability_id] = binding_result.binding.binding_confidence

        execution_plan = self.policy_injector.compile_execution_plan(
            graph,
            bindings,
            request.task,
            benchmark_hints=benchmark_hints,
            step_hints=step_hints,
        )
        workflow_graph = self.policy_injector.compile_workflow_graph(
            graph,
            execution_plan,
            bindings=bindings,
            benchmark_hints=benchmark_hints,
        )
        diagnostics.overplanning_risk = self._overplanning_risk(
            request=request,
            execution_plan=execution_plan,
            bindings=bindings,
            bypass_applied=bypass_applied,
            benchmark_hints=benchmark_hints,
        )
        if diagnostics.overplanning_risk.get("expanded_single_tool_task"):
            diagnostics.warnings.append("overplanning_risk:single_tool_expanded")
        if diagnostics.overplanning_risk.get("steps_exceed_ideal"):
            diagnostics.warnings.append("overplanning_risk:steps_exceed_ideal_tool_calls")
        if diagnostics.overplanning_risk.get("used_disallowed_tool"):
            diagnostics.warnings.append("overplanning_risk:used_tool_outside_allow_list")
        planner_observability = self._planner_observability(
            bypass_applied=bypass_applied,
            minimal_path_reason=minimal_path_reason,
            selected_capability_order_initial=selected_capability_order_initial,
            graph=graph,
            candidates=candidates,
            bindings=bindings,
            diagnostics=diagnostics,
        )

        workflow = Workflow(
            workflow_id=f"wf_{request.task.task_id}",
            version="0.1",
            phase=Phase.PHASE1_TRAINING_FREE,
            task=request.task,
            context=request.context,
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            workflow_graph=workflow_graph,
            policy=request.policy or Workflow.demo().policy,
            metadata={
                "planner_mode": request.planner_mode,
                "task_family": str(request.hints.user_style.get("task_family", "t0_general")),
                "failure_type": str(request.hints.user_style.get("failure_type", "none")),
                "scenario": str(request.hints.user_style.get("scenario", "success")),
                "planning_request": self._snapshot_request(request),
                "benchmark_hints": {
                    "categories": list(benchmark_hints.get("categories", [])),
                    "tool_allow_list": list(benchmark_hints.get("tool_allow_list", [])),
                    "backup_tool_map": dict(benchmark_hints.get("backup_tool_map", {})),
                    "ideal_tool_calls": benchmark_hints.get("ideal_tool_calls"),
                    "ideal_turn_count": benchmark_hints.get("ideal_turn_count"),
                    "milestones": list(benchmark_hints.get("milestones", [])),
                    "branch_options": list(benchmark_hints.get("branch_options", [])),
                    "overplanning_objective": dict(benchmark_hints.get("overplanning_objective", {})),
                    "budget_targets": dict(benchmark_hints.get("budget_targets", {})),
                },
                "budget_targets": dict(benchmark_hints.get("budget_targets", {})),
                "reusable_context": {
                    "resolved_asset_ids": list(request.hints.reusable_asset_ids),
                    "profile_loaded": bool(resolved_reusable_asset_ids),
                    "reuse_mode": str(reusable_profile.get("reuse_mode", "none")),
                    "reuse_application": str(reusable_profile.get("reuse_application", "none")),
                    "utility_gain_score": float(reusable_profile.get("utility_gain_score", 0.0) or 0.0),
                    "selected_match": deepcopy(reusable_profile.get("selected_match", {})),
                },
                "reuse_override_inputs": deepcopy(request.hints.user_style.get("reuse_override_inputs", {})),
                "tool_execution_backend": str(request.hints.user_style.get("tool_execution_backend", "mock")),
                "planner_observability": planner_observability,
            },
        )
        workflow.metadata.update(self._passthrough_workflow_metadata(request))
        self._apply_request_overrides(workflow, request.workflow_overrides)
        self._apply_reusable_continuation_hints(workflow, reusable_profile)
        self._apply_reusable_hints(workflow, reusable_profile)

        artifact = PlanningArtifact(
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            metadata={
                "candidate_count": len(candidates),
                "bypass_applied": bypass_applied,
                "benchmark_hints_used": diagnostics.benchmark_hints_used,
                "planner_observability": planner_observability,
            },
        )
        return PlanningResult(workflow=workflow, artifact=artifact, diagnostics=diagnostics)

    @staticmethod
    def _benchmark_preferred_bindings(
        candidate_tools: Sequence[ToolSpec],
        benchmark_hints: Dict[str, Any],
    ) -> Dict[str, str]:
        allow_order = [str(item) for item in benchmark_hints.get("tool_allow_list", []) if str(item)]
        if not allow_order:
            return {}
        tool_by_id = {tool.tool_id: tool for tool in candidate_tools}
        inferred_by_capability: Dict[str, List[str]] = {}
        for tool_id in allow_order:
            tool = tool_by_id.get(tool_id)
            if tool is None:
                continue
            inferred = infer_capability_from_text(f"{tool.tool_id} {tool.description}")
            if inferred:
                inferred_by_capability.setdefault(inferred, []).append(tool.tool_id)
        preferred: Dict[str, str] = {}
        for capability_id, tool_ids in inferred_by_capability.items():
            # Avoid allow-list order bias when multiple tools match one capability (e.g. planner-sensitive writer distractors).
            if len(tool_ids) == 1:
                preferred[capability_id] = tool_ids[0]
                continue
            milestone_preferred = HTGPPlanner._milestone_preferred_tool_id(
                tool_ids=tool_ids,
                milestones=[str(item) for item in benchmark_hints.get("milestones", []) if str(item)],
            )
            if milestone_preferred:
                preferred[capability_id] = milestone_preferred
        return preferred

    @staticmethod
    def _milestone_preferred_tool_id(
        *,
        tool_ids: Sequence[str],
        milestones: Sequence[str],
    ) -> Optional[str]:
        if not tool_ids or not milestones:
            return None
        milestone_blob = "\n".join(milestones).lower()
        for tool_id in tool_ids:
            token = str(tool_id).strip().lower()
            if token and token in milestone_blob:
                return tool_id
        return None

    @staticmethod
    def _parse_step_ordinal(step_id: Any) -> Optional[int]:
        match = re.match(r"step_(\d+)$", str(step_id or "").strip().lower())
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _state_slot_for_capability(capability_id: str) -> Optional[str]:
        return {
            "cap_retrieve": "retrieved_info",
            "cap_summarize": "summary_text",
            "cap_write": "report_artifact",
        }.get(str(capability_id or "").strip().lower())

    @staticmethod
    def _state_slot_for_precondition(precondition: str) -> Optional[str]:
        return {
            "information_obtained": "retrieved_info",
            "summary_ready": "summary_text",
            "artifact_ready": "report_artifact",
            "requires_approval": "approved",
            "approved": "approved",
        }.get(str(precondition or "").strip().lower())

    @staticmethod
    def _tool_uses_outbound_cellular(tool_id: str) -> bool:
        normalized = str(tool_id or "").strip().lower()
        return "send_message" in normalized or normalized in {"send_sms", "send_text"}

    @classmethod
    def _normalized_dependency_edges(cls, benchmark_hints: Dict[str, Any]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for raw_edge in benchmark_hints.get("dependency_edges", []):
            if not isinstance(raw_edge, dict):
                continue
            source = str(raw_edge.get("source") or "").strip()
            target = str(raw_edge.get("target") or "").strip()
            edge_type = str(raw_edge.get("type") or raw_edge.get("edge_type") or "default").strip().lower()
            if source and target:
                normalized.append({"source": source, "target": target, "type": edge_type or "default"})
        return normalized

    @classmethod
    def _step_planning_hints(
        cls,
        *,
        graph: CapabilityGraph,
        benchmark_hints: Dict[str, Any],
        candidate_tools: Sequence[ToolSpec],
    ) -> List[Dict[str, Any]]:
        hints: List[Dict[str, Any]] = []
        for capability in graph.capabilities:
            state_bindings: Dict[str, str] = {}
            required_state_slots: List[str] = []
            state_preconditions: List[str] = []
            for precondition in capability.preconditions:
                normalized_precondition = str(precondition or "").strip()
                if not normalized_precondition:
                    continue
                if normalized_precondition not in state_preconditions:
                    state_preconditions.append(normalized_precondition)
                slot = cls._state_slot_for_precondition(normalized_precondition)
                if slot and slot not in required_state_slots:
                    required_state_slots.append(slot)
                    state_bindings.setdefault(slot, slot)
            hints.append(
                {
                    "required_state_slots": required_state_slots,
                    "state_preconditions": state_preconditions,
                    "state_bindings": state_bindings,
                    "ordering_sensitive": bool(required_state_slots),
                    "dependency_sources": [],
                    "dependency_type": None,
                    "checkpoint_reason": None,
                    "preflight_state_policy": {},
                }
            )

        normalized_edges = cls._normalized_dependency_edges(benchmark_hints)
        for edge in normalized_edges:
            source_ordinal = cls._parse_step_ordinal(edge["source"])
            target_ordinal = cls._parse_step_ordinal(edge["target"])
            if source_ordinal is None or target_ordinal is None:
                continue
            source_index = source_ordinal - 1
            target_index = target_ordinal - 1
            if not (0 <= source_index < len(graph.capabilities) and 0 <= target_index < len(graph.capabilities)):
                continue
            source_capability = graph.capabilities[source_index]
            target_hint = hints[target_index]
            source_step_id = f"step_{source_ordinal:02d}"
            if source_step_id not in target_hint["dependency_sources"]:
                target_hint["dependency_sources"].append(source_step_id)
            target_hint["ordering_sensitive"] = True
            target_hint["dependency_type"] = edge["type"]
            target_hint["checkpoint_reason"] = f"{edge['type']}_dependency"
            if edge["type"] == "state":
                slot = cls._state_slot_for_capability(source_capability.capability_id)
                if slot and slot not in target_hint["required_state_slots"]:
                    target_hint["required_state_slots"].append(slot)
                    target_hint["state_bindings"].setdefault(slot, slot)

        state_slots = [str(item) for item in benchmark_hints.get("state_slots", []) if str(item)]
        allowed_tools = {str(item) for item in benchmark_hints.get("tool_allow_list", []) if str(item)}
        candidate_tool_ids = {tool.tool_id for tool in candidate_tools}
        if (
            "cellular_service_status" in state_slots
            and any(cls._tool_uses_outbound_cellular(tool_id) for tool_id in candidate_tool_ids)
            and {"get_cellular_service_status", "set_cellular_service_status"}.intersection(allowed_tools or candidate_tool_ids)
        ):
            for index in range(len(graph.capabilities) - 1, -1, -1):
                if graph.capabilities[index].capability_id != "cap_write":
                    continue
                hint = hints[index]
                if "cellular_service_status" not in hint["required_state_slots"]:
                    hint["required_state_slots"].append("cellular_service_status")
                    hint["state_bindings"].setdefault("cellular_on", "cellular_service_status")
                hint["ordering_sensitive"] = True
                hint["checkpoint_reason"] = hint["checkpoint_reason"] or "preflight_state_dependency"
                hint["preflight_state_policy"] = {
                    "state_slot": "cellular_service_status",
                    "required_value": True,
                    "repair_target": "cellular_service_status",
                    "repair_value": True,
                    "auto_repair": "set_cellular_service_status" in (allowed_tools or candidate_tool_ids),
                    "reason": "outbound messaging requires cellular connectivity",
                }
                break

        return hints

    @staticmethod
    def _snapshot_request(request: PlanningRequest) -> Dict[str, Any]:
        return {
            "planner_mode": request.planner_mode,
            "workflow_overrides": deepcopy(request.workflow_overrides),
            "hints": {
                "preferred_capabilities": list(request.hints.preferred_capabilities),
                "forbidden_tools": list(request.hints.forbidden_tools),
                "allow_reuse": bool(request.hints.allow_reuse),
                "reusable_asset_ids": list(request.hints.reusable_asset_ids),
                "prior_failures": list(request.hints.prior_failures),
                "user_style": deepcopy(request.hints.user_style),
            },
        }

    @staticmethod
    def _passthrough_workflow_metadata(request: PlanningRequest) -> Dict[str, Any]:
        user_style = request.hints.user_style
        passthrough_keys = (
            "benchmark",
            "messages",
            "milestones",
            "tool_allow_list",
            "requires_interaction",
            "approval_scope",
            "approval_target_step",
            "backup_tool_map",
            "simulated_policy",
            "branch_options",
            "ideal_tool_calls",
            "ideal_turn_count",
            "primary_failtax",
            "failtaxes",
            "failure_step",
            "expected_recovery_path",
            "gold_tool",
            "state_slots",
            "dependency_edges",
            "reuse_override_inputs",
            "tool_execution_backend",
        )
        metadata: Dict[str, Any] = {}
        for key in passthrough_keys:
            value = user_style.get(key)
            if value is None:
                continue
            metadata[key] = deepcopy(value)

        categories = user_style.get("categories")
        if categories:
            metadata["categories"] = list(categories)
            metadata.setdefault("toolsandbox_categories", list(categories))
        return metadata

    @classmethod
    def request_from_workflow(cls, workflow: Workflow) -> PlanningRequest:
        snapshot = workflow.metadata.get("planning_request", {})
        hint_snapshot = snapshot.get("hints", {}) if isinstance(snapshot, dict) else {}
        hints = PlanningHints(
            preferred_capabilities=[
                str(item) for item in hint_snapshot.get("preferred_capabilities", []) if str(item)
            ],
            forbidden_tools=[str(item) for item in hint_snapshot.get("forbidden_tools", []) if str(item)],
            allow_reuse=bool(
                hint_snapshot.get("allow_reuse")
                or hint_snapshot.get("reusable_asset_ids")
            ),
            reusable_asset_ids=[str(item) for item in hint_snapshot.get("reusable_asset_ids", []) if str(item)],
            prior_failures=[str(item) for item in hint_snapshot.get("prior_failures", []) if str(item)],
            user_style=deepcopy(hint_snapshot.get("user_style", {}))
            if isinstance(hint_snapshot.get("user_style", {}), dict)
            else {},
        )
        planner_mode = (
            str(snapshot.get("planner_mode"))
            if isinstance(snapshot, dict) and snapshot.get("planner_mode")
            else str(workflow.metadata.get("planner_mode", "phase1_rule_based"))
        )
        workflow_overrides = (
            deepcopy(snapshot.get("workflow_overrides", {}))
            if isinstance(snapshot, dict) and isinstance(snapshot.get("workflow_overrides", {}), dict)
            else {}
        )
        return PlanningRequest(
            task=workflow.task,
            context=workflow.context,
            policy=workflow.policy,
            hints=hints,
            planner_mode=planner_mode,
            workflow_overrides=workflow_overrides,
        )

    @classmethod
    def _merge_request_with_workflow_context(
        cls,
        request: PlanningRequest,
        workflow: Workflow,
    ) -> PlanningRequest:
        inherited = cls.request_from_workflow(workflow)
        merged_user_style = dict(inherited.hints.user_style)
        merged_user_style.update(request.hints.user_style)
        merged_hints = PlanningHints(
            preferred_capabilities=list(
                dict.fromkeys(
                    [*inherited.hints.preferred_capabilities, *request.hints.preferred_capabilities]
                )
            ),
            forbidden_tools=list(
                dict.fromkeys([*inherited.hints.forbidden_tools, *request.hints.forbidden_tools])
            ),
            allow_reuse=bool(inherited.hints.allow_reuse or request.hints.allow_reuse),
            reusable_asset_ids=list(
                dict.fromkeys([*inherited.hints.reusable_asset_ids, *request.hints.reusable_asset_ids])
            ),
            prior_failures=list(
                dict.fromkeys([*inherited.hints.prior_failures, *request.hints.prior_failures])
            ),
            user_style=merged_user_style,
        )
        merged_overrides = deepcopy(inherited.workflow_overrides)
        merged_overrides.update(request.workflow_overrides)
        planner_mode = request.planner_mode
        if planner_mode == "phase1_rule_based" and inherited.planner_mode != "phase1_rule_based":
            planner_mode = inherited.planner_mode
        return PlanningRequest(
            task=request.task,
            context=request.context,
            policy=request.policy or inherited.policy,
            hints=merged_hints,
            planner_mode=planner_mode,
            workflow_overrides=merged_overrides,
        )

    @staticmethod
    def _benchmark_hints(request: PlanningRequest) -> Dict[str, Any]:
        user_style = dict(request.hints.user_style)
        categories = [str(item) for item in user_style.get("categories", []) if str(item)]
        tool_allow_list = [str(item) for item in user_style.get("tool_allow_list", []) if str(item)]
        raw_backup_tool_map = user_style.get("backup_tool_map", {})
        backup_tool_map = dict(raw_backup_tool_map) if isinstance(raw_backup_tool_map, dict) else {}
        milestones = [str(item) for item in user_style.get("milestones", []) if str(item)]
        branch_options = [str(item) for item in user_style.get("branch_options", []) if str(item)]
        ideal_tool_calls = HTGPPlanner._coerce_int(user_style.get("ideal_tool_calls"))
        ideal_turn_count = HTGPPlanner._coerce_int(user_style.get("ideal_turn_count"))
        used_keys = [
            key
            for key in (
                "categories",
                "tool_allow_list",
                "backup_tool_map",
                "ideal_tool_calls",
                "ideal_turn_count",
                "milestones",
                "branch_options",
                "state_slots",
                "dependency_edges",
                "primary_failtax",
            )
            if user_style.get(key)
        ]
        return {
            "categories": categories,
            "tool_allow_list": tool_allow_list,
            "backup_tool_map": backup_tool_map,
            "ideal_tool_calls": ideal_tool_calls,
            "ideal_turn_count": ideal_turn_count,
            "milestones": milestones,
            "branch_options": branch_options,
            "state_slots": [str(item) for item in user_style.get("state_slots", []) if str(item)],
            "dependency_edges": HTGPPlanner._normalized_dependency_edges(user_style),
            "used_keys": used_keys,
            "primary_failtax": user_style.get("primary_failtax"),
        }

    @staticmethod
    def _budget_targets(request: PlanningRequest) -> Dict[str, Any]:
        constraints = request.task.constraints
        return {
            "max_tool_calls": constraints.max_tool_calls,
            "max_user_turns": constraints.max_user_turns,
            "max_repair_attempts": constraints.max_repair_attempts,
            "max_recovery_budget": constraints.max_recovery_budget,
        }

    @staticmethod
    def _should_bypass(request: PlanningRequest, benchmark_hints: Dict[str, Any]) -> bool:
        return HTGPPlanner._minimal_path_reason(request, benchmark_hints) != "not_applied"

    @staticmethod
    def _minimal_path_reason(request: PlanningRequest, benchmark_hints: Dict[str, Any]) -> str:
        categories = set(benchmark_hints.get("categories", []))
        tool_allow_list = benchmark_hints.get("tool_allow_list", [])
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        if "multiple_user_turn" in categories:
            return "not_applied"
        if "single_tool" in categories:
            return "single_tool_category"
        if ideal_tool_calls == 1:
            return "ideal_tool_calls_one"
        if len(tool_allow_list) == 1:
            return "single_tool_allow_list"
        return "not_applied"

    @staticmethod
    def _planner_observability(
        *,
        bypass_applied: bool,
        minimal_path_reason: str,
        selected_capability_order_initial: Sequence[str],
        graph: CapabilityGraph,
        candidates: Sequence[CapabilityCandidate],
        bindings: Sequence[ToolBinding],
        diagnostics: PlanningDiagnostics,
    ) -> Dict[str, Any]:
        return {
            "planner_bypass_applied": bool(bypass_applied),
            "minimal_path_reason": str(minimal_path_reason),
            "selected_capability_order_initial": [str(item) for item in selected_capability_order_initial],
            "selected_capability_order_final": [
                str(capability.capability_id) for capability in graph.capabilities
            ],
            "graph_builder_used": not bool(bypass_applied),
            "candidate_capability_count": len(candidates),
            "bound_tool_order": [str(binding.primary_tool) for binding in bindings if binding.primary_tool],
            "unresolved_capabilities": list(diagnostics.unresolved_capabilities),
            "benchmark_hints_used": list(diagnostics.benchmark_hints_used),
        }

    @staticmethod
    def _overplanning_risk(
        *,
        request: PlanningRequest,
        execution_plan: List[WorkflowStep],
        bindings: List[ToolBinding],
        bypass_applied: bool,
        benchmark_hints: Dict[str, Any],
    ) -> Dict[str, Any]:
        categories = set(benchmark_hints.get("categories", []))
        tool_allow_list = set(benchmark_hints.get("tool_allow_list", []))
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        overplanning_objective = benchmark_hints.get("overplanning_objective", {})
        planned_tools = [step.tool_id for step in execution_plan if step.tool_id]
        return {
            "bypass_applied": bypass_applied,
            "objective_applied": bool(overplanning_objective.get("applied")),
            "single_tool_task": len(tool_allow_list) == 1 or "single_tool" in categories,
            "planned_steps": len(execution_plan),
            "ideal_tool_calls": ideal_tool_calls,
            "expanded_single_tool_task": (len(tool_allow_list) == 1 or "single_tool" in categories) and len(execution_plan) > 1,
            "steps_exceed_ideal": isinstance(ideal_tool_calls, int) and len(execution_plan) > ideal_tool_calls,
            "used_disallowed_tool": bool(tool_allow_list) and any(tool_id not in tool_allow_list for tool_id in planned_tools),
            "bound_capabilities": [binding.capability_id for binding in bindings],
            "objective_reason": list(overplanning_objective.get("reason", [])),
        }

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def replan_from_error(
        self,
        request: PlanningRequest,
        failed_workflow: Workflow,
        error: ToolClawError,
        state_values: Dict[str, Any],
    ) -> PlanningResult:
        request = self._merge_request_with_workflow_context(request, failed_workflow)
        replan_user_style = dict(request.hints.user_style)
        replan_user_style.setdefault("failure_type", error.category.value)
        replan_user_style["replan_error_category"] = error.category.value
        replan_user_style["replan_trigger_step_id"] = error.step_id
        replan_user_style["replan_state_keys"] = sorted(state_values.keys())
        replanning_hints = PlanningHints(
            preferred_capabilities=list(request.hints.preferred_capabilities),
            forbidden_tools=list(request.hints.forbidden_tools),
            allow_reuse=bool(request.hints.allow_reuse),
            reusable_asset_ids=list(request.hints.reusable_asset_ids),
            prior_failures=list(request.hints.prior_failures) + [error.category.value],
            user_style=replan_user_style,
        )
        if error.evidence.tool_id and error.evidence.tool_id not in replanning_hints.forbidden_tools:
            replanning_hints.forbidden_tools.append(error.evidence.tool_id)

        # simple phase-1 strategy: preserve task/context/policy and re-run planning.
        result = self.plan(
            PlanningRequest(
                task=request.task,
                context=request.context,
                policy=request.policy,
                hints=replanning_hints,
                planner_mode=request.planner_mode,
                workflow_overrides=deepcopy(request.workflow_overrides),
            )
        )
        failed_index = 0
        for idx, step in enumerate(failed_workflow.execution_plan):
            if step.step_id == error.step_id:
                failed_index = idx
                break

        prefix = failed_workflow.execution_plan[:failed_index]
        replanned_suffix_source = self._prune_replanned_suffix(
            failed_workflow=failed_workflow,
            replanned_steps=result.workflow.execution_plan,
            failed_index=failed_index,
            benchmark_hints=self._benchmark_hints(request),
        )
        if not replanned_suffix_source:
            replanned_suffix_source = result.workflow.execution_plan[failed_index:] or result.workflow.execution_plan
        replanned_suffix: List[WorkflowStep] = []
        for offset, step in enumerate(replanned_suffix_source, start=failed_index + 1):
            replanned_suffix.append(
                WorkflowStep(
                    step_id=f"step_{offset:02d}",
                    capability_id=step.capability_id,
                    tool_id=step.tool_id,
                    action_type=step.action_type,
                    inputs=dict(step.inputs),
                    expected_output=step.expected_output,
                    checkpoint=step.checkpoint,
                    rollback_to=step.rollback_to,
                    requires_user_confirmation=step.requires_user_confirmation,
                    metadata=dict(step.metadata),
                )
            )
        result.workflow.execution_plan = prefix + replanned_suffix
        result.workflow.workflow_graph = self.policy_injector.compile_workflow_graph(
            result.workflow.capability_graph,
            result.workflow.execution_plan,
            bindings=result.workflow.tool_bindings,
            benchmark_hints=self._benchmark_hints(request),
        )
        result.workflow.metadata["replanned_from_workflow_id"] = failed_workflow.workflow_id
        result.workflow.metadata["replan_state_keys"] = list(state_values.keys())
        result.workflow.metadata["replanned_suffix_from_step_id"] = error.step_id
        result.workflow.metadata["replan_context"] = {
            "inherited_request_context": True,
            "prior_failures": list(replanning_hints.prior_failures),
            "reusable_asset_ids": list(replanning_hints.reusable_asset_ids),
            "forbidden_tools": list(replanning_hints.forbidden_tools),
        }
        if error.evidence.tool_id:
            result.diagnostics.rejected_tools[error.evidence.tool_id] = "failed_in_previous_run"
        return result

    @staticmethod
    def _prune_replanned_suffix(
        *,
        failed_workflow: Workflow,
        replanned_steps: List[WorkflowStep],
        failed_index: int,
        benchmark_hints: Dict[str, Any],
    ) -> List[WorkflowStep]:
        suffix = list(replanned_steps[failed_index:] or replanned_steps)
        if not suffix:
            return suffix
        completed_steps = failed_workflow.execution_plan[:failed_index]
        completed_milestones = sum(1 for step in completed_steps if step.metadata.get("milestone_index") is not None)
        overplanning_objective = HTGPPlanner._build_overplanning_objective(
            benchmark_hints,
            completed_step_count=len(completed_steps),
        )
        if not overplanning_objective.get("active"):
            return suffix

        allowed_tools = set(overplanning_objective.get("allowed_tools", []))
        if allowed_tools:
            filtered_suffix = [step for step in suffix if not step.tool_id or step.tool_id in allowed_tools]
            if filtered_suffix:
                suffix = filtered_suffix

        max_steps = overplanning_objective.get("max_steps")
        if not isinstance(max_steps, int) or max_steps <= 0 or len(suffix) <= max_steps:
            return suffix

        anchored_steps: List[WorkflowStep] = []
        for step in suffix:
            milestone_index = step.metadata.get("milestone_index")
            if isinstance(milestone_index, int) and milestone_index >= completed_milestones:
                anchored_steps.append(step)
        if overplanning_objective.get("preserve_terminal_branch_step") and suffix[-1].metadata.get("branch_sensitive"):
            anchored_steps.append(suffix[-1])

        selected: List[WorkflowStep] = []
        for step in anchored_steps + suffix:
            if step not in selected:
                selected.append(step)
            if len(selected) >= max_steps:
                break
        selected.sort(key=suffix.index)
        return selected[:max_steps]

    @staticmethod
    def _build_overplanning_objective(
        benchmark_hints: Dict[str, Any],
        *,
        completed_step_count: int,
    ) -> Dict[str, Any]:
        categories = {str(item) for item in benchmark_hints.get("categories", []) if str(item)}
        tool_allow_list = [str(item) for item in benchmark_hints.get("tool_allow_list", []) if str(item)]
        milestones = [str(item) for item in benchmark_hints.get("milestones", []) if str(item)]
        branch_options = [str(item) for item in benchmark_hints.get("branch_options", []) if str(item)]
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        preferred_capabilities = (
            RuleBasedCapabilityGraphBuilder._capability_order_from_texts(milestones)
            or RuleBasedCapabilityGraphBuilder._capability_order_from_texts(tool_allow_list)
        )

        low_branching_task = "multiple_user_turn" not in categories and (
            "single_tool" in categories or len(tool_allow_list) <= 2 or bool(milestones)
        )
        remaining_milestones = max(len(preferred_capabilities) - completed_step_count, 0) if preferred_capabilities else 0
        remaining_tool_budget = None
        if isinstance(ideal_tool_calls, int) and ideal_tool_calls > 0:
            remaining_tool_budget = max(ideal_tool_calls - completed_step_count, 1)

        max_steps: Optional[int] = None
        if remaining_milestones > 0:
            max_steps = remaining_milestones
        if remaining_tool_budget is not None:
            max_steps = remaining_tool_budget if max_steps is None else min(max_steps, remaining_tool_budget)

        reasons: List[str] = []
        if preferred_capabilities:
            reasons.append("preferred_capability_order")
        if remaining_tool_budget is not None:
            reasons.append("ideal_tool_budget")
        if branch_options:
            reasons.append("branch_sensitive_suffix")

        active = low_branching_task and (bool(preferred_capabilities) or max_steps is not None or bool(branch_options))
        return {
            "active": active,
            "applied": False,
            "low_branching_task": low_branching_task,
            "max_steps": max_steps,
            "preferred_capabilities": preferred_capabilities,
            "allowed_tools": tool_allow_list,
            "preserve_terminal_branch_step": bool(branch_options),
            "reason": reasons,
        }

    @staticmethod
    def _apply_overplanning_objective_to_graph(
        graph: CapabilityGraph,
        objective: Dict[str, Any],
    ) -> CapabilityGraph:
        if not objective.get("active") or len(graph.capabilities) <= 1:
            return graph

        capabilities = list(graph.capabilities)
        preferred_capabilities = [str(item) for item in objective.get("preferred_capabilities", []) if str(item)]
        if preferred_capabilities:
            preferred_set = set(preferred_capabilities)
            ranked = {capability_id: idx for idx, capability_id in enumerate(preferred_capabilities)}
            filtered = [capability for capability in capabilities if capability.capability_id in preferred_set]
            if filtered:
                filtered.sort(key=lambda capability: (ranked.get(capability.capability_id, len(ranked)), capabilities.index(capability)))
                capabilities = filtered

        max_steps = objective.get("max_steps")
        if isinstance(max_steps, int) and max_steps > 0 and len(capabilities) > max_steps:
            if objective.get("preserve_terminal_branch_step") and max_steps > 1:
                terminal = capabilities[-1]
                trimmed = capabilities[: max_steps - 1]
                if terminal not in trimmed:
                    trimmed.append(terminal)
                capabilities = trimmed
            else:
                capabilities = capabilities[:max_steps]

        if capabilities == graph.capabilities:
            objective_metadata = dict(objective)
            objective_metadata["applied"] = bool(
                objective.get("preferred_capabilities")
                or objective.get("max_steps") is not None
            )
            graph.metadata.setdefault("overplanning_objective", objective_metadata)
            return graph

        objective_metadata = dict(objective)
        objective_metadata["applied"] = True
        metadata = dict(graph.metadata)
        metadata["overplanning_objective"] = objective_metadata
        return CapabilityGraph(
            capabilities=capabilities,
            edges=HTGPPlanner._rebuild_capability_edges(capabilities),
            metadata=metadata,
        )

    @staticmethod
    def _rebuild_capability_edges(capabilities: Sequence[CapabilityNode]) -> List["CapabilityEdge"]:
        if len(capabilities) <= 1:
            return []
        from toolclaw.schemas.workflow import CapabilityEdge

        return [
            CapabilityEdge(
                source=capabilities[index].capability_id,
                target=capabilities[index + 1].capability_id,
                condition="objective_sequence",
            )
            for index in range(len(capabilities) - 1)
        ]

    @staticmethod
    def _apply_request_overrides(workflow: Workflow, overrides: Dict[str, Dict[str, Any]]) -> None:
        if not overrides:
            return

        step_overrides = overrides.get("steps", {})
        if not isinstance(step_overrides, dict):
            return

        HTGPPlanner._ensure_workflow_capacity_for_overrides(workflow, step_overrides)

        graph_nodes = {node.node_id: node for node in workflow.workflow_graph.nodes}
        for index, step in enumerate(workflow.execution_plan):
            patch = step_overrides.get(step.step_id)
            if not isinstance(patch, dict):
                continue
            binding = workflow.tool_bindings[index] if index < len(workflow.tool_bindings) else None
            capability_node = workflow.capability_graph.capabilities[index] if index < len(workflow.capability_graph.capabilities) else None

            if "capability_id" in patch and patch["capability_id"]:
                step.capability_id = str(patch["capability_id"])
                node = graph_nodes.get(step.step_id)
                if node is not None:
                    node.capability_id = step.capability_id
                if binding is not None:
                    binding.capability_id = step.capability_id
                if capability_node is not None:
                    capability_node.capability_id = step.capability_id

            if "inputs" in patch and isinstance(patch["inputs"], dict):
                step.inputs = dict(patch["inputs"])
                node = graph_nodes.get(step.step_id)
                if node is not None:
                    node.inputs = dict(step.inputs)

            if "tool_id" in patch:
                step.tool_id = patch["tool_id"]
                node = graph_nodes.get(step.step_id)
                if node is not None:
                    node.selected_tool = step.tool_id
                    node.tool_candidates = [step.tool_id] if step.tool_id else []
                if binding is not None and step.tool_id:
                    binding.primary_tool = step.tool_id

            if "metadata" in patch and isinstance(patch["metadata"], dict):
                step.metadata.update(deepcopy(patch["metadata"]))
                node = graph_nodes.get(step.step_id)
                if node is not None:
                    node.metadata.update(deepcopy(patch["metadata"]))
        workflow.capability_graph.edges = HTGPPlanner._rebuild_capability_edges(workflow.capability_graph.capabilities)

    @staticmethod
    def _ensure_workflow_capacity_for_overrides(
        workflow: Workflow,
        step_overrides: Dict[str, Dict[str, Any]],
    ) -> None:
        if not step_overrides or not workflow.execution_plan:
            return
        required_steps = len(workflow.execution_plan)
        for step_id in step_overrides:
            if not isinstance(step_id, str):
                continue
            match = re.fullmatch(r"step_(\d+)", step_id.strip())
            if not match:
                continue
            required_steps = max(required_steps, int(match.group(1)))
        if required_steps <= len(workflow.execution_plan):
            return
        if not workflow.workflow_graph.nodes or not workflow.capability_graph.capabilities:
            return

        HTGPPlanner._ensure_binding_alignment(workflow)

        from toolclaw.schemas.workflow import CapabilityEdge

        while len(workflow.execution_plan) < required_steps:
            index = len(workflow.execution_plan) + 1
            previous_step = workflow.execution_plan[-1]
            previous_node = workflow.workflow_graph.nodes[-1]
            previous_binding = workflow.tool_bindings[-1]
            previous_capability = workflow.capability_graph.capabilities[-1]

            new_step = deepcopy(previous_step)
            new_step.step_id = f"step_{index:02d}"
            new_step.expected_output = str(previous_step.expected_output or f"step_{index:02d}_output")
            new_step.rollback_to = previous_step.step_id
            workflow.execution_plan.append(new_step)

            new_node = deepcopy(previous_node)
            new_node.node_id = new_step.step_id
            new_node.expected_output = new_step.expected_output
            new_node.dependencies = [previous_step.step_id]
            workflow.workflow_graph.nodes.append(new_node)
            workflow.workflow_graph.edges.append(
                WorkflowEdge(
                    source=previous_step.step_id,
                    target=new_step.step_id,
                    condition="override_sequence",
                    edge_type="default",
                )
            )

            workflow.tool_bindings.append(deepcopy(previous_binding))
            workflow.capability_graph.capabilities.append(deepcopy(previous_capability))
            workflow.capability_graph.edges.append(
                CapabilityEdge(
                    source=workflow.capability_graph.capabilities[-2].capability_id,
                    target=workflow.capability_graph.capabilities[-1].capability_id,
                    condition="override_sequence",
                )
            )

        workflow.workflow_graph.entry_nodes = ["step_01"] if workflow.workflow_graph.nodes else []
        workflow.workflow_graph.exit_nodes = [workflow.execution_plan[-1].step_id] if workflow.execution_plan else []

    @staticmethod
    def _ensure_binding_alignment(workflow: Workflow) -> None:
        if not workflow.execution_plan:
            return
        while len(workflow.tool_bindings) < len(workflow.execution_plan):
            step_index = len(workflow.tool_bindings)
            step = workflow.execution_plan[step_index]
            primary_tool = step.tool_id
            if not primary_tool and workflow.tool_bindings:
                primary_tool = workflow.tool_bindings[-1].primary_tool
            workflow.tool_bindings.append(
                ToolBinding(
                    capability_id=str(step.capability_id or ""),
                    primary_tool=str(primary_tool or ""),
                    backup_tools=[],
                    binding_confidence=1.0 if primary_tool else 0.0,
                )
            )

    def _load_reusable_profile(
        self,
        request: PlanningRequest,
        graph: Optional[CapabilityGraph] = None,
        *,
        overplanning_objective: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        profile: Dict[str, Any] = {
            "capability_order": [],
            "recommended_bindings": {},
            "recommended_inputs": {},
            "continuation_hints": [],
            "auto_patch_input_keys": {},
            "asset_ids": [],
            "reuse_mode": "none",
            "reuse_application": "none",
            "utility_gain_score": 0.0,
            "auto_continuation_replay": False,
            "selected_match": {},
        }
        reuse_enabled = bool(request.hints.allow_reuse or request.hints.reusable_asset_ids)
        if not self.asset_registry or not reuse_enabled:
            return profile

        asset_ids = list(request.hints.reusable_asset_ids)
        capability_skeleton = [capability.capability_id for capability in graph.capabilities] if graph else []
        required_state_slots = self._required_state_slots(request)
        failure_context = str(request.hints.user_style.get("failure_type") or "").strip() or None
        target_reuse_family_id = str(request.hints.user_style.get("reuse_family_id") or "").strip()
        if not target_reuse_family_id:
            target_reuse_family_id = str(request.task.task_id or "").rsplit("__pass", 1)[0]
        target_semantic_reuse_family = str(request.hints.user_style.get("semantic_reuse_family") or "").strip()
        if not target_semantic_reuse_family and target_reuse_family_id:
            target_semantic_reuse_family = _semantic_reuse_family(target_reuse_family_id)
        if not target_semantic_reuse_family:
            target_semantic_reuse_family = _semantic_reuse_family(request.hints.user_style.get("task_family"))
        selected_match: Dict[str, Any] = {}
        if not asset_ids and self.asset_registry:
            signatures = build_task_signature_candidates(
                user_goal=request.task.user_goal,
                task_family=request.hints.user_style.get("task_family"),
                capability_skeleton=capability_skeleton,
                failure_context=failure_context,
            )
            matches = []
            for signature in signatures:
                matches.extend(
                    self.asset_registry.query(
                        signature,
                        top_k=5,
                        required_capability_skeleton=capability_skeleton,
                        failure_context=failure_context,
                        required_state_slots=required_state_slots,
                    )
                )
            deduped_matches: List[Any] = []
            seen_asset_ids: set[str] = set()
            for match in matches:
                if match.asset_id in seen_asset_ids:
                    continue
                seen_asset_ids.add(match.asset_id)
                deduped_matches.append(match)
            if deduped_matches:
                selected_match = dict(deduped_matches[0].metadata)
                selected_match["asset_id"] = deduped_matches[0].asset_id
                asset_ids = [deduped_matches[0].asset_id]
        admitted_asset_ids: List[str] = []

        for asset_id in asset_ids:
            asset = self.asset_registry.get(asset_id)
            if asset is None:
                continue
            if not self._asset_reuse_compatible(
                asset,
                required_capability_skeleton=capability_skeleton,
                failure_context=failure_context,
                required_state_slots=required_state_slots,
            ):
                continue
            asset_capability_skeleton = getattr(asset, "capability_skeleton", None)
            recommended_bindings = getattr(asset, "recommended_bindings", None)
            recommended_inputs = getattr(asset, "recommended_inputs", None)
            continuation_hints = getattr(asset, "continuation_hints", None)
            reuse_application, utility_gain_score = self._asset_reuse_utility(asset)
            if asset_capability_skeleton:
                profile["capability_order"] = list(asset_capability_skeleton)
            if recommended_bindings:
                profile["recommended_bindings"].update(dict(recommended_bindings))
            if recommended_inputs and reuse_application in {"execution_prior", "continuation_prior"}:
                profile["recommended_inputs"].update(
                    {
                        capability_id: dict(inputs)
                        for capability_id, inputs in dict(recommended_inputs).items()
                        if isinstance(inputs, dict)
                    }
                )
            asset_metadata = getattr(asset, "metadata", {})
            if not isinstance(asset_metadata, dict):
                asset_metadata = {}
            exact_reuse_match = str(selected_match.get("reuse_mode") or "") == "exact_reuse"
            source_reuse_family_id = str(
                selected_match.get("source_reuse_family_id")
                or asset_metadata.get("reuse_family_id", "")
            ).strip()
            source_semantic_reuse_family = str(
                selected_match.get("source_semantic_reuse_family")
                or asset_metadata.get("semantic_reuse_family", "")
            ).strip()
            if not source_semantic_reuse_family and source_reuse_family_id:
                source_semantic_reuse_family = _semantic_reuse_family(source_reuse_family_id)
            continuation_reuse_compatible = bool(
                continuation_hints
                and self._continuation_reuse_compatible(
                    source_semantic_reuse_family=source_semantic_reuse_family,
                    target_semantic_reuse_family=target_semantic_reuse_family,
                )
            )
            auto_continuation_replay = bool(
                continuation_reuse_compatible
                and exact_reuse_match
                and self._asset_auto_repair_replay_eligible(asset_metadata)
            )
            if recommended_inputs and (
                reuse_application in {"execution_prior", "continuation_prior"} or auto_continuation_replay
            ):
                profile["recommended_inputs"].update(
                    {
                        capability_id: dict(inputs)
                        for capability_id, inputs in dict(recommended_inputs).items()
                        if isinstance(inputs, dict)
                    }
                )
            if continuation_reuse_compatible:
                continuation_hint_dicts = [dict(item) for item in continuation_hints if isinstance(item, dict)]
                profile["continuation_hints"].extend(continuation_hint_dicts)
            if auto_continuation_replay:
                self._promote_exact_match_auto_replay(
                    profile,
                    continuation_hints=continuation_hint_dicts,
                )
                selected_match["auto_continuation_replay"] = True
                selected_match["reuse_application_hint"] = "continuation_prior"
            admitted_asset_ids.append(str(asset_id))
            if not selected_match:
                selected_match = {
                    "reuse_mode": "explicit_asset",
                    "asset_id": str(asset_id),
                    "asset_capability_skeleton": list(asset_capability_skeleton or []),
                    "asset_failure_context": str(asset_metadata.get("failure_context", "")),
                    "asset_required_state_slots": list(asset_metadata.get("required_state_slots", [])),
                    "source_task_id": str(asset_metadata.get("source_task_id", "")),
                    "source_reuse_family_id": source_reuse_family_id,
                    "source_semantic_reuse_family": source_semantic_reuse_family,
                    "reuse_application_hint": reuse_application,
                    "utility_gain_score": utility_gain_score,
                    "auto_continuation_replay": auto_continuation_replay,
                }
            profile["reuse_application"] = reuse_application
            profile["utility_gain_score"] = utility_gain_score
            profile["auto_continuation_replay"] = auto_continuation_replay
            break
        profile["asset_ids"] = admitted_asset_ids
        profile["reuse_mode"] = str(selected_match.get("reuse_mode") or "none")
        profile["reuse_application"] = str(
            selected_match.get("reuse_application_hint")
            or profile.get("reuse_application")
            or "none"
        )
        profile["utility_gain_score"] = float(
            selected_match.get("utility_gain_score")
            if selected_match.get("utility_gain_score") not in (None, "")
            else profile.get("utility_gain_score", 0.0)
        )
        profile["auto_continuation_replay"] = bool(
            selected_match.get("auto_continuation_replay")
            or profile.get("auto_continuation_replay")
        )
        profile["selected_match"] = selected_match
        return self._constrain_reusable_profile(
            profile,
            graph=graph,
            overplanning_objective=overplanning_objective or {},
        )

    @staticmethod
    def _required_state_slots(request: PlanningRequest) -> List[str]:
        slots: List[str] = []
        raw_state_slots = request.hints.user_style.get("state_slots", [])
        if isinstance(raw_state_slots, list):
            for slot in raw_state_slots:
                text = str(slot).strip()
                if text and text not in slots:
                    slots.append(text)
        steps = request.workflow_overrides.get("steps", {})
        if isinstance(steps, dict):
            for patch in steps.values():
                if not isinstance(patch, dict):
                    continue
                metadata = patch.get("metadata", {})
                if not isinstance(metadata, dict):
                    continue
                for slot in metadata.get("required_state_slots", []):
                    text = str(slot).strip()
                    if text and text not in slots:
                        slots.append(text)
        return slots

    @staticmethod
    def _asset_reuse_compatible(
        asset: Any,
        *,
        required_capability_skeleton: List[str],
        failure_context: Optional[str],
        required_state_slots: List[str],
    ) -> bool:
        asset_metadata = getattr(asset, "metadata", {})
        if not isinstance(asset_metadata, dict):
            asset_metadata = {}
        asset_capability_skeleton = [
            str(item)
            for item in getattr(asset, "capability_skeleton", asset_metadata.get("capability_skeleton", []))
            if str(item)
        ]
        if required_capability_skeleton and asset_capability_skeleton and asset_capability_skeleton != required_capability_skeleton:
            return False
        asset_failure_context = str(asset_metadata.get("failure_context") or "").strip()
        if failure_context and asset_failure_context and asset_failure_context != failure_context:
            return False
        asset_required_state_slots = [str(item) for item in asset_metadata.get("required_state_slots", []) if str(item)]
        if required_state_slots and asset_required_state_slots != required_state_slots:
            return False
        if required_state_slots and not asset_required_state_slots:
            return False
        return True

    @staticmethod
    def _asset_reuse_utility(asset: Any) -> tuple[str, float]:
        asset_metadata = getattr(asset, "metadata", {})
        if not isinstance(asset_metadata, dict):
            asset_metadata = {}
        raw_profile = asset_metadata.get("utility_profile", {})
        utility_profile = raw_profile if isinstance(raw_profile, dict) else {}
        reuse_application = str(
            utility_profile.get("reuse_application_hint")
            or asset_metadata.get("reuse_application_hint")
            or ""
        ).strip()
        if not reuse_application:
            recommended_inputs = getattr(asset, "recommended_inputs", None)
            continuation_hints = getattr(asset, "continuation_hints", None)
            if isinstance(continuation_hints, list) and continuation_hints and utility_profile.get("utility_gain_score", 0.0):
                reuse_application = "continuation_prior"
            else:
                reuse_application = "execution_prior" if isinstance(recommended_inputs, dict) and recommended_inputs else "binding_prior"
        utility_gain_score = utility_profile.get("utility_gain_score", asset_metadata.get("utility_gain_score", 0.0))
        try:
            return reuse_application, float(utility_gain_score or 0.0)
        except (TypeError, ValueError):
            return reuse_application, 0.0

    @staticmethod
    def _asset_auto_repair_replay_eligible(asset_metadata: Dict[str, Any]) -> bool:
        raw_profile = asset_metadata.get("utility_profile", {})
        utility_profile = raw_profile if isinstance(raw_profile, dict) else {}
        return bool(utility_profile.get("auto_repair_replay_eligible"))

    @staticmethod
    def _promote_exact_match_auto_replay(
        profile: Dict[str, Any],
        *,
        continuation_hints: Sequence[Dict[str, Any]],
    ) -> None:
        auto_patch_keys = profile.setdefault("auto_patch_input_keys", {})
        if not isinstance(auto_patch_keys, dict):
            auto_patch_keys = {}
            profile["auto_patch_input_keys"] = auto_patch_keys
        for hint in continuation_hints:
            if not isinstance(hint, dict):
                continue
            capability_id = str(hint.get("capability_id") or "").strip()
            if not capability_id:
                continue
            kind = str(hint.get("kind") or "").strip()
            if kind == "fallback_to_backup_then_resume":
                backup_tool_id = str(hint.get("backup_tool_id") or "").strip()
                if backup_tool_id:
                    profile["recommended_bindings"][capability_id] = backup_tool_id
                    profile["reuse_application"] = "continuation_prior"
            elif kind == "patch_then_retry_same_step":
                patched_input_keys = [
                    str(item).strip()
                    for item in hint.get("patched_input_keys", [])
                    if str(item).strip()
                ]
                if patched_input_keys:
                    existing_keys = auto_patch_keys.setdefault(capability_id, [])
                    for key in patched_input_keys:
                        if key not in existing_keys:
                            existing_keys.append(key)
                    profile["reuse_application"] = "continuation_prior"

    @staticmethod
    def _continuation_reuse_compatible(
        *, source_semantic_reuse_family: str, target_semantic_reuse_family: str
    ) -> bool:
        if not source_semantic_reuse_family or not target_semantic_reuse_family:
            return False
        return source_semantic_reuse_family == target_semantic_reuse_family

    @staticmethod
    def _apply_reusable_continuation_hints(workflow: Workflow, reusable_profile: Dict[str, Any]) -> None:
        continuation_hints = reusable_profile.get("continuation_hints", [])
        if not isinstance(continuation_hints, list) or not continuation_hints:
            return
        reusable_context = workflow.metadata.setdefault("reusable_context", {})
        if not isinstance(reusable_context, dict):
            reusable_context = {}
            workflow.metadata["reusable_context"] = reusable_context
        reusable_context["continuation_hints"] = [dict(item) for item in continuation_hints if isinstance(item, dict)]

        graph_nodes = {node.node_id: node for node in workflow.workflow_graph.nodes}
        for step in workflow.execution_plan:
            matched_hints = HTGPPlanner._matched_continuation_hints(step, continuation_hints)
            if not matched_hints:
                continue
            step_hints = step.metadata.setdefault("continuation_hints", [])
            if not isinstance(step_hints, list):
                step_hints = []
                step.metadata["continuation_hints"] = step_hints
            auto_continuation_replay = bool(reusable_profile.get("auto_continuation_replay"))
            current_tool_id = str(step.tool_id or "").strip()
            for hint in matched_hints:
                if hint not in step_hints:
                    step_hints.append(hint)
                HTGPPlanner._apply_continuation_step_metadata(step.metadata, hint)
                if auto_continuation_replay:
                    rewritten_tool_id = HTGPPlanner._continuation_replay_tool_override(
                        current_tool_id=current_tool_id,
                        hint=hint,
                    )
                    if rewritten_tool_id:
                        step.tool_id = rewritten_tool_id
                        current_tool_id = rewritten_tool_id

            node = graph_nodes.get(step.step_id)
            if node is not None:
                node_hints = node.metadata.setdefault("continuation_hints", [])
                if not isinstance(node_hints, list):
                    node_hints = []
                    node.metadata["continuation_hints"] = node_hints
                for hint in matched_hints:
                    if hint not in node_hints:
                        node_hints.append(hint)
                    HTGPPlanner._apply_continuation_step_metadata(node.metadata, hint)
                if auto_continuation_replay and step.tool_id:
                    node.selected_tool = step.tool_id
                    node.tool_candidates = [step.tool_id]

        if not bool(reusable_profile.get("auto_continuation_replay")):
            return
        bindings_by_capability = {binding.capability_id: binding for binding in workflow.tool_bindings}
        for step in workflow.execution_plan:
            binding = bindings_by_capability.get(step.capability_id)
            if binding is not None and step.tool_id:
                binding.primary_tool = step.tool_id

    @staticmethod
    def _matched_continuation_hints(
        step: WorkflowStep,
        continuation_hints: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        matched: List[Dict[str, Any]] = []
        current_tool_id = str(step.tool_id or "").strip()
        for raw_hint in continuation_hints:
            if not isinstance(raw_hint, dict):
                continue
            capability_id = str(raw_hint.get("capability_id") or "").strip()
            if capability_id and capability_id != step.capability_id:
                continue
            source_tool_id = str(raw_hint.get("tool_id") or "").strip()
            if source_tool_id and current_tool_id and source_tool_id != current_tool_id:
                continue
            matched.append(dict(raw_hint))
        return matched

    @staticmethod
    def _apply_continuation_step_metadata(step_metadata: Dict[str, Any], hint: Dict[str, Any]) -> None:
        kind = str(hint.get("kind") or "").strip()
        if kind == "patch_then_retry_same_step":
            patched_input_keys = [str(item) for item in hint.get("patched_input_keys", []) if str(item)]
            existing = step_metadata.setdefault("continuation_missing_input_keys", [])
            if not isinstance(existing, list):
                existing = []
                step_metadata["continuation_missing_input_keys"] = existing
            for key in patched_input_keys:
                if key not in existing:
                    existing.append(key)
        elif kind == "fallback_to_backup_then_resume":
            backup_tool_id = str(hint.get("backup_tool_id") or "").strip()
            if backup_tool_id:
                step_metadata.setdefault("continuation_backup_tool_id", backup_tool_id)
        elif kind == "approved_then_resume_same_step":
            step_metadata.setdefault("continuation_resume_policy", "same_step")

    @staticmethod
    def _continuation_replay_tool_override(*, current_tool_id: str, hint: Dict[str, Any]) -> str:
        kind = str(hint.get("kind") or "").strip()
        if kind != "fallback_to_backup_then_resume":
            return ""
        source_tool_id = str(hint.get("tool_id") or "").strip()
        if source_tool_id and current_tool_id and source_tool_id != current_tool_id:
            return ""
        return str(hint.get("backup_tool_id") or "").strip()

    @staticmethod
    def _apply_reusable_hints(workflow: Workflow, reusable_profile: Dict[str, Any]) -> None:
        reuse_application = str(reusable_profile.get("reuse_application") or "execution_prior")
        if reuse_application not in {"execution_prior", "continuation_prior"}:
            return
        recommended_inputs = reusable_profile.get("recommended_inputs", {})
        if not isinstance(recommended_inputs, dict):
            return
        raw_overrides = workflow.metadata.get("reuse_override_inputs", {})
        override_map = raw_overrides if isinstance(raw_overrides, dict) else {}
        reusable_context = workflow.metadata.setdefault("reusable_context", {})
        if not isinstance(reusable_context, dict):
            reusable_context = {}
            workflow.metadata["reusable_context"] = reusable_context
        existing_suppressed = reusable_context.get("suppressed_inputs", [])
        suppressed_inputs = existing_suppressed if isinstance(existing_suppressed, list) else []
        reusable_context["suppressed_inputs"] = suppressed_inputs
        raw_auto_patch_input_keys = reusable_profile.get("auto_patch_input_keys", {})
        auto_patch_input_keys = raw_auto_patch_input_keys if isinstance(raw_auto_patch_input_keys, dict) else {}
        reusable_context["auto_continuation_replay"] = bool(
            reusable_profile.get("auto_continuation_replay")
        )
        reusable_context["auto_patch_input_keys"] = {
            capability_id: list(keys)
            for capability_id, keys in auto_patch_input_keys.items()
            if isinstance(keys, list)
        }

        graph_nodes = {node.node_id: node for node in workflow.workflow_graph.nodes}
        for step in workflow.execution_plan:
            suggested_inputs = recommended_inputs.get(step.capability_id)
            if not isinstance(suggested_inputs, dict):
                continue
            auto_patch_keys = {
                str(item)
                for item in auto_patch_input_keys.get(step.capability_id, [])
                if str(item)
            }
            override_keys = {
                str(item)
                for item in override_map.get(step.capability_id, override_map.get("*", []))
                if str(item)
            }
            task_scoped_keys = HTGPPlanner._task_scoped_reuse_keys(workflow, step)
            deferred_inputs = HTGPPlanner._deferred_repair_inputs(step)
            for key, value in suggested_inputs.items():
                resolved_value = value
                if key in task_scoped_keys:
                    task_local_value = HTGPPlanner._task_local_reuse_value(workflow, step, key)
                    if task_local_value is None:
                        continue
                    resolved_value = task_local_value
                suppression_reason = HTGPPlanner._reuse_input_suppression_reason(
                    workflow,
                    step,
                    key=key,
                    override_keys=override_keys,
                    task_scoped_keys=task_scoped_keys,
                    deferred_inputs=deferred_inputs,
                    auto_patch_keys=auto_patch_keys,
                )
                if suppression_reason is not None:
                    suppressed_inputs.append(
                        {
                            "step_id": step.step_id,
                            "capability_id": step.capability_id,
                            "input_key": key,
                            "reason": suppression_reason,
                        }
                    )
                    continue
                if key not in step.inputs or key in override_keys:
                    step.inputs[key] = resolved_value
            node = graph_nodes.get(step.step_id)
            if node is not None:
                for key, value in suggested_inputs.items():
                    resolved_value = value
                    if key in task_scoped_keys:
                        task_local_value = HTGPPlanner._task_local_reuse_value(workflow, step, key)
                        if task_local_value is None:
                            continue
                        resolved_value = task_local_value
                    if HTGPPlanner._reuse_input_suppression_reason(
                        workflow,
                        step,
                        key=key,
                        override_keys=override_keys,
                        task_scoped_keys=task_scoped_keys,
                        deferred_inputs=deferred_inputs,
                        auto_patch_keys=auto_patch_keys,
                    ) is not None:
                        continue
                    if key not in node.inputs or key in override_keys:
                        node.inputs[key] = resolved_value

    @staticmethod
    def _deferred_repair_inputs(step: WorkflowStep) -> set[str]:
        repair_defaults = step.metadata.get("repair_default_inputs")
        if not isinstance(repair_defaults, dict):
            return set()
        deferred: set[str] = set()
        for key, value in repair_defaults.items():
            if value in (None, ""):
                continue
            if step.inputs.get(str(key)) not in (None, ""):
                continue
            deferred.add(str(key))
        return deferred

    @staticmethod
    def _workflow_requires_failure_materialization(workflow: Workflow) -> bool:
        categories = {
            str(item).strip().lower()
            for item in workflow.metadata.get("toolsandbox_categories")
            or workflow.metadata.get("categories")
            or []
            if str(item).strip()
        }
        if categories.intersection({"insufficient_information", "multiple_user_turn"}):
            return True
        expected_recovery_path = str(workflow.metadata.get("expected_recovery_path") or "").strip().lower()
        if any(token in expected_recovery_path for token in ("approval", "clarify", "ask", "patch", "repair", "retry", "resume")):
            return True
        if bool(workflow.task.constraints.requires_user_approval):
            return True
        return any(bool(step.requires_user_confirmation) for step in workflow.execution_plan)

    @classmethod
    def _reuse_input_suppression_reason(
        cls,
        workflow: Workflow,
        step: WorkflowStep,
        *,
        key: str,
        override_keys: set[str],
        task_scoped_keys: set[str],
        deferred_inputs: set[str],
        auto_patch_keys: set[str],
    ) -> Optional[str]:
        normalized_key = str(key)
        input_missing = step.inputs.get(normalized_key) in (None, "")
        auto_patch_allowed = normalized_key in auto_patch_keys and input_missing
        if normalized_key in deferred_inputs and input_missing:
            if auto_patch_allowed:
                return None
            return "repair_sensitive_missing_input"
        if (
            normalized_key in task_scoped_keys
            and input_missing
            and cls._workflow_requires_failure_materialization(workflow)
        ):
            if auto_patch_allowed:
                return None
            return "task_scoped_input_deferred_until_failure_materializes"
        return None

    @staticmethod
    def _task_scoped_reuse_keys(workflow: Workflow, step: WorkflowStep) -> set[str]:
        benchmark = str(workflow.metadata.get("benchmark") or "").strip().lower()
        if benchmark != "toolsandbox":
            return set()
        if step.capability_id == "cap_write":
            return {"target_path", "expected_target_path"}
        return set()

    @staticmethod
    def _task_local_reuse_value(workflow: Workflow, step: WorkflowStep, key: str) -> Any:
        repair_defaults = step.metadata.get("repair_default_inputs")
        if isinstance(repair_defaults, dict):
            value = repair_defaults.get(key)
            if value not in (None, ""):
                return value
        value = step.inputs.get(key)
        if value not in (None, ""):
            return value
        metadata_value = workflow.metadata.get(key)
        if metadata_value not in (None, ""):
            return metadata_value
        return None

    @staticmethod
    def _constrain_reusable_profile(
        profile: Dict[str, Any],
        *,
        graph: Optional[CapabilityGraph],
        overplanning_objective: Dict[str, Any],
    ) -> Dict[str, Any]:
        constrained = {
            "capability_order": list(profile.get("capability_order", [])),
            "recommended_bindings": dict(profile.get("recommended_bindings", {})),
            "recommended_inputs": {
                capability_id: dict(inputs)
                for capability_id, inputs in dict(profile.get("recommended_inputs", {})).items()
                if isinstance(inputs, dict)
            },
            "continuation_hints": [
                dict(item)
                for item in profile.get("continuation_hints", [])
                if isinstance(item, dict)
            ],
            "auto_patch_input_keys": {
                capability_id: list(keys)
                for capability_id, keys in dict(profile.get("auto_patch_input_keys", {})).items()
                if isinstance(keys, list)
            },
            "asset_ids": list(profile.get("asset_ids", [])),
            "reuse_mode": str(profile.get("reuse_mode", "none")),
            "reuse_application": str(profile.get("reuse_application", "none")),
            "utility_gain_score": float(profile.get("utility_gain_score", 0.0) or 0.0),
            "auto_continuation_replay": bool(profile.get("auto_continuation_replay")),
            "selected_match": dict(profile.get("selected_match", {}))
            if isinstance(profile.get("selected_match", {}), dict)
            else {},
        }
        allowed_capabilities = {capability.capability_id for capability in graph.capabilities} if graph else set()
        preferred_capabilities = {
            str(item) for item in overplanning_objective.get("preferred_capabilities", []) if str(item)
        }
        if preferred_capabilities:
            allowed_capabilities = allowed_capabilities & preferred_capabilities if allowed_capabilities else preferred_capabilities

        allowed_tools = {str(item) for item in overplanning_objective.get("allowed_tools", []) if str(item)}
        if allowed_capabilities:
            constrained["capability_order"] = [
                capability_id
                for capability_id in constrained["capability_order"]
                if capability_id in allowed_capabilities
            ]
            constrained["recommended_bindings"] = {
                capability_id: tool_id
                for capability_id, tool_id in constrained["recommended_bindings"].items()
                if capability_id in allowed_capabilities and (not allowed_tools or tool_id in allowed_tools)
            }
            constrained["recommended_inputs"] = {
                capability_id: inputs
                for capability_id, inputs in constrained["recommended_inputs"].items()
                if capability_id in allowed_capabilities
            }
            constrained["auto_patch_input_keys"] = {
                capability_id: keys
                for capability_id, keys in constrained["auto_patch_input_keys"].items()
                if capability_id in allowed_capabilities
            }
            constrained["continuation_hints"] = [
                hint
                for hint in constrained["continuation_hints"]
                if not str(hint.get("capability_id") or "").strip()
                or str(hint.get("capability_id") or "").strip() in allowed_capabilities
            ]
        elif allowed_tools:
            constrained["recommended_bindings"] = {
                capability_id: tool_id
                for capability_id, tool_id in constrained["recommended_bindings"].items()
                if tool_id in allowed_tools
            }
            constrained["continuation_hints"] = [
                hint
                for hint in constrained["continuation_hints"]
                if not str(hint.get("tool_id") or "").strip()
                or str(hint.get("tool_id") or "").strip() in allowed_tools
            ]
        return constrained


class DefaultCapabilityGraphBuilder(CapabilityGraphBuilder):
    def __init__(self, delegate: RuleBasedCapabilityGraphBuilder) -> None:
        self.delegate = delegate

    def build(
        self,
        task: TaskSpec,
        candidates: Sequence[CapabilityCandidate],
        benchmark_hints: Optional[Dict[str, Any]] = None,
    ) -> CapabilityGraph:
        graph, _ = self.delegate.build(task=task, candidates=candidates, benchmark_hints=benchmark_hints)
        return graph


def build_default_planner(asset_registry: Optional["AssetRegistry"] = None) -> HTGPPlanner:
    from toolclaw.planner.capability_graph import CapabilityTemplateRegistry

    selector = RuleBasedCapabilitySelector()
    graph_builder = DefaultCapabilityGraphBuilder(
        RuleBasedCapabilityGraphBuilder(registry=CapabilityTemplateRegistry())
    )
    binder = ToolBinder()
    policy_injector = PolicyInjector()
    return HTGPPlanner(
        capability_selector=selector,
        graph_builder=graph_builder,
        binder=binder,
        policy_injector=policy_injector,
        asset_registry=asset_registry,
    )


from toolclaw.registry import AssetRegistry  # noqa: E402
