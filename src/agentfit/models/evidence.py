"""Content-addressed candidate and external-evaluation evidence contracts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from .sample import SampleRef, canonical_hash


HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _require_hash(value: str, field_name: str, *, allow_genesis: bool = False) -> None:
    if allow_genesis and value == "GENESIS":
        return
    if HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a 64-character lowercase sha256")


@dataclass(frozen=True)
class CandidateManifest:
    """Persisted identity of the exact candidate presented to an evaluator."""

    candidate_id: str
    kind: str
    specification: dict[str, Any]
    provenance_complete: bool
    content_hash: str

    @classmethod
    def create(cls, *, candidate_id: str, kind: str,
               specification: dict[str, Any],
               provenance_complete: bool) -> "CandidateManifest":
        body = {
            "candidate_id": candidate_id,
            "kind": kind,
            "specification": dict(specification),
            "provenance_complete": provenance_complete,
        }
        return cls(**body, content_hash=canonical_hash(body))

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.kind:
            raise ValueError("candidate_id and kind are required")
        if not isinstance(self.provenance_complete, bool):
            raise TypeError("provenance_complete must be a boolean")
        if not isinstance(self.specification, dict):
            raise TypeError("candidate specification must be a mapping")
        _require_hash(self.content_hash, "content_hash")
        expected = canonical_hash({
            "candidate_id": self.candidate_id,
            "kind": self.kind,
            "specification": self.specification,
            "provenance_complete": self.provenance_complete,
        })
        if self.content_hash != expected:
            raise ValueError("candidate manifest content_hash does not match content")

    @property
    def candidate_ref(self) -> str:
        return self.content_hash

    @classmethod
    def for_solution(cls, solution: Any) -> "CandidateManifest":
        """Identify four-layer semantics without embedding runtime implementation choices."""
        solution_ref = canonical_hash(solution)
        return cls.create(
            candidate_id=solution_ref,
            kind="agentfit.solution",
            specification={"solution_ref": solution_ref, "solution": asdict(solution)},
            provenance_complete=True,
        )


@dataclass(frozen=True)
class ExternalEvidenceRecord:
    """One raw source record bound to its normalized evaluation evidence."""

    source_index: int
    source_record_hash: str
    candidate_ref: str
    sample_ref: SampleRef
    run_index: int
    trace_ref: str
    result: str
    cost_usd: float
    trace_hash: str
    previous_hash: str
    content_hash: str

    @classmethod
    def create(cls, *, source_index: int, source_record_hash: str,
               candidate_ref: str, sample_ref: SampleRef, run_index: int,
               trace_ref: str, result: str, cost_usd: float,
               trace_hash: str, previous_hash: str) -> "ExternalEvidenceRecord":
        body = {
            "source_index": source_index,
            "source_record_hash": source_record_hash,
            "candidate_ref": candidate_ref,
            "sample_ref": sample_ref,
            "run_index": run_index,
            "trace_ref": trace_ref,
            "result": result,
            "cost_usd": cost_usd,
            "trace_hash": trace_hash,
            "previous_hash": previous_hash,
        }
        return cls(**body, content_hash=canonical_hash(body))

    def __post_init__(self) -> None:
        if self.source_index < 0 or self.run_index < 0:
            raise ValueError("source_index and run_index must be non-negative")
        _require_hash(self.source_record_hash, "source_record_hash")
        _require_hash(self.candidate_ref, "candidate_ref")
        _require_hash(self.trace_hash, "trace_hash")
        _require_hash(self.previous_hash, "previous_hash", allow_genesis=True)
        _require_hash(self.content_hash, "content_hash")
        if not self.trace_ref:
            raise ValueError("trace_ref is required")
        if self.result not in {"PASS", "FAIL", "ERROR"}:
            raise ValueError("result must be PASS, FAIL or ERROR")
        if self.cost_usd < 0:
            raise ValueError("cost_usd must be non-negative")
        expected = canonical_hash({
            "source_index": self.source_index,
            "source_record_hash": self.source_record_hash,
            "candidate_ref": self.candidate_ref,
            "sample_ref": self.sample_ref,
            "run_index": self.run_index,
            "trace_ref": self.trace_ref,
            "result": self.result,
            "cost_usd": self.cost_usd,
            "trace_hash": self.trace_hash,
            "previous_hash": self.previous_hash,
        })
        if self.content_hash != expected:
            raise ValueError("external evidence content_hash does not match content")
