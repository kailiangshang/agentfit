"""Stable contracts that keep model, retrieval and tool runtimes out of core."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class EvidenceReference:
    uri: str
    content_hash: str
    media_type: str = "application/json"


@dataclass(frozen=True)
class CognitiveRequest:
    slot: str
    payload: dict[str, Any]
    instructions: str = ""
    evidence_refs: tuple[EvidenceReference, ...] = ()
    budget_usd: float | None = None


@dataclass(frozen=True)
class CognitiveResult:
    output: Any
    evidence_refs: tuple[EvidenceReference, ...] = ()
    model_ref: str = ""
    cost_usd: float = 0.0
    trace_ref: str = ""


@runtime_checkable
class CognitiveAdapter(Protocol):
    def invoke(self, request: CognitiveRequest) -> CognitiveResult: ...


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 10


@dataclass(frozen=True)
class RetrievedEvidence:
    reference: EvidenceReference
    content: Any
    score: float


@runtime_checkable
class RetrievalAdapter(Protocol):
    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedEvidence, ...]: ...


@dataclass(frozen=True)
class SandboxRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class SandboxResult:
    status: str
    output: Any = None
    error: str | None = None
    evidence_ref: EvidenceReference | None = None
    cost_usd: float = 0.0


@runtime_checkable
class SandboxAdapter(Protocol):
    def execute(self, request: SandboxRequest) -> SandboxResult: ...


@runtime_checkable
class ExternalEvidenceProjector(Protocol):
    """Bridge callback that deterministically projects raw source evidence."""

    def __call__(self, source_results: dict[str, Any], candidate_ref: str) -> Any: ...
