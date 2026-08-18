#!/usr/bin/env python3
"""Import canonical AgentTeams results into an existing training RunStore.

用法：
  python bridges/agentteams/import_results.py results.json \
    --run-dir output/agentteams-run --epoch 1 --phase agentteams
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from bridges.agentteams.executor import (  # noqa: E402
    RESULT_SCHEMA,
    trace_from_result,
)
from agentfit.models.evidence import CandidateManifest  # noqa: E402
from agentfit.models.loss import Expected, ExpectedAction  # noqa: E402
from agentfit.models.sample import (  # noqa: E402
    Episode,
    EvaluationIdentity,
    ObservationRef,
    TaskSample,
    canonical_hash,
)
from agentfit.store.run_store import RunStore  # noqa: E402


_LOCK_NAME = ".agentteams-import.lock"
_JOURNAL_NAME = ".agentteams-import-journal.json"
_JOURNAL_TEMP_NAME = ".agentteams-import-journal.tmp"


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    directories = [root, *(path for path in root.rglob("*") if path.is_dir())]
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        _fsync_directory(directory)


def _safe_import_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("AgentTeams import journal path escapes RunStore")
    return root / path


def _write_import_journal(root: Path, document: dict[str, Any]) -> None:
    temporary = root / _JOURNAL_TEMP_NAME
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(document, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, root / _JOURNAL_NAME)
    _fsync_directory(root)


def _remove_empty_import_parents(root: Path, targets: list[Path]) -> None:
    parents = {
        parent
        for path in targets
        for parent in path.parents
        if parent != root and root in parent.parents
    }
    for directory in sorted(parents, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass


def _recover_interrupted_import(root: Path) -> None:
    """Roll back an uncommitted file batch or finish committed cleanup."""
    journal_path = root / _JOURNAL_NAME
    if not journal_path.exists():
        (root / _JOURNAL_TEMP_NAME).unlink(missing_ok=True)
        for staging in root.glob(".agentteams-import.*"):
            if staging.is_dir():
                shutil.rmtree(staging)
        return
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("AgentTeams import journal is malformed") from exc
    state = journal.get("state")
    relative_targets = journal.get("targets")
    staging_name = journal.get("staging")
    if (
        state not in {"publishing", "committed"}
        or not isinstance(relative_targets, list)
        or any(not isinstance(item, str) for item in relative_targets)
        or not isinstance(staging_name, str)
        or Path(staging_name).name != staging_name
        or not staging_name.startswith(".agentteams-import.")
    ):
        raise ValueError("AgentTeams import journal is invalid")
    targets = [_safe_import_path(root, relative) for relative in relative_targets]
    if state == "publishing":
        for target in reversed(targets):
            target.unlink(missing_ok=True)
        _remove_empty_import_parents(root, targets)
    shutil.rmtree(root / staging_name, ignore_errors=True)
    journal_path.unlink()
    (root / _JOURNAL_TEMP_NAME).unlink(missing_ok=True)
    _fsync_directory(root)


def _task_sample(data: dict[str, Any]) -> TaskSample:
    expected_data = data.get("expected") or {}
    expected = Expected(
        actions=[ExpectedAction(**action) for action in expected_data.get("actions", [])],
        outcome=dict(expected_data.get("outcome") or {}),
    )
    return TaskSample(
        id=data["id"],
        observation_refs=tuple(
            ObservationRef(**ref) for ref in data.get("observation_refs", [])
        ),
        input_data=dict(data.get("input_data") or {}),
        expected=expected,
        evaluator=data.get("evaluator", "exact"),
        constraints=dict(data.get("constraints") or {}),
        requires_human=bool(data.get("requires_human", False)),
        complexity=data.get("complexity", "simple"),
    )


def _candidate(data: dict[str, Any]) -> CandidateManifest:
    return CandidateManifest(
        candidate_id=data["candidate_id"],
        kind=data["kind"],
        specification=data["specification"],
        provenance_complete=data["provenance_complete"],
        content_hash=data["content_hash"],
    )


def import_results_to_runstore(
    results: list[dict[str, Any]],
    run_dir: str | Path,
    *,
    epoch: int,
    phase: str = "agentteams",
) -> int:
    """Validate a complete offline result batch, then append canonical evidence."""
    if not isinstance(results, list) or not results:
        raise ValueError("AgentTeams results must be a non-empty list")
    if not isinstance(epoch, int) or epoch < 0:
        raise ValueError("epoch must be non-negative")
    if not isinstance(phase, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", phase) is None:
        raise ValueError("phase must be one safe path segment")

    store = RunStore(run_dir)
    run = store.load_json("run.json")
    if run.get("run_kind") != "training":
        raise ValueError("AgentTeams results can only be imported into a training RunStore")
    runtime_ref = run.get("runtime_ref")
    if not isinstance(runtime_ref, str) or not runtime_ref:
        raise ValueError("training RunStore runtime_ref is required")
    runtime_provenance = run.get("runtime_provenance")
    if (
        not isinstance(runtime_provenance, dict)
        or canonical_hash(runtime_provenance) != runtime_ref
    ):
        raise ValueError("training RunStore runtime provenance does not match runtime_ref")

    tasks_document = store.load_json("task_samples.json")
    tasks = [_task_sample(item) for item in tasks_document.get("samples", [])]
    samples_by_ref = {(task.id, task.content_hash): task for task in tasks}
    if tasks_document.get("total") != len(tasks) or not tasks:
        raise ValueError("training RunStore task samples are invalid")

    candidate_dir = store.root / "candidate_manifests"
    candidates: dict[str, CandidateManifest] = {}
    for path in candidate_dir.glob("*.json"):
        manifest = _candidate(json.loads(path.read_text(encoding="utf-8")))
        if path.stem != manifest.candidate_ref:
            raise ValueError("candidate manifest filename does not match candidate")
        candidates[manifest.candidate_ref] = manifest
    if not candidates:
        raise ValueError("training RunStore has no candidate manifest")

    normalized: list[tuple[EvaluationIdentity, Any, Episode]] = []
    identities: set[str] = set()
    for result in results:
        if not isinstance(result, dict) or result.get("schema") != RESULT_SCHEMA:
            raise ValueError("AgentTeams result schema is invalid")
        if not result.get("task_id"):
            raise ValueError("AgentTeams result task_id is required")
        candidate_ref = result.get("candidate_ref")
        if candidate_ref not in candidates:
            raise ValueError("AgentTeams result candidate does not match a frozen manifest")
        sample_data = result.get("sample_ref")
        if not isinstance(sample_data, dict):
            raise ValueError("AgentTeams result sample_ref is invalid")
        sample = samples_by_ref.get((sample_data.get("sample_id"), sample_data.get("content_hash")))
        if sample is None or sample_data != asdict(sample.ref):
            raise ValueError("AgentTeams result sample does not match a frozen TaskSample")
        run_index = result.get("run_index")
        if not isinstance(run_index, int) or isinstance(run_index, bool) or run_index < 0:
            raise ValueError("AgentTeams result run_index must be non-negative")
        if result.get("runtime_ref") != runtime_ref:
            raise ValueError("AgentTeams result runtime_ref does not match the RunStore")

        identity = EvaluationIdentity(candidate_ref, sample.ref, run_index)
        if identity.key in identities:
            raise ValueError("AgentTeams result contains a duplicate evaluation identity")
        identities.add(identity.key)
        trace = trace_from_result(result, sample, runtime_ref=runtime_ref)
        if trace.error_code == "agentteams_result_contract_error":
            raise ValueError("AgentTeams result payload violates the result contract")
        trace_ref = (
            Path("training_traces") / phase / f"epoch_{epoch:03d}" / f"{identity.key}.json"
        ).as_posix()
        episode = Episode(
            identity=identity,
            trace_ref=trace_ref,
            result=trace.result,
            cost_usd=trace.cost_usd,
            evidence_hash=canonical_hash(trace),
            risk_events=len(trace.risk_events),
            runtime_ref=runtime_ref,
        )
        normalized.append((identity, trace, episode))

    lock_path = store.root / _LOCK_NAME
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_fd)
        raise ValueError("another AgentTeams result import is in progress") from exc
    metadata = json.dumps({"pid": os.getpid(), "started_at_ns": time.time_ns()}).encode()
    os.ftruncate(lock_fd, 0)
    os.write(lock_fd, metadata)
    os.fsync(lock_fd)

    staging: Path | None = None
    published: list[Path] = []
    journal_written = False
    committed = False
    try:
        _recover_interrupted_import(store.root)
        staging = Path(tempfile.mkdtemp(prefix=".agentteams-import.", dir=store.root))
        existing_identity_keys = {
            path.stem
            for evidence_root in ("training_traces", "training_episodes")
            for path in (store.root / evidence_root).rglob("*.json")
        }
        for identity, _, _ in normalized:
            if identity.key in existing_identity_keys:
                raise ValueError("AgentTeams result evaluation identity already exists")
            trace_path = store.root / "training_traces" / phase / f"epoch_{epoch:03d}" / f"{identity.key}.json"
            episode_path = store.root / "training_episodes" / phase / f"epoch_{epoch:03d}" / f"{identity.key}.json"
            if trace_path.exists() or episode_path.exists():
                raise ValueError("AgentTeams result evaluation identity already exists")

        staged_store = RunStore(staging)
        staged_paths: list[tuple[Path, Path]] = []
        for identity, trace, episode in normalized:
            staged_trace = staged_store.save_training_trace(epoch, phase, identity, trace)
            staged_episode = staged_store.save_training_episode(epoch, phase, episode)
            staged_paths.extend((
                (
                    staged_trace,
                    store.root / staged_trace.relative_to(staging),
                ),
                (
                    staged_episode,
                    store.root / staged_episode.relative_to(staging),
                ),
            ))

        journal = {
            "state": "publishing",
            "targets": [
                target.relative_to(store.root).as_posix()
                for _, target in staged_paths
            ],
            "staging": staging.name,
        }
        _fsync_tree(staging)
        _write_import_journal(store.root, journal)
        journal_written = True
        for source, target in staged_paths:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
            published.append(target)
        publication_directories = {
            parent
            for path in published
            for parent in path.parents
            if parent == store.root or store.root in parent.parents
        }
        for parent in sorted(
            publication_directories,
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            _fsync_directory(parent)
        _write_import_journal(store.root, {**journal, "state": "committed"})
        committed = True
        return len(normalized)
    except BaseException:
        if not committed:
            for path in reversed(published):
                path.unlink(missing_ok=True)
            _remove_empty_import_parents(store.root, published)
        raise
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        if journal_written:
            (store.root / _JOURNAL_NAME).unlink(missing_ok=True)
            (store.root / _JOURNAL_TEMP_NAME).unlink(missing_ok=True)
            _fsync_directory(store.root)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--epoch", required=True, type=int)
    parser.add_argument("--phase", default="agentteams")
    args = parser.parse_args()
    results = json.loads(Path(args.input).read_text(encoding="utf-8"))
    imported = import_results_to_runstore(
        results,
        args.run_dir,
        epoch=args.epoch,
        phase=args.phase,
    )
    print(f"imported {imported} AgentTeams result(s) → {args.run_dir}")


if __name__ == "__main__":
    main()
