"""端到端：Telecom 模拟场景，训练循环提升通过率。

验收（对应提交材料的"方案是训练出来的"主张）：
- 初始最简方案通过率 ~50%（只覆盖 F1/F2）
- 训练归纳出 F3 路由规则（L3 更新）+ 复合样本触发双 Agent 拓扑（L4 更新）
- 训练后通过率 ≥ 90%，回归池零遗忘，日志哈希链可验证，方案各版本无悬空引用
"""
from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.data.sample_pool import SamplePool
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.solution.validator import validate_existence_dependencies

from telecom_world import make_initial_solution, make_samples


def _run(max_epochs: int = 5):
    samples = make_samples()
    pool = SamplePool(samples)
    executor = SimulatorExecutor()
    initial = make_initial_solution()
    # baseline：初始方案裸跑（不训练）
    results = [executor.evaluate(executor.execute(initial, s), s.expected) for s in samples]
    baseline_rate = sum(results) / len(results)

    orch = Orchestrator(initial, pool, executor,
                        TrainingConfig(batch_size=21, max_epochs=max_epochs,
                                       review_policy=AutoApprove()))
    build_team(orch)
    outcomes = orch.train()
    return orch, baseline_rate, outcomes


def test_training_improves_pass_rate():
    orch, baseline_rate, outcomes = _run()
    assert baseline_rate < 0.6, f"初始方案应只覆盖 F1/F2（约 52%），实际 {baseline_rate}"
    final = outcomes[-1].pass_rate
    assert final >= 0.9, f"训练后应 ≥90%，实际 {final}（轨迹 {[round(o.pass_rate,2) for o in outcomes]}）"


def test_training_added_l3_rule_and_l4_topology():
    orch, _, _ = _run()
    rules = [k for k in orch.solution.L3_knowledge
             if k.type == "routing_rule" and not k.superseded]
    assert any(r.dispatches_to == "safe_run_sim_diagnostics" for r in rules), "F3 规则应被训练归纳出来"
    assert len(orch.solution.L4_topology.agents) >= 2, "复合样本证据应触发双 Agent 拓扑"


def test_no_forgetting_and_clean_versions():
    orch, _, _ = _run()
    assert all(not o.rolled_back for o in orch.outcomes), "正常路径不应出现回滚"
    assert orch.log.verify(), "哈希链必须可验证"
    assert validate_existence_dependencies(orch.solution) == [], "最终方案无悬空引用"
    assert orch.solution.version >= 1, "至少一次有效提交（一个事务可携带 L3+L4 多层变更）"


def test_budget_accounted():
    orch, _, _ = _run()
    assert orch.total_cost() > 0 and not orch.budget_exceeded()
