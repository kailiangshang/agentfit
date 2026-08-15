# AgentFit 整体方案

> 文档地位：唯一当前有效的整体方案
>
> 方案版本：v4（强层级映射纪律与场景内持续学习）
>
> 最近收敛：2026-08-15
>
> 当前阶段：唯一初赛提交版本已冻结；AgentTeams M0 已完成并为 `READY`，M1 已进入 `IN_PROGRESS`，M2–M4 仍为 `NOT_STARTED`

## 1. 文档地位与当前状态

本文件统一 AgentFit 的产品定位、方法论、系统边界、责任闭环、评测治理、交付结果和阶段门禁。后续设计与实现必须以本文件为准；旧方案只存在于 Git 历史中，不构成并行方案。

当前证据状态分为五层：

| 层级 | 当前状态 | 可以对外表述 | 不可以对外表述 |
|---|---|---|---|
| 整体方案与设计契约 | `READY` | 产品定义、方法、五元团队、Skill、Human 与风险边界已收敛 | 已经自动生成或优化了真实 Agent 方案 |
| 初赛材料 | `READY` | 500 字以内简介、12 页主路演、5 页附录，以及 PPTX/PDF 的结构、内容、可编辑性、几何和视觉检查已完成 | PPT 中的设计图等于运行证据 |
| AgentTeams 平台试用 | 已有独立 smoke test | Worker、Team、Human、文件同步、定时任务等底座能力曾被单独试用 | 历史平台测试等于 AgentFit 已集成 |
| retail / airline 探索性 Demo | 有限探索证据 | DeepSeek + OpenCode、本地路径与自建工具/代理评估器可用于发现设计问题 | 官方 τ³-bench 成绩、正式 Candidate、统一候选对照或生产效果 |
| AgentFit 真实运行 | M0 `READY`；M1 `IN_PROGRESS`；M2–M4 `NOT_STARTED` | 办公室基线固定 AgentTeams v1.1.2；2026-08-15 家庭实例因 v1.1.2 确定性 Team 房间配置缺陷（reconcile leader DM membership 403）经项目所有者决定改用 v1.2.0-beta.1 官方镜像，五元 Team `Active`、1 Leader + 4 Worker 运行、Human `Active`；已完成三轮 ProjectCase preparation（办公室 R1：task 0；R2：task 0/2/13 结构化验证 PASS；家庭 R3：task 0/2/13 终态 complete，106 事件，治理审查 SUCCESS 有条件） | 已运行 Candidate、候选评测、闭环、多 Agent 优势或跨场景学习 |

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

场景在 AgentFit 中被视为随时间演化的活分布，而不是静态数据集：样本持续流入、子场景持续分化。因此 AgentFit 不是一次性方案设计，而是伴随场景演化的持续学习循环——样本流驱动层级化的受控更新，旧能力受回归保护，漂移被检测、裁定和吸收。场景是方案的实例化参数，不是架构本身；同一套层级纪律、持续学习机制与追溯合同适用于故障诊断、零售、航空等任何可描述输入输出与验收的场景。

AgentFit 把机器学习中“样本构建、批量试验、误差分析和验证停止”的工程范式引入 Agent 方案设计；调整的不是模型权重，而是完整 Agent Solution 的组成与边界。用户定义目标权重、验收门槛、预算和 Human 边界，AgentFit 只在这些冻结约束内探索、比较并收敛方案。

### 2.3 产品、工程表示与研究类比

| 层级 | 回答的问题 | 冻结表述 |
|---|---|---|
| 产品价值：Agent 方案建筑师 | 为用户解决什么 | 基于材料、案例和优先级，交付最小充分、可验收的方案 |
| 核心工程闭环 | 如何作出选择 | 定义案例与验收 → 构建简单方案 → 运行测量 → 分析调整 → 新案例验证并停止；调整按层级离散化，更新算子按层白名单化 |
| 机器学习工程纪律 | 如何让闭环易于理解 | 借鉴样本构建、批量试验、误差分析和验证停止，并硬映射化：四层资产对应从数据基础设施到架构的离散层级，持续学习对应场景演化，回归池对应防遗忘回放；它不是产品名称、训练系统，自动优化器是可插拔工具而非自研目标 |

