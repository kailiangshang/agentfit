"""正则传播 + 冻结语义 + advisory + 语义双轨 合同测试（设计定稿 §四-§七）。

- 正则在 trained 子集上计算；frozen 不计入违规、不触发 λ
- 正则产生简化提案（origin=regularization，metric 证据 + 语义句）
- 任务提案加剧超阈指标 → reg_conflict 标注
- modify/supersede 冻结元素 → 事务拒绝
- 根因落冻结元素 → advisory（非阻塞非提案）
- 提案带 semantic 双轨呈现并落盘
"""
from __future__ import annotations

import json

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.core.regularization import (compute_structural,
                                          regularization_proposals)
from agentfit.core.proposals import annotate_reg_conflicts
from agentfit.core.transaction import ChangeTransaction, UpdateProposal, ValidationError
from agentfit.data.sample_pool import SamplePool
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.models.solution import Knowledge, Solution
from agentfit.models.taxonomy import (CORE_L1_DOMAINS, CustomType,
                                      TypeRegistry, registry_from_dict)
from agentfit.solution.validator import validate_taxonomy

from telecom_world import make_initial_solution, make_samples


# ---------- 类型学 + 注册制 ----------
def test_core_taxonomy_closed_and_registry_validated():
    sol = make_initial_solution()
    assert validate_taxonomy(sol) == []
    # 非法域被拒
    bad = make_initial_solution()
    bad.L1_atoms[0].domain = "quantum_interface"
    assert any("能力域非法" in e for e in validate_taxonomy(bad))
    # 注册制：自定义必须挂靠 core + 带 label
    registry = TypeRegistry(customs=[CustomType("hri", "L1_domain", "external_system", "医院信息系统接口")])
    assert registry.validate() == []
    assert "hri" in registry.l1_domains()
    assert registry.semantic_l1_domain("hri") == "医院信息系统接口"   # 自定义用用户描述
    bad_registry = TypeRegistry(customs=[CustomType("hri", "L1_domain", "not_core", "x")])
    assert bad_registry.validate() != []
    # 材料节解析
    parsed = registry_from_dict({"customs": [{"name": "hri", "layer": "L1_domain",
                                              "parent": "external_system", "label": "HIS 接口"}]})
    assert parsed.l1_domains() > set(CORE_L1_DOMAINS)


# ---------- 冻结语义 ----------
def test_frozen_elements_are_protected_and_excluded_from_regularization():
    sol = make_initial_solution()
    # 冻结元素的违规不计：把大量冻结原子塞进去 → 稀缺率只按 trained 算
    from agentfit.models.solution import SolidAtom
    trained = sol
    frozen_sol = make_initial_solution()
    for i in range(20):
        frozen_sol.L1_atoms.append(SolidAtom(f"frozen_unused_{i}", "read",
                                             description="用户提供的闲置接口", frozen=True))
    reg_frozen = compute_structural(frozen_sol)
    reg_plain = compute_structural(sol)
    # 冻结的未使用原子不应推高 trained 稀缺违规（frozen 排除后两者一致）
    assert reg_frozen.values.get("atom_scarcity", 0) == reg_plain.values.get("atom_scarcity", 0)

    # 提案保护：supersede 冻结知识 → 事务拒绝
    frozen_rule = Knowledge(id="frozen_rule", type="routing_rule", frozen=True,
                            condition="airplane", dispatches_to="safe_reset_airplane_mode")
    sol2 = make_initial_solution()
    sol2.L3_knowledge.append(frozen_rule)
    tx = ChangeTransaction(sol2, [UpdateProposal("L3", "supersede", frozen_rule, reason="test")])
    try:
        tx.execute()
        raise AssertionError("冻结元素不可被提案下线")
    except ValidationError:
        pass
    # trained 元素照常可动
    trained_rule = sol2.knowledge("rule_roaming")
    assert trained_rule.frozen is False


