# AgentFit 整体方案

> 文档地位：唯一当前有效的整体方案
>
> 最近收敛：2026-08-11
>
> 当前阶段：初赛材料已就绪；下一阶段是在 AgentTeams 上验证一个可复现的 walking skeleton

## 1. 文档地位与当前状态

本文件统一 AgentFit 的产品定位、方法论、系统边界、责任闭环、评测治理、交付结果和近期验证门禁。后续设计与实现必须以本文件为准；旧方案只存在于 Git 历史中，不构成并行方案。

当前证据状态分为四层：

| 层级 | 当前状态 | 可以对外表述 | 不可以对外表述 |
|---|---|---|---|
| 整体方案与设计契约 | `READY` | 产品定义、方法、五元团队、Skill、Human 与风险边界已收敛 | 已经自动生成或优化了真实 Agent 方案 |
| 初赛材料 | `READY` | 500 字以内简介、12 页主路演、5 页附录和同版 PPTX/PDF 已完成并验证 | PPT 中的设计图等于运行证据 |
| AgentTeams 平台试用 | 已有独立 smoke test | Worker、Team、Human、文件同步、定时任务等底座能力曾被单独试用 | 历史平台测试等于 AgentFit 已集成 |
| AgentFit 真实运行 | `NOT_STARTED` | 正在准备首个 walking skeleton | 已跑通 ProjectCase、候选评测或跨项目学习 |

初赛材料的当前完成态以[准备看板](../competition/2026-08-15/planning/readiness-board.md)为准；真实 AgentFit 运行状态以本文件第 13 节和[AgentTeams 落地设计](../competition/2026-08-15/design/agentteams-landing-design.md)为准。

所有事实必须区分“规范设计”“设计模拟”“平台单项试用”“AgentFit 真实运行”和“生产效果”。下游简介、PPT、演示与口头陈述不得反向改变本文件的事实状态。

## 2. 产品问题、唯一定位与非目标

### 2.1 要解决的问题

现有 Agent 方案通常落在两个极端：

- 重型平台能力丰富，但使用者需要理解和部署大量与当前任务无关的组件；
- 轻型框架足够灵活，但要求使用者自行完成业务抽象、Agent 设计、工具开发和评测。

真实项目往往只有材料、流程、问题、案例和现有系统，却需要先回答：

- 是否应该自动化，是否应该使用 Agent；
- 应选择固定 Workflow、单 Agent、多 Agent还是 Human 混合；
- 哪些 Rule、Algorithm、Model、Skill、MCP、Memory 和通信能力真正必要；
- 哪些能力应该私有、共享、审批或继续由人工承担；
- 新增复杂度是否带来可验证的边际价值；
- 方案如何验收、审计、部署、降级和回滚。

缺失的不是另一组预制 Agent，而是把业务任务转化为可比较架构并用证据作出选择的方案工程层。

### 2.2 唯一产品定义

> AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师。它把业务任务和可用能力编译为可搜索的架构空间，通过统一评测找到“刚好够用”的方案，也允许有证据地保留人工或拒绝自动化。

AgentFit 不预设多 Agent 更好，也不以 Agent 数量为优化目标。它交付的是满足任务、成本、安全和责任约束的最小充分方案。

### 2.3 三层关系

| 层级 | 回答的问题 | 冻结表述 |
|---|---|---|
| 产品价值：Fit / Agent 建筑师 | 为用户解决什么 | 给 Agent 量体裁衣，交付最小充分、可验收的方案 |
| 核心方法：Agent Architecture Search | 如何作出选择 | 任务语义 + 能力语义 + 受约束的架构搜索 + 统一评测 |
| 未来方向：Meta-learning | 如何跨项目变好 | 经脱敏、适配、比较和未见项目验证后，才更新跨项目搜索先验 |

三者不是并列定位。Architecture Search 是核心方法，不覆盖全部审批、审计和交付责任；Meta-learning 是未来跨项目方向，不是当前已实现能力。

### 2.4 五种合法结果

`DeliveryDecision` 的五种合法取值是：

1. 全自动方案；
2. 部分自动化方案；
3. 降级方案；
4. 保留人工；
5. 拒绝自动化。

形式上：

```text
DeliveryDecision =
  SelectedSolution(FullAutomation | PartialAutomation | Degraded)
  | HumanRetained
  | RejectionDecision
```

“不应该增加 Agent”或“当前不应该自动化”也是有效结论，但必须给出证据、适用边界和重新评估条件。

