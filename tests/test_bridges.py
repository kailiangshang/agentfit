"""Platform bridges preserve canonical names, contracts and evidence."""
from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys

import pytest

from agentfit.models.sample import canonical_hash
from agentfit.store.run_store import RunStore
from telecom_world import make_initial_solution, make_samples


REPO = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agentteams_manifest_is_generated_from_canonical_registry() -> None:
    script = REPO / "bridges" / "agentteams" / "render_team.py"
    assert script.is_file(), "AgentTeams render bridge is missing"
    renderer = _load(script, "agentfit_render_team")
    expected = renderer.render_resources()
    bridge = _load(REPO / "bridges" / "agentteams" / "apply_team.py", "agentfit_apply_resources")
    checked_in = bridge.load_resources(REPO / "bridges" / "agentteams" / "team.yaml")

    assert checked_in == expected
    assert expected["apiVersion"] == "hiclaw.io/v1beta1"
    assert expected["kind"] == "Team"
    team = expected
    assert team["metadata"]["name"] == "agentfit"
    annotations = team["metadata"]["annotations"]
    assert annotations["agentfit.io/registry-hash"]
    assert annotations["agentfit.io/source"] == "bridges/agentteams/render_team.py"
    assert annotations["agentfit.io/model-ref"] == "deepseek/deepseek-chat"
    assert annotations["agentfit.io/platform-contract"] == "hiclaw-v1.1.2-inline-team"
    assert "workerMembers" not in team["spec"]

    roles = [team["spec"]["leader"], *team["spec"]["workers"]]
    assert [role["name"] for role in roles] == [
        "agentfit-steward", "agentfit-attributor", "agentfit-architect",
    ]
    assert all(role["model"] == annotations["agentfit.io/model-ref"] for role in roles)
    assert "runtime" not in roles[0]
    for role in roles:
        assert role["state"] == "Running"
        assert role["workerName"] == role["name"]
        assert role["identity"]
        assert "## 步骤" in role["soul"]


def test_agentteams_deployment_artifact_rejects_wrong_resource_contract() -> None:
    bridge = _load(REPO / "bridges" / "agentteams" / "apply_team.py", "agentfit_validate_resources")
    resource = bridge.load_resources(REPO / "bridges" / "agentteams" / "team.yaml")
    bridge.validate_resources(resource)

    wrong_api = json.loads(json.dumps(resource))
    wrong_api["apiVersion"] = "hiclaw.io/v1"
    with pytest.raises(SystemExit, match="apiVersion"):
        bridge.validate_resources(wrong_api)

    ambiguous_model = json.loads(json.dumps(resource))
    ambiguous_model["spec"]["workers"][0]["model"] = "deepseek-chat"
    with pytest.raises(SystemExit, match="model-ref"):
        bridge.validate_resources(ambiguous_model)

    bad_leader_runtime = json.loads(json.dumps(resource))
    bad_leader_runtime["spec"]["leader"]["runtime"] = "copaw"
    with pytest.raises(SystemExit, match="runtime"):
        bridge.validate_resources(bad_leader_runtime)

    bad_worker_name = json.loads(json.dumps(resource))
    bad_worker_name["spec"]["workers"][1]["name"] = "agentfit-extra"
    with pytest.raises(SystemExit, match="canonical"):
        bridge.validate_resources(bad_worker_name)

    legacy = json.loads(json.dumps(resource))
    legacy["spec"]["workerMembers"] = []
    with pytest.raises(SystemExit, match="workerMembers"):
        bridge.validate_resources(legacy)

    bad_contract = json.loads(json.dumps(resource))
    bad_contract["metadata"]["annotations"]["agentfit.io/platform-contract"] = "hiclaw-v1.2.0"
    with pytest.raises(SystemExit, match="platform-contract"):
        bridge.validate_resources(bad_contract)


