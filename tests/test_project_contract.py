"""Project-level contracts that prevent phantom capabilities and false delivery."""
from __future__ import annotations

import pytest
from dataclasses import asdict

from agentfit.models.loss import Expected, ExpectedAction
from agentfit.models.manifest import (
    FreezeDecision,
    SampleSetCollection,
    SampleSetManifest,
    SampleSetPurpose,
    default_access_policy,
)
from agentfit.models.sample import SourceObservation, TaskSample, canonical_hash
from agentfit.models.solution import CapabilityTool, SolidAtom


def _sample(tool: str = "safe_fix") -> TaskSample:
    observation = SourceObservation.create(
        "approved-procedure", "procedure", "Use only approved capabilities.",
    )
    return TaskSample(
        "adaptation-sample",
        (observation.ref,),
        {"needs_fix": True},
        Expected([ExpectedAction(tool)]),
    )


def _sample_sets(sample: TaskSample) -> SampleSetCollection:
    freeze = FreezeDecision(
        reviewer="human-owner",
        approved=True,
        decided_at="2026-08-17T20:00:00+08:00",
        reason="project contract fixture",
    )
    refs = {
        SampleSetPurpose.ADAPTATION: (sample.ref,),
        SampleSetPurpose.VALIDATION: (
            type(sample.ref)("validation", canonical_hash({"sample": "validation"})),
        ),
        SampleSetPurpose.SEALED_HOLDOUT: (
            type(sample.ref)("sealed", canonical_hash({"sample": "sealed"})),
        ),
        SampleSetPurpose.STRESS_AND_FAILURE: (
            type(sample.ref)("stress", canonical_hash({"sample": "stress"})),
        ),
    }
    return SampleSetCollection(tuple(
        SampleSetManifest.create(
            purpose, refs[purpose], default_access_policy(purpose), freeze,
        )
        for purpose in SampleSetPurpose
    ))


def test_capability_inventory_is_content_addressed_and_rejects_phantom_wraps() -> None:
    from agentfit.models.project import CapabilityInventory

    inventory = CapabilityInventory.create(
        atoms=(SolidAtom("fix", "write"),),
        tools=(CapabilityTool("safe_fix", ["fix"]),),
    )

    assert inventory.content_hash == canonical_hash({
        "atoms": inventory.atoms,
        "tools": inventory.tools,
    })
    with pytest.raises(ValueError, match="unknown L1 atom"):
        CapabilityInventory.create(
            atoms=(SolidAtom("fix", "write"),),
            tools=(CapabilityTool("unsafe_phantom", ["missing"]),),
        )


def test_l1_contract_declares_capability_without_runtime_backend() -> None:
    from agentfit.models.project import CapabilityInventory

    atom = SolidAtom("fix", "write", description="Apply an approved correction")
    inventory = CapabilityInventory.create(
        atoms=(atom,),
        tools=(CapabilityTool("safe_fix", ["fix"]),),
    )

    assert inventory.atoms == (atom,)
    assert "backend" not in asdict(atom)


def test_candidate_uses_only_confirmed_capability_inventory() -> None:
    from agentfit.models.project import CapabilityInventory
    from agentfit.solution.builder import build_candidate

    sample = _sample()
    inventory = CapabilityInventory.create(
        atoms=(SolidAtom("fix", "write"),),
        tools=(CapabilityTool("safe_fix", ["fix"]),),
    )

    candidate = build_candidate(
        [sample], _sample_sets(sample), inventory, coverage=1.0,
    )

    assert candidate.L1_atoms == [SolidAtom("fix", "write")]
    assert candidate.L2_tools == [CapabilityTool("safe_fix", ["fix"])]


def test_candidate_rejects_expected_tool_outside_confirmed_inventory() -> None:
    from agentfit.models.project import CapabilityInventory
    from agentfit.solution.builder import build_candidate

    sample = _sample("safe_missing")
    inventory = CapabilityInventory.create(
        atoms=(SolidAtom("fix", "write"),),
        tools=(CapabilityTool("safe_fix", ["fix"]),),
    )

    with pytest.raises(ValueError, match="approved capability inventory"):
        build_candidate([sample], _sample_sets(sample), inventory, coverage=1.0)


