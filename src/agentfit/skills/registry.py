"""Load the canonical Skill files without copying their content elsewhere."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models.sample import canonical_hash


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    title: str
    content: str
    content_hash: str
    source: str


class SkillRegistry:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parent
        self._cache: dict[str, SkillDefinition] | None = None

    def load(self) -> dict[str, SkillDefinition]:
        if self._cache is not None:
            return dict(self._cache)
        skills: dict[str, SkillDefinition] = {}
        for path in sorted(self.root.glob("*.md")):
            content = path.read_text(encoding="utf-8").strip()
            title = next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), "")
            if not title or "## 步骤" not in content:
                raise ValueError(f"invalid Skill definition: {path}")
            name = path.stem
            if name in skills:
                raise ValueError(f"duplicate Skill name: {name}")
            skills[name] = SkillDefinition(
                name=name, title=title, content=content,
                content_hash=canonical_hash(content), source=path.name,
            )
        self._cache = skills
        return dict(skills)

    def require(self, *names: str) -> tuple[str, ...]:
        skills = self.load()
        missing = [name for name in names if name not in skills]
        if missing:
            raise KeyError(f"unknown canonical Skills: {missing}")
        return tuple(names)
