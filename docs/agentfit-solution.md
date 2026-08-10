# AgentFit 整体方案

> 文档地位：唯一当前有效的整体方案
>
> 最近收敛：2026-08-10
>
> 适用范围：产品定位、方法论、系统边界、执行闭环、评测治理、跨项目成长和比赛证明责任

## 1. 文档地位与当前证据状态

本文件是 AgentFit 唯一当前有效的整体方案。后续设计和正式实现必须以本文件为准；历史讨论、旧方法论和执行计划仅用于追溯，不构成并行版本。

内部事实由以下材料支撑：

- [初赛要求矩阵](internal/competition/preliminary-requirements-matrix.md)和[红线清单](internal/competition/preliminary-red-line-checklist.md)；
- [Evidence Registry](internal/evidence-research/evidence-registry.json)及十二张已核验来源卡；
- [ProjectCase 契约](internal/cross-scenario-project-suite/project-case-template.md)；
- [v0 选择矩阵](internal/cross-scenario-project-suite/v0-selection-matrix.md)、[选择理由](internal/cross-scenario-project-suite/v0-selection-rationale.md)和 [Manifest](internal/cross-scenario-project-suite/v0-manifest.json)；
- [官方参赛手册](reference/新智基座-参赛手册.pdf)。

截至本文收敛时：

- 已完成方法论、证据契约、十二张跨领域证据卡和 v0 候选评分；
- v0 Manifest 状态仍是 `proposed_for_user_approval`；
- 本地同步模拟器已隔离到被 Git 忽略的 `demo/`，其结果不属于正式证据；
- 尚未完成真实 ProjectCase、真实 AgentTeams 集成、真实模型评测、生产验证或跨项目 Meta-learning 验证。

所有对外材料必须区分“规范设计”“本地模拟”“真实运行”和“生产效果”。内部证据是唯一事实源；比赛简介和 PPT 只能由已核验事实派生。

## 2. 问题、定位与非目标

### 2.1 要解决的问题

现有 Agent 方案通常落在两个极端：

- 重型平台能力丰富，但使用者需要理解和部署大量与当前任务无关的组件；
- 轻型框架足够灵活，但要求使用者自行完成业务抽象、Agent 设计、工具开发和评测。

真实项目通常只有材料、流程、问题、案例和现有系统，并不知道：

- 是否应该使用 Agent；
- 应选择固定 Workflow、单 Agent 还是多 Agent；
- 哪些 Skill、MCP、Memory、通信和非 LLM 方法真正必要；
- 哪些能力应私有、共享或保留人工；
- 新增复杂度是否带来可验证价值；
- 方案如何部署、审计、回滚和成长。

### 2.2 正式定位

> AgentFit 是运行在 AgentTeams 上的 Agent 解决方案元团队。它从用户材料、任务目标和现有能力出发，将任务与能力编译为结构化语义，构造并评测 Agentless、单 Agent、多 Agent和 Human 混合候选，最终交付可部署、可评测、可审计、可回滚的最小充分方案，或者有证据地降级、保留人工或拒绝自动化。

AgentFit 解决的是业务问题与 Agent 基础设施之间缺失的“方案工程”，而不是再造一个通用 Agent 运行框架。

### 2.3 场景边界

AgentFit 不限制企业规模、行业、岗位或使用者类型。适用场景应满足：

1. 存在重复或可迁移的任务；
2. 输入、输出、失败和责任边界能够描述；
3. 存在案例、规则、数据、运行反馈或其他可核验事实；
4. 能通过测试、证据、人工复核或业务指标验收；
5. 存在质量、成本、时延、安全或自动化率之间的权衡；
6. 工具和系统能够在受控权限下访问；
7. 可以设置预算、沙箱、审批、降级和回滚；
8. 存在两个以上有意义的候选方案可比较。

若验收标准不可描述、证据不足或最终责任无法安全转移，合法结果是补充材料、限制自动化、保留人工或拒绝自动化。

### 2.4 非目标

AgentFit 不以以下事项为目标：

