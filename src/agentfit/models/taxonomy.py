"""层级类型学：核心闭集（系统级）+ Case 注册制扩展（Intake 制）。

语义（设计定稿）：
- Core 类型学是闭集，变更走正本评审；所有系统机制（验证器规则、语义兜底、
  正则分组）只依赖 core。
- 用户扩展在 Intake 时注册、G0 冻结，作用域为本次 ProjectCase：
  必须挂靠 core 超类 + 提供语义描述（label/description，语义双轨的原料）。
- 自定义类型按超类参与系统规则；语义呈现优先用用户自己的描述。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---- L1 能力域（core 闭集）：原子对准什么基础设施 ----
CORE_L1_DOMAINS = {
    "data_interface": "数据接口",
    "knowledge_interface": "知识库接口",
    "external_system": "外部系统接口",
    "human_review": "人工审核",
    "notification": "通知",
}
# ---- L1 读写语义（core 闭集） ----
CORE_L1_ACCESS = {
    "read": "只读",
    "write": "写入",
    "human": "人工",
    "notify": "通知",
}
# ---- L2 封装类型（core 闭集） ----
CORE_L2_CAPABILITY_TYPES = {
    "safe_wrapper": "安全包装",
    "composite": "组合能力",
    "caliber": "口径封装",
    "review_routing": "送审路由",
}
# ---- L3 知识类型（core 闭集，模型既有五类） ----
CORE_L3_KNOWLEDGE_TYPES = {
    "skill": "操作模板",
    "routing_rule": "路由规则",
    "chain": "排查链",
    "threshold": "决策阈值",
    "experience": "经验记录",
}
# ---- L4 Agent 角色（core 默认集） ----
CORE_L4_ROLES = {
    "single": "单 Agent",
    "diagnostic": "诊断",
    "repair": "修复",
    "orchestrate": "编排",
}
# ---- L4 触发方式（core 闭集） ----
CORE_L4_TRIGGER_MODES = {"passive", "proactive", "scheduled", "event"}


@dataclass(frozen=True)
class CustomType:
    """Case 级注册的自定义类型：挂靠 core 超类 + 用户语义描述。"""
    name: str
    layer: str                  # "L1_domain" | "L2_capability" | "L4_role"
    parent: str                 # 必须是同层 core 值
    label: str                  # 用户语义名（语义双轨原料）
    description: str = ""


@dataclass
class TypeRegistry:
    """一次 ProjectCase 的类型学注册表：core 全集 + 用户挑选/扩展，G0 冻结。"""
    customs: list[CustomType] = field(default_factory=list)
    # 用户挑选的适用子集（空 = 全选 core）
    selected_l1_domains: set[str] = field(default_factory=set)
    selected_l2_capability_types: set[str] = field(default_factory=set)

    # ---- 校验 ----
    def validate(self) -> list[str]:
        errors: list[str] = []
        core_by_layer = {"L1_domain": CORE_L1_DOMAINS, "L2_capability": CORE_L2_CAPABILITY_TYPES,
                         "L4_role": CORE_L4_ROLES}
        seen: set[str] = set()
        for custom in self.customs:
            if custom.name in seen:
                errors.append(f"自定义类型重名: {custom.name}")
            seen.add(custom.name)
            core = core_by_layer.get(custom.layer)
            if core is None:
                errors.append(f"自定义类型 {custom.name} 的 layer 非法: {custom.layer}")
            elif custom.parent not in core:
                errors.append(f"自定义类型 {custom.name} 必须挂靠 core 超类，实际 {custom.parent}")
            if not custom.label.strip():
                errors.append(f"自定义类型 {custom.name} 缺少语义名 label（语义双轨的原料）")
        for domain in self.selected_l1_domains:
            if domain not in CORE_L1_DOMAINS and domain not in seen:
                errors.append(f"L1 域不在 core 且未注册: {domain}")
        for ctype in self.selected_l2_capability_types:
            if ctype not in CORE_L2_CAPABILITY_TYPES and ctype not in seen:
                errors.append(f"L2 封装类型不在 core 且未注册: {ctype}")
        return errors

    # ---- 值域 ----
    def l1_domains(self) -> set[str]:
        return set(CORE_L1_DOMAINS) | {c.name for c in self.customs if c.layer == "L1_domain"}

    def l2_capability_types(self) -> set[str]:
        return set(CORE_L2_CAPABILITY_TYPES) | {c.name for c in self.customs if c.layer == "L2_capability"}

    def l3_knowledge_types(self) -> set[str]:
        return set(CORE_L3_KNOWLEDGE_TYPES)

    def l4_roles(self) -> set[str]:
        return set(CORE_L4_ROLES) | {c.name for c in self.customs if c.layer == "L4_role"}

    def custom(self, name: str) -> CustomType | None:
        return next((c for c in self.customs if c.name == name), None)

    # ---- 语义映射（core 用内置表，自定义用用户描述） ----
    def semantic_l1_domain(self, domain: str) -> str:
        custom = self.custom(domain)
        if custom:
            return custom.label
        return CORE_L1_DOMAINS.get(domain, domain)

    def semantic_l2_type(self, ctype: str) -> str:
        custom = self.custom(ctype)
        if custom:
            return custom.label
        return CORE_L2_CAPABILITY_TYPES.get(ctype, ctype)

    def semantic_l3_type(self, ktype: str) -> str:
        return CORE_L3_KNOWLEDGE_TYPES.get(ktype, ktype)

    def semantic_l4_role(self, role: str) -> str:
        custom = self.custom(role)
        if custom:
            return custom.label
        return CORE_L4_ROLES.get(role, role)


DEFAULT_REGISTRY = TypeRegistry()


def registry_from_dict(data: dict) -> TypeRegistry:
    """从材料 bundle 的 taxonomy 节恢复注册表。"""
    registry = TypeRegistry(
        customs=[CustomType(**item) for item in data.get("customs", [])],
        selected_l1_domains=set(data.get("selected_l1_domains", [])),
        selected_l2_capability_types=set(data.get("selected_l2_capability_types", [])),
    )
    errors = registry.validate()
    if errors:
        raise ValueError("taxonomy 注册表非法: " + "; ".join(errors))
    return registry
