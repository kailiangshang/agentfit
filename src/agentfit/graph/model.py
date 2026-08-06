"""AgentFit unified graph model.

Every candidate solution — whether a rule script, a single LLM node, or a
multi-agent system — is represented as an AgentGraph.  The graph consists of
typed nodes connected by typed edges.  The overall structure is a DAG
(ensuring termination) with local SCCs (bounded iteration loops) and
optional memory-dependency edges (cross-node state read/write).

This unification lets AgentArchitect search a single space when designing
candidates, and lets ValidationEngineer compare fundamentally different
architectures on the same task set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class NodeType(Enum):
    LLM = "llm"
    TOOL = "tool"
    RULE = "rule"
    HUMAN = "human"


class EdgeType(Enum):
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    BACK = "back"
    MEMORY = "memory"


@dataclass
class Node:
    id: str
    type: NodeType
    label: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 1

    def complexity_weight(self) -> float:
        base = {
            NodeType.RULE: 1.0,
            NodeType.TOOL: 2.0,
            NodeType.LLM: 5.0,
            NodeType.HUMAN: 8.0,
        }[self.type]
        iter_factor = max(1, self.max_iterations)
        return base * iter_factor


@dataclass
class Edge:
    source: str
    target: str
    type: EdgeType = EdgeType.SEQUENTIAL
    condition: str = ""
    label: str = ""


@dataclass
class AgentGraph:
    name: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def successors(self, node_id: str) -> list[tuple[Edge, Node]]:
        result = []
        for edge in self.edges:
            if edge.source == node_id and edge.type != EdgeType.BACK:
                target = self.get_node(edge.target)
                if target:
                    result.append((edge, target))
        return result

    def back_edges(self, node_id: str) -> list[tuple[Edge, Node]]:
        result = []
        for edge in self.edges:
            if edge.source == node_id and edge.type == EdgeType.BACK:
                target = self.get_node(edge.target)
                if target:
                    result.append((edge, target))
        return result

    def memory_sources(self, node_id: str) -> list[Node]:
        result = []
        for edge in self.edges:
            if edge.target == node_id and edge.type == EdgeType.MEMORY:
                source = self.get_node(edge.source)
                if source:
                    result.append(source)
        return result

    def entry_node(self) -> Node | None:
        targets = {e.target for e in self.edges if e.type != EdgeType.MEMORY}
        for node in self.nodes:
            if node.id not in targets:
                return node
        return self.nodes[0] if self.nodes else None

    def complexity(self) -> float:
        node_sum = sum(n.complexity_weight() for n in self.nodes)
        scc_count = sum(
            1 for e in self.edges if e.type == EdgeType.BACK
        )
        memory_count = sum(
            1 for e in self.edges if e.type == EdgeType.MEMORY
        )
        conditional_count = sum(
            1 for e in self.edges if e.type == EdgeType.CONDITIONAL
        )
        return node_sum + scc_count * 3.0 + memory_count * 2.0 + conditional_count * 1.0

    def complexity_label(self) -> str:
        c = self.complexity()
        if c <= 5:
            return "minimal"
        if c <= 15:
            return "low"
        if c <= 35:
            return "moderate"
        return "high"

    def has_scc(self) -> bool:
        return any(e.type == EdgeType.BACK for e in self.edges)

    def has_memory(self) -> bool:
        return any(e.type == EdgeType.MEMORY for e in self.edges)

    def node_count(self) -> int:
        return len(self.nodes)

    def describe(self) -> str:
        lines = [f"Graph '{self.name}' — complexity={self.complexity():.1f} ({self.complexity_label()})"]
        lines.append(f"  Nodes ({len(self.nodes)}):")
        for n in self.nodes:
            extra = f" max_iter={n.max_iterations}" if n.max_iterations > 1 else ""
            lines.append(f"    [{n.type.value:6s}] {n.id}: {n.label}{extra}")
        lines.append(f"  Edges ({len(self.edges)}):")
        for e in self.edges:
            cond = f" ({e.condition})" if e.condition else ""
            lines.append(f"    {e.source} --{e.type.value}{cond}--> {e.target}")
        return "\n".join(lines)
