"""Validator role: deterministic structure and regression decisions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..bus.messages import MsgType, ResultMsg, TaskMsg
from ..models.solution import Solution
from ..solution import validator as solution_validator

if TYPE_CHECKING:
    from .orchestrator import Orchestrator


def make_handler(orchestrator: "Orchestrator"):
    def handle(msg: TaskMsg) -> ResultMsg:
        if msg.type == MsgType.VALIDATE_STRUCT:
            solution: Solution = msg.payload.get("solution", orchestrator.solution)
            errors = solution_validator.validate_existence_dependencies(solution)
            errors += solution_validator.validate_same_layer_constraints(solution)
            return ResultMsg(
                task_id=msg.task_id,
                status="ok" if not errors else "failed",
                output=errors,
            )
        return ResultMsg(task_id=msg.task_id, status="ok", output=None)
    return handle
