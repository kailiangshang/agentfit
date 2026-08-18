#!/usr/bin/env python3
"""Execute an AgentFit semantic candidate through an AgentTeams worker sandbox.

The four-layer Solution never selects MCP, native functions, HTTP, or a Memory
implementation.  A platform-owned SandboxAdapter resolves those details and
returns the stable AgentFit result envelope normalized here.
"""
from __future__ import annotations

from dataclasses import asdict
import math
import re
from typing import Any

from agentfit.adapters.protocols import SandboxAdapter, SandboxRequest
from agentfit.executors.base import ExecutorBase
from agentfit.models.evidence import CandidateManifest
from agentfit.models.loss import Expected, Trace, TraceStep
from agentfit.models.sample import TaskSample, canonical_hash
from agentfit.models.solution import Solution


TASK_SCHEMA = "agentfit.agentteams-task"
RESULT_SCHEMA = "agentfit.agentteams-result"


def _valid_cost(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    cost = float(value)
    return cost if math.isfinite(cost) and cost >= 0 else None


def _runtime_error(sample: TaskSample, runtime_ref: str, code: str, *,
                   cost_usd: Any = 0.0) -> Trace:
    cost = _valid_cost(cost_usd)
    return Trace(
        sample_id=sample.id,
        result="ERROR",
        cost_usd=cost if cost is not None else 0.0,
        error_scope="runtime",
        error_code=code,
        runtime_ref=runtime_ref,
    )


def _parse_step(data: Any) -> TraceStep:
    if not isinstance(data, dict):
        raise TypeError("step must be an object")
    layer = data.get("layer")
    element_id = data.get("element_id")
    action = data.get("action", "")
    ok = data.get("ok", True)
    error = data.get("error")
    downstream = data.get("downstream", [])
    if layer not in {"L1", "L2", "L3", "L4"}:
        raise ValueError("step layer is invalid")
    if not isinstance(element_id, str) or not element_id:
        raise TypeError("step element_id must be a non-empty string")
    if not isinstance(action, str) or type(ok) is not bool:
        raise TypeError("step action/ok types are invalid")
    if error is not None and not isinstance(error, str):
        raise TypeError("step error must be a string or null")
    if (
        not isinstance(downstream, list)
        or any(type(index) is not int or index < 0 for index in downstream)
    ):
        raise TypeError("step downstream must contain non-negative integers")
    return TraceStep(
        layer=layer,
        element_id=element_id,
        action=action,
        ok=ok,
        error=error,
        output=data.get("output"),
        expected_output=data.get("expected_output"),
        downstream=downstream,
    )


def trace_from_result(
    payload: Any,
    sample: TaskSample,
    *,
    runtime_ref: str,
    fallback_cost_usd: float = 0.0,
) -> Trace:
    """Normalize the stable AgentTeams result envelope into an AgentFit Trace."""
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != RESULT_SCHEMA
        or payload.get("runtime_ref") != runtime_ref
    ):
        return _runtime_error(
            sample, runtime_ref, "agentteams_result_contract_error",
            cost_usd=fallback_cost_usd,
        )
    cost_usd = _valid_cost(payload.get("cost_usd", fallback_cost_usd))
    if cost_usd is None:
        return _runtime_error(
            sample, runtime_ref, "agentteams_result_contract_error",
            cost_usd=fallback_cost_usd,
        )
    if payload.get("status") != "completed":
        error_code = payload.get("error_code") or "agentteams_execution_error"
        if not isinstance(error_code, str):
            return _runtime_error(
                sample, runtime_ref, "agentteams_result_contract_error",
                cost_usd=cost_usd,
            )
        return _runtime_error(
            sample, runtime_ref, error_code, cost_usd=cost_usd,
        )
    try:
        step_data = payload.get("steps", [])
        if not isinstance(step_data, list):
            raise TypeError("steps must be a list")
        steps = [_parse_step(step) for step in step_data]
        raw_risk_events = payload.get("risk_events", [])
        if not isinstance(raw_risk_events, list):
            raise TypeError("risk events must be a list")
        risk_events = list(raw_risk_events)
        if any(not isinstance(event, str) for event in risk_events):
            raise TypeError("risk events must be strings")
        routed_knowledge_id = payload.get("routed_knowledge_id")
        if routed_knowledge_id is not None and not isinstance(routed_knowledge_id, str):
            raise TypeError("routed knowledge id must be a string or null")
    except (TypeError, ValueError):
        return _runtime_error(
            sample, runtime_ref, "agentteams_result_contract_error",
            cost_usd=fallback_cost_usd,
        )
    trace = Trace(
        sample_id=sample.id,
        result="PASS",
        steps=steps,
        routed_knowledge_id=routed_knowledge_id,
        cost_usd=cost_usd,
        risk_events=risk_events,
        runtime_ref=runtime_ref,
    )
    trace.result = "PASS" if evaluate_trace(trace, sample.expected) else "FAIL"
    return trace


