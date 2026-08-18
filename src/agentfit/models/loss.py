"""执行轨迹与损失轨迹：归因的输入输出。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExpectedAction:
    tool: str                      # 期望调用的 L2 工具（或 L1 原子名）
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Expected:
    actions: list[ExpectedAction] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceStep:
    """执行轨迹中的一步。downstream 记录消费本步输出的后续步骤索引（关键路径判定用）。"""
    layer: str                     # "L1" | "L2" | "L3" | "L4"
    element_id: str
    action: str = ""
    ok: bool = True
    error: str | None = None
    output: Any = None
    expected_output: Any = None
    downstream: list[int] = field(default_factory=list)


@dataclass
class Trace:
    """一次样本执行的完整轨迹。"""
    sample_id: str
    result: str = "PASS"           # "PASS" | "FAIL" | "ERROR"
    steps: list[TraceStep] = field(default_factory=list)
    routed_knowledge_id: str | None = None    # L3 命中的路由规则
    cost_usd: float = 0.0
    risk_events: list[str] = field(default_factory=list)
    error_scope: str | None = None  # "runtime" | "evaluation"；不属于 L1-L4
    error_code: str | None = None
    runtime_ref: str = ""           # 本次解析后的运行环境/沙箱证据引用


@dataclass
class SideIssue:
    """附带问题：发现但不构成根因的异常，不阻塞归因。"""
    layer: str
    element_id: str
    detail: str


@dataclass
class LossTrace:
    """归因产物：失败样本的根因判定。"""
    sample_id: str
    root_cause_layer: str          # "L1" | "L2" | "L3" | "L4" | "human" | "eval_error"
    root_cause_element: str
    failure_mode: str              # "missing_atom" | "tool_error" | "missing_rule" | "routing_error" | "topology_mismatch" | "needs_human" | "eval_error"
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    side_issues: list[SideIssue] = field(default_factory=list)
