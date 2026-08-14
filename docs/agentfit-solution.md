# AgentFit 整体方案

> 文档地位：唯一当前有效的整体方案
>
> 最近收敛：2026-08-14
>
> 当前阶段：唯一初赛提交版本已冻结；真实 AgentFit 运行保持 `NOT_STARTED`，后续是否启动由晋级结果与赛事反馈决定

## 1. 文档地位与当前状态

本文件统一 AgentFit 的产品定位、方法论、系统边界、责任闭环、评测治理、交付结果和阶段门禁。后续设计与实现必须以本文件为准；旧方案只存在于 Git 历史中，不构成并行方案。

当前证据状态分为五层：

| 层级 | 当前状态 | 可以对外表述 | 不可以对外表述 |
|---|---|---|---|
| 整体方案与设计契约 | `READY` | 产品定义、方法、五元团队、Skill、Human 与风险边界已收敛 | 已经自动生成或优化了真实 Agent 方案 |
| 初赛材料 | `READY` | 500 字以内简介、12 页主路演、5 页附录，以及 PPTX/PDF 的结构、内容、可编辑性、几何和视觉检查已完成 | PPT 中的设计图等于运行证据 |
| AgentTeams 平台试用 | 已有独立 smoke test | Worker、Team、Human、文件同步、定时任务等底座能力曾被单独试用 | 历史平台测试等于 AgentFit 已集成 |
| retail / airline 探索性 Demo | 有限探索证据 | DeepSeek + OpenCode、本地路径与自建工具/代理评估器可用于发现设计问题 | 官方 τ³-bench 成绩、正式 Candidate、统一候选对照或生产效果 |
| AgentFit 真实运行 | `NOT_STARTED` | 运行合同和启动条件已定义 | 已经批准或启动 walking skeleton，或已跑通 ProjectCase、候选评测、跨项目学习 |

初赛材料以[唯一提交目录](../competition/2026-08-15/submission/)为准；真实 AgentFit 运行状态、AgentTeams 边界和后续启动条件以本文件第 3、7、8、13 节为准。

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

> AgentFit 是面向 AgentTeams 构建的 Agent 方案建筑师。企业提供业务材料、代表性案例和用户优先级；AgentFit 从简单方案开始，在案例中运行、依据证据调整完整方案、用新案例验证，并交付最小充分的已验证方案包，也允许保留人工或拒绝自动化。

AgentFit 不预设多 Agent 更好，也不以 Agent 数量为优化目标。它交付的是满足任务、成本、安全和责任约束的最小充分方案。

AgentFit 把机器学习中“样本构建、批量试验、误差分析和验证停止”的工程范式引入 Agent 方案设计；调整的不是模型权重，而是完整 Agent Solution 的组成与边界。用户定义目标权重、验收门槛、预算和 Human 边界，AgentFit 只在这些冻结约束内探索、比较并收敛方案。

### 2.3 产品、工程表示与研究类比

| 层级 | 回答的问题 | 冻结表述 |
|---|---|---|
| 产品价值：Agent 方案建筑师 | 为用户解决什么 | 基于材料、案例和优先级，交付最小充分、可验收的方案 |
| 核心工程闭环 | 如何作出选择 | 定义案例与验收 → 构建简单方案 → 运行测量 → 分析调整 → 新案例验证并停止 |
| 机器学习工程纪律 | 如何让闭环易于理解 | 借鉴样本构建、批量试验、误差分析和验证停止；它不是产品名称、训练系统，自动优化器也不是当前能力 |

三者不是并列定位。对用户，AgentFit 提供的是方案工程与交付责任；机器学习工程纪律是比赛主线中的解释桥梁，严格候选表示仍服务于实现与审计。指标告诉系统“错了多少”，Trace 帮助定位“错在哪里”；`Simple First` 则以复杂度控制避免没有证据的过度设计。这里不声称 AutoML、反向传播，自动优化器也不是当前能力；任何跨项目学习仍是未来方向，不是当前能力。

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
- 将飞书或其他外部 IM 作为初赛提交依赖；
- 让优化器静默修改任务目标、验收标准或权限；
- 用本地模拟或历史平台试用替代真实 AgentFit 证据；
- 在没有跨项目未见集验证前宣称 Meta-learning。