### 2.5 场景边界与非目标

AgentFit 不限制企业规模、行业、岗位或使用者类型。一个场景适合进入方案设计，需要能够描述输入、输出、验收、失败成本、权限、预算和责任边界，并存在可核验的材料、案例、规则、数据或运行反馈。

AgentFit 当前不做：

- 预先定义所有行业 Agent；
- 把每个 Prompt、Skill、工具或 Workflow 阶段包装成 Agent；
- 托管所有 MCP、模型和业务系统；
- 开发独立产品界面；
- 修改 AgentTeams 核心；
- 在第一阶段接入飞书；
- 让优化器静默修改任务目标、验收标准或权限；
- 用本地模拟或历史平台试用替代真实 AgentFit 证据；
- 在没有跨项目未见集验证前宣称 Meta-learning。

## 3. AgentTeams、AgentFit 与 Human 的边界

| 主体 | 负责内容 | 不负责内容 |
|---|---|---|
| AgentTeams | 身份、Worker/Team/Human、房间与通信、容器、生命周期、共享存储、凭证和 Skill/MCP 绑定 | 决定某个业务任务应该采用什么 Agent 架构 |
| AgentFit | 任务与能力语义、能力对齐、候选生成、架构搜索、统一评测、审计、Human 门禁和交付 | 重造通用 Agent 运行时、IM、容器编排或企业 IAM |
| Human | 提供材料、确认任务契约、批准预算与高风险动作、处理责任边界、接受或否决交付 | 替 Agent 静默补证据、修改评测结果或承担未记录的兜底 |

第一阶段采用“AgentTeams 原生底座 + AgentFit 能力包”：

- 使用 AgentTeams 已有 Dashboard、Manager/聊天入口、Worker、Team、Human、Skill、MCP、共享存储和通信；
- 用元 Agent 配置、Prompt、Skill、Schema、项目档案、评测工具和审计模板表达 AgentFit；
- 先手动或半自动跑通最小闭环，再根据真实失败点决定哪些约束必须固化为代码；
- 平台缺口被真实复现后，记录为外部依赖、上游 Issue 或扩展请求，并选择适配、降级或阻塞；AgentFit 不通过修改 AgentTeams 核心吸收该缺口。

```text
Human 与业务材料
        ↓
AgentFit 五元团队
任务编译 → 能力对齐 → 候选设计 → 受控试验 → 独立审计 → 方案交付
        ↓
AgentTeams
身份 / 通信 / Worker / Team / Human / 容器 / Skill / MCP / 共享存储
```

界面和聊天只是控制与观察入口。正式状态由 Project Dossier 中版本化、机器可读的产物决定；聊天结论只有被结构化写入并通过门禁后才能推进项目状态。

## 4. 任务语义、能力语义与 Agent 定义

### 4.1 语义编译

语义编译把自然语言、数据和系统事实转换为结构化、可比较、可计算和可审计的 AgentFit Semantic IR，而不是只做摘要或向量化。

LLM、Embedding、规则解析、Schema 映射、知识图谱、SVD、聚类、传统 ML 和人工标注都可以参与。大模型是实现手段之一；任何生成表示都不能覆盖原始证据或自动成为新事实。

### 4.2 TaskSemanticSpec

任务语义定义“要优化什么，以及什么结果才算解决”：

```text
TaskSemanticSpec = {
  spec_id, version, objective,
  input_space, expected_output, examples, distribution,
  metrics, tradeoffs, acceptance_thresholds,
  budgets, risk_constraints, failure_costs,
  human_boundaries, evidence_requirements, provenance
}
```

候选比较期间任务契约必须冻结。目标、分布、指标、权衡或验收标准变化时，必须产生新版本、由责任人确认并重新执行比较；优化器不得为了让候选通过而降低门槛。

### 4.3 CapabilitySemanticRegistry

能力语义定义“可以使用什么进行安全搜索”：

```text
CapabilitySemanticSpec = {
  capability_id, version, capability_type,
  purpose, applicability,
  input_contract, output_contract, trigger_condition,
  dependencies, cost_latency,
  permissions, side_effects,
  failure_modes, recovery, observability,
  compatibility, scope_policy, reuse_value,
  provenance_and_license
}
```

`capability_type` 至少允许：

```text
Rule / Algorithm / MLModel / LLM / Skill / Tool / MCP / Memory / State / Communication / Human
```

