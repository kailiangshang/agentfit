"""Stable platform-independent AgentFit command line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .agents.orchestrator import Orchestrator
from .agents.team import build_team
from .dashboard import generate_dashboard
from .data.sample_pool import SamplePool
from .delivery.boundary import write_boundary
from .delivery.package import export_evidence_package, export_package
from .executors.simulator import SimulatorExecutor
from .log.report import generate_report
from .models.config import AutoApprove, TrainingConfig
from .models.loss import Expected, ExpectedAction, Sample
from .models.manifest import (
    FreezeDecision, SampleSetCollection, SampleSetManifest, SampleSetPurpose,
    default_access_policy,
)
from .models.sample import Episode, EvaluationIdentity, canonical_hash, task_sample_from_legacy
from .models.solution import solution_from_dict
from .solution.builder import build_candidate
from .store.run_store import RunStore


class CliError(ValueError):
    pass


def _read_case(path: Path) -> tuple[dict[str, Any], list[Sample], SampleSetCollection]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid case: {exc}") from exc
    samples: list[Sample] = []
    for item in doc.get("samples", []):
        actions = [ExpectedAction(**action) for action in item.get("expected", {}).get("actions", [])]
        if not actions:
            raise CliError(f"sample {item.get('id', '<missing>')} has no expected actions")
        samples.append(Sample(
            id=item["id"],
            features=dict(item.get("features", {})),
            expected=Expected(actions=actions, outcome=dict(item.get("expected", {}).get("outcome", {}))),
            requires_human=bool(item.get("requires_human", False)),
            complexity=item.get("complexity", "simple"),
            group="catalog",
        ))
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
    for run_index, sample in enumerate(adaptation):
        trace = executor.execute(orchestrator.solution, sample)
        sample_ref = task_sample_from_legacy(sample).ref
        identity = EvaluationIdentity(candidate_ref, sample_ref, run_index)
        trace_path = store.save_trace(identity, trace)
        episode = Episode(
            identity=identity,
            trace_ref=trace_path.relative_to(store.root).as_posix(),
            result=trace.result,
            cost_usd=trace.cost_usd,
            evidence_hash=canonical_hash(trace),
        )
        store.save_episode(episode)
    print(args.output)
    return 0


def _validate_sample_sets(store: RunStore) -> None:
    doc = store.load_json("sample_sets.json")
    manifests = doc.get("manifests", [])
    if len(manifests) != 4 or {item.get("purpose") for item in manifests} != {p.value for p in SampleSetPurpose}:
        raise CliError("invalid RunStore: sample-set contract")
    for item in manifests:
        if not item.get("content_hash") or not item.get("freeze", {}).get("approved"):
            raise CliError("invalid RunStore: sample-set freeze evidence")


def _assert_valid_runstore(path: Path) -> RunStore:
    if not path.is_dir():
        raise CliError("invalid RunStore: directory does not exist")
    required = ("run.json", "samples.json", "sample_sets.json", "summary.json")
    if any(not (path / name).is_file() for name in required):
        raise CliError("invalid RunStore: required artifacts missing")
    store = RunStore(path)
    _validate_sample_sets(store)
    if not store.verify_hash_chain():
        raise CliError("invalid RunStore: hash chain verification failed")
    if not store.solution_versions():
        raise CliError("invalid RunStore: candidate snapshot missing")
    return store


def _validate(args: argparse.Namespace) -> int:
    _assert_valid_runstore(args.run_dir)
    print("RunStore valid")
    return 0


def _report(args: argparse.Namespace) -> int:
    store = _assert_valid_runstore(args.run_dir)
    print(generate_report(store.root))
    print(generate_dashboard(store.root))
    return 0


def _export(args: argparse.Namespace) -> int:
    store = _assert_valid_runstore(args.run_dir)
    latest = store.solution_versions()[-1]
    snapshot = store.load_json(f"solution_versions/v{latest:03d}.json")["solution"]
    solution = solution_from_dict(snapshot)
    write_boundary(store.root)
    print(export_package(solution, store.root))
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
    except (CliError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