def test_agentteams_dry_run_never_calls_apply(monkeypatch) -> None:
    bridge = _load(REPO / "bridges" / "agentteams" / "apply_team.py", "agentfit_dry_run")
    called = False

    def forbid_apply(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("dry-run must not apply")

    monkeypatch.setattr(bridge, "find_controller", lambda: "test-controller")
    monkeypatch.setattr(bridge, "controller_cli", lambda _controller: "hiclaw")
    monkeypatch.setattr(bridge, "get_teams", lambda _controller, _cli: [])
    monkeypatch.setattr(bridge, "apply_manifest", forbid_apply)
    monkeypatch.setattr(sys, "argv", [
        "apply_team.py", "--manifest", str(REPO / "bridges" / "agentteams" / "team.yaml"), "--dry-run",
    ])

    bridge.main()
    assert called is False


def test_agentteams_drift_is_precise_and_ignores_unrelated_teams() -> None:
    bridge = _load(REPO / "bridges" / "agentteams" / "apply_team.py", "agentfit_apply_team")
    assert hasattr(bridge, "reconcile_status")
    expected = {
        "metadata": {"name": "agentfit", "annotations": {"agentfit.io/registry-hash": "abc"}},
        "spec": {
            "leader": {"name": "agentfit-steward"},
            "workers": [{"name": "agentfit-attributor"}, {"name": "agentfit-architect"}],
        },
    }
    actual = [
        {"metadata": {"name": "agentfit-retail-m1"}},
        {"metadata": {"name": "unrelated-team"}},
    ]
    drift = bridge.reconcile_status(expected, actual)
    assert drift.missing == ("agentfit",)
    assert drift.unexpected == ("agentfit-retail-m1",)
    assert drift.changed == ()
    assert drift.in_sync is False

    actual = [expected, {"metadata": {"name": "unrelated-team"}}]
    assert bridge.reconcile_status(expected, actual).in_sync is True

    changed = json.loads(json.dumps(expected))
    changed["spec"]["leader"]["model"] = "other-model"
    changed["spec"]["workers"][0]["soul"] = "drifted"
    changed["spec"]["workers"][1]["runtime"] = "other-runtime"
    changed["spec"]["peerMentions"] = True
    report = bridge.reconcile_status(expected, [changed])
    assert report.in_sync is False
    assert "agentfit:spec" in report.changed

    full_expected = bridge.load_resources(REPO / "bridges" / "agentteams" / "team.yaml")
    partial = {
        "metadata": full_expected["metadata"],
        "spec": {
            "leader": full_expected["spec"]["leader"],
            "workers": full_expected["spec"]["workers"],
        },
    }
    report = bridge.reconcile_status(full_expected, [partial])
    assert report.changed == ()
    assert report.unverified == ("agentfit:content",)

    flattened = {
        "metadata": {"name": "agentfit"},
        "leaderName": full_expected["spec"]["leader"]["name"],
        "workerNames": [worker["name"] for worker in full_expected["spec"]["workers"]],
    }
    report = bridge.reconcile_status(full_expected, {"teams": [flattened]})
    assert report.changed == ()
    assert report.unverified == ("agentfit:content", "agentfit:registry-hash")


def test_agentteams_solution_export_requires_g3(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "export_solution.py",
        "agentfit_export_solution",
    )
    store = RunStore(tmp_path)
    store.save_solution_version(make_initial_solution())
    store.save_summary({"delivery_approved": False})
    with pytest.raises(SystemExit, match="G3"):
        bridge.export(str(tmp_path))


def test_agentteams_exports_only_the_g3_approved_candidate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTFIT_G3_SIGNING_KEY", "agentfit-test-key-not-for-production-0001")
    monkeypatch.setenv("AGENTFIT_G3_KEY_ID", "pytest")
    run_dir = tmp_path / "run"
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO / "src"),
        "AGENTFIT_G3_SIGNING_KEY": "agentfit-test-key-not-for-production-0001",
        "AGENTFIT_G3_KEY_ID": "pytest",
    }
    bundle = json.loads(
        (REPO / "examples" / "telecom-materials.json").read_text(encoding="utf-8")
    )
    bundle["objective"] = {
        "criteria": [
            {
                "purpose": purpose,
                "min_pass_rate": 0.0,
                "max_errors": 0,
                "max_cost_usd": 1.0,
                "max_risk_events": 0,
            }
            for purpose in (
                "adaptation", "validation", "sealed_holdout", "stress_and_failure",
            )
        ],
        "max_total_evaluation_cost_usd": 3.0,
    }
    mechanical_bundle = tmp_path / "mechanical-materials.json"
    mechanical_bundle.write_text(json.dumps(bundle), encoding="utf-8")
    case = tmp_path / "telecom-case.json"
    compiled = subprocess.run(
        [
            sys.executable, "-m", "agentfit", "compile",
            "--bundle", str(mechanical_bundle),
            "--output", str(case),
        ],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert compiled.returncode == 0, compiled.stderr
    trained = subprocess.run(
        [
            sys.executable, "-m", "agentfit", "train",
            "--case", str(case),
            "--output", str(run_dir), "--auto-approve",
        ],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert trained.returncode == 0, trained.stderr
    bridge = _load(
        REPO / "bridges" / "agentteams" / "export_solution.py",
        "agentfit_export_approved_solution",
    )
    config = bridge.export(str(run_dir))
    decision = json.loads((run_dir / "delivery_decision.json").read_text(encoding="utf-8"))
    assert config["source"]["solution_version"] == decision["final_solution_version"]
    assert config["delivery_conditions"] == decision["review_conditions"]
    assert all("solid_atoms" in tool for tool in config["tools"])
    assert all("backend_atoms" not in tool for tool in config["tools"])
    with pytest.raises(SystemExit, match="G3-approved"):
        bridge.export(str(run_dir), decision["final_solution_version"] + 1)


def test_agentteams_sandbox_executor_round_trips_semantic_task_and_trace() -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_executor",
    )
    from agentfit.adapters.protocols import SandboxResult

    class RecordingSandbox:
        def __init__(self):
            self.request = None

        def execute(self, request):
            self.request = request
            task = request.arguments
            return SandboxResult(
                status="ok",
                output={
                    "schema": "agentfit.agentteams-result",
                    "task_id": task["task_id"],
                    "candidate_ref": task["candidate_ref"],
                    "sample_ref": task["sample_ref"],
                    "run_index": task["run_index"],
                    "runtime_ref": task["runtime_ref"],
                    "status": "completed",
                    "steps": [{
                        "layer": "L2",
                        "element_id": "safe_toggle_roaming",
                        "action": "execute",
                        "ok": True,
                        "output": "safe_toggle_roaming",
                        "expected_output": "safe_toggle_roaming",
                    }],
                    "routed_knowledge_id": "rule_roaming",
                    "cost_usd": 0.02,
                    "risk_events": [],
                },
                cost_usd=0.02,
            )

    sandbox = RecordingSandbox()
    executor = bridge.AgentTeamsSandboxExecutor(
        sandbox,
        deployment_ref="agentteams://team/agentfit-candidate",
        sandbox_ref="agentteams://worker/sandbox-1",
        model_ref="deepseek-chat",
    )
    sample = next(item for item in make_samples() if item.id == "F1-0")

    trace = executor.execute(make_initial_solution(), sample)

    assert sandbox.request.tool == "agentteams.execute_candidate"
    task = sandbox.request.arguments
    assert task["schema"] == "agentfit.agentteams-task"
    assert task["sample_ref"]["content_hash"] == sample.content_hash
    assert task["input_data"] == sample.input_data
    assert "expected" not in task
    assert trace.result == "PASS"
    assert trace.runtime_ref == canonical_hash(executor.runtime_provenance())
    assert trace.cost_usd == 0.02
    assert [step.element_id for step in trace.steps] == ["safe_toggle_roaming"]


def test_agentteams_sandbox_failure_returns_runtime_error_not_layer_failure() -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_error_executor",
    )
    from agentfit.adapters.protocols import SandboxResult

    class UnavailableSandbox:
        def execute(self, request):
            return SandboxResult(
                status="error",
                error="worker unavailable",
                cost_usd=0.001,
            )

    executor = bridge.AgentTeamsSandboxExecutor(
        UnavailableSandbox(),
        deployment_ref="agentteams://team/agentfit-candidate",
        sandbox_ref="agentteams://worker/sandbox-1",
    )
    sample = next(item for item in make_samples() if item.id == "F1-0")

    trace = executor.execute(make_initial_solution(), sample)

    assert trace.result == "ERROR"
    assert trace.error_scope == "runtime"
    assert trace.error_code == "agentteams_sandbox_error"
    assert trace.steps == []


