"""Steward role: material intake, clarification and evidence-based explanation."""
from __future__ import annotations

from ..bus.messages import ResultMsg, TaskMsg
from ..models.loss import Sample


def handle(msg: TaskMsg):
    samples = [Sample(**spec) for spec in msg.payload.get("samples", [])]
    if not samples:
        return ResultMsg(
            task_id=msg.task_id, status="escalated", output=[],
            evidence={"reason": "样本不足，需澄清"},
        )
    return samples