三者不是并列定位。对用户，AgentFit 提供的是方案工程与交付责任；机器学习工程纪律是比赛主线中的解释桥梁，严格候选表示仍服务于实现与审计。指标告诉系统“错了多少”，Trace 帮助定位“错在哪里”；`Simple First` 则以复杂度控制避免没有证据的过度设计。这里不声称 AutoML、反向传播，自动优化器是可插拔工具而非自研目标；场景内持续学习是当前设计语义，跨场景迁移仍是未来方向。

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
- 把场景内持续学习表述为跨场景 Meta-learning；跨场景迁移仍需未见场景验证，属远期方向；
- 自研 prompt、结构优化器或训练底座模型权重；既有优化器只作为内环可插拔工具接入；
- 追求对黑盒 LLM 节点的可微性或"文本梯度"式精确归因；AgentFit 的信用分配是层级离散的。

## 3. AgentTeams、AgentFit 与 Human 的边界

| 主体 | 负责内容 | 不负责内容 |
|---|---|---|
| AgentTeams | 身份、Worker/Team/Human、房间与通信、容器、生命周期、共享存储、凭证和 Skill/MCP 绑定 | 决定某个业务任务应该采用什么 Agent 架构 |
| AgentFit | 任务与能力语义、能力对齐、候选生成、架构搜索、统一评测、审计、Human 门禁和交付，以及四层资产治理与持续学习治理（回归保护、漂移裁定） | 重造通用 Agent 运行时、IM、容器编排或企业 IAM |
| Human | 提供材料、确认任务契约、批准预算与高风险动作、处理责任边界、接受或否决交付 | 替 Agent 静默补证据、修改评测结果或承担未记录的兜底 |

当前获准启动的工程采用“AgentTeams 原生底座 + AgentFit 能力包”：

- 使用 AgentTeams 已有 Dashboard、Manager/聊天入口、Worker、Team、Human、Skill、MCP、共享存储和通信；
- AgentTeams 固定 `v1.1.2`，使用官方预构建镜像运行，不执行镜像编译；AgentFit、Benchmark 适配器、场景模拟器、评测与诊断服务以源码方式维护和运行；
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

### 4.12 实体污染与语义复用

样本语料天然携带污染信息：同一实体（同名用户、同号订单、同一工单模板）会跨任务反复出现。这是数据集构造的产物，不构成任何复用证据。

- **实体键的唯一用途是泄漏控制**：按实体分组做近重复切分，防止同一业务事件的近似观察跨 split 污染（真实 retail 语料中存在同用户同订单跨任务的实例，已验证该风险非理论性）；
- **一切学习信号按语义计算**：复用率、缺口率、路由统计一律基于任务的语义结构——意图类型、归一化后的动作模式、约束形态——禁止按实体重合计数；
- **虚假复用的危害**：按实体计数会把语料污染误读为资产沉淀，导致复用率虚高、回归池代表性失真；语义复用才是 Solid 池边际成本递减的真实度量；
- 实体分组键作为版本化资产进入 manifest 的 `grouping_rule`，其变更需重新审计 split 有效性。

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

### 5.6 强层级映射纪律

完整方案空间按四层资产模型组织，层是离散化映射的载体，也是更新权限的边界：

| 层 | 资产 | 职责 | 共享范围 | 可变性 |
|---|---|---|---|---|
| L1 Solid | 固定资产/原子接口（知识库、查询、CMDB 等） | 通用原子访问；不提供复杂可配置参数，配置责任全部上移 | 全局 | 受控生长：观察区 + 升格门限 + 引用计数 + TTL；废弃走 deprecation |
| L2 Tool | source tool / MCP 封装 | 唯一合法触达 L1 的层；聚合、分析、切片的口径在此唯一定义 | 全局/项目 | 语义版本 |
| L3 Knowledge | Skill / Memory | 排查链、问题路由、人工门限等组合沉淀 | 项目（可晋升） | 可变；每次变更绑定证据并通过回归门 |
| L4 DAG | Agent 组合与流程（即 Π） | 独立决策、权限与责任分区 | 项目 | 结构变更需影子模式验证后切换 |