Skill、MCP、Memory 和通信可以是私有、团队、项目或全局资源。共享资源不会自动合并 Agent，私有资源也不会自动生成 Agent。

### 4.4 Agent 的严格定义

> Agent 是具有独立身份、任务所有权、决策闭环、状态边界、权限边界和责任边界的可执行子图。

```text
Agent = {
  Identity, Objective, DecisionPolicy, ActionSpace,
  StateBoundary, PermissionBoundary, CommunicationPort,
  Lifecycle, TraceOwnership
}
```

决策策略可以是 LLM、规则、传统 ML 或混合实现。判定重点是主体能否基于目标和状态选择下一行动、停止、重试、委派或升级人工，并对独立产物负责。

以下对象本身不构成 Agent：单次 LLM 调用、只有 Prompt 和工具列表的角色、不能选择下一行动的固定 Workflow 阶段、Skill、MCP、API、数据库、Memory、容器、进程或通信房间。

Skill 是可复用做事方法；MCP/Tool 是外部接口；Memory 是状态介质；Communication 是跨边界协议；Workflow 是外部顺序和门禁；Agent 是组合和支配能力子图的独立决策与责任主体。

### 4.5 任务—能力对齐

语义编译后必须生成 `AlignmentReport`，逐项记录：

- 完整覆盖、部分覆盖和未覆盖要求；
- 输入输出不兼容和能力冲突；
- 无法观测或验证的要求；
- 必须人工确认或需要更高权限的能力；
- 私有、团队、项目和全局共享范围；
- 进入候选生成前必须解决的缺口。

能力缺口不能通过虚构 Agent 名称掩盖。无法在授权范围内补齐时，应请求材料、缩小范围、保留人工或停止搜索。

## 5. 候选空间与 Agent Architecture Search

### 5.1 联合候选表示

```text
Candidate = (G, Π, θ, ρ)
```

- `G`：能力图，包含能力节点、数据边、控制边、状态依赖、DAG 主干和局部 SCC；
- `Π`：Agent 分区，决定哪些可执行子图拥有独立身份与责任；
- `θ`：模型、Prompt、Embedding、算法、阈值、重试、预算和局部策略；
- `ρ`：Skill、MCP、Memory、数据、状态和通信的私有与共享范围。

Agent 不是与 Skill 或 Tool 并列的普通节点，而是对能力子图施加身份、决策、状态、权限、生命周期和责任边界的分区。

### 5.2 图与约束

能力图可以包含规则、算法、模型推理、工具/MCP、Human 决策、记忆读写和可折叠 Skill 子图；边可以表示顺序、条件、并行、汇聚、Artifact 传递和环境反馈。

局部 SCC 用于有界反思、验证、工具反馈或协商；DAG 主干保证阶段推进和终止。权限冲突、禁止组合和不得执行的路径表示为显式约束或门禁，不使用含义不明的“负边”。

### 5.3 Agentize

```text
Agentize(
  subgraph, identity, objective, decision_policy,
  state_boundary, permissions, communication,
  trace_responsibility
)
```

只有子图确实需要独立决策、上下文隔离、权限隔离、并行执行、独立生命周期或独立审计责任时，才允许 Agentize；否则保留为能力节点、Skill 或 Workflow 阶段。

### 5.4 连续搜索空间

```text
固定规则或工具 DAG
→ 加入模型能力节点
→ 加入局部反馈 SCC
→ Agentize 局部子图
→ 单 Agent
→ 按上下文、权限、并行或责任拆分为多 Agent
```

Agentless、固定 Workflow、单 Agent、多 Agent、Human 混合、部分自动化和拒绝自动化属于同一搜索空间。

### 5.5 Baseline-first 纪律

```text
从覆盖核心契约的最简候选开始
→ 只有局部不足时增加反馈循环
→ 只有出现独立决策或边界需求时 Agentize
→ 只有单 Agent 遭遇上下文、权限、并行或责任问题时拆分
→ 选择满足门槛的最小充分候选
```

每增加一个 Agent、模型、工具、循环或共享范围，都必须在统一输入、预算、指标和安全门禁下证明边际价值。比赛要求的多 Agent 闭环由 AgentFit 常驻元团队承担；被设计的候选系统不为凑数量而拆分。

## 6. 内循环、外循环与 Meta-learning 边界

### 6.1 内循环

