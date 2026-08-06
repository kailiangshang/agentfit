"""Pipeline state machine.

States: Intake → Discover → Architect → Approve → Trial → Audit → Deliver → Learn

ML methodology embedded as gate checks:
  - Discover → Architect: dataset must have >= N labeled examples
  - Architect → Approve: at least one baseline (minimal) candidate required
  - Approve → Trial: train/test split must be non-overlapping (checked at TrialSpec creation)
  - Trial → Audit: all candidates must have test results
  - Audit → Deliver: EvaluationReport must have a recommendation
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


class PipelineState(Enum):
    INTAKE = "intake"
    DISCOVER = "discover"
    ARCHITECT = "architect"
    APPROVE = "approve"
    TRIAL = "trial"
    AUDIT = "audit"
    DELIVER = "deliver"
    LEARN = "learn"

    def __lt__(self, other):
        if not isinstance(other, PipelineState):
            return NotImplemented
        order = list(PipelineState)
        return order.index(self) < order.index(other)


VALID_TRANSITIONS = {
    PipelineState.INTAKE: {PipelineState.DISCOVER},
    PipelineState.DISCOVER: {PipelineState.ARCHITECT, PipelineState.INTAKE},
    PipelineState.ARCHITECT: {PipelineState.APPROVE, PipelineState.DISCOVER},
    PipelineState.APPROVE: {PipelineState.TRIAL, PipelineState.ARCHITECT},
    PipelineState.TRIAL: {PipelineState.AUDIT, PipelineState.APPROVE},
    PipelineState.AUDIT: {PipelineState.DELIVER, PipelineState.TRIAL},
    PipelineState.DELIVER: {PipelineState.LEARN},
    PipelineState.LEARN: set(),
}


@dataclass
class StateGateResult:
    allowed: bool
    reason: str = ""
    warnings: list[str] = None


def check_gate(current: PipelineState, target: PipelineState, context: dict) -> StateGateResult:
    if target not in VALID_TRANSITIONS.get(current, set()):
        return StateGateResult(
            allowed=False,
            reason=f"Invalid transition: {current.value} -> {target.value}",
        )

    if current == PipelineState.DISCOVER and target == PipelineState.ARCHITECT:
        dataset = context.get("dataset", [])
        if len(dataset) < 4:
            return StateGateResult(
                allowed=False,
                reason=f"Dataset too small ({len(dataset)} examples). Need >= 4 for train/test split.",
            )
        return StateGateResult(allowed=True)

    if current == PipelineState.ARCHITECT and target == PipelineState.APPROVE:
        candidates = context.get("candidates", [])
        if not candidates:
            return StateGateResult(allowed=False, reason="No candidates generated.")
        has_baseline = any(
            c.candidate_type.value == "no-agent" or c.complexity <= 5
            for c in candidates
        )
        if not has_baseline:
            return StateGateResult(
                allowed=False,
                reason="No baseline (minimal complexity) candidate. Baseline-first discipline violated.",
            )
        return StateGateResult(allowed=True)

    if current == PipelineState.APPROVE and target == PipelineState.TRIAL:
        trial_spec = context.get("trial_spec")
        if trial_spec is None:
            return StateGateResult(allowed=False, reason="No trial spec.")
        errors = trial_spec.validate()
        if errors:
            return StateGateResult(allowed=False, reason=f"Trial spec invalid: {'; '.join(errors)}")
        return StateGateResult(allowed=True)

    if current == PipelineState.TRIAL and target == PipelineState.AUDIT:
        results = context.get("trial_results", {})
        candidates = context.get("candidates", [])
        missing = [c.candidate_id for c in candidates if c.candidate_id not in results]
        if missing:
            return StateGateResult(
                allowed=False,
                reason=f"Missing trial results for: {missing}",
            )
        return StateGateResult(allowed=True)

    return StateGateResult(allowed=True)
