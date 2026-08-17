"""Explicit Human Gate decisions; production defaults to blocking."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class GateType(str, Enum):
    G0 = "G0"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"


@dataclass(frozen=True)
class ReviewRequest:
    gate: GateType
    subject: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewDecision:
    approved: bool
    reason: str
    reviewer: str
    conditions: tuple[str, ...] = ()


class HumanGatePolicy(Protocol):
    def review(self, request: ReviewRequest) -> ReviewDecision: ...  # noqa: E704


class BlockingHumanGate:
    """Safe production default: no mutation or delivery without a decision."""

    def review(self, request: ReviewRequest) -> ReviewDecision:
        return ReviewDecision(
            approved=False,
            reason=f"explicit human approval required for {request.gate.value}",
            reviewer="unassigned",
        )
