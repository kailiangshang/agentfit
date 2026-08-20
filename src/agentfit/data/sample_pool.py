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
        self._seed = seed
        self._epoch = 0

    @property
    def all_tasks(self) -> list[TaskSample]:
        return list(self._train)

    def by_id(self) -> dict[str, TaskSample]:
        return {task.id: task for task in self.all_tasks}

    def epoch_batches(self, batch_size: int, epoch: int) -> list[list[TaskSample]]:
        """规范的 Epoch 分批：每个 SampleRef 恰好进入一个 Batch，不重复不放回。

        每轮用 epoch 派生种子重排（G0 未批准有放回采样时唯一合法语义）。
        """
        order = list(self._train)
        rng = random.Random(self._seed + epoch)
        rng.shuffle(order)
        return [order[i:i + batch_size] for i in range(0, len(order), batch_size)]

    def next_batch(self, size: int) -> list[TaskSample]:
        """顺序取批；池子耗尽后重新洗牌（旧语义，仅为兼容保留）。"""
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
