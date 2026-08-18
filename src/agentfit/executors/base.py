"""执行器接口：任何环境实现三方法即可插拔（τ²-bench / 模拟器 / 影子模式）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.loss import Expected, Trace
from ..models.sample import TaskSample
from ..models.solution import Solution


class ExecutorBase(ABC):
    def runtime_provenance(self) -> dict[str, str]:
        """Describe the resolved executor without leaking it into the four-layer Solution."""
        cls = type(self)
        return {"executor": f"{cls.__module__}.{cls.__qualname__}"}

    @abstractmethod
    def execute(self, solution: Solution, sample: TaskSample) -> Trace: ...

    @abstractmethod
    def evaluate(self, trace: Trace, expected: Expected) -> bool: ...

    def replay(self, solution: Solution, samples: list[TaskSample]) -> list[bool]:
        return [self.evaluate(self.execute(solution, s), s.expected) for s in samples]