## 3. AgentTeams、AgentFit 与 Human 的边界

| 主体 | 负责内容 | 不负责内容 |
|---|---|---|
| AgentTeams | 身份、Worker/Team/Human、房间与通信、容器、生命周期、共享存储、凭证和 Skill/MCP 绑定 | 决定某个业务任务应该采用什么 Agent 架构 |
| AgentFit | 任务与能力语义、能力对齐、候选生成、架构搜索、统一评测、审计、Human 门禁和交付 | 重造通用 Agent 运行时、IM、容器编排或企业 IAM |
| Human | 提供材料、确认任务契约、批准预算与高风险动作、处理责任边界、接受或否决交付 | 替 Agent 静默补证据、修改评测结果或承担未记录的兜底 |

后续工程若启动，采用“AgentTeams 原生底座 + AgentFit 能力包”：

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

## 4. 样本语义、任务语义、能力语义与 Agent 定义

### 4.1 语义编译

语义编译把自然语言、数据和系统事实转换为结构化、可比较、可计算和可审计的 AgentFit Semantic IR，而不是只做摘要或向量化。

LLM、Embedding、规则解析、Schema 映射、知识图谱、SVD、聚类、传统 ML 和人工标注都可以参与。大模型是实现手段之一；任何生成表示都不能覆盖原始证据或自动成为新事实。

### 4.2 七层映射

| 层级 | AgentFit 对象 | ML / 搜索含义 |
|---|---|---|
| L1 | Sample 语义 | 样本单位、实例空间、边界、重放与标注契约 |
| L2 | Task 语义 | 样本分布、目标、输出、损失、指标与权衡 |
| L3 | Capability 语义 | 可用算子、契约、权限、成本和适用域 |
| L4 | Candidate 表示 | 能力图、Agent 分区、参数与共享范围 |
| L5 | Inner Loop | 固定架构，在 adaptation samples 上优化局部参数 |
| L6 | Outer Loop | 在 validation samples 上比较和更新候选架构 |
| L7 | Cross-project Learning | 经未见项目验证后更新搜索先验 |

### 4.3 Sample 的对象层次

```text
SourceObservation = 原始业务观察
TaskSample = 当前任务契约下可独立冻结、重放、执行和评价的最小单位
Episode = 固定候选在固定 TaskSample 上的一次完整执行
EvaluationUnit = CandidateVersion × SampleVersion × RunIndex
```

`SourceObservation` 是告警、用户反馈、Issue、日志或工单等原始业务观察，保留来源与时间边界；是否构成可评价样本由当前任务契约决定。`TaskSample` 是当前 `TaskSemanticSpec` 下可独立执行和验收的单位，`Episode` 是固定候选在固定 `TaskSample` 上的一次完整运行轨迹，而不是输入样本。

Sample can be independently frozen, replayed, executed, and evaluated under one task contract. 因此 `ProjectCase != Sample`：前者描述任务分布、样本集合、候选空间、预算和评测协议，后者是其中一个具体评价单位。样本边界不得由候选运行时临时改变；从告警级改为事故级会创建新的 Sample 和 Task 版本，并重新批准试验。

`ProjectCase` 是一次完整方案选择的版本化试验合同，而不是一个示例或一个样本：

```text
ProjectCase = {
  project_case_id, version,
  source_evidence, sample_semantic_spec, task_semantic_spec,
  adaptation_manifest, validation_manifest,
  sealed_holdout_manifest, stress_and_failure_manifest,
  capability_boundary, candidate_space,
  trial_protocol, budgets, safety_constraints,
  approvals, audit_policy, delivery_contract
}
```

四份 `SampleSetManifest` 必须互异、不可变并各自具有版本、内容哈希与访问策略；Sample/Task 契约和四份 manifest 在候选生成前冻结，候选冻结后只有 GovernanceAuditor 可以解析 sealed-holdout 结果。

### 4.4 SampleSemanticSpec