- 预先定义所有行业 Agent；
- 预设多 Agent 优于单 Agent或固定 Workflow；
- 把每个 Prompt、Skill、工具或流程阶段包装成 Agent；
- 托管所有 MCP、模型和业务系统；
- 让优化器静默修改任务目标和验收标准；
- 用本地模拟替代真实 AgentTeams 与业务证据；
- 在第一版构建无边界的自主进化系统。

## 3. AgentTeams 与 AgentFit 的系统边界

系统采用“运行底座 + 方案工程层”两层结构：

| 层级 | 责任 |
|---|---|
| AgentTeams | 身份、Manager/Worker/Human/Team、通信房间、任务分发、运行容器、共享文件和基础能力绑定 |
| AgentFit | 语义编译、能力对齐、候选建图、Agent 分区、实验控制、评测审计、审批回滚、方案交付和跨项目资产治理 |

AgentTeams 提供 Agent 系统能够运行和协同的底层条件；AgentFit 决定针对一个具体任务应设计什么系统，以及该设计是否值得部署。

AgentFit 不重新定义 AgentTeams 上游实现，也不把底层存在某项能力写成场景已经完成。正式接入时必须记录 AgentTeams 版本、实际使用能力、未验证边界和对应 Trace。

候选系统在隔离实验环境中被创建、运行、比较和销毁：

```text
用户与业务材料
       ↓
AgentFit 常驻元团队
语义编译 → 候选设计 → 试验控制 → 独立审计 → 交付
       ↓
Preflight Lab
固定 Workflow / 单 Agent / 多 Agent / Human 混合候选
```

Preflight Lab 是实验边界，不是独立产品。正式实现可以替换其具体技术，但必须保留候选隔离、统一输入、统一预算、失败注入和独立审计能力。

## 4. 任务语义与能力语义

### 4.1 语义编译

语义编译不是对材料做摘要，也不等同于生成向量。它把自然语言、数据和系统事实转换为结构化、可比较、可计算和可审计的 AgentFit Semantic IR。

LLM、Embedding、规则解析、Schema 映射、知识图谱、SVD、聚类和人工标注都可以参与；任何生成表示都不能覆盖原始证据或自动变成新事实。

### 4.2 TaskSemanticSpec

任务语义定义“要优化什么，以及什么结果才算解决”：

```text
TaskSemanticSpec = {
  spec_id,
  version,
  objective,
  input_space,
  expected_output,
  examples,
  distribution,
  metrics,
  tradeoffs,
  acceptance_thresholds,
  budgets,
  risk_constraints,
  failure_costs,
  human_boundaries,
  evidence_requirements,
  provenance
}
```

候选比较期间任务契约必须稳定。目标、分布、指标、权衡或验收标准的变化必须：

1. 产生新的 `TaskSemanticSpec` 版本；
2. 由责任人确认；
3. 重新划分或核验数据；
4. 重新执行候选比较。

优化器不得为了让候选“通过”而静默降低验收标准。

### 4.3 CapabilitySemanticRegistry

能力语义定义“可以使用什么进行安全搜索”：

```text
CapabilitySemanticSpec = {
  capability_id,
  version,
  capability_type,
  purpose,
  applicability,
  input_contract,
  output_contract,
  trigger_condition,
  dependencies,
  cost_latency,
  permissions,
  side_effects,
  failure_modes,
  recovery,
  observability,
  compatibility,
  scope_policy,
  reuse_value,
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
  Identity,
  Objective,
  DecisionPolicy,
  ActionSpace,
  StateBoundary,
  PermissionBoundary,
  CommunicationPort,
  Lifecycle,
  TraceOwnership
}
```

决策策略可以是 LLM、规则、传统 ML 或混合实现。判定重点是主体能否基于目标和状态选择下一行动、停止、重试、委派或升级人工，并对独立产物负责。

以下对象本身不构成 Agent：

- 单次 LLM 调用；
- 只有 Prompt 和工具列表、没有任务所有权的角色；
- 不能选择下一行动的固定 Workflow 阶段；
- Skill、MCP、API、数据库、Memory 或共享状态；
- 容器、进程或通信房间。

Skill 是可复用做事方法；MCP/Tool 是外部接口；Memory 是状态介质；Communication 是跨边界协议；Workflow 是外部顺序和门禁；Agent 是组合和支配能力子图的独立决策与责任主体。