def test_agentteams_result_contract_rejects_non_boolean_step_status() -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_strict_step_contract",
    )
    sample = next(item for item in make_samples() if item.id == "F1-0")
    runtime_ref = canonical_hash({"runtime": "test"})

    trace = bridge.trace_from_result({
        "schema": "agentfit.agentteams-result",
        "runtime_ref": runtime_ref,
        "status": "completed",
        "steps": [{
            "layer": "L2",
            "element_id": "safe_toggle_roaming",
            "action": "execute",
            "ok": "false",
        }],
        "cost_usd": 0.01,
        "risk_events": [],
    }, sample, runtime_ref=runtime_ref)

    assert trace.result == "ERROR"
    assert trace.error_scope == "runtime"
    assert trace.error_code == "agentteams_result_contract_error"


@pytest.mark.parametrize("cost", ["bad", float("nan"), -1.0])
def test_agentteams_result_contract_rejects_invalid_cost(cost) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_strict_cost_contract",
    )
    sample = next(item for item in make_samples() if item.id == "F1-0")
    runtime_ref = canonical_hash({"runtime": "test"})

    trace = bridge.trace_from_result({
        "schema": "agentfit.agentteams-result",
        "runtime_ref": runtime_ref,
        "status": "error",
        "cost_usd": cost,
    }, sample, runtime_ref=runtime_ref)

    assert trace.result == "ERROR"
    assert trace.error_scope == "runtime"
    assert trace.error_code == "agentteams_result_contract_error"


