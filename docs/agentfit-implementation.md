# AgentFit 落地设计：真实实现架构

> 基于四层骨架 v3（定稿），设计 AgentFit 的真实实现。回答"哪些 Agent 在协同、各持什么 Skill、怎么交互、任务怎么分发、代码怎么写"。
>
> **核心设计原则：AgentFit 自己也是一副四层方案。** 训练系统的内部结构必须遵守它强加给被训练方案的同一套纪律（纵向逐层、横向禁互调、存在依赖）。它训练别人的方法，就是它自己运行的方法。

---

## 〇、双层视角：先分清"训练者"和"被训练者"

AgentFit 体系里存在**两副四层方案**，混淆它们是设计错误：

```
┌──────────────────────────────────────────────────────────────┐
│  元层（训练者）：AgentFit 内部                                  │
│  L4 = 五个内部 Agent + 一个人审门禁（本文 §一）                  │
│  L3 = 七个训练 Skill（归因/聚合/建议/验证/回归/λ/审计，本文 §二）  │
│  L2 = safe_llm_call / safe_code_run / safe_retrieval / 送审路由 │
│  L1 = LLM API / 沙箱执行 / 向量库 / 文件系统 / human_review 原子  │
├──────────────────────────────────────────────────────────────┤
│  对象层（被训练者）：用户场景方案（如 telecom 客服）               │
│  L4 = 被训练出的 Agent 拓扑（单/多 Agent，由训练证据决定）         │
│  L3 = 被训练出的路由规则/排查链/阈值/经验                         │
│  L2 = 被训练出的 safe_* 工具封装                                 │
│  L1 = 场景基础设施（telecom API / 数据库 / 人工坐席）             │
└──────────────────────────────────────────────────────────────┘
```

| | 元层（AgentFit 内部） | 对象层（被训练方案） |
|---|---|---|
| 是什么 | 固定的训练机器 | 可变的训练产物 |
| 谁改它 | 只有人（代码级演进） | 训练循环（ChangeTransaction） |
| 拓扑 | 5 Agent + 1 人审，固定 | 从单 Agent 起步，证据驱动演化 |
| 优化目标 | 稳定、可审计地执行训练循环 | 在样本上拟合，收敛可交付 |

本文 §一~§五 定义元层；§六~§九 定义对象层的支撑结构与算法；§十 文件结构把两层落位。

---

## 一、元层 L4：内部 Agent 拓扑（明确的 Agent）

### Agent 清单（5 个 AI Agent + 1 个人审门禁）

| Agent | 职责（它有权决定什么） | 持有的 Skill（§二） | 不许做什么（权限边界） |
|---|---|---|---|
| **Steward 交互官** | 用户唯一对话出口：材料理解与操作化；澄清对话；解释呈现（G1/G2/G3/交付/追溯） | intake_skill, clarify_skill, explain_skill | 不替用户决策、不替架构师改方案——翻译官不是决策者 |
| **Orchestrator 编排者** | 持有训练循环；任务分发；预算与熔断；收敛判定；λ Level 1 自动调节 | train_loop_skill, lambda_skill | 不亲自归因/不亲自改方案——只分发和裁决 |
| **Attributor 归因师**（可多实例） | 对单个失败样本产出 LossTrace；置信度自评 | attribution_skill | 不提更新建议——归因止于根因，改什么是架构师的事 |
| **Architect 架构师** | 初始方案归纳构建；聚合损失模式；生成分层更新建议；级联存在依赖检查；漂移/震荡分析 | bootstrap_skill, aggregation_skill, proposal_skill, cascade_skill | 不绕过验证直接落盘——建议必须经 Validator |
| **Validator 验证官** | 存在依赖验证；结构性正则计算；回归验证执行；COMMIT/ROLLBACK 裁决 | validation_skill, regression_skill | 不修改方案——只有否决权和通过权 |
| **Auditor 审计官** | 哈希链日志追加；成本/预算监控；漂移检测；异常告警 | audit_skill | 不参与任何决策——只记录和告警（中立性） |
| **Human Gate 人审门禁**（非 AI） | 三类硬门禁的批准/拒绝（见 §四） | — | — |