### 4.5 任务—能力对齐

语义编译后必须生成 AlignmentReport，逐项记录：

- 完整覆盖、部分覆盖和未覆盖要求；
- 输入输出不兼容和能力冲突；
- 无法观测或无法验证的要求；
- 必须人工确认或需要更高权限的能力；
- 私有、团队、项目和全局共享范围；
- 进入候选生成前必须解决的缺口。

能力缺口不能通过虚构 Agent 名称掩盖。缺口无法在授权范围内补齐时，应请求材料、缩小范围或停止搜索。

## 5. 候选图与结构搜索

### 5.1 联合候选表示

```text
Candidate = (G, Π, θ, ρ)
```

- `G`：基础能力图，包含能力节点、数据边、控制边、状态依赖、DAG 主干和局部 SCC；
- `Π`：Agent 分区，决定哪些可执行子图拥有独立身份与责任；
- `θ`：模型、Prompt、Embedding、分解秩、阈值、重试、规则权重、工具配置和局部策略；
- `ρ`：Skill、MCP、Memory、数据、状态和通信的私有与共享范围。

Agent 不是与 Skill 或 Tool 并列的普通节点，而是对能力子图施加身份、决策、状态、权限、生命周期和责任边界的分区。

### 5.2 图元素

基础能力图可以包含：

- 规则、算法、模型推理、工具/MCP、Human 决策和记忆读写节点；
- 可折叠或展开的 Skill 子图；
- 顺序、条件、并行、汇聚、Artifact 传递和环境反馈边；
- 私有状态、共享状态和外部事实源；
- 用于有界反思、验证、工具反馈或协商的局部 SCC；
- 保证阶段推进和终止路径的 DAG 主干。

禁止组合、权限冲突和不得执行的路径在未形成其他规范前表示为搜索约束或门禁，不使用含义不明的“负边”。

### 5.3 Agentize

```text
Agentize(
  subgraph,
  identity,
  objective,
  decision_policy,
  state_boundary,
  permissions,
  communication,
  trace_responsibility
)
```

只有当子图确实需要独立决策、上下文隔离、权限隔离、并行执行、独立生命周期或独立审计责任时，才允许 Agentize；否则应保留为 Skill、能力节点或 Workflow 阶段。

### 5.4 连续复杂度空间

```text
固定规则或工具 DAG
→ 加入模型能力节点
→ 加入局部反馈 SCC
→ Agentize 局部子图
→ 单 Agent
→ 按上下文、权限、并行或责任拆分
→ 多 Agent
```

Agentless、固定 Workflow、单 Agent、多 Agent、Human 混合、部分自动化和拒绝自动化属于同一搜索空间。Agent 数量不是目标；每增加一个 Agent，都必须在统一数据和预算下证明边际价值。

### 5.5 Baseline-first 搜索纪律

```text
从覆盖核心契约的最简 Workflow 开始
→ 只有局部不足时增加反馈循环
→ 只有出现独立决策或边界需求时 Agentize
→ 只有单 Agent 遭遇上下文、权限、并行或责任问题时拆分
→ 选择满足门槛的最小充分候选
```

比赛要求的多 Agent 闭环由 AgentFit 常驻元团队真实承担；候选系统不得为了数量要求把每个阶段改名为 Agent。

## 6. 内循环、外循环与 Meta-learning

### 6.1 内循环

内循环在任务契约和 Agent 边界不变时优化局部节点或 SCC，可以调整：

- Prompt、模型、Embedding、特征和分解秩；
- 阈值、规则权重、检索和工具配置；
- Skill 选择、内部调用顺序和上下文压缩；
- 重试、局部预算和 SCC 终止条件；
- 不改变外部契约的内部拓扑。

内循环不得自行创建或销毁 Agent、扩大权限、改变责任边界或修改验收标准。

### 6.2 外循环

外循环根据 validation、成本、复杂度、风险和审计结果改变整体候选：

- 增删能力节点或改变全局拓扑；
- Agentize、取消 Agentize、拆分或合并 Agent；
- 改变通信和共享范围；
- 在 Agentless、单 Agent、多 Agent和 Human 混合之间迁移；
- 降级、停止或否决自动化。

