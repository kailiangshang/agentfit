"""Platform-neutral candidate and external-evidence contracts."""
from __future__ import annotations

from dataclasses import replace
import importlib

import pytest

from agentfit.models.sample import SampleRef, canonical_hash


def _contracts():
    module = importlib.import_module("agentfit.models.evidence")
    return module.CandidateManifest, module.ExternalEvidenceRecord


def test_candidate_ref_is_the_persisted_manifest_content_hash() -> None:
    CandidateManifest, _ = _contracts()

    manifest = CandidateManifest.create(
        candidate_id="tau2-baseline",
        kind="external_system",
        specification={
            "bridge": "tau2bench",
            "source_configuration_hash": canonical_hash({"model": "fixture"}),
        },
        provenance_complete=False,
    )

    assert manifest.candidate_ref == manifest.content_hash
    assert len(manifest.content_hash) == 64
    with pytest.raises(ValueError, match="content_hash"):
        replace(manifest, specification={"bridge": "changed"})


def test_external_evidence_records_form_a_content_bound_chain() -> None:
    _, ExternalEvidenceRecord = _contracts()
    sample_ref = SampleRef("task-1", canonical_hash({"task": 1}))
    candidate_ref = canonical_hash({"candidate": 1})
    trace_hash = canonical_hash({"trace": 1})

    first = ExternalEvidenceRecord.create(
        source_index=0,
        source_record_hash=canonical_hash({"reward": 1}),
        candidate_ref=candidate_ref,
        sample_ref=sample_ref,
        run_index=0,
        trace_ref="traces/first.json",
        result="PASS",
        cost_usd=0.01,
        trace_hash=trace_hash,
        previous_hash="GENESIS",
    )
    second = ExternalEvidenceRecord.create(
        source_index=1,
        source_record_hash=canonical_hash({"reward": 0}),
        candidate_ref=candidate_ref,
        sample_ref=sample_ref,
        run_index=1,
        trace_ref="traces/second.json",
        result="FAIL",
        cost_usd=0.02,
        trace_hash=trace_hash,
        previous_hash=first.content_hash,
    )

    assert second.previous_hash == first.content_hash
    with pytest.raises(ValueError, match="content_hash"):
        replace(second, result="PASS")


def test_candidate_manifest_requires_boolean_provenance_flag() -> None:
    from agentfit.models.evidence import CandidateManifest

    with pytest.raises(TypeError, match="provenance_complete"):
        CandidateManifest.create(
            candidate_id="candidate",
            kind="external_system",
            specification={},
            provenance_complete="false",  # type: ignore[arg-type]
        )
