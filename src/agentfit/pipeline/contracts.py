"""Pipeline contracts: structured artifacts that flow between stages.

These are the three core ML-methodology carriers:

  TrialSpec       — dataset + train/test split + acceptance criteria + complexity budget
  CandidateCard   — architecture + complexity declaration + rationale + expected fit
  EvaluationReport — per-candidate scores + overfit diagnosis + comparison + recommendation

Methodology is welded into the Schema: if test_split is missing, the state
machine won't let you enter Trial; if rationale is missing, the CandidateCard
is incomplete.  No structure = no progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass
class TaskExample:
    task_id: str
    input: dict[str, Any]
    expected_output: Any
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class TrialSpec:
    scenario_name: str
    dataset: list[TaskExample]
    train_split: list[str]
    test_split: list[str]
    acceptance_criteria: dict[str, float]
    complexity_budget: float
    fault_plan: list[dict[str, Any]] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors = []
        if not self.dataset:
            errors.append("dataset is empty")
        all_ids = {t.task_id for t in self.dataset}
        train_overlap = set(self.train_split) & set(self.test_split)
        if train_overlap:
            errors.append(f"train/test overlap: {train_overlap}")
        missing_train = set(self.train_split) - all_ids
        if missing_train:
            errors.append(f"train ids not in dataset: {missing_train}")
        missing_test = set(self.test_split) - all_ids
        if missing_test:
            errors.append(f"test ids not in dataset: {missing_test}")
        if "accuracy" not in self.acceptance_criteria:
            errors.append("acceptance_criteria missing 'accuracy'")
        if self.complexity_budget <= 0:
            errors.append("complexity_budget must be positive")
        return errors


class CandidateType(Enum):
    NO_AGENT = "no-agent"
    SINGLE_AGENT = "single-agent"
    MULTI_AGENT = "multi-agent"


@dataclass
class CandidateCard:
    candidate_id: str
    pattern_name: str
    candidate_type: CandidateType
    complexity: float
    rationale: str
    expected_fit: str
    expected_failure: str = ""
    graph_description: str = ""

    def validate(self) -> list[str]:
        errors = []
        if not self.rationale:
            errors.append("rationale is empty (no justification for complexity)")
        if not self.expected_fit:
            errors.append("expected_fit is empty")
        return errors


@dataclass
class CandidateScore:
    candidate_id: str
    train_accuracy: float
    test_accuracy: float
    latency_ms: float
    token_cost: int
    human_interventions: int
    stability: float
    overfit_signal: float
    per_task_results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accuracy_gap(self) -> float:
        return self.train_accuracy - self.test_accuracy


@dataclass
class EvaluationReport:
    scenario_name: str
    candidate_scores: list[CandidateScore]
    diagnosis: dict[str, str] = field(default_factory=dict)
    recommendation: str = ""
    recommendation_type: str = ""
    comparison_table: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)

    def build_comparison(self) -> list[dict[str, Any]]:
        rows = []
        for score in sorted(self.candidate_scores, key=lambda s: s.test_accuracy, reverse=True):
            rows.append({
                "candidate": score.candidate_id,
                "train_acc": f"{score.train_accuracy:.1%}",
                "test_acc": f"{score.test_accuracy:.1%}",
                "overfit": f"{score.overfit_signal:.1%}",
                "latency_ms": f"{score.latency_ms:.0f}",
                "tokens": score.token_cost,
                "human": score.human_interventions,
                "stability": f"{score.stability:.1%}",
            })
        self.comparison_table = rows
        return rows

    def make_recommendation(self, acceptance: dict[str, float]) -> None:
        threshold = acceptance.get("accuracy", 0.8)
        max_overfit = acceptance.get("max_overfit", 0.15)
        max_cost = acceptance.get("max_tokens", 100000)

        passing = [
            s for s in self.candidate_scores
            if s.test_accuracy >= threshold
            and s.overfit_signal <= max_overfit
            and s.token_cost <= max_cost
        ]

        if not passing:
            all_fail_accuracy = all(s.test_accuracy < threshold * 0.6 for s in self.candidate_scores)
            if all_fail_accuracy:
                self.recommendation = (
                    f"All candidates scored below {threshold * 0.6:.0%} on test set. "
                    "Insufficient capability for automation. REJECT."
                )
                self.recommendation_type = "reject"
            else:
                self.recommendation = (
                    f"Candidates showed some capability but none met acceptance threshold "
                    f"(accuracy >= {threshold:.0%}, overfit <= {max_overfit:.0%}). "
                    "Recommend partial automation with human review, or collect more data."
                )
                self.recommendation_type = "partial"
            return

        passing.sort(key=lambda s: (s.token_cost, s.human_interventions))
        best = passing[0]
        self.recommendation = (
            f"Select '{best.candidate_id}' — minimal sufficient candidate. "
            f"Test accuracy {best.test_accuracy:.1%}, "
            f"overfit {best.overfit_signal:.1%}, "
            f"cost {best.token_cost} tokens."
        )
        self.recommendation_type = "deploy"
