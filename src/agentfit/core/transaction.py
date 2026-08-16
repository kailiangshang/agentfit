"""ChangeTransaction：级联变更的原子性保障（骨架 §四 / 实现 §九）。

BEGIN → APPLY(自底向上 L1→L2→L3→L4) → VALIDATE → COMMIT/ROLLBACK。
禁止中间状态、禁止部分成功。纯确定性。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from ..models.solution import Solution
from ..solution.validator import validate_existence_dependencies, validate_same_layer_constraints

LAYER_ORDER = {"L1": 0, "L2": 1, "L3": 2, "L4": 3}


@dataclass
class UpdateProposal:
    """一条分层更新建议（Architect 产出，人审后进事务）。"""
    layer: str                     # "L1" | "L2" | "L3" | "L4"
    action: str                    # "add" | "modify" | "supersede"
    element: Any                   # SolidAtom | CapabilityTool | Knowledge | Topology 片段
    reason: str = ""
    evidence_sample_ids: list[str] | None = None


class ValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class ChangeTransaction:
    def __init__(self, solution: Solution, changes: list[UpdateProposal]):
        self.solution = solution
        self.changes = sorted(changes, key=lambda c: LAYER_ORDER.get(c.layer, 99))   # 自底向上
        self.snapshot: Solution | None = None
        self.status = "PENDING"
        self.applied: list[UpdateProposal] = []

    def execute(self) -> Solution:
        """应用全部变更并验证；任何失败自动回滚。"""
        self.snapshot = copy.deepcopy(self.solution)
        self.status = "IN_PROGRESS"
        try:
            for change in self.changes:
                self._apply(change)
            errors = validate_existence_dependencies(self.solution)
            errors += validate_same_layer_constraints(self.solution)
            if errors:
                raise ValidationError(errors)
        except Exception:
            self.rollback()
            raise
        self._commit()
        return self.solution

    def _apply(self, change: UpdateProposal) -> None:
        layer, action, elem = change.layer, change.action, change.element
        store = {
            "L1": self.solution.L1_atoms, "L2": self.solution.L2_tools,
            "L3": self.solution.L3_knowledge,
        }
        if layer in store:
            items = store[layer]
            existing = next((i for i in items if i.id == getattr(elem, "id", None)), None)
            if action == "add" and existing is None:
                items.append(elem)
            elif action == "add" and existing is not None:
                items[items.index(existing)] = elem      # 幂等：同 id 视为替换
            elif action == "supersede" and existing is not None:
                existing.superseded = True
            elif action == "modify" and existing is not None:
                items[items.index(existing)] = elem
            else:
                raise ValueError(f"无法应用变更 {layer}/{action}/{getattr(elem, 'id', elem)}")
        elif layer == "L4":
            if action in ("add", "modify"):
                self.solution.L4_topology = elem        # 拓扑整体替换（L4 变更影响全局，走人审）
            else:
                raise ValueError(f"L4 不支持 {action}")
        else:
            raise ValueError(f"未知层 {layer}")
        self.applied.append(change)

    def _commit(self) -> None:
        self.solution.version += 1
        self.status = "COMMITTED"

    def rollback(self) -> None:
        """恢复快照（回归失败或验证失败时调用）。"""
        if self.snapshot is None:
            return
        self.solution.__dict__.update(self.snapshot.__dict__)
        self.solution.version = self.snapshot.version
        self.applied.clear()
        self.status = "ROLLED_BACK"
