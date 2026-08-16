"""AgentRuntime：角色的消息循环基类。

确定性边界（实现文档 §一）：Steward/Attributor/Architect 是 LLM 认知体（本实现先落确定性内核，
LLM 槽位经接口注入）；Orchestrator/Validator/Auditor 是确定性官员（无 LLM）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..bus.messages import Handler, MsgType, ResultMsg, TaskMsg


@dataclass
class AgentRuntime:
    name: str
    handled_types: tuple[MsgType, ...]
    handler: Handler
    llm_slots: list[str] = field(default_factory=list)     # 声明的 LLM 槽位（审计用）
    total_invocations: int = 0
    total_llm_calls: int = 0
    total_cost_usd: float = 0.0

    def handle(self, msg: TaskMsg) -> ResultMsg:
        self.total_invocations += 1
        result = self.handler(msg)
        self.total_cost_usd += result.cost.get("usd", 0.0)
        self.total_llm_calls += result.cost.get("llm_calls", 0)
        return result


def make_agent(name: str, types: tuple[MsgType, ...], fn: Callable[[TaskMsg], Any],
               llm_slots: list[str] | None = None) -> AgentRuntime:
    """快速构造：fn 返回任意结果，包装成 ResultMsg。"""

    def handler(msg: TaskMsg) -> ResultMsg:
        out = fn(msg)
        if isinstance(out, ResultMsg):
            return out
        return ResultMsg(task_id=msg.task_id, status="ok", output=out)

    return AgentRuntime(name, types, handler, llm_slots or [])