### 确定性边界（实现方式的裁决：角色 ≠ LLM Agent）

**推导**（为什么这不是偷懒而是对的）：

1. 九步循环中真正需要认知推理的只有两处：歧义轨迹的归因消解（复合根因、反事实判断）与更新建议生成。验证=图/集合运算、正则=算术、回归=重放比对、日志=哈希、λ Level 1=算术、收敛=算术——确定性工作必须用确定性代码。
2. 安全关键裁决必须可复现：裁决 COMMIT 的验证官若是概率性 LLM，"禁止部分成功"退化为"大概率没部分成功"，哈希链的审计价值被上游不确定性抵消。
3. 成本纪律：$0.006/样本是卖点。训练系统自身在确定性步骤上烧 LLM token 会摧毁单位经济性；元层 LLM 用量限定在标记槽位并逐次计量。
4. 骨架自律：Simple First + Agent 数量需要证据。**训练循环内部的推导只支持 2 个认知 Agent；把推导范围扩大到全链路（用户提交材料→交付，见下表）后暴露用户侧认知缺口，演化到 3 个**——这本身就是"证据驱动复杂化"的第一次执行：先最简，出现缺口证据才加角色，后续继续有证据再演化（元层 L4 也是被训练对象）。

| 角色 | 实现方式 | LLM 使用 |
|---|---|---|
| Steward | LLM 为中心（对话+操作化） | 材料理解、澄清、解释——全部版本化+计量 |
| Orchestrator | 确定性控制器（路由表 + 状态机） | 无 |
| Attributor | 机械层走查优先，LLM 只进歧义槽位 | 仅复合根因/反事实不定时；带置信度，<0.6 升级人审 |
| Architect | LLM 为主（模板约束）+ 确定性级联展开 | 初始归纳+建议生成，逐次计量 |
| Validator | **纯确定性代码**（安全关键） | 无 |
| Auditor | **纯确定性代码**（中立性） | 无 |

对外这句话依然成立且更强：**AgentFit 自身就是多 Agent 协同**——三个认知 Agent + 三个确定性官员 + 一个人审门禁，全部消息走总线、带因果链；而"验证官与审计官是纯代码"正是"可审计"的机制级保证，不是口号。

### 拓扑边（唯一的合法 Agent 间通道）

```
┌────────┐ 材料/样本/评价/澄清对话 ┌──────────┐
│  用户   │◄────解释/呈现/提问────►│ Steward   │
└───┬────┘                        │ 交互官    │
    │ G1/G2/G3 批准/拒绝            └────┬─────┘
    ▼                                  │ (经L2送审路由)
┌──────────────┐                       │
│ Human Gate   │◄──────────────────────┤
└──────────────┘                       ▼
        ┌────────────────────┐   ┌───────────────┐
        │     消息总线         │◄──│ Orchestrator  │
        └──┬─────┬─────┬────┬─┘   │ 编排者(确定性) │
           │     │     │    │     └───────────────┘
           ▼     ▼     ▼    ▼
      Attributor Architect Validator Auditor
        归因师     架构师     验证官     审计官
           │
           └── execute ──► 执行适配器(L1级基础设施，非Agent，见§六)
```

**边规则（对应骨架横向约束的 L4 例外）**：
- Agent 间**运行时禁止直呼**——一切消息经总线，由 Orchestrator 按路由表转发（§三）
- 拓扑边是声明式的：`Attributor→Architect`（归因结果流向）、`Architect→Validator`（建议送验）、`Validator→Orchestrator`（裁决回流）、`*→Auditor`（证据写入，唯一广播边）
- 每条边有明确的 payload 类型，不许夹带私货（消息 schema 见 §三）

### 为什么是 6 个：全链路场景推演的证据（不是拍脑袋）

对齐骨架自身的 L4 正则（Agent 数量 > 5 需要证据）。证据来自**从用户提交材料到最终交付的全链路推演**——训练循环内部 2 个认知 Agent 足够，但两端暴露出用户侧认知缺口：