def test_agentteams_sandbox_exception_returns_runtime_error() -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_sandbox_exception",
    )

    class TimedOutSandbox:
        def execute(self, request):
            raise TimeoutError("worker timed out")

    executor = bridge.AgentTeamsSandboxExecutor(
        TimedOutSandbox(),
        deployment_ref="agentteams://team/agentfit-candidate",
        sandbox_ref="agentteams://worker/sandbox-1",
    )
    sample = next(item for item in make_samples() if item.id == "F1-0")

    trace = executor.execute(make_initial_solution(), sample)

    assert trace.result == "ERROR"
    assert trace.error_scope == "runtime"
    assert trace.error_code == "agentteams_sandbox_error"


def test_agentteams_sandbox_rejects_result_identity_drift() -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_identity_drift_executor",
    )
    from agentfit.adapters.protocols import SandboxResult

    class DriftedSandbox:
        def execute(self, request):
            task = request.arguments
            return SandboxResult(status="ok", output={
                "schema": "agentfit.agentteams-result",
                "task_id": task["task_id"],
                "candidate_ref": canonical_hash({"candidate": "drifted"}),
                "sample_ref": task["sample_ref"],
                "run_index": task["run_index"],
                "runtime_ref": task["runtime_ref"],
                "status": "completed",
                "steps": [{"layer": "L2", "element_id": "safe_toggle_roaming", "ok": True}],
            })

    executor = bridge.AgentTeamsSandboxExecutor(
        DriftedSandbox(),
        deployment_ref="agentteams://team/agentfit-candidate",
        sandbox_ref="agentteams://worker/sandbox-1",
    )
    sample = next(item for item in make_samples() if item.id == "F1-0")

    trace = executor.execute(make_initial_solution(), sample)

    assert trace.result == "ERROR"
    assert trace.error_scope == "runtime"
    assert trace.error_code == "agentteams_result_contract_error"


