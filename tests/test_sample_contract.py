"""Contracts for samples, immutable sets, access boundaries and episodes."""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _sample_module():
    try:
        return importlib.import_module("agentfit.models.sample")
    except ModuleNotFoundError as exc:
        pytest.fail(f"样本合同模块缺失: {exc}")


def _manifest_module():
    try:
        return importlib.import_module("agentfit.models.manifest")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Manifest 合同模块缺失: {exc}")


def _refs(sample_mod):
    return tuple(
        sample_mod.SampleRef(f"sample-{index}", f"{index:064x}")
        for index in range(1, 5)
    )


def _frozen_manifests(sample_mod, manifest_mod):
    freeze = manifest_mod.FreezeDecision(
        reviewer="human-owner",
        approved=True,
        decided_at="2026-08-17T14:00:00+08:00",
        reason="样本与评价边界确认",
    )
    refs = _refs(sample_mod)
    return tuple(
        manifest_mod.SampleSetManifest.create(
            purpose=purpose,
            sample_refs=(refs[index],),
            access_policy=manifest_mod.default_access_policy(purpose),
            freeze=freeze,
        )
        for index, purpose in enumerate(manifest_mod.SampleSetPurpose)
    )


def _safe_fix_inventory():
    from agentfit.models.project import CapabilityInventory
    from agentfit.models.solution import CapabilityTool, SolidAtom

    return CapabilityInventory.create(
        atoms=[SolidAtom("fix", "write")],
        tools=[CapabilityTool("safe_fix", ["fix"])],
    )


def test_canonical_hash_is_independent_of_mapping_order() -> None:
    sample_mod = _sample_module()
    assert sample_mod.canonical_hash({"a": 1, "b": 2}) == sample_mod.canonical_hash({"b": 2, "a": 1})


def test_canonical_hash_is_stable_for_sets_across_hash_seeds() -> None:
    code = "from agentfit.models.sample import canonical_hash; print(canonical_hash({'values': {'alpha', 'beta', 'gamma'}}))"
    repo = Path(__file__).resolve().parents[1]
    values = []
    for seed in ("1", "2", "3"):
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=repo,
            env={**os.environ, "PYTHONPATH": str(repo / "src"), "PYTHONHASHSEED": seed},
            capture_output=True, text=True, check=True,
        )
        values.append(result.stdout.strip())
    assert len(set(values)) == 1