def _objective(*, min_pass_rate: float = 0.8):
    from agentfit.models.objective import ObjectiveSpec, PurposeAcceptance

    return ObjectiveSpec.create(
        criteria=tuple(
            PurposeAcceptance(
                purpose=purpose,
                min_pass_rate=min_pass_rate,
                max_errors=0,
                max_cost_usd=1.0,
                max_risk_events=0,
            )
            for purpose in SampleSetPurpose
        ),
        max_total_evaluation_cost_usd=3.0,
    )


def _evaluation(pass_rate: float = 1.0) -> dict[str, dict]:
    return {
        purpose.value: {
            "total": 2,
            "passed": round(2 * pass_rate),
            "failed": 2 - round(2 * pass_rate),
            "errors": 0,
            "pass_rate": pass_rate,
            "cost_usd": 0.1,
            "risk_events": 0,
        }
        for purpose in SampleSetPurpose
    }


def test_objective_spec_requires_four_content_addressed_purpose_criteria() -> None:
    from agentfit.models.objective import ObjectiveSpec, PurposeAcceptance

    objective = _objective()

    assert objective.content_hash == canonical_hash({
        "criteria": objective.criteria,
        "max_total_evaluation_cost_usd": 3.0,
    })
    with pytest.raises(ValueError, match="four required purpose criteria"):
        ObjectiveSpec.create(
            criteria=(PurposeAcceptance(
                SampleSetPurpose.ADAPTATION, 0.8, 0, 1.0, 0,
            ),),
            max_total_evaluation_cost_usd=3.0,
        )


def test_acceptance_result_rejects_one_failed_purpose_even_when_adaptation_passes() -> None:
    from agentfit.models.objective import evaluate_acceptance

    evaluation = _evaluation()
    evaluation[SampleSetPurpose.VALIDATION.value] = {
        **evaluation[SampleSetPurpose.VALIDATION.value],
        "passed": 0,
        "failed": 2,
        "pass_rate": 0.0,
    }

    result = evaluate_acceptance(_objective(), evaluation)

    assert result.met is False
    assert result.criteria_met[SampleSetPurpose.ADAPTATION.value] is True
    assert result.criteria_met[SampleSetPurpose.VALIDATION.value] is False
    assert any("validation.pass_rate" in failure for failure in result.failures)
    assert result.content_hash == canonical_hash({
        "objective_ref": result.objective_ref,
        "evaluation_by_purpose": result.evaluation_by_purpose,
        "criteria_met": result.criteria_met,
        "met": result.met,
        "failures": result.failures,
    })


def test_acceptance_result_enforces_global_cost_and_risk_thresholds() -> None:
    from agentfit.models.objective import evaluate_acceptance

    evaluation = _evaluation()
    evaluation[SampleSetPurpose.SEALED_HOLDOUT.value]["risk_events"] = 1
    evaluation[SampleSetPurpose.STRESS_AND_FAILURE.value]["cost_usd"] = 4.0

    result = evaluate_acceptance(_objective(), evaluation)

    assert result.met is False
    assert any("sealed_holdout.risk_events" in item for item in result.failures)
    assert any("stress_and_failure.cost_usd" in item for item in result.failures)
    assert any("total_evaluation_cost_usd" in item for item in result.failures)


def test_acceptance_rejects_unobserved_runtime_cost() -> None:
    from agentfit.models.objective import evaluate_acceptance

    evaluation = _evaluation()
    evaluation[SampleSetPurpose.ADAPTATION.value]["cost_observed"] = False

    result = evaluate_acceptance(_objective(), evaluation)

    assert result.met is False
    assert result.criteria_met[SampleSetPurpose.ADAPTATION.value] is False
    assert any(
        "adaptation.cost_usd unavailable" in item
        for item in result.failures
    )
