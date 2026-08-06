"""Pipeline orchestrator.

Drives the AgentFit meta-team through the 8-stage pipeline:
Intake → Discover → Architect → Approve → Trial → Audit → Deliver → Learn

Coordinates the 5 agents, enforces state-machine gates, and produces
structured evidence at every stage.
"""

from __future__ import annotations

from typing import Any

from agentfit.agents.agent_architect import AgentArchitect
from agentfit.agents.business_engineer import BusinessEngineer
from agentfit.agents.engagement_lead import EngagementLead
from agentfit.agents.governance_auditor import GovernanceAuditor
from agentfit.agents.validation_engineer import ValidationEngineer
from agentfit.graph.executor import GraphExecutor
from agentfit.pipeline.contracts import (
    CandidateCard,
    CandidateScore,
    CandidateType,
    EvaluationReport,
    TaskExample,
    TrialSpec,
)
from agentfit.pipeline.dossier import ProjectDossier
from agentfit.pipeline.states import PipelineState, check_gate


class PipelineOrchestrator:
    def __init__(self, llm_simulator):
        self.llm = llm_simulator
        self.engagement_lead = EngagementLead()
        self.business_engineer = BusinessEngineer()
        self.architect = AgentArchitect()
        self.validator = ValidationEngineer(GraphExecutor(llm_simulator))
        self.auditor = GovernanceAuditor()

    def run(
        self,
        scenario_name: str,
        materials: list[dict],
        problem: str,
        scenario_config: dict[str, Any],
        graph_builder: Any = None,
    ) -> dict[str, Any]:
        dossier = ProjectDossier(
            project_id=f"{scenario_name}-001",
            domain=scenario_config.get("domain", "general"),
        )
        state = PipelineState.INTAKE
        gate_log: list[dict] = []
        trial_results: dict[str, CandidateScore] = {}
        report: EvaluationReport | None = None
        candidates: list[CandidateCard] = []
        trial_spec: TrialSpec | None = None
        graphs: dict[str, Any] = {}

        def _gate(target: PipelineState, ctx: dict) -> bool:
            result = check_gate(state, target, ctx)
            gate_log.append({
                "from": state.value,
                "to": target.value,
                "allowed": result.allowed,
                "reason": result.reason,
            })
            return result.allowed

        # 1. INTAKE
        intake_result = self.engagement_lead.intake(materials, problem, dossier)
        if _gate(PipelineState.DISCOVER, {}):
            state = PipelineState.DISCOVER

        # 2. DISCOVER
        discover_result = self.business_engineer.discover(
            materials, problem, scenario_config, dossier,
        )
        dataset_raw = dossier.get("materials")
        dataset = self._reconstruct_dataset(dossier)

        spec_data = self.business_engineer.create_trial_spec(dataset, scenario_config)
        trial_spec = TrialSpec(
            scenario_name=scenario_name,
            dataset=dataset,
            train_split=spec_data["train_split"],
            test_split=spec_data["test_split"],
            acceptance_criteria=spec_data["acceptance_criteria"],
            complexity_budget=spec_data["complexity_budget"],
            fault_plan=spec_data["fault_plan"],
        )
        dossier.write("discover", self.business_engineer.name, "write_trial_spec", {
            "trial_spec": {
                "train_split": trial_spec.train_split,
                "test_split": trial_spec.test_split,
                "acceptance_criteria": trial_spec.acceptance_criteria,
                "complexity_budget": trial_spec.complexity_budget,
            },
        })

        if _gate(PipelineState.ARCHITECT, {"dataset": dataset}):
            state = PipelineState.ARCHITECT

        # 3. ARCHITECT
        facts = dossier.get("facts") or []
        boundary = dossier.get("automation_boundary") or {}
        candidates = self.architect.design_candidates(
            facts, boundary, scenario_config, trial_spec.complexity_budget,
        )

        if graph_builder:
            graphs = graph_builder(candidates, scenario_config)
        else:
            graphs = self._default_graph_builder(candidates, scenario_config)

        candidate_data = [
            {
                "candidate_id": c.candidate_id,
                "pattern": c.pattern_name,
                "type": c.candidate_type.value,
                "complexity": c.complexity,
                "rationale": c.rationale,
            }
            for c in candidates
        ]
        dossier.write("architect", self.architect.name, "write_candidates", {
            "candidates": candidate_data,
        })

        if _gate(PipelineState.APPROVE, {"candidates": candidates}):
            state = PipelineState.APPROVE

        # 4. APPROVE
        approved = self.engagement_lead.approve_trial(trial_spec, dossier)

        if _gate(PipelineState.TRIAL, {"trial_spec": trial_spec}):
            state = PipelineState.TRIAL

        # 5. TRIAL
        trial_results = self.validator.run_trial(
            candidates, graphs, trial_spec, scenario_config,
        )
        dossier.write("trial", self.validator.name, "write_trial_results", {
            "results": {
                k: {
                    "train_accuracy": v.train_accuracy,
                    "test_accuracy": v.test_accuracy,
                    "overfit_signal": v.overfit_signal,
                    "token_cost": v.token_cost,
                    "human_interventions": v.human_interventions,
                    "stability": v.stability,
                }
                for k, v in trial_results.items()
            },
        })

        if _gate(PipelineState.AUDIT, {"trial_results": trial_results, "candidates": candidates}):
            state = PipelineState.AUDIT

        # 6. AUDIT
        report = self.auditor.audit(
            candidates, trial_results,
            trial_spec.acceptance_criteria, scenario_name,
        )
        dossier.write("audit", self.auditor.name, "write_evaluation", {
            "report": {
                "recommendation": report.recommendation,
                "recommendation_type": report.recommendation_type,
                "diagnosis": report.diagnosis,
                "comparison_table": report.comparison_table,
            },
        })

        if _gate(PipelineState.DELIVER, {"candidates": candidates}):
            state = PipelineState.DELIVER

        # 7. DELIVER
        decision = self.engagement_lead.confirm_delivery(report.recommendation, dossier)

        if _gate(PipelineState.LEARN, {}):
            state = PipelineState.LEARN

        # 8. LEARN
        assets = self._extract_assets(candidates, trial_results, report, dossier.domain)
        dossier.write("learn", self.auditor.name, "write_assets", {"assets": assets})

        return {
            "scenario_name": scenario_name,
            "dossier_summary": dossier.summary(),
            "candidates": candidate_data,
            "trial_results": {
                k: {
                    "train_accuracy": v.train_accuracy,
                    "test_accuracy": v.test_accuracy,
                    "overfit_signal": v.overfit_signal,
                    "latency_ms": v.latency_ms,
                    "token_cost": v.token_cost,
                    "human_interventions": v.human_interventions,
                    "stability": v.stability,
                }
                for k, v in trial_results.items()
            },
            "evaluation_report": {
                "recommendation": report.recommendation,
                "recommendation_type": report.recommendation_type,
                "diagnosis": report.diagnosis,
                "comparison_table": report.comparison_table,
                "evidence_refs": report.evidence_refs,
            },
            "gate_log": gate_log,
            "assets": assets,
            "final_state": state.value,
        }

    def _reconstruct_dataset(self, dossier: ProjectDossier) -> list[TaskExample]:
        for entry in reversed(dossier.log):
            if entry.action == "write_dataset":
                return [
                    TaskExample(
                        task_id=d["task_id"],
                        input=d["input"],
                        expected_output=d["expected_output"],
                        difficulty=d.get("difficulty", "medium"),
                        tags=d.get("tags", []),
                    )
                    for d in entry.data.get("dataset", [])
                ]
        return []

    def _default_graph_builder(self, candidates: list[CandidateCard], config: dict) -> dict:
        from agentfit.graph.model import AgentGraph, Edge, EdgeType, Node, NodeType
        from agentfit.graph.patterns import PATTERN_REGISTRY

        graphs = {}
        for card in candidates:
            cfg = next(
                (c for c in config.get("candidate_configs", []) if c["id"] == card.candidate_id),
                None,
            )
            if cfg is None:
                continue

            pattern_fn = PATTERN_REGISTRY.get(cfg["pattern"])
            if pattern_fn:
                params = cfg.get("params", {})
                if cfg["pattern"] == "linear":
                    graph = pattern_fn(card.candidate_id, params.get("stages"))
                elif cfg["pattern"] == "router":
                    graph = pattern_fn(card.candidate_id, params.get("branches"))
                elif cfg["pattern"] in ("react", "evaluator_optimizer"):
                    graph = pattern_fn(card.candidate_id, params.get("max_iterations", 3))
                elif cfg["pattern"] == "orchestrator_worker":
                    graph = pattern_fn(card.candidate_id, params.get("worker_count", 3))
                elif cfg["pattern"] == "debate":
                    graph = pattern_fn(card.candidate_id, params.get("rounds", 2))
                elif cfg["pattern"] == "hierarchical":
                    graph = pattern_fn(card.candidate_id, params.get("worker_count", 3))
                elif cfg["pattern"] == "handoff":
                    graph = pattern_fn(card.candidate_id, params.get("agents"))
                elif cfg["pattern"] == "sop":
                    graph = pattern_fn(card.candidate_id, params.get("roles"))
                else:
                    graph = pattern_fn(card.candidate_id)
                self._attach_node_configs(graph, cfg, config)
                graphs[card.candidate_id] = graph
        return graphs

    def _attach_node_configs(self, graph: AgentGraph, candidate_cfg: dict, scenario_config: dict) -> None:
        node_configs = candidate_cfg.get("node_configs", {})
        evaluators = scenario_config.get("evaluators", {})
        for node in graph.nodes:
            if node.id in node_configs:
                node.config.update(node_configs[node.id])
            if node.id in evaluators:
                node.config["evaluator_key"] = node.id

    def _extract_assets(
        self,
        candidates: list[CandidateCard],
        scores: dict[str, CandidateScore],
        report: EvaluationReport,
        domain: str,
    ) -> list[dict]:
        assets = []
        for card in candidates:
            score = scores.get(card.candidate_id)
            if score and score.test_accuracy >= 0.75 and score.overfit_signal <= 0.15:
                assets.append({
                    "type": "candidate_template",
                    "domain": domain,
                    "pattern": card.pattern_name,
                    "candidate_id": card.candidate_id,
                    "complexity": card.complexity,
                    "test_accuracy": score.test_accuracy,
                    "applicability": card.expected_fit,
                    "limitations": card.expected_failure,
                })
        return assets
