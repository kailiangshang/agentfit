"""Regression tests for evidence that must remain truthful and reproducible."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.core.regularization import LambdaController, RegReport
from agentfit.data.sample_pool import SamplePool
from agentfit.delivery.package import analyze_boundary, export_package
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.models.loss import Expected, Sample
from agentfit.store.run_store import RunStore

from telecom_world import make_initial_solution, make_samples


REPO = Path(__file__).resolve().parents[1]


def test_lambda_ignores_layers_without_violations() -> None:
    report = RegReport(
        layer_reg={"L1": 0.5, "L2": 0.0, "L3": 0.0, "L4": 0.0},
        over_threshold={"L1": ["atom_scarcity"], "L2": [], "L3": [], "L4": []},
    )
    controller = LambdaController()
    controller.observe(report)
    lambdas, events = controller.observe(report)
    assert lambdas["L1"] == 0.12
    assert lambdas["L4"] == 0.4
    assert events[0]["layer"] == "L1"


def _proposal_id_from_fresh_process() -> str:
    code = """
from agentfit.core.proposals import _rule_from_evidence
from agentfit.models.loss import Expected, ExpectedAction, Sample
from agentfit.models.solution import CapabilityTool, SolidAtom, Solution
sample = Sample('sample', {'second': False, 'first': True}, Expected([ExpectedAction('safe_fix')]))
solution = Solution(L1_atoms=[SolidAtom('fix', 'write', 'api')], L2_tools=[CapabilityTool('safe_fix', ['fix'])])
print(_rule_from_evidence([sample], solution).id)
"""
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO, env=env,
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def test_proposal_ids_are_stable_across_processes() -> None:
    assert _proposal_id_from_fresh_process() == _proposal_id_from_fresh_process()


def test_boundary_counts_successful_human_episode_as_human_required(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save_samples([
        Sample("automatic", {}, Expected()),
        Sample("human", {}, Expected(), requires_human=True),
    ])
    boundary = analyze_boundary(tmp_path)
    assert boundary["human_required"] == ["human"]
    assert boundary["automated"] == 0
    assert boundary["untested"] == ["automatic"]
    assert boundary["coverage"] == 0.0
    assert boundary["recommended_delivery"] == "保留人工"
    assert boundary["evidence_source"] == "no_episode_evidence"


def test_solution_package_contains_structured_topology(tmp_path: Path) -> None:
    path = export_package(
        make_initial_solution(), tmp_path,
        delivery_conditions=["human confirmation before write"],
    )
    package = json.loads(path.read_text(encoding="utf-8"))
    topology = package["agent_config"]["topology"]
    assert topology["agents"][0] == {
        "id": "solo",
        "role": "single",
        "uses": ["rule_roaming", "rule_airplane"],
    }
    assert topology["edges"] == []
    assert package["delivery_conditions"] == ["human confirmation before write"]


def test_tau2_ingestion_writes_a_real_valid_hash_chain(tmp_path: Path) -> None:
    from bridges.tau2bench.results_to_runstore import convert

    source = tmp_path / "results.json"
    source.write_text(json.dumps({"simulations": [{
        "task_id": "[TASK]airplane_mode_on[PERSONA]traveler",
        "reward_info": {"reward": 1},
        "agent_cost": 0.001,
        "user_cost": 0.002,
    }]}), encoding="utf-8")
    run_dir = tmp_path / "run"
    convert(source, str(run_dir), "fixture")

    epoch = json.loads((run_dir / "epochs" / "epoch_001.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(epoch["hash"]) == 64
    assert epoch["previous_hash"] == "GENESIS"
    assert summary["log_chain_valid"] is True


def test_orchestrator_keeps_distinct_previous_solution_snapshot() -> None:
    solution = make_initial_solution()
    orchestrator = Orchestrator(
        solution, SamplePool(make_samples()), SimulatorExecutor(),
        TrainingConfig(batch_size=21, max_epochs=1, review_policy=AutoApprove()),
    )
    build_team(orchestrator)
    orchestrator.train()
    assert orchestrator._prev_solution is not orchestrator.solution
    assert orchestrator._prev_solution.version < orchestrator.solution.version