`SampleSemanticSpec` 定义样本类型，而不是保存某条业务数据：

```text
SampleSemanticSpec = {
  sample_spec_id, version, task_spec_ref,
  sample_type, sample_level, unit_description,
  input_schema, context_schema, expected_output_contract,
  temporal_boundary, grouping_rule, identity_rule,
  label_or_oracle, replay_contract,
  metric_applicability,
  sensitivity_policy, provenance_requirements
}
```

`temporal_boundary` 限定可见事实以防止未来信息泄漏；`grouping_rule` 规定多条原始观察何时组成同一样本；`identity_rule` 规定稳定业务 ID 以避免重复计数；`label_or_oracle` 可以是自动标签、规则 Oracle、人工复核或仅契约验收；`replay_contract` 固定重放所需输入、环境快照、模拟器与允许的外部依赖；`metric_applicability` 说明单样本计算与跨样本聚合的指标边界。

### 4.5 Sample

`Sample` 是不可变、可寻址的具体实例：

Sample 是在特定任务契约下，可以被独立冻结、重放、执行和评价的最小业务语义单元。

```text
Sample = {
  sample_id, version, sample_spec_ref,
  source_observation_refs,
  input_snapshot_ref, input_hash,
  context_snapshot_ref, context_hash,
  expected_contract_ref,
  event_time, cutoff_time, grouping_keys,
  split, sensitivity, provenance,
  content_hash
}
```

sealed holdout 可以隐藏 `expected_contract_ref` 的实际内容，但必须保留由审计者解析的受控引用；候选、Prompt 和普通执行 Agent 不得读取该引用。

### 4.6 SampleSetManifest

数据划分使用版本化 `SampleSetManifest`，不再用模糊的“数据集”描述：

```text
SampleSetManifest = {
  sample_set_id, version, purpose,
  sample_spec_ref, sample_refs,
  selection_rule, distribution_summary,
  access_policy, frozen_at, content_hash
}
```

一个 ProjectCase 至少包含 `adaptation_set`、`validation_set`、`sealed_holdout_set` 和 `stress_and_failure_set`：adaptation 允许内循环查看输出和反馈；validation 用于候选选择和外循环更新；sealed holdout 仅供最终独立审计；stress and failure 覆盖错误输入、工具故障、权限拒绝、超时和不安全动作。相同 `content_hash` 不得跨集合出现；按事故、客户、仓库、环境、模板或时间相关的样本必须分组切分，不能把同一业务事件的近重复观察随机拆到不同集合。

### 4.7 SampleEvaluation

每个 Episode 必须记录样本级结果：

```text
SampleEvaluation = {
  candidate_version, sample_version, run_index,
  seed, environment_snapshot, budget_snapshot,
  result_ref, trace_ref, metric_values,
  status, failure_class, human_actions
}
```

项目级结果只能由样本级结果按预先冻结的聚合规则产生。平均值、成功率、成本、人工接管率和失败率必须同时记录分母、缺失样本、失败样本和适用范围，禁止只汇报成功 Episode。

### 4.8 TaskSemanticSpec

任务语义定义“要优化什么，以及什么结果才算解决”：

```text
TaskSemanticSpec = {
  spec_id, version, objective,
  sample_spec_ref, sample_distribution,
  expected_output, metrics, tradeoffs,
  acceptance_thresholds, aggregation_rules,
  budgets, risk_constraints, failure_costs,
  human_boundaries, evidence_requirements, provenance
}
```

候选比较期间任务契约必须冻结。目标、样本分布、指标、权衡、聚合规则或验收标准变化时，必须产生新版本、由责任人确认并重新执行比较；优化器不得为了让候选通过而降低门槛。`examples` 只能帮助理解，不能替代冻结的 Sample 契约或 SampleSetManifest。

### 4.9 CapabilitySemanticRegistry

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

### 4.10 Agent 的严格定义

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

### 4.11 任务—能力对齐

语义编译后必须生成 `AlignmentReport`，逐项记录：

