"""存在依赖验证 + 同层约束检查（骨架 §一强约束，S5 的确定性内核）。

纯确定性代码：Validator 角色的裁决依据，同输入必同输出。
"""
from __future__ import annotations

from ..models.solution import CapabilityTool, Knowledge, Solution

BACKEND_REGISTRY: set[str] = set()   # 已确认存在的基础设施（测试/运行时注册）


def register_infrastructure(backends: list[str]) -> None:
    BACKEND_REGISTRY.update(backends)


def validate_existence_dependencies(solution: Solution, check_backend: bool = False) -> list[str]:
    """验证所有层间依赖完整，无悬空引用。空列表 = 通过。

    链条：L1→基础设施 / L2→L1 / L3→L2 / L4→L3。
    """
    errors: list[str] = []
    atom_ids = {a.id for a in solution.L1_atoms}
    tool_ids = {t.id for t in solution.L2_tools}
    knowledge_ids = {k.id for k in solution.L3_knowledge}

    for atom in solution.L1_atoms:
        if check_backend and atom.backend not in BACKEND_REGISTRY:
            errors.append(f"L1 原子 {atom.id} 引用了未确认的基础设施 {atom.backend}")

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

    for agent in solution.L4_topology.agents:
        for used in agent.uses:
            if used not in knowledge_ids:
                errors.append(f"L4 Agent {agent.id} 使用了不存在的 L3 知识 {used}")

    return errors


def validate_same_layer_constraints(solution: Solution) -> list[str]:
    """横向约束：同层禁止执行时互调（L3 dispatch 是组织功能，合法；链步骤调用别的 Skill 是执行耦合，非法）。"""
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
