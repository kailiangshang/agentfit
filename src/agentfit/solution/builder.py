"""初始方案构建（S1b 简版）：从样本归纳 Simple First 初始方案。

策略：按特征签名聚类 → 每个聚类的共性期望工具 = 一条 L3 路由规则；
coverage 控制初始覆盖比例（Simple First：不追求全覆盖，剩余交给训练）。
L1/L2 只能来自已确认 CapabilityInventory，不从期望动作名称推导。
"""
from __future__ import annotations

import copy

from ..data.clustering import cluster_samples
from ..models.manifest import SampleSetCollection, SampleSetPurpose
from ..models.project import CapabilityInventory
from ..models.sample import TaskSample
from ..models.solution import Agent, Knowledge, Solution, Topology


def build_candidate(samples: list[TaskSample],
                    sample_sets: SampleSetCollection,
                    capability_inventory: CapabilityInventory,
                    coverage: float = 0.5, seed: int = 7) -> Solution:
    """Build a candidate only from Human-frozen adaptation samples."""
    sample_sets.assert_ready_for_candidate_generation()
    adaptation = sample_sets.by_purpose(SampleSetPurpose.ADAPTATION)
    adaptation.require_access("architect", candidate_frozen=False, for_update=True)

    tasks = list(samples)
    if any(not isinstance(item, TaskSample) for item in tasks):
        raise TypeError("candidate builder accepts canonical TaskSample objects only")
    by_id = {task.id: task for task in tasks}
    selected: list[TaskSample] = []
    for ref in adaptation.sample_refs:
        task = by_id.get(ref.sample_id)
        if task is None:
            raise ValueError(f"adaptation sample is missing: {ref.sample_id}")
        actual_ref = task.ref
        if actual_ref.content_hash != ref.content_hash:
            raise ValueError(f"adaptation sample hash mismatch: {ref.sample_id}")
        if not task.observation_refs:
            raise ValueError(f"adaptation sample requires an ObservationRef: {ref.sample_id}")
        selected.append(task)
    return build_initial(
        selected, capability_inventory, coverage=coverage, seed=seed,
    )


def build_initial(samples: list[TaskSample],
                  capability_inventory: CapabilityInventory,
                  coverage: float = 0.5,
                  seed: int = 7) -> Solution:
    if any(not isinstance(item, TaskSample) for item in samples):
        raise TypeError("candidate builder accepts canonical TaskSample objects only")
    capability_inventory.assert_integrity()
    clusters = sorted(cluster_samples(samples).items(), key=lambda kv: (len(kv[1]), kv[0]), reverse=True)
    n_covered = max(1, round(len(clusters) * coverage))

    confirmed_tools = {tool.id for tool in capability_inventory.tools}
    required_tools = {
        action.tool for sample in samples for action in sample.expected.actions
    }
    unknown_tools = sorted(required_tools - confirmed_tools)
    if unknown_tools:
        raise ValueError(
            "expected tool is not present in approved capability inventory: "
            f"{unknown_tools[0]}"
        )

    # L3：初始知识只覆盖前 n_covered 个聚类（Simple First，剩余交给训练归纳）
    rules: list[Knowledge] = []
    for sig, members in clusters[:n_covered]:
        target = members[0].expected.actions[0].tool
        conditions = [t for t in sig.split(",") if "=" in t]
        cond = " AND ".join((t[:-2] if t.endswith("=1") else f"NOT {t[:-2]}") for t in conditions)
        rules.append(Knowledge(id=f"rule_{target}_{len(rules)}", type="routing_rule",
                               condition=cond, dispatches_to=target,
                               description=f"bootstrap 覆盖聚类 {sig[:40]}",
                               evidence_sample_ids=[s.id for s in members]))

    return Solution(version=0,
                    L1_atoms=list(copy.deepcopy(capability_inventory.atoms)),
                    L2_tools=list(copy.deepcopy(capability_inventory.tools)),
                    L3_knowledge=rules,
                    L4_topology=Topology(agents=[Agent("solo", "single", uses=[r.id for r in rules])]))