- 完整覆盖、部分覆盖和未覆盖要求；
- 输入输出不兼容和能力冲突；
- 无法观测或验证的要求；
- 必须人工确认或需要更高权限的能力；
- 私有、团队、项目和全局共享范围；
- 进入候选生成前必须解决的缺口。

能力缺口不能通过虚构 Agent 名称掩盖。无法在授权范围内补齐时，应请求材料、缩小范围、保留人工或停止搜索。

## 5. 完整方案空间与候选表示

### 5.1 联合候选表示

```text
Candidate = (G, Π, θ, ρ)
```

- `G`：能力图，包含能力节点、数据边、控制边、状态依赖、DAG 主干和局部 SCC；
- `Π`：Agent 分区，决定哪些可执行子图拥有独立身份与责任；
- `θ`：模型、Prompt、Embedding、算法、阈值、重试、预算和局部策略；
- `ρ`：Skill、MCP、Memory、数据、状态和通信的私有与共享范围。

Agent 不是与 Skill 或 Tool 并列的普通节点，而是对能力子图施加身份、决策、状态、权限、生命周期和责任边界的分区。

因此，企业可见的“完整方案”不只是哪几个 Agent：Tool、Skill、MCP、Memory、Model、Agent 拓扑和 Human 边界都是可比较的方案变量。`Candidate = (G, Π, θ, ρ)` 是内部严格表示，不是对外产品名称；任何调整都不能绕过已冻结的案例、验收、权限、预算和 Human 门禁。

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

每增加一个 Agent、模型、工具、循环或共享范围，都必须在同一冻结 `SampleSetManifest`、同一版本化 `TaskSample`、相同模型与工具边界、预算、指标和安全门禁下证明边际价值。AgentFit 的常驻五元团队提供方案工程闭环；被设计的候选系统不为凑数量而拆分。

## 6. 调整、验证与工程类比边界

### 6.1 在固定方案内调整

在冻结的 Sample、任务契约和 Agent 边界不变时，可以调整局部节点或 SCC，例如 Prompt、模型、Embedding、特征、阈值、规则权重、检索、工具配置、Skill 选择、上下文压缩、重试和局部预算。固定候选在 adaptation SampleSet 上的完整处理可用于记录这一类调整。

内循环不得自行创建或销毁 Agent、扩大权限、改变责任边界或修改验收标准。

### 6.2 基于证据调整完整方案

基于 validation SampleSet、成本、复杂度、风险和审计结果，才可以调整整体候选：增删能力节点、改变拓扑、Agentize 或取消 Agentize、拆分或合并 Agent、改变通信与共享范围，以及在 Agentless、单 Agent、多 Agent 和 Human 混合之间迁移。

```text
固定方案内：比较局部调整的证据与代价
完整方案间：比较新案例上的验收、复杂度、成本、风险和不可观测性
```

正式实现尚未启动。未来可在明确授权后使用硬阈值、分层门禁、图搜索、规则或人工评审；这些是可选工程手段，不构成自动训练或优化系统的当前声明。

### 6.3 运行单位与术语类比

| 名称 | 定义 |
|---|---|
| Step | 一次推理、工具调用或环境反馈 |
| Episode | 一个固定候选在一个固定 TaskSample 上的一次完整执行 |
| 固定方案调整轮 | 固定候选完整处理一轮 adaptation SampleSet |
| 完整方案比较轮 | 一次候选生成、局部调整、validation SampleSet 比较和方案调整 |
| 跨项目资产复验 | 跨多个项目比较候选资产的适用边界 |

局部 SCC 的一次循环只是 Step。附录中可将上述层次与 ML 的 inner/outer loop 作高层工程类比，但不表示 AgentFit 已实现训练、反向传播或自动优化。

### 6.4 跨项目学习是未来方向

项目内调整和方案比较不是 Meta-learning。跨项目资产复用只有在多个项目轨迹更新可审计先验，并在未见项目上相对无先验 baseline 稳定改善时，才构成 Meta-learning 证据。

LLM、Embedding、SVD、图算法或其他方法都只是处理材料、比较方案或形成资产建议的可选技术手段，不能替代新案例验证或未见项目验证。

## 7. 五元 Agent 团队与责任闭环

