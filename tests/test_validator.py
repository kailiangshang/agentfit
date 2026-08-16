"""单元测试：存在依赖 / 同层约束 / 事务 / 正则 / 日志 / 归因。"""
from agentfit.core.regularization import LambdaController, RegReport, compute_structural
from agentfit.core.transaction import ChangeTransaction, UpdateProposal, ValidationError
from agentfit.log.training_log import EpochEntry, TrainingLog
from agentfit.models.solution import (Agent, CapabilityTool, Knowledge, Solution,
                                      SolidAtom, Topology)
from agentfit.solution.validator import (validate_existence_dependencies,
                                         validate_same_layer_constraints)

from telecom_world import make_initial_solution, make_samples


# ---------- 存在依赖 ----------
def test_initial_solution_has_no_dangling_refs():
    assert validate_existence_dependencies(make_initial_solution()) == []


def test_dangling_tool_wrap_detected():
    sol = make_initial_solution()
    sol.L2_tools.append(CapabilityTool("safe_ghost", ["ghost_atom"], "封装不存在的原子"))
    errors = validate_existence_dependencies(sol)
    assert any("ghost_atom" in e for e in errors)


def test_dangling_knowledge_dispatch_detected():
    sol = make_initial_solution()
    sol.L3_knowledge.append(Knowledge("rule_bad", "routing_rule", condition="x", dispatches_to="no_such_tool"))
    errors = validate_existence_dependencies(sol)
    assert any("no_such_tool" in e for e in errors)


def test_dangling_l4_usage_detected():
    sol = make_initial_solution()
    sol.L4_topology = Topology(agents=[Agent("a", "single", uses=["no_such_knowledge"])])
    errors = validate_existence_dependencies(sol)
    assert any("no_such_knowledge" in e for e in errors)


# ---------- 同层约束 ----------
def test_routing_rule_dispatching_knowledge_is_illegal():
    sol = make_initial_solution()
    sol.L3_knowledge.append(Knowledge("rule_meta", "routing_rule", condition="y", dispatches_to="rule_roaming"))
    errors = validate_same_layer_constraints(sol)
    assert errors, "路由规则调度 L3 知识 = 执行时耦合，必须被查出"


# ---------- ChangeTransaction ----------
def test_transaction_commits_and_bumps_version():
    sol = make_initial_solution()
    tx = ChangeTransaction(sol, [UpdateProposal("L3", "add", Knowledge("rule_new", "routing_rule",
                                                condition="sim_ok AND NOT airplane",
                                                dispatches_to="safe_run_sim_diagnostics"))])
    out = tx.execute()
    assert tx.status == "COMMITTED" and out.version == 1 and out.knowledge("rule_new") is not None


def test_transaction_rolls_back_on_invalid():
    sol = make_initial_solution()
    tx = ChangeTransaction(sol, [UpdateProposal("L3", "add", Knowledge("rule_bad", "routing_rule",
                                                condition="z", dispatches_to="missing_tool"))])
    try:
        tx.execute()
        assert False, "应当抛 ValidationError"
    except ValidationError:
        pass
    assert tx.status == "ROLLED_BACK" and sol.version == 0 and sol.knowledge("rule_bad") is None


# ---------- 正则 + λ ----------
def test_structural_regularization_green_on_initial():
    report = compute_structural(make_initial_solution())
    # L3/L4 初始全绿；L1 稀缺率与 L2 复用率在训练早期合法地报"原子/工具未被演练"
    # （真实信号：随着训练归纳规则，未演练容量会被消化）
    assert report.layer_reg["L3"] == 0.0
    assert report.layer_reg["L4"] == 0.0


def test_atom_overusage_detected():
    sol = make_initial_solution()
    # 造出单原子被全量引用的场景：只保留一条规则且只引用一个工具
    sol.L3_knowledge = [Knowledge("rule_only", "routing_rule", condition=None,
                                  dispatches_to="safe_toggle_roaming")]
    report = compute_structural(sol)
    assert report.values.get("atom_usage", 0) > 0


def test_lambda_level1_auto_after_two_rounds():
    ctl = LambdaController()
    bad = RegReport(layer_reg={"L1": 0, "L2": 0, "L3": 0.5, "L4": 0},
                    over_threshold={"L3": ["chain_coverage"]})
    ctl.observe(bad)
    lambdas, events = ctl.observe(bad)     # 连续第 2 轮 → 触发 Level 1
    assert lambdas["L3"] == round(0.3 * 1.2, 4)
    assert events and events[0]["type"] == "lambda_L1_auto"


# ---------- 哈希链日志 ----------
def test_log_chain_verifies_and_detects_tamper():
    log = TrainingLog()
    log.append(EpochEntry(epoch=1, solution_version=1, pass_rate=0.6))
    log.append(EpochEntry(epoch=2, solution_version=2, pass_rate=0.85))
    assert log.verify()
    log.entries[0]["entry"]["pass_rate"] = 0.99   # 篡改历史
    assert not log.verify()


# ---------- 归因 ----------
def test_attribution_missing_rule_then_l4():
    from agentfit.core.attribution import attribute_loss
    from agentfit.executors.simulator import SimulatorExecutor
    sol = make_initial_solution()
    ex = SimulatorExecutor()
    samples = {s.id: s for s in make_samples()}

    lt = attribute_loss(samples["F3-0"], ex.execute(sol, samples["F3-0"]), sol)
    assert (lt.root_cause_layer, lt.failure_mode) == ("L3", "missing_rule")

    lt = attribute_loss(samples["F4-0"], ex.execute(sol, samples["F4-0"]), sol)
    assert (lt.root_cause_layer, lt.failure_mode) == ("L4", "topology_mismatch")


def test_attribution_side_issue_not_root():
    from agentfit.core.attribution import is_root_cause
    from agentfit.models.loss import Trace, TraceStep
    trace = Trace("x", "FAIL", steps=[
        TraceStep("L2", "logger", ok=False, error="日志格式错误", output="raw", expected_output="raw"),
        TraceStep("L2", "safe_fix", ok=False, error="关键失败", output="bad", expected_output="good", downstream=[1]),
    ])
    assert is_root_cause(0, trace) is False   # 旁路：无下游
    assert is_root_cause(1, trace) is True    # 关键路径：有下游且输出不符
