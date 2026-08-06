"""GovernanceAuditor — Governance & audit engineer.

Responsibilities: independently verify results, safety boundaries, and
delivery conditions. Read-only access to evidence.

Does NOT: modify candidate solutions or run records.

ML methodology checks:
  1. Overfit detection: train vs test gap
  2. Baseline-first verification: was baseline generated before complex?
  3. Complexity-value tradeoff: does added complexity bring significant lift?
  4. Stability check: consistent performance across difficulty levels
"""

from __future__ import annotations

from typing import Any

from agentfit.pipeline.contracts import CandidateCard, CandidateScore, EvaluationReport


class GovernanceAuditor:
    name = "GovernanceAuditor"
    role = "Governance & Audit Engineer"

    def audit(
        self,
        candidates: list[CandidateCard],
        scores: dict[str, CandidateScore],
        acceptance_criteria: dict[str, float],
        scenario_name: str,
    ) -> EvaluationReport:
        report = EvaluationReport(
            scenario_name=scenario_name,
            candidate_scores=list(scores.values()),
        )

        for card in candidates:
            score = scores.get(card.candidate_id)
            if score is None:
                continue
            diagnosis = self._diagnose(card, score, candidates, scores)
            report.diagnosis[card.candidate_id] = diagnosis

        report.build_comparison()
        report.make_recommendation(acceptance_criteria)

        self._verify_baseline_first(candidates, report)
        self._check_complexity_value(candidates, scores, report)

        return report

    def _diagnose(
        self,
        card: CandidateCard,
        score: CandidateScore,
        all_candidates: list[CandidateCard],
        all_scores: dict[str, CandidateScore],
    ) -> str:
        parts = []

        if score.overfit_signal > 0.15:
            parts.append(f"OVERFIT: train {score.train_accuracy:.1%} vs test {score.test_accuracy:.1%} (gap {score.overfit_signal:.1%})")
        elif score.overfit_signal > 0.08:
            parts.append(f"MILD OVERFIT: gap {score.overfit_signal:.1%}")
        else:
            parts.append(f"WELL GENERALIZED: gap {score.overfit_signal:.1%}")

        threshold = 0.80
        if score.test_accuracy >= threshold:
            parts.append("PASS: meets accuracy threshold")
        elif score.test_accuracy >= threshold * 0.75:
            parts.append("MARGINAL: below threshold but promising")
        else:
            parts.append("UNDERFIT: significantly below threshold")

        if card.complexity > 15 and score.test_accuracy < threshold:
            parts.append("INEFFICIENT: high complexity without payoff")
        elif card.complexity <= 5 and score.test_accuracy >= threshold:
            parts.append("EFFICIENT: minimal complexity meets threshold")

        if score.stability < 0.9:
            parts.append(f"UNSTABLE: stability {score.stability:.1%}")

        if score.human_interventions > 0:
            parts.append(f"HUMAN-IN-THE-LOOP: {score.human_interventions} interventions")

        return "; ".join(parts)

    def _verify_baseline_first(
        self,
        candidates: list[CandidateCard],
        report: EvaluationReport,
    ) -> None:
        if not candidates:
            return
        sorted_by_complexity = sorted(candidates, key=lambda c: c.complexity)
        baseline = sorted_by_complexity[0]
        is_no_agent = baseline.candidate_type.value == "no-agent"
        if not is_no_agent and baseline.complexity > 5:
            report.evidence_refs.append(
                "WARNING: baseline candidate is not minimal — baseline-first discipline violated"
            )

    def _check_complexity_value(
        self,
        candidates: list[CandidateCard],
        scores: dict[str, CandidateScore],
        report: EvaluationReport,
    ) -> None:
        sorted_cards = sorted(candidates, key=lambda c: c.complexity)
        for i in range(1, len(sorted_cards)):
            prev = sorted_cards[i - 1]
            curr = sorted_cards[i]
            prev_score = scores.get(prev.candidate_id)
            curr_score = scores.get(curr.candidate_id)
            if prev_score and curr_score:
                lift = curr_score.test_accuracy - prev_score.test_accuracy
                complexity_increase = curr.complexity - prev.complexity
                if lift < 0.05 and complexity_increase > 5:
                    report.evidence_refs.append(
                        f"DIMINISHING RETURNS: {curr.candidate_id} adds {complexity_increase:.0f} complexity "
                        f"for only {lift:.1%} accuracy lift over {prev.candidate_id}"
                    )
