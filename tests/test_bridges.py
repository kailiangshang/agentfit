"""Platform bridges preserve canonical names, contracts and evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from agentfit.models.sample import canonical_hash
from agentfit.store.run_store import RunStore
from telecom_world import make_initial_solution


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
    expected = renderer.render_manifest()
    checked_in = json.loads((REPO / "bridges" / "agentteams" / "team.yaml").read_text(encoding="utf-8"))

    assert checked_in == expected
    assert expected["metadata"]["name"] == "agentfit"
    assert expected["spec"]["leader"]["name"] == "agentfit-steward"
    assert {worker["name"] for worker in expected["spec"]["workers"]} == {
        "agentfit-attributor", "agentfit-architect",
    }
    for role in (expected["spec"]["leader"], *expected["spec"]["workers"]):
        assert "## 步骤" in role["soul"]
    assert expected["metadata"]["annotations"]["agentfit.io/registry-hash"]


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


def test_tau2_bridge_converts_task_trace_episode_and_runstore(tmp_path: Path) -> None:
    bridge = _load(
        REPO / "bridges" / "tau2bench" / "results_to_runstore.py",
        "agentfit_tau2_results",
    )
    for name in ("simulation_to_task_sample", "simulation_to_episode"):
        assert hasattr(bridge, name)
    simulation = _tau2_fixture()["simulations"][0]
    task = bridge.simulation_to_task_sample(simulation)
    candidate_ref = canonical_hash({"candidate": "baseline"})
    episode, trace = bridge.simulation_to_episode(
        simulation, task, candidate_ref=candidate_ref, run_index=0,
    )
    assert task.complexity == "compound"
    assert episode.result == "FAIL"
    assert episode.cost_usd == 0.03
    assert [step.element_id for step in trace.steps] == ["get_customer", "toggle_airplane_mode"]

    source = tmp_path / "results.json"
    source.write_text(json.dumps(_tau2_fixture()), encoding="utf-8")
    run_dir = tmp_path / "run"
    bridge.convert(source, str(run_dir), "fixture")
    store = RunStore(run_dir)
    assert (run_dir / "task_samples.json").is_file()
    assert (run_dir / "source_results.json").is_file()
    assert len(list((run_dir / "episodes").glob("*.json"))) == 1
    assert len(list((run_dir / "traces").glob("*.json"))) == 1
    assert store.verify_hash_chain() is True


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
    bridge.convert(source, str(run_dir), "fixture")
    episodes = [json.loads(path.read_text(encoding="utf-8"))
                for path in (run_dir / "episodes").glob("*.json")]
    assert len(episodes) == 2
    assert {episode["identity"]["run_index"] for episode in episodes} == {0, 1}
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run["config"] == {"num_tasks": 1, "num_trials": 2}
