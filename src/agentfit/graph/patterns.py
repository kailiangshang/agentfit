"""Topology pattern factories.

These factories construct AgentGraph instances for the canonical agent
topologies discovered in our framework survey:

  LangGraph     — Prompt Chaining, Routing, Parallelization,
                  Orchestrator-Worker, Evaluator-Optimizer, ReAct
  AutoGen       — Group Chat, Sequential Chat, Constrained Transitions
  CrewAI        — Sequential Crew, Hierarchical Crew, Flow DAG
  MetaGPT       — SOP Pipeline (subscribe-based relay)
  OpenAI SDK    — Handoff Chain
  Anthropic     — Orchestrator-Worker with parallel subagents
  DSPy          — ChainOfThought with self-refine

All boil down to: DAG backbone + local SCCs + optional memory deps.
"""

from __future__ import annotations

from agentfit.graph.model import (
    AgentGraph,
    Edge,
    EdgeType,
    Node,
    NodeType,
)


def linear_pipeline(
    name: str = "linear-pipeline",
    stages: list[tuple[str, str]] | None = None,
) -> AgentGraph:
    stages = stages or [("rule_classify", "Rule: classify"), ("rule_decide", "Rule: decide")]
    g = AgentGraph(name=name)
    prev = None
    for idx, (nid, label) in enumerate(stages):
        nt = NodeType.RULE if idx == 0 and "rule" in nid else NodeType.RULE
        g.add_node(Node(id=nid, type=nt, label=label))
        if prev:
            g.add_edge(Edge(source=prev, target=nid))
        prev = nid
    return g


def react_loop(
    name: str = "react-loop",
    max_iterations: int = 3,
) -> AgentGraph:
    g = AgentGraph(name=name)
    g.add_node(Node(
        id="llm_reason", type=NodeType.LLM,
        label="LLM: reason + decide action",
        max_iterations=max_iterations,
    ))
    g.add_node(Node(
        id="tool_exec", type=NodeType.TOOL,
        label="Tool: execute action",
    ))
    g.add_node(Node(
        id="llm_synthesize", type=NodeType.LLM,
        label="LLM: synthesize final answer",
    ))
    g.add_edge(Edge("llm_reason", "tool_exec", EdgeType.SEQUENTIAL, label="has_tool_call"))
    g.add_edge(Edge("tool_exec", "llm_reason", EdgeType.BACK, label="iterate"))
    g.add_edge(Edge("llm_reason", "llm_synthesize", EdgeType.CONDITIONAL, condition="done"))
    return g


def evaluator_optimizer(
    name: str = "evaluator-optimizer",
    max_iterations: int = 3,
) -> AgentGraph:
    g = AgentGraph(name=name)
    g.add_node(Node(id="generator", type=NodeType.LLM, label="LLM: generate output"))
    g.add_node(Node(id="evaluator", type=NodeType.LLM, label="LLM: evaluate quality"))
    g.add_node(Node(id="refiner", type=NodeType.LLM, label="LLM: refine based on feedback", max_iterations=max_iterations))
    g.add_edge(Edge("generator", "evaluator"))
    g.add_edge(Edge("evaluator", "refiner", EdgeType.CONDITIONAL, condition="needs_improvement"))
    g.add_edge(Edge("refiner", "evaluator", EdgeType.BACK, label="re-evaluate"))
    g.add_edge(Edge("evaluator", "", EdgeType.CONDITIONAL, condition="accepted"))
    return g


def orchestrator_worker(
    name: str = "orchestrator-worker",
    worker_count: int = 3,
) -> AgentGraph:
    g = AgentGraph(name=name)
    g.add_node(Node(id="orchestrator", type=NodeType.LLM, label="LLM: decompose and assign"))
    g.add_node(Node(id="synthesizer", type=NodeType.LLM, label="LLM: synthesize results"))
    for i in range(worker_count):
        wid = f"worker_{i}"
        g.add_node(Node(id=wid, type=NodeType.LLM, label=f"LLM: worker {i} subtask"))
        g.add_edge(Edge("orchestrator", wid, EdgeType.CONDITIONAL, condition=f"task_{i}"))
        g.add_edge(Edge(wid, "synthesizer"))
    return g