def test_agentteams_offline_results_import_full_trace_episode_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "import_results.py",
        "agentfit_agentteams_result_import",
    )
    from agentfit.models.evidence import CandidateManifest

    solution = make_initial_solution()
    candidate = CandidateManifest.for_solution(solution)
    sample = next(item for item in make_samples() if item.id == "F1-0")
    runtime_provenance = {
        "platform": "agentteams",
        "execution_boundary": "worker_sandbox",
        "deployment_ref": "agentteams://team/agentfit-candidate",
        "sandbox_ref": "agentteams://worker/sandbox-1",
    }
    runtime_ref = canonical_hash(runtime_provenance)
    run_dir = tmp_path / "run"
    store = RunStore(run_dir)
    store.init_run({
        "run_kind": "training",
        "runtime_provenance": runtime_provenance,
        "runtime_ref": runtime_ref,
    })
    store.save_task_samples([sample])
    store.save_training_candidate_manifest(candidate)
    results = [{
        "schema": "agentfit.agentteams-result",
        "task_id": "task-1",
        "candidate_ref": candidate.candidate_ref,
        "sample_ref": asdict(sample.ref),
        "run_index": 0,
        "status": "completed",
        "steps": [{
            "layer": "L2",
            "element_id": "safe_toggle_roaming",
            "action": "execute",
            "ok": True,
        }],
        "routed_knowledge_id": "rule_roaming",
        "cost_usd": 0.03,
        "risk_events": [],
        "runtime_ref": runtime_ref,
    }]

    save_episode = RunStore.save_training_episode

    def fail_episode_write(*args, **kwargs):
        raise OSError("simulated episode write failure")

    monkeypatch.setattr(RunStore, "save_training_episode", fail_episode_write)
    with pytest.raises(OSError, match="simulated"):
        bridge.import_results_to_runstore(
            results, run_dir, epoch=1, phase="agentteams",
        )
    assert not (run_dir / "training_traces").exists()
    assert not (run_dir / "training_episodes").exists()

    monkeypatch.setattr(RunStore, "save_training_episode", save_episode)
    imported = bridge.import_results_to_runstore(
        results, run_dir, epoch=1, phase="agentteams",
    )

    assert imported == 1
    trace_path = next((run_dir / "training_traces" / "agentteams" / "epoch_001").glob("*.json"))
    episode_path = next((run_dir / "training_episodes" / "agentteams" / "epoch_001").glob("*.json"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    assert trace["result"] == episode["result"] == "PASS"
    assert episode["trace_ref"] == trace_path.relative_to(run_dir).as_posix()
    assert episode["identity"] == {
        "candidate_ref": candidate.candidate_ref,
        "sample_ref": asdict(sample.ref),
        "run_index": 0,
    }
    assert episode["runtime_ref"] == runtime_ref

    with pytest.raises(ValueError, match="already exists"):
        bridge.import_results_to_runstore(
            results, run_dir, epoch=2, phase="replayed",
        )
    assert not (run_dir / "training_episodes" / "replayed").exists()


@pytest.mark.parametrize("phase", ("../escape", "/tmp/escape", "nested/escape", "."))
def test_agentteams_result_import_rejects_unsafe_phase_paths(
    tmp_path: Path, phase: str,
) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "import_results.py",
        f"agentfit_agentteams_unsafe_phase_{canonical_hash(phase)[:8]}",
    )

    with pytest.raises(ValueError, match="phase"):
        bridge.import_results_to_runstore(
            [{}], tmp_path / "run", epoch=1, phase=phase,
        )


def test_agentteams_result_import_cli_uses_the_canonical_runstore_contract(
    tmp_path: Path,
) -> None:
    from agentfit.models.evidence import CandidateManifest

    candidate = CandidateManifest.for_solution(make_initial_solution())
    sample = next(item for item in make_samples() if item.id == "F1-0")
    runtime_provenance = {
        "platform": "agentteams",
        "execution_boundary": "worker_sandbox",
        "deployment_ref": "agentteams://team/agentfit-candidate",
        "sandbox_ref": "agentteams://worker/sandbox-1",
    }
    runtime_ref = canonical_hash(runtime_provenance)
    run_dir = tmp_path / "run"
    store = RunStore(run_dir)
    store.init_run({
        "run_kind": "training",
        "runtime_provenance": runtime_provenance,
        "runtime_ref": runtime_ref,
    })
    store.save_task_samples([sample])
    store.save_training_candidate_manifest(candidate)
    result_path = tmp_path / "agentteams-results.json"
    result_path.write_text(json.dumps([{
        "schema": "agentfit.agentteams-result",
        "task_id": "task-1",
        "candidate_ref": candidate.candidate_ref,
        "sample_ref": asdict(sample.ref),
        "run_index": 0,
        "status": "completed",
        "steps": [{"layer": "L2", "element_id": "safe_toggle_roaming", "ok": True}],
        "runtime_ref": runtime_ref,
    }]), encoding="utf-8")

    imported = subprocess.run(
        [
            sys.executable,
            str(REPO / "bridges" / "agentteams" / "import_results.py"),
            str(result_path),
            "--run-dir", str(run_dir),
            "--epoch", "1",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert imported.returncode == 0, imported.stderr
    assert "imported 1 AgentTeams result" in imported.stdout
    assert len(list((run_dir / "training_episodes" / "agentteams" / "epoch_001").glob("*.json"))) == 1
    assert not (tmp_path / "traces.json").exists()


def test_agentteams_offline_result_import_rejects_candidate_drift(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "import_results.py",
        "agentfit_agentteams_result_drift",
    )
    from agentfit.models.evidence import CandidateManifest

    candidate = CandidateManifest.for_solution(make_initial_solution())
    sample = next(item for item in make_samples() if item.id == "F1-0")
    run_dir = tmp_path / "run"
    store = RunStore(run_dir)
    runtime_provenance = {"runtime": "test"}
    store.init_run({
        "run_kind": "training",
        "runtime_provenance": runtime_provenance,
        "runtime_ref": canonical_hash(runtime_provenance),
    })
    store.save_task_samples([sample])
    store.save_training_candidate_manifest(candidate)

    with pytest.raises(ValueError, match="candidate"):
        bridge.import_results_to_runstore([{
            "schema": "agentfit.agentteams-result",
            "task_id": "task-1",
            "candidate_ref": canonical_hash({"candidate": "drifted"}),
            "sample_ref": asdict(sample.ref),
            "run_index": 0,
            "status": "completed",
            "steps": [],
        }], run_dir, epoch=1, phase="agentteams")

    assert not (run_dir / "training_episodes").exists()


def test_agentteams_offline_result_import_rejects_tampered_runtime_provenance(
    tmp_path: Path,
) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "import_results.py",
        "agentfit_agentteams_result_runtime_drift",
    )
    from agentfit.models.evidence import CandidateManifest

    candidate = CandidateManifest.for_solution(make_initial_solution())
    sample = next(item for item in make_samples() if item.id == "F1-0")
    run_dir = tmp_path / "run"
    store = RunStore(run_dir)
    tampered_runtime_ref = canonical_hash({"runtime": "tampered"})
    store.init_run({
        "run_kind": "training",
        "runtime_provenance": {"runtime": "original"},
        "runtime_ref": tampered_runtime_ref,
    })
    store.save_task_samples([sample])
    store.save_training_candidate_manifest(candidate)

    with pytest.raises(ValueError, match="runtime"):
        bridge.import_results_to_runstore([{
            "schema": "agentfit.agentteams-result",
            "task_id": "task-1",
            "candidate_ref": candidate.candidate_ref,
            "sample_ref": asdict(sample.ref),
            "run_index": 0,
            "runtime_ref": tampered_runtime_ref,
            "status": "completed",
            "steps": [],
        }], run_dir, epoch=1, phase="agentteams")

    assert not (run_dir / "training_episodes").exists()


def test_agentteams_executor_orchestrator_runstore_round_trip(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "executor.py",
        "agentfit_agentteams_orchestrated_executor",
    )
    from agentfit.adapters.protocols import SandboxResult
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    from agentfit.models.config import AutoApprove, TrainingConfig

    class RecordingSandbox:
        def execute(self, request):
            task = request.arguments
            return SandboxResult(status="ok", output={
                "schema": "agentfit.agentteams-result",
                "task_id": task["task_id"],
                "candidate_ref": task["candidate_ref"],
                "sample_ref": task["sample_ref"],
                "run_index": task["run_index"],
                "runtime_ref": task["runtime_ref"],
                "status": "completed",
                "steps": [{
                    "layer": "L2",
                    "element_id": "safe_toggle_roaming",
                    "action": "execute",
                    "ok": True,
                }],
                "cost_usd": 0.02,
                "risk_events": [],
            })

    sample = next(item for item in make_samples() if item.id == "F1-0")
    executor = bridge.AgentTeamsSandboxExecutor(
        RecordingSandbox(),
        deployment_ref="agentteams://team/agentfit-candidate",
        sandbox_ref="agentteams://worker/sandbox-1",
    )
    run_dir = tmp_path / "agentteams-training"
    orchestrator = Orchestrator(
        make_initial_solution(),
        SamplePool([sample]),
        executor,
        TrainingConfig(batch_size=1, max_epochs=1, review_policy=AutoApprove()),
        run_dir=str(run_dir),
        scenario="agentteams-round-trip",
    )
    build_team(orchestrator)

    outcomes = orchestrator.train()

    assert outcomes[0].pass_rate == 1.0
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run["runtime_provenance"]["platform"] == "agentteams"
    traces = list((run_dir / "training_traces" / "forward" / "epoch_001").glob("*.json"))
    episodes = list((run_dir / "training_episodes" / "forward" / "epoch_001").glob("*.json"))
    manifests = list((run_dir / "candidate_manifests").glob("*.json"))
    assert len(traces) == len(episodes) == len(manifests) == 1
    trace = json.loads(traces[0].read_text(encoding="utf-8"))
    episode = json.loads(episodes[0].read_text(encoding="utf-8"))
    assert trace["runtime_ref"] == episode["runtime_ref"] == run["runtime_ref"]


def test_agentteams_import_recovers_an_interrupted_publish(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "import_results.py",
        "agentfit_agentteams_import_recovery",
    )
    target = tmp_path / "training_traces" / "agentteams" / "epoch_001" / "partial.json"
    target.parent.mkdir(parents=True)
    target.write_text("partial", encoding="utf-8")
    staging = tmp_path / ".agentteams-import.interrupted"
    staging.mkdir()
    (tmp_path / ".agentteams-import-journal.json").write_text(json.dumps({
        "state": "publishing",
        "targets": [target.relative_to(tmp_path).as_posix()],
        "staging": staging.name,
    }), encoding="utf-8")

    bridge._recover_interrupted_import(tmp_path)

    assert not target.exists()
    assert not staging.exists()
    assert not (tmp_path / ".agentteams-import-journal.json").exists()


def test_agentteams_import_preserves_a_committed_publish_during_recovery(
    tmp_path: Path,
) -> None:
    bridge = _load(
        REPO / "bridges" / "agentteams" / "import_results.py",
        "agentfit_agentteams_committed_recovery",
    )
    target = tmp_path / "training_traces" / "agentteams" / "epoch_001" / "complete.json"
    target.parent.mkdir(parents=True)
    target.write_text("complete", encoding="utf-8")
    staging = tmp_path / ".agentteams-import.committed"
    staging.mkdir()
    (tmp_path / ".agentteams-import-journal.json").write_text(json.dumps({
        "state": "committed",
        "targets": [target.relative_to(tmp_path).as_posix()],
        "staging": staging.name,
    }), encoding="utf-8")

    bridge._recover_interrupted_import(tmp_path)

    assert target.read_text(encoding="utf-8") == "complete"
    assert not staging.exists()
    assert not (tmp_path / ".agentteams-import-journal.json").exists()


def _tau2_fixture() -> dict:
    simulation = {
            "task_id": "[TASK]airplane_mode_on|user_abroad_roaming_enabled_off[PERSONA]traveler",
            "reward_info": {"reward": 0},
            "agent_cost": {"total_cost_usd": 0.02},
            "user_cost": 0.01,
            "messages": [{
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "get_customer"}},
                    {"name": "toggle_airplane_mode"},
                ],
            }],
        }
    return {"simulations": [simulation]}