| 真实情况 | 处理者 | 若无此角色 |
|---|---|---|
| 最简输入：只有样本+评价，要反推 L1/归纳初始知识 | Architect（bootstrap_skill） | 初始方案无法构建 |
| 样本矛盾/格式乱/评价模糊（"处理得好"） | **Steward**（操作化为 evaluator） | 评价函数无法执行 |
| 样本太少（如 8 个）不能训练 | **Steward**（充分性判定+扩增建议/拒绝） | 带病训练 |
| 用户需要澄清对话、中途改需求 | **Steward**（clarify_skill + 差异理解） | 无对话能力 |
| G1 人审时用户问"为什么/有无别的方案" | **Steward** 呈现 + Architect 供解释 | 门禁退化成按钮 |
| 预算将尽未收敛，需要与用户谈权衡 | **Steward**（呈现 Orchestrator 的确定性告警+选项） | 只会熔断不会沟通 |
| 追溯查询"这个样本为何归因 L3" | 检索确定性 + **Steward** 解释 | 可追溯不可读 |
| 漂移告警后的分析报告 | Auditor 检测 + Architect 分析 + **Steward** 呈现 | 只有告警没有洞察 |
| 训练震荡/不收敛的诊断 | Auditor 告警 + Architect 元层分析，严重则人审 | 无法自诊 |

**裁决：3 个 LLM 认知 Agent（Steward/Attributor/Architect）+ 3 个确定性官员（Orchestrator/Validator/Auditor）+ 1 个人审门禁。** Steward 是单一用户接口（对话上下文一致性），但它是翻译官不是决策者——决策权仍在架构师提案、验证官裁决、人审批准。数据工程、执行适配器**不是 Agent**——没有决策权，是 L1/L2 级共享能力（不是有代码模块就叫 Agent，有独立决策体才叫）。

---

## 二、元层 L3：十一个 Skill（明确的 Skill）

每个 Skill 是 L3 的操作序列模板：**可版本化、可被训练更新**（AgentFit 优化自身 = 优化这些 Skill 的步骤与参数，这就是"skill 是优化目标"的落点）。存储格式见 §十。

### S0a · intake_skill（持有者：Steward）——材料理解与操作化

```
输入: 用户原始材料（任意形态：文档/表格/对话记录）
步骤:
  1. 识别材料类型: 工具清单? 审核规则? 领域知识? 样本? 评价方式?
  2. 已提供项 → 结构化后直接映射到对应层（骨架 §六映射表）
  3. 未提供项 → 标记为"待构建"，交给 bootstrap
  4. 评价方式操作化: 模糊表述("处理得好") → 可执行 evaluator
     (能对一次执行输出 PASS/FAIL 的判定程序或判定标准)
  5. 样本充分性判定: 数量/覆盖面/标注质量 → 能否训练
     不足 → 生成扩增建议或明确拒绝(附理由)
  6. 一致性检查: 材料内部矛盾 → 生成澄清问题清单(交 clarify)
输出: StructuredIntake(可映射项 + 待构建项 + evaluator + 澄清清单)
```

### S0b · clarify_skill（持有者：Steward）——澄清对话

```
输入: 澄清清单 + 用户
步骤:
  1. 生成最小必要问题集(一次不超过 3 问, 按阻塞程度排序)
  2. 理解用户回答 → 增量更新结构化理解
  3. 新回答引入新矛盾 → 回到 intake 一致性检查
  4. 3 轮无进展 → 升级 G1 附带人审
  5. 会话记忆沉淀为元层 L3 经验记录(不是独立记忆系统)
输出: 更新后的 StructuredIntake
```

### S0c · explain_skill（持有者：Steward）——解释与呈现

```
输入: 解释请求(为何改/为何归因L3/边界为何如此/λ为何调) + 证据引用
步骤:
  1. 从对应角色拉取证据(建议/归因/日志的 ref, 不重新推理)
  2. 按用户角色选择呈现粒度(决策者看权衡, 工程师看细节)
  3. 呈现 + 标注证据出处(哪个 epoch 哪条 LossTrace)
约束: 只解释不辩护——用户否决后不争论, 执行否决并沉淀理由
输出: 呈现内容(文本/表格/图)
```

