"""Immutable sample-set manifests, Human Freeze and access policies."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .sample import SampleRef, canonical_hash


class SampleSetPurpose(str, Enum):
    ADAPTATION = "adaptation"
    VALIDATION = "validation"
    SEALED_HOLDOUT = "sealed_holdout"
    STRESS_AND_FAILURE = "stress_and_failure"


@dataclass(frozen=True)
class AccessPolicy:
    readers: tuple[str, ...]
    allows_updates: bool = False
    requires_candidate_freeze: bool = False


@dataclass(frozen=True)
class FreezeDecision:
    reviewer: str
    approved: bool
    decided_at: str
    reason: str

    def __post_init__(self) -> None:
        if not self.reviewer or not self.decided_at or not self.reason:
            raise ValueError("complete Human Freeze evidence is required")


def default_access_policy(purpose: SampleSetPurpose) -> AccessPolicy:
    policies = {
        SampleSetPurpose.ADAPTATION: AccessPolicy(
            ("steward", "architect", "orchestrator", "validator"), allows_updates=True,
        ),
        SampleSetPurpose.VALIDATION: AccessPolicy(
            ("orchestrator", "validator", "auditor"),
        ),
        SampleSetPurpose.SEALED_HOLDOUT: AccessPolicy(
            ("validator", "auditor"), requires_candidate_freeze=True,
        ),
        SampleSetPurpose.STRESS_AND_FAILURE: AccessPolicy(
            ("validator", "auditor"), requires_candidate_freeze=True,
        ),
    }
    return policies[purpose]


@dataclass(frozen=True)
class SampleSetManifest:
    purpose: SampleSetPurpose
    sample_refs: tuple[SampleRef, ...]
    access_policy: AccessPolicy
    content_hash: str
    freeze: FreezeDecision | None = None

    @classmethod
    def create(cls, purpose: SampleSetPurpose, sample_refs: tuple[SampleRef, ...],
               access_policy: AccessPolicy,
               freeze: FreezeDecision | None) -> "SampleSetManifest":
        refs = tuple(sample_refs)
        if not refs:
            raise ValueError("sample set cannot be empty")
        content_hash = canonical_hash({
            "purpose": purpose,
            "sample_refs": refs,
            "access_policy": access_policy,
        })
        return cls(purpose, refs, access_policy, content_hash, freeze)

    def require_access(self, actor: str, candidate_frozen: bool,
                       for_update: bool = False) -> None:
        if actor not in self.access_policy.readers:
            raise PermissionError(f"{actor} cannot read {self.purpose.value}")
        if self.access_policy.requires_candidate_freeze and not candidate_frozen:
            raise PermissionError(f"{self.purpose.value} requires candidate freeze")
        if for_update and not self.access_policy.allows_updates:
            raise PermissionError(f"{self.purpose.value} cannot drive direct updates")


@dataclass(frozen=True)
class SampleSetCollection:
    manifests: tuple[SampleSetManifest, ...]

    def __post_init__(self) -> None:
        purposes = [manifest.purpose for manifest in self.manifests]
        required = set(SampleSetPurpose)
        if len(self.manifests) != 4 or set(purposes) != required or len(set(purposes)) != 4:
            raise ValueError("four required sample sets must be present exactly once")
        hashes = [manifest.content_hash for manifest in self.manifests]
        if len(set(hashes)) != 4:
            raise ValueError("four required sample sets must have distinct content hashes")
        members = [ref.content_hash for manifest in self.manifests for ref in manifest.sample_refs]
        if len(members) != len(set(members)):
            raise ValueError("a sample cannot cross immutable set boundaries")

    def by_purpose(self, purpose: SampleSetPurpose) -> SampleSetManifest:
        return next(manifest for manifest in self.manifests if manifest.purpose == purpose)

    def assert_ready_for_candidate_generation(self) -> None:
        pending = [
            manifest.purpose.value for manifest in self.manifests
            if manifest.freeze is None or not manifest.freeze.approved
        ]
        if pending:
            raise PermissionError(f"Human Freeze required for: {', '.join(pending)}")