def router_branch(
    name: str = "router-branch",
    branches: list[str] | None = None,
) -> AgentGraph:
    branches = branches or ["simple", "moderate", "complex"]
    g = AgentGraph(name=name)
    g.add_node(Node(id="router", type=NodeType.LLM, label="LLM: classify and route"))
    for br in branches:
        bid = f"handler_{br}"
        g.add_node(Node(
            id=bid,
            type=NodeType.RULE if br == "simple" else NodeType.LLM,
            label=f"{'Rule' if br == 'simple' else 'LLM'}: handle {br} case",
        ))
        g.add_edge(Edge("router", bid, EdgeType.CONDITIONAL, condition=f"is_{br}"))
    return g


def handoff_chain(
    name: str = "handoff-chain",
    agents: list[str] | None = None,
) -> AgentGraph:
    agents = agents or ["triage", "specialist", "reviewer"]
    g = AgentGraph(name=name)
    prev = None
    for aid in agents:
        g.add_node(Node(id=aid, type=NodeType.LLM, label=f"Agent: {aid}"))
        if prev:
            g.add_edge(Edge(prev, aid, EdgeType.CONDITIONAL, condition=f"handoff_to_{aid}"))
        prev = aid
    return g


def debate_scc(
    name: str = "debate-scc",
    rounds: int = 2,
) -> AgentGraph:
    g = AgentGraph(name=name)
    g.add_node(Node(id="proposer", type=NodeType.LLM, label="LLM: propose solution", max_iterations=rounds))
    g.add_node(Node(id="critic", type=NodeType.LLM, label="LLM: critique proposal", max_iterations=rounds))
    g.add_node(Node(id="judge", type=NodeType.LLM, label="LLM: final judgment"))
    g.add_edge(Edge("proposer", "critic"))
    g.add_edge(Edge("critic", "proposer", EdgeType.BACK, label="revise"))
    g.add_edge(Edge("critic", "judge", EdgeType.CONDITIONAL, condition="consensus_reached"))
    return g


def hierarchical_team(
    name: str = "hierarchical-team",
    worker_count: int = 3,
) -> AgentGraph:
    g = AgentGraph(name=name)
    g.add_node(Node(id="manager", type=NodeType.LLM, label="Manager: plan and assign"))
    g.add_node(Node(id="team_leader", type=NodeType.LLM, label="Team Leader: coordinate workers"))
    g.add_node(Node(id="quality_gate", type=NodeType.HUMAN, label="Human: review result"))
    g.add_edge(Edge("manager", "team_leader"))
    for i in range(worker_count):
        wid = f"worker_{i}"
        g.add_node(Node(id=wid, type=NodeType.LLM, label=f"Worker {i}: execute task"))
        g.add_edge(Edge("team_leader", wid, EdgeType.CONDITIONAL, condition=f"assign_{i}"))
        g.add_edge(Edge(wid, "team_leader", EdgeType.BACK, label="report_back"))
    g.add_edge(Edge("team_leader", "quality_gate", EdgeType.CONDITIONAL, condition="all_done"))
    return g


def sop_pipeline(
    name: str = "sop-pipeline",
    roles: list[str] | None = None,
) -> AgentGraph:
    roles = roles or ["analyst", "designer", "implementer", "tester"]
    g = AgentGraph(name=name)
    prev = None
    for role in roles:
        rid = f"role_{role}"
        g.add_node(Node(id=rid, type=NodeType.LLM, label=f"Role: {role}"))
        if prev:
            g.add_edge(Edge(prev, rid))
        prev = rid
    return g


PATTERN_REGISTRY = {
    "linear": linear_pipeline,
    "react": react_loop,
    "evaluator_optimizer": evaluator_optimizer,
    "orchestrator_worker": orchestrator_worker,
    "router": router_branch,
    "handoff": handoff_chain,
    "debate": debate_scc,
    "hierarchical": hierarchical_team,
    "sop": sop_pipeline,
}
