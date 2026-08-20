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


def semantic_for_element(element, registry=None) -> str:
    """语义双轨的人话句（三层保底：description → 类型映射 → 最小人话，不编造）。"""
    from ..models.taxonomy import (CORE_L1_ACCESS, DEFAULT_REGISTRY)
    registry = registry or DEFAULT_REGISTRY
    eid = getattr(element, "id", str(element))
    desc = (getattr(element, "description", "") or "").strip()
    etype = getattr(element, "type", None)
    layer_cls = type(element).__name__
    if layer_cls == "SolidAtom":
        access = CORE_L1_ACCESS.get(getattr(element, "type", ""), getattr(element, "type", ""))
        domain = registry.semantic_l1_domain(getattr(element, "domain", "data_interface"))
        return f"原子接口“{eid}”（{domain}·{access}）——{desc}" if desc else \
               f"原子接口“{eid}”（{domain}·{access}，未提供用途描述）"
    if layer_cls == "CapabilityTool":
        label = registry.semantic_l2_type(getattr(element, "capability_type", "safe_wrapper"))
        return f"{label}“{eid}”——{desc}" if desc else f"{label}“{eid}”（未提供用途描述）"
    if layer_cls == "Knowledge":
        label = registry.semantic_l3_type(etype or "")
        return f"{label}“{eid}”——{desc}" if desc else f"{label}“{eid}”（未提供用途描述）"
    if layer_cls == "Topology":
        agents = getattr(element, "agents", [])
        return f"Agent 拓扑（{len(agents)} 个角色：{', '.join(a.role for a in agents)}）"
    return f"{layer_cls}“{eid}”"


_ACTION_SEMANTIC = {"add": "新增", "modify": "调整", "supersede": "下线", "remove": "删除"}


def semantic_for_proposal(proposal, registry=None) -> str:
    action = _ACTION_SEMANTIC.get(proposal.action, proposal.action)
    return f"维护{action}了{semantic_for_element(proposal.element, registry)}"


def annotate_reg_conflicts(proposals: list, report, solution: Solution) -> None:
    """任务提案加剧已超阈指标 → 标注 reg_conflict（人审可见对抗关系）。"""
    over = set(report.over_threshold.get("L3", [])) | set(report.over_threshold.get("L2", []))
    if not over:
        return
    ref_count: dict[str, int] = {}
    for k in solution.L3_knowledge:
        if k.steps:
            for step in k.steps:
                ref_count[step.tool] = ref_count.get(step.tool, 0) + 1
        elif k.dispatches_to:
            ref_count[k.dispatches_to] = ref_count.get(k.dispatches_to, 0) + 1
    for proposal in proposals:
        if proposal.origin != "task" or proposal.reg_conflict:
            continue
        if proposal.layer == "L3" and "chain_coverage" in over:
            element = proposal.element
            if getattr(element, "dispatches_to", None) and ref_count.get(element.dispatches_to, 0) > 0:
                proposal.reg_conflict = "chain_coverage"


def stable_element_id(prefix: str, payload: object) -> str:
    """Build a reproducible identifier from canonical content."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def propagate_reverse_dependencies(proposals: list[UpdateProposal],
                                   solution: Solution) -> list[UpdateProposal]:
    """反向依赖传播：修复"变更对已有依赖者的影响"，不替归因做接线决策。

    语义边界（防止旁路化）：
    - 纯新增（add）没有依赖者，无影响可传播——新增知识是否接入 L4 由训练循环
      通过 unreachable_knowledge 归因驱动（失败证据 → 建议 → G1 → 事务），不自动送。
    - supersede 下线已有元素时，依赖它的上层引用（L4 uses）是真实的变更影响，
      由传播修复：移除被下线引用，替换为同批新增的修正元素。
    """
    extra: list[UpdateProposal] = []
    if not proposals or not solution.L4_topology.agents:
        return extra
    superseded_ids = {p.element.id for p in proposals
                      if p.layer == "L3" and p.action == "supersede"
                      and isinstance(p.element, Knowledge)}
    added_ids = {p.element.id for p in proposals
                 if p.layer == "L3" and p.action == "add"
                 and isinstance(p.element, Knowledge)}
    if not superseded_ids:
        return extra
    replacement = next(iter(added_ids), None) if len(added_ids) == 1 else None
    import copy
    topology = copy.deepcopy(solution.L4_topology)
    changed = False
    for agent in topology.agents:
        for stale in [u for u in agent.uses if u in superseded_ids]:
            agent.uses.remove(stale)
            if replacement and replacement not in agent.uses:
                agent.uses.append(replacement)
            changed = True
    if not changed:
        return extra
    extra.append(UpdateProposal(
        "L4", "modify", topology,
        reason=f"反向依赖传播：{len(superseded_ids)} 个下线元素的 L4 引用清理",
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
                                                semantic=semantic_for_proposal(UpdateProposal("L3", "add", rule)),
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
            if orphan is not None and solution.L4_topology.agents:
                import copy
                topology = copy.deepcopy(solution.L4_topology)
                same_type_ids = {k.id for k in solution.L3_knowledge
                                 if k.type == orphan.type and k.id != orphan.id}
                holders = [a for a in topology.agents if any(k in same_type_ids for k in a.uses)]
                targets = holders or topology.agents
                for agent in targets:
                    if orphan.id not in agent.uses:
                        agent.uses.append(orphan.id)
                proposals.append(UpdateProposal(
                    "L4", "modify", topology,
                    reason=f"不可达知识 {element} 接入拓扑（unreachable_knowledge 归因证据驱动）",
                    evidence_sample_ids=sample_ids))
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
    混合证据（无共性特征但目标工具不同）先按期望动作分组，逐组归纳。
    """
    if any(not isinstance(item, TaskSample) for item in evidence):
        raise TypeError("proposal evidence accepts canonical TaskSample objects only")
    if not evidence:
        return None
    action_key = lambda s: tuple(sorted(a.tool for a in s.expected.actions))  # noqa: E731
    groups: dict[tuple, list[TaskSample]] = {}
    for sample in evidence:
        groups.setdefault(action_key(sample), []).append(sample)
    if len(groups) > 1:
        # 混合失败模式：逐组归纳返回首个成功结果（调用方按 pattern 聚合，
        # 同 pattern 内不同工具的样本各有自己的规则）
        for members in groups.values():
            rule = _rule_from_evidence(members, solution, replace_id)
            if rule is not None:
                return rule
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
