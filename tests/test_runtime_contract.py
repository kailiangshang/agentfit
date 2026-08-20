"""Runtime contracts for Skills, roles, Human Gates and message causality."""
from __future__ import annotations

import importlib
import json
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


def test_training_defers_delivery_gate_until_final_evidence() -> None:
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
    assert "delivery boundary" not in subjects
    with pytest.raises(ValueError, match="final evaluation evidence"):
        orchestrator.finalize_delivery()
    from agentfit.models.manifest import SampleSetPurpose
    from agentfit.models.objective import (ObjectiveSpec, PurposeAcceptance,
                                           evaluate_acceptance)
    from agentfit.models.sample import canonical_hash
    evaluation = {
        purpose.value: {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "pass_rate": 1.0,
            "cost_usd": 0.0,
            "risk_events": 0,
        }
        for purpose in SampleSetPurpose
    }
    objective = ObjectiveSpec.create(
        criteria=tuple(
            PurposeAcceptance(purpose, 1.0, 0, 1.0, 0)
            for purpose in SampleSetPurpose
        ),
        max_total_evaluation_cost_usd=3.0,
    )
    acceptance = evaluate_acceptance(objective, evaluation)
    orchestrator.finalize_delivery({
        "candidate_ref": canonical_hash(orchestrator.solution),
        "candidate_frozen": True,
        "evaluation_by_purpose": evaluation,
        "objective_ref": objective.content_hash,
        "acceptance_ref": acceptance.content_hash,
        "acceptance_met": acceptance.met,
        "acceptance_failures": list(acceptance.failures),
    })
    subjects = [request.subject for request in gate.requests]
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


def test_runtime_error_is_not_used_as_four_layer_training_signal() -> None:
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.base import ExecutorBase
    from agentfit.models.config import AutoApprove, TrainingConfig
    from agentfit.models.loss import Expected, Trace
    from telecom_world import make_initial_solution, make_samples

    class BrokenSandboxExecutor(ExecutorBase):
        def execute(self, solution, sample):
            return Trace(
                sample_id=sample.id,
                result="ERROR",
                error_scope="runtime",
                error_code="sandbox_unavailable",
                runtime_ref="agentteams:test-sandbox",
            )

        def evaluate(self, trace: Trace, expected: Expected) -> bool:
            return False

    missing_rule_sample = next(sample for sample in make_samples() if sample.id == "F3-0")
    orchestrator = Orchestrator(
        make_initial_solution(),
        SamplePool([missing_rule_sample]),
        BrokenSandboxExecutor(),
        TrainingConfig(batch_size=1, max_epochs=1, review_policy=AutoApprove()),
    )

    outcome = orchestrator.run_epoch(1)

    assert outcome.execution_errors == 1
    assert outcome.proposals_count == 0
    assert orchestrator.solution.version == 0
    assert orchestrator.log.entries[0]["entry"]["execution_errors"] == 1


def test_four_layer_attribution_rejects_execution_errors() -> None:
    from agentfit.core.attribution import attribute_loss
    from agentfit.models.loss import Trace
    from telecom_world import make_initial_solution, make_samples

    sample = next(sample for sample in make_samples() if sample.id == "F3-0")
    trace = Trace(
        sample_id=sample.id,
        result="ERROR",
        error_scope="runtime",
        error_code="dependency_install_failed",
    )

    with pytest.raises(ValueError, match="execution errors cannot be attributed to L1-L4"):
        attribute_loss(sample, trace, make_initial_solution())