触达规则（全部由 schema 与 checker 代码强制，不依赖 prompt 自觉）：

1. 知识层不得直接调用 Solid 层，直连即层级违规；
2. 一切聚合、分析、切片操作必须经工具层 source tool 二次封装，原始加工口径全局唯一；
3. 知识层产出只供 Agent（L4）消费，知识资产之间不互相调用，防止知识层形成隐性 DAG；
4. 共享范围随层递减：Solid 全局共享但必须原子化，复杂参数即不可信组合；
5. Candidate 的每个能力节点必须携带 `layer` 标签，每条边必须满足触达规则；越层依赖在注册表校验时即被拒绝。

层内更新算子白名单——离散信用分配，取代对黑盒节点的梯度幻想：

| 层 | 合法更新算子 | 触发证据 |
|---|---|---|
| L1 Solid | 接口新增/废弃（原子粒度） | 批次样本暴露的接口需求缺口 |
| L2 Tool | source tool 参数与聚合口径调整 | 工具调用失败或口径不一致的 episode |
| L3 Knowledge | 链路重组、路由修正、人工门限调整 | 路由命中率、链路断点、修正样本 |
| L4 DAG | 拓扑增删、Agentize/合并、权限边界调整 | 验证集对照中的结构性失败 |

一次 episode 失败，ExecutionTrace 定位涉案资产所在层，只开放该层的更新算子，且更新必须引用证据（样本 ID、episode、指标差值）写入轮次记录。上层不得越层代改：工具层不得改接口定义，DAG 层不得改排查链内容。这是反向传播的离散等价物——误差沿层级单向归因，更新沿层级受限回传。

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
| 场景资产复验 | 跨批次在回归池上比较候选资产的适用边界与退化 |

局部 SCC 的一次循环只是 Step。附录中可将上述层次与 ML 的 inner/outer loop 作高层工程类比，但不表示 AgentFit 已实现训练、反向传播或自动优化。

### 6.4 场景内持续学习（取代跨项目 Meta-learning）

企业单个场景随时间演化：样本持续累积、子场景持续分化。一个场景内部的分布宽度已足以支撑资产演化，因此 AgentFit 的学习语义是**场景内持续学习**，不是跨场景迁移。

**样本类型学**——每个进入系统的样本首先被分类为一种学习信号，触发不同的更新路径：

| 类型 | 特征 | 触发的学习动作 | 主要影响层 |
|---|---|---|---|
| A 确认样本 | 现有方案正确处理 | 强化置信度，更新统计量 | L3 阈值微调 |
| B 修正样本 | 出错但根因在已知能力范围内 | 产出离散 Correction，定向修补 | L3 / L4 |
| C 扩展样本 | 需要新的原子接口/数据源才能解决 | 触发 Solid 升格流程 | L1 → L2 |
| D 重构样本 | 多个知识资产重叠/矛盾/碎片化 | 触发合并、拆分、抽象 | L3 |
| E 退役样本 | 某类问题长期未出现或系统下线 | 触发衰减、归档、级联清理 | 全层 |
| F 漂移样本 | 同类问题的表现或根因随时间变化 | 触发版本分叉或条件分支 | L3 + L4 |

样本分类器本身是版本化组件，受同一纪律治理：其修正属于 B 类信号作用于自身，必须过回归门，不得成为游离于审计之外的隐形优化器。

**各层持续学习机制**：