def _tau2_candidate_declaration(system: str = "fixture-system") -> dict:
    return {
        "candidate_id": system,
        "kind": "external_system",
        "specification": {
            "system_ref": canonical_hash({"external_system": system}),
        },
        "provenance_complete": False,
    }


def test_tau2_bridge_rejects_display_label_as_candidate_identity(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_explicit_candidate_identity",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")

    with pytest.raises(TypeError, match="candidate declaration"):
        bridge.convert(source, str(tmp_path / "run"), "display-only")


def test_tau2_bridge_cli_can_revalidate_source_projection(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_revalidation_cli_fixture",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "bridges" / "tau2bench" / "results_to_runstore.py"),
            "--validate-run-dir", str(run_dir),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "source projection valid" in result.stdout


def test_tau2_bridge_converts_task_trace_episode_and_runstore(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_results",
    )
    for name in ("simulation_to_task_sample", "simulation_to_episode"):
        assert hasattr(bridge, name)
    simulation = _tau2_fixture()["simulations"][0]
    simulation["risk_events"] = ["unsafe_tool_call"]
    task = bridge.simulation_to_task_sample(simulation)
    candidate_ref = canonical_hash({"candidate": "baseline"})
    episode, trace = bridge.simulation_to_episode(
        simulation, task, candidate_ref=candidate_ref, run_index=0,
    )
    assert task.complexity == "compound"
    assert episode.result == "FAIL"
    assert episode.cost_usd == 0.03
    assert episode.risk_events == 1
    assert trace.risk_events == ["unsafe_tool_call"]
    assert [step.element_id for step in trace.steps] == ["get_customer", "toggle_airplane_mode"]

    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())
    store = RunStore(run_dir)
    assert (run_dir / "task_samples.json").is_file()
    assert (run_dir / "source_results.json").is_file()
    assert (run_dir / "candidate_manifest.json").is_file()
    assert len(list((run_dir / "external_evidence").glob("*.json"))) == 1
    assert len(list((run_dir / "episodes").glob("*.json"))) == 1
    assert len(list((run_dir / "traces").glob("*.json"))) == 1
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run["run_kind"] == "external_evaluation"
    assert run["runtime_ref"] == canonical_hash(run["runtime_provenance"])
    candidate = json.loads((run_dir / "candidate_manifest.json").read_text(encoding="utf-8"))
    assert run["candidate_ref"] == candidate["content_hash"]
    assert candidate["provenance_complete"] is False
    assert "source_configuration_hash" not in candidate["specification"]
    episode_doc = json.loads(next((run_dir / "episodes").glob("*.json")).read_text(encoding="utf-8"))
    trace_doc = json.loads((run_dir / episode_doc["trace_ref"]).read_text(encoding="utf-8"))
    assert episode_doc["evidence_hash"] == canonical_hash(trace_doc)
    assert episode_doc["runtime_ref"] == trace_doc["runtime_ref"] == run["runtime_ref"]

    from agentfit.cli import assert_valid_runstore
    assert_valid_runstore(run_dir)


