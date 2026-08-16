"""Telecom 测试世界：样本生成 + 初始最简方案（Simple First）。

故障类型（4 类根因）：
  F1 漫游关闭且在境外      → safe_toggle_roaming
  F2 飞行模式残留          → safe_reset_airplane_mode
  F3 SIM 卡故障            → safe_run_sim_diagnostics
  F4 复合（飞行模式+漫游） → 需要 reset + toggle 两步（双 Agent 才能处理）
初始方案只覆盖 F1/F2 —— 训练必须归纳出 F3 规则并升级拓扑处理 F4。
"""
from __future__ import annotations

from agentfit.models.loss import Expected, ExpectedAction, Sample
from agentfit.models.solution import (Agent, CapabilityTool, HumanGate, Knowledge,
                                      Solution, SolidAtom, Topology)

N_PER_TYPE = 5   # 每类 5 个 → 20 个训练样本 + 少量回归/人工样本


def make_samples() -> list[Sample]:
    samples: list[Sample] = []
    for i in range(N_PER_TYPE):
        samples.append(Sample(f"F1-{i}", {"abroad": True, "roaming_off": True, "airplane": False, "sim_ok": True},
                              Expected([ExpectedAction("safe_toggle_roaming")])))
        samples.append(Sample(f"F2-{i}", {"abroad": False, "roaming_off": False, "airplane": True, "sim_ok": True},
                              Expected([ExpectedAction("safe_reset_airplane_mode")])))
        samples.append(Sample(f"F3-{i}", {"abroad": False, "roaming_off": False, "airplane": False, "sim_ok": False},
                              Expected([ExpectedAction("safe_run_sim_diagnostics")])))
        samples.append(Sample(f"F4-{i}", {"abroad": True, "roaming_off": True, "airplane": True, "sim_ok": True},
                              Expected([ExpectedAction("safe_reset_airplane_mode"),
                                        ExpectedAction("safe_toggle_roaming")]),
                              complexity="compound"))
    # 边界样本：需人工（不该被训练成自动化）
    samples.append(Sample("H-1", {"vip": True, "contract_dispute": True},
                          Expected([ExpectedAction("safe_escalate_human")]), requires_human=True))
    return samples


def make_initial_solution() -> Solution:
    """Simple First：原子齐备、工具齐备，但 L3 只归纳出 F1/F2 两条规则，L4 单 Agent。"""
    atoms = [
        SolidAtom("toggle_roaming", "write", "telecom_api", "开关漫游"),
        SolidAtom("reset_airplane_mode", "write", "telecom_api", "重置飞行模式"),
        SolidAtom("run_sim_diagnostics", "read", "telecom_api", "SIM 诊断"),
        SolidAtom("escalate_human", "human", "human_cs_team", "升级人工"),
    ]
    tools = [
        CapabilityTool("safe_toggle_roaming", ["toggle_roaming"], "安全开关漫游"),
        CapabilityTool("safe_reset_airplane_mode", ["reset_airplane_mode"], "安全重置飞行模式",
                       human_gate=HumanGate("night_window", "noc_team", "block")),
        CapabilityTool("safe_run_sim_diagnostics", ["run_sim_diagnostics"], "SIM 安全诊断"),
        CapabilityTool("safe_escalate_human", ["escalate_human"], "升级人工", human_gate=HumanGate("always", "cs_team")),
    ]
    rules = [
        Knowledge("rule_roaming", "routing_rule", condition="abroad AND roaming_off",
                  dispatches_to="safe_toggle_roaming", description="境外且漫游关 → 开漫游"),
        Knowledge("rule_airplane", "routing_rule", condition="airplane",
                  dispatches_to="safe_reset_airplane_mode", description="飞行模式残留 → 重置"),
    ]
    topology = Topology(agents=[Agent("solo", "single", uses=["rule_roaming", "rule_airplane"])])
    return Solution(version=0, L1_atoms=atoms, L2_tools=tools, L3_knowledge=rules, L4_topology=topology)
