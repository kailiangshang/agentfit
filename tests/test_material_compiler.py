"""Business material compilation into traceable samples and frozen sets."""
from __future__ import annotations

import copy

import pytest


def _bundle() -> dict:
    purposes = ("adaptation", "validation", "sealed_holdout", "stress_and_failure")
    return {
        "scenario": "material-fixture",
        "materials": [
            {
                "id": "procedure-roaming",
                "kind": "procedure",
                "content": "When roaming is disabled abroad, request a safe roaming change.",
                "metadata": {"source": "operations-handbook"},
            },
        ],
        "capabilities": {
            "atoms": [
                {
                    "id": f"fix_{index}",
                    "type": "write",
                    "description": f"fixture capability {index}",
                }
                for index in range(1, 5)
            ],
            "tools": [
                {
                    "id": f"safe_fix_{index}",
                    "wraps": [f"fix_{index}"],
                    "description": f"safe fixture capability {index}",
                }
                for index in range(1, 5)
            ],
        },
        "objective": {
            "criteria": [
                {
                    "purpose": purpose,
                    "min_pass_rate": 0.8,
                    "max_errors": 0,
                    "max_cost_usd": 1.0,
                    "max_risk_events": 0,
                }
                for purpose in purposes
            ],
            "max_total_evaluation_cost_usd": 3.0,
        },
        "tasks": [
            {
                "id": f"task-{index}",
                "purpose": purpose,
                "observation_ids": ["procedure-roaming"],
                "input_data": {"abroad": True, f"condition_{index}": True},
                "expected": {
                    "actions": [{"tool": f"safe_fix_{index}", "params": {}}],
                    "outcome": {"resolved": True},
                },
                "requires_human": purpose == "stress_and_failure",
                "complexity": "compound" if purpose == "stress_and_failure" else "simple",
            }
            for index, purpose in enumerate(purposes, 1)
        ],
        "freeze": {
            "reviewer": "human-owner",
            "approved": True,
            "decided_at": "2026-08-17T18:00:00+08:00",
            "reason": "material fixture approved",
        },
        "training": {"batch_size": 1, "max_epochs": 1},
    }


def test_material_bundle_compiles_traceable_samples_and_four_frozen_sets() -> None:
    from plugins.materials.compiler import compile_material_bundle

    compiled = compile_material_bundle(_bundle())
    assert len(compiled.observations) == 1
    observation = compiled.observations[0]
    assert len(observation.content_hash) == 64
    assert len(compiled.task_samples) == 4
    assert len(compiled.capability_inventory.atoms) == 4
    assert len(compiled.capability_inventory.tools) == 4
    assert len(compiled.objective_spec.criteria) == 4
    assert {
        task.observation_refs[0].observation_id for task in compiled.task_samples
    } == {observation.id}
    assert {
        task.observation_refs[0].content_hash for task in compiled.task_samples
    } == {observation.content_hash}
    assert len(compiled.sample_sets.manifests) == 4
    compiled.sample_sets.assert_ready_for_candidate_generation()

    document = compiled.to_case_document()
    assert document["source_observations"][0]["content_hash"] == observation.content_hash
    assert len(document["task_samples"]) == 4
    assert document["capability_inventory"]["content_hash"] == (
        compiled.capability_inventory.content_hash
    )
    assert document["objective"]["content_hash"] == compiled.objective_spec.content_hash
    assert {item["purpose"] for item in document["sample_sets"]} == {
        "adaptation", "validation", "sealed_holdout", "stress_and_failure",
    }


def test_material_change_invalidates_task_and_manifest_hashes() -> None:
    from plugins.materials.compiler import compile_material_bundle

    before = compile_material_bundle(_bundle())
    changed = copy.deepcopy(_bundle())
    changed["materials"][0]["content"] += " Human confirmation is required."
    after = compile_material_bundle(changed)

    assert before.observations[0].content_hash != after.observations[0].content_hash
    assert before.task_samples[0].content_hash != after.task_samples[0].content_hash
    assert (
        before.sample_sets.manifests[0].content_hash
        != after.sample_sets.manifests[0].content_hash
    )


def test_material_metadata_change_invalidates_lineage_hashes() -> None:
    from plugins.materials.compiler import compile_material_bundle

    before = compile_material_bundle(_bundle())
    changed = copy.deepcopy(_bundle())
    changed["materials"][0]["metadata"]["source"] = "revised-handbook"
    after = compile_material_bundle(changed)

    assert before.observations[0].content_hash != after.observations[0].content_hash
    assert before.task_samples[0].content_hash != after.task_samples[0].content_hash
    assert before.sample_sets.manifests[0].content_hash != after.sample_sets.manifests[0].content_hash


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda bundle: bundle["tasks"][0].update(observation_ids=["missing"]), "unknown observation"),
        (lambda bundle: bundle["tasks"][1].update(id="task-1"), "task ids must be unique"),
        (lambda bundle: bundle["tasks"][0]["expected"].update(actions=[]), "expected action"),
        (lambda bundle: bundle.pop("capabilities"), "capability inventory"),
        (lambda bundle: bundle.pop("objective"), "objective"),
        (lambda bundle: bundle["objective"]["criteria"].pop(), "four required purpose criteria"),
        (
            lambda bundle: bundle["capabilities"]["tools"][0].update(wraps=["missing"]),
            "unknown L1 atom",
        ),
        (
            lambda bundle: bundle["capabilities"]["atoms"][0].update(backend="fixture_api"),
            "runtime binding",
        ),
        (
            lambda bundle: bundle["capabilities"]["tools"].pop(),
            "approved capability inventory",
        ),
        (lambda bundle: bundle["tasks"].pop(), "four required sample sets"),
        (lambda bundle: (bundle.update(materials=[]), [task.update(observation_ids=[]) for task in bundle["tasks"]]), "materials are required"),
        (lambda bundle: bundle["tasks"][0].update(observation_ids=[]), "requires an observation"),
        (lambda bundle: bundle.pop("freeze"), "approved Human Freeze"),
        (lambda bundle: bundle["freeze"].update(approved=False), "approved Human Freeze"),
    ],
)
def test_material_compiler_rejects_incomplete_or_conflicting_contracts(mutate, message: str) -> None:
    from plugins.materials.compiler import compile_material_bundle

    bundle = _bundle()
    mutate(bundle)
    with pytest.raises(ValueError, match=message):
        compile_material_bundle(bundle)
