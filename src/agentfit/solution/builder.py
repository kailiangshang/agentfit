"""初始方案构建（S1b 简版）：从样本归纳 Simple First 初始方案。

策略：按特征签名聚类 → 每个聚类的共性期望工具 = 一条 L3 路由规则；
coverage 控制初始覆盖比例（Simple First：不追求全覆盖，剩余交给训练）。
L1/L2 从期望工具命名约定推导（safe_x → 原子 x）；用户提供工具清单时可注入。
"""
from __future__ import annotations

from ..data.clustering import cluster_samples
from ..models.loss import Sample
from ..models.solution import (Agent, CapabilityTool, Knowledge, Solution,
                               SolidAtom, Topology)


def build_initial(samples: list[Sample], coverage: float = 0.5,
                  seed: int = 7) -> Solution:
    clusters = sorted(cluster_samples(samples).items(), key=lambda kv: (len(kv[1]), kv[0]), reverse=True)
    n_covered = max(1, round(len(clusters) * coverage))

    # L1/L2：从全部样本反推工具清单（基础设施从材料可知，不靠训练补）
    atoms: dict[str, SolidAtom] = {}
    tools: dict[str, CapabilityTool] = {}
    for _, members in clusters:
        for action in {a.tool for s in members for a in s.expected.actions}:
            atom_id = action.removeprefix("safe_")
            atoms.setdefault(atom_id, SolidAtom(atom_id, "write", "scenario_api", atom_id))
            tools.setdefault(action, CapabilityTool(action, [atom_id], action))

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

    return Solution(version=0, L1_atoms=list(atoms.values()), L2_tools=list(tools.values()),
                    L3_knowledge=rules,
                    L4_topology=Topology(agents=[Agent("solo", "single", uses=[r.id for r in rules])]))
