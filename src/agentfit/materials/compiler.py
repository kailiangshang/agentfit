"""Deterministic compiler for structured business-material bundles."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..models.loss import Expected, ExpectedAction
from ..models.manifest import (
    FreezeDecision,
    SampleSetCollection,
    SampleSetManifest,
    SampleSetPurpose,
    default_access_policy,
)
from ..models.objective import ObjectiveSpec, objective_spec_from_material
from ..models.project import CapabilityInventory
from ..models.sample import SourceObservation, TaskSample
from ..models.solution import CapabilityTool, HumanGate, SolidAtom


@dataclass(frozen=True)
class CompiledProjectCase:
    scenario: str
    observations: tuple[SourceObservation, ...]
    task_samples: tuple[TaskSample, ...]
    sample_sets: SampleSetCollection
    capability_inventory: CapabilityInventory
    objective_spec: ObjectiveSpec
    training: dict[str, Any]

    def to_case_document(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "source_observations": [asdict(item) for item in self.observations],
            "task_samples": [asdict(item) for item in self.task_samples],
            "sample_sets": [
                {**asdict(item), "purpose": item.purpose.value}
                for item in self.sample_sets.manifests
            ],
            "capability_inventory": asdict(self.capability_inventory),
            "objective": {
                "criteria": [
                    {**asdict(item), "purpose": item.purpose.value}
                    for item in self.objective_spec.criteria
                ],
                "max_total_evaluation_cost_usd": (
                    self.objective_spec.max_total_evaluation_cost_usd
                ),
                "content_hash": self.objective_spec.content_hash,
            },
            "training": dict(self.training),
        }


def compile_material_bundle(bundle: dict[str, Any]) -> CompiledProjectCase:
    """Compile a structured bundle without invoking a model or external runtime."""
    scenario = str(bundle.get("scenario", "")).strip()
    if not scenario:
        raise ValueError("scenario is required")

    material_specs = bundle.get("materials")
    if not isinstance(material_specs, list) or not material_specs:
        raise ValueError("materials are required")
    observations = tuple(
        SourceObservation.create(
            id=str(item.get("id", "")).strip(),
            kind=str(item.get("kind", "")).strip(),
            content=item.get("content"),
            metadata=dict(item.get("metadata") or {}),
        )
        for item in material_specs
    )
    observation_by_id = {item.id: item for item in observations}
    if len(observation_by_id) != len(observations):
        raise ValueError("material ids must be unique")

    capability_data = bundle.get("capabilities")
    if not isinstance(capability_data, dict):
        raise ValueError("capability inventory is required")
    try:
        raw_atoms = capability_data.get("atoms", [])
        raw_tools = capability_data.get("tools", [])
        runtime_fields = {"backend", "implementation", "mcp", "function", "memory"}
        for item in raw_atoms:
            if isinstance(item, dict) and runtime_fields.intersection(item):
                raise ValueError(
                    "L1 atoms cannot contain a runtime binding; resolve it in an Executor/bridge"
                )
        capability_inventory = CapabilityInventory.create(
            atoms=tuple(
                SolidAtom(
                    id=str(item.get("id", "")).strip(),
                    type=str(item.get("type", "")).strip(),
                    description=str(item.get("description", "")),
                    input_schema=dict(item.get("input_schema") or {}),
                    output_schema=dict(item.get("output_schema") or {}),
                )
                for item in raw_atoms
            ),
            tools=tuple(
                CapabilityTool(
                    id=str(item.get("id", "")).strip(),
                    wraps=list(item.get("wraps") or []),
                    description=str(item.get("description", "")),
                    preconditions=list(item.get("preconditions") or []),
                    postconditions=list(item.get("postconditions") or []),
                    human_gate=(
                        HumanGate(**item["human_gate"])
                        if item.get("human_gate") else None
                    ),
                    aggregation_logic=item.get("aggregation_logic"),
                )
                for item in raw_tools
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid capability inventory: {exc}") from exc

    objective_data = bundle.get("objective")
    if not isinstance(objective_data, dict):
        raise ValueError("objective is required")
    try:
        objective_spec = objective_spec_from_material(objective_data)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid objective: {exc}") from exc

    task_specs = list(bundle.get("tasks", []))
    task_ids = [str(item.get("id", "")).strip() for item in task_specs]
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("task ids must be unique")

    tasks: list[tuple[SampleSetPurpose, TaskSample]] = []
    for item, task_id in zip(task_specs, task_ids):
        if not task_id:
            raise ValueError("task id is required")
        try:
            purpose = SampleSetPurpose(item["purpose"])
        except (KeyError, ValueError) as exc:
            raise ValueError("task purpose is invalid") from exc
        observation_ids = tuple(item.get("observation_ids") or ())
        if not observation_ids:
            raise ValueError(f"task {task_id} requires an observation")
        unknown = [identifier for identifier in observation_ids if identifier not in observation_by_id]
        if unknown:
            raise ValueError(f"unknown observation: {unknown[0]}")
        actions = [
            ExpectedAction(tool=str(action.get("tool", "")).strip(),
                           params=dict(action.get("params") or {}))
            for action in (item.get("expected") or {}).get("actions", [])
        ]
        if not actions or any(not action.tool for action in actions):
            raise ValueError(f"task {task_id} requires an expected action")
        expected = Expected(
            actions=actions,
            outcome=dict((item.get("expected") or {}).get("outcome") or {}),
        )
        tasks.append((purpose, TaskSample(
            id=task_id,
            observation_refs=tuple(observation_by_id[identifier].ref for identifier in observation_ids),
            input_data=dict(item.get("input_data") or {}),
            expected=expected,
            evaluator=str(item.get("evaluator", "exact")),
            constraints=dict(item.get("constraints") or {}),
            requires_human=bool(item.get("requires_human", False)),
            complexity=str(item.get("complexity", "simple")),
        )))

    confirmed_tools = {tool.id for tool in capability_inventory.tools}
    unknown_tools = sorted({
        action.tool
        for _, task in tasks
        for action in task.expected.actions
        if action.tool not in confirmed_tools
    })
    if unknown_tools:
        raise ValueError(
            "expected tool is not present in approved capability inventory: "
            f"{unknown_tools[0]}"
        )

    freeze_data = bundle.get("freeze")
    if not isinstance(freeze_data, dict) or freeze_data.get("approved") is not True:
        raise ValueError("an approved Human Freeze is required")
    freeze = FreezeDecision(**freeze_data)
    try:
        manifests = tuple(
            SampleSetManifest.create(
                purpose=purpose,
                sample_refs=tuple(task.ref for task_purpose, task in tasks if task_purpose == purpose),
                access_policy=default_access_policy(purpose),
                freeze=freeze,
            )
            for purpose in SampleSetPurpose
        )
        sample_sets = SampleSetCollection(manifests)
    except ValueError as exc:
        raise ValueError("four required sample sets must each contain a task") from exc

    return CompiledProjectCase(
        scenario=scenario,
        observations=observations,
        task_samples=tuple(task for _, task in tasks),
        sample_sets=sample_sets,
        capability_inventory=capability_inventory,
        objective_spec=objective_spec,
        training=dict(bundle.get("training") or {}),
    )