内循环在任务契约和 Agent 边界不变时优化局部节点或 SCC，例如 Prompt、模型、Embedding、特征、分解秩、阈值、规则权重、检索、工具配置、Skill 选择、上下文压缩、重试和局部预算。

内循环不得自行创建或销毁 Agent、扩大权限、改变责任边界或修改验收标准。

### 6.2 外循环

外循环根据 validation、成本、复杂度、风险和审计结果改变整体候选，例如增删能力节点、改变拓扑、Agentize 或取消 Agentize、拆分或合并 Agent、改变通信与共享范围，以及在 Agentless、单 Agent、多 Agent和 Human 混合之间迁移。

```text
内循环：在固定架构 A 下寻找局部最优参数 θ*A
外循环：比较架构 A 的验证损失、复杂度、成本、风险和不可观测性
```

正式实现可以使用硬阈值、Pareto 前沿、分层门禁、图搜索、进化搜索、贝叶斯优化、规则或人工评审，不要求固定线性权重。

### 6.3 运行单位

| 名称 | 定义 |
|---|---|
| Step | 一次推理、工具调用或环境反馈 |
| Episode | 一个任务样例的完整执行 |
| Inner Epoch | 固定候选对全部 adaptation 样例的一轮适配 |
| Outer Generation | 一次候选生成、局部适配、validation 和架构更新 |
| Meta Epoch | 跨多个项目更新并验证搜索先验 |

局部 SCC 的一次循环只是 Step，不称为 Epoch。

### 6.4 Meta-learning 是未来方向

项目内参数优化和架构搜索不是 Meta-learning。跨项目资产复用只有在多个项目轨迹更新搜索先验，并在未见项目上相对无先验 baseline 稳定改善时，才构成 Meta-learning 证据。

LLM、Embedding、SVD、图算法或其他方法都只是更新表示、局部参数、候选结构或搜索先验的可选技术手段，不能替代未见项目验证。

## 7. 五元 Agent 团队与责任闭环

### 7.1 常驻元团队

| Agent | 核心职责 | 独立责任产物 |
|---|---|---|
| EngagementLead | 接收任务、控制阶段、组织审批和交付 | Project Dossier 状态、ArchitectureDecision、DeliveryDecision |
| BusinessEngineer | 理解材料、编译任务语义和自动化边界 | TaskSemanticSpec |
| AgentArchitect | 盘点能力、对齐、建图和 Agent 分区 | Capability Registry、AlignmentReport、CandidateGraphSet |
| ValidationEngineer | 部署候选、执行受控试验和故障注入 | EvaluationRun、ExecutionTrace |
| GovernanceAuditor | 独立检查 holdout、安全、复杂度和证据 | EvaluationReport、审计结论 |

五个 Agent 具有独立目标、状态、决策、权限和责任产物，不是五个角色标签。`EngagementLead` 第一阶段可映射到 AgentTeams Manager 或 Team Leader；其余四个角色使用独立 Worker，实际映射以固定版本的运行配置为准。

### 7.2 固定阶段骨架

```text
Intake → Discover → Architect → Approve → Trial → Audit → Deliver → Learn
```

| 阶段 | 核心产物 | 门禁 |
|---|---|---|
| Intake | Project Dossier、范围和来源 | 责任人和材料来源明确 |
| Discover | TaskSemanticSpec、Capability Registry、AlignmentReport | 输入、输出、验收和缺口可描述 |
| Architect | CandidateGraphSet、风险和预算 | 候选可执行且复杂度有理由 |
| Approve | TrialSpec、权限和审批记录 | 数据、预算、回滚和试验范围获批 |
| Trial | 运行结果、Trace、故障和成本 | 输入、数据划分和预算受控 |
| Audit | EvaluationReport、选择或否决建议 | 审计输入与结论可独立追溯 |
| Deliver | DeliveryDecision；对应的 AgentSolutionPackage、HumanRetained 或 RejectionDecision | 用户确认责任和风险 |
| Learn | ProjectAsset；可选 MetaAsset 提案 | 脱敏、复验、审计和回滚 |

### 7.3 通信、状态与责任

通信渠道用于委派、讨论、质疑和人工介入；Project Dossier 是状态事实源；ExecutionTrace 保存决策与执行证据。

```text
RawMaterials
  → TaskSemanticSpec
  → CapabilitySemanticRegistry + AlignmentReport
  → CandidateGraphSet + TrialSpec
  → EvaluationRun[] + EvaluationReport
  → DeliveryDecision
  → AgentSolutionPackage | HumanRetained | RejectionDecision
```