- **L1 受控生长与修剪**：候选接口先进观察区（带计数器），达到升格门限 N 才进入正式池；正式接口有引用计数与 TTL，长期无引用降级归档；语义高度重叠的接口触发合并提案（人工确认）。生长门限防止噪声样本污染全局池。
- **L2 适配演化**：Solid 升格时自动生成 source tool 骨架；知识层重构后检查无消费者的工具标记待清理。
- **L3 增量更新与冲突消解（主战场）**：B 类样本产出带证据链的定向 Correction。新 Correction 与既有规则冲突时按序消解：证据强度优先 → 条件分叉（两者适用不同子场景）→ 漂移确认后的时序覆盖 → 人工仲裁。**时序优先仅在漂移被独立裁定后合法**，防止"最新即最对"被噪声利用。防遗忘双机制：RegressionPool（核心样本回放，见 §11）+ 离散弹性权重（高频高置信节点修改阻力更高，需要更强证据）。周期性离线重构（consolidation）：聚类分析知识资产重叠、合并相似项、重组路由——在线学习负责可塑性，离线重构负责稳定性。
- **L4 影子模式**：结构变更候选并行运行不生效，输出差异达标并通过回归门后才切换。

**免疫系统**（持续学习的安全边界）：

| 机制 | 防什么 | 实现方式 |
|---|---|---|
| 回归守卫 | 灾难性遗忘 | RegressionPool 回放 + 自动回归 |
| 膨胀熔断 | 知识/接口熵增 | 数量上限 + 增长率告警 |
| 漂移探针 | 语义漂移 | 定期探针样本检验关键资产输出一致性 |
| 修改阻力梯度 | 过度敏感 | 高频高置信节点更高修改门槛 |
| 人工兜底环 | 自动化失控 | 低置信修正、冲突、结构变更 → 人工审批 |
| 回滚快照 | 不可逆损害 | 重大更新前自动快照，一键回退 |

**多速率演化**：四层更新速率天然不同——L4 最快（参数微调）、L3 中速（增量 + 周期重构）、L2 慢速（跟随上下两层）、L1 最慢（强治理）。底层稳定提供锚点，上层灵活适应变化；若所有层同速更新，要么整体僵化，要么整体失控。

**持续学习度量**：Forward Transfer（学新后旧核心样本通过率变化）、Backward Transfer（负值即遗忘）、Solid 复用率与缺口率趋势、知识碎片度、修正命中率、人工介入率趋势、漂移检测延迟。所有指标按 §4.12 的语义口径计算，实体重复不计入任何复用统计。

跨场景迁移保留为远期方向：只有多个场景的资产轨迹更新可审计先验、并在未见场景上相对无先验 baseline 稳定改善时，才构成跨场景 Meta-learning 证据；AgentFit 当前不预设跨场景项目集。

## 7. 五元 Agent 团队与责任闭环

### 7.1 常驻元团队

| Agent | 核心职责 | 独立责任产物 |
|---|---|---|
| EngagementLead | 接收任务、控制阶段、组织审批和交付 | Project Dossier 状态、ArchitectureDecision、DeliveryDecision |
| BusinessEngineer | 从原始材料定义样本单位、Schema、边界、分布、验收，编译任务语义和自动化边界，并做批级 Solid 需求抽象（接口缺口、语义复用率） | SampleSemanticSpec、SampleSetManifest、TaskSemanticSpec、Solid 需求清单 |
| AgentArchitect | 盘点能力、对齐、建图和 Agent 分区 | Capability Registry、AlignmentReport、CandidateGraphSet |
| ValidationEngineer | 在 adaptation、validation 和 failure samples 上部署候选、执行可重放试验和故障注入 | SampleEvaluation[]、EvaluationRun、ExecutionTrace |
| GovernanceAuditor | 候选冻结后独占 sealed holdout 的解析、评价和泄漏检查，并审计层级触达纪律与实体污染控制 | Holdout EvaluationReport、审计结论 |

五个 Agent 具有独立目标、状态、决策、权限和责任产物，不是五个角色标签。团队的常驻性由持续学习语义直接论证：场景是活分布，样本流、漂移裁定、回归守护和资产演化是持续性职责，一次性项目制无法承载。`EngagementLead` 在后续运行中可映射到 AgentTeams Manager 或 Team Leader；其余四个角色使用独立 Worker，实际映射以固定版本的运行配置为准。