def test_tau2_validation_recomputes_normalized_evidence_from_source(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_source_projection_validation",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    episode_path = next((run_dir / "episodes").glob("*.json"))
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    trace_path = run_dir / episode["trace_ref"]
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["result"] = "PASS"
    trace["steps"] = []
    trace["cost_usd"] = 9.99
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    episode["result"] = "PASS"
    episode["cost_usd"] = 9.99
    episode["evidence_hash"] = canonical_hash(trace)
    episode_path.write_text(json.dumps(episode), encoding="utf-8")

    from agentfit.models.evidence import ExternalEvidenceRecord
    from agentfit.models.sample import SampleRef

    record_path = run_dir / "external_evidence" / "record_000000.json"
    record_data = json.loads(record_path.read_text(encoding="utf-8"))
    record = ExternalEvidenceRecord.create(
        source_index=0,
        source_record_hash=record_data["source_record_hash"],
        candidate_ref=record_data["candidate_ref"],
        sample_ref=SampleRef(**record_data["sample_ref"]),
        run_index=record_data["run_index"],
        trace_ref=record_data["trace_ref"],
        result="PASS",
        cost_usd=9.99,
        trace_hash=canonical_hash(trace),
        previous_hash="GENESIS",
    )
    record_path.write_text(json.dumps(asdict(record)), encoding="utf-8")

    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update({
        "evaluation": {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "pass_rate": 1.0,
            "cost_usd": 9.99,
            "risk_events": 0,
        },
        "total_cost_usd": 9.99,
        "evidence_chain_root": record.content_hash,
    })
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    from agentfit.cli import CliError

    with pytest.raises(CliError, match="source projection"):
        bridge.validate(run_dir)


def test_tau2_bridge_treats_null_risk_events_as_empty() -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_null_risk_events",
    )
    simulation = _tau2_fixture()["simulations"][0]
    simulation["risk_events"] = None
    task = bridge.simulation_to_task_sample(simulation)

    episode, trace = bridge.simulation_to_episode(
        simulation,
        task,
        candidate_ref=canonical_hash({"candidate": "baseline"}),
        run_index=0,
    )

    assert trace.risk_events == []
    assert episode.risk_events == 0


