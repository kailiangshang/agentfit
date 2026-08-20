"""更新建议生成（S3 内核）+ 级联检查（S4 内核）。

模式 → 更新动作映射（骨架）：
  L3 missing_rule   → 新增路由规则（条件=共性特征合取，目标=证据样本期望工具）
  L3 routing_error  → supersede 错误规则 + 新增修正规则
  L4 topology_mismatch → 拓扑变更（必须走 G1 人审）
  human / eval_error → 不改方案（边界项记录）
  L1 missing_atom   → 升级用户确认基础设施（不自动建）
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json

from ..core.aggregation import AggregatedLoss
from ..core.transaction import UpdateProposal
from ..models.sample import TaskSample
from ..models.solution import Agent, Knowledge, Solution, Topology


def stable_element_id(prefix: str, payload: object) -> str:
    """Build a reproducible identifier from canonical content."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def propagate_reverse_dependencies(proposals: list[UpdateProposal],
                                   solution: Solution) -> list[UpdateProposal]:
    """反向依赖传播：新增 L3 知识必须被 L4 Agent 引用，否则沿 L4→L3 不可达。

    确定性规则：引用了同类型知识的 Agent 获得新元素；没有任何 Agent 引用过
    该类型时，所有 Agent 获得（Simple First 单 Agent 场景即该 Agent）。
    """
    extra: list[UpdateProposal] = []
    if not proposals:
        return extra
    referenced = {u for agent in solution.L4_topology.agents for u in agent.uses}
    new_knowledge = [p.element for p in proposals
                     if p.layer == "L3" and p.action == "add"
                     and isinstance(p.element, Knowledge) and p.element.id not in referenced]
    if not new_knowledge:
        return extra
    import copy
    topology = copy.deepcopy(solution.L4_topology)
    for element in new_knowledge:
        same_type_ids = {k.id for k in solution.L3_knowledge if k.type == element.type}
        holders = [a for a in topology.agents if any(k in same_type_ids for k in a.uses)]
        targets = holders or topology.agents
        for agent in targets:
            if element.id not in agent.uses:
                agent.uses.append(element.id)
    extra.append(UpdateProposal(
        "L4", "modify", topology,
        reason=f"反向依赖传播：{len(new_knowledge)} 个新增 L3 知识接入拓扑",
        evidence_sample_ids=sorted({sid for p in proposals
                                    for sid in (p.evidence_sample_ids or [])}) or None,
    ))
    return extra


def propose_updates(agg: AggregatedLoss, samples_by_id: dict[str, TaskSample],
                    solution: Solution) -> tuple[list[UpdateProposal], list[str]]:
    """返回 (建议列表, 边界备注列表)。"""
    proposals: list[UpdateProposal] = []
    notes: list[str] = []

    for (layer, mode, element), sample_ids in sorted(agg.patterns.items(), key=lambda kv: -len(kv[1])):
        evidence = [samples_by_id[sid] for sid in sample_ids if sid in samples_by_id]
        if layer == "L3" and mode == "missing_rule":
            rule = _rule_from_evidence(evidence, solution)
            if rule is not None:
                proposals.append(UpdateProposal("L3", "add", rule,
                                                reason=f"{len(sample_ids)} 个样本缺路由覆盖",
                                                evidence_sample_ids=sample_ids))
        elif layer == "L3" and mode == "routing_error" and element != "-":
            old = solution.knowledge(element)
            fixed = _rule_from_evidence(evidence, solution, replace_id=element)
            if old is not None and fixed is not None:
                proposals.append(UpdateProposal("L3", "supersede", old,
                                                reason="错误分支下线", evidence_sample_ids=sample_ids))
                proposals.append(UpdateProposal("L3", "add", fixed,
                                                reason=f"{len(sample_ids)} 个样本路由错误修正",
                                                evidence_sample_ids=sample_ids))
        elif layer == "L4" and mode == "unreachable_knowledge" and element != "-":
            orphan = solution.knowledge(element)
            if orphan is not None:
                proposals.extend(propagate_reverse_dependencies(
                    [UpdateProposal("L3", "add", orphan, reason="不可达知识重新接入",
                                    evidence_sample_ids=sample_ids)], solution))
        elif layer == "L4" and mode == "topology_mismatch":
            all_knowledge_ids = [k.id for k in solution.L3_knowledge if not k.superseded]
            dual = Topology(agents=[Agent("triage", "diagnostic", uses=list(all_knowledge_ids)),
                                    Agent("resolver", "repair", uses=list(all_knowledge_ids))],
                            edges=[], human_gate_positions=[], trigger_mode="passive")
            proposals.append(UpdateProposal("L4", "add", dual,
                                            reason="复合样本证据：需要诊断+修复双 Agent",
                                            evidence_sample_ids=sample_ids))
        elif layer in ("human",):
            notes.append(f"{len(sample_ids)} 个样本归因 needs_human：纳入交付边界（保留人工）")
        elif layer == "eval_error":
            notes.append(f"{len(sample_ids)} 个样本归因 eval_error：评价方式需复核")
        elif layer == "L1" and mode == "missing_atom":
            notes.append(f"缺原子 {element}：需用户确认基础设施后才能建（不自动创建）")
    return proposals, notes


def _rule_from_evidence(evidence: list[TaskSample], solution: Solution, replace_id: str | None = None) -> Knowledge | None:
    """从失败样本归纳新知识：条件 = 样本布尔特征的合取（出现率 100% 的键）。

    单动作证据 → routing_rule（调度一个 L2 工具）；
    多动作证据 → chain 排查链（任务拆解为有序步骤，骨架 L3 知识类型）。
    """
    if any(not isinstance(item, TaskSample) for item in evidence):
        raise TypeError("proposal evidence accepts canonical TaskSample objects only")
    if not evidence:
        return None
    bool_keys: list[str] = []
    for key, val in evidence[0].input_data.items():
        if isinstance(val, bool) and all(s.input_data.get(key) is val for s in evidence):
            bool_keys.append(key if val else f"NOT {key}")
    bool_keys.sort()
    actions = list(evidence[0].expected.actions)
    tool_counter = Counter(a.tool for s in evidence for a in s.expected.actions)
    if not tool_counter:
        return None
    if not bool_keys:
        return None            # 无共性布尔特征 → 拒绝生成无条件兜底规则（会匹配一切）
    condition = " AND ".join(bool_keys)

    if len(actions) > 1:      # 多动作 → 排查链（任务拆解）
        if any(solution.tool(a.tool) is None for a in actions):
            return None       # 链上任何工具缺失 → 级联下移，不盲建
        chain_id = replace_id or stable_element_id("chain", bool_keys)
        from ..models.solution import ChainStep
        return Knowledge(id=chain_id, type="chain", condition=condition,
                         steps=[ChainStep(tool=a.tool) for a in actions],
                         description=f"训练归纳（多步）：{[s.id for s in evidence[:3]]}")

    target_tool = tool_counter.most_common(1)[0][0]
    if solution.tool(target_tool) is None:
        return None            # 目标工具不存在 → 级联下移场景，此处不盲建（保持最小实现）
    rule_id = replace_id or stable_element_id(f"rule_{target_tool}", bool_keys)
    return Knowledge(id=rule_id, type="routing_rule", condition=condition, dispatches_to=target_tool,
                     description=f"训练归纳：{[s.id for s in evidence[:3]]}")