### 7.2 固定阶段骨架（持续学习的单轮骨架）

九阶段描述一个 ProjectCase 的单轮流转；在持续学习语义下，它是 §6.4 大循环（样本分类→层内更新→回归验证→资产沉淀→漂移触发新一轮）的一个周期，不是项目的终点。

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
| Learn | BatchAsset/ScenarioAsset 沉淀、RegressionPool 更新、ScenarioLedger 追加 | 实体去重、回归验证、审计和版本化 |

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
  regression_pool_ref, scenario_ledger_ref,
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
- 人工接管质量和最终责任边界；
- 持续学习指标：Solid 复用率与缺口率趋势、Forward/Backward Transfer（回归池前后通过率差）、知识碎片度、修正命中率、人工介入率趋势、漂移检测延迟；实体重复不计入任何复用统计（见 4.12）。

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
  asset_versions_and_rollback,
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

## 11. 场景内持续学习资产

### 11.1 资产演化语义

每个已交付 ProjectCase 沉淀 BatchAsset：任务与能力语义、经验证的候选图、Agentize 决策、Skill/Prompt/算法配置、Solid 需求增量、评测模板、失败模式、审批回滚和 Trace。BatchAsset 累积为 ScenarioAsset——场景在某时点的完整资产状态。

各层资产的版本化语义：

| 资产 | 演化语义 |
|---|---|
| SolidPool | append + deprecation，永不静默删除；生长经观察区与升格门限 |
| SourceTool | 语义版本；聚合口径变更即 minor 提升，通知全部引用方 |
| Knowledge 资产 | 可变；每次变更绑定（证据引用 + RegressionPool 回归结果） |
| Candidate | 不可变；每次交付即冻结版本，回滚等价于重部署历史版本 |

### 11.2 RegressionPool（回归池，一等合同）

RegressionPool 是防灾难性遗忘的核心机制，与四份 SampleSetManifest 并列的版本化对象：

- 构成：已交付 ProjectCase 的冻结样本，按子场景分层抽样，版本化并带内容哈希；
- 强制门禁：任何 L2/L3/L4 资产更新，必须先在 RegressionPool 上全量回归；老子场景通过率下降即 FAIL，要么回滚（资产版本化使回滚等价于重部署历史 candidate_version），要么携带证据走人工门禁修复；
- 净化：池内样本按 §4.12 做实体去重，防止虚假复用扭曲回归代表性；
- 双重身份：回归池既是安全机制也是"分布增量 vs 近重复回归"的判定素材——与历史实体高度重合的新批次优先作为回归验证，而非拟合输入。

### 11.3 ScenarioLedger（场景演化账本）

ProjectCase 之间以 hash 链连接：每条 ScenarioLedger 记录引用前一条的哈希、本 case 的资产版本指针、复用率/缺口率/回归通过率等指标。断链即不可审计。逐批次的复用率与缺口率曲线（设计推演中已用 114 个公开 retail 任务验证：接口池从 9 增长到 15 后复用率稳定在 1.00）是资产沉淀边际成本的直接度量，也是漂移检测的监控对象——缺口率从 0 回升即为"场景长出新形态"的信号。

### 11.4 当前边界

场景内持续学习是当前设计；RegressionPool 与 ScenarioLedger 的机器校验属 M2 范围。跨场景迁移保留为远期方向：只有多个场景的资产轨迹更新可审计先验、并在未见场景上相对无先验 baseline 稳定改善时，才构成跨场景 Meta-learning 证据；在此之前任何表述不得使用 Meta-learning 一词。后续运行库计划开源，开源范围与许可证见开放与合规披露。

## 12. 比赛映射与事实红线

### 12.1 比赛价值主张

AgentFit 的差异不是“又一个多 Agent 框架”，而是：