def test_tau2_repeated_trials_keep_distinct_run_indices(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_repeated_results",
    )
    fixture = _tau2_fixture()
    fixture["simulations"].append(dict(fixture["simulations"][0]))
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())
    episodes = [json.loads(path.read_text(encoding="utf-8"))
                for path in (run_dir / "episodes").glob("*.json")]
    assert len(episodes) == 2
    assert {episode["identity"]["run_index"] for episode in episodes} == {0, 1}
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run["config"] == {"num_tasks": 1, "num_trials": 2}


def test_tau2_external_evaluation_is_valid_but_not_exportable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_external_evaluation",
    )
    fixture = _tau2_fixture()
    passing = json.loads(json.dumps(fixture["simulations"][0]))
    passing["reward_info"]["reward"] = 1
    passing["agent_cost"] = 0.01
    passing["user_cost"] = 0.0
    fixture["simulations"].append(passing)
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture), encoding="utf-8")
    run_dir = tmp_path / "run"

    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    from agentfit.cli import assert_valid_runstore, main

    assert_valid_runstore(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_kind"] == "external_evaluation"
    assert summary["evaluation"] == {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "errors": 0,
        "pass_rate": 0.5,
        "cost_usd": 0.04,
        "risk_events": 0,
    }
    assert main(["export", str(run_dir)]) == 2
    assert "external evaluation" in capsys.readouterr().err


@pytest.mark.parametrize("artifact", [
    "sample_sets.json", "objective.json", "acceptance.json",
])
def test_tau2_external_evaluation_rejects_training_and_delivery_artifacts(
    tmp_path: Path, artifact: str,
) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_artifact_isolation",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())
    (run_dir / artifact).write_text("{}", encoding="utf-8")

    from agentfit.cli import CliError, assert_valid_runstore

    with pytest.raises(CliError, match="forbidden external evaluation artifact"):
        assert_valid_runstore(run_dir)


def test_tau2_bridge_refuses_to_overwrite_existing_runstore(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_no_overwrite",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "preserve.txt").write_text("immutable", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    assert (run_dir / "preserve.txt").read_text(encoding="utf-8") == "immutable"


def test_tau2_failed_conversion_is_atomic_and_retryable(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_atomic_conversion",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps({"simulations": []}), encoding="utf-8")
    run_dir = tmp_path / "run"

    with pytest.raises(ValueError, match="no simulations"):
        bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    assert not run_dir.exists()
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())
    assert (run_dir / "summary.json").is_file()


def test_tau2_report_is_evaluation_specific(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_evaluation_report",
    )
    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    from agentfit.cli import main

    assert main(["report", str(run_dir)]) == 0
    report = (run_dir / "evaluation_report.md").read_text(encoding="utf-8")
    dashboard = (run_dir / "dashboard.html").read_text(encoding="utf-8")
    assert "外部评价报告" in report
    assert "训练轮数" not in report
    assert "外部评价证据" in dashboard
    assert "训练曲线" not in dashboard
    assert not (run_dir / "training_report.md").exists()


def test_tau2_external_evaluation_counts_runtime_errors_separately(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_error_metrics",
    )
    fixture = _tau2_fixture()
    fixture["simulations"][0]["error"] = "provider timeout"
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture), encoding="utf-8")
    run_dir = tmp_path / "run"

    bridge.convert(source, str(run_dir), _tau2_candidate_declaration())

    from agentfit.cli import assert_valid_runstore

    assert_valid_runstore(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["evaluation"] == {
        "total": 1,
        "passed": 0,
        "failed": 0,
        "errors": 1,
        "pass_rate": 0.0,
        "cost_usd": 0.03,
        "risk_events": 0,
    }
    episode = json.loads(next((run_dir / "episodes").glob("*.json")).read_text(encoding="utf-8"))
    trace = json.loads((run_dir / episode["trace_ref"]).read_text(encoding="utf-8"))
    assert episode["result"] == trace["result"] == "ERROR"
    assert trace["error_scope"] == "runtime"
    assert trace["error_code"] == "tau2_runtime_error"
    assert all(step["element_id"] != "tau2_runtime" for step in trace["steps"])