### S1 · attribution_skill（持有者：Attributor）

```
输入: 失败样本 + 执行轨迹 + 期望结果 + 当前方案快照
执行策略: 步骤 1-5 为确定性代码；仅步骤 6 在机械验证无法判定时进入 LLM 槽位（版本化+置信度+计量）
步骤:
  1. 解析轨迹为步骤序列，标注每步的层归属(L1-L4)与下游消费者
  2. L1 检查: 期望动作所需原子是否存在？
     缺 → 进入因果性验证；不缺 → 上移
  3. L2 检查: 已执行步骤中封装是否有错？
     有错 → 判断是否在关键路径(有下游消费者且输出影响结果)
     在 → 候选根因；不在 → 记附带问题，上移
  4. L3 检查: 实际路径 vs 期望路径
     无覆盖链路 / 走错分支 → 候选根因
  5. L4 检查: 样本复杂度 vs 当前拓扑适配性
  6. 因果性验证(反事实): "若该异常修复，样本能通过吗？"
     能 → 确认根因，停止
     不能 → 降级为附带问题，继续上查
  7. 四层皆无异常 → 归因 needs_human 或 eval_error
输出: LossTrace(含根因层/元素/失败模式/置信度/附带问题清单)
版本: 归因策略本身有版本号，写入 LossTrace.evidence（可追溯用了哪版策略）
```

### S1b · bootstrap_skill（持有者：Architect）——初始方案归纳构建

```
输入: StructuredIntake + 样本池
步骤:
  1. 样本聚类(embedding+聚类为确定性步骤), 认知步骤 = 聚类语义复核/命名/合并判断
  2. 从聚类反推 L1 原子清单(用户提供了工具清单则校验合并)
  3. 构建 L2 封装(默认最保守: 所有写操作送审)
  4. 从解决轨迹归纳 L3 初始路由规则与排查链
  5. L4 拓扑 = 单 Agent(Simple First, 无证据不加复杂度)
  6. 全部过 validate_existence_dependencies 后提交用户确认(G1)
输出: 初始 Solution(版本 0)
```

### S2 · aggregation_skill（持有者：Architect）

```
输入: 本轮全部 LossTrace
步骤:
  1. 按根因层 × 失败模式 × 涉及元素 三维统计
  2. 相似失败聚类（同一元素/同一模式合并）
  3. 识别模式: 单点高频 / 长尾分散 / 复合根因
  4. 产出瓶颈层判定（某层占比 > 60% 标记为瓶颈）
输出: AggregatedLoss（模式清单 + 各层占比 + 瓶颈层）
```

### S3 · proposal_skill（持有者：Architect）

```
输入: AggregatedLoss + 当前方案 + 正则约束
步骤:
  1. 模式 → 更新动作映射:
     缺原子(L1) → 提议新增原子（需用户确认基础设施）
     缺封装(L2) → 提议 safe_* 封装
     缺链路/路由错(L3) → 提议新增路由规则或修正分支
     架构不适配(L4) → 提议拓扑变更（必须走 G1 人审）
     needs_human → 不改方案，标记为边界内人工项
  2. 每条建议附: 触发证据(样本ID清单) / 预期影响 / 违反的正则项
  3. 按更新优先级排序（先低层后高层，先高频后低频）
输出: UpdateProposal 列表
```

### S4 · cascade_skill（持有者：Architect）

```
输入: UpdateProposal
步骤:
  1. 检查建议的下游支撑: 目标层声明的能力，下层是否已有？
  2. 断链 → 更新目标下移，补齐下层（自底向上展开成级联计划）
  3. 级联到基础设施仍断 → 升级给用户（G1 附带基础设施确认）
输出: 展开后的原子变更清单（含依赖顺序）
```

### S5 · validation_skill（持有者：Validator）

```
输入: 变更后的方案快照
步骤:
  1. validate_existence_dependencies: L1↔基础设施 / L2→L1 / L3→L2 / L4→L3 全链无悬空
  2. 同层约束: 无执行时互调声明（L3 dispatch 与 invocation 的区分检查）
  3. 结构性正则 7 项计算（原子使用率/稀缺率/封装复杂度/复用率/链长/分支/Agent数）
输出: ValidationError 列表（空 = 通过）+ 结构正则值
```

