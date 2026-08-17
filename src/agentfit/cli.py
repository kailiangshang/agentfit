"""Stable platform-independent AgentFit command line interface."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .agents.orchestrator import Orchestrator
from .agents.team import build_team
from .dashboard import generate_dashboard
from .data.sample_pool import SamplePool
from .delivery.approval import assert_delivery_approved, verify_delivery_decision
from .delivery.boundary import write_boundary
from .delivery.package import export_evidence_package, export_package
from .executors.simulator import SimulatorExecutor
from .log.report import generate_report
from .models.config import AutoApprove, TrainingConfig
from .models.loss import Expected, ExpectedAction, Sample
from .models.manifest import (
    AccessPolicy, FreezeDecision, SampleSetCollection, SampleSetManifest,
    SampleSetPurpose, default_access_policy,
)
from .models.sample import (Episode, EvaluationIdentity, SampleRef, canonical_hash,
                            task_sample_from_legacy)
from .models.solution import solution_from_dict
from .solution.builder import build_candidate
from .store.run_store import RunStore


class CliError(ValueError):
    pass


def _sample_from_dict(item: dict[str, Any], *, group: str = "catalog") -> Sample:
    actions = [ExpectedAction(**action) for action in item.get("expected", {}).get("actions", [])]
    if not actions:
        raise CliError(f"sample {item.get('id', '<missing>')} has no expected actions")
    return Sample(
        id=item["id"],
        features=dict(item.get("features", {})),
        expected=Expected(actions=actions, outcome=dict(item.get("expected", {}).get("outcome", {}))),
        requires_human=bool(item.get("requires_human", False)),
        complexity=item.get("complexity", "simple"),
        group=group,
    )


def _read_case(path: Path) -> tuple[dict[str, Any], list[Sample], SampleSetCollection]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid case: {exc}") from exc
    samples = [_sample_from_dict(item) for item in doc.get("samples", [])]
    if not samples:
        raise CliError("case has no samples")
    by_id = {sample.id: sample for sample in samples}
    if len(by_id) != len(samples):
        raise CliError("sample ids must be unique")

    manifests = []
    for item in doc.get("sample_sets", []):
        purpose = SampleSetPurpose(item["purpose"])
        try:
            refs = tuple(task_sample_from_legacy(by_id[sample_id]).ref for sample_id in item["sample_ids"])
        except KeyError as exc:
            raise CliError(f"sample set references unknown sample: {exc.args[0]}") from exc
        freeze_data = item.get("freeze")
        freeze = FreezeDecision(**freeze_data) if freeze_data else None
        manifests.append(SampleSetManifest.create(
            purpose, refs, default_access_policy(purpose), freeze,
        ))
    try:
        collection = SampleSetCollection(tuple(manifests))
        collection.assert_ready_for_candidate_generation()
    except (ValueError, PermissionError) as exc:
        raise CliError(f"invalid sample sets: {exc}") from exc
    return doc, samples, collection


def _adaptation_samples(samples: list[Sample], collection: SampleSetCollection) -> list[Sample]:
    adaptation = collection.by_purpose(SampleSetPurpose.ADAPTATION)
    ids = {ref.sample_id for ref in adaptation.sample_refs}
    return [Sample(
        id=sample.id, features=sample.features, expected=sample.expected,
        requires_human=sample.requires_human, complexity=sample.complexity, group="train",
    ) for sample in samples if sample.id in ids]


def _train(args: argparse.Namespace) -> int:
    if args.output.exists():
        raise CliError(f"output already exists: {args.output}")
    doc, samples, collection = _read_case(args.case)
    adaptation = _adaptation_samples(samples, collection)
    solution = build_candidate(samples, collection)
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
    store.save_samples(samples)
    store.save_sample_manifests(collection)
    candidate_ref = canonical_hash(orchestrator.solution)
    by_id = {sample.id: sample for sample in samples}
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
            trace = executor.execute(orchestrator.solution, sample)
            identity = EvaluationIdentity(candidate_ref, sample_ref, 0)
            trace_path = store.save_trace(identity, trace)
            episode = Episode(
                identity=identity,
                trace_ref=trace_path.relative_to(store.root).as_posix(),
                result=trace.result,
                cost_usd=trace.cost_usd,
                evidence_hash=canonical_hash(trace),
            )
            store.save_episode(episode)
            results.append(episode)
        evaluation_by_purpose[manifest.purpose.value] = _purpose_metrics(results)
    orchestrator.finalize_delivery({
        "candidate_ref": candidate_ref,
        "candidate_frozen": True,
        "evaluation_by_purpose": evaluation_by_purpose,
    })
    print(args.output)
    return 0


def _purpose_metrics(episodes: list[Episode] | list[dict]) -> dict[str, Any]:
    results = [episode.result if isinstance(episode, Episode) else episode["result"]
               for episode in episodes]
    costs = [episode.cost_usd if isinstance(episode, Episode) else float(episode.get("cost_usd", 0))
             for episode in episodes]
    total = len(results)
    passed = results.count("PASS")
    return {
        "total": total,
        "passed": passed,
        "failed": results.count("FAIL"),
        "errors": results.count("ERROR"),
        "pass_rate": passed / total if total else None,
        "cost_usd": round(sum(costs), 4),
    }


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
        samples_doc = store.load_json("samples.json")
        samples = [_sample_from_dict(item, group=item.get("group", "catalog"))
                   for item in samples_doc.get("samples", [])]
    except (KeyError, TypeError, CliError) as exc:
        raise CliError(f"invalid RunStore: samples: {exc}") from exc
    actual_refs = {sample.id: task_sample_from_legacy(sample).ref for sample in samples}
    for manifest in collection.manifests:
        for ref in manifest.sample_refs:
            if ref.sample_id not in actual_refs or actual_refs[ref.sample_id] != ref:
                raise CliError(f"invalid RunStore: sample reference mismatch: {ref.sample_id}")
    return collection


def _safe_artifact(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise CliError("invalid RunStore: evidence path escapes root")
    return root / rel


def _validate_episodes(store: RunStore) -> list[dict]:
    candidate_refs = set()
    for version in store.solution_versions():
        snapshot = store.load_json(f"solution_versions/v{version:03d}.json")["solution"]
        candidate_refs.add(canonical_hash(solution_from_dict(snapshot)))
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
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError(f"invalid RunStore: malformed Episode: {path.name}") from exc
        if episode.status != "completed":
            raise CliError("invalid RunStore: Episode is not completed")
        if path.name != f"{identity.key}.json":
            raise CliError("invalid RunStore: Episode filename does not match identity")
        if identity.candidate_ref not in candidate_refs:
            raise CliError("invalid RunStore: Episode candidate snapshot mismatch")
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
        expected_trace_result = "PASS" if episode.result == "PASS" else "FAIL"
        if trace.get("result") != expected_trace_result:
            raise CliError("invalid RunStore: Episode result does not match Trace")
        if float(trace.get("cost_usd", 0)) != episode.cost_usd:
            raise CliError("invalid RunStore: Episode cost does not match Trace")
        if episode.evidence_hash != canonical_hash(trace):
            raise CliError("invalid RunStore: Episode evidence hash mismatch")
        episodes.append(episode_data)
    if not episodes:
        raise CliError("invalid RunStore: no Episode evidence")
    return episodes


def _evaluation_from_episodes(collection: SampleSetCollection,
                              episodes: list[dict]) -> dict[str, dict[str, Any]]:
    purpose_by_ref = {
        (ref.sample_id, ref.content_hash): manifest.purpose
        for manifest in collection.manifests for ref in manifest.sample_refs
    }
    grouped: dict[SampleSetPurpose, list[dict]] = {purpose: [] for purpose in SampleSetPurpose}
    expected_identities = {
        (ref.sample_id, ref.content_hash, 0)
        for manifest in collection.manifests for ref in manifest.sample_refs
    }
    actual_identities = set()
    for episode in episodes:
        ref = episode["identity"]["sample_ref"]
        actual_identities.add((
            ref.get("sample_id"), ref.get("content_hash"), episode["identity"].get("run_index"),
        ))
        purpose = purpose_by_ref.get((ref.get("sample_id"), ref.get("content_hash")))
        if purpose is None:
            raise CliError("invalid RunStore: Episode references sample outside frozen sets")
        grouped[purpose].append(episode)
    if actual_identities != expected_identities or len(episodes) != len(expected_identities):
        raise CliError("invalid RunStore: every frozen sample requires exactly one completed Episode")
    return {purpose.value: _purpose_metrics(grouped[purpose]) for purpose in SampleSetPurpose}


def _validate_summary(store: RunStore, collection: SampleSetCollection,
                      episodes: list[dict]) -> None:
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
        "evaluation_by_purpose": _evaluation_from_episodes(collection, episodes),
    }
    candidate_refs = {episode["identity"]["candidate_ref"] for episode in episodes}
    if len(candidate_refs) != 1:
        raise CliError("invalid RunStore: final evaluation mixes candidate identities")
    expected["candidate_ref"] = next(iter(candidate_refs))
    expected["candidate_frozen"] = True
    final_snapshot = store.load_json(
        f"solution_versions/v{expected['final_solution_version']:03d}.json"
    )["solution"]
    if canonical_hash(solution_from_dict(final_snapshot)) != expected["candidate_ref"]:
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


def assert_valid_runstore(path: Path) -> RunStore:
    if not path.is_dir():
        raise CliError("invalid RunStore: directory does not exist")
    required = (
        "run.json", "samples.json", "sample_sets.json", "summary.json",
        "delivery_decision.json",
    )
    if any(not (path / name).is_file() for name in required):
        raise CliError("invalid RunStore: required artifacts missing")
    store = RunStore(path)
    collection = _validate_sample_sets(store)
    if not store.verify_hash_chain():
        raise CliError("invalid RunStore: hash chain verification failed")
    if not store.solution_versions():
        raise CliError("invalid RunStore: candidate snapshot missing")
    episodes = _validate_episodes(store)
    _validate_summary(store, collection, episodes)
    _validate_evidence_manifest(store)
    verify_delivery_decision(store)
    return store


def _validate(args: argparse.Namespace) -> int:
    assert_valid_runstore(args.run_dir)
    print("RunStore valid")
    return 0


def _report(args: argparse.Namespace) -> int:
    store = assert_valid_runstore(args.run_dir)
    print(generate_report(store.root))
    print(generate_dashboard(store.root))
    return 0


def _export(args: argparse.Namespace) -> int:
    store = assert_valid_runstore(args.run_dir)
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