形式上：

```text
内循环：θ*A = argminθ L_adaptation(A, θ)

外循环：A* = argminA [
  L_validation(A, θ*A)
  + complexity
  + cost
  + risk
  + unobservability
]
```

正式实现可以使用硬阈值、Pareto 前沿、分层门禁、图搜索、进化搜索、贝叶斯优化、规则或人工评审，不要求固定线性权重。

### 6.3 Step、Episode 与 Epoch

| 名称 | 定义 |
|---|---|
| Step | 一次推理、工具调用或环境反馈 |
| Episode | 一个任务样例的完整执行 |
| Inner Epoch | 固定候选对全部 adaptation 样例的一轮适配 |
| Outer Generation | 一次候选生成、局部适配、validation 和架构更新 |
| Meta Epoch | 跨多个项目更新并验证搜索先验 |

局部 SCC 的一次循环只是 Step，不称为 Epoch。

### 6.4 跨项目 Meta-learning

单项目内部的参数优化和架构搜索不属于 Meta-learning。跨项目学习分为：

| 层级 | 定义 | 结论 |
|---|---|---|
| 项目内双层优化 | 当前项目中优化参数和结构 | 不是 Meta-learning |
| 跨项目资产复用 | 使用已验证模板作为起点并重新适配 | 迁移与复用 |
| 跨项目先验更新 | 多项目轨迹更新候选生成、Agentize 条件和搜索顺序，并在未见项目验证 | 才是 Meta-learning |

可学习的先验包括初始图、Agentize 条件、Skill/MCP/Memory 组合、失败模式、评测模板和搜索顺序。新项目必须使用自己的任务语义、数据和 holdout 重新适配。

ProjectAsset 晋升为 MetaAsset 必须经历：

```text
脱敏 → 参数化 → 标注适用域和失败边界
→ 在其他项目重新适配
→ 与无先验 baseline 比较
→ 污染和负迁移检查
→ 独立审计
→ 版本化晋升
→ 持续回归与回滚
```

只要未见项目 holdout 退化、数据污染、适用边界不清或证据被推翻，资产就不得晋升或必须冻结。

## 7. 元 Agent 团队及执行流程

### 7.1 常驻元团队

| Agent | 核心职责 | 独立责任产物 |
|---|---|---|
| EngagementLead | 接收任务、控制阶段、审批和交付 | 项目状态、ArchitectureDecision、最终交付 |
| BusinessEngineer | 理解材料、编译任务语义和自动化边界 | TaskSemanticSpec |
| AgentArchitect | 盘点能力、对齐、建图和 Agent 分区 | Capability Registry、AlignmentReport、CandidateGraph |
| ValidationEngineer | 部署候选、执行内循环、故障和统一试验 | EvaluationRun、ExecutionTrace |
| GovernanceAuditor | 独立检查 holdout、安全、复杂度和证据 | EvaluationReport、审计结论 |

五个 Agent 具有独立目标、状态、决策、权限和责任产物，不是为了比赛数量而进行的名称拆分。

### 7.2 固定阶段骨架

```text
Intake
→ Discover
→ Architect
→ Approve
→ Trial
→ Audit
→ Deliver
→ Learn
```

| 阶段 | 核心产物 | 门禁 |
|---|---|---|
| Intake | Project Dossier、范围和来源 | 责任人和材料来源明确 |
| Discover | TaskSemanticSpec、Capability Registry、AlignmentReport | 输入、输出、验收和缺口可描述 |
| Architect | CandidateGraphSet、Agent 分区、风险和预算 | 候选可执行且复杂度有理由 |
| Approve | TrialSpec、权限和审批记录 | 数据、预算、回滚和试验范围获批 |
| Trial | 适配结果、Trace、故障和成本 | adaptation 与 holdout 隔离 |
| Audit | EvaluationReport、选择或否决建议 | 每个结论可追溯 |
| Deliver | AgentSolutionPackage 或 RejectionDecision | 用户确认责任和风险 |
| Learn | ProjectAsset 和 MetaAsset 提案 | 脱敏、复验、审计和回滚 |

