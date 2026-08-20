"""存在依赖验证 + 同层约束检查（骨架 §一强约束，S5 的确定性内核）。

纯确定性代码：Validator 角色的裁决依据，同输入必同输出。
"""
from __future__ import annotations

from ..models.solution import CapabilityTool, Knowledge, Solution


def validate_taxonomy(solution: Solution, registry=None) -> list[str]:
    """类型合同（第一道检查）：每个元素的类型值必须在 core ∪ 注册表内。"""
    from ..models.taxonomy import (CORE_L1_ACCESS, CORE_L4_TRIGGER_MODES,
                                   DEFAULT_REGISTRY)
    registry = registry or DEFAULT_REGISTRY
    errors: list[str] = []
    l1_domains = registry.l1_domains()
    for atom in solution.L1_atoms:
        if atom.type not in CORE_L1_ACCESS:
            errors.append(f"L1 原子 {atom.id} 读写语义非法: {atom.type}")
        if atom.domain not in l1_domains:
            errors.append(f"L1 原子 {atom.id} 能力域非法: {atom.domain}（不在 core ∪ 注册表）")
    l2_types = registry.l2_capability_types()
    for tool in solution.L2_tools:
        if tool.capability_type not in l2_types:
            errors.append(f"L2 工具 {tool.id} 封装类型非法: {tool.capability_type}")
    l3_types = registry.l3_knowledge_types()
    for knowledge in solution.L3_knowledge:
        if knowledge.type not in l3_types:
            errors.append(f"L3 知识 {knowledge.id} 类型非法: {knowledge.type}")
    l4_roles = registry.l4_roles()
    for agent in solution.L4_topology.agents:
        if agent.role not in l4_roles:
            errors.append(f"L4 Agent {agent.id} 角色非法: {agent.role}")
    if solution.L4_topology.trigger_mode not in CORE_L4_TRIGGER_MODES:
        errors.append(f"L4 触发方式非法: {solution.L4_topology.trigger_mode}")
    return errors


def validate_existence_dependencies(solution: Solution) -> list[str]:
    """验证所有层间依赖完整，无悬空引用。空列表 = 通过。

    链条：L2→L1 / L3→L2 / L4→L3。L1 的运行绑定由 Executor/bridge 验证。
    """
    errors: list[str] = []
    atom_ids = {a.id for a in solution.L1_atoms}
    tool_ids = {t.id for t in solution.L2_tools}
    knowledge_ids = {k.id for k in solution.L3_knowledge}

    for tool in solution.L2_tools:
        for wrapped in tool.wraps:
            if wrapped not in atom_ids:
                errors.append(f"L2 工具 {tool.id} 封装了不存在的 L1 原子 {wrapped}")

    for knowledge in solution.L3_knowledge:
        if knowledge.superseded:
            continue
        if knowledge.dispatches_to and knowledge.dispatches_to not in tool_ids:
            errors.append(f"L3 知识 {knowledge.id} 调度的 L2 工具 {knowledge.dispatches_to} 不存在")
        if knowledge.steps:
            for step in knowledge.steps:
                if step.tool not in tool_ids:
                    errors.append(f"L3 排查链 {knowledge.id} 引用了不存在的 L2 工具 {step.tool}")

    agent_ids = [agent.id for agent in solution.L4_topology.agents]
    known_agents = set(agent_ids)
    for duplicate in sorted({agent_id for agent_id in agent_ids if agent_ids.count(agent_id) > 1}):
        errors.append(f"duplicate L4 Agent id {duplicate}")

    for agent in solution.L4_topology.agents:
        for used in agent.uses:
            if used not in knowledge_ids:
                errors.append(f"L4 Agent {agent.id} 使用了不存在的 L3 知识 {used}")

    for edge in solution.L4_topology.edges:
        if edge.from_agent not in known_agents:
            errors.append(
                f"L4 TopologyEdge {edge.from_agent}->{edge.to_agent} 的起点 Agent 不存在: {edge.from_agent}"
            )
        if edge.to_agent not in known_agents:
            errors.append(
                f"L4 TopologyEdge {edge.from_agent}->{edge.to_agent} 的终点 Agent 不存在: {edge.to_agent}"
            )
        if not edge.payload_type:
            errors.append(
                f"L4 TopologyEdge {edge.from_agent}->{edge.to_agent} requires payload_type"
            )

    for agent_id in solution.L4_topology.human_gate_positions:
        if agent_id not in known_agents:
            errors.append(f"L4 Human Gate position references unknown Agent: {agent_id}")

    return errors


def validate_same_layer_constraints(solution: Solution) -> list[str]:
    """L1-L3 禁止隐藏的同层执行依赖；L4 仅允许显式 TopologyEdge。"""
    errors: list[str] = []
    knowledge_ids = {k.id for k in solution.L3_knowledge}
    for knowledge in solution.L3_knowledge:
        if knowledge.type == "routing_rule":
            # 路由规则只能调度 L2 工具，不能调度别的知识
            if knowledge.dispatches_to and knowledge.dispatches_to in knowledge_ids:
                errors.append(f"路由规则 {knowledge.id} 调度了 L3 知识 {knowledge.dispatches_to}（执行时耦合，禁止）")
        if knowledge.steps:
            for step in knowledge.steps:
                if step.tool in knowledge_ids:
                    errors.append(f"排查链 {knowledge.id} 的步骤执行时调用了另一个 L3 知识 {step.tool}（禁止）")
    return errors


def cascade_target(solution: Solution, proposal_layer: str, needed_below: list[str]) -> str | None:
    """级联检查：要在 proposal_layer 建能力，下层缺失则返回应下移到的层（骨架 §一级联更新）。

    needed_below 按自底向上顺序给出下层必须已存在的元素描述；
    返回 None 表示下层支撑完整，可在目标层直接建。
    """
    have = {
        "L1": {a.id for a in solution.L1_atoms},
        "L2": {t.id for t in solution.L2_tools},
        "L3": {k.id for k in solution.L3_knowledge},
    }
    order = ["L1", "L2", "L3"]
    limit = order.index(proposal_layer)
    for layer in order[:limit]:
        for needed in needed_below:
            if needed not in have[layer]:
                return layer        # 断链层：更新目标下移到这里
    return None