### S6 · regression_skill（持有者：Validator）

```
输入: 候选方案 + 回归池
步骤:
  1. 从回归池抽样（分层，覆盖历史全部失败模式）
  2. 逐样本 replay
  3. 对比历史结果: 曾通过的现在失败 = 遗忘
  4. 遗忘率 > 0 → 裁决 ROLLBACK；= 0 → 裁决 COMMIT
输出: RegressionResult + 裁决
```

### S7 · lambda_skill + audit_skill（持有者：Orchestrator / Auditor）

```
lambda_skill:
  Level 1: 单 λ ≤±20% 且连续 2 轮触发 → 自动调，记日志
  Level 2: 超限或多 λ → 生成结构化建议进 G2 人审
  约束: 每轮最多 1 个 λ，累计 ≤±50%

audit_skill:
  每个总线消息 → 日志条目（含 task_id 因果链）
  日志条目 → sha256(前条哈希 + 本条内容) 串链
  成本/预算比对 → 超限告警 → 通知 Orchestrator 熔断
  漂移检测（部署后）: 工单分布偏移 > 15% → 建议重训练
```

---

## 三、元层交互协议（明确的交互）

### 消息结构（总线唯一合法格式）

```json
// TaskMsg —— 一切任务的开始
{
  "msg_id": "uuid", "task_id": "epoch3-attr-#42",
  "from": "orchestrator", "to": "attributor",
  "type": "ATTRIBUTE",
  "payload": { "sample_ref": "...", "trace_ref": "...", "solution_version": 5 },
  "context_ref": "epoch3",          // 因果链锚点，全链路可追溯
  "created_at": "...", "deadline": "..."
}

// ResultMsg —— 一切任务的结束
{
  "msg_id": "uuid", "task_id": "epoch3-attr-#42",
  "status": "ok | failed | escalated",
  "output_ref": "losstrace/42.json",
  "evidence": { "skill_version": "attribution@1.3", "confidence": 0.87 },
  "cost": { "tokens": 1832, "usd": 0.003 }
}
```

规则：`context_ref` 串起同一 epoch 的全部消息 → Auditor 可以重建任意决策的完整因果链（可审计的机制保证，不是口号）。所有 payload 走引用（ref）不走值——大对象落盘，消息只传指针。

### 任务路由表（Orchestrator 的 L3 路由规则，明确的任务分发）

| 任务类型 | 路由到 | 并行策略 | 失败/升级处理 |
|---|---|---|---|
| `INTAKE` | Steward | — | 不可操作化 → clarify 循环；3 轮无进展 → G1 附带人审 |
| `CLARIFY` | Steward ↔ 用户 | — | 同上 |
| `BOOTSTRAP` | Architect | — | 失败 → 最简兜底方案 + 告警 |
| `EXPLAIN` | Steward | — | 证据缺失 → 标注"不可解释"而非编造 |
| `EXECUTE_BATCH` | 执行适配器（L1 级） | 批内样本并行 | 重试 1 次 → 标记 executor_fault |
| `ATTRIBUTE` | Attributor ×N 实例 | **按失败样本并行**（扇出） | 置信度 < 0.6 → escalated → G1 附带人审 |
| `AGGREGATE` + `PROPOSE` + `CASCADE` | Architect（单实例串行） | — | 建议生成失败 → 本轮跳过，记日志 |
| `VALIDATE_STRUCT` | Validator | — | 不通过 → 打回 Architect 一次 → 再败放弃本轮 |
| `HUMAN_REVIEW` | Human Gate（经 L2 送审路由） | — | **硬同步点**，不响应 = 不应用（骨架铁律） |
| `APPLY_TRANSACTION` | Orchestrator 自执（无 AI 决策，纯机械） | — | VALIDATE 失败自动 ROLLBACK |
| `REGRESSION` | Validator | 回归样本并行 | 遗忘 > 0 → ROLLBACK + 记录 |
| `LOG_APPEND` | Auditor | 每步异步追加 | 只追加不改写 |