1. 从原始材料和业务目标编译任务与能力语义，并抽象 Solid 层接口需求；
2. 将 Agent 方案设计转化为受四层触达纪律约束的图和分区搜索；
3. 在同一任务上比较 Agentless、单 Agent、多 Agent和 Human 混合；
4. 同时优化效果、成本、风险、稳定性和可审计性；
5. 以场景内持续学习吸收样本流演化：回归池防遗忘、漂移探针防语义漂移、膨胀熔断防熵增；
6. 不依赖对黑盒节点的可微性假设——信用分配层级离散、证据驱动、可机器审计。

### 12.2 2026-08-15 初赛提交阶段

本阶段只负责完成、验证和上传初赛材料，不把真实 AgentTeams 元团队或 walking skeleton 作为提交前置。当前唯一提交版本包括：

- 不超过 500 个非空白字符的作品简介；
- 12 页主路演 + 5 页附录；
- 17 页 HTML-first、可编辑 PPTX 和同版 PDF；
- 五个 Agent Identity、七个核心 Skill、Human/风险门禁、开放与合规披露；
- 自动合同、结构、逐页内容、原生可编辑性、几何和视觉复核。

OpsPilot 代码级审计、ProjectCase 设计和事故样本只作为方案依据；真实五元团队已经实例化并完成两轮 ProjectCase preparation，但统一候选对照尚未运行，不得把 preparation 结果伪装为 Candidate 或闭环证据。

### 12.3 后续阶段

初赛提交材料仍与真实运行证据隔离，不把 M0/M1 作为上传前置。2026-08-14，项目所有者已明确授权按第 13 节启动 AgentTeams M0，并在 M0 通过后进入 M1；当前 M0 已完成、M1 已实例化五元 Team 并进入 `IN_PROGRESS`。复赛扩展、M2–M4、场景内持续学习工程和生产部署仍需以晋级结果、评审反馈、运行证据与后续授权为准。

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
- 把跨场景 Meta-learning、自动搜索或生产收益写成当前能力；
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
- RegressionPool、ScenarioLedger、BatchAsset/ScenarioAsset 存储与校验系统；
- 任一完整、冻结的真实 ProjectCase；
- AgentFit 五元 Team 已真实实例化，并完成两轮 ProjectCase preparation、结构化 Dossier 导出及 Team/Leader-DM Trace 合并；Skill/工具运行绑定、正式 manifest 实例化与冻结、Project Dossier 持久共享状态和 Candidate 执行尚未完成；
- 统一预算下的 Agentless、单 Agent和多 Agent真实对照；
- 跨场景迁移收益、生产部署或真实业务效果。

### 13.2 后续运行启动条件

启动门禁已于 2026-08-14 由项目所有者明确放行。当前采用“AgentTeams `v1.1.2` 官方预构建镜像 + AgentFit 源码 + 外部 Benchmark/评测源码服务 + OpenAI-compatible 模型 API”的运行方式；办公室实测连接 LiteLLM，家庭环境可直连 DeepSeek，不修改 AgentTeams 核心，不执行镜像编译。当前真实状态为：M0：`READY`；M1：`IN_PROGRESS`；M2–M4：`NOT_STARTED`。M0 已固定官方镜像 tag 与 digest、运行入口、首个 ProjectCase、LiteLLM/Manager smoke 和本地证据完整性；镜像内 CLI 版本字段仍报告 `dev`，作为官方构建元数据缺口保留。M1 已取得 Team `Active`、1 个 Leader 和 4 个 Worker `Running`、Human `Active` 与五份运行合同证据；已完成两轮 ProjectCase preparation（Round 1：task 0；Round 2：task 0、2、13），第二轮完成语义规格、四类 manifest 合同、Dossier/Trace 导出和结构化验证。四份正式 manifest 仍未实例化并经 Human freeze，因此尚未运行 Candidate，不能写成候选评测或闭环证据。

可声称“AgentFit 已在 AgentTeams 跑通最小闭环”，必须同时满足：

