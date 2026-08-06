"""AgentArchitect — Agent system architect.

Responsibilities: generate candidate solutions (no-agent, single-agent,
multi-agent) following baseline-first discipline. Search the graph
topology space from minimal to complex.

Does NOT: deploy candidate teams, evaluate own solutions.

The architect uses ML methodology as thinking discipline:
  1. Always generate a baseline (minimal complexity) candidate first
  2. Only increase complexity when there's evidence of underfitting
  3. Each candidate has a rationale for its complexity level
  4. Each candidate declares expected fit and expected failure
"""

from __future__ import annotations

from typing import Any

from agentfit.graph.model import AgentGraph, Edge, EdgeType, Node, NodeType
from agentfit.graph.patterns import (
    debate_scc,
    evaluator_optimizer,
    handoff_chain,
    hierarchical_team,
    linear_pipeline,
    orchestrator_worker,
    react_loop,
    router_branch,
    sop_pipeline,
)
from agentfit.pipeline.contracts import CandidateCard, CandidateType


class AgentArchitect:
    name = "AgentArchitect"
    role = "Agent System Architect"

    def design_candidates(
        self,
        facts: list[dict],
        boundary: dict,
        scenario_config: dict[str, Any],
        complexity_budget: float,
    ) -> list[CandidateCard]:
        candidate_configs = scenario_config.get("candidate_configs", [])
        cards = []

        for cfg in candidate_configs:
            graph = self._build_graph(cfg)
            card = CandidateCard(
                candidate_id=cfg["id"],
                pattern_name=cfg["pattern"],
                candidate_type=CandidateType(cfg["type"]),
                complexity=graph.complexity(),
                rationale=cfg["rationale"],
                expected_fit=cfg["expected_fit"],
                expected_failure=cfg.get("expected_failure", ""),
                graph_description=graph.describe(),
            )
            cards.append(card)

        cards.sort(key=lambda c: c.complexity)
        return cards

    def _build_graph(self, cfg: dict) -> AgentGraph:
        pattern = cfg["pattern"]
        params = cfg.get("params", {})

        if pattern == "linear":
            return linear_pipeline(cfg["id"], params.get("stages"))
        if pattern == "router":
            return router_branch(cfg["id"], params.get("branches"))
        if pattern == "react":
            return react_loop(cfg["id"], params.get("max_iterations", 3))
        if pattern == "evaluator_optimizer":
            return evaluator_optimizer(cfg["id"], params.get("max_iterations", 3))
        if pattern == "orchestrator_worker":
            return orchestrator_worker(cfg["id"], params.get("worker_count", 3))
        if pattern == "handoff":
            return handoff_chain(cfg["id"], params.get("agents"))
        if pattern == "debate":
            return debate_scc(cfg["id"], params.get("rounds", 2))
        if pattern == "hierarchical":
            return hierarchical_team(cfg["id"], params.get("worker_count", 3))
        if pattern == "sop":
            return sop_pipeline(cfg["id"], params.get("roles"))
        if pattern == "custom":
            return self._build_custom_graph(cfg["id"], params)
        return linear_pipeline(cfg["id"])

    def _build_custom_graph(self, name: str, params: dict) -> AgentGraph:
        g = AgentGraph(name=name)
        for node_def in params.get("nodes", []):
            g.add_node(Node(
                id=node_def["id"],
                type=NodeType(node_def["type"]),
                label=node_def.get("label", node_def["id"]),
                max_iterations=node_def.get("max_iterations", 1),
                config=node_def.get("config", {}),
            ))
        for edge_def in params.get("edges", []):
            g.add_edge(Edge(
                source=edge_def["source"],
                target=edge_def["target"],
                type=EdgeType(edge_def.get("type", "sequential")),
                condition=edge_def.get("condition", ""),
                label=edge_def.get("label", ""),
            ))
        return g