一个 Agent 不可用时，对应阶段保持未完成并记录失败；其他 Agent 不得静默冒充其责任产物。

### 7.4 首轮 walking skeleton

最近几天只验证一条链路：

```text
Human 提交材料
→ EngagementLead 建立 Project Dossier
→ BusinessEngineer 生成 TaskSemanticSpec
→ AgentArchitect 生成能力清单、缺口和候选
→ Human 批准预算与试验
→ ValidationEngineer 执行至少一个真实候选
→ GovernanceAuditor 独立审计
→ EngagementLead 输出 DeliveryDecision
```

首轮允许人工触发阶段和创建资源，但不得人工口头补齐结构化产物、责任归属、候选输入、预算或审计结论。

## 8. Project Dossier、版本、预算与安全

### 8.1 Project Dossier

每个正式项目必须维护版本化 Project Dossier：

```text
ProjectDossier = {
  source_evidence, raw_materials,
  task_semantic_spec, capability_semantic_registry,
  alignment_report, candidate_graph_set,
  data_splits, trial_specs, budgets, safety_constraints,
  evaluation_runs, execution_traces, audit_reports,
  approvals, delivery_decision, artifacts,
  provenance_and_license
}
```

数据应按仓库、环境、任务族、模板、时间或其他真实分布边界划分，而不是只做随机行切分。单项目至少区分 adaptation、validation 和 sealed holdout；失败与压力样例单独记录。

### 8.2 版本与可复现

每次试验必须固定或记录：

- TaskSemanticSpec、能力、候选和 TrialSpec 版本；
- 数据集、任务 ID、来源快照和哈希；
- 模型、Prompt、Embedding、算法和依赖版本；
- AgentTeams、Skill、MCP、工具和外部服务版本；
- 随机种子、预算、超时、最大步数和并发；
- 权限、审批、环境、镜像和部署配置。

### 8.3 预算与公平比较

候选必须使用可比的样例、模型与工具边界、token/API/工具调用预算、wall-clock、步数、重试、并行和 Human 规则。候选不能通过未披露地增加模型、工具、预算或人工投入获得“胜利”。

### 8.4 安全和 Human 边界

所有候选遵循：

- 最小权限和明确数据范围；
- 密钥由基础设施持有，不进入 Agent 上下文；
- 外部写入、真实发布、预算变更和责任转移需要 Human 审批；
- 沙箱、超时、预算和最大循环次数；
- 失败、拒绝、人工接管、降级和回滚路径预先定义；
- 成功、失败和否决证据同等保留；
- 共享资产晋升前脱敏、参数化、复验和审计。

Human 是候选图中的能力和约束对象，必须记录触发条件、审批主体、输入输出、响应时限、拒绝、超时和回滚；不是一句“必要时人工处理”的兜底文案。

## 9. 统一评测、Trace、审计与停止规则

### 9.1 统一评测

至少评估：

- 任务正确性、关键子群表现和验收阈值；
- 泛化、稳定性、重试和失败恢复；
- 成本、时延、步数、资源和人工投入；
- 权限、数据、外部副作用和回滚；
- Trace 完整性、证据质量和可复现性；
- Agent、Skill、模型和能力节点的边际价值；
- adaptation、validation 和 holdout 差距；
- 人工接管质量和最终责任边界。

### 9.2 ExecutionTrace

```text
ExecutionTrace = {
  task_spec_version, candidate_version,
  episode_and_step, agent_identity,
  input_and_state_refs, decision_and_reason_code,
  tool_or_skill_call, permission_and_approval,
  output_and_artifact_refs, cost_latency_and_errors,
  retry_fallback_and_rollback
}
```

Trace 必须能从结论回到输入、版本、决策、工具调用、审批和产物，也能从原始任务正向重放关键路径。

### 9.3 独立审计

AgentArchitect 不得使用 sealed holdout 定向修改候选。ValidationEngineer 执行隔离评测；GovernanceAuditor 只基于获准证据解释留出表现、安全、复杂度和可复现性；EngagementLead 只能基于审计产物作出交付决定。

压力与失败集至少覆盖工具超时、权限拒绝、错误输入、环境故障、数据漂移、循环失控、成本超限、审批缺失、错误写入和回滚失败。

### 9.4 停止规则

满足以下任一条件可以停止：