1. 五个 Agent 具有可检查身份、独立责任和独立产物；
2. 一个冻结 ProjectCase 从 Intake 流转到 Deliver；
3. 至少执行一个真实候选，并保留输入、输出、版本、模型、工具、用量和 Trace；
4. 至少保留一个失败、降级、拒绝或 Human 门禁分支；
5. GovernanceAuditor 的审计输入与结论可独立追溯；
6. 固定 AgentTeams 版本、配置、已验证能力和未验证边界；
7. 能在干净环境按仓库说明复现。

### 13.3 后续最小实施顺序与阶段完成定义

以下顺序只在第 13.2 节第一段的外部授权条件满足后生效。该条件已于 2026-08-14 满足，M0 已独立验收为 `READY`，M1 已进入 `IN_PROGRESS`；每个后续里程碑仍必须独立验收，不得用后一阶段的界面、自动化或演示材料替代缺失证据。M0/M1 的唯一运行入口是[`runtime/agentteams/README.md`](../runtime/agentteams/README.md)。

| 里程碑 | 实施内容 | 阶段完成定义 |
|---|---|---|
| M0 · 启动授权与基线冻结 | 记录赛事条件、授权范围和首个 ProjectCase；固定 AgentTeams 版本、运行入口、可用能力和未验证边界；冻结本阶段代码与材料基线 | 存在审批记录、ProjectCase 选择理由、版本清单和可复现的 AgentTeams 基线；只能声明“已获准启动”，不能声明已运行闭环 |
| M1 · 手动可审计 walking skeleton | 先使用 AgentTeams 原生 Worker、Team、Room、Human、Skill/工具和共享存储实例化五元团队；允许人工触发阶段，但必须写出第 7.4 节规定的结构化产物 | 一个冻结 ProjectCase 在当前环境从 Intake 到 Deliver；执行至少一个真实候选，并保留至少一个失败、降级、拒绝或 Human 门禁分支。M1 只证明当前环境首次贯通，不构成可复现最小闭环完成声明 |
| M2 · 确定性合同代码化 | 只把 M1 暴露的真实缺口固化为 Schema、版本/哈希、阶段状态机、四份 manifest 的冻结与访问策略、审批、预算和 Trace 校验；继续复用 AgentTeams 运行能力 | 机器校验可以拒绝非法状态推进、holdout 越权、版本漂移、预算越界和缺失审批；候选冻结后只有 GovernanceAuditor 可以解析 sealed holdout；同一 M1 ProjectCase 可在不依赖口头补证据的情况下重放；层级触达与实体分组违规可被机器拒绝；RegressionPool 与 ScenarioLedger 校验器就位 |
| M3 · 统一候选对照 | 在同一冻结 Sample/Task、四份 manifest、模型/工具边界、预算、指标和 Human 规则下比较候选 | 必须真实运行 Agentless、单 Agent 和多 Agent 三类候选；Human 混合候选必须真实运行，或由 GovernanceAuditor 记录不适用理由、证据与重新评估条件。每个 `EvaluationUnit = CandidateVersion × SampleVersion × RunIndex` 均有 SampleEvaluation 和 Trace；候选冻结后只有 GovernanceAuditor 可以解析 sealed holdout；报告同时呈现成功、失败、成本、风险与人工投入，并形成可追溯的 DeliveryDecision，不预设多 Agent 胜出；对照即回归——新候选必须在 RegressionPool 的既有冻结样本上不退化方可胜出 |
| M4 · 复现与比赛证据包 | 在干净环境复现选定 ProjectCase，固定依赖、配置、模型、工具、预算和运行入口；汇总日志、Trace、审批、失败、审计与交付产物 | 独立复现得到同一合同边界下的结论；比赛声明可逐项反向定位到仓库产物，完成态只依据可复现证据更新。独立复现成功且第 13.2 节七项完成门禁全部满足后，才可声明“AgentFit 已在 AgentTeams 跑通最小闭环” |

M0–M4 是单场景落地顺序，不等于跨场景 Meta-learning。持续学习的资产演化遵循第 11 节的回归保护、账本记录与版本化语义；只有多个场景的资产轨迹在未见场景上稳定优于无先验 baseline 后，才允许进入跨场景迁移工作。

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
