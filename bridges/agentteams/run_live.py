#!/usr/bin/env python3
"""Provision a run-scoped AgentTeams Worker and execute a live E2 batch."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any, Callable
import urllib.parse

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from agentfit.models.evidence import CandidateManifest  # noqa: E402
from plugins.materials.compiler import compile_material_bundle  # noqa: E402
from agentfit.solution.builder import build_candidate  # noqa: E402
from bridges.agentteams.candidate_sandbox import (  # noqa: E402
    CandidateWorkerLifecycle,
    DockerAgentTeamsControl,
    render_candidate_worker,
)
from bridges.agentteams.live_batch import (  # noqa: E402
    LiveBatchOutcome,
    LiveEvaluationOutcome,
    run_adaptation_batch,
    run_full_evaluation_batch,
)
from bridges.agentteams.matrix_sandbox import (  # noqa: E402
    MatrixHttpTransport,
    MatrixSandboxAdapter,
    MatrixTransport,
    load_manager_matrix_credentials,
)


@dataclass(frozen=True)
class LiveRunOutcome:
    batch: LiveBatchOutcome | LiveEvaluationOutcome
    worker_name: str
    worker_retired: bool


def _candidate_ref(bundle: dict[str, Any]) -> str:
    compiled = compile_material_bundle(bundle)
    solution = build_candidate(
        list(compiled.task_samples),
        compiled.sample_sets,
        compiled.capability_inventory,
    )
    return CandidateManifest.for_solution(solution).candidate_ref


def run_live_agentteams_batch(
    bundle: dict[str, Any],
    run_dir: str | Path,
    *,
    run_id: str,
    model_ref: str,
    manager_container: str = "agentteams-manager",
    homeserver: str = "http://127.0.0.1:18080",
    auto_approve: bool = False,
    final_evaluation: bool = False,
    keep_sandbox: bool = False,
    lifecycle: CandidateWorkerLifecycle | None = None,
    transport: MatrixTransport | None = None,
    batch_runner: Callable[..., LiveBatchOutcome | LiveEvaluationOutcome] | None = None,
    ready_timeout_seconds: float = 180,
) -> LiveRunOutcome:
    if not run_id.strip():
        raise ValueError("run_id is required")
    candidate_ref = _candidate_ref(bundle)
    manifest = render_candidate_worker(
        candidate_ref=candidate_ref,
        run_id=run_id,
        model_ref=model_ref,
    )
    active_lifecycle = lifecycle or CandidateWorkerLifecycle(
        DockerAgentTeamsControl(manager_container)
    )
    worker_name = manifest["metadata"]["name"]
    try:
        endpoint = active_lifecycle.provision(
            manifest,
            timeout_seconds=ready_timeout_seconds,
        )
    except BaseException:
        active_lifecycle.retire_if_present(
            worker_name,
            timeout_seconds=ready_timeout_seconds,
        )
        raise
    retired = False
    try:
        active_transport = transport
        if active_transport is None:
            credentials = load_manager_matrix_credentials(
                manager_container=manager_container,
                homeserver_override=homeserver,
            )
            active_transport = MatrixHttpTransport(credentials)
        sandbox = MatrixSandboxAdapter(
            active_transport,
            room_id=endpoint.room_id,
            worker_user_id=endpoint.matrix_user_id,
        )
        encoded_run = urllib.parse.quote(run_id, safe="")
        encoded_room = urllib.parse.quote(endpoint.room_id, safe="")
        active_batch_runner = batch_runner or (
            run_full_evaluation_batch if final_evaluation else run_adaptation_batch
        )
        batch = active_batch_runner(
            bundle,
            run_dir,
            sandbox,
            deployment_ref=f"agentteams://worker/{endpoint.name}",
            sandbox_ref=(
                f"agentteams://worker/{endpoint.name}?run={encoded_run}&room={encoded_room}"
            ),
            model_ref=model_ref,
            auto_approve=auto_approve,
        )
    finally:
        if not keep_sandbox:
            active_lifecycle.retire(
                endpoint.name,
                timeout_seconds=ready_timeout_seconds,
            )
            retired = True
    return LiveRunOutcome(batch, endpoint.name, retired)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an adaptation batch through a temporary AgentTeams Worker",
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--manager-container", default="agentteams-manager")
    parser.add_argument("--homeserver", default="http://127.0.0.1:18080")
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument(
        "--final-evaluation",
        action="store_true",
        help="freeze the adapted candidate and evaluate all four sample sets",
    )
    parser.add_argument("--keep-sandbox", action="store_true")
    parser.add_argument("--ready-timeout-seconds", type=float, default=180)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    outcome = run_live_agentteams_batch(
        bundle,
        args.output,
        run_id=args.run_id,
        model_ref=args.model,
        manager_container=args.manager_container,
        homeserver=args.homeserver,
        auto_approve=args.auto_approve,
        final_evaluation=args.final_evaluation,
        keep_sandbox=args.keep_sandbox,
        ready_timeout_seconds=args.ready_timeout_seconds,
    )
    payload = {
        "run_dir": str(outcome.batch.run_dir),
        "candidate_ref": outcome.batch.candidate_ref,
        "epochs_run": outcome.batch.epochs_run,
        "pass_rate": outcome.batch.pass_rate,
        "execution_errors": outcome.batch.execution_errors,
        "worker_name": outcome.worker_name,
        "worker_retired": outcome.worker_retired,
    }
    if isinstance(outcome.batch, LiveEvaluationOutcome):
        payload.update({
            "acceptance_met": outcome.batch.acceptance_met,
            "delivery_approved": outcome.batch.delivery_approved,
            "evaluation_by_purpose": outcome.batch.evaluation_by_purpose,
        })
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
