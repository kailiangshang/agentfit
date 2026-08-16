"""执行器接口：任何环境实现三方法即可插拔（τ²-bench / 模拟器 / 影子模式）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.loss import Expected, Sample, Trace
from ..models.solution import Solution


class ExecutorBase(ABC):
    @abstractmethod
    def execute(self, solution: Solution, sample: Sample) -> Trace: ...

    @abstractmethod
    def evaluate(self, trace: Trace, expected: Expected) -> bool: ...

    def replay(self, solution: Solution, samples: list[Sample]) -> list[bool]:
        return [self.evaluate(self.execute(solution, s), s.expected) for s in samples]
