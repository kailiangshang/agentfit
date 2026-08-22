"""Agent/Skill 活动追踪：训练过程中自动记录谁用哪个 Skill 做了什么。

证据链的一部分：每次 Skill 调用记 {agent, skill, skill_version, epoch, step,
输入摘要, 产出摘要}，落盘到 RunStore agent_activity/ 供 dashboard 呈现。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import json

# Skill 正本版本（从 skills/*.md 读取，运行时缓存）
_SKILL_VERSIONS: dict[str, str] = {}


def skill_version(skill_id: str) -> str:
    """读取 Skill 正本的当前版本号。"""
    if skill_id not in _SKILL_VERSIONS:
        skill_path = Path(__file__).parent.parent / "skills" / f"{skill_id}.md"
        if skill_path.exists():
            for line in skill_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("版本:") or line.startswith("Version:"):
                    _SKILL_VERSIONS[skill_id] = line.split(":", 1)[1].strip()
                    break
        _SKILL_VERSIONS.setdefault(skill_id, "unknown")
    return _SKILL_VERSIONS[skill_id]


@dataclass
class SkillInvocation:
    """一次 Skill 调用的记录。"""
    agent: str                 # "attributor" | "architect" | "validator" | "orchestrator" | ...
    skill: str                 # "attribution" | "aggregation" | "proposal" | ...
    epoch: int
    step: int                  # step_index（0 = epoch 级操作）
    input_summary: str = ""    # 输入的一句话摘要
    output_summary: str = ""   # 产出的一句话摘要
    detail: dict[str, Any] = field(default_factory=dict)
    skill_version: str = ""

    def __post_init__(self) -> None:
        if not self.skill_version:
            self.skill_version = skill_version(self.skill)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent, "skill": self.skill,
            "skill_version": self.skill_version,
            "epoch": self.epoch, "step": self.step,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "detail": self.detail,
        }


class ActivityTracker:
    """Orchestrator 持有，每个 Step 结束时落盘增量。"""

    def __init__(self) -> None:
        self.invocations: list[SkillInvocation] = []

    def record(self, agent: str, skill: str, epoch: int, step: int,
               input_summary: str = "", output_summary: str = "",
               **detail: Any) -> None:
        self.invocations.append(SkillInvocation(
            agent=agent, skill=skill, epoch=epoch, step=step,
            input_summary=input_summary, output_summary=output_summary,
            detail=detail,
        ))

    def save(self, run_dir: str | Path, epoch: int) -> None:
        """按 epoch 落盘该轮的 Skill 调用记录。"""
        out = Path(run_dir) / "agent_activity"
        out.mkdir(parents=True, exist_ok=True)
        epoch_invocations = [inv.to_dict() for inv in self.invocations
                              if inv.epoch == epoch]
        (out / f"epoch_{epoch:03d}.json").write_text(
            json.dumps(epoch_invocations, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
