"""样本聚类（简版）：按布尔特征签名分组。builder 与 dashboard 共用。"""
from __future__ import annotations

from ..models.loss import Sample


def signature(sample: Sample) -> str:
    return ",".join(f"{k}={'1' if v else '0'}" for k, v in sorted(sample.features.items())
                    if isinstance(v, bool))


def cluster_samples(samples: list[Sample]) -> dict[str, list[Sample]]:
    """返回 签名→样本列表。真实实现可换 embedding 聚类，接口不变。"""
    groups: dict[str, list[Sample]] = {}
    for s in samples:
        groups.setdefault(signature(s), []).append(s)
    return groups
