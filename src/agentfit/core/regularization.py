"""正则约束：16 指标 + λ 两级调节（骨架 §三/§四 的确定性内核）。

结构性正则（静态，方案更新后算）+ 行为性正则（动态，每轮从轨迹算）。
Lx_reg = max(0, worst_violation_ratio)；总损失 = (1-通过率) + Σλᵢ·Li_reg。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models.loss import Trace
from ..models.solution import Solution

# ---- 阈值表（骨架 §三；单一事实来源，正则与测试共用） ----
STRUCTURAL_THRESHOLDS = {
    "atom_usage": 0.80,       # L1 单原子被引用占比 > 80% = 过耦合
    "atom_scarcity": 0.30,    # L1 使用率<5% 的原子占比 > 30% = 冗余
    "wrapper_complexity": 5,  # L2 封装 > 5 原子 = 太复杂
    "tool_reuse": 2,          # L2 被 < 2 条链路引用 = 低复用
    "chain_length": 10,       # L3 链 > 10 步 = 太长
    "branch_factor": 15,      # L3 分支 > 15 = 太复杂
    "agent_count": 5,         # L4 Agent > 5 = 需要理由
}
BEHAVIORAL_THRESHOLDS = {
    "chain_coverage": 0.60,       # L3 单链覆盖 > 60% = 过度集中
    "human_intervention": 0.30,   # L4 人工介入 > 30% = 自动化价值低
    "communication_overhead": 10, # L4 消息 > 10 轮/样本
    "atom_growth": 5,             # L1 每轮新增 > 5 = 过快
    "knowledge_conflict": 0.05,   # L3 同输入不同输出 > 5%
    "experience_dedup": 0.20,     # L3 教训重复 > 20%
    "topology_change": 1,         # L4 每轮拓扑变更 > 1
}


@dataclass
class RegReport:
    values: dict[str, float] = field(default_factory=dict)    # 指标 → 超限比(0 = 未超)
    layer_reg: dict[str, float] = field(default_factory=lambda: {"L1": 0.0, "L2": 0.0, "L3": 0.0, "L4": 0.0})
    over_threshold: dict[str, list[str]] = field(default_factory=dict)   # 层 → 超限指标名

    def total_loss(self, pass_rate: float, lambdas: dict[str, float]) -> float:
        return (1.0 - pass_rate) + sum(lambdas[l] * self.layer_reg[l] for l in self.layer_reg)


def compute_structural(solution: Solution) -> RegReport:
    """结构性正则 7 项（静态分析）。"""
    r = RegReport()
    n_rules = max(1, len(solution.routing_rules()))

    # L1：原子使用率（被 L3 引用最多的原子占总引用比）+ 稀缺率
    refs: dict[str, int] = {}
    for k in solution.L3_knowledge:
        if k.steps:
            for s in k.steps:
                for t in solution.L2_tools:
                    if t.id == s.tool:
                        for a in t.wraps:
                            refs[a] = refs.get(a, 0) + 1
        elif k.dispatches_to:
            t = solution.tool(k.dispatches_to)
            if t:
                for a in t.wraps:
                    refs[a] = refs.get(a, 0) + 1
    total_refs = sum(refs.values())
    if total_refs:
        usage = max(refs.values()) / total_refs
        r.values["atom_usage"] = max(0.0, usage / STRUCTURAL_THRESHOLDS["atom_usage"] - 1)
        scarce = sum(1 for a in solution.L1_atoms if refs.get(a.id, 0) / total_refs < 0.05) / max(1, len(solution.L1_atoms))
        r.values["atom_scarcity"] = max(0.0, scarce / STRUCTURAL_THRESHOLDS["atom_scarcity"] - 1)
    r.over_threshold["L1"] = [k for k in ("atom_usage", "atom_scarcity") if r.values.get(k, 0) > 0]

    # L2：封装复杂度 + 工具复用
    worst_wrap = max((len(t.wraps) for t in solution.L2_tools), default=0)
    r.values["wrapper_complexity"] = max(0.0, worst_wrap / STRUCTURAL_THRESHOLDS["wrapper_complexity"] - 1)
    ref_count: dict[str, int] = {}
    for k in solution.L3_knowledge:
        for tid in ([s.tool for s in (k.steps or [])] + ([k.dispatches_to] if k.dispatches_to else [])):
            ref_count[tid] = ref_count.get(tid, 0) + 1
    min_reuse = min((ref_count.get(t.id, 0) for t in solution.L2_tools), default=STRUCTURAL_THRESHOLDS["tool_reuse"])
    if ref_count:
        r.values["tool_reuse"] = max(0.0, (STRUCTURAL_THRESHOLDS["tool_reuse"] - min_reuse) / STRUCTURAL_THRESHOLDS["tool_reuse"])
    r.over_threshold["L2"] = [k for k in ("wrapper_complexity", "tool_reuse") if r.values.get(k, 0) > 0]

    # L3：链长 + 分支因子
    longest = max((len(k.steps or []) for k in solution.L3_knowledge), default=0)
    r.values["chain_length"] = max(0.0, longest / STRUCTURAL_THRESHOLDS["chain_length"] - 1)
    branch = max((len(solution.routing_rules()) for _ in [0]), default=0)
    r.values["branch_factor"] = max(0.0, branch / STRUCTURAL_THRESHOLDS["branch_factor"] - 1)
    r.over_threshold["L3"] = [k for k in ("chain_length", "branch_factor") if r.values.get(k, 0) > 0]

    # L4：Agent 数量
    n_agents = len(solution.L4_topology.agents)
    r.values["agent_count"] = max(0.0, n_agents / STRUCTURAL_THRESHOLDS["agent_count"] - 1)
    r.over_threshold["L4"] = [k for k in ("agent_count",) if r.values.get(k, 0) > 0]

    for layer, keys in (("L1", ("atom_usage", "atom_scarcity")), ("L2", ("wrapper_complexity", "tool_reuse")),
                        ("L3", ("chain_length", "branch_factor")), ("L4", ("agent_count",))):
        r.layer_reg[layer] = max((r.values.get(k, 0.0) for k in keys), default=0.0)
    return r


def compute_behavioral(solution: Solution, traces: list[Trace], prev_solution: Solution | None = None) -> dict[str, float]:
    """行为性正则（每轮训练后，从执行轨迹计算）。返回指标 → 超限比。"""
    values: dict[str, float] = {}
    if not traces:
        return values
    # L3 链路覆盖度
    hit: dict[str, int] = {}
    for t in traces:
        if t.routed_knowledge_id:
            hit[t.routed_knowledge_id] = hit.get(t.routed_knowledge_id, 0) + 1
    if hit:
        coverage = max(hit.values()) / len(traces)
        values["chain_coverage"] = max(0.0, coverage / BEHAVIORAL_THRESHOLDS["chain_coverage"] - 1)
    # L4 人工介入率
    human = sum(1 for t in traces if any(s.element_id == "human_review" for s in t.steps)) / len(traces)
    values["human_intervention"] = max(0.0, human / BEHAVIORAL_THRESHOLDS["human_intervention"] - 1)
    # L4 通信开销（拓扑边上的消息轮次近似 = 步骤数/样本）
    avg_steps = sum(len(t.steps) for t in traces) / len(traces)
    values["communication_overhead"] = max(0.0, avg_steps / BEHAVIORAL_THRESHOLDS["communication_overhead"] - 1)
    # L1 原子增长率
    if prev_solution is not None:
        growth = len(solution.L1_atoms) - len(prev_solution.L1_atoms)
        values["atom_growth"] = max(0.0, growth / BEHAVIORAL_THRESHOLDS["atom_growth"] - 1)
    return values


def merge_behavioral(structural: RegReport, behavioral: dict[str, float]) -> RegReport:
    layer_of = {"chain_coverage": "L3", "human_intervention": "L4", "communication_overhead": "L4", "atom_growth": "L1"}
    for key, val in behavioral.items():
        structural.values[key] = val
        if val > 0:
            structural.over_threshold.setdefault(layer_of[key], []).append(key)
            structural.layer_reg[layer_of[key]] = max(structural.layer_reg[layer_of[key]], val)
    return structural


@dataclass
class LambdaController:
    """λ 两级调节（骨架 §四）。Level 1 自动 ≤±20%；Level 2 生成建议进人审，不响应=不应用。"""
    initial: dict[str, float] = field(default_factory=lambda: {"L1": 0.1, "L2": 0.2, "L3": 0.3, "L4": 0.4})
    over_threshold_streak: dict[str, int] = field(default_factory=dict)
    cumulative: dict[str, float] = field(default_factory=lambda: {k: 0.0 for k in ("L1", "L2", "L3", "L4")})

    def observe(self, report: RegReport) -> tuple[dict[str, float], list[dict]]:
        """每轮调用：返回 (新λ, Level2建议列表)。每轮最多自动调 1 个 λ。"""
        lambdas = dict(self.initial)
        level2: list[dict] = []
        for layer, metrics in report.over_threshold.items():
            self.over_threshold_streak[layer] = self.over_threshold_streak.get(layer, 0) + 1
        for layer in list(self.over_threshold_streak):
            if layer not in report.over_threshold:
                self.over_threshold_streak[layer] = 0
        # Level 1：连续 2 轮超阈值且累计变化未到 ±50% 的第一个层
        for layer in ("L4", "L3", "L2", "L1"):
            if self.over_threshold_streak.get(layer, 0) >= 2 and abs(self.cumulative.get(layer, 0)) < 0.5:
                new_val = round(lambdas[layer] * 1.2, 4)
                self.cumulative[layer] += 0.2
                lambdas[layer] = new_val
                level2_note = {"type": "lambda_L1_auto", "layer": layer, "from": self.initial[layer], "to": new_val}
                self.initial = lambdas
                return lambdas, [level2_note]
        self.initial = lambdas
        return lambdas, level2