通信渠道用于委派、讨论、质疑和人工介入；Project Dossier 是项目状态事实源；Trace 保存决策和执行证据。聊天内容只有被结构化写入后才能改变正式状态。

### 7.3 规范数据流

```text
RawMaterials
  → TaskSemanticSpec
  → CapabilitySemanticRegistry
  → CandidateGraphSet
  → EvaluationRunSet
  → SelectedSolution | RejectionDecision
  → AgentSolutionPackage
  → CrossProjectLearningRecord
```

## 8. 数据、版本、预算与安全约束

### 8.1 ProjectCase

每个正式项目必须建立：

```text
ProjectCase = {
  source_evidence,
  raw_materials,
  task_semantic_spec,
  capability_semantic_registry,
  task_capability_alignment,
  candidate_space,
  adaptation_set,
  validation_set,
  holdout_set,
  stress_and_failure_set,
  budgets,
  safety_constraints,
  evaluation_protocol,
  expected_artifacts,
  provenance_and_license
}
```

数据不能只做随机行切分。应按仓库、环境、任务族、文档模板、时间或其他真实分布边界隔离。

单项目使用：

```text
adaptation → validation → holdout
```

跨项目使用：

```text
meta-train projects → meta-validation projects → meta-test projects
```

### 8.2 版本与可复现

每次评测必须固定或记录：

- TaskSemanticSpec、能力和候选版本；
- 数据集、任务 ID、来源快照和哈希；
- 模型、Prompt、Embedding、算法和依赖版本；
- AgentTeams、Skill、MCP、工具和外部服务版本；
- 随机种子、预算、超时、最大步数和并发；
- 权限、审批、环境、镜像和部署配置。

### 8.3 预算与公平比较

候选之间必须使用可比的：

- 样例和输入材料；
- 模型与工具访问边界；
- token、API、工具调用和执行成本；
- wall-clock、步数、重试和并行预算；
- 安全门禁和人工参与规则。

架构不能通过未披露地增加 token、工具、模型或人工成本获得“胜利”。

### 8.4 安全和 Human 边界

所有候选遵循：

- 最小权限和明确数据范围；
- 密钥由基础设施持有，不进入 Agent 上下文；
- 外部写入、高风险动作和责任转移需要 Human 审批；
- 沙箱、超时、预算和最大循环次数；
- 失败、拒绝、人工接管、降级和回滚路径预先定义；
- 成功和失败证据同等保留；
- 共享资产晋升前脱敏、参数化、复验和审计。

Human 不是兜底文案，而是候选图中的能力和约束对象，必须具有触发条件、审批主体、输入输出、响应时限、拒绝和回滚记录。

## 9. 评测、Holdout、Trace 与审计

### 9.1 评价维度

至少评估：

- 任务正确性和关键子群表现；
- 泛化、稳定性、重试和失败恢复；
- 成本、时延、步数、资源和人工投入；
- 权限、数据、外部副作用和回滚；
- Trace 完整性、证据质量和可复现性；
- Agent、Skill、模型和能力节点的边际价值；
- adaptation、validation 和 holdout 差距；
- 人工接管质量和最终责任边界。

### 9.2 Trace 与独立审计

ExecutionTrace 至少包含：

```text
task_spec_version
candidate_version
episode_and_step
agent_identity
input_and_state_refs
decision_and_reason_code
tool_or_skill_call
permission_and_approval
output_and_artifact_refs
cost_latency_and_errors
retry_fallback_and_rollback
```

AgentArchitect 不得使用 holdout 定向修改候选。ValidationEngineer 执行隔离评测；GovernanceAuditor解释留出、安全、复杂度和证据；EngagementLead只能基于审计产物做外循环和交付决定。

### 9.3 失败与停止

压力和失败集应覆盖工具超时、权限拒绝、错误输入、环境故障、数据漂移、循环失控、成本超限、审批缺失、错误写入和回滚失败。

满足以下任一条件可以停止：

1. 达到全部硬阈值且没有更简单的等价候选；
2. 连续若干代没有足够边际改进；
3. 达到预算、时间或复杂度上限；
4. 核心能力缺口无法在授权范围内补齐；
5. holdout 暴露不可接受风险；
6. 人工责任无法安全转移；
7. 新 Agent 的成本和风险高于收益。

