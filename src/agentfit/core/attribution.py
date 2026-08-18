"""反向归因器（S1 的确定性内核 + LLM 歧义槽位）。

骨架 §二：自底向上 L1→L4，找到即验证（因果性/反事实），附带问题不阻塞，就近归因。
执行策略：步骤 1-5 确定性代码；仅反事实无法机械判定时进入 ambiguity_resolver（LLM 槽位）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models.loss import LossTrace, SideIssue, Trace
from ..models.sample import TaskSample
from ..models.solution import Solution


class AmbiguityResolver(Protocol):
    """LLM 槽位接口：仅处理机械验证无法判定的反事实问题。生产接 LLM，测试接确定性 mock。"""

    def would_fix_make_pass(self, sample: TaskSample, trace: Trace, anomaly: str) -> tuple[bool, float]: ...  # noqa: E704


class MechanicalResolver:
    """确定性兜底：假设"修复该异常样本即通过"（乐观假设 + 满置信）。

    仅用于异常明确位于期望路径上的情形；歧义场景应由 LLM resolver 降低置信度。
    """

    def would_fix_make_pass(self, sample: TaskSample, trace: Trace, anomaly: str) -> tuple[bool, float]:
        return True, 0.7


@dataclass
class _Candidate:
    layer: str
    element: str
    failure_mode: str
    detail: str
    anomaly_key: str


def attribute_loss(sample: TaskSample, trace: Trace, solution: Solution,
                   resolver: AmbiguityResolver | None = None) -> LossTrace:
    if not isinstance(sample, TaskSample):
        raise TypeError("attribute_loss accepts canonical TaskSample objects only")
    if trace.result == "ERROR":
        raise ValueError("execution errors cannot be attributed to L1-L4")
    resolver = resolver or MechanicalResolver()
    side_issues: list[SideIssue] = []

    # Step 1 → L1：期望动作对应的能力有底层支撑吗？
    # 期望动作命名 L2 工具；工具存在且其封装的原子齐全 → 本层通过。
    # 工具不存在时区分：原子在而封装缺 → L2；连原子都缺 → L1（需用户确认基础设施）。
    for action in sample.expected.actions:
        target = action.tool
        tool = solution.tool(target)
        if tool is not None:
            continue                     # 工具在，原子由存在依赖验证保证
        if solution.atom(target) is None:
            ok, conf = resolver.would_fix_make_pass(sample, trace, f"L1:missing:{target}")
            if ok:
                return LossTrace(sample.id, "L1", target, "missing_atom",
                                 f"期望动作 {target} 无 L1 原子支撑", confidence=conf, side_issues=side_issues)
            side_issues.append(SideIssue("L1", target, "缺原子但非根因"))
        else:
            side_issues.append(SideIssue("L2", target, "缺封装（原子已在）"))

    # Step 2 → L2：已执行步骤中封装有错吗？（关键路径 = 有下游消费者且输出与期望不符）
    for idx, step in enumerate(trace.steps):
        if step.layer == "L2" and step.error:
            if step.downstream and step.output != step.expected_output:
                ok, conf = resolver.would_fix_make_pass(sample, trace, f"L2:error:{step.element_id}")
                if ok:
                    return LossTrace(sample.id, "L2", step.element_id, "tool_error",
                                     step.error or "封装执行错误", confidence=conf, side_issues=side_issues,
                                     evidence={"step_index": idx})
            side_issues.append(SideIssue("L2", step.element_id, step.error or "旁路错误"))

    # 执行器若在拓扑入口明确阻断，后续路由根本没有发生；不能把未执行的
    # L3 路径臆测为根因。
    if any(step.layer == "L4" and not step.ok for step in trace.steps):
        return LossTrace(sample.id, "L4", "topology", "topology_mismatch",
                         "Trace 明确记录拓扑能力不足", confidence=1.0,
                         side_issues=side_issues)

    # Step 3 → L3：实际路径 vs 期望路径（缺链路 / 走错分支）。
    # 仅当路由确实发生过（routed_knowledge_id 非空）才判 routing_error；
    # 路由未发生但规则存在 → 失败不在 L3，落到 L4 检查。
    actual_tools = [s.element_id for s in trace.steps if s.layer == "L2"]
    expected_tools = [a.tool for a in sample.expected.actions]
    if trace.routed_knowledge_id is None:
        matched = [r for r in solution.routing_rules() if _condition_match(r.condition, sample.input_data)]
        if not matched:
            ok, conf = resolver.would_fix_make_pass(sample, trace, "L3:missing_rule")
            if ok:
                return LossTrace(sample.id, "L3", "-", "missing_rule",
                                 f"无路由规则覆盖特征 {sample.input_data}", confidence=conf, side_issues=side_issues)
            side_issues.append(SideIssue("L3", "-", "缺规则但非根因"))
    elif actual_tools != expected_tools:
        ok, conf = resolver.would_fix_make_pass(sample, trace, f"L3:routing:{trace.routed_knowledge_id}")
        if ok:
            return LossTrace(sample.id, "L3", trace.routed_knowledge_id, "routing_error",
                             f"实际路径 {actual_tools} ≠ 期望 {expected_tools}", confidence=conf,
                             side_issues=side_issues,
                             evidence={"actual": actual_tools, "expected": expected_tools})
        side_issues.append(SideIssue("L3", trace.routed_knowledge_id, "路径偏差但非根因"))

    # Step 4 → L4：拓扑适配吗？
    if sample.complexity == "compound" and len(solution.L4_topology.agents) <= 1:
        return LossTrace(sample.id, "L4", "topology", "topology_mismatch",
                         "复合样本但当前为单 Agent 拓扑", confidence=0.8, side_issues=side_issues)

    # 前置检查：需要人 or 评价标准有误
    if sample.requires_human:
        return LossTrace(sample.id, "human", "-", "needs_human",
                         "样本标注为需人工处理", side_issues=side_issues)
    return LossTrace(sample.id, "eval_error", "-", "eval_error",
                     "四层均无异常但样本判失败：检查评价方式", side_issues=side_issues)


def _condition_match(condition: str | None, features: dict) -> bool:
    """路由条件的极简求值：AND 项全部命中（None = 兜底规则）。"""
    if condition is None:
        return True
    for term in condition.split(" AND "):
        term = term.strip()
        neg = term.startswith("NOT ")
        key = term[4:] if neg else term
        val = bool(features.get(key, False))
        if val == neg:
            return False
    return True


def is_root_cause(anomaly_step_index: int, trace: Trace) -> bool:
    """反事实推演的机械部分：异常步骤是否在关键路径上（有下游且输出影响结果）。"""
    if anomaly_step_index < 0 or anomaly_step_index >= len(trace.steps):
        return False
    step = trace.steps[anomaly_step_index]
    if not step.downstream:
        return False            # 旁路操作（如日志）→ 附带问题
    return step.output != step.expected_output
