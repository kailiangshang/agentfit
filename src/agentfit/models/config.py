"""训练配置：预算、批次、收敛、λ、人审策略。"""
from __future__ import annotations

from dataclasses import dataclass, field
from ..gates.human import (BlockingHumanGate, GateType, HumanGatePolicy,
                           ReviewDecision, ReviewRequest)


class AutoApprove:
    """测试用：全部批准（人审槽位的 mock，不代表生产行为）。"""

    def __init__(self, delivery_conditions: tuple[str, ...] = ()):
        self.delivery_conditions = tuple(delivery_conditions)

    def review(self, request: ReviewRequest) -> ReviewDecision:
        conditions = self.delivery_conditions if request.gate == GateType.G3 else ()
        return ReviewDecision(True, "explicit test approval", "test-policy", conditions)

    def review_updates(self, proposals: list) -> bool:
        return self.review(ReviewRequest(GateType.G1, "updates", {"count": len(proposals)})).approved


@dataclass
class TrainingConfig:
    batch_size: int = 50
    max_epochs: int = 5
    convergence_window: int = 3            # 连续 N 轮提升 < min_improvement 判收敛
    min_improvement: float = 0.02
    regression_min_pass: float = 1.0       # 回归池遗忘率必须 0（骨架铁律：必须 100%）
    budget_usd: float = 10.0               # 超支熔断
    attribution_confidence_floor: float = 0.6   # 低于此值升级人审
    lambda_level1_step: float = 0.2        # Level 1 自动调节上限 ±20%
    lambda_level1_cap: float = 0.5         # 累计变化上限 ±50%
    lambda_consecutive_rounds: int = 2     # 连续 N 轮超阈值触发 Level 1
    review_policy: HumanGatePolicy = field(default_factory=BlockingHumanGate)