### 一个 Epoch 的交互时序（泳道）

```
Orchestrator   Attributor(×N)   Architect      Validator      Auditor    HumanGate
    │────────EXECUTE_BATCH──────────────────────────────────────►│(适配器)
    │◄──────────────────────────batch traces──────────────────────│
    │──ATTRIBUTE #1..#k──►(扇出并行)
    │◄──LossTrace×k────────┤
    │────AGGREGATE+PROPOSE+CASCADE──────►│
    │◄──UpdateProposals─────┤
    │────(G1: 更新建议人审)─────────────────────────────────────────────►│
    │◄──approved/rejected───────────────────────────────────────────────│
    │──APPLY(机械)─►│────VALIDATE_STRUCT────►│
    │                │◄──pass/fail───────────┤
    │                │────REGRESSION─────────►│
    │                │◄──COMMIT/ROLLBACK──────┤
    │◄─epoch 汇总─────────────────────────────────────►LOG_APPEND─►│
    │(λ Level 1 自动 / Level 2 → G2)
    ▼ 收敛判定 → 下一轮 或 G3 交付确认
```

关键同步点只有三个：G1（每轮更新建议）、G2（Level 2 λ）、G3（交付边界确认）。其余全异步。

---

## 四、人审门禁（Human Gate 的三类硬门禁）

| 门禁 | 触发 | 审什么 | 不响应的默认 |
|---|---|---|---|
| **G1 更新审批** | 每轮有 UpdateProposal 时 | 分层更新建议 + 触发证据 + 预期影响 | 不应用，本轮空转并记日志 |
| **G2 λ 调整** | Level 2（>±20% 或多 λ） | 结构化权衡建议（牺牲什么换什么） | 保持当前值，3 轮内不重提 |
| **G3 交付确认** | 收敛后 | 适用边界 + 五选一交付形态 | 不交付，继续监控 |

触发式额外送审：归因置信度 < 0.6 的样本、拓扑变更提议、预算超限熔断、基础设施缺失升级。

**人审是 L1 原子**（human_review），Orchestrator 经 L2 送审路由触达——元层自己遵守"必须经 L2 使用能力"的铁律。

---

## 五、元层的自举（AgentFit 优化自身）

训练 Skill（§二的 S1-S7）本身就是元层的 L3 知识，因此：

- 每次 G1 审批中，用户可以否决某条归因/建议 → 该否决作为元层经验记录沉淀（"此类样本归因到 L3 不当"）
- 累积的元层经验触发元层重训练：修改 Skill 的步骤/参数（如归因的置信度阈值、聚类相似度参数）→ 走同样的 ChangeTransaction + 回归
- **训练系统训练方案；使用经验训练训练系统。** 两层共用一套机制，这就是"方案是训练出来的"在元层的兑现

---

## 六、对象层：执行环境适配（可插拔）

任何系统实现三方法即可作为执行环境（τ²-bench / 自建模拟器 / 生产影子模式同一接口）：

```python
class ExecutorBase(ABC):
    def execute(self, solution: Solution, sample: Sample) -> Trace: ...
    def evaluate(self, trace: Trace, expected: Expected) -> Result: ...
    def replay(self, solution: Solution, samples: list[Sample]) -> list[Result]: ...
```

执行适配器在元层架构中是 **L1 级基础设施**（无决策权），不是 Agent。`Tau2BenchExecutor` 把 Solution 转换为 τ²-bench 的 agent 配置并回转 Trace 格式；`SimulatorExecutor` 是确定性模拟器，用于无 API 成本的回归测试与 CI。

---

## 七、核心数据结构（对象层 + 共享）

