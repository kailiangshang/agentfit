---
name: s5-independent-audit
version: 0.1.0
layer: L3
owner_agent: GovernanceAuditor
seed: R4 improvised verify_hashes.py (2026-08-15, retail-home-r4)
---

# S5 独立审计 Skill（independent-audit）

## 用途

对已实例化的 SampleSetManifest 做独立机器复核：集合哈希重算、成员查重、覆盖核对、实体泄漏检查。审计独立于生产者——本 Skill 的输出是审计记录，不是修复。

## 触发条件

Audit 阶段或 Freeze 前：GovernanceAuditor 接到依赖序审查任务时调用本 Skill 脚本；不得引用生产者（BusinessEngineer）的计算脚本作为审计依据，只共享同一哈希口径定义。

## IO 契约

- 输入：`samples.json`（供给批次）+ `sample-set-manifests.json`（待审 manifest，符合 S1 schema）+ 可选 `entity-groups.json`（实体分组）
- 输出：机器字段结论（`checks` 数组 + `verdict`），GA 的 `audit-decision.json` 必须逐字引用 verdict 字段
- 检查项：① 每份 manifest 集合哈希独立重算一致 ② 无样本跨 manifest 重复 ③ 成员均存在于批次 ④ （若供实体分组）无实体组跨 split

## 脚本

- `verify_manifests.py --batch samples.json --manifests sample-set-manifests.json [--entity-groups entity-groups.json]`

## 失败处理

任何一项检查失败 → `verdict: FAIL` 带明细；输入 schema 不符 → `verdict: INVALID_INPUT`。不猜测、不降级为警告。

## 权限与安全

只读；sealed holdout 相关输入仅在候选冻结后按权限解析（本 Skill v0.1 不含 holdout 解析）。

## 复用价值

哈希口径与 S1 共享同一常量定义但实现独立（双实现防同源错误）；审计结论可追溯至输入哈希。
