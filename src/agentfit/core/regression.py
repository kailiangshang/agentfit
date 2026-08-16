"""回归验证（S6 内核）：旧样本重跑，曾通过现在失败 = 遗忘 → ROLLBACK。"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..executors.base import ExecutorBase
from ..models.loss import Sample
from ..models.solution import Solution


@dataclass
class RegressionPool:
    """分层回归池：覆盖历史全部失败模式。"""
    samples: list[Sample] = field(default_factory=list)
    passed_ids: set[str] = field(default_factory=set)

    def add(self, sample: Sample, passed: bool) -> None:
        if not any(s.id == sample.id for s in self.samples):
            self.samples.append(sample)
        if passed:
            self.passed_ids.add(sample.id)

    def update(self, results: dict[str, bool]) -> None:
        for sid, ok in results.items():
            if ok:
                self.passed_ids.add(sid)

    def forget_check(self, results: dict[str, bool]) -> list[str]:
        """返回遗忘样本 ID：曾通过、现在失败。"""
        return [sid for sid in self.passed_ids if sid in results and not results[sid]]


@dataclass
class RegressionResult:
    tested: int
    passed: int
    forgot: list[str] = field(default_factory=list)
    verdict: str = "COMMIT"       # "COMMIT" | "ROLLBACK"

    @property
    def rate(self) -> float:
        return self.passed / self.tested if self.tested else 1.0


def validate_regression(candidate: Solution, pool: RegressionPool,
                        executor: ExecutorBase) -> RegressionResult:
    if not pool.samples:
        return RegressionResult(0, 0, [], "COMMIT")
    results = {}
    for s in pool.samples:
        results[s.id] = executor.evaluate(executor.execute(candidate, s), s.expected)
    forgot = pool.forget_check(results)
    passed = sum(1 for v in results.values() if v)
    return RegressionResult(len(results), passed, forgot,
                            "ROLLBACK" if forgot else "COMMIT")