### 7.1 常驻元团队

| Agent | 核心职责 | 独立责任产物 |
|---|---|---|
| EngagementLead | 接收任务、控制阶段、组织审批和交付 | Project Dossier 状态、ArchitectureDecision、DeliveryDecision |
| BusinessEngineer | 从原始材料定义样本单位、Schema、边界、分布、验收，编译任务语义和自动化边界 | SampleSemanticSpec、SampleSetManifest、TaskSemanticSpec |
| AgentArchitect | 盘点能力、对齐、建图和 Agent 分区 | Capability Registry、AlignmentReport、CandidateGraphSet |
| ValidationEngineer | 在 adaptation、validation 和 failure samples 上部署候选、执行可重放试验和故障注入 | SampleEvaluation[]、EvaluationRun、ExecutionTrace |
| GovernanceAuditor | 候选冻结后独占 sealed holdout 的解析、评价和泄漏检查 | Holdout EvaluationReport、审计结论 |

五个 Agent 具有独立目标、状态、决策、权限和责任产物，不是五个角色标签。`EngagementLead` 在后续运行中可映射到 AgentTeams Manager 或 Team Leader；其余四个角色使用独立 Worker，实际映射以固定版本的运行配置为准。

### 7.2 固定阶段骨架

```text
Intake → Discover → Freeze → Architect → Approve → Trial → Audit → Deliver → Learn
```

| 阶段 | 核心产物 | 门禁 |
|---|---|---|
| Intake | Project Dossier、范围和来源 | 责任人和材料来源明确 |
| Discover | SampleSemanticSpec、TaskSemanticSpec、adaptation/validation/sealed_holdout/stress_and_failure 四份 SampleSetManifest | 样本单位、边界、四份 manifest、输入、输出与验收可描述 |
| Freeze | Sample/Task 冻结版本、四份 manifest 与审批记录 | 样本/任务契约及四份互异 manifest 在候选生成前获 Human 批准并冻结 |
| Architect | Capability Registry、AlignmentReport、CandidateGraphSet、风险和预算 | 候选可执行且复杂度有理由 |
| Approve | TrialSpec、权限、预算和审批记录 | 候选生成后，试验范围、权限、预算与回滚单独获批 |
| Trial | 运行结果、Trace、故障和成本 | 输入、数据划分和预算受控 |
| Audit | EvaluationReport、选择或否决建议 | 审计输入与结论可独立追溯 |
| Deliver | DeliveryDecision；对应的 AgentSolutionPackage、HumanRetained 或 RejectionDecision | 用户确认责任和风险 |
| Learn | ProjectAsset；可选 MetaAsset 提案 | 脱敏、复验、审计和回滚 |

### 7.3 通信、状态与责任

通信渠道用于委派、讨论、质疑和人工介入；Project Dossier 是状态事实源；ExecutionTrace 保存决策与执行证据。

```text
RawMaterials + SourceObservations
  → SampleSemanticSpec + four distinct SampleSetManifests(adaptation, validation, sealed_holdout, stress_and_failure)
  → TaskSemanticSpec
  → HumanApproval(Sample/Task + four SampleSetManifests)
  → CapabilitySemanticRegistry + AlignmentReport
  → CandidateGraphSet
  → HumanApproval(TrialSpec + permissions + budgets)
  → SampleEvaluation[] + ExecutionTrace[]
  → EvaluationReport
  → DeliveryDecision
  → AgentSolutionPackage | HumanRetained | RejectionDecision
```

一个 Agent 不可用时，对应阶段保持未完成并记录失败；其他 Agent 不得静默冒充其责任产物。

### 7.4 后续阶段候选 walking skeleton

如后续阶段获准启动，只验证一条最小链路：

