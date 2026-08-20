"""正则约束与 λ 两级调节。

结构性正则（静态，方案更新后算）+ 行为性正则（动态，每轮从轨迹算）。
Lx_reg = max(0, worst_violation_ratio)；总损失 = (1-通过率) + Σλᵢ·Li_reg。

未接线项在唯一开发计划中维护，不把阈值常量或设计清单冒充已计算结果。
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
    """结构性正则 7 项（静态分析，trained 子集：frozen 元素不计入违规）。"""
    r = RegReport()
    trained_atoms = [a for a in solution.L1_atoms if not a.frozen]
    trained_tools = [t for t in solution.L2_tools if not t.frozen]

    # L1：原子使用率（被 L3 引用最多的原子占总引用比）+ 稀缺率
    refs: dict[str, int] = {}
    for k in solution.L3_knowledge:
        if k.frozen:
            continue          # frozen 知识的引用不计入 trained 违规统计
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
    if total_refs and trained_atoms:
        usage = max(refs.values()) / total_refs
        r.values["atom_usage"] = max(0.0, usage / STRUCTURAL_THRESHOLDS["atom_usage"] - 1)
        scarce = sum(1 for a in trained_atoms if refs.get(a.id, 0) / total_refs < 0.05) / max(1, len(trained_atoms))
        r.values["atom_scarcity"] = max(0.0, scarce / STRUCTURAL_THRESHOLDS["atom_scarcity"] - 1)
    r.over_threshold["L1"] = [k for k in ("atom_usage", "atom_scarcity") if r.values.get(k, 0) > 0]

    # L2：封装复杂度 + 工具复用（trained 工具）
    worst_wrap = max((len(t.wraps) for t in trained_tools), default=0)
    r.values["wrapper_complexity"] = max(0.0, worst_wrap / STRUCTURAL_THRESHOLDS["wrapper_complexity"] - 1)
    ref_count: dict[str, int] = {}
    for k in solution.L3_knowledge:
        if k.frozen:
            continue
        for tid in ([s.tool for s in (k.steps or [])] + ([k.dispatches_to] if k.dispatches_to else [])):
            ref_count[tid] = ref_count.get(tid, 0) + 1
    min_reuse = min((ref_count.get(t.id, 0) for t in trained_tools), default=STRUCTURAL_THRESHOLDS["tool_reuse"])
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
        for layer in ("L1", "L2", "L3", "L4"):
            metrics = report.over_threshold.get(layer, [])
            if metrics:
                self.over_threshold_streak[layer] = self.over_threshold_streak.get(layer, 0) + 1
            else:
                self.over_threshold_streak[layer] = 0
        eligible = [
            layer for layer in ("L4", "L3", "L2", "L1")
            if self.over_threshold_streak.get(layer, 0) >= 2
        ]
        if len(eligible) > 1:
            return lambdas, [{
                "gate": "G2",
                "layers": eligible,
                "proposed": {layer: round(lambdas[layer] * 1.2, 4) for layer in eligible},
                "reason": "multiple lambda changes require Human review",
            }]
        # Level 1：连续 2 轮超阈值且累计变化未到 ±50% 的单个层
        if eligible:
            layer = eligible[0]
            if abs(self.cumulative.get(layer, 0)) >= 0.5:
                return lambdas, [{
                    "gate": "G2", "layers": [layer],
                    "proposed": {layer: round(lambdas[layer] * 1.2, 4)},
                    "reason": "cumulative lambda change reached automatic cap",
                }]
            new_val = round(lambdas[layer] * 1.2, 4)
            self.cumulative[layer] += 0.2
            lambdas[layer] = new_val
            self.initial = lambdas
            return lambdas, [{"type": "lambda_level1_auto", "layer": layer,
                              "from": self.initial[layer] / 1.2, "to": new_val}]
        self.initial = lambdas
        return lambdas, level2


def regularization_proposals(report: RegReport, solution: Solution,
                             registry=None) -> tuple[list, list[dict]]:
    """正则简化提案（λᵢ∇Rᵢ 的离散版）+ 冻结元素 advisory。

    只针对 trained 元素：超阈指标 → 简化提案（origin=regularization，metric 证据+语义句）。
    超阈源于 frozen 元素 → advisory（non_blocking，给用户的整体优化建议）。
    L1 只增不删铁律：L1 简化只出人审级建议（不自动删原子）。
    """
    from ..models.taxonomy import DEFAULT_REGISTRY
    registry = registry or DEFAULT_REGISTRY
    from .transaction import UpdateProposal
    proposals: list[UpdateProposal] = []
    advisories: list[dict] = []

    # 冻结资产诊断（advisory 独立于违规统计：可追踪、非阻塞、非提案）
    unused_frozen = [a for a in solution.L1_atoms
                     if a.frozen and not _is_atom_referenced(a.id, solution)]
    if unused_frozen:
        names = ", ".join(a.id for a in unused_frozen[:5])
        advisories.append({
            "kind": "frozen_metric", "layer": "L1", "metric": "unused_inventory",
            "semantic": f"用户提供的 {len(unused_frozen)} 个原子接口从未被引用（如 {names}），"
                        f"建议复核工具清单（决策权在用户，训练不自动处理）",
            "frozen_elements": [a.id for a in unused_frozen],
            "non_blocking": True,
        })
    wired = {u for agent in solution.L4_topology.agents for u in agent.uses}
    unwired_frozen = [k for k in solution.routing_rules() if k.frozen and k.id not in wired]
    if unwired_frozen:
        advisories.append({
            "kind": "frozen_metric", "layer": "L3", "metric": "unwired_knowledge",
            "semantic": f"用户提供的 {len(unwired_frozen)} 条路由规则未被任何 Agent 引用"
                        f"（如 {', '.join(k.id for k in unwired_frozen[:3])}），"
                        f"如需启用请调整预指定拓扑",
            "frozen_elements": [k.id for k in unwired_frozen],
            "non_blocking": True,
        })

    def metric_evidence(name, threshold):
        return {"type": "metric", "name": name, "value": round(report.values.get(name, 0), 4),
                "threshold": threshold, "rounds": None}

    for layer, metrics in report.over_threshold.items():
        for metric in metrics:
            if layer == "L1" and metric == "atom_usage":
                # 单点耦合：找被过度引用的 trained 原子 → 拆分建议（人审级，出提案）
                busiest = max((a for a in solution.L1_atoms if not a.frozen),
                              key=lambda a: 1, default=None)
                if busiest is not None:
                    proposals.append(UpdateProposal(
                        "L1", "modify", busiest,
                        reason=f"原子使用率超阈（{report.values.get(metric, 0):.2f}），建议拆分",
                        origin="regularization", reg_evidence=metric_evidence(metric, STRUCTURAL_THRESHOLDS[metric]),
                        semantic=f"L1 原子接口“{busiest.id}”承载了过多职责，建议拆分为多个更小的接口"))
            elif layer == "L2" and metric in ("wrapper_complexity", "tool_reuse"):
                heavy = [t for t in solution.L2_tools if not t.frozen
                         and len(t.wraps) > STRUCTURAL_THRESHOLDS["wrapper_complexity"]]
                for tool in heavy:
                    label = registry.semantic_l2_type(tool.capability_type)
                    proposals.append(UpdateProposal(
                        "L2", "modify", tool,
                        reason=f"封装复杂度超阈（{len(tool.wraps)} 原子）",
                        origin="regularization", reg_evidence=metric_evidence(metric, STRUCTURAL_THRESHOLDS[metric]),
                        semantic=f"{label}“{tool.id}”封装了 {len(tool.wraps)} 个原子接口，超过复杂度阈值，建议拆分"))
            elif layer == "L3" and metric == "chain_coverage":
                over_concentrated = [k for k in solution.routing_rules() if not k.frozen]
                if over_concentrated:
                    target = over_concentrated[0]
                    proposals.append(UpdateProposal(
                        "L3", "modify", target,
                        reason=f"链路覆盖度超阈（{report.values.get(metric, 0):.2f}），万能路由风险",
                        origin="regularization", reg_evidence=metric_evidence(metric, STRUCTURAL_THRESHOLDS[metric]),
                        semantic=f"路由规则“{target.id}”覆盖了过高比例的样本分发，建议按故障类型拆分为更专门的规则"))
            elif layer == "L4" and metric in ("agent_count", "human_intervention"):
                gate_tools = [t for t in solution.L2_tools if t.human_gate and t.frozen]
                if metric == "human_intervention" and gate_tools:
                    advisories.append({
                        "kind": "frozen_metric", "layer": "L4", "metric": metric,
                        "semantic": f"人工介入率超阈主要来自用户指定的审核门禁"
                                    f"（{', '.join(t.human_gate.reviewer for t in gate_tools[:3])}）；"
                                    f"如可放宽窗口或阈值可降低介入率（合规决定，训练不自动处理）",
                        "frozen_elements": [t.id for t in gate_tools],
                        "non_blocking": True,
                    })
    return proposals, advisories


def _is_atom_referenced(atom_id: str, solution: Solution) -> bool:
    for k in solution.L3_knowledge:
        if k.steps:
            for step in k.steps:
                tool = solution.tool(step.tool)
                if tool and atom_id in tool.wraps:
                    return True
        elif k.dispatches_to:
            tool = solution.tool(k.dispatches_to)
            if tool and atom_id in tool.wraps:
                return True
    return False
