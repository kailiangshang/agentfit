"""Runtime contracts for Skills, roles, Human Gates and message causality."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from agentfit.bus.messages import MessageBus, MsgType, ResultMsg, TaskMsg


REPO = Path(__file__).resolve().parents[1]


def _import(name: str):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"运行合同模块缺失: {exc}")


def test_skill_registry_loads_each_canonical_skill_once() -> None:
    registry_mod = _import("agentfit.skills.registry")
    registry = registry_mod.SkillRegistry(REPO / "src" / "agentfit" / "skills")
    skills = registry.load()
    assert len(skills) == 11
    assert set(skills) == {
        "aggregation", "attribution", "bootstrap", "cascade", "clarify",
        "explain", "intake", "lambda_audit", "proposal", "regression", "validation",
    }
    assert all(len(skill.content_hash) == 64 for skill in skills.values())
    assert all("## 版本" not in skill.content for skill in skills.values())


def test_team_roles_bind_registry_skills_without_copied_content() -> None:
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import AutoApprove, TrainingConfig
    from telecom_world import make_initial_solution, make_samples

    orchestrator = Orchestrator(
        make_initial_solution(), SamplePool(make_samples()), SimulatorExecutor(),
        TrainingConfig(review_policy=AutoApprove()),
    )
    team = build_team(orchestrator)
    assert team["steward"].skills == ("intake", "clarify", "explain")
    assert team["attributor"].skills == ("attribution",)
    assert team["architect"].skills == ("bootstrap", "aggregation", "proposal", "cascade")
    assert team["validator"].skills == ("validation", "regression")


def test_role_handlers_have_focused_modules() -> None:
    for name in ("steward", "attributor", "architect", "validator"):
        module = _import(f"agentfit.agents.{name}")
        assert module.__doc__


def test_production_human_gate_blocks_every_gate_by_default() -> None:
    human = _import("agentfit.gates.human")
    policy = human.BlockingHumanGate()
    for gate in human.GateType:
        decision = policy.review(human.ReviewRequest(gate, "subject", {"evidence": "ref"}))
        assert decision.approved is False
        assert "explicit human approval" in decision.reason


def test_test_human_gate_requires_explicit_injection() -> None:
    human = _import("agentfit.gates.human")
    from agentfit.models.config import AutoApprove, TrainingConfig

    assert isinstance(TrainingConfig().review_policy, human.BlockingHumanGate)
    policy = AutoApprove()
    decision = policy.review(human.ReviewRequest(human.GateType.G1, "change", {}))
    assert decision.approved is True


def test_default_gate_prevents_candidate_mutation() -> None:
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import TrainingConfig
    from telecom_world import make_initial_solution, make_samples

    orchestrator = Orchestrator(
        make_initial_solution(), SamplePool(make_samples()), SimulatorExecutor(),
        TrainingConfig(batch_size=21, max_epochs=1),
    )
    build_team(orchestrator)
    orchestrator.train()
    assert orchestrator.solution.version == 0
    assert orchestrator.outcomes[0].proposals_count > 0
    assert "Human Gate blocked G1" in orchestrator.outcomes[0].notes


def test_multi_layer_lambda_change_requires_g2_review() -> None:
    from agentfit.core.regularization import LambdaController, RegReport

    report = RegReport(
        layer_reg={"L1": 0.5, "L2": 0.5, "L3": 0.0, "L4": 0.0},
        over_threshold={"L1": ["atom_scarcity"], "L2": ["tool_reuse"], "L3": [], "L4": []},
    )
    controller = LambdaController()
    controller.observe(report)
    lambdas, review_requests = controller.observe(report)
    assert lambdas == {"L1": 0.1, "L2": 0.2, "L3": 0.3, "L4": 0.4}
    assert review_requests[0]["gate"] == "G2"
    assert set(review_requests[0]["layers"]) == {"L1", "L2"}


def test_message_context_chain_does_not_mix_epochs() -> None:
    bus = MessageBus()
    bus.register(
        "worker", (MsgType.EXPLAIN,),
        lambda msg: ResultMsg(task_id=msg.task_id, status="ok", output=msg.context_ref),
    )
    bus.dispatch(TaskMsg(to="worker", type=MsgType.EXPLAIN, context_ref="epoch1"))
    bus.dispatch(TaskMsg(to="worker", type=MsgType.EXPLAIN, context_ref="epoch2"))
    chain = bus.context_chain("epoch1")
    assert len(chain) == 2
    assert all(item["context_ref"] == "epoch1" for item in chain)


def test_low_confidence_attribution_and_delivery_reach_human_gate() -> None:
    human = _import("agentfit.gates.human")
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import TrainingConfig
    from telecom_world import make_initial_solution, make_samples

    class RecordingGate:
        def __init__(self):
            self.requests = []

        def review(self, request):
            self.requests.append(request)
            return human.ReviewDecision(False, "recorded", "reviewer")

    gate = RecordingGate()
    orchestrator = Orchestrator(
        make_initial_solution(), SamplePool(make_samples()), SimulatorExecutor(),
        TrainingConfig(batch_size=21, max_epochs=1,
                       attribution_confidence_floor=0.8, review_policy=gate),
    )
    build_team(orchestrator)
    orchestrator.train()
    subjects = [request.subject for request in gate.requests]
    assert "low-confidence attribution" in subjects
    assert "delivery boundary" in subjects


def test_multi_layer_lambda_signal_reaches_g2_human_gate() -> None:
    human = _import("agentfit.gates.human")
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import TrainingConfig
    from telecom_world import make_initial_solution, make_samples

    class RecordingGate:
        def __init__(self):
            self.requests = []

        def review(self, request):
            self.requests.append(request)
            return human.ReviewDecision(False, "recorded", "reviewer")

    gate = RecordingGate()
    orchestrator = Orchestrator(
        make_initial_solution(), SamplePool(make_samples()), SimulatorExecutor(),
        TrainingConfig(batch_size=21, max_epochs=2, convergence_window=3,
                       review_policy=gate),
    )
    build_team(orchestrator)
    orchestrator.train()
    assert any(request.gate == human.GateType.G2 for request in gate.requests)