```text
Human 提交 RawMaterials + SourceObservations
→ EngagementLead 建立 Project Dossier
→ BusinessEngineer 产出 SampleSemanticSpec、TaskSemanticSpec 与 adaptation/validation/sealed_holdout/stress_and_failure 四份互异 SampleSetManifest
→ Human 在候选生成前批准并冻结 Sample/Task 契约与四份 SampleSetManifest
→ AgentArchitect 生成能力清单、缺口和 CandidateGraphSet
→ Human 在候选生成后单独批准 TrialSpec、权限和预算
→ EvaluationUnit = CandidateVersion × SampleVersion × RunIndex
→ ValidationEngineer 生成 SampleEvaluation[] + ExecutionTrace[]
→ GovernanceAuditor 独立审计
→ EngagementLead 输出 DeliveryDecision
```

该链路不是初赛提交前置条件，也不是当前已批准计划。若启动，允许人工触发阶段和创建资源，但不得人工口头补齐结构化产物、责任归属、候选输入、预算或审计结论。

## 8. Project Dossier、版本、预算与安全

### 8.1 Project Dossier

每个正式项目必须维护版本化 Project Dossier：

```text
ProjectDossier = {
  source_evidence, raw_materials,
  sample_semantic_spec, samples, sample_set_manifests,
  task_semantic_spec, capability_semantic_registry,
  alignment_report, candidate_graph_set,
  trial_specs, budgets, safety_constraints,
  sample_evaluations, evaluation_runs, execution_traces,
  aggregate_reports, audit_reports,
  approvals, delivery_decision, artifacts,
  provenance_and_license
}
```

数据应按仓库、环境、任务族、模板、时间或其他真实分布边界划分，而不是只做随机行切分。Project Dossier 先保存样本规格、样本、清单和样本级评价，再保存聚合报告；单项目必须包含 adaptation、validation、sealed holdout 和 stress and failure 四份互异的 SampleSetManifest，失败与压力样例不能只作为普通 validation 样本附带记录。

### 8.2 版本与可复现

每次试验必须固定或记录：

- SampleSemanticSpec、Sample、SampleSetManifest、TaskSemanticSpec、能力、候选和 TrialSpec 版本；
- 样本 ID、任务 ID、来源快照和哈希；
- 模型、Prompt、Embedding、算法和依赖版本；
- AgentTeams、Skill、MCP、工具和外部服务版本；
- 随机种子、预算、超时、最大步数和并发；
- 权限、审批、环境、镜像和部署配置。

### 8.3 预算与公平比较

候选必须使用同一冻结 `SampleSetManifest` 中的同一版本化 `TaskSample`，并共享相同模型与工具边界、token/API/工具调用预算、wall-clock、步数、重试、并行和 Human 规则。候选不能通过未披露地增加模型、工具、预算或人工投入获得“胜利”。

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

每一项指标都必须记录样本单位、分母、聚合规则、缺失样本和失败样本；聚合报告还必须标明适用范围。不得用只含成功 Episode 的均值、成功率、成本或人工接管率代替完整样本级结果。

### 9.2 ExecutionTrace

```text
ExecutionTrace = {
  task_spec_version, candidate_version,
  sample_version, run_index, episode_and_step,
  agent_identity,
  input_and_state_refs, decision_and_reason_code,
  tool_or_skill_call, permission_and_approval,
  output_and_artifact_refs, cost_latency_and_errors,
  retry_fallback_and_rollback
}
```

Trace 必须能从结论回到输入、版本、决策、工具调用、审批和产物，也能从原始任务正向重放关键路径。

### 9.3 独立审计

AgentArchitect 不得使用 sealed holdout 定向修改候选。ValidationEngineer 只在 adaptation、validation 和 failure samples 上执行可重放隔离评测；GovernanceAuditor 在候选冻结后独占解析并评价 sealed holdout，任何基于 holdout 的候选修改都会使该轮结果失效；EngagementLead 只能基于审计产物作出交付决定。

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

### 12.2 2026-08-15 初赛提交阶段

本阶段只负责完成、验证和上传初赛材料，不把真实 AgentTeams 元团队或 walking skeleton 作为提交前置。当前唯一提交版本包括：

- 不超过 500 个非空白字符的作品简介；
- 12 页主路演 + 5 页附录；
- 17 页 HTML-first、可编辑 PPTX 和同版 PDF；
- 五个 Agent Identity、七个核心 Skill、Human/风险门禁、开放与合规披露；
- 自动合同、结构、逐页内容、原生可编辑性、几何和视觉复核。

