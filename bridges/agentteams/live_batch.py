#!/usr/bin/env python3
"""Run an adaptation batch through a live AgentTeams SandboxAdapter."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentfit.adapters.protocols import SandboxAdapter
from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.data.sample_pool import SamplePool
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.models.evidence import CandidateManifest
from agentfit.models.manifest import SampleSetPurpose
from agentfit.models.objective import evaluate_acceptance, summarize_episodes
from agentfit.models.sample import Episode, canonical_hash
from plugins.materials.compiler import compile_material_bundle
from agentfit.solution.builder import build_candidate
from agentfit.store.run_store import RunStore
from plugins.dashboard.generate import generate_dashboard
from plugins.report import generate_report

from bridges.agentteams.executor import AgentTeamsSandboxExecutor


@dataclass(frozen=True)
class LiveBatchOutcome:
    run_dir: Path
    candidate_ref: str
    epochs_run: int
    pass_rate: float
    execution_errors: int


@dataclass(frozen=True)
class LiveEvaluationOutcome:
    run_dir: Path
    candidate_ref: str
    epochs_run: int
    pass_rate: float
    execution_errors: int
    acceptance_met: bool
    delivery_approved: bool
    evaluation_by_purpose: dict[str, dict[str, Any]]


def run_adaptation_batch(
    bundle: dict[str, Any],
    run_dir: str | Path,
    sandbox: SandboxAdapter,
    *,
    deployment_ref: str,
    sandbox_ref: str,
    model_ref: str,
    auto_approve: bool = False,
) -> LiveBatchOutcome:
    """Compile, run and persist one live adaptation-only training batch.

    Final validation, sealed holdout, stress evaluation and G3 are deliberately
    outside this E2 entry point.
    """
    output = Path(run_dir)
    if output.exists():
        raise FileExistsError(f"run directory already exists: {output}")
    compiled = compile_material_bundle(bundle)
    all_samples = list(compiled.task_samples)
    adaptation_ids = {
        ref.sample_id
        for ref in compiled.sample_sets.by_purpose(
            SampleSetPurpose.ADAPTATION
        ).sample_refs
    }
    adaptation = [sample for sample in all_samples if sample.id in adaptation_ids]
    solution = build_candidate(
        all_samples,
        compiled.sample_sets,
        compiled.capability_inventory,
    )
    executor = AgentTeamsSandboxExecutor(
        sandbox,
        deployment_ref=deployment_ref,
        sandbox_ref=sandbox_ref,
        model_ref=model_ref,
        binding_mode="semantic_dry_run",
        cost_accounting="unavailable",
    )
    training = compiled.training
    config_args: dict[str, Any] = {
        "batch_size": int(training.get("batch_size", len(adaptation))),
        "max_epochs": int(training.get("max_epochs", 1)),
    }
    if auto_approve:
        config_args["review_policy"] = AutoApprove()
    orchestrator = Orchestrator(
        solution,
        SamplePool(adaptation),
        executor,
        TrainingConfig(**config_args),
        run_dir=str(output),
        scenario=compiled.scenario,
    )
    store = RunStore(output)
    run_manifest = store.load_json("run.json")
    run_manifest.update({
        "execution_scope": "adaptation_only",
        "lifecycle_state": "IN_PROGRESS",
        "stage": {"name": "adaptation", "state": "RUNNING"},
        "final_evaluation_state": "NOT_RUN",
        "delivery_state": "NOT_REQUESTED",
    })
    store.init_run(run_manifest)
    build_team(orchestrator)
    try:
        outcomes = orchestrator.train()
    except BaseException:
        run_manifest["stage"] = {"name": "adaptation", "state": "FAILED"}
        store.init_run(run_manifest)
        raise

    store.save_task_samples(all_samples)
    store.save_source_observations(list(compiled.observations))
    store.save_sample_manifests(compiled.sample_sets)
    store.save_capability_inventory(compiled.capability_inventory)
    store.save_objective(compiled.objective_spec)
    candidate = CandidateManifest.for_solution(orchestrator.solution)
    store.save_training_candidate_manifest(candidate)
    run_manifest["stage"] = {"name": "adaptation", "state": "COMPLETE"}
    store.init_run(run_manifest)
    generate_report(output)
    generate_dashboard(output)
    final = outcomes[-1]
    return LiveBatchOutcome(
        run_dir=output,
        candidate_ref=candidate.candidate_ref,
        epochs_run=len(outcomes),
        pass_rate=final.pass_rate,
        execution_errors=sum(item.execution_errors for item in outcomes),
    )


def run_full_evaluation_batch(
    bundle: dict[str, Any],
    run_dir: str | Path,
    sandbox: SandboxAdapter,
    *,
    deployment_ref: str,
    sandbox_ref: str,
    model_ref: str,
    auto_approve: bool = False,
) -> LiveEvaluationOutcome:
    """Train on adaptation, freeze the candidate, then evaluate four sets."""
    output = Path(run_dir)
    if output.exists():
        raise FileExistsError(f"run directory already exists: {output}")
    compiled = compile_material_bundle(bundle)
    all_samples = list(compiled.task_samples)
    adaptation_ids = {
        ref.sample_id
        for ref in compiled.sample_sets.by_purpose(
            SampleSetPurpose.ADAPTATION
        ).sample_refs
    }
    adaptation = [sample for sample in all_samples if sample.id in adaptation_ids]
    solution = build_candidate(
        all_samples,
        compiled.sample_sets,
        compiled.capability_inventory,
    )
    executor = AgentTeamsSandboxExecutor(
        sandbox,
        deployment_ref=deployment_ref,
        sandbox_ref=sandbox_ref,
        model_ref=model_ref,
        binding_mode="semantic_dry_run",
        cost_accounting="unavailable",
    )
    training = compiled.training
    config_args: dict[str, Any] = {
        "batch_size": int(training.get("batch_size", len(adaptation))),
        "max_epochs": int(training.get("max_epochs", 1)),
    }
    if auto_approve:
        config_args["review_policy"] = AutoApprove()
    orchestrator = Orchestrator(
        solution,
        SamplePool(adaptation),
        executor,
        TrainingConfig(**config_args),
        run_dir=str(output),
        scenario=compiled.scenario,
    )
    store = RunStore(output)
    run_manifest = store.load_json("run.json")
    run_manifest.update({
        "execution_scope": "full_evaluation",
        "lifecycle_state": "IN_PROGRESS",
        "stage": {"name": "adaptation", "state": "RUNNING"},
        "final_evaluation_state": "NOT_RUN",
        "delivery_state": "NOT_REQUESTED",
    })
    store.init_run(run_manifest)
    build_team(orchestrator)
    try:
        outcomes = orchestrator.train()
    except BaseException:
        run_manifest["stage"] = {"name": "adaptation", "state": "FAILED"}
        store.init_run(run_manifest)
        raise

    store.save_task_samples(all_samples)
    store.save_source_observations(list(compiled.observations))
    store.save_sample_manifests(compiled.sample_sets)
    store.save_capability_inventory(compiled.capability_inventory)
    store.save_objective(compiled.objective_spec)
    candidate = CandidateManifest.for_solution(orchestrator.solution)
    store.save_training_candidate_manifest(candidate)
    run_manifest.update({
        "stage": {"name": "adaptation", "state": "COMPLETE"},
        "candidate_frozen": True,
        "candidate_ref": candidate.candidate_ref,
        "final_evaluation_state": "RUNNING",
    })
    store.init_run(run_manifest)

    by_id = {sample.id: sample for sample in all_samples}
    actors = {
        SampleSetPurpose.ADAPTATION: "architect",
        SampleSetPurpose.VALIDATION: "validator",
        SampleSetPurpose.SEALED_HOLDOUT: "auditor",
        SampleSetPurpose.STRESS_AND_FAILURE: "auditor",
    }
    evaluation_by_purpose: dict[str, dict[str, Any]] = {}
    try:
        for manifest in compiled.sample_sets.manifests:
            manifest.require_access(actors[manifest.purpose], candidate_frozen=True)
            episodes: list[Episode] = []
            for sample_ref in manifest.sample_refs:
                sample = by_id[sample_ref.sample_id]
                trace, identity = orchestrator.execute_evaluation(
                    orchestrator.solution, sample,
                )
                if (
                    identity.candidate_ref != candidate.candidate_ref
                    or identity.sample_ref != sample_ref
                ):
                    raise ValueError("final evaluation identity drift")
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
                episodes.append(episode)
            evaluation_by_purpose[manifest.purpose.value] = summarize_episodes(
                episodes,
                cost_observed=False,
            )
    except BaseException:
        run_manifest["final_evaluation_state"] = "FAILED"
        store.init_run(run_manifest)
        raise

    acceptance = evaluate_acceptance(
        compiled.objective_spec,
        evaluation_by_purpose,
    )
    store.save_acceptance(acceptance)
    run_manifest.update({
        "lifecycle_state": "COMPLETE",
        "final_evaluation_state": "COMPLETE",
        "delivery_state": "G3_REVIEW_COMPLETE",
    })
    store.init_run(run_manifest)
    try:
        decision = orchestrator.finalize_delivery({
            "candidate_ref": candidate.candidate_ref,
            "candidate_frozen": True,
            "evaluation_by_purpose": evaluation_by_purpose,
            "objective_ref": compiled.objective_spec.content_hash,
            "acceptance_ref": acceptance.content_hash,
            "acceptance_met": acceptance.met,
            "acceptance_failures": list(acceptance.failures),
        })
    except BaseException:
        run_manifest["delivery_state"] = "G3_REVIEW_FAILED"
        store.init_run(run_manifest)
        raise
    generate_report(output)
    generate_dashboard(output)
    final = outcomes[-1]
    return LiveEvaluationOutcome(
        run_dir=output,
        candidate_ref=candidate.candidate_ref,
        epochs_run=len(outcomes),
        pass_rate=final.pass_rate,
        execution_errors=sum(item.execution_errors for item in outcomes),
        acceptance_met=acceptance.met,
        delivery_approved=decision.approved,
        evaluation_by_purpose=evaluation_by_purpose,
    )
