"""Canonical sample and evaluation identities.

SourceObservation, TaskSample and Episode are intentionally distinct.  Active
objects keep stable names; immutable evidence is addressed by content hashes.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .loss import Expected, Sample


HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical evidence cannot contain NaN or Infinity")
        return value
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical evidence mapping keys must be strings")
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_jsonable(item) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ),
        )
    raise TypeError(f"unsupported canonical evidence type: {type(value).__name__}")


def canonical_hash(value: Any) -> str:
    """Hash canonical JSON so mapping order never changes evidence identity."""
    payload = json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require_hash(value: str, field_name: str) -> None:
    if not HASH_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a 64-character lowercase sha256")


@dataclass(frozen=True)
class SampleRef:
    sample_id: str
    content_hash: str

    def __post_init__(self) -> None:
        if not self.sample_id:
            raise ValueError("sample_id is required")
        _require_hash(self.content_hash, "content_hash")


@dataclass(frozen=True)
class SourceObservation:
    id: str
    kind: str
    content: Any
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, id: str, kind: str, content: Any,
               metadata: dict[str, Any] | None = None) -> "SourceObservation":
        metadata = dict(metadata or {})
        return cls(id, kind, content, canonical_hash({"kind": kind, "content": content}), metadata)

    def __post_init__(self) -> None:
        if not self.id or not self.kind:
            raise ValueError("observation id and kind are required")
        _require_hash(self.content_hash, "content_hash")
        expected = canonical_hash({"kind": self.kind, "content": self.content})
        if self.content_hash != expected:
            raise ValueError("observation content_hash does not match content")


@dataclass(frozen=True)
class TaskSample:
    id: str
    observation_refs: tuple[str, ...]
    input_data: dict[str, Any]
    expected: "Expected"
    evaluator: str = "exact"
    constraints: dict[str, Any] = field(default_factory=dict)
    requires_human: bool = False
    complexity: str = "simple"
    legacy_group: str | None = None

    @property
    def content_hash(self) -> str:
        return canonical_hash({
            "id": self.id,
            "observation_refs": self.observation_refs,
            "input_data": self.input_data,
            "expected": self.expected,
            "evaluator": self.evaluator,
            "constraints": self.constraints,
            "requires_human": self.requires_human,
            "complexity": self.complexity,
        })

    @property
    def ref(self) -> SampleRef:
        return SampleRef(self.id, self.content_hash)


def task_sample_from_legacy(sample: "Sample",
                            observation_refs: tuple[str, ...] = ()) -> TaskSample:
    """Compatibility boundary for the existing simulator Sample model."""
    return TaskSample(
        id=sample.id,
        observation_refs=tuple(observation_refs),
        input_data=dict(sample.features),
        expected=sample.expected,
        requires_human=sample.requires_human,
        complexity=sample.complexity,
        legacy_group=sample.group,
    )


@dataclass(frozen=True)
class EvaluationIdentity:
    candidate_ref: str
    sample_ref: SampleRef
    run_index: int

    def __post_init__(self) -> None:
        _require_hash(self.candidate_ref, "candidate_ref")
        if self.run_index < 0:
            raise ValueError("run_index must be non-negative")

    @property
    def key(self) -> str:
        return f"{self.candidate_ref}.{self.sample_ref.content_hash}.{self.run_index}"


@dataclass(frozen=True)
class Episode:
    identity: EvaluationIdentity
    trace_ref: str
    result: str
    cost_usd: float
    evidence_hash: str
    status: str = "completed"

    def __post_init__(self) -> None:
        if not self.trace_ref:
            raise ValueError("trace_ref is required")
        if self.result not in {"PASS", "FAIL", "ERROR"}:
            raise ValueError("result must be PASS, FAIL or ERROR")
        if self.cost_usd < 0:
            raise ValueError("cost_usd must be non-negative")
        _require_hash(self.evidence_hash, "evidence_hash")
