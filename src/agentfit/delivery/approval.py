"""Content-bound G3 decisions shared by core and platform bridges."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models.sample import canonical_hash
from ..models.solution import solution_from_dict
from ..store.run_store import RunStore


EVIDENCE_ROOT_FILES = {"run.json", "samples.json", "sample_sets.json"}
EVIDENCE_DIRECTORIES = {
    "epochs", "loss_traces", "messages", "solution_versions", "traces", "episodes",
}


def final_evidence_hash(store: RunStore) -> str:
    """Bind G3 to the immutable evidence present before the decision."""
    files: dict[str, str] = {}
    for path in sorted(item for item in store.root.rglob("*") if item.is_file()):
        relative = path.relative_to(store.root)
        if relative.as_posix() in EVIDENCE_ROOT_FILES or relative.parts[0] in EVIDENCE_DIRECTORIES:
            files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not files:
        raise ValueError("final evaluation evidence is missing")
    return canonical_hash(files)


def create_delivery_decision(store: RunStore, decision: Any, summary: dict[str, Any]) -> dict[str, Any]:
    candidate_ref = summary.get("candidate_ref")
    final_version = summary.get("final_solution_version")
    evaluations = summary.get("evaluation_by_purpose")
    if not isinstance(candidate_ref, str) or not isinstance(final_version, int) or not isinstance(evaluations, dict):
        raise ValueError("complete final evaluation evidence is required before G3")
    payload = {
        "approved": bool(decision.approved),
        "reviewer": str(decision.reviewer),
        "reason": str(decision.reason),
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "candidate_ref": candidate_ref,
        "final_solution_version": final_version,
        "evidence_hash": final_evidence_hash(store),
        "conditions": {
            "candidate_frozen": summary.get("candidate_frozen") is True,
            "evaluation_by_purpose": evaluations,
        },
    }
    payload["decision_hash"] = canonical_hash(payload)
    return payload


def verify_delivery_decision(store: RunStore, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or store.load_json("summary.json")
    try:
        decision = store.load_json("delivery_decision.json")
    except (OSError, ValueError) as exc:
        raise ValueError("delivery decision artifact is missing") from exc
    if not isinstance(decision, dict):
        raise ValueError("delivery decision artifact is invalid")
    payload = {key: value for key, value in decision.items() if key != "decision_hash"}
    if decision.get("decision_hash") != canonical_hash(payload):
        raise ValueError("delivery decision hash mismatch")
    if decision.get("evidence_hash") != final_evidence_hash(store):
        raise ValueError("delivery decision evidence hash mismatch")
    summary_keys = {
        "approved": "delivery_approved",
        "reviewer": "delivery_reviewer",
        "reason": "delivery_review_reason",
    }
    for key, summary_key in summary_keys.items():
        if summary.get(summary_key) != decision.get(key):
            raise ValueError(f"delivery decision summary mismatch: {key}")
    if summary.get("delivery_decision_hash") != decision.get("decision_hash"):
        raise ValueError("delivery decision summary mismatch: decision_hash")
    if decision.get("candidate_ref") != summary.get("candidate_ref"):
        raise ValueError("delivery decision candidate mismatch")
    if decision.get("final_solution_version") != summary.get("final_solution_version"):
        raise ValueError("delivery decision solution version mismatch")
    conditions = decision.get("conditions") or {}
    if conditions.get("candidate_frozen") is not True:
        raise ValueError("delivery decision requires a frozen candidate")
    if conditions.get("evaluation_by_purpose") != summary.get("evaluation_by_purpose"):
        raise ValueError("delivery decision evaluation mismatch")
    if not decision.get("reviewer") or not decision.get("reason") or not decision.get("decided_at"):
        raise ValueError("delivery decision review evidence is incomplete")

    version = decision["final_solution_version"]
    snapshot = store.load_json(f"solution_versions/v{version:03d}.json")["solution"]
    if canonical_hash(solution_from_dict(snapshot)) != decision.get("candidate_ref"):
        raise ValueError("delivery decision candidate snapshot mismatch")
    return decision


def assert_delivery_approved(store: RunStore, version: int | None = None) -> dict[str, Any]:
    summary = store.load_json("summary.json")
    if not summary.get("delivery_approved"):
        raise ValueError("G3 delivery approval is required before export")
    decision = verify_delivery_decision(store, summary)
    approved_version = decision["final_solution_version"]
    if version is not None and version != approved_version:
        raise ValueError("only the G3-approved solution version can be exported")
    return decision
