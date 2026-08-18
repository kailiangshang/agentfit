"""Content-bound G3 decisions shared by core and platform bridges."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models.evidence import CandidateManifest
from ..models.sample import canonical_hash
from ..models.solution import solution_from_dict
from ..store.run_store import RunStore


EVIDENCE_ROOT_FILES = {
    "run.json", "samples.json", "sample_sets.json", "task_samples.json",
    "source_observations.json", "capability_inventory.json", "objective.json",
    "acceptance.json", "source_results.json",
}
EVIDENCE_DIRECTORIES = {
    "epochs", "loss_traces", "messages", "solution_versions", "traces", "episodes",
    "candidate_manifests", "training_traces", "training_episodes",
}
SIGNING_KEY_ENV = "AGENTFIT_G3_SIGNING_KEY"
KEY_ID_ENV = "AGENTFIT_G3_KEY_ID"


def _signing_material() -> tuple[bytes, str] | None:
    raw = os.environ.get(SIGNING_KEY_ENV)
    if raw is None:
        return None
    key = raw.encode("utf-8")
    if len(key) < 32:
        raise ValueError(f"{SIGNING_KEY_ENV} must contain at least 32 bytes")
    key_id = os.environ.get(KEY_ID_ENV, "").strip()
    if not key_id:
        raise ValueError(f"{KEY_ID_ENV} is required with the G3 signing key")
    return key, key_id


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
    objective_ref = summary.get("objective_ref")
    acceptance_ref = summary.get("acceptance_ref")
    acceptance_met = summary.get("acceptance_met")
    if (
        not isinstance(candidate_ref, str)
        or not isinstance(final_version, int)
        or not isinstance(evaluations, dict)
        or not isinstance(objective_ref, str)
        or not isinstance(acceptance_ref, str)
        or not isinstance(acceptance_met, bool)
    ):
        raise ValueError("complete final evaluation evidence is required before G3")
    if decision.approved and not acceptance_met:
        raise ValueError("G3 cannot approve a failed objective acceptance")
    signing = _signing_material() if decision.approved else None
    if decision.approved and signing is None:
        raise ValueError(f"approved G3 requires external {SIGNING_KEY_ENV}")
    payload = {
        "approved": bool(decision.approved),
        "reviewer": str(decision.reviewer),
        "reason": str(decision.reason),
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "candidate_ref": candidate_ref,
        "final_solution_version": final_version,
        "evidence_hash": final_evidence_hash(store),
        "review_conditions": list(decision.conditions),
        "objective_ref": objective_ref,
        "acceptance_ref": acceptance_ref,
        "acceptance_met": acceptance_met,
        "acceptance_failures": list(summary.get("acceptance_failures") or []),
        "evidence_scope": {
            "candidate_frozen": summary.get("candidate_frozen") is True,
            "evaluation_by_purpose": evaluations,
        },
        "signature_algorithm": "hmac-sha256" if signing else "unsigned",
        "key_id": signing[1] if signing else "",
    }
    payload["decision_hash"] = canonical_hash(payload)
    payload["signature"] = (
        hmac.new(signing[0], payload["decision_hash"].encode("ascii"), hashlib.sha256).hexdigest()
        if signing else ""
    )
    return payload


def verify_delivery_decision(store: RunStore, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or store.load_json("summary.json")
    try:
        decision = store.load_json("delivery_decision.json")
    except (OSError, ValueError) as exc:
        raise ValueError("delivery decision artifact is missing") from exc
    if not isinstance(decision, dict):
        raise ValueError("delivery decision artifact is invalid")
    payload = {
        key: value for key, value in decision.items()
        if key not in {"decision_hash", "signature"}
    }
    if decision.get("decision_hash") != canonical_hash(payload):
        raise ValueError("delivery decision hash mismatch")
    algorithm = decision.get("signature_algorithm")
    if algorithm == "hmac-sha256":
        signing = _signing_material()
        if signing is None:
            raise ValueError(f"delivery decision signature requires {SIGNING_KEY_ENV}")
        if decision.get("key_id") != signing[1]:
            raise ValueError("delivery decision signature key id mismatch")
        expected_signature = hmac.new(
            signing[0], decision["decision_hash"].encode("ascii"), hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(str(decision.get("signature", "")), expected_signature):
            raise ValueError("delivery decision signature mismatch")
    elif algorithm != "unsigned" or decision.get("approved"):
        raise ValueError("approved delivery decision signature is missing")
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
    for key in (
        "objective_ref", "acceptance_ref", "acceptance_met", "acceptance_failures",
    ):
        if decision.get(key) != summary.get(key):
            raise ValueError(f"delivery decision acceptance mismatch: {key}")
    if decision.get("approved") and decision.get("acceptance_met") is not True:
        raise ValueError("approved delivery decision requires objective acceptance")
    evidence_scope = decision.get("evidence_scope") or {}
    if evidence_scope.get("candidate_frozen") is not True:
        raise ValueError("delivery decision requires a frozen candidate")
    if evidence_scope.get("evaluation_by_purpose") != summary.get("evaluation_by_purpose"):
        raise ValueError("delivery decision evaluation mismatch")
    if decision.get("review_conditions", []) != summary.get("delivery_conditions", []):
        raise ValueError("delivery decision review conditions mismatch")
    if not decision.get("reviewer") or not decision.get("reason") or not decision.get("decided_at"):
        raise ValueError("delivery decision review evidence is incomplete")

    version = decision["final_solution_version"]
    snapshot = store.load_json(f"solution_versions/v{version:03d}.json")["solution"]
    candidate_ref = decision.get("candidate_ref")
    try:
        manifest_data = store.load_json(f"candidate_manifests/{candidate_ref}.json")
        manifest = CandidateManifest(
            candidate_id=manifest_data["candidate_id"],
            kind=manifest_data["kind"],
            specification=manifest_data["specification"],
            provenance_complete=manifest_data["provenance_complete"],
            content_hash=manifest_data["content_hash"],
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("delivery decision candidate manifest is invalid") from exc
    if (
        manifest.candidate_ref != candidate_ref
        or manifest.specification.get("solution_ref")
        != canonical_hash(solution_from_dict(snapshot))
    ):
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
