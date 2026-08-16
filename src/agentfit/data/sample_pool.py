"""样本池：分层抽样、批次构建、训练/回归/对照分组（A/B/C/D）。"""
from __future__ import annotations

import random
from dataclasses import field

from ..models.loss import Sample


class SamplePool:
    def __init__(self, samples: list[Sample], seed: int = 42):
        self._by_group: dict[str, list[Sample]] = {}
        for s in samples:
            self._by_group.setdefault(s.group, []).append(s)
        self._rng = random.Random(seed)
        self._cursor = 0
        self._train = self._by_group.get("train", [])
        self._rng.shuffle(self._train)

    @property
    def all_samples(self) -> list[Sample]:
        return [s for group in self._by_group.values() for s in group]

    def by_id(self) -> dict[str, Sample]:
        return {s.id: s for s in self.all_samples}

    def next_batch(self, size: int) -> list[Sample]:
        """顺序取批；池子耗尽后重新洗牌（epoch 语义）。"""
        batch = []
        while len(batch) < size:
            if self._cursor >= len(self._train):
                self._rng.shuffle(self._train)
                self._cursor = 0
            batch.append(self._train[self._cursor])
            self._cursor += 1
        return batch

    def group(self, name: str) -> list[Sample]:
        return list(self._by_group.get(name, []))