1. 达到全部硬阈值且没有更简单的等价候选；
2. 连续若干轮没有足够边际改进；
3. 达到预算、时间或复杂度上限；
4. 核心能力缺口无法在授权范围内补齐；
5. holdout 暴露不可接受风险；
6. 人工责任无法安全转移；
7. 新增 Agent 或能力的成本与风险高于收益。

停止必须产生明确的全自动、部分自动化、降级、保留人工或拒绝决定，而不是隐藏失败。

## 10. 交付方案包与选择结果

```text
AgentSolutionPackage = {
  task_spec_version,
  delivery_decision,
  candidate_and_architecture_decision,
  agent_identities,
  skills_and_mcp_bindings,
  memory_and_communication_topology,
  human_approval_and_refusal_gates,
  permissions_and_side_effects,
  deployment_manifest,
  evaluation_protocol_and_results,
  trace_and_audit_artifacts,
  rollback_and_failure_handling,
  provenance_dependencies_and_licenses
}
```

`ArchitectureDecision` 必须回答：

```text
为什么这样理解任务
→ 为什么选择这些能力
→ 为什么形成这张图
→ 为什么这些子图需要或不需要 Agentize
→ 为什么该候选优于更简单或更复杂的候选
→ 为什么可以部署、必须降级、保留人工或应该拒绝
```

交付不是 Prompt 或聊天记录。选择自动化方案时交付可部署或可执行、可评测、可审计、可回滚并带适用边界的 `AgentSolutionPackage`；保留人工或拒绝自动化时，交付对应决定、证据和重新评估条件。

## 11. 跨项目资产方向

### 11.1 ProjectAsset

单项目可以沉淀任务和能力语义、经验证的候选图、Agentize 决策、Skill/Prompt/算法配置、评测模板、失败模式、审批回滚和 Trace。ProjectAsset 默认只有项目作用域，不自动成为全局能力。

### 11.2 MetaAsset 晋升

ProjectAsset 只有经过以下流程才能晋升为 MetaAsset：

```text
脱敏 → 参数化 → 标注适用域和失败边界
→ 在其他项目重新适配
→ 与无先验 baseline 比较
→ 污染和负迁移检查
→ 独立审计
→ 版本化晋升
→ 持续回归与回滚
```

只要未见项目退化、数据污染、适用边界不清或证据被推翻，资产就不得晋升或必须冻结。

### 11.3 当前边界

仓库当前不预设跨场景项目集或迁移对。首个真实 ProjectCase 完成后，才能依据任务语义、能力边界和运行证据选择迁移对象；单组迁移结果仍不能写成 Meta-learning。

## 12. 比赛映射与事实红线

### 12.1 比赛价值主张

AgentFit 的差异不是“又一个多 Agent 框架”，而是：

1. 从原始材料和业务目标编译任务与能力语义；
2. 将 Agent 方案设计转化为受约束的图和分区搜索；
3. 在同一任务上比较 Agentless、单 Agent、多 Agent和 Human 混合；
4. 同时优化效果、成本、风险、稳定性和可审计性；
5. 只在未见项目验证后才更新跨项目先验。

### 12.2 初赛材料状态

当前已完成并验证：

- 468 个非空白字符的作品简介；
- 12 页主路演 + 5 页附录；
- 17 页 HTML-first、可编辑 PPTX 和同版 PDF；
- 五个 Agent Identity、七个核心 Skill、Human/风险门禁、开放与合规披露；
- 官网参考方向拆解与软件研发设计模拟，均明确标记为非运行证据。

ProjectCase、真实五元团队和统一候选对照尚未完成，不是初赛方案冻结的前置条件，也不得在材料中伪装为完成。

### 12.3 官方关注点映射

| 官方关注点 | AgentFit 证明对象 |
|---|---|
| 不少于三个不同职能 Agent | 五个常驻元 Agent 的 Identity、责任产物和协作 Trace |
| AgentTeams 为协同基点 | 角色、房间、任务、状态、Worker、Human、共享存储和 Trace 的真实映射 |
| Skill 工程和复用 | 任务编译、能力对齐、候选建图、统一试验、独立审计、人工门禁和经验沉淀 Skill |
| 上下文机制 | Project Dossier 共享状态和 ExecutionTrace 轨迹可观测 |
| 工具与 MCP | 版本、Schema、权限、鉴权、错误、幂等、降级和审计 |
| 高风险动作 | Human 审批、拒绝、超时、回滚和责任记录 |
| 工程和安全 | 可复现入口、依赖、配置、故障、成本、权限和证据包 |
| 开放贡献 | 可复用 Schema、Skill、评测、示例、文档、许可证和维护计划 |

