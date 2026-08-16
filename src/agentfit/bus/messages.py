"""消息总线：元层六角色协同的唯一合法通道。

设计对应 docs/agentfit-implementation.md §三：
- TaskMsg / ResultMsg 是唯一消息格式，payload 走引用不走值
- context_ref 串起同一 epoch 的全部消息（因果链锚点）
- 角色运行时禁止直呼，一切经总线按路由表转发
- *→Auditor 是唯一广播边（证据写入）
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class MsgType(str, Enum):
    INTAKE = "INTAKE"
    CLARIFY = "CLARIFY"
    EXPLAIN = "EXPLAIN"
    BOOTSTRAP = "BOOTSTRAP"
    EXECUTE_BATCH = "EXECUTE_BATCH"
    ATTRIBUTE = "ATTRIBUTE"
    AGGREGATE = "AGGREGATE"
    PROPOSE = "PROPOSE"
    VALIDATE_STRUCT = "VALIDATE_STRUCT"
    APPLY_TRANSACTION = "APPLY_TRANSACTION"
    REGRESSION = "REGRESSION"
    LOG_APPEND = "LOG_APPEND"
    HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass
class TaskMsg:
    to: str
    type: MsgType
    payload: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_: str = "orchestrator"
    context_ref: str = ""          # 因果链锚点（如 epoch3）
    created_at: float = field(default_factory=time.time)
    deadline: float | None = None


@dataclass
class ResultMsg:
    task_id: str
    status: str                    # "ok" | "failed" | "escalated"
    output: Any = None
    evidence: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, float] = field(default_factory=dict)


Handler = Callable[[TaskMsg], ResultMsg]


class MessageBus:
    """路由表驱动的同步总线。持久化策略由 Auditor 订阅落盘。"""

    def __init__(self) -> None:
        self._routes: dict[MsgType, list[tuple[str, Handler]]] = defaultdict(list)
        self._audit_sink: Handler | None = None
        self.traffic: list[dict[str, Any]] = []      # 全量消息记录（重建因果链用）

    def register(self, role: str, types: tuple[MsgType, ...], handler: Handler) -> None:
        for t in types:
            self._routes[t].append((role, handler))

    def set_audit_sink(self, sink: Handler) -> None:
        self._audit_sink = sink

    def dispatch(self, msg: TaskMsg) -> list[ResultMsg]:
        self.traffic.append({"dir": "task", "task_id": msg.task_id, "type": msg.type.value,
                             "from": msg.from_, "to": msg.to, "context_ref": msg.context_ref})
        results = []
        for role, handler in self._routes.get(msg.type, []):
            if msg.to not in ("*", role):
                continue
            res = handler(msg)
            self.traffic.append({"dir": "result", "task_id": msg.task_id,
                                 "to": role, "status": res.status})
            results.append(res)
        if self._audit_sink is not None:
            self._audit_sink(msg)
        return results

    def context_chain(self, context_ref: str) -> list[dict[str, Any]]:
        """重建某个 context（如一个 epoch）的完整因果链。"""
        return [t for t in self.traffic if t.get("context_ref") == context_ref or t["dir"] == "result"]
