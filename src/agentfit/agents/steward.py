"""Steward role: material intake, clarification and evidence-based explanation."""
from __future__ import annotations

from ..bus.messages import ResultMsg, TaskMsg
from ..materials.compiler import compile_material_bundle
from ..models.sample import TaskSample


def handle(msg: TaskMsg):
    bundle = msg.payload.get("material_bundle")
    if isinstance(bundle, dict):
        tasks = list(compile_material_bundle(bundle).task_samples)
    else:
        tasks = [item for item in msg.payload.get("task_samples", [])
                 if isinstance(item, TaskSample)]
    if not tasks:
        return ResultMsg(
            task_id=msg.task_id, status="escalated", output=[],
            evidence={"reason": "样本不足，需澄清"},
        )
    return tasks
