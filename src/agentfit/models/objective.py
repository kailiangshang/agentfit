"""Content-addressed user objectives and deterministic acceptance results."""
from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from typing import Any

from .manifest import SampleSetPurpose
from .sample import canonical_hash


_HASH = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class PurposeAcceptance:
    """Hard acceptance thresholds for one immutable sample-set purpose."""

    purpose: SampleSetPurpose
    min_pass_rate: float
    max_errors: int
    max_cost_usd: float
    max_risk_events: int

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, SampleSetPurpose):
            raise TypeError("purpose must be a SampleSetPurpose")
        if not math.isfinite(self.min_pass_rate) or not 0 <= self.min_pass_rate <= 1:
            raise ValueError("min_pass_rate must be between 0 and 1")
        if not isinstance(self.max_errors, int) or self.max_errors < 0:
            raise ValueError("max_errors must be a non-negative integer")
        if not math.isfinite(self.max_cost_usd) or self.max_cost_usd < 0:
            raise ValueError("max_cost_usd must be non-negative")
        if not isinstance(self.max_risk_events, int) or self.max_risk_events < 0:
            raise ValueError("max_risk_events must be a non-negative integer")


@dataclass(frozen=True)
class ObjectiveSpec:
    """Human-defined objective; one criterion is required for every purpose."""

    criteria: tuple[PurposeAcceptance, ...]
    max_total_evaluation_cost_usd: float
    content_hash: str

    @classmethod
    def create(cls, *, criteria: tuple[PurposeAcceptance, ...] | list[PurposeAcceptance],
               max_total_evaluation_cost_usd: float) -> "ObjectiveSpec":
        criteria = tuple(copy.deepcopy(tuple(criteria)))
        body = {
            "criteria": criteria,
            "max_total_evaluation_cost_usd": max_total_evaluation_cost_usd,
        }
        return cls(**body, content_hash=canonical_hash(body))

    def __post_init__(self) -> None:
        purposes = [item.purpose for item in self.criteria]
        if (
            len(self.criteria) != 4
            or set(purposes) != set(SampleSetPurpose)
            or len(set(purposes)) != 4
        ):
            raise ValueError("four required purpose criteria must be present exactly once")
        if (
            not math.isfinite(self.max_total_evaluation_cost_usd)
            or self.max_total_evaluation_cost_usd < 0
        ):
            raise ValueError("max_total_evaluation_cost_usd must be non-negative")
        expected = canonical_hash({
            "criteria": self.criteria,
            "max_total_evaluation_cost_usd": self.max_total_evaluation_cost_usd,
        })
        if self.content_hash != expected:
            raise ValueError("objective content_hash does not match content")

    def by_purpose(self, purpose: SampleSetPurpose) -> PurposeAcceptance:
        return next(item for item in self.criteria if item.purpose == purpose)


def _criteria_from_dict(items: Any) -> tuple[PurposeAcceptance, ...]:
    if not isinstance(items, list):
        raise ValueError("objective criteria must be a list")
    return tuple(
        PurposeAcceptance(
            purpose=SampleSetPurpose(item["purpose"]),
            min_pass_rate=float(item["min_pass_rate"]),
            max_errors=item["max_errors"],
            max_cost_usd=float(item["max_cost_usd"]),
            max_risk_events=item["max_risk_events"],
        )
        for item in items
    )


def objective_spec_from_material(data: dict[str, Any]) -> ObjectiveSpec:
    """Create an objective from a mutable material-bundle declaration."""
    if not isinstance(data, dict):
        raise TypeError("objective must be an object")
    return ObjectiveSpec.create(
        criteria=_criteria_from_dict(data.get("criteria")),
        max_total_evaluation_cost_usd=float(
            data["max_total_evaluation_cost_usd"]
        ),
    )


def objective_spec_from_dict(data: dict[str, Any]) -> ObjectiveSpec:
    """Restore and verify a persisted objective."""
    if not isinstance(data, dict):
        raise TypeError("objective must be an object")
    content_hash = data.get("content_hash")
    if not isinstance(content_hash, str):
        raise ValueError("objective content_hash is required")
    return ObjectiveSpec(
        criteria=_criteria_from_dict(data.get("criteria")),
        max_total_evaluation_cost_usd=float(
            data["max_total_evaluation_cost_usd"]
        ),
        content_hash=content_hash,
    )


@dataclass(frozen=True)
class AcceptanceResult:
    """Deterministic verdict recomputed from persisted per-purpose metrics."""

    objective_ref: str
    evaluation_by_purpose: dict[str, dict[str, Any]]
    criteria_met: dict[str, bool]
    met: bool
    failures: tuple[str, ...]
    content_hash: str

    def __post_init__(self) -> None:
        required = {purpose.value for purpose in SampleSetPurpose}
        if _HASH.fullmatch(self.objective_ref) is None:
            raise ValueError("objective_ref must be a sha256")
        if set(self.evaluation_by_purpose) != required or set(self.criteria_met) != required:
            raise ValueError("acceptance result requires all four purposes")
        if self.met != (not self.failures):
            raise ValueError("acceptance met flag does not match failures")
        expected = canonical_hash({
            "objective_ref": self.objective_ref,
            "evaluation_by_purpose": self.evaluation_by_purpose,
            "criteria_met": self.criteria_met,
            "met": self.met,
            "failures": self.failures,
        })
        if self.content_hash != expected:
            raise ValueError("acceptance result content_hash does not match content")