OpsPilot 代码级审计、ProjectCase 设计和事故样本只作为方案依据；真实五元团队和统一候选对照尚未完成，不得伪装为运行证据。

### 12.3 后续阶段

初赛提交后暂停扩展性开发。是否进入 AgentTeams walking skeleton、复赛工程或跨项目试验，由晋级结果、评审反馈和后续赛程共同决定；在出现新的赛事条件与明确授权前，只保留启动门禁，不把后续设想写成已启动计划。

### 12.4 官方关注点映射

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

### 12.5 红线

禁止：

- 把概念图、设计模拟或历史 smoke test 写成 AgentFit 真实运行；
- 把 AgentTeams 名称或底座能力当作集成证据；
- 把 Meta-learning、自动搜索或生产收益写成当前能力；
- 隐瞒既有仓库、第三方贡献、商业 API、闭源模型、数据来源或许可证；
- 让高风险动作绕过审批、拒绝、超时、回滚和审计；
- 只展示成功，不保留失败、降级、人工保留和否决；
- 让比赛材料与内部证据状态不一致。

## 13. 当前未实现范围与 AgentTeams 后续运行门禁

### 13.1 当前未实现

当前没有证据表明以下能力已经完成：

- SampleSemanticSpec、Sample、SampleSetManifest、SampleEvaluation、SplitLeakagePolicy、SplitLeakageReport、TaskSemanticSpec、CapabilitySemanticSpec、AlignmentReport、Candidate、CandidateGraphSet、TrialSpec、EvaluationRun、ExecutionTrace、EvaluationReport、DeliveryDecision 的正式机器可执行 Schema；
- Task–Capability 覆盖、冲突和缺口算法；
- Agentize 必要性、复杂度代价和自动候选搜索；
- ProjectAsset/MetaAsset 正式存储、晋升和回归系统；
- 任一完整、冻结的真实 ProjectCase；
- AgentFit 五元团队、Skill、MCP、共享状态和 Trace 的真实 AgentTeams 集成；
- 统一预算下的 Agentless、单 Agent和多 Agent真实对照；
- 跨项目迁移收益、Meta-learning、生产部署或真实业务效果。

### 13.2 后续运行启动条件

后续工作不会因初赛提交自动启动。只有晋级结果、评审反馈或新的赛事安排证明值得继续，并得到明确授权后，才在 AgentTeams 上选择一个首个 ProjectCase，执行第 7.4 节的最小 walking skeleton；在此之前不得写成已批准测试项目。

可声称“AgentFit 已在 AgentTeams 跑通最小闭环”，必须同时满足：

1. 五个 Agent 具有可检查身份、独立责任和独立产物；
2. 一个冻结 ProjectCase 从 Intake 流转到 Deliver；
3. 至少执行一个真实候选，并保留输入、输出、版本、模型、工具、用量和 Trace；
4. 至少保留一个失败、降级、拒绝或 Human 门禁分支；
5. GovernanceAuditor 的审计输入与结论可独立追溯；
6. 固定 AgentTeams 版本、配置、已验证能力和未验证边界；
7. 能在干净环境按仓库说明复现。

### 13.3 后续最小实施顺序与阶段完成定义

以下顺序只在第 13.2 节第一段的外部授权条件满足后生效。每个里程碑必须独立验收；前一阶段未完成时，不得用后一阶段的界面、自动化或演示材料替代缺失证据。

