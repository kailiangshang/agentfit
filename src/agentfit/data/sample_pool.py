"""样本池：分层抽样、批次构建、训练/回归/对照分组（A/B/C/D）。"""
from __future__ import annotations

import random
from ..models.sample import TaskSample


class SamplePool:
    def __init__(self, samples: list[TaskSample], seed: int = 42):
        if any(not isinstance(item, TaskSample) for item in samples):
            raise TypeError("SamplePool accepts canonical TaskSample objects only")
        tasks = list(samples)
        self._rng = random.Random(seed)
        self._cursor = 0
        self._train = tasks
        self._rng.shuffle(self._train)

    @property
    def all_tasks(self) -> list[TaskSample]:
        return list(self._train)

    def by_id(self) -> dict[str, TaskSample]:
        return {task.id: task for task in self.all_tasks}

    def next_batch(self, size: int) -> list[TaskSample]:
        """顺序取批；池子耗尽后重新洗牌（epoch 语义）。"""
        batch = []
        while len(batch) < size:
            if self._cursor >= len(self._train):
                self._rng.shuffle(self._train)
                self._cursor = 0
            batch.append(self._train[self._cursor])
            self._cursor += 1
        return batch

    def group(self, name: str) -> list[TaskSample]:
        return list(self._train) if name == "train" else []