停止必须输出明确的部署、部分自动化、降级、保留人工或拒绝决定，而不是隐藏失败。

## 10. 项目交付物与成长资产

### 10.1 AgentSolutionPackage

```text
AgentSolutionPackage = {
  task_spec_version,
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

方案还必须包含 ArchitectureDecision，能够回答：

```text
为什么这样理解任务
→ 为什么选择这些能力
→ 为什么形成这张图
→ 为什么这些子图需要或不需要 Agentize
→ 为什么该候选优于更简单或更复杂的候选
→ 为什么可以部署、必须降级或应该拒绝
```

### 10.2 ProjectAsset

单项目可以沉淀：

- 任务和能力语义版本；
- 经验证的能力组合和候选图；
- Agentize、拆分、合并和拒绝决策；
- Skill、Prompt、阈值、算法和预算配置；
- 评测、故障、审批和回滚模板；
- 失败模式和无收益复杂度；
- Trace、报告和来源链。

ProjectAsset 默认只有项目作用域，不能直接成为全局能力。

### 10.3 MetaAsset

经跨项目复验后晋升的 MetaAsset 必须记录：

- 稳定 ID、语义和实现版本；
- 来源项目和证据；
- 适用任务分布和不适用条件；
- 参数槽、默认值和允许范围；
- 跨项目成功与失败结果；
- 污染、负迁移和无先验 baseline 比较；
- 回归样例、降级、回滚和上一稳定版本。

## 11. v0 跨场景项目集与迁移验证

v0 的目标不是同时实现六个产品，而是建立能够区分不同结构选择的训练和评测项目集。

| 项目 | 结构作用 | 当前条件 |
|---|---|---|
| `swe-bench` | 补丁和测试反馈，比较 Workflow、单 Agent和模块化候选 | 使用适合比赛资源的仓库级小切分 |
| `aiopslab` | 状态反馈、故障注入和运维闭环 | 冻结低风险本地 kind 任务 |
| `itbench` | 未见运维环境和迁移目标 | 选择本地可复现场景并披露依赖 |
| `tau-bench` | 策略约束、状态写入和 Human 门禁 | 实现前核验当前 τ³-bench 版本与许可证 |
| `gaia` | 开放工具研究和条件式并行 | 核验许可证并冻结易漂移证据 |
| `contract-nli` | 固定 Workflow 和 Agentless 强基线 | 建立证据、弃权和法律专家复核边界 |

该清单仍处于提案状态。审批后才可创建完整 ProjectCase；优先实施顺序必须根据比赛时间、资源和许可再次门禁，而不是把六个项目同时开工。

首个迁移假设为：

```text
AIOpsLab → ITBench
```

可迁移先验包括 detection/localization/analysis/mitigation 分解、Trace 和 Evaluator Schema、故障分类、安全动作边界和候选初始化。

预期收益是比 ITBench target-from-scratch 搜索使用更少的架构或 Prompt 试验、评测 Episode、token 或工具成本达到可接受候选。必要条件是在相同预算的 sealed ITBench holdout 上，任务成功、安全和审计完整性均不低于 target-from-scratch。

一组迁移成功只构成迁移证据；只有多项目轨迹更新搜索先验，并在未见 meta-test 项目上稳定改善，才能形成 Meta-learning 结论。

## 12. 比赛映射与证明责任

### 12.1 比赛价值主张

AgentFit 的差异不是“又一个多 Agent 框架”，而是：

1. 从原始材料和业务目标编译任务与能力语义；
2. 将 Agent 方案设计转化为受约束的图和分区搜索；
3. 在同一任务上比较 Agentless、单 Agent和多 Agent；
4. 同时优化效果、成本、风险、稳定性和可审计性；
5. 通过未见项目验证跨项目先验是否真正产生价值。

### 12.2 官方要求映射

| 官方关注点 | AgentFit 证明对象 |
|---|---|
| 不少于三个不同职能 Agent | 五个常驻元 Agent 的 Identity、责任产物和协作 Trace |
| AgentTeams 为协同基点 | 角色、房间、任务、状态、上下文、Worker、Human 和 Trace 的真实映射 |
| Skill 工程和复用 | 语义编译、对齐、候选生成、试验、评测、审计 Skill 的契约、版本、失败和复用证据 |
| 上下文机制 | Project Dossier 共享状态和 ExecutionTrace 轨迹可观测；效果必须评测证明 |
| 工具与 MCP | 版本、Schema、权限、鉴权、错误、幂等、降级、替代方案和审计 |
| 高风险动作 | Human 审批、拒绝、回滚、责任和完整 Trace |
| 工程和安全 | 可复现入口、依赖、配置、故障、成本、权限和证据包 |
| 开放贡献 | 可复用 Schema、Skill、评测、示例、文档、许可证和维护计划 |

### 12.3 初赛材料

初赛至少需要：

- 500 字以内作品简介；
- 方案 PPT/PDF；
- Agent Identity 清单；
- Skill 清单；
- AgentTeams 协同和上下文设计；
- 当前进展与未完成范围；
- 可复现、依赖、数据、模型、许可证和维护计划；
- 至少一种 PoC、实验、仿真、Trace、视频或等价证据。

多 Agent、Skill 和云产品不按数量获胜。每项都必须说明必要性、接口、可替换性、权限、失败、迁移成本和闭环证据。

### 12.4 红线

禁止：

- 把概念图或本地模拟写成真实运行；
- 把 AgentTeams 名称当作集成证据；
- 隐瞒既有仓库、第三方贡献、商业 API 或闭源模型；
- 未披露数据授权、许可证、密钥、权限和依赖；
- 高风险动作没有审批、拒绝、回滚和审计；
- 只展示成功，不保留失败、降级和否决；
- 比赛材料与内部证据状态不一致。

## 13. 当前未实现范围与下一门禁

当前没有证据表明以下能力已经完成：

- `TaskSemanticSpec` 和 `CapabilitySemanticSpec` 的正式机器可执行 Schema；
- Task–Capability Alignment 的可执行覆盖、冲突和缺口算法；
- Agentize 必要性和复杂度代价判定；
- 自动候选生成、内外循环搜索和 Pareto 选择；
- ProjectAsset/MetaAsset 的正式存储、晋升和回归系统；
- 任一完整 ProjectCase；
- 真实 AgentTeams 元团队、Skill、MCP、共享状态和 Trace；
- 统一预算下的 Agentless、单 Agent、多 Agent真实对照；
- AIOpsLab 到 ITBench 的真实迁移收益；
- 真实业务或生产效果。

下一门禁不是扩展总体概念，而是：

1. 审批或调整 v0 项目集和首个正式 ProjectCase；
2. 冻结该 ProjectCase 的来源、版本、数据划分、预算和安全边界；
3. 形式化 Task/Capability/Alignment/Candidate/Trace Schema；
4. 在 AgentTeams 上实现最小的元团队闭环；
5. 完成 Agentless、单 Agent和多 Agent统一对照；
6. 只有形成真实证据后，才派生比赛简介、PPT 和 Demo。

## 14. 规范引用

当前规范只引用以下事实和契约材料：

- [GOAI Agent Infra 初赛要求矩阵](internal/competition/preliminary-requirements-matrix.md)
- [GOAI Agent Infra 初赛红线与声明检查表](internal/competition/preliminary-red-line-checklist.md)
- [Evidence Research](internal/evidence-research/README.md)
- [Evidence Registry](internal/evidence-research/evidence-registry.json)
- [ProjectCase Contract](internal/cross-scenario-project-suite/project-case-template.md)
- [v0 Selection Matrix](internal/cross-scenario-project-suite/v0-selection-matrix.md)
- [v0 Selection Rationale](internal/cross-scenario-project-suite/v0-selection-rationale.md)
- [v0 Manifest](internal/cross-scenario-project-suite/v0-manifest.json)
- [《新智基座》Agent Infra 参赛手册](reference/新智基座-参赛手册.pdf)

`docs/archive/` 中的文件只用于追溯决策历史。它们可以解释本方案如何形成，但不能覆盖本文件的当前定义。