# ---------- 正则简化提案 ----------
def test_regularization_proposals_target_only_trained_with_metric_evidence():
    sol = make_initial_solution()
    # 造过度集中：只保留一条规则且它派发到唯一被引用工具
    from agentfit.models.solution import Agent, Topology
    sol.L3_knowledge = [Knowledge("rule_only", "routing_rule", condition=None,
                                  dispatches_to="safe_toggle_roaming")]
    sol.L4_topology = Topology(agents=[Agent("solo", "single", uses=["rule_only"])])
    reg = compute_structural(sol)
    proposals, advisories = regularization_proposals(reg, sol)
    reg_proposals = [p for p in proposals if p.origin == "regularization"]
    assert reg_proposals, "过度集中的 trained 方案必须产出正则简化提案"
    for p in reg_proposals:
        assert p.reg_evidence and p.reg_evidence.get("type") == "metric"
        assert p.semantic, "正则提案必须带语义句"
    # 冻结造成的同样超阈 → 只出 advisory 不出提案
    frozen_heavy = make_initial_solution()
    frozen_heavy.L3_knowledge = [Knowledge("rule_only", "routing_rule", frozen=True,
                                           condition=None, dispatches_to="safe_toggle_roaming")]
    reg2 = compute_structural(frozen_heavy)
    proposals2, advisories2 = regularization_proposals(reg2, frozen_heavy)
    assert not [p for p in proposals2 if p.origin == "regularization"]
    assert advisories2, "冻结元素超阈必须出 advisory"


# ---------- 冲突标注 ----------
def test_conflict_annotation_flags_task_proposals_worsening_violated_metric():
    sol = make_initial_solution()
    reg = compute_structural(sol)
    # 假设 L3 覆盖度已超阈：任务提案再加派发到同一工具的规则 → 冲突
    reg.values["chain_coverage"] = 0.2   # 模拟已违规
    reg.over_threshold["L3"] = ["chain_coverage"]
    reg.layer_reg["L3"] = 0.2
    task = UpdateProposal("L3", "add", Knowledge("rule_x", "routing_rule",
                                                 condition="a", dispatches_to="safe_toggle_roaming"),
                          origin="task")
    annotate_reg_conflicts([task], reg, sol)
    assert task.reg_conflict == "chain_coverage", "加剧超阈指标的任务提案必须被标注"


# ---------- 根因落冻结元素 → advisory（编排分流） ----------
def test_full_training_routes_frozen_root_cause_to_advisory(tmp_path):
    samples = make_samples()
    adaptation = [s for s in samples if not s.id.startswith("V-")]
    validation = [s for s in samples if s.id.startswith("V-")]
    sol = make_initial_solution()
    # 冻结现有全部规则 + Agent → 一切知识缺口都源于冻结边界
    for k in sol.L3_knowledge:
        k.frozen = True
    for a in sol.L4_topology.agents:
        a.frozen = True
    run_dir = tmp_path / "advisory-run"
    orch = Orchestrator(sol, SamplePool(adaptation), SimulatorExecutor(),
                        TrainingConfig(batch_size=6, max_epochs=2, review_policy=AutoApprove()),
                        run_dir=str(run_dir), scenario="frozen-boundary",
                        validation_samples=validation)
    build_team(orch)
    orch.train()
    advisory_dir = run_dir / "optimization_suggestions"
    assert advisory_dir.is_dir() and list(advisory_dir.glob("*.json")), \
        "冻结边界导致的失败必须产生 advisory"
    suggestion = json.loads(next(iter(advisory_dir.glob("*.json"))).read_text(encoding="utf-8"))
    assert suggestion.get("non_blocking") is True
    assert suggestion.get("semantic")


# ---------- 语义双轨落盘 ----------
def test_proposals_carry_semantic_and_origin_through_transaction(tmp_path):
    samples = make_samples()
    run_dir = tmp_path / "semantic-run"
    orch = Orchestrator(make_initial_solution(), SamplePool(samples),
                        SimulatorExecutor(),
                        TrainingConfig(batch_size=24, max_epochs=1, review_policy=AutoApprove()),
                        run_dir=str(run_dir), scenario="semantic")
    build_team(orch)
    orch.train()
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    committed = summary.get("transactions_committed") or []
    changes = [c for t in committed for c in (t.get("changes") or [])]
    assert changes, "训练应产生提交"
    assert all(c.get("origin") in ("task", "regularization") for c in changes), \
        "每条变更必须带来源"
    assert all(c.get("semantic") for c in changes), "每条变更必须带语义句"
