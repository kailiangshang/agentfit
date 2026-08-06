"""Graph executor — runs an AgentGraph on a task input.

Simulates the AgentTeams collaboration model:
- Sequential nodes execute in order
- Conditional edges route based on node output
- BACK edges create bounded SCCs (iteration loops)
- MEMORY edges inject cross-node state

The executor produces a full execution trace, which GovernanceAuditor
uses for auditing.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from agentfit.graph.model import AgentGraph, EdgeType, Node, NodeType


@dataclass
class TraceEntry:
    step: int
    node_id: str
    node_type: str
    action: str
    output: Any
    elapsed_ms: float
    iteration: int = 0
    detail: str = ""


@dataclass
class ExecutionResult:
    task_id: str
    graph_name: str
    success: bool
    output: Any
    trace: list[TraceEntry] = field(default_factory=list)
    total_elapsed_ms: float = 0.0
    iterations_total: int = 0
    human_interventions: int = 0
    error: str = ""

    def token_cost_estimate(self) -> int:
        cost = 0
        for entry in self.trace:
            if entry.node_type == NodeType.LLM.value:
                cost += 800 + len(str(entry.output)) * 2
            elif entry.node_type == NodeType.TOOL.value:
                cost += 100
            elif entry.node_type == NodeType.HUMAN.value:
                cost += 0
        return cost


class GraphExecutor:
    def __init__(self, llm_simulator):
        self.llm = llm_simulator

    def execute(self, graph: AgentGraph, task_input: dict) -> ExecutionResult:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        trace: list[TraceEntry] = []
        start = time.perf_counter()

        entry = graph.entry_node()
        if entry is None:
            return ExecutionResult(
                task_id=task_id, graph_name=graph.name,
                success=False, output=None, error="No entry node",
            )

        context: dict[str, Any] = {"input": task_input, "memory": {}}
        current = entry
        visited_count: dict[str, int] = {}
        human_count = 0
        iterations = 0
        result_output = None
        error = ""

        while current is not None:
            nid = current.id
            visited_count[nid] = visited_count.get(nid, 0) + 1
            iteration = visited_count[nid]

            t0 = time.perf_counter()
            try:
                node_output, action, detail = self._run_node(current, context, graph)
            except Exception as exc:
                error = f"Node {nid} failed: {exc}"
                elapsed = (time.perf_counter() - t0) * 1000
                trace.append(TraceEntry(
                    step=len(trace), node_id=nid,
                    node_type=current.type.value,
                    action="error", output=str(exc),
                    elapsed_ms=elapsed, iteration=iteration,
                ))
                break

            elapsed = (time.perf_counter() - t0) * 1000
            trace.append(TraceEntry(
                step=len(trace), node_id=nid,
                node_type=current.type.value,
                action=action, output=node_output,
                elapsed_ms=elapsed, iteration=iteration,
                detail=detail,
            ))

            if current.type == NodeType.HUMAN:
                human_count += 1

            context[f"output_{nid}"] = node_output
            result_output = node_output

            if current.type == NodeType.LLM and current.max_iterations > 1:
                context["memory"][nid] = node_output

            next_node = self._route(graph, current, node_output, context, visited_count)
            if next_node is None:
                break
            if visited_count.get(next_node.id, 0) >= next_node.max_iterations + 5:
                error = f"Max iterations exceeded at {next_node.id}"
                break
            iterations += 1
            if iterations > 50:
                error = "Global iteration limit exceeded"
                break
            current = next_node

        total_elapsed = (time.perf_counter() - start) * 1000
        return ExecutionResult(
            task_id=task_id,
            graph_name=graph.name,
            success=not error,
            output=result_output,
            trace=trace,
            total_elapsed_ms=total_elapsed,
            iterations_total=iterations,
            human_interventions=human_count,
            error=error,
        )

    def _run_node(self, node: Node, context: dict, graph: AgentGraph) -> tuple[Any, str, str]:
        if node.type == NodeType.RULE:
            return self._run_rule(node, context)
        if node.type == NodeType.LLM:
            return self._run_llm(node, context, graph)
        if node.type == NodeType.TOOL:
            return self._run_tool(node, context)
        if node.type == NodeType.HUMAN:
            return self._run_human(node, context)
        return None, "noop", ""

    def _run_rule(self, node: Node, context: dict) -> tuple[Any, str, str]:
        rule_fn = node.config.get("rule_fn")
        if rule_fn:
            result = rule_fn(context)
            return result, "rule_matched", str(result)
        return {"matched": True}, "rule_default", ""

    def _run_llm(self, node: Node, context: dict, graph: AgentGraph) -> tuple[Any, str, str]:
        memory_sources = graph.memory_sources(node.id)
        memory_context = {}
        for src in memory_sources:
            if src.id in context.get("memory", {}):
                memory_context[src.id] = context["memory"][src.id]

        prompt_key = node.config.get("prompt_key", node.id)
        iteration = context.get("_iteration", 0)

        output = self.llm.generate(
            prompt_key=prompt_key,
            context=context,
            memory=memory_context,
            config=node.config,
        )
        detail = f"memory_sources={[s.id for s in memory_sources]}" if memory_sources else ""
        return output, "llm_inference", detail

    def _run_tool(self, node: Node, context: dict) -> tuple[Any, str, str]:
        tool_fn = node.config.get("tool_fn")
        if tool_fn:
            result = tool_fn(context)
            return result, "tool_executed", str(result)
        return {"executed": True}, "tool_default", ""

    def _run_human(self, node: Node, context: dict) -> tuple[Any, str, str]:
        auto_fn = node.config.get("auto_fn")
        if auto_fn:
            return auto_fn(context), "human_auto_approved", "simulated"
        return {"approved": True}, "human_approved", "simulated"

    def _route(
        self, graph: AgentGraph, current: Node,
        output: Any, context: dict,
        visited: dict[str, int],
    ) -> Node | None:
        successors = graph.successors(current.id)
        if not successors:
            back = graph.back_edges(current.id)
            if back:
                iteration = visited.get(current.id, 0)
                if iteration < current.max_iterations:
                    should_continue = output.get("iterate", False) if isinstance(output, dict) else False
                    if should_continue:
                        return back[0][1]
            return None

        conditional = [(e, n) for e, n in successors if e.type == EdgeType.CONDITIONAL]
        if conditional:
            for edge, node in conditional:
                condition_met = self._check_condition(edge.condition, output, context)
                if condition_met:
                    return node
            back = graph.back_edges(current.id)
            if back:
                iteration = visited.get(current.id, 0)
                if iteration < current.max_iterations:
                    return back[0][1]
            return None

        sequential = [(e, n) for e, n in successors if e.type == EdgeType.SEQUENTIAL]
        if sequential:
            return sequential[0][1]

        return None

    def _check_condition(self, condition: str, output: Any, context: dict) -> bool:
        if not condition:
            return True
        if isinstance(output, dict):
            if condition in output:
                return bool(output[condition])
            if "route" in output:
                return output["route"] == condition
            if "done" in output and condition == "done":
                return output["done"]
            if "accepted" in output and condition == "accepted":
                return output["accepted"]
        return False