def acceptance_result_from_dict(data: dict[str, Any]) -> AcceptanceResult:
    """Restore and verify a persisted acceptance result."""
    if not isinstance(data, dict):
        raise TypeError("acceptance result must be an object")
    return AcceptanceResult(
        objective_ref=data["objective_ref"],
        evaluation_by_purpose=copy.deepcopy(data["evaluation_by_purpose"]),
        criteria_met=dict(data["criteria_met"]),
        met=data["met"],
        failures=tuple(data.get("failures", ())),
        content_hash=data["content_hash"],
    )


def _validated_metrics(purpose: SampleSetPurpose,
                       metrics: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(metrics, dict):
        raise TypeError(f"{purpose.value} metrics must be an object")
    try:
        total = metrics["total"]
        passed = metrics["passed"]
        failed = metrics["failed"]
        errors = metrics["errors"]
        pass_rate = metrics["pass_rate"]
        cost_usd = metrics["cost_usd"]
        risk_events = metrics["risk_events"]
    except KeyError as exc:
        raise ValueError(f"{purpose.value} metrics missing {exc.args[0]}") from exc
    if not all(isinstance(value, int) and value >= 0
               for value in (total, passed, failed, errors, risk_events)):
        raise ValueError(f"{purpose.value} counts must be non-negative integers")
    if total <= 0 or passed + failed + errors != total:
        raise ValueError(f"{purpose.value} outcome counts do not match total")
    expected_rate = passed / total
    if not isinstance(pass_rate, (int, float)) or not math.isfinite(pass_rate):
        raise ValueError(f"{purpose.value} pass_rate is invalid")
    if abs(float(pass_rate) - expected_rate) > 1e-12:
        raise ValueError(f"{purpose.value} pass_rate does not match counts")
    if not isinstance(cost_usd, (int, float)) or not math.isfinite(cost_usd) or cost_usd < 0:
        raise ValueError(f"{purpose.value} cost_usd is invalid")
    cost_observed = metrics.get("cost_observed", True)
    if type(cost_observed) is not bool:
        raise ValueError(f"{purpose.value} cost_observed must be a boolean")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": float(pass_rate),
        "cost_usd": float(cost_usd),
        "cost_observed": cost_observed,
        "risk_events": risk_events,
    }


def evaluate_acceptance(objective: ObjectiveSpec,
                        evaluation_by_purpose: dict[str, dict[str, Any]]) -> AcceptanceResult:
    """Evaluate every hard threshold; one failed purpose rejects the whole result."""
    required = {purpose.value for purpose in SampleSetPurpose}
    if set(evaluation_by_purpose) != required:
        raise ValueError("evaluation requires all four purposes")
    normalized: dict[str, dict[str, Any]] = {}
    criteria_met: dict[str, bool] = {}
    failures: list[str] = []
    for purpose in SampleSetPurpose:
        metrics = _validated_metrics(purpose, evaluation_by_purpose[purpose.value])
        normalized[purpose.value] = metrics
        criterion = objective.by_purpose(purpose)
        purpose_failures = []
        if metrics["pass_rate"] < criterion.min_pass_rate:
            purpose_failures.append(
                f"{purpose.value}.pass_rate {metrics['pass_rate']:.4f} < "
                f"{criterion.min_pass_rate:.4f}"
            )
        if metrics["errors"] > criterion.max_errors:
            purpose_failures.append(
                f"{purpose.value}.errors {metrics['errors']} > {criterion.max_errors}"
            )
        if not metrics["cost_observed"]:
            purpose_failures.append(f"{purpose.value}.cost_usd unavailable")
        elif metrics["cost_usd"] > criterion.max_cost_usd:
            purpose_failures.append(
                f"{purpose.value}.cost_usd {metrics['cost_usd']:.4f} > "
                f"{criterion.max_cost_usd:.4f}"
            )
        if metrics["risk_events"] > criterion.max_risk_events:
            purpose_failures.append(
                f"{purpose.value}.risk_events {metrics['risk_events']} > "
                f"{criterion.max_risk_events}"
            )
        criteria_met[purpose.value] = not purpose_failures
        failures.extend(purpose_failures)
    total_cost = sum(item["cost_usd"] for item in normalized.values())
    if total_cost > objective.max_total_evaluation_cost_usd:
        failures.append(
            f"total_evaluation_cost_usd {total_cost:.4f} > "
            f"{objective.max_total_evaluation_cost_usd:.4f}"
        )
    body = {
        "objective_ref": objective.content_hash,
        "evaluation_by_purpose": normalized,
        "criteria_met": criteria_met,
        "met": not failures,
        "failures": tuple(failures),
    }
    return AcceptanceResult(**body, content_hash=canonical_hash(body))


def summarize_episodes(
    episodes: list[Any],
    *,
    cost_observed: bool = True,
) -> dict[str, Any]:
    """Summarize one purpose or external batch from persisted Episode semantics."""
    results = [
        episode.result if hasattr(episode, "result") else episode["result"]
        for episode in episodes
    ]
    costs = [
        episode.cost_usd if hasattr(episode, "cost_usd")
        else float(episode.get("cost_usd", 0))
        for episode in episodes
    ]
    risk_events = [
        episode.risk_events if hasattr(episode, "risk_events")
        else int(episode.get("risk_events", 0))
        for episode in episodes
    ]
    total = len(results)
    passed = results.count("PASS")
    return {
        "total": total,
        "passed": passed,
        "failed": results.count("FAIL"),
        "errors": results.count("ERROR"),
        "pass_rate": passed / total if total else None,
        "cost_usd": round(sum(costs), 4),
        "cost_observed": cost_observed,
        "risk_events": sum(risk_events),
    }