def test_training_forward_run_persists_candidate_trace_episode_and_runtime_provenance(
    tmp_path: Path,
) -> None:
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import AutoApprove, TrainingConfig
    from agentfit.models.sample import canonical_hash
    from telecom_world import make_initial_solution, make_samples

    solution = make_initial_solution()
    sample = next(item for item in make_samples() if item.id == "F1-0")
    run_dir = tmp_path / "training-run"
    orchestrator = Orchestrator(
        solution,
        SamplePool([sample]),
        SimulatorExecutor(),
        TrainingConfig(batch_size=1, max_epochs=1, review_policy=AutoApprove()),
        run_dir=str(run_dir),
    )

    orchestrator.train()

    manifests = list((run_dir / "candidate_manifests").glob("*.json"))
    traces = list((run_dir / "training_traces" / "forward" / "epoch_001").glob("*.json"))
    episodes = list((run_dir / "training_episodes" / "forward" / "epoch_001").glob("*.json"))
    assert len(manifests) == len(traces) == len(episodes) == 1

    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    trace = json.loads(traces[0].read_text(encoding="utf-8"))
    episode = json.loads(episodes[0].read_text(encoding="utf-8"))
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))

    assert manifest["specification"]["solution_ref"] == canonical_hash(solution)
    assert episode["identity"]["candidate_ref"] == manifest["content_hash"]
    assert episode["trace_ref"] == traces[0].relative_to(run_dir).as_posix()
    assert episode["runtime_ref"] == trace["runtime_ref"] == run["runtime_ref"]
    assert episode["identity"]["sample_ref"]["content_hash"] == sample.content_hash
    assert episode["identity"]["run_index"] == 0


def test_training_regression_reuses_the_same_recorded_execution_contract(
    tmp_path: Path,
) -> None:
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import AutoApprove, TrainingConfig
    from telecom_world import make_initial_solution, make_samples

    # F1-0 恒通过；F3-0 在首个 Step 失败驱动提交 → 第二个 Step 的提交触发回归重放。
    # 状态机语义（正本 §Batch、Step、Epoch）：每 Epoch 两个 Step（batch_size=1），
    # forward 每 Epoch 恰好执行每个样本一次；regression 只发生在有提交的 Step。
    world = {item.id: item for item in make_samples()}
    run_dir = tmp_path / "training-run"
    orchestrator = Orchestrator(
        make_initial_solution(),
        SamplePool([world["F1-0"], world["F3-0"]]),
        SimulatorExecutor(),
        TrainingConfig(
            batch_size=1,
            max_epochs=2,
            convergence_window=3,
            review_policy=AutoApprove(),
        ),
        run_dir=str(run_dir),
    )

    orchestrator.train()

    forward = list((run_dir / "training_episodes" / "forward").rglob("*.json"))
    regression = list((run_dir / "training_episodes" / "regression").rglob("*.json"))
    identities = [
        json.loads(path.read_text(encoding="utf-8"))["identity"]
        for path in forward + regression
    ]
    # 2 个 Epoch × 2 个 Step × 每批 1 样本 = 4 次 forward
    assert len(forward) == 4
    # epoch1 step2（F3-0 修复提交）时回归池含 F1-0 → 恰好 1 次 regression
    assert len(regression) == 1
    # 回归复用与 forward 相同的记录执行合同：同一 (candidate_ref, sample_ref) 身份
    forward_keys = {
        (identity["candidate_ref"], identity["sample_ref"]["sample_id"])
        for identity in (
            json.loads(path.read_text(encoding="utf-8"))["identity"] for path in forward
        )
    }
    regression_keys = {
        (identity["candidate_ref"], identity["sample_ref"]["sample_id"])
        for identity in (
            json.loads(path.read_text(encoding="utf-8"))["identity"] for path in regression
        )
    }
    assert regression_keys <= forward_keys


def test_regression_runtime_error_blocks_commit_without_claiming_solution_forgetting() -> None:
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import AutoApprove, TrainingConfig
    from agentfit.models.loss import Trace
    from telecom_world import make_initial_solution, make_samples

    samples = {item.id: item for item in make_samples()}

    class RegressionOutageExecutor(SimulatorExecutor):
        def execute(self, solution, sample):
            if sample.id == "F1-0":
                return Trace(
                    sample_id=sample.id,
                    result="ERROR",
                    error_scope="runtime",
                    error_code="agentteams_worker_unavailable",
                )
            return super().execute(solution, sample)

    orchestrator = Orchestrator(
        make_initial_solution(),
        SamplePool([samples["F3-0"]]),
        RegressionOutageExecutor(),
        TrainingConfig(batch_size=1, max_epochs=1, review_policy=AutoApprove()),
    )
    orchestrator.regression_pool.add(samples["F1-0"], passed=True)

    orchestrator.run_epoch(1)

    outcome = orchestrator.outcomes[0]
    assert outcome.rolled_back is True
    assert outcome.execution_errors == 1
    assert any("regression blocked by execution error" in note for note in outcome.notes)
    assert all("回归遗忘" not in note for note in outcome.notes)