@pytest.mark.parametrize("value", [
    object(),
    {object(): "unstable-key"},
    float("nan"),
    float("inf"),
])
def test_canonical_hash_rejects_non_json_evidence(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        _sample_module().canonical_hash(value)


def test_sample_set_collection_requires_all_four_distinct_purposes() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    manifests = _frozen_manifests(sample_mod, manifest_mod)
    with pytest.raises(ValueError, match="four required sample sets"):
        manifest_mod.SampleSetCollection(manifests=manifests[:3])


def test_manifest_rejects_forged_hash_and_noncanonical_access_policy() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    ref = _refs(sample_mod)[0]
    purpose = manifest_mod.SampleSetPurpose.SEALED_HOLDOUT
    freeze = manifest_mod.FreezeDecision(
        reviewer="human-owner", approved=True,
        decided_at="2026-08-17T14:00:00+08:00", reason="approved",
    )
    with pytest.raises(ValueError, match="canonical access policy"):
        manifest_mod.SampleSetManifest.create(
            purpose, (ref,),
            manifest_mod.AccessPolicy(("architect",), allows_updates=True),
            freeze,
        )
    with pytest.raises(ValueError, match="content_hash"):
        manifest_mod.SampleSetManifest(
            purpose, (ref,), manifest_mod.default_access_policy(purpose),
            "f" * 64, freeze,
        )


def test_human_freeze_is_required_before_candidate_generation() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    manifests = list(_frozen_manifests(sample_mod, manifest_mod))
    adaptation = manifests[0]
    manifests[0] = manifest_mod.SampleSetManifest.create(
        purpose=adaptation.purpose,
        sample_refs=adaptation.sample_refs,
        access_policy=adaptation.access_policy,
        freeze=None,
    )
    collection = manifest_mod.SampleSetCollection(manifests=tuple(manifests))
    with pytest.raises(PermissionError, match="Human Freeze"):
        collection.assert_ready_for_candidate_generation()


def test_candidate_builder_enforces_manifest_freeze() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    from agentfit.solution import builder
    from agentfit.models.loss import Expected

    build_candidate = getattr(builder, "build_candidate", None)
    assert callable(build_candidate), "缺少受 Manifest 门禁保护的 candidate builder"
    manifests = list(_frozen_manifests(sample_mod, manifest_mod))
    adaptation = manifests[0]
    manifests[0] = manifest_mod.SampleSetManifest.create(
        purpose=adaptation.purpose,
        sample_refs=adaptation.sample_refs,
        access_policy=adaptation.access_policy,
        freeze=None,
    )
    collection = manifest_mod.SampleSetCollection(manifests=tuple(manifests))
    with pytest.raises(PermissionError, match="Human Freeze"):
        build_candidate(
            [sample_mod.TaskSample("sample", (), {"x": True}, Expected())],
            collection,
            _safe_fix_inventory(),
        )


def test_candidate_builder_uses_only_frozen_adaptation_samples() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    from agentfit.solution.builder import build_candidate
    from agentfit.models.loss import Expected, ExpectedAction

    observation = sample_mod.SourceObservation.create(
        "procedure", "procedure", "approved fix procedure",
    )
    sample = sample_mod.TaskSample(
        "adaptation-sample", (observation.ref,), {"needs_fix": True},
        Expected([ExpectedAction("safe_fix")]),
    )
    task_ref = sample.ref
    freeze = manifest_mod.FreezeDecision(
        reviewer="human-owner", approved=True,
        decided_at="2026-08-17T14:00:00+08:00", reason="approved",
    )
    other_refs = _refs(sample_mod)[1:]
    refs_by_purpose = {
        manifest_mod.SampleSetPurpose.ADAPTATION: (task_ref,),
        manifest_mod.SampleSetPurpose.VALIDATION: (other_refs[0],),
        manifest_mod.SampleSetPurpose.SEALED_HOLDOUT: (other_refs[1],),
        manifest_mod.SampleSetPurpose.STRESS_AND_FAILURE: (other_refs[2],),
    }
    collection = manifest_mod.SampleSetCollection(manifests=tuple(
        manifest_mod.SampleSetManifest.create(
            purpose, refs_by_purpose[purpose],
            manifest_mod.default_access_policy(purpose), freeze,
        )
        for purpose in manifest_mod.SampleSetPurpose
    ))
    candidate = build_candidate(
        [sample], collection, _safe_fix_inventory(), coverage=1.0,
    )
    assert candidate.version == 0
    assert candidate.routing_rules()[0].dispatches_to == "safe_fix"


def test_candidate_builder_rejects_adaptation_sample_without_observation_lineage() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    from agentfit.models.loss import Expected, ExpectedAction
    from agentfit.solution.builder import build_candidate

    sample = sample_mod.TaskSample(
        "adaptation-sample", (), {"needs_fix": True},
        Expected([ExpectedAction("safe_fix")]),
    )
    freeze = manifest_mod.FreezeDecision(
        reviewer="human-owner", approved=True,
        decided_at="2026-08-17T14:00:00+08:00", reason="approved",
    )
    other_refs = _refs(sample_mod)[1:]
    refs_by_purpose = {
        manifest_mod.SampleSetPurpose.ADAPTATION: (sample.ref,),
        manifest_mod.SampleSetPurpose.VALIDATION: (other_refs[0],),
        manifest_mod.SampleSetPurpose.SEALED_HOLDOUT: (other_refs[1],),
        manifest_mod.SampleSetPurpose.STRESS_AND_FAILURE: (other_refs[2],),
    }
    collection = manifest_mod.SampleSetCollection(manifests=tuple(
        manifest_mod.SampleSetManifest.create(
            purpose, refs_by_purpose[purpose],
            manifest_mod.default_access_policy(purpose), freeze,
        )
        for purpose in manifest_mod.SampleSetPurpose
    ))

    with pytest.raises(ValueError, match="ObservationRef"):
        build_candidate([sample], collection, _safe_fix_inventory())


def test_sealed_holdout_is_inaccessible_until_candidate_freeze() -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    collection = manifest_mod.SampleSetCollection(
        manifests=_frozen_manifests(sample_mod, manifest_mod)
    )
    sealed = collection.by_purpose(manifest_mod.SampleSetPurpose.SEALED_HOLDOUT)
    with pytest.raises(PermissionError):
        sealed.require_access("auditor", candidate_frozen=False)
    with pytest.raises(PermissionError):
        sealed.require_access("architect", candidate_frozen=True)
    sealed.require_access("auditor", candidate_frozen=True)
    sealed.require_access("validator", candidate_frozen=True)


def test_evaluation_identity_is_candidate_sample_run_triple() -> None:
    sample_mod = _sample_module()
    identity = sample_mod.EvaluationIdentity(
        candidate_ref="a" * 64,
        sample_ref=sample_mod.SampleRef("sample", "b" * 64),
        run_index=2,
    )
    assert identity.key == f"{'a' * 64}.{'b' * 64}.2"
    with pytest.raises(ValueError, match="run_index"):
        sample_mod.EvaluationIdentity("a" * 64, sample_mod.SampleRef("sample", "b" * 64), -1)


def test_task_sample_keeps_canonical_semantics() -> None:
    sample_mod = _sample_module()
    from agentfit.models.loss import Expected, ExpectedAction

    observation = sample_mod.SourceObservation.create(
        "observation", "procedure", "approved operating procedure",
    )
    task = sample_mod.TaskSample(
        "canonical", (observation.ref,), {"abroad": True},
        Expected([ExpectedAction("safe_fix")]),
        requires_human=True, complexity="compound",
    )
    assert task.id == "canonical"
    assert task.input_data == {"abroad": True}
    assert task.expected.actions[0].tool == "safe_fix"
    assert task.requires_human is True
    assert task.complexity == "compound"
    assert task.observation_refs == (observation.ref,)


def test_runstore_persists_manifests_and_episode_identity(tmp_path: Path) -> None:
    sample_mod, manifest_mod = _sample_module(), _manifest_module()
    from agentfit.store.run_store import RunStore

    collection = manifest_mod.SampleSetCollection(
        manifests=_frozen_manifests(sample_mod, manifest_mod)
    )
    identity = sample_mod.EvaluationIdentity(
        candidate_ref="c" * 64,
        sample_ref=sample_mod.SampleRef("sample", "d" * 64),
        run_index=0,
    )
    episode = sample_mod.Episode(
        identity=identity,
        trace_ref="traces/sample.json",
        result="PASS",
        cost_usd=0.01,
        evidence_hash="e" * 64,
    )
    store = RunStore(tmp_path)
    store.save_sample_manifests(collection)
    path = store.save_episode(episode)

    saved_sets = json.loads((tmp_path / "sample_sets.json").read_text(encoding="utf-8"))
    saved_episode = json.loads(path.read_text(encoding="utf-8"))
    assert len(saved_sets["manifests"]) == 4
    assert saved_episode["identity"]["run_index"] == 0
    assert saved_episode["evidence_hash"] == "e" * 64
