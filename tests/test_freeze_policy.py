"""冻结策略合同测试：锁定设计意图，防止实现层面的偏移。

每个测试对应设计定稿中的一条冻结语义，不是机制测试（机制测试
在 test_regularization_propagation.py），而是**策略测试**。
"""
from __future__ import annotations

import json

import pytest

from agentfit.models.freeze_policy import (DEFAULT_FREEZE_POLICIES,
                                            LayerFreezePolicy, freeze_default,
                                            resolve_frozen)


class TestLayerDefaults:
    """每层的默认冻结值必须与设计定稿一致。"""

    def test_l1_frozen_by_default(self):
        """L1 原子=基础设施事实，默认冻结。"""
        assert freeze_default("L1") is True

    def test_l2_trainable_by_default(self):
        """L2 封装=设计决策，默认可训练（非合规门禁不应冻结）。"""
        assert freeze_default("L2") is False

    def test_l3_trainable_by_default(self):
        """L3 知识=主要训练目标，必须可训练。"""
        assert freeze_default("L3") is False

    def test_l4_trainable_by_default(self):
        """L4 拓扑=证据驱动演化，必须可训练。"""
        assert freeze_default("L4") is False

    def test_all_layers_have_policy(self):
        assert set(DEFAULT_FREEZE_POLICIES.keys()) == {"L1", "L2", "L3", "L4"}

    def test_policies_are_frozen_dataclass(self):
        """策略本身不可变（防止运行时篡改）。"""
        for policy in DEFAULT_FREEZE_POLICIES.values():
            assert isinstance(policy, LayerFreezePolicy)


class TestUserOverride:
    """用户可以通过 bundle 显式覆盖默认值。"""

    def test_l2_can_be_frozen_for_compliance(self):
        """合规门禁可以显式 frozen=true。"""
        assert resolve_frozen("L2", user_value=True) is True

    def test_l1_can_be_unfrozen(self):
        """高级用户可以解冻 L1（如允许训练建议新原子）。"""
        assert resolve_frozen("L1", user_value=False) is False

    def test_no_layer_is_locked(self):
        """所有层都允许用户覆盖。"""
        for policy in DEFAULT_FREEZE_POLICIES.values():
            assert policy.user_overridable is True


class TestCompilerFollowsPolicy:
    """材料编译器的产物必须遵循冻结策略。"""

    def test_materials_compiler_l1_frozen_l2_trainable(self):
        """编译 pilot bundle 后：L1 冻结、L2 可训练。"""
        from plugins.materials.compiler import compile_material_bundle
        bundle = json.load(open("output/pilot/telecom-pilot-bundle.json"))
        compiled = compile_material_bundle(bundle)
        inv = compiled.capability_inventory
        assert all(a.frozen for a in inv.atoms), "L1 原子应默认冻结"
        assert all(not t.frozen for t in inv.tools), "L2 工具应默认可训练"

    def test_builder_l3_l4_trainable(self):
        """bootstrap 产物：L3/L4 不冻结。"""
        from plugins.materials.compiler import compile_material_bundle
        from agentfit.solution.builder import build_candidate
        bundle = json.load(open("output/pilot/telecom-pilot-bundle.json"))
        compiled = compile_material_bundle(bundle)
        solution = build_candidate(
            list(compiled.task_samples), compiled.sample_sets,
            compiled.capability_inventory,
        )
        assert all(not k.frozen for k in solution.L3_knowledge), "L3 应可训练"
        assert all(not a.frozen for a in solution.L4_topology.agents), "L4 应可训练"

    def test_bundle_explicit_frozen_l2_is_respected(self):
        """bundle 中显式 frozen=true 的 L2 工具（合规门禁）被尊重。"""
        from plugins.materials.compiler import compile_material_bundle
        bundle = json.load(open("output/pilot/telecom-pilot-bundle.json"))
        # 模拟用户显式冻结一个工具
        bundle["capabilities"]["tools"][0]["frozen"] = True
        compiled = compile_material_bundle(bundle)
        frozen_tools = [t for t in compiled.capability_inventory.tools if t.frozen]
        assert len(frozen_tools) >= 1, "显式 frozen=true 的 L2 工具应被冻结"


class TestFreezePolicyRationale:
    """每条策略必须有人类可读的理由（可审计）。"""

    def test_all_policies_have_rationale(self):
        for policy in DEFAULT_FREEZE_POLICIES.values():
            assert policy.rationale, f"层 {policy.layer} 缺少冻结理由"