```python
@dataclass
class Solution:            # 被训练方案
    version: int
    L1_atoms: list[SolidAtom]
    L2_tools: list[CapabilityTool]
    L3_knowledge: list[Knowledge]
    L4_topology: Topology
    regularization_state: RegState
    lambda_values: dict[str, float]     # λ₁~λ₄

@dataclass
class SolidAtom:           # L1 原子
    id: str                # "toggle_roaming"
    type: str              # "read" | "write" | "human" | "notify"
    backend: str           # "telecom_api" | "human_finance_team"
    input_schema: dict
    output_schema: dict
    description: str

@dataclass
class CapabilityTool:      # L2 工具
    id: str                # "safe_toggle_roaming"
    wraps: list[str]       # L1 原子 ID（存在依赖锚点）
    preconditions: list[str]
    postconditions: list[str]
    human_gate: HumanGate | None
    aggregation_logic: str | None

@dataclass
class Knowledge:           # L3 知识（五类）
    id: str
    type: str              # "skill" | "routing_rule" | "chain" | "threshold" | "experience"
    condition: str | None      # 路由条件
    dispatches_to: str | None  # 调度目标 L2 工具（调度≠调用）
    steps: list[ChainStep] | None
    lesson: str | None
    evidence_sample_ids: list[str]

@dataclass
class Topology:            # L4 拓扑
    agents: list[Agent]
    edges: list[TopologyEdge]          # 声明式通信边
    human_gates: list[HumanGatePosition]
    trigger_mode: str

@dataclass
class LossTrace:           # 归因产物
    sample_id: str
    root_cause_layer: str  # "L1"|"L2"|"L3"|"L4"|"human"|"eval_error"
    root_cause_element: str
    failure_mode: str
    detail: str
    evidence: dict             # 含 attribution skill 版本（元层可追溯）
    confidence: float
    side_issues: list[SideIssue]
```

---

## 八、核心算法

### 训练循环（Orchestrator 持有，对应 §三时序）

```python
def train(initial_solution, sample_pool, evaluation, config):
    solution = initial_solution
    for epoch in range(config.max_epochs):
        batch = sample_pool.next_batch(config.batch_size)                  # ①
        traces = executor.execute_batch(solution, batch)                   # ①
        loss_traces = [attribute(s, t, solution) for s, t in failures]     # ② Attributor 扇出
        aggregated = aggregate(loss_traces)                                 # ③ Architect
        reg = compute_regularization(solution, traces)                      # ③ Validator+Auditor
        proposals = propose_updates(aggregated, reg)                        # ④ Architect
        lambda_adj = check_lambda(reg, config)                              # ⑤ Orchestrator/G2
        approved = human_gate_g1(proposals, lambda_adj)                     # ⑥ 硬同步点
        if approved:
            tx = ChangeTransaction(solution, approved)
            candidate = tx.execute()                                        # ⑦ 机械应用+验证
            if validate_regression(candidate, regression_pool).forgot:      # ⑧
                tx.rollback(); continue
            solution = candidate
        training_log.append(epoch, ...)                                     # ⑨ Auditor 哈希链
        if check_convergence(training_log, config): break
    return build_delivery(solution, training_log)
```

### 反向归因（Attributor 持有，S1 的算法化）

```python
def attribute_loss(sample, trace, solution):
    side_issues = []
    # Step 1 → L1: 期望动作的原子存在吗？缺 → 因果性验证 → 是根因则停，否则记附带问题
    # Step 2 → L2: 封装有错吗？在关键路径(有下游消费者且影响输出) → 停；旁路 → 附带问题
    # Step 3 → L3: 实际路径 vs 期望路径？缺链/错分支 → 反事实验证 → 停
    # Step 4 → L4: 拓扑适配吗？复合样本+单Agent → L4
    # 全过 → needs_human / eval_error
```

因果性验证（反事实）：

```python
def is_root_cause(anomaly, trace, expected):
    step = find_step(trace, anomaly)
    if step is None: return False
    if not step.downstream_consumers: return False      # 旁路 → 附带问题
    return would_change_outcome(step, expected)          # 输出不同 → 候选根因
```

---

## 九、ChangeTransaction（对象层原子事务）

```python
class ChangeTransaction:
    """级联变更的原子性保障。BEGIN→APPLY(自底向上)→VALIDATE→COMMIT/ROLLBACK"""
    def execute(self) -> Solution:
        self.snapshot = deepcopy(self.solution)
        try:
            for change in sorted(self.changes, key=lambda c: c.layer):   # L1→L4
                self._apply(change)
            errors = validate_existence_dependencies(self.solution)      # S5
            if errors: raise ValidationError(errors)
            self.solution.version += 1; self.status = "COMMITTED"
            return self.solution
        except Exception:
            self.solution = self.snapshot; self.status = "ROLLED_BACK"; raise
```

