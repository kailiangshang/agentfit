"""冻结策略：一等公民定义 + 按层默认 + 用户可覆盖。

设计定稿（架构正本）：
- L1 原子（基础设施事实）→ 默认冻结（训练不能凭空造接口）
- L2 能力封装（设计决策）→ 默认可训练（除合规门禁可显式冻结）
- L3 知识（主要训练目标）→ 默认可训练
- L4 拓扑（证据驱动演化）→ 默认可训练

策略测试（tests/test_freeze_policy.py）锁定这些默认值，
防止实现层面的"顺手一设"再次偏离设计意图。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerFreezePolicy:
    """每层的冻结默认策略（一等配置，不是散落的布尔值）。"""
    layer: str
    default_frozen: bool
    user_overridable: bool
    rationale: str


DEFAULT_FREEZE_POLICIES: dict[str, LayerFreezePolicy] = {
    "L1": LayerFreezePolicy(
        layer="L1",
        default_frozen=True,
        user_overridable=True,
        rationale="基础设施事实（API/数据库确实存在），训练不能凭空造接口",
    ),
    "L2": LayerFreezePolicy(
        layer="L2",
        default_frozen=False,
        user_overridable=True,
        rationale="安全封装是设计决策（组合方式/前置条件/门禁阈值），训练应可优化；"
                  "仅合规门禁可通过 bundle 显式 frozen=true 冻结",
    ),
    "L3": LayerFreezePolicy(
        layer="L3",
        default_frozen=False,
        user_overridable=True,
        rationale="主要训练目标（路由规则/排查链/阈值/经验），必须可训练",
    ),
    "L4": LayerFreezePolicy(
        layer="L4",
        default_frozen=False,
        user_overridable=True,
        rationale="拓扑由失败证据驱动演化（Simple First 起步），必须可训练",
    ),
}


def freeze_default(layer: str) -> bool:
    """获取某层的默认冻结值。"""
    policy = DEFAULT_FREEZE_POLICIES.get(layer)
    if policy is None:
        raise ValueError(f"未知层 {layer}，冻结策略只覆盖 L1-L4")
    return policy.default_frozen


def resolve_frozen(layer: str, user_value: bool | None = None) -> bool:
    """合并层默认值与用户显式声明。"""
    policy = DEFAULT_FREEZE_POLICIES[layer]
    if user_value is not None:
        if not policy.user_overridable:
            raise ValueError(f"层 {layer} 的冻结策略不可被用户覆盖")
        return user_value
    return policy.default_frozen