### 12.4 红线

禁止：

- 把概念图、设计模拟或历史 smoke test 写成 AgentFit 真实运行；
- 把 AgentTeams 名称或底座能力当作集成证据；
- 把 Meta-learning、自动搜索或生产收益写成当前能力；
- 隐瞒既有仓库、第三方贡献、商业 API、闭源模型、数据来源或许可证；
- 让高风险动作绕过审批、拒绝、超时、回滚和审计；
- 只展示成功，不保留失败、降级、人工保留和否决；
- 让比赛材料与内部证据状态不一致。

## 13. 当前未实现范围与 AgentTeams 首轮验证门禁

### 13.1 当前未实现

当前没有证据表明以下能力已经完成：

- TaskSemanticSpec、CapabilitySemanticSpec、AlignmentReport、Candidate 和 Trace 的正式机器可执行 Schema；
- Task–Capability 覆盖、冲突和缺口算法；
- Agentize 必要性、复杂度代价和自动候选搜索；
- ProjectAsset/MetaAsset 正式存储、晋升和回归系统；
- 任一完整、冻结的真实 ProjectCase；
- AgentFit 五元团队、Skill、MCP、共享状态和 Trace 的真实 AgentTeams 集成；
- 统一预算下的 Agentless、单 Agent和多 Agent真实对照；
- 跨项目迁移收益、Meta-learning、生产部署或真实业务效果。

### 13.2 近期唯一验证目标

下一阶段不是继续扩展方案，也不是同时建设六个场景，而是在 AgentTeams 上完成一个最小 walking skeleton。首个 ProjectCase 仍需明确选择，在冻结前不得写成已批准测试项目。

可声称“AgentFit 已在 AgentTeams 跑通最小闭环”，必须同时满足：

1. 五个 Agent 具有可检查身份、独立责任和独立产物；
2. 一个冻结 ProjectCase 从 Intake 流转到 Deliver；
3. 至少执行一个真实候选，并保留输入、输出、版本、模型、工具、用量和 Trace；
4. 至少保留一个失败、降级、拒绝或 Human 门禁分支；
5. GovernanceAuditor 的审计输入与结论可独立追溯；
6. 固定 AgentTeams 版本、配置、已验证能力和未验证边界；
7. 能在干净环境按仓库说明复现。

### 13.3 代码边界判定

首轮验证后，只有以下内容应优先固化为 AgentFit 代码：

- Schema 校验和版本约束；
- 阶段状态、审批主体和失败状态的确定性门禁；
- 数据划分与候选预算隔离；
- Trace、依赖、模型和版本的自动记录；
- 高风险动作的拒绝、审批、超时与回滚；
- 评测汇总和比赛声明到内部证据的反向定位。

AgentFit 不开发独立 UI、不修改 AgentTeams 核心，也不自建通用运行平台。真实试验只用于确定哪些 AgentFit 领域约束需要通过配置、Skill、工具、MCP、适配层或仓库内代码固化。

## 14. 规范引用

- [初赛方案与路演冻结设计](../competition/2026-08-15/design/presentation-redesign.md)
- [AgentTeams 落地设计](../competition/2026-08-15/design/agentteams-landing-design.md)
- [初赛准备看板](../competition/2026-08-15/planning/readiness-board.md)
- [Agent Identity 清单](../competition/2026-08-15/submission/agent-identity.md)
- [核心 Skill 清单](../competition/2026-08-15/submission/skill-catalog.md)
- [Human 与风险门禁](../competition/2026-08-15/submission/risk-and-human-gates.md)
- [开放与合规披露](../competition/2026-08-15/submission/openness-and-compliance.md)
- [GOAI Agent Infra 初赛要求矩阵](internal/competition/preliminary-requirements-matrix.md)
- [GOAI Agent Infra 初赛红线与声明检查表](internal/competition/preliminary-red-line-checklist.md)
- [Evidence Registry](internal/evidence-research/evidence-registry.json)
- [ProjectCase Contract](internal/contracts/project-case-template.md)
- [《新智基座》Agent Infra 参赛手册](reference/新智基座-参赛手册.pdf)

历史版本只通过 Git 提交记录追溯，不能覆盖本文件的当前定义、完成状态和证据边界。
