"""Canonical, deterministic projection of tau2-bench source results.

The bridge writer and RunStore validator both use this module. Persisted
Trace/Episode files therefore cannot redefine what the original simulation
record means while remaining internally hash-consistent.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from agentfit.models.loss import Expected, Trace, TraceStep
from agentfit.models.sample import (
    Episode, EvaluationIdentity, TaskSample, canonical_hash,
)


FEATURE_MAP = {
    "airplane_mode_on": "airplane",
    "data_mode_off": "data_mode_off",
    "data_saver_mode_on": "data_saver",
    "bad_network_preference": "bad_network",
    "data_usage_exceeded": "data_exceeded",
    "user_abroad_roaming_enabled_off": "roaming_off_abroad",
    "user_abroad_roaming_disabled_on": "roaming_on_abroad",
}


@dataclass(frozen=True)
class Tau2ProjectedRecord:
    source_index: int
    task: TaskSample
    episode: Episode
    trace: Trace


@dataclass(frozen=True)
class Tau2Projection:
    runtime_provenance: dict[str, str]
    runtime_ref: str
    tasks: tuple[TaskSample, ...]
    records: tuple[Tau2ProjectedRecord, ...]
    num_trials: int
    evaluation: dict[str, int | float | bool]


def _cost(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, dict):
        value = value.get("total_cost_usd", 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("tau2 cost must be numeric")
    cost = float(value)
    if not math.isfinite(cost) or cost < 0:
        raise ValueError("tau2 cost must be finite and non-negative")
    return cost


def _features(simulation: dict[str, Any]) -> dict[str, bool]:
    task_id = str(simulation.get("task_id", ""))
    return {feature: True for cause, feature in FEATURE_MAP.items() if cause in task_id}


def simulation_to_task_sample(simulation: dict[str, Any]) -> TaskSample:
    """Convert one tau2 task/run record into the canonical TaskSample."""
    if not isinstance(simulation, dict):
        raise TypeError("tau2 simulation must be an object")
    task_id = str(simulation.get("task_id") or canonical_hash(simulation)[:16])
    features = _features(simulation)
    return TaskSample(
        id=task_id,
        observation_refs=(),
        input_data={"task_id": task_id, "features": features},
        expected=Expected(),
        evaluator="tau2_reward",
        constraints={"source": "tau2-bench"},
        complexity="compound" if len(features) >= 2 else "simple",
    )


def _tool_names(simulation: dict[str, Any]) -> list[str]:
    direct_calls = simulation.get("tool_calls") or []
    messages = simulation.get("messages") or []
    if not isinstance(direct_calls, list) or not isinstance(messages, list):
        raise ValueError("tau2 tool calls and messages must be lists")
    calls = list(direct_calls)
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("tau2 message must be an object")
        message_calls = message.get("tool_calls") or []
        if not isinstance(message_calls, list):
            raise ValueError("tau2 message tool_calls must be a list")
        calls.extend(message_calls)
    names: list[str] = []
    for call in calls:
        if isinstance(call, str):
            name = call
        elif isinstance(call, dict):
            function = call.get("function") or {}
            if not isinstance(function, dict):
                raise ValueError("tau2 function call must be an object")
            name = call.get("name") or function.get("name")
        else:
            raise ValueError("tau2 tool call must be a string or object")
        if name is not None:
            if not isinstance(name, str) or not name:
                raise ValueError("tau2 tool name must be a non-empty string")
            names.append(name)
    return names


def simulation_to_episode(
    simulation: dict[str, Any],
    task: TaskSample,
    *,
    candidate_ref: str,
    run_index: int,
    trace_ref: str | None = None,
    runtime_ref: str = "",
) -> tuple[Episode, Trace]:
    reward_info = simulation.get("reward_info") or {}
    if not isinstance(reward_info, dict):
        raise ValueError("tau2 reward_info must be an object")
    reward = reward_info.get("reward", 0)
    error = simulation.get("error") or simulation.get("exception")
    result = "ERROR" if error else "PASS" if reward == 1 else "FAIL"
    raw_risk_events = simulation.get("risk_events") or []
    if not isinstance(raw_risk_events, list):
        raise ValueError("tau2 risk_events must be a list")
    risk_events = [str(event) for event in raw_risk_events]
    trace = Trace(
        sample_id=task.id,
        result=result,
        steps=[
            TraceStep(layer="L2", element_id=name, action="tool_call", ok=True)
            for name in _tool_names(simulation)
        ],
        cost_usd=_cost(simulation.get("agent_cost")) + _cost(simulation.get("user_cost")),
        risk_events=risk_events,
        error_scope="runtime" if error else None,
        error_code="tau2_runtime_error" if error else None,
        runtime_ref=runtime_ref,
    )
    identity = EvaluationIdentity(candidate_ref, task.ref, run_index)
    episode = Episode(
        identity=identity,
        trace_ref=trace_ref or f"traces/{identity.key}.json",
        result=result,
        cost_usd=trace.cost_usd,
        evidence_hash=canonical_hash(trace),
        risk_events=len(trace.risk_events),
        runtime_ref=runtime_ref,
    )
    return episode, trace


def runtime_provenance(data: dict[str, Any]) -> dict[str, str]:
    configuration = data.get("config") or data.get("info") or data.get("metadata") or {}
    return {
        "platform": "tau2bench",
        "source_configuration_ref": canonical_hash(configuration),
    }


def project_results(data: dict[str, Any], candidate_ref: str) -> Tau2Projection:
    """Recompute the complete normalized evidence projection from source results."""
    if not isinstance(data, dict):
        raise TypeError("tau2 results must be an object")
    simulations = data.get("simulations")
    if not isinstance(simulations, list) or not simulations:
        raise ValueError("tau2 results contain no simulations")
    provenance = runtime_provenance(data)
    runtime_ref = canonical_hash(provenance)
    task_by_id: dict[str, TaskSample] = {}
    trial_counts: dict[str, int] = {}
    for simulation in simulations:
        task = simulation_to_task_sample(simulation)
        previous = task_by_id.get(task.id)
        if previous is not None and previous.content_hash != task.content_hash:
            raise ValueError(f"tau2 task id maps to conflicting content: {task.id}")
        task_by_id.setdefault(task.id, task)
        trial_counts[task.id] = trial_counts.get(task.id, 0) + 1

    run_indices: dict[str, int] = {}
    records: list[Tau2ProjectedRecord] = []
    for source_index, simulation in enumerate(simulations):
        task = task_by_id[simulation_to_task_sample(simulation).id]
        run_index = run_indices.get(task.id, 0)
        run_indices[task.id] = run_index + 1
        episode, trace = simulation_to_episode(
            simulation,
            task,
            candidate_ref=candidate_ref,
            run_index=run_index,
            runtime_ref=runtime_ref,
        )
        records.append(Tau2ProjectedRecord(source_index, task, episode, trace))

    passed = sum(record.episode.result == "PASS" for record in records)
    failed = sum(record.episode.result == "FAIL" for record in records)
    errors = sum(record.episode.result == "ERROR" for record in records)
    total_cost = sum(record.episode.cost_usd for record in records)
    evaluation: dict[str, int | float | bool] = {
        "total": len(records),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": passed / len(records),
        "cost_usd": round(total_cost, 4),
        "cost_observed": True,
        "risk_events": sum(record.episode.risk_events for record in records),
    }
    return Tau2Projection(
        runtime_provenance=provenance,
        runtime_ref=runtime_ref,
        tasks=tuple(task_by_id.values()),
        records=tuple(records),
        num_trials=max(trial_counts.values()),
        evaluation=evaluation,
    )
