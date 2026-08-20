"""确定性 Telecom 模拟执行器：CI / 回归测试用，零 API 成本。

行为完全由方案内容决定：路由规则覆盖 → 派发对的工具 → PASS。
缺规则 → FAIL（归因 L3 missing_rule）；规则派发错工具 → FAIL（routing_error）；
复合样本在单 Agent 拓扑下 → FAIL（归因 L4 topology_mismatch）。
"""
from __future__ import annotations

from ..core.attribution import _condition_match
from ..models.loss import Expected, Trace, TraceStep
from ..models.sample import TaskSample
from ..models.solution import Solution
from .base import ExecutorBase

COST_PER_SAMPLE = 0.006


class SimulatorExecutor(ExecutorBase):
    def execute(self, solution: Solution, sample: TaskSample) -> Trace:
        if not isinstance(sample, TaskSample):
            raise TypeError("SimulatorExecutor accepts canonical TaskSample objects only")
        trace = Trace(sample_id=sample.id, cost_usd=COST_PER_SAMPLE)

        # L4：复合样本需要多 Agent 协同（单 Agent 拓扑撑不住）
        if sample.complexity == "compound" and len(solution.L4_topology.agents) <= 1:
            trace.result = "FAIL"
            trace.steps.append(TraceStep(layer="L4", element_id="topology",
                                         action="compound_requires_multi_agent", ok=False,
                                         error="复合根因样本，单 Agent 拓扑无法并行诊断"))
            return trace

        # 需人工样本：经 human_review 原子处理（合法交付 = 保留人工）
        if sample.requires_human:
            trace.steps.append(TraceStep(layer="L1", element_id="human_review",
                                         action="escalate", ok=True, output="handled_by_human"))
            trace.result = "PASS"
            return trace

        # L4→L3 可达性：只有被 Agent uses 引用的知识才可被路由（真实平台语义）
        reachable = {u for agent in solution.L4_topology.agents for u in agent.uses}

        # L3 优先匹配排查链（多步知识 = 任务拆解），再走路由规则
        chains = [k for k in solution.L3_knowledge
                  if k.type == "chain" and not k.superseded and k.steps]
        matched_chain = next((c for c in chains if _condition_match(c.condition, sample.input_data)), None)
        if matched_chain is not None:
            if matched_chain.id not in reachable:
                trace.result = "FAIL"
                trace.steps.append(TraceStep(layer="L4", element_id=matched_chain.id,
                                             action="unreachable_knowledge", ok=False,
                                             error=f"L3 知识 {matched_chain.id} 存在但未被任何 Agent 引用"))
                return trace
            trace.routed_knowledge_id = matched_chain.id
            for step in matched_chain.steps:
                tool = solution.tool(step.tool)
                if tool is None:
                    trace.result = "FAIL"
                    trace.steps.append(TraceStep(layer="L2", element_id=step.tool,
                                                 action="tool_missing", ok=False, error="链步骤工具不存在"))
                    return trace
                trace.steps.append(TraceStep(layer="L2", element_id=tool.id, action="execute",
                                             ok=True, output=tool.id, expected_output=tool.id))
                if tool.human_gate is not None:
                    trace.steps.append(TraceStep(layer="L1", element_id="human_review",
                                                 action=f"gate:{tool.human_gate.condition}", ok=True))
            trace.result = "PASS" if self.evaluate(trace, sample.expected) else "FAIL"
            return trace

        # L3 路由
        matched = [r for r in solution.routing_rules() if _condition_match(r.condition, sample.input_data)]
        if not matched:
            trace.result = "FAIL"
            trace.steps.append(TraceStep(layer="L3", element_id="-", action="no_rule_matched", ok=False,
                                         error=f"无路由规则覆盖 {sample.input_data}"))
            return trace
        reachable_matched = [r for r in matched if r.id in reachable]
        if not reachable_matched:
            unreachable_ids = [r.id for r in matched]
            trace.result = "FAIL"
            trace.steps.append(TraceStep(layer="L4", element_id=unreachable_ids[0],
                                         action="unreachable_knowledge", ok=False,
                                         error=f"L3 知识 {unreachable_ids} 存在但未被任何 Agent 引用"))
            return trace
        rule = reachable_matched[0]              # 具体性排序由方案构建保证；模拟器取首个
        trace.routed_knowledge_id = rule.id

        # 派发到 L2 工具（调度）。复合样本 + 多 Agent 拓扑 = 并行诊断，执行全部命中规则
        dispatch_targets = reachable_matched if (sample.complexity == "compound"
                                                 and len(solution.L4_topology.agents) > 1) else [rule]
        for r in dispatch_targets:
            if r.dispatches_to is None:
                trace.result = "FAIL"
                trace.steps.append(TraceStep(layer="L3", element_id=r.id, action="no_dispatch_target", ok=False))
                return trace
            tool = solution.tool(r.dispatches_to)
            if tool is None:
                trace.result = "FAIL"
                trace.steps.append(TraceStep(layer="L2", element_id=r.dispatches_to,
                                             action="tool_missing", ok=False, error="调度的工具不存在"))
                return trace

            # L2 执行（含人工门禁步骤）
            step = TraceStep(layer="L2", element_id=tool.id, action="execute", ok=True,
                             output=tool.id, expected_output=tool.id)
            trace.steps.append(step)
            if tool.human_gate is not None:
                trace.steps.append(TraceStep(layer="L1", element_id="human_review",
                                             action=f"gate:{tool.human_gate.condition}", ok=True))

        trace.result = "PASS" if self.evaluate(trace, sample.expected) else "FAIL"
        return trace

    def evaluate(self, trace: Trace, expected: Expected) -> bool:
        executed = sorted(s.element_id for s in trace.steps if s.layer == "L2")
        # 只有纯人工升级（没有执行 L2 工具）才按人工处理通过；普通工具的
        # Human Gate 只是审批步骤，不能掩盖错误动作。
        if not executed and any(s.element_id == "human_review" for s in trace.steps):
            return trace.result == "PASS"
        want = sorted(a.tool for a in expected.actions)
        return executed == want and trace.result == "PASS"
