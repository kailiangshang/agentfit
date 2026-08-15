---
name: s1-task-compile
version: 0.1.0
layer: L3
owner_agent: BusinessEngineer
schema: agentfit.samplesetmanifest/v1
seed: R4 improvised compute_hashes.py (2026-08-15, retail-home-r4)
---

# S1 任务编译 Skill（task-compile）

## 用途

把脱敏源批次编译为结构化样本合同：四份 SampleSetManifest（adaptation / validation / sealed_holdout / stress_and_failure）的成员分配、内容哈希与集合哈希。所有哈希**从供给批次计算，绝不发明**。

## 触发条件

Discover / Freeze 阶段：BusinessEngineer 接到语义编译或 manifest 实例化任务时调用本 Skill 的脚本，不现场手写哈希逻辑。

## IO 契约

- 输入：`samples.json`（prepare_projectcase 产出的脱敏批次，含每样本 `source_record_sha256`）+ 成员分配方案（实体分组感知：同一实体组不得跨 manifest）
- 输出：`sample-set-manifests.json`（符合 `schema/sample-set-manifest.schema.json`；集合哈希由 `compute_set_hashes.py` 计算）
- 约束：不可分配成员保持字面 `not_instantiated` 并写明理由；集合哈希算法固定（成员哈希按 sample_id 升序拼接后 SHA-256），变更即新版本

## 脚本

- `compute_set_hashes.py --batch samples.json --members adaptation=0,20,45 ...`：确定性计算各 manifest 的 `set_model_sha256`，输出 JSON

## 失败处理

批次 schema 漂移、成员引用不存在、实体组跨 split → 立即报错退出，输出 `not_instantiated` 加原因，不得猜测补齐。

## 权限与安全

只读消费供给批次；不接触评测答案与 holdout 内容；输出不含任何凭据。

## 复用价值

哈希口径全场景唯一；Skill 版本化，调用记录进 Trace（输入哈希/版本/输出哈希）。
