"""Stable platform-independent AgentFit command line interface."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .adapters.protocols import ExternalEvidenceProjector
from .agents.orchestrator import Orchestrator
from .agents.team import build_team
from .dashboard import generate_dashboard
from .data.sample_pool import SamplePool
from .delivery.approval import assert_delivery_approved, verify_delivery_decision
from .delivery.boundary import write_boundary
from .delivery.package import export_evidence_package, export_package
from .executors.simulator import SimulatorExecutor
from .log.report import generate_report
from .materials.compiler import compile_material_bundle
from .models.evidence import CandidateManifest, ExternalEvidenceRecord
from .models.config import AutoApprove, TrainingConfig
from .models.loss import Expected, ExpectedAction
from .models.manifest import (
    AccessPolicy, FreezeDecision, SampleSetCollection, SampleSetManifest,
    SampleSetPurpose,
)
from .models.objective import (
    AcceptanceResult, ObjectiveSpec, acceptance_result_from_dict,
    evaluate_acceptance, objective_spec_from_dict, summarize_episodes,
)
from .models.project import CapabilityInventory, capability_inventory_from_dict
from .models.sample import (
    Episode, EvaluationIdentity, ObservationRef, SampleRef, SourceObservation,
    TaskSample, canonical_hash,
)
from .models.solution import solution_from_dict
from .solution.builder import build_candidate
from .store.run_store import RunStore


class CliError(ValueError):
    pass


def _task_sample_from_dict(item: dict[str, Any]) -> TaskSample:
    expected_data = item.get("expected") or {}
    actions = [ExpectedAction(**action) for action in expected_data.get("actions", [])]
    evaluator = str(item.get("evaluator", "exact"))
    if evaluator == "exact" and not actions:
        raise CliError(f"sample {item.get('id', '<missing>')} has no expected actions")
    return TaskSample(
        id=item["id"],
        observation_refs=tuple(ObservationRef(**ref) for ref in item.get("observation_refs", [])),
        input_data=dict(item.get("input_data") or {}),
        expected=Expected(actions=actions, outcome=dict(expected_data.get("outcome") or {})),
        evaluator=evaluator,
        constraints=dict(item.get("constraints") or {}),
        requires_human=bool(item.get("requires_human", False)),
        complexity=item.get("complexity", "simple"),
    )


def _read_case(path: Path) -> tuple[
    dict[str, Any], list[TaskSample], SampleSetCollection, CapabilityInventory,
    ObjectiveSpec,
]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid case: {exc}") from exc
    if doc.get("task_samples") is None:
        raise CliError("case must contain canonical task_samples")
    task_samples = [_task_sample_from_dict(item) for item in doc.get("task_samples", [])]
    if not task_samples:
        raise CliError("case has no samples")
    by_id = {task.id: task for task in task_samples}
    if len(by_id) != len(task_samples):
        raise CliError("sample ids must be unique")

    inventory_data = doc.get("capability_inventory")
    if not isinstance(inventory_data, dict):
        raise CliError("case must contain a capability inventory")
    try:
        capability_inventory = capability_inventory_from_dict(inventory_data)
    except (TypeError, ValueError) as exc:
        raise CliError(f"invalid capability inventory: {exc}") from exc

    objective_data = doc.get("objective")
    if not isinstance(objective_data, dict):
        raise CliError("case must contain an objective")
    try:
        objective = objective_spec_from_dict(objective_data)
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError(f"invalid objective: {exc}") from exc

    observation_items = doc.get("source_observations")
    if not isinstance(observation_items, list) or not observation_items:
        raise CliError("case must contain source observations")
    try:
        observations = [SourceObservation(**item) for item in observation_items]
    except (TypeError, ValueError) as exc:
        raise CliError(f"invalid source observations: {exc}") from exc
    observation_by_id = {observation.id: observation for observation in observations}
    if len(observation_by_id) != len(observations):
        raise CliError("source observation ids must be unique")
    for task in task_samples:
        if not task.observation_refs:
            raise CliError(f"sample requires an ObservationRef: {task.id}")
        for ref in task.observation_refs:
            observation = observation_by_id.get(ref.observation_id)
            if observation is None or observation.ref != ref:
                raise CliError(f"observation reference mismatch: {ref.observation_id}")

    manifests = []
    for item in doc.get("sample_sets", []):
        purpose = SampleSetPurpose(item["purpose"])
        refs = tuple(SampleRef(**ref) for ref in item["sample_refs"])
        policy_data = item.get("access_policy") or {}
        policy = AccessPolicy(
            readers=tuple(policy_data.get("readers", ())),
            allows_updates=bool(policy_data.get("allows_updates", False)),
            requires_candidate_freeze=bool(policy_data.get("requires_candidate_freeze", False)),
        )
        freeze_data = item.get("freeze")
        freeze = FreezeDecision(**freeze_data) if freeze_data else None
        manifest = SampleSetManifest.create(purpose, refs, policy, freeze)
        if item.get("content_hash") not in (None, manifest.content_hash):
            raise CliError("sample-set content hash mismatch")
        manifests.append(manifest)
    try:
        collection = SampleSetCollection(tuple(manifests))
        collection.assert_ready_for_candidate_generation()
    except (ValueError, PermissionError) as exc:
        raise CliError(f"invalid sample sets: {exc}") from exc
    actual_task_refs = {task.id: task.ref for task in task_samples}
    for manifest in collection.manifests:
        for ref in manifest.sample_refs:
            if actual_task_refs.get(ref.sample_id) != ref:
                raise CliError(f"sample reference mismatch: {ref.sample_id}")
    return doc, task_samples, collection, capability_inventory, objective


def _compile(args: argparse.Namespace) -> int:
    if args.output.exists():
        raise CliError(f"output already exists: {args.output}")
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid material bundle: {exc}") from exc
    document = compile_material_bundle(bundle).to_case_document()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(args.output)
    return 0


def _adaptation_samples(samples: list[TaskSample], collection: SampleSetCollection) -> list[TaskSample]:
    adaptation = collection.by_purpose(SampleSetPurpose.ADAPTATION)
    ids = {ref.sample_id for ref in adaptation.sample_refs}
    return [sample for sample in samples if sample.id in ids]


def _train(args: argparse.Namespace) -> int:
    if args.output.exists():
        raise CliError(f"output already exists: {args.output}")
    doc, task_samples, collection, capability_inventory, objective = _read_case(args.case)
    adaptation = _adaptation_samples(task_samples, collection)
    solution = build_candidate(task_samples, collection, capability_inventory)
    training = doc.get("training", {})
    config_args: dict[str, Any] = {
        "batch_size": int(training.get("batch_size", len(adaptation))),
        "max_epochs": int(training.get("max_epochs", 1)),
    }
    if args.auto_approve:
        config_args["review_policy"] = AutoApprove()
    executor = SimulatorExecutor()
    orchestrator = Orchestrator(
        solution, SamplePool(adaptation), executor, TrainingConfig(**config_args),
        run_dir=str(args.output), scenario=doc.get("scenario", "default"),
    )
    build_team(orchestrator)
    orchestrator.train()

    store = RunStore(args.output)
    store.save_task_samples(task_samples)
    store.save_capability_inventory(capability_inventory)
    store.save_objective(objective)
    if doc.get("source_observations") is not None:
        observations = [SourceObservation(**item) for item in doc["source_observations"]]
        store.save_source_observations(observations)
    store.save_sample_manifests(collection)
    candidate = CandidateManifest.for_solution(orchestrator.solution)
    store.save_training_candidate_manifest(candidate)
    candidate_ref = candidate.candidate_ref
    by_id = {sample.id: sample for sample in task_samples}
    actors = {
        SampleSetPurpose.ADAPTATION: "architect",
        SampleSetPurpose.VALIDATION: "validator",
        SampleSetPurpose.SEALED_HOLDOUT: "auditor",
        SampleSetPurpose.STRESS_AND_FAILURE: "auditor",
    }
    evaluation_by_purpose: dict[str, dict[str, Any]] = {}
    for manifest in collection.manifests:
        manifest.require_access(actors[manifest.purpose], candidate_frozen=True)
        results = []
        for sample_ref in manifest.sample_refs:
            sample = by_id[sample_ref.sample_id]
            trace, identity = orchestrator.execute_evaluation(
                orchestrator.solution, sample,
            )
            if identity.candidate_ref != candidate_ref or identity.sample_ref != sample_ref:
                raise CliError("final evaluation identity drift")
            trace_path = store.save_trace(identity, trace)
            episode = Episode(
                identity=identity,
                trace_ref=trace_path.relative_to(store.root).as_posix(),
                result=trace.result,
                cost_usd=trace.cost_usd,
                evidence_hash=canonical_hash(trace),
                risk_events=len(trace.risk_events),
                runtime_ref=trace.runtime_ref,
            )
            store.save_episode(episode)
            results.append(episode)
        evaluation_by_purpose[manifest.purpose.value] = summarize_episodes(results)
    acceptance = evaluate_acceptance(objective, evaluation_by_purpose)
    store.save_acceptance(acceptance)
    orchestrator.finalize_delivery({
        "candidate_ref": candidate_ref,
        "candidate_frozen": True,
        "evaluation_by_purpose": evaluation_by_purpose,
        "objective_ref": objective.content_hash,
        "acceptance_ref": acceptance.content_hash,
        "acceptance_met": acceptance.met,
        "acceptance_failures": list(acceptance.failures),
    })
    print(args.output)
    return 0


def _validate_sample_sets(store: RunStore) -> SampleSetCollection:
    doc = store.load_json("sample_sets.json")
    manifests = doc.get("manifests", [])
    if len(manifests) != 4 or {item.get("purpose") for item in manifests} != {p.value for p in SampleSetPurpose}:
        raise CliError("invalid RunStore: sample-set contract")
    rebuilt = []
    for item in manifests:
        try:
            purpose = SampleSetPurpose(item["purpose"])
            refs = tuple(SampleRef(ref["sample_id"], ref["content_hash"])
                         for ref in item["sample_refs"])
            policy_data = item["access_policy"]
            policy = AccessPolicy(
                readers=tuple(policy_data["readers"]),
                allows_updates=bool(policy_data.get("allows_updates", False)),
                requires_candidate_freeze=bool(policy_data.get("requires_candidate_freeze", False)),
            )
            freeze = FreezeDecision(**item["freeze"]) if item.get("freeze") else None
            manifest = SampleSetManifest.create(purpose, refs, policy, freeze)
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError(f"invalid RunStore: sample-set structure: {exc}") from exc
        if item.get("content_hash") != manifest.content_hash:
            raise CliError("invalid RunStore: sample-set content hash mismatch")
        if manifest.freeze is None or not manifest.freeze.approved:
            raise CliError("invalid RunStore: sample-set freeze evidence")
        rebuilt.append(manifest)
    try:
        collection = SampleSetCollection(tuple(rebuilt))
    except ValueError as exc:
        raise CliError(f"invalid RunStore: sample-set contract: {exc}") from exc

    try:
        tasks_doc = store.load_json("task_samples.json")
        tasks = [_task_sample_from_dict(item) for item in tasks_doc.get("samples", [])]
        actual_refs = {task.id: task.ref for task in tasks}
    except (KeyError, TypeError, CliError) as exc:
        raise CliError(f"invalid RunStore: task samples: {exc}") from exc
    for manifest in collection.manifests:
        for ref in manifest.sample_refs:
            if ref.sample_id not in actual_refs or actual_refs[ref.sample_id] != ref:
                raise CliError(f"invalid RunStore: sample reference mismatch: {ref.sample_id}")
    return collection


def _validate_material_lineage(store: RunStore) -> None:
    task_path = store.root / "task_samples.json"
    if not task_path.is_file():
        return
    tasks_doc = store.load_json("task_samples.json")
    tasks = [_task_sample_from_dict(item) for item in tasks_doc.get("samples", [])]
    if tasks_doc.get("total") != len(tasks):
        raise CliError("invalid RunStore: task sample count mismatch")
    refs = [ref for task in tasks for ref in task.observation_refs]
    if not refs:
        return
    observation_path = store.root / "source_observations.json"
    if not observation_path.is_file():
        raise CliError("invalid RunStore: source observations are missing")
    observations_doc = store.load_json("source_observations.json")
    observations = [SourceObservation(**item) for item in observations_doc.get("observations", [])]
    if observations_doc.get("total") != len(observations):
        raise CliError("invalid RunStore: source observation count mismatch")
    by_id = {observation.id: observation for observation in observations}
    if len(by_id) != len(observations):
        raise CliError("invalid RunStore: source observation ids must be unique")
    for ref in refs:
        observation = by_id.get(ref.observation_id)
        if observation is None or observation.ref != ref:
            raise CliError(
                f"invalid RunStore: observation reference mismatch: {ref.observation_id}"
            )


def _validate_capability_inventory(store: RunStore) -> CapabilityInventory:
    try:
        inventory = capability_inventory_from_dict(
            store.load_json("capability_inventory.json")
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CliError(f"invalid RunStore: capability inventory: {exc}") from exc
    return inventory


def _validate_objective_acceptance(
    store: RunStore, evaluation_by_purpose: dict[str, dict[str, Any]],
) -> tuple[ObjectiveSpec, AcceptanceResult]:
    try:
        objective = objective_spec_from_dict(store.load_json("objective.json"))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CliError(f"invalid RunStore: objective: {exc}") from exc
    try:
        persisted = acceptance_result_from_dict(store.load_json("acceptance.json"))
        expected = evaluate_acceptance(objective, evaluation_by_purpose)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CliError(f"invalid RunStore: acceptance result: {exc}") from exc
    if persisted != expected:
        raise CliError("invalid RunStore: acceptance result mismatch")
    return objective, persisted


def _validate_training_candidates(store: RunStore) -> dict[str, CandidateManifest]:
    directory = store.root / "candidate_manifests"
    if not directory.is_dir():
        raise CliError("invalid RunStore: training candidate manifests are missing")
    candidates: dict[str, CandidateManifest] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            candidate = CandidateManifest(
                candidate_id=data["candidate_id"],
                kind=data["kind"],
                specification=data["specification"],
                provenance_complete=data["provenance_complete"],
                content_hash=data["content_hash"],
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise CliError(f"invalid RunStore: training candidate manifest: {path.name}") from exc
        if path.stem != candidate.candidate_ref:
            raise CliError("invalid RunStore: training candidate filename mismatch")
        specification = candidate.specification
        if candidate.kind != "agentfit.solution" or not isinstance(specification.get("solution"), dict):
            raise CliError("invalid RunStore: training candidate specification")
        try:
            solution_ref = canonical_hash(solution_from_dict(specification["solution"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError("invalid RunStore: training candidate solution") from exc
        if specification.get("solution_ref") != solution_ref or candidate.candidate_id != solution_ref:
            raise CliError("invalid RunStore: training candidate solution reference mismatch")
        candidates[candidate.candidate_ref] = candidate
    if not candidates:
        raise CliError("invalid RunStore: training candidate manifests are empty")
    return candidates


def _safe_artifact(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise CliError("invalid RunStore: evidence path escapes root")
    return root / rel


def _validate_training_evidence(
    store: RunStore,
    candidate_refs: set[str],
    runtime_ref: str,
) -> None:
    episode_root = store.root / "training_episodes"
    trace_root = store.root / "training_traces"
    episode_paths = sorted(episode_root.rglob("*.json"))
    trace_paths = sorted(trace_root.rglob("*.json"))
    if not episode_paths or not trace_paths:
        raise CliError("invalid RunStore: training Trace/Episode evidence is missing")

    tasks_document = store.load_json("task_samples.json")
    try:
        tasks = [_task_sample_from_dict(item) for item in tasks_document.get("samples", [])]
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError("invalid RunStore: training TaskSample evidence") from exc
    sample_refs = {(task.id, task.content_hash) for task in tasks}
    identities: set[str] = set()
    referenced_traces: set[Path] = set()
    run_indices: dict[tuple[str, str], list[int]] = {}

    for episode_path in episode_paths:
        relative = episode_path.relative_to(episode_root)
        if len(relative.parts) != 3 or not relative.parts[1].startswith("epoch_"):
            raise CliError("invalid RunStore: malformed training Episode path")
        phase, epoch_dir, _ = relative.parts
        episode_data = json.loads(episode_path.read_text(encoding="utf-8"))
        identity_data = episode_data.get("identity") or {}
        ref_data = identity_data.get("sample_ref") or {}
        try:
            identity = EvaluationIdentity(
                candidate_ref=identity_data["candidate_ref"],
                sample_ref=SampleRef(ref_data["sample_id"], ref_data["content_hash"]),
                run_index=identity_data["run_index"],
            )
            episode = Episode(
                identity=identity,
                trace_ref=episode_data["trace_ref"],
                result=episode_data["result"],
                cost_usd=episode_data["cost_usd"],
                evidence_hash=episode_data["evidence_hash"],
                status=episode_data.get("status", "completed"),
                risk_events=episode_data.get("risk_events", 0),
                runtime_ref=episode_data.get("runtime_ref", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError("invalid RunStore: malformed training Episode") from exc
        if identity.key in identities:
            raise CliError("invalid RunStore: duplicate training evaluation identity")
        identities.add(identity.key)
        if identity.candidate_ref not in candidate_refs:
            raise CliError("invalid RunStore: training Episode candidate mismatch")
        if (identity.sample_ref.sample_id, identity.sample_ref.content_hash) not in sample_refs:
            raise CliError("invalid RunStore: training Episode sample mismatch")
        if episode.status != "completed" or episode_path.name != f"{identity.key}.json":
            raise CliError("invalid RunStore: training Episode identity mismatch")

        expected_trace_ref = (
            Path("training_traces") / phase / epoch_dir / f"{identity.key}.json"
        ).as_posix()
        if episode.trace_ref != expected_trace_ref:
            raise CliError("invalid RunStore: training Episode trace reference mismatch")
        trace_path = _safe_artifact(store.root, episode.trace_ref)
        if not trace_path.is_file():
            raise CliError("invalid RunStore: training Trace is missing")
        referenced_traces.add(trace_path)
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if (
            trace.get("sample_id") != identity.sample_ref.sample_id
            or trace.get("result") != episode.result
            or float(trace.get("cost_usd", 0)) != episode.cost_usd
            or canonical_hash(trace) != episode.evidence_hash
            or len(trace.get("risk_events", [])) != episode.risk_events
        ):
            raise CliError("invalid RunStore: training Trace/Episode mismatch")
        if episode.runtime_ref != runtime_ref or trace.get("runtime_ref") != runtime_ref:
            raise CliError("invalid RunStore: training runtime reference mismatch")
        run_indices.setdefault(
            (identity.candidate_ref, identity.sample_ref.content_hash), [],
        ).append(identity.run_index)

    if set(trace_paths) != referenced_traces:
        raise CliError("invalid RunStore: orphan or missing training Trace")
    for indices in run_indices.values():
        if sorted(indices) != list(range(len(indices))):
            raise CliError("invalid RunStore: training run indices are not contiguous")


def _validate_episodes(store: RunStore,
                       candidate_refs: set[str] | None = None,
                       runtime_ref: str | None = None) -> list[dict]:
    if candidate_refs is None:
        candidate_refs = set(_validate_training_candidates(store))
    episodes = []
    for path in sorted((store.root / "episodes").glob("*.json")):
        episode_data = json.loads(path.read_text(encoding="utf-8"))
        identity_data = episode_data.get("identity") or {}
        ref_data = identity_data.get("sample_ref") or {}
        try:
            identity = EvaluationIdentity(
                candidate_ref=identity_data["candidate_ref"],
                sample_ref=SampleRef(ref_data["sample_id"], ref_data["content_hash"]),
                run_index=identity_data["run_index"],
            )
            episode = Episode(
                identity=identity,
                trace_ref=episode_data["trace_ref"],
                result=episode_data["result"],
                cost_usd=episode_data["cost_usd"],
                evidence_hash=episode_data["evidence_hash"],
                status=episode_data.get("status", "completed"),
                risk_events=episode_data.get("risk_events", 0),
                runtime_ref=episode_data.get("runtime_ref", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError(f"invalid RunStore: malformed Episode: {path.name}") from exc
        if episode.status != "completed":
            raise CliError("invalid RunStore: Episode is not completed")
        if path.name != f"{identity.key}.json":
            raise CliError("invalid RunStore: Episode filename does not match identity")
        if identity.candidate_ref not in candidate_refs:
            raise CliError("invalid RunStore: Episode candidate reference mismatch")
        expected_trace_ref = f"traces/{identity.key}.json"
        if episode.trace_ref != expected_trace_ref:
            raise CliError("invalid RunStore: Episode trace reference does not match identity")
        trace_path = _safe_artifact(store.root, episode.trace_ref)
        if not trace_path.is_file():
            raise CliError("invalid RunStore: Episode trace missing")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        sample_id = identity.sample_ref.sample_id
        if trace.get("sample_id") != sample_id:
            raise CliError("invalid RunStore: Episode trace sample mismatch")
        if trace.get("result") != episode.result:
            raise CliError("invalid RunStore: Episode result does not match Trace")
        if float(trace.get("cost_usd", 0)) != episode.cost_usd:
            raise CliError("invalid RunStore: Episode cost does not match Trace")
        if episode.evidence_hash != canonical_hash(trace):
            raise CliError("invalid RunStore: Episode evidence hash mismatch")
        if episode.risk_events != len(trace.get("risk_events", [])):
            raise CliError("invalid RunStore: Episode risk events do not match Trace")
        if runtime_ref is not None and (
            episode.runtime_ref != runtime_ref or trace.get("runtime_ref") != runtime_ref
        ):
            raise CliError("invalid RunStore: Episode runtime reference mismatch")
        episodes.append(episode_data)
    if not episodes:
        raise CliError("invalid RunStore: no Episode evidence")
    return episodes


def _evaluation_from_episodes(
    collection: SampleSetCollection,
    episodes: list[dict],
    *,
    cost_observed: bool = True,
) -> dict[str, dict[str, Any]]:
    purpose_by_ref = {
        (ref.sample_id, ref.content_hash): manifest.purpose
        for manifest in collection.manifests for ref in manifest.sample_refs
    }
    grouped: dict[SampleSetPurpose, list[dict]] = {purpose: [] for purpose in SampleSetPurpose}
    expected_sample_refs = {
        (ref.sample_id, ref.content_hash)
        for manifest in collection.manifests for ref in manifest.sample_refs
    }
    actual_sample_refs = set()
    for episode in episodes:
        ref = episode["identity"]["sample_ref"]
        actual_sample_refs.add((ref.get("sample_id"), ref.get("content_hash")))
        purpose = purpose_by_ref.get((ref.get("sample_id"), ref.get("content_hash")))
        if purpose is None:
            raise CliError("invalid RunStore: Episode references sample outside frozen sets")
        grouped[purpose].append(episode)
    if (
        actual_sample_refs != expected_sample_refs
        or len(episodes) != len(expected_sample_refs)
    ):
        raise CliError("invalid RunStore: every frozen sample requires exactly one completed Episode")
    return {
        purpose.value: summarize_episodes(
            grouped[purpose], cost_observed=cost_observed,
        )
        for purpose in SampleSetPurpose
    }


def _validate_global_evaluation_indices(
    store: RunStore,
    final_episodes: list[dict],
) -> None:
    """Keep CandidateRef + SampleRef + RunIndex unique across the whole run."""
    episode_documents = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((store.root / "training_episodes").rglob("*.json"))
    ] + list(final_episodes)
    by_unit: dict[tuple[str, str], list[int]] = {}
    for episode in episode_documents:
        identity = episode["identity"]
        sample_ref = identity["sample_ref"]
        key = (identity["candidate_ref"], sample_ref["content_hash"])
        by_unit.setdefault(key, []).append(identity["run_index"])
    if any(
        sorted(indices) != list(range(len(indices)))
        for indices in by_unit.values()
    ):
        raise CliError("invalid RunStore: global evaluation run indices are not contiguous")


def _validate_summary(
    store: RunStore,
    collection: SampleSetCollection,
    episodes: list[dict],
    acceptance: AcceptanceResult,
    *,
    cost_observed: bool = True,
) -> None:
    summary = store.load_json("summary.json")
    entries = [store.load_json(f"epochs/epoch_{epoch:03d}.json")["entry"]
               for epoch in store.epochs()]
    valid_entries = [entry for entry in entries if not entry.get("rolled_back")]
    expected = {
        "epochs_run": len(entries),
        "final_pass_rate": valid_entries[-1]["pass_rate"] if valid_entries else None,
        "final_solution_version": store.solution_versions()[-1],
        "lambda_values": entries[-1]["lambda_values"] if entries else {},
        "total_cost_usd": round(sum(float(entry.get("cost_usd", 0)) for entry in entries), 4),
        "log_chain_valid": True,
        "evaluation_by_purpose": _evaluation_from_episodes(
            collection, episodes, cost_observed=cost_observed,
        ),
        "objective_ref": acceptance.objective_ref,
        "acceptance_ref": acceptance.content_hash,
        "acceptance_met": acceptance.met,
        "acceptance_failures": list(acceptance.failures),
    }
    candidate_refs = {episode["identity"]["candidate_ref"] for episode in episodes}
    if len(candidate_refs) != 1:
        raise CliError("invalid RunStore: final evaluation mixes candidate identities")
    expected["candidate_ref"] = next(iter(candidate_refs))
    expected["candidate_frozen"] = True
    final_snapshot = store.load_json(
        f"solution_versions/v{expected['final_solution_version']:03d}.json"
    )["solution"]
    candidate_path = store.root / "candidate_manifests" / f"{expected['candidate_ref']}.json"
    if not candidate_path.is_file():
        raise CliError("invalid RunStore: final candidate manifest is missing")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if (
        candidate.get("content_hash") != expected["candidate_ref"]
        or (candidate.get("specification") or {}).get("solution_ref")
        != canonical_hash(solution_from_dict(final_snapshot))
    ):
        raise CliError("invalid RunStore: final candidate was not evaluated")
    for key, value in expected.items():
        if summary.get(key) != value:
            raise CliError(f"invalid RunStore: summary mismatch: {key}")


def _validate_evidence_manifest(store: RunStore) -> None:
    path = store.root / "evidence_package" / "manifest.json"
    if not path.is_file():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or manifest.get("content_hash") != canonical_hash(files):
        raise CliError("invalid RunStore: evidence manifest content hash mismatch")
    for relative, expected in files.items():
        artifact = _safe_artifact(store.root, relative)
        if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected:
            raise CliError(f"invalid RunStore: evidence manifest mismatch: {relative}")


def _validate_external_evaluation(
    store: RunStore,
    run: dict[str, Any],
    external_projector: ExternalEvidenceProjector | None = None,
) -> None:
    forbidden = (
        "sample_sets.json", "delivery_decision.json", "training_report.md",
        "objective.json", "acceptance.json",
        "meta_review.md", "boundary.json", "epochs", "loss_traces", "messages",
        "solution_versions", "solution_package", "evidence_package",
    )
    for relative in forbidden:
        if (store.root / relative).exists():
            raise CliError(
                f"invalid RunStore: forbidden external evaluation artifact: {relative}"
            )

    runtime_provenance = run.get("runtime_provenance")
    runtime_ref = run.get("runtime_ref")
    if (
        not isinstance(runtime_provenance, dict)
        or not isinstance(runtime_ref, str)
        or canonical_hash(runtime_provenance) != runtime_ref
    ):
        raise CliError("invalid RunStore: external runtime provenance mismatch")

    source_path = store.root / "source_results.json"
    source_results = store.load_json("source_results.json")
    expected_source_hash = run.get("source_results_content_hash")
    if expected_source_hash != canonical_hash(source_results):
        raise CliError("invalid RunStore: source results hash mismatch")
    raw_hash = run.get("source_results_sha256")
    if not isinstance(raw_hash, str) or re.fullmatch(r"[0-9a-f]{64}", raw_hash) is None:
        raise CliError("invalid RunStore: source results raw hash missing")
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != raw_hash:
        raise CliError("invalid RunStore: source results raw hash mismatch")

    try:
        candidate_data = store.load_json("candidate_manifest.json")
        candidate = CandidateManifest(
            candidate_id=candidate_data["candidate_id"],
            kind=candidate_data["kind"],
            specification=candidate_data["specification"],
            provenance_complete=candidate_data["provenance_complete"],
            content_hash=candidate_data["content_hash"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError(f"invalid RunStore: candidate manifest: {exc}") from exc
    candidate_ref = run.get("candidate_ref")
    if candidate_ref != candidate.candidate_ref:
        raise CliError("invalid RunStore: external candidate reference mismatch")
    source_projection = None
    if external_projector is not None:
        try:
            source_projection = external_projector(source_results, candidate_ref)
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError("invalid RunStore: external source projection") from exc
        if (
            source_projection.runtime_provenance != runtime_provenance
            or source_projection.runtime_ref != runtime_ref
        ):
            raise CliError("invalid RunStore: external source projection runtime mismatch")

    tasks_doc = store.load_json("task_samples.json")
    try:
        tasks = [_task_sample_from_dict(item) for item in tasks_doc.get("samples", [])]
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError(f"invalid RunStore: task samples: {exc}") from exc
    if tasks_doc.get("total") != len(tasks) or not tasks:
        raise CliError("invalid RunStore: task sample count mismatch")
    by_id = {task.id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise CliError("invalid RunStore: task sample ids must be unique")
    if source_projection is not None:
        projected_task_refs = {task.ref for task in source_projection.tasks}
        if {task.ref for task in tasks} != projected_task_refs:
            raise CliError("invalid RunStore: task samples do not match source projection")

    episodes = _validate_episodes(store, {candidate_ref}, runtime_ref=runtime_ref)
    episodes_by_key = {
        EvaluationIdentity(
            episode["identity"]["candidate_ref"],
            SampleRef(**episode["identity"]["sample_ref"]),
            episode["identity"]["run_index"],
        ).key: episode
        for episode in episodes
    }
    indices: dict[str, list[int]] = {task.id: [] for task in tasks}
    for episode in episodes:
        identity_data = episode["identity"]
        episode_ref = SampleRef(**identity_data["sample_ref"])
        task = by_id.get(episode_ref.sample_id)
        if task is None or task.ref != episode_ref:
            raise CliError("invalid RunStore: external Episode sample reference mismatch")
        indices[task.id].append(identity_data["run_index"])
    for task_id, task_indices in indices.items():
        if not task_indices:
            raise CliError(f"invalid RunStore: no Episode for task sample: {task_id}")
        if sorted(task_indices) != list(range(len(task_indices))):
            raise CliError(f"invalid RunStore: run indices are not contiguous: {task_id}")

    simulations = source_results.get("simulations") if isinstance(source_results, dict) else None
    if not isinstance(simulations, list):
        raise CliError("invalid RunStore: source results do not contain simulations")
    try:
        evidence_indices = store.external_evidence_indices()
    except (TypeError, ValueError) as exc:
        raise CliError("invalid RunStore: malformed external evidence filename") from exc
    if evidence_indices != list(range(len(simulations))):
        raise CliError("invalid RunStore: external evidence indices do not match source records")

    previous_hash = "GENESIS"
    for source_index, simulation in enumerate(simulations):
        projected = (
            source_projection.records[source_index]
            if source_projection is not None else None
        )
        record_data = store.load_json(
            f"external_evidence/record_{source_index:06d}.json"
        )
        ref_data = record_data.get("sample_ref") or {}
        try:
            record = ExternalEvidenceRecord(
                source_index=record_data["source_index"],
                source_record_hash=record_data["source_record_hash"],
                candidate_ref=record_data["candidate_ref"],
                sample_ref=SampleRef(ref_data["sample_id"], ref_data["content_hash"]),
                run_index=record_data["run_index"],
                trace_ref=record_data["trace_ref"],
                result=record_data["result"],
                cost_usd=record_data["cost_usd"],
                trace_hash=record_data["trace_hash"],
                previous_hash=record_data["previous_hash"],
                content_hash=record_data["content_hash"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError(f"invalid RunStore: malformed external evidence: {source_index}") from exc
        if record.source_index != source_index:
            raise CliError("invalid RunStore: external evidence source index mismatch")
        if record.source_record_hash != canonical_hash(simulation):
            raise CliError("invalid RunStore: external evidence source record hash mismatch")
        if record.previous_hash != previous_hash:
            raise CliError("invalid RunStore: external evidence chain mismatch")
        previous_hash = record.content_hash
        if record.candidate_ref != candidate_ref:
            raise CliError("invalid RunStore: external evidence candidate mismatch")
        task = by_id.get(record.sample_ref.sample_id)
        if task is None or task.ref != record.sample_ref:
            raise CliError("invalid RunStore: external evidence sample reference mismatch")
        identity = EvaluationIdentity(candidate_ref, record.sample_ref, record.run_index)
        episode = episodes_by_key.get(identity.key)
        if episode is None:
            raise CliError("invalid RunStore: external evidence Episode missing")
        trace = store.load_json(record.trace_ref)
        if (
            episode["trace_ref"] != record.trace_ref
            or episode["result"] != record.result
            or float(episode["cost_usd"]) != record.cost_usd
            or episode["evidence_hash"] != record.trace_hash
            or canonical_hash(trace) != record.trace_hash
        ):
            raise CliError("invalid RunStore: external evidence does not match Trace/Episode")
        if projected is not None and (
            record.sample_ref != projected.task.ref
            or record.run_index != projected.episode.identity.run_index
            or record.result != projected.episode.result
            or record.cost_usd != projected.episode.cost_usd
            or record.trace_ref != projected.episode.trace_ref
            or record.trace_hash != projected.episode.evidence_hash
            or canonical_hash(trace) != canonical_hash(projected.trace)
        ):
            raise CliError("invalid RunStore: evidence does not match source projection")

    if len(simulations) != len(episodes):
        raise CliError("invalid RunStore: source results do not match Episode count")

    evaluation = summarize_episodes(episodes)
    if source_projection is not None and evaluation != source_projection.evaluation:
        raise CliError("invalid RunStore: evaluation does not match source projection")
    summary = store.load_json("summary.json")
    expected_summary = {
        "run_kind": "external_evaluation",
        "candidate_ref": candidate_ref,
        "candidate_provenance_complete": candidate.provenance_complete,
        "total_cost_usd": evaluation["cost_usd"],
        "evaluation": evaluation,
        "evidence_records": len(simulations),
        "evidence_chain_root": previous_hash,
        "evidence_chain_valid": True,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            raise CliError(f"invalid RunStore: summary mismatch: {key}")
    config = run.get("config") or {}
    expected_trials = max(len(values) for values in indices.values())
    if config.get("num_tasks") != len(tasks) or config.get("num_trials") != expected_trials:
        raise CliError("invalid RunStore: external evaluation config mismatch")

def assert_valid_runstore(
    path: Path,
    *,
    external_projector: ExternalEvidenceProjector | None = None,
) -> RunStore:
    if not path.is_dir():
        raise CliError("invalid RunStore: directory does not exist")
    run_path = path / "run.json"
    if not run_path.is_file():
        raise CliError("invalid RunStore: required artifacts missing")
    try:
        run = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise CliError("invalid RunStore: malformed run manifest") from exc
    run_kind = run.get("run_kind", "training")
    if run_kind == "external_evaluation":
        required = (
            "task_samples.json", "source_results.json", "candidate_manifest.json",
            "external_evidence", "summary.json",
        )
        if any(not (path / name).is_file() for name in required):
            directories = {"external_evidence"}
            missing = [
                name for name in required
                if not ((path / name).is_dir() if name in directories else (path / name).is_file())
            ]
            if missing:
                raise CliError("invalid RunStore: required external evaluation artifacts missing")
        store = RunStore(path)
        _validate_material_lineage(store)
        _validate_external_evaluation(store, run, external_projector)
        return store
    if run_kind != "training":
        raise CliError(f"invalid RunStore: unsupported run kind: {run_kind}")
    if run.get("execution_scope") == "adaptation_only":
        required = (
            "run.json", "task_samples.json", "sample_sets.json",
            "capability_inventory.json", "objective.json", "summary.json",
        )
        if any(not (path / name).is_file() for name in required):
            raise CliError("invalid adaptation RunStore: required artifacts missing")
        if (
            run.get("lifecycle_state") != "IN_PROGRESS"
            or run.get("stage") != {"name": "adaptation", "state": "COMPLETE"}
            or run.get("final_evaluation_state") != "NOT_RUN"
            or run.get("delivery_state") != "NOT_REQUESTED"
        ):
            raise CliError("invalid adaptation RunStore: lifecycle state mismatch")
        forbidden = ("acceptance.json", "delivery_decision.json", "evidence_package")
        if any((path / name).exists() for name in forbidden):
            raise CliError("invalid adaptation RunStore: final-delivery artifacts are forbidden")
        store = RunStore(path)
        runtime_provenance = run.get("runtime_provenance")
        runtime_ref = run.get("runtime_ref")
        if (
            not isinstance(runtime_provenance, dict)
            or not isinstance(runtime_ref, str)
            or canonical_hash(runtime_provenance) != runtime_ref
        ):
            raise CliError("invalid adaptation RunStore: runtime provenance mismatch")
        _validate_material_lineage(store)
        _validate_capability_inventory(store)
        _validate_sample_sets(store)
        if not store.verify_hash_chain():
            raise CliError("invalid adaptation RunStore: hash chain verification failed")
        if not store.solution_versions():
            raise CliError("invalid adaptation RunStore: candidate snapshot missing")
        candidates = _validate_training_candidates(store)
        _validate_training_evidence(store, set(candidates), runtime_ref)
        summary = store.load_json("summary.json")
        epochs = store.epochs()
        if not epochs:
            raise CliError("invalid adaptation RunStore: epoch evidence missing")
        last_entry = store.load_json(f"epochs/epoch_{epochs[-1]:03d}.json")["entry"]
        total_cost = round(sum(
            float(store.load_json(f"epochs/epoch_{epoch:03d}.json")["entry"].get("cost_usd", 0))
            for epoch in epochs
        ), 4)
        if (
            summary.get("epochs_run") != len(epochs)
            or summary.get("final_pass_rate") != last_entry.get("pass_rate")
            or summary.get("total_cost_usd") != total_cost
            or summary.get("log_chain_valid") is not True
            or summary.get("evaluation_by_purpose") is not None
            or summary.get("delivery_approved") is not False
        ):
            raise CliError("invalid adaptation RunStore: summary mismatch")
        return store
    required = (
        "run.json", "task_samples.json", "sample_sets.json",
        "capability_inventory.json", "objective.json", "acceptance.json",
        "summary.json", "delivery_decision.json",
    )
    if any(not (path / name).is_file() for name in required):
        raise CliError("invalid RunStore: required artifacts missing")
    store = RunStore(path)
    runtime_provenance = run.get("runtime_provenance")
    runtime_ref = run.get("runtime_ref")
    if (
        not isinstance(runtime_provenance, dict)
        or not isinstance(runtime_ref, str)
        or canonical_hash(runtime_provenance) != runtime_ref
    ):
        raise CliError("invalid RunStore: runtime provenance mismatch")
    _validate_material_lineage(store)
    _validate_capability_inventory(store)
    collection = _validate_sample_sets(store)
    if not store.verify_hash_chain():
        raise CliError("invalid RunStore: hash chain verification failed")
    if not store.solution_versions():
        raise CliError("invalid RunStore: candidate snapshot missing")
    candidates = _validate_training_candidates(store)
    _validate_training_evidence(store, set(candidates), runtime_ref)
    episodes = _validate_episodes(store, runtime_ref=runtime_ref)
    _validate_global_evaluation_indices(store, episodes)
    cost_observed = runtime_provenance.get("cost_accounting") != "unavailable"
    evaluation_by_purpose = _evaluation_from_episodes(
        collection, episodes, cost_observed=cost_observed,
    )
    _, acceptance = _validate_objective_acceptance(store, evaluation_by_purpose)
    _validate_summary(
        store,
        collection,
        episodes,
        acceptance,
        cost_observed=cost_observed,
    )
    _validate_evidence_manifest(store)
    verify_delivery_decision(store)
    return store


def _validate(args: argparse.Namespace) -> int:
    store = assert_valid_runstore(args.run_dir)
    run = store.load_json("run.json")
    if run.get("execution_scope") == "adaptation_only":
        print("Adaptation RunStore valid (overall lifecycle IN_PROGRESS)")
    else:
        print("RunStore valid")
    return 0


def _report(args: argparse.Namespace) -> int:
    store = assert_valid_runstore(args.run_dir)
    print(generate_report(store.root))
    print(generate_dashboard(store.root))
    return 0


def _export(args: argparse.Namespace) -> int:
    store = assert_valid_runstore(args.run_dir)
    if store.load_json("run.json").get("run_kind") == "external_evaluation":
        raise CliError("external evaluation RunStore cannot be exported as an approved solution")
    decision = assert_delivery_approved(store)
    approved_version = decision["final_solution_version"]
    snapshot = store.load_json(f"solution_versions/v{approved_version:03d}.json")["solution"]
    solution = solution_from_dict(snapshot)
    write_boundary(store.root)
    print(export_package(
        solution, store.root,
        delivery_conditions=decision.get("review_conditions", []),
    ))
    print(export_evidence_package(store.root))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentfit")
    commands = parser.add_subparsers(dest="command", required=True)
    compile_cmd = commands.add_parser("compile", help="compile materials into a frozen case")
    compile_cmd.add_argument("--bundle", type=Path, required=True)
    compile_cmd.add_argument("--output", type=Path, required=True)
    compile_cmd.set_defaults(handler=_compile)
    train = commands.add_parser("train", help="train a solution from a frozen case")
    train.add_argument("--case", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    train.add_argument("--auto-approve", action="store_true", help="explicit test-only Human Gate policy")
    train.set_defaults(handler=_train)
    for name, help_text, handler in (
        ("validate", "verify a RunStore from persisted evidence", _validate),
        ("report", "render the report and dashboard", _report),
        ("export", "export solution and evidence packages", _export),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("run_dir", type=Path)
        command.set_defaults(handler=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.handler(args))
    except (CliError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
