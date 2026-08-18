#!/usr/bin/env python3
"""桥接：tau2-bench results.json → AgentFit RunStore 标准目录（可出 dashboard）。

用法：
  PYTHONPATH=src python bridges/tau2bench/results_to_runstore.py \
      ../tau2-bench/data/simulations/agentfit-smoke-001/results.json \
      --run-dir output/tau2-smoke-001 --candidate-spec candidate.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from bridges.tau2bench.projector import (project_results,  # noqa: E402
                                          simulation_to_episode,
                                          simulation_to_task_sample)
from agentfit.store.run_store import RunStore  # noqa: E402
from agentfit.models.evidence import (CandidateManifest,  # noqa: E402
                                      ExternalEvidenceRecord)
from agentfit.models.loss import Trace  # noqa: E402
from agentfit.models.sample import Episode, canonical_hash  # noqa: E402


def validate(run_dir: str | Path) -> RunStore:
    """Run core integrity checks plus the tau2 source-semantics projector."""
    from agentfit.cli import assert_valid_runstore

    return assert_valid_runstore(
        Path(run_dir), external_projector=project_results,
    )


def candidate_from_declaration(data: object) -> CandidateManifest:
    """Build or restore a semantic candidate identity declared by the caller."""
    if not isinstance(data, dict):
        raise TypeError("candidate declaration must be an object, not a display label")
    candidate_id = data.get("candidate_id")
    kind = data.get("kind")
    specification = data.get("specification")
    provenance_complete = data.get("provenance_complete")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise TypeError("candidate declaration candidate_id must be a non-empty string")
    if not isinstance(kind, str) or not kind:
        raise TypeError("candidate declaration kind must be a non-empty string")
    if not isinstance(specification, dict):
        raise TypeError("candidate declaration specification must be an object")
    content_hash = data.get("content_hash")
    if content_hash is not None:
        return CandidateManifest(
            candidate_id=candidate_id,
            kind=kind,
            specification=specification,
            provenance_complete=provenance_complete,
            content_hash=content_hash,
        )
    return CandidateManifest.create(
        candidate_id=candidate_id,
        kind=kind,
        specification=specification,
        provenance_complete=provenance_complete,
    )


def convert(results_path: Path, run_dir: str, candidate_declaration: object) -> None:
    raw_results = results_path.read_bytes()
    data = json.loads(raw_results)
    target = Path(run_dir)
    if target.exists():
        raise ValueError(f"RunStore already exists: {target}")
    candidate = candidate_from_declaration(candidate_declaration)
    candidate_ref = candidate.candidate_ref
    projection = project_results(data, candidate_ref)
    normalized: list[tuple[Episode, Trace, ExternalEvidenceRecord]] = []
    previous_hash = "GENESIS"
    for projected in projection.records:
        episode, trace = projected.episode, projected.trace
        record = ExternalEvidenceRecord.create(
            source_index=projected.source_index,
            source_record_hash=canonical_hash(data["simulations"][projected.source_index]),
            candidate_ref=candidate_ref,
            sample_ref=projected.task.ref,
            run_index=episode.identity.run_index,
            trace_ref=episode.trace_ref,
            result=episode.result,
            cost_usd=episode.cost_usd,
            trace_hash=canonical_hash(trace),
            previous_hash=previous_hash,
        )
        previous_hash = record.content_hash
        normalized.append((episode, trace, record))
    total_cost = float(projection.evaluation["cost_usd"])
    summary = {
        "run_kind": "external_evaluation",
        "candidate_ref": candidate_ref,
        "candidate_provenance_complete": candidate.provenance_complete,
        "evaluation": projection.evaluation,
        "total_cost_usd": round(total_cost, 4),
        "evidence_records": len(normalized),
        "evidence_chain_root": previous_hash,
        "evidence_chain_valid": True,
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        store = RunStore(temporary)
        store.init_run({
            "run_kind": "external_evaluation",
            "scenario": f"tau2-telecom-baseline:{candidate.candidate_id}",
            "executor": "tau2bench-bridge",
            "config": {
                "num_tasks": len(projection.tasks),
                "num_trials": projection.num_trials,
            },
            "candidate_ref": candidate_ref,
            "runtime_provenance": projection.runtime_provenance,
            "runtime_ref": projection.runtime_ref,
            "source_results_sha256": hashlib.sha256(raw_results).hexdigest(),
            "source_results_content_hash": canonical_hash(data),
        })
        store.save_source_results_bytes(raw_results)
        store.save_candidate_manifest(candidate)
        store.save_task_samples(list(projection.tasks))
        for episode, trace, record in normalized:
            trace_path = store.save_trace(episode.identity, trace)
            if episode.trace_ref != trace_path.relative_to(store.root).as_posix():
                raise ValueError("τ² trace reference does not match persisted trace")
            store.save_episode(episode)
            store.save_external_evidence(record)
        store.save_summary(summary)

        validate(temporary)
        if target.exists():
            raise ValueError(f"RunStore already exists: {target}")
        temporary.rename(target)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_json", nargs="?")
    parser.add_argument("--run-dir")
    parser.add_argument(
        "--candidate-spec", type=Path,
        help="JSON declaration or complete CandidateManifest for the system under test",
    )
    parser.add_argument(
        "--validate-run-dir", type=Path,
        help="revalidate an existing tau2 RunStore against its raw source projection",
    )
    args = parser.parse_args()
    if args.validate_run_dir is not None:
        if args.results_json is not None or args.run_dir is not None or args.candidate_spec is not None:
            parser.error("--validate-run-dir cannot be combined with conversion arguments")
        validate(args.validate_run_dir)
        print(f"source projection valid: {args.validate_run_dir}")
        return
    if args.results_json is None or args.run_dir is None or args.candidate_spec is None:
        parser.error("conversion requires results_json, --run-dir and --candidate-spec")
    declaration = json.loads(args.candidate_spec.read_text(encoding="utf-8"))
    convert(Path(args.results_json), args.run_dir, declaration)
    print(f"RunStore: {args.run_dir}")


if __name__ == "__main__":
    main()