| 里程碑 | 实施内容 | 阶段完成定义 |
|---|---|---|
| M0 · 启动授权与基线冻结 | 记录赛事条件、授权范围和首个 ProjectCase；固定 AgentTeams 版本、运行入口、可用能力和未验证边界；冻结本阶段代码与材料基线 | 存在审批记录、ProjectCase 选择理由、版本清单和可复现的 AgentTeams 基线；只能声明“已获准启动”，不能声明已运行闭环 |
| M1 · 手动可审计 walking skeleton | 先使用 AgentTeams 原生 Worker、Team、Room、Human、Skill/工具和共享存储实例化五元团队；允许人工触发阶段，但必须写出第 7.4 节规定的结构化产物 | 一个冻结 ProjectCase 在当前环境从 Intake 到 Deliver；执行至少一个真实候选，并保留至少一个失败、降级、拒绝或 Human 门禁分支。M1 只证明当前环境首次贯通，不构成可复现最小闭环完成声明 |
| M2 · 确定性合同代码化 | 只把 M1 暴露的真实缺口固化为 Schema、版本/哈希、阶段状态机、四份 manifest 的冻结与访问策略、审批、预算和 Trace 校验；继续复用 AgentTeams 运行能力 | 机器校验可以拒绝非法状态推进、holdout 越权、版本漂移、预算越界和缺失审批；候选冻结后只有 GovernanceAuditor 可以解析 sealed holdout；同一 M1 ProjectCase 可在不依赖口头补证据的情况下重放 |
| M3 · 统一候选对照 | 在同一冻结 Sample/Task、四份 manifest、模型/工具边界、预算、指标和 Human 规则下比较候选 | 必须真实运行 Agentless、单 Agent 和多 Agent 三类候选；Human 混合候选必须真实运行，或由 GovernanceAuditor 记录不适用理由、证据与重新评估条件。每个 `EvaluationUnit = CandidateVersion × SampleVersion × RunIndex` 均有 SampleEvaluation 和 Trace；候选冻结后只有 GovernanceAuditor 可以解析 sealed holdout；报告同时呈现成功、失败、成本、风险与人工投入，并形成可追溯的 DeliveryDecision，不预设多 Agent 胜出 |
| M4 · 复现与比赛证据包 | 在干净环境复现选定 ProjectCase，固定依赖、配置、模型、工具、预算和运行入口；汇总日志、Trace、审批、失败、审计与交付产物 | 独立复现得到同一合同边界下的结论；比赛声明可逐项反向定位到仓库产物，完成态只依据可复现证据更新。独立复现成功且第 13.2 节七项完成门禁全部满足后，才可声明“AgentFit 已在 AgentTeams 跑通最小闭环” |

M0–M4 是单项目落地顺序，不等于跨项目 Meta-learning。只有多个 ProjectAsset 经过第 11 节的脱敏、迁移、未见项目比较和独立审计后，才允许进入 MetaAsset 或 Meta-learning 工作。

### 13.4 代码边界判定

后续验证若获准启动，只有以下内容应优先固化为 AgentFit 代码：

- Schema 校验和版本约束；
- 阶段状态、审批主体和失败状态的确定性门禁；
- 数据划分与候选预算隔离；
- Trace、依赖、模型和版本的自动记录；
- 高风险动作的拒绝、审批、超时与回滚；
- 评测汇总和比赛声明到内部证据的反向定位。

AgentFit 不开发独立 UI、不修改 AgentTeams 核心，也不自建通用运行平台。真实试验只用于确定哪些 AgentFit 领域约束需要通过配置、Skill、工具、MCP、适配层或仓库内代码固化。

## 14. 规范引用

- [初赛提交入口](../competition/2026-08-15/README.md)
- [最终初赛提交](../competition/2026-08-15/submission/README.md)
- [Agent Identity 清单](../competition/2026-08-15/submission/agent-identity.md)
- [核心 Skill 清单](../competition/2026-08-15/submission/skill-catalog.md)
- [Human 与风险门禁](../competition/2026-08-15/submission/risk-and-human-gates.md)
- [开放与合规披露](../competition/2026-08-15/submission/openness-and-compliance.md)
- [GOAI Agent Infra 初赛要求矩阵](internal/competition/preliminary-requirements-matrix.md)
- [GOAI Agent Infra 初赛红线与声明检查表](internal/competition/preliminary-red-line-checklist.md)
- [Evidence Registry](internal/evidence-research/evidence-registry.json)
- [《新智基座》Agent Infra 参赛手册](reference/新智基座-参赛手册.pdf)

历史版本只通过 Git 提交记录追溯，不能覆盖本文件的当前定义、完成状态和证据边界。
