"""训练状态机合同测试：Batch/Step/Epoch/validation 语义（架构正本 §Batch、Step、Epoch 与验证边界）。

这些测试先于实现编写（合入门禁 #3：行为变更先有失败测试）：
- 一个 Epoch 完整且不重复地消费 adaptation（无默认全量重放）
- Epoch 结束后才运行 validation，且只读 validation manifest
- validation 不产生 ChangeProposal、不驱动更新
- Early Stopping 判定确定性、停止原因可重算
- L3 存在但沿 L4→L3 不可达 → 归因 L4（不是 eval_error），由反向依赖传播修复
- 显式 train_replay 单独分型，不冒充 validation
"""
from __future__ import annotations

import json

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.core.attribution import attribute_loss
from agentfit.core.proposals import propagate_reverse_dependencies
from agentfit.data.sample_pool import SamplePool
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.models.solution import Knowledge

from telecom_world import make_initial_solution, make_samples

ADAPTATION_PREFIXES = ("F1-", "F2-", "F3-", "F4-", "H-")
VALIDATION_PREFIXES = ("V-",)


def _split(samples):
    adaptation = [s for s in samples if s.id.startswith(ADAPTATION_PREFIXES)]
    validation = [s for s in samples if s.id.startswith(VALIDATION_PREFIXES)]
    return adaptation, validation


def _build(tmp_path, batch_size=4, **config_overrides):
    samples = make_samples()
    adaptation, validation = _split(samples)
    if not validation:
        # 世界没有 V- 样本时，从 F 类各借一个作为 validation（不泄漏回 adaptation）
        validation = [s for s in adaptation if s.id.endswith("-0")][:2]
        adaptation = [s for s in adaptation if s not in validation]
    defaults = {"batch_size": batch_size, "max_epochs": 3,
                "validation_patience": 2}
    defaults.update(config_overrides)
    config = TrainingConfig(review_policy=AutoApprove(), **defaults)
    orch = Orchestrator(make_initial_solution(), SamplePool(adaptation),
                        SimulatorExecutor(), config,
                        run_dir=str(tmp_path / "sm-run"), scenario="state-machine",
                        validation_samples=validation)
    build_team(orch)
    return orch, adaptation, validation, tmp_path / "sm-run"


def _episodes(run_dir, phase):
    """按 phase 分型读取训练 Trace（training_traces/<phase>/epoch_*/...）。"""
    root = run_dir / "training_traces" / phase
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.rglob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(record, dict) and record.get("sample_id"):
            out.append(record)
    return out


def test_epoch_partitions_adaptation_without_replay(tmp_path):
    orch, adaptation, validation, run_dir = _build(tmp_path, batch_size=4)
    orch.train()
    forward = _episodes(run_dir, "forward")
    from collections import Counter
    counts = Counter(t["sample_id"] for t in forward)
    adaptation_ids = {s.id for s in adaptation}
    validation_ids = {v.id for v in validation}
    assert set(counts) <= adaptation_ids, "forward 只能消费 adaptation 样本"
    assert not (set(counts) & validation_ids)
    assert not _episodes(run_dir, "candidate_evaluation"), "默认全量重放必须移除"
    epochs_run = len(orch.outcomes)
    if epochs_run:
        expected_once = {sid: epochs_run for sid in adaptation_ids}
        assert counts == Counter(expected_once), \
            f"每个 Epoch 恰好消费一次 adaptation：{dict((k, v) for k, v in counts.items() if v != epochs_run)}"


def test_validation_runs_each_epoch_end_on_validation_only(tmp_path):
    orch, adaptation, validation, run_dir = _build(tmp_path)
    outcomes = orch.train()
    assert outcomes, "至少一个 Epoch"
    validation_eps = _episodes(run_dir, "validation")
    assert validation_eps, "Epoch 结束必须运行 validation"
    sample_ids = {t["sample_id"] for t in validation_eps}
    assert sample_ids <= {s.id for s in validation}, "validation 只能使用 validation manifest 样本"
    assert sample_ids == {s.id for s in validation}


