"""对象层数据结构：被训练的四层方案。规范见 docs/architecture.md。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SolidAtom:
    """L1 semantic atom; runtime bindings are resolved outside the core."""
    id: str                        # "toggle_roaming"
    type: str                      # "read" | "write" | "human" | "notify"
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class HumanGate:
    condition: str                 # "amount > 100"
    reviewer: str                  # "finance_team"
    on_timeout: str = "block"      # "block" | "escalate" | "default_approve"


@dataclass
class CapabilityTool:
    """L2 工具：对 L1 原子的安全封装/组合/口径统一/送审路由。"""
    id: str                        # "safe_toggle_roaming"
    wraps: list[str]               # L1 原子 ID（存在依赖锚点）
    description: str = ""
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    human_gate: HumanGate | None = None
    aggregation_logic: str | None = None


@dataclass
class ChainStep:
    tool: str                      # L2 工具 ID
    params: dict[str, Any] = field(default_factory=dict)
    on_failure: str = "abort"      # "abort" | "human" | "skip"


@dataclass
class Knowledge:
    """L3 知识：skill / routing_rule / chain / threshold / experience 五类。"""
    id: str
    type: str                      # 五类之一
    description: str = ""
    # routing_rule
    condition: str | None = None   # 特征表达式，如 "abroad AND roaming_off"
    dispatches_to: str | None = None   # L2 工具 ID（调度≠调用）
    # chain
    steps: list[ChainStep] | None = None
    # threshold
    value: float | None = None
    # experience
    lesson: str | None = None
    superseded: bool = False
    evidence_sample_ids: list[str] = field(default_factory=list)


@dataclass
class Agent:
    """L4 Agent（对象层被训练方案的组成单元）。"""
    id: str
    role: str = "single"           # "single" | "diagnostic" | "repair" | ...
    uses: list[str] = field(default_factory=list)   # 依赖的 L3 知识 ID


@dataclass
class TopologyEdge:
    from_agent: str
    to_agent: str
    payload_type: str = "L3_decision"


@dataclass
class Topology:
    """L4 拓扑：Agent 架构 + 协作边 + 人工介入位置。"""
    agents: list[Agent] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)
    human_gate_positions: list[str] = field(default_factory=list)   # agent id 列表
    trigger_mode: str = "passive"


@dataclass
class Solution:
    """被训练方案：四层内容的集合 + 训练状态。"""
    version: int = 0
    L1_atoms: list[SolidAtom] = field(default_factory=list)
    L2_tools: list[CapabilityTool] = field(default_factory=list)
    L3_knowledge: list[Knowledge] = field(default_factory=list)
    L4_topology: Topology = field(default_factory=Topology)
    lambda_values: dict[str, float] = field(default_factory=lambda: {"L1": 0.1, "L2": 0.2, "L3": 0.3, "L4": 0.4})

    # ---- 便捷查找（O(1) 视图，不持有额外状态） ----
    def atom(self, atom_id: str) -> SolidAtom | None:
        return next((a for a in self.L1_atoms if a.id == atom_id), None)

    def tool(self, tool_id: str) -> CapabilityTool | None:
        return next((t for t in self.L2_tools if t.id == tool_id), None)

    def knowledge(self, kid: str) -> Knowledge | None:
        return next((k for k in self.L3_knowledge if k.id == kid), None)

    def routing_rules(self) -> list[Knowledge]:
        return [k for k in self.L3_knowledge if k.type == "routing_rule" and not k.superseded]

    def experiences(self) -> list[Knowledge]:
        return [k for k in self.L3_knowledge if k.type == "experience" and not k.superseded]


def solution_from_dict(data: dict[str, Any]) -> Solution:
    """Restore a canonical Solution snapshot from RunStore JSON."""
    topology_data = data.get("L4_topology") or {}
    topology = Topology(
        agents=[Agent(**item) for item in topology_data.get("agents", [])],
        edges=[TopologyEdge(**item) for item in topology_data.get("edges", [])],
        human_gate_positions=list(topology_data.get("human_gate_positions", [])),
        trigger_mode=topology_data.get("trigger_mode", "passive"),
    )
    tools = []
    for item in data.get("L2_tools", []):
        payload = dict(item)
        gate = payload.get("human_gate")
        payload["human_gate"] = HumanGate(**gate) if gate else None
        tools.append(CapabilityTool(**payload))
    knowledge = []
    for item in data.get("L3_knowledge", []):
        payload = dict(item)
        steps = payload.get("steps")
        payload["steps"] = [ChainStep(**step) for step in steps] if steps else None
        knowledge.append(Knowledge(**payload))
    return Solution(
        version=int(data.get("version", 0)),
        L1_atoms=[SolidAtom(**item) for item in data.get("L1_atoms", [])],
        L2_tools=tools,
        L3_knowledge=knowledge,
        L4_topology=topology,
        lambda_values=dict(data.get("lambda_values") or {"L1": 0.1, "L2": 0.2, "L3": 0.3, "L4": 0.4}),
    )