禁止中间状态、禁止部分成功。回归失败同样触发 ROLLBACK（§八 ⑧）。

---

## 十、文件结构（两层落位）

```
agentfit/
├── docs/                              # 定稿文档（骨架不改）
├── src/agentfit/
│   ├── agents/                        # ── 元层 L4：六个内部角色 ──
│   │   ├── base.py                    #   AgentRuntime：消息循环基类
│   │   ├── steward.py                 #   交互官（用户唯一对话出口）
│   │   ├── orchestrator.py            #   编排者（路由表+熔断+收敛+λ，确定性）
│   │   ├── attributor.py              #   归因师（可多实例扇出）
│   │   ├── architect.py               #   架构师（bootstrap+聚合+建议+级联）
│   │   ├── validator.py               #   验证官（存在依赖+正则+回归，纯代码）
│   │   └── auditor.py                 #   审计官（哈希链+预算+漂移，纯代码）
│   ├── skills/                        # ── 元层 L3：可训练的 Skill ──
│   │   ├── intake.md                  #   S0a 材料操作化
│   │   ├── clarify.md                 #   S0b 澄清对话
│   │   ├── explain.md                 #   S0c 解释呈现
│   │   ├── attribution.md             #   S1（版本化，训练可更新）
│   │   ├── bootstrap.md               #   S1b 初始方案归纳
│   │   ├── aggregation.md             #   S2
│   │   ├── proposal.md                #   S3
│   │   ├── cascade.md                 #   S4
│   │   ├── validation.md              #   S5
│   │   ├── regression.md              #   S6
│   │   └── lambda_audit.md            #   S7
│   ├── bus/
│   │   └── messages.py                #   TaskMsg/ResultMsg + 路由总线
│   ├── models/                        # ── 对象层数据结构 ──
│   │   ├── solution.py                #   Solution/SolidAtom/... 
│   │   ├── loss.py                    #   LossTrace/SideIssue
│   │   └── config.py                  #   TrainingConfig/LambdaConfig
│   ├── core/                          # ── 对象层算法（Agent 的执行内核）──
│   │   ├── attribution.py
│   │   ├── aggregation.py
│   │   ├── proposals.py
│   │   ├── regularization.py
│   │   ├── regression.py
│   │   └── transaction.py             #   ChangeTransaction
│   ├── data/
│   │   ├── sample_pool.py             #   样本池+回归池（分层抽样）
│   │   └── clustering.py
│   ├── executors/                     # ── L1 级执行基础设施 ──
│   │   ├── base.py                    #   ExecutorBase
│   │   ├── simulator.py               #   确定性模拟器（CI 用）
│   │   └── tau2bench.py               #   τ²-bench 适配器
│   ├── solution/
│   │   ├── builder.py                 #   初始方案构建（Simple First）
│   │   ├── validator.py               #   validate_existence_dependencies
│   │   └── versioning.py
│   ├── log/
│   │   └── training_log.py            #   哈希链日志
│   └── delivery/
│       ├── package.py                 #   交付打包
│       └── boundary.py                #   适用边界分析
└── tests/
    ├── test_attribution.py            #   归因+因果性验证
    ├── test_transaction.py            #   原子性+回滚
    ├── test_regularization.py         #   16 指标+λ 两级
    ├── test_bus.py                    #   消息协议+路由
    └── test_scenarios/
        └── test_telecom.py            #   端到端：训练提升通过率
```

**元层/对象层在代码里的对应**：`agents/` 中 Steward/Attributor/Architect 是 LLM 决策体（消息循环 + 系统 prompt），Orchestrator/Validator/Auditor 是确定性官员（消息循环 + 纯代码，无 prompt）；`skills/*.md` 是认知体的 L3 知识（加载进 prompt，可版本化重训练），`core/` 是无决策的算法内核（Agent 调用的 L2 级能力），`executors/` 是 L1 级基础设施。