def evaluate_trace(trace: Trace, expected: Expected) -> bool:
    if trace.result == "ERROR":
        return False
    actual = sorted(step.element_id for step in trace.steps if step.layer == "L2" and step.ok)
    wanted = sorted(action.tool for action in expected.actions)
    return actual == wanted


class AgentTeamsSandboxExecutor(ExecutorBase):
    """Platform bridge that delegates execution to an existing isolated worker."""

    def __init__(
        self,
        sandbox: SandboxAdapter,
        *,
        deployment_ref: str,
        sandbox_ref: str,
        model_ref: str = "",
        binding_mode: str = "platform_resolved",
        cost_accounting: str = "unavailable",
        timeout_seconds: float = 120.0,
    ) -> None:
        if not deployment_ref or not sandbox_ref:
            raise ValueError("deployment_ref and sandbox_ref are required")
        self.sandbox = sandbox
        self.deployment_ref = deployment_ref
        self.sandbox_ref = sandbox_ref
        self.model_ref = model_ref
        self.binding_mode = binding_mode
        self.cost_accounting = cost_accounting
        self.timeout_seconds = timeout_seconds
        self._run_indices: dict[tuple[str, str], int] = {}

    def runtime_provenance(self) -> dict[str, str]:
        return {
            "platform": "agentteams",
            "execution_boundary": "worker_sandbox",
            "deployment_ref": self.deployment_ref,
            "sandbox_ref": self.sandbox_ref,
            "model_ref": self.model_ref,
            "binding_mode": self.binding_mode,
            "cost_accounting": self.cost_accounting,
        }

    def _task(self, solution: Solution, sample: TaskSample) -> dict[str, Any]:
        candidate = CandidateManifest.for_solution(solution)
        counter_key = (candidate.candidate_ref, sample.content_hash)
        run_index = self._run_indices.get(counter_key, 0)
        self._run_indices[counter_key] = run_index + 1
        runtime_ref = canonical_hash(self.runtime_provenance())
        task_id = canonical_hash({
            "candidate_ref": candidate.candidate_ref,
            "sample_ref": sample.ref,
            "run_index": run_index,
            "runtime_ref": runtime_ref,
        })[:24]
        return {
            "schema": TASK_SCHEMA,
            "task_id": task_id,
            "candidate_ref": candidate.candidate_ref,
            "run_index": run_index,
            "runtime_ref": runtime_ref,
            "solution": candidate.specification["solution"],
            "sample_ref": asdict(sample.ref),
            "input_data": sample.input_data,
            "constraints": sample.constraints,
            "requires_human": sample.requires_human,
        }

    def execute(self, solution: Solution, sample: TaskSample) -> Trace:
        if not isinstance(sample, TaskSample):
            raise TypeError("AgentTeamsSandboxExecutor accepts canonical TaskSample objects only")
        task = self._task(solution, sample)
        runtime_ref = canonical_hash(self.runtime_provenance())
        try:
            sandbox_result = self.sandbox.execute(SandboxRequest(
                tool="agentteams.execute_candidate",
                arguments=task,
                timeout_seconds=self.timeout_seconds,
            ))
        except Exception:
            return _runtime_error(
                sample, runtime_ref, "agentteams_sandbox_error",
            )
        sandbox_cost = _valid_cost(getattr(sandbox_result, "cost_usd", None))
        if getattr(sandbox_result, "status", None) != "ok":
            reported_error = getattr(sandbox_result, "error", None)
            error_code = (
                reported_error
                if isinstance(reported_error, str)
                and re.fullmatch(r"agentteams_[a-z0-9_]+", reported_error)
                else "agentteams_sandbox_error"
            )
            return _runtime_error(
                sample, runtime_ref, error_code,
                cost_usd=sandbox_cost,
            )
        payload = getattr(sandbox_result, "output", None)
        if (
            not isinstance(payload, dict)
            or payload.get("task_id") != task["task_id"]
            or payload.get("candidate_ref") != task["candidate_ref"]
            or payload.get("sample_ref") != task["sample_ref"]
            or payload.get("run_index") != task["run_index"]
            or payload.get("runtime_ref") != task["runtime_ref"]
        ):
            return _runtime_error(
                sample, runtime_ref, "agentteams_result_contract_error",
                cost_usd=sandbox_cost,
            )
        return trace_from_result(
            payload,
            sample,
            runtime_ref=runtime_ref,
            fallback_cost_usd=sandbox_cost if sandbox_cost is not None else 0.0,
        )

    def evaluate(self, trace: Trace, expected: Expected) -> bool:
        return evaluate_trace(trace, expected)