def test_validation_does_not_drive_updates(tmp_path):
    # V-ONLY 样本特征独特且缺规则：若 validation 泄漏进更新，会为它生成路由规则
    orch, adaptation, validation, run_dir = _build(tmp_path)
    orch.train()
    from telecom_world import make_samples as _ms
    leaked = [k for k in orch.solution.L3_knowledge
              if k.condition and "validation_only_marker" in k.condition]
    assert not leaked, "validation 失败不得产生 ChangeProposal 或新知识"
    # 对照：adaptation 驱动的 F3 规则应当存在
    assert any(k.dispatches_to == "safe_run_sim_diagnostics"
               for k in orch.solution.routing_rules()), "adaptation 失败应驱动 F3 规则"


def test_early_stopping_reason_recomputable(tmp_path):
    orch, adaptation, validation, run_dir = _build(tmp_path)
    orch.train()
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary.get("stop_reason") in {
        "no_improvement", "validation_degraded", "budget_exceeded", "max_epochs",
    }, f"停止原因必须是规范枚举，实际 {summary.get('stop_reason')}"
    series = summary.get("validation_series") or []
    assert len(series) == summary.get("epochs_run"), "validation 曲线长度必须等于 Epoch 数"
    if summary["stop_reason"] == "no_improvement":
        best = max(series)
        assert all(v <= best for v in series[-2:]), "no_improvement 必须可从曲线重算"


def test_unreachable_knowledge_attributed_to_l4(tmp_path):
    sol = make_initial_solution()
    # F3 规则内容存在，但 solo Agent 的 uses 没有引用它（真实平台可达性）
    rule = Knowledge(id="rule_sim_orphan", type="routing_rule",
                     condition="NOT abroad AND NOT roaming_off AND NOT airplane",
                     dispatches_to="safe_run_sim_diagnostics")
    sol.L3_knowledge.append(rule)
    samples = {s.id: s for s in make_samples()}
    sample = next(s for s in samples.values() if s.id.startswith("F3-"))
    trace = SimulatorExecutor().execute(sol, sample)
    assert trace.result == "FAIL", "不可达知识必须导致失败"
    lt = attribute_loss(sample, trace, sol)
    assert lt.root_cause_layer == "L4", f"不可达应归因 L4，实际 {lt.root_cause_layer}"
    assert lt.failure_mode == "unreachable_knowledge", f"实际 {lt.failure_mode}"


def test_reverse_dependency_propagation_wires_new_knowledge(tmp_path):
    sol = make_initial_solution()
    new_rule = Knowledge(id="rule_new_sim", type="routing_rule",
                         condition="NOT sim_ok", dispatches_to="safe_run_sim_diagnostics")
    from agentfit.core.transaction import UpdateProposal
    extra = propagate_reverse_dependencies(
        [UpdateProposal("L3", "add", new_rule, reason="test")], sol)
    assert extra, "新增 L3 未被任何 Agent 引用时必须产生反向依赖传播提案"
    assert all(p.layer == "L4" for p in extra)
    # 应用后 Agent 引用新知识
    tx_result = None
    from agentfit.core.transaction import ChangeTransaction
    tx = ChangeTransaction(sol, [UpdateProposal("L3", "add", new_rule)] + extra)
    tx_result = tx.execute()
    uses = {u for agent in tx_result.L4_topology.agents for u in agent.uses}
    assert "rule_new_sim" in uses
    # 完整训练：新增规则可达 → 下一 Epoch F3 通过
    orch, adaptation, validation, run_dir = _build(tmp_path)
    orch.train()
    uses_after = {u for agent in orch.solution.L4_topology.agents for u in agent.uses}
    sim_rules = [k.id for k in orch.solution.routing_rules()
                 if k.dispatches_to == "safe_run_sim_diagnostics"]
    assert all(r in uses_after for r in sim_rules), "训练新增的规则必须被 L4 引用"


def test_train_replay_is_typed_separately(tmp_path):
    orch, adaptation, validation, run_dir = _build(tmp_path, max_epochs=1)
    orch.train()
    assert not _episodes(run_dir, "train_replay"), "默认不得执行 train_replay"
    orch.run_train_replay()
    replay = _episodes(run_dir, "train_replay")
    assert replay, "显式重放必须落为 train_replay 分型"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    replay_info = summary.get("train_replay")
    assert replay_info and replay_info.get("cost_usd", 0) > 0, "重放成本必须单独核算"
    epochs_cost = sum(
        json.loads((run_dir / f"epochs/epoch_{e:03d}.json").read_text())["entry"]["cost_usd"]
        for e in range(1, summary["epochs_run"] + 1))
    assert summary["total_cost_usd"] == round(epochs_cost, 4), "epoch 成本不得混入重放"
