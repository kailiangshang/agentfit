# Skill S1 设计演练总结

> 状态：设计演练，非运行证据。人工模拟 BusinessEngineer，用 τ³-bench retail task 0 的真实数据走了一遍 Skill S1（Sample 与任务编译）。
>
> 演练时间：2026-08-13
>
> 环境：无 API key、无 AgentTeams、无真实模型调用。纯人工基于 source 数据编译。

## 演练了什么

把 τ³-bench v1.0.1 retail task 0（用户换货场景）用 AgentFit 的 S1 契约结构编译成两份草案：

1. [`01-sample-semantic-spec.json`](01-sample-semantic-spec.json) — 定义这个场景里"什么是一个 Sample"
2. [`02-task-semantic-spec.json`](02-task-semantic-spec.json) — 定义"优化什么、什么算解决"

两份草案均标注 `evidence_role: design-mockup`。

## 验证结论：S1 契约结构可落地

SampleSemanticSpec 的 15 个字段 **全部能从 task 0 + policy.md 编译**。S1 的契约结构对这个场景可落地，不需要新增字段就能表达：

| 契约字段 | task 0 编译来源 | 编译难度 |
|---|---|---|
| sample_type | customer_service_dialogue | 直觉 |
| sample_level | episode_level（一个完整对话） | 直觉 |
| unit_description | task id = 一个对话 | 直觉 |
| temporal_boundary | 从首条消息到对话结束 | 需思考，但 policy 给了明确边界 |
| grouping_rule | 一个 task id = 一个 Sample | τ³-bench 原生结构 |
| identity_rule | tau2-retail-{task_id} | τ³-bench 原生结构 |
| label_or_oracle | tau2-bench native evaluator | 需理解 evaluator 机制 |
| replay_contract | mock server + 模型 + seed | **需额外记录**（见下） |
| metric_applicability | per_sample vs cross_sample | 需区分 |
| sensitivity_policy | PII 标注 | mock 数据但仍需标注 |

**结论：S1 的契约设计是扎实的，不是纸面空谈。**

## 发现的设计缺口（演练的真正价值）

### 缺口 1：replay_contract 缺少 env_snapshot_ref

task 0 的 `initial_state = null`——初始状态（用户数据、订单、产品）不在 task.json 里，而是 τ³-bench mock server 运行时注入。

**影响**：SampleSemanticSpec 的 `replay_contract` 只记录模型和 seed 不够，必须记录 mock server 版本和配置。当前 Schema 有 `env_snapshot_ref` 字段，但 task.json 不包含快照。

**建议**：SampleSemanticSpec 补充 `replay_contract.runtime_version`（mock server commit）和 `replay_contract.config_ref`（τ³-bench 运行参数）。

### 缺口 2：nl_assertions = null 但 reward_basis 含 NL_ASSERTION

task 0 的 `evaluation_criteria.nl_assertions = null`，但 `reward_basis = ["DB", "NL_ASSERTION"]`。

**影响**：不确定 evaluator 如何处理 null nl_assertions——是忽略还是计为 0 分。

**建议**：在正式 preflight 前确认 τ³-bench evaluator 的行为；TaskSemanticSpec 的 metrics 需要标注"nl_assertions 可选"。

### 缺口 3：最小步数与预算约束

policy.md 规定"at most one tool call at a time"，task 0 有 5 个期望 action。这意味着**一个成功 episode 至少 5 个 Step**。

**影响**：预算约束（token/calls）的下限由任务结构决定，不是任意设的。TrialSpec 冻结预算时必须考虑最小步数。

**建议**：Skill S4（统一试验）的 TrialSpec 模板加 `min_steps_inferred_from_task` 字段。

### 缺口 4：公开 test split 不是 sealed holdout

τ³-bench 的 test split (40 tasks) 是公开的。任何人都能查到期望答案。

**影响**：不能把 test split 当 sealed holdout 用。四份正式 SampleSetManifest 不能直接从 train/test 切分来。

**建议**：如果 retail 场景要成为正式 ProjectCase，必须设计独立的数据划分策略——比如从 114 个 task 里自定义 adaptation/validation/holdout，而不是用官方 train/test。但这又引出"官方 test 里的 task 可能被候选生成上下文见过"的泄漏风险。

**这是零售场景作为首个 ProjectCase 的最大障碍。**

## 对 Skill 架构设计的启示

### S1 可细化方向

1. **输入校验器**：S1 应该有前置校验，检查 source 数据是否满足编译条件（如 initial_state 是否可重放）
2. **Oracle 隔离器**：编译 SampleSemanticSpec 时，自动把 evaluation_criteria 标为 sealed，防止后续 Skill 意外读取
3. **重放依赖记录器**：自动记录 mock server 版本、模型版本、seed，生成 replay manifest

### S2（能力对齐）演练方向

下一步可以基于 task 0 演练 S2——盘点 retail 场景需要哪些能力，生成 AlignmentReport：
- 身份验证能力（find_user_*）
- 订单查询能力（get_order_details）
- 产品查询能力（get_product_details）
- 换货执行能力（exchange_delivered_order_items）
- 用户沟通能力（确认、解释、拒绝）
- 策略遵守能力（不编造、不越权）

每个能力可以分析 C0/C1/C2/C3 候选如何组合这些能力。

## 下一步建议

1. **先解决缺口 4**（数据划分），它决定了 retail 场景能否成为正式 ProjectCase
2. **演练 S2**（能力对齐），进一步验证 Skill 架构
3. **演练 C0/C1/C2 候选设计**，对 task 0 画出四类候选的能力图 G
4. 有 API key 后，跑 §7 preflight，验证 mock server 工具链
