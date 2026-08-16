"""损失聚合（S2 内核）：按 层×失败模式×元素 统计，识别瓶颈层。"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..models.loss import LossTrace

BOTTLENECK_RATIO = 0.60


@dataclass
class AggregatedLoss:
    patterns: dict[tuple[str, str, str], list[str]] = field(default_factory=dict)  # (层,模式,元素)→样本ID
    layer_share: dict[str, float] = field(default_factory=dict)
    bottleneck_layer: str | None = None
    total: int = 0


def aggregate(loss_traces: list[LossTrace]) -> AggregatedLoss:
    agg = AggregatedLoss(total=len(loss_traces))
    if not loss_traces:
        return agg
    counter: Counter = Counter()
    for lt in loss_traces:
        key = (lt.root_cause_layer, lt.failure_mode, lt.root_cause_element)
        agg.patterns.setdefault(key, []).append(lt.sample_id)
        counter[lt.root_cause_layer] += 1
    agg.layer_share = {layer: n / len(loss_traces) for layer, n in counter.items()}
    agg.bottleneck_layer = max(agg.layer_share, key=agg.layer_share.get) \
        if any(v > BOTTLENECK_RATIO for v in agg.layer_share.values()) else None
    return agg
