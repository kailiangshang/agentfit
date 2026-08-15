# AgentFit 核心 Skill 清单

> 状态:设计契约 `READY`,Skill/工具真实绑定 `NOT_STARTED`(五元团队实例化与三轮 preparation 已完成)。当前定义 7 个核心 Skill。
>
> 真实 AgentTeams Skill 绑定待完成。在 [AgentFit 整体方案](../../../docs/agentfit-solution.md) §13 门禁满足前,本清单描述的是设计契约,不是已运行的 Skill 实例。

## 事实源

本清单从以下文件派生:

- [AgentFit 整体方案](../../../docs/agentfit-solution.md) §4.9(能力语义)、§4.11(任务—能力对齐)、§7(元团队与流程);
- [AgentFit 整体方案](../../../docs/agentfit-solution.md) §3(AgentTeams 边界)、§13(后续运行门禁)。

## Skill 契约结构

每个 Skill 同时定义名称、类型、使用场景、输入参数、输出结果、调用条件、依赖工具系统、失败处理、权限安全和复用价值，使能力可以被发现、调用、审计和迁移。

## Skill 与层级的关系

七项自研 Skill 均属方案工程层产物：任务编译(S1)与能力对齐(S2)产出 L1 接口需求与 L2 封装契约；候选建图(S3)作用于 L4；统一试验(S4)采集分层 Trace；独立审计(S5)执行层级触达与泄漏检查；人工门禁(S6)是全层风险截断；经验沉淀(S7)写入 L3 版本化资产并经回归池验证。

## Skill 与 Agent 的关系

Skill 是**可复用、可版本化的做事方法**,不是 Agent。Agent 是组合和支配能力子图的独立决策与责任主体。一个 Skill 可被多个 Agent 调用,一个 Agent 可调用多个 Skill。AgentFit 不把每个 Prompt、Skill、工具或流程阶段包装成 Agent。

失败模式可以提出新的 Skill 或新版本，但不能自动成为共享能力：必须限定适用边界、完成版本化记录，并在新案例上验证后才允许晋升。当前七个核心 Skill 固定；真实绑定仍为 `NOT_STARTED`。

## 与阿里云官方 Skills 的关系

AgentFit 按必要性而非数量评审官方 Skills。原则:

- 官方 Skill 能覆盖的领域能力,优先复用,不重复造;
- AgentFit 独有的"方案工程"能力(Sample/Task 编译、能力对齐、候选搜索、统一评测、独立审计)是官方 Skill 不覆盖的,需要自研;
- 与云 Skills 门户的契约对照:鉴权沿用门户凭证体系、编排由 AgentFit 阶段状态机触发、端到端体验经 Dossier 审计;迁移成本限定为 Skill 包格式适配,不涉及治理语义迁移;
- 使用或不使用官方 Skill 的选择基于场景需求、可替换性和迁移成本。

---

## 核心自研 Skill(方案工程层)

### S1. Sample 与任务编译 Skill

| 字段 | 内容 |
|---|---|
| 名称 | Sample 与任务编译(sample-and-task-compilation) |
| 类型 | 领域 Skill(LLM + 规则 + Schema 校验) |
| 使用场景 | 业务架构师先把 SourceObservation 编译为可冻结、重放、执行和评价的 Sample 合同，再编译可验收的任务合同 |
| 输入参数 | 项目简报、原始材料、SourceObservation、验收目标、约束条件 |
| 输出结果 | SampleSemanticSpec、SampleSetManifest、TaskSemanticSpec，全部版本化；分别定义样本单位/边界/重放契约、冻结 split/访问策略/内容哈希，以及目标/输出/指标/聚合/预算/风险/Human 边界 |
| 调用条件 | 交付官冻结项目简报后触发 |
| 依赖工具系统 | LLM、文档解析、Schema 校验器;不直接调用外部写入工具 |
| 失败处理 | 样本单位、分组、cutoff、split 或验收标准不可描述时请求补充、缩小范围或建议拒绝；Schema 校验失败阻塞推进 |
| 权限安全 | 只读原始材料；可编译 sealed_holdout manifest 的受控引用，但不能读取 sealed holdout 内容或结果；不持有外部写入权限 |
| 复用价值 | 跨场景通用，Sample 与 Task Schema 是 AgentFit 资产复用基础 |

### S2. 能力对齐 Skill

| 字段 | 内容 |
|---|---|
| 名称 | 能力对齐(capability-alignment) |
| 类型 | 领域 Skill(规则 + LLM) |
| 使用场景 | 方案架构师盘点能力,生成任务—能力对齐报告与缺口清单 |
| 输入参数 | SampleSemanticSpec、SampleSetManifest 分布摘要、TaskSemanticSpec、能力清单(Skill/MCP/工具/模型/规则/记忆/Human)、权限边界 |
| 输出结果 | 能力库(每项含类型/目的/输入输出契约/触发条件/依赖/成本/权限/副作用/失败模式/恢复)、缺口报告(完整/部分/未覆盖/冲突/不可观测/需人工确认) |
| 调用条件 | Sample/Task 契约与四份 SampleSetManifest 获 Human 批准并冻结后触发 |
| 依赖工具系统 | 能力注册表、Schema 校验器 |
| 失败处理 | 缺口无法补齐时请求材料、缩小范围或停止搜索;不得虚构 Agent 名称掩盖缺口 |
| 权限安全 | 只读能力定义;不调用能力本身 |
| 复用价值 | 能力库可跨批次复用;缺口模式是 ScenarioAsset 候选 |

### S3. 候选建图 Skill

| 字段 | 内容 |
|---|---|
| 名称 | 候选建图(candidate-graph-building) |
| 类型 | 领域 Skill(图构建 + 约束求解) |
| 使用场景 | 方案架构师生成无 Agent/单 Agent/多 Agent/人工混合并列候选,执行 Agent 分区 |
| 输入参数 | SampleSemanticSpec、获准的 SampleSetManifest 与分布摘要、TaskSemanticSpec、能力库、缺口报告、权限边界、预算 |
| 输出结果 | 候选方案集(每个候选含基础能力图 G、Agent 分区 Π、参数 θ、共享范围 ρ) |
| 调用条件 | 能力对齐报告产出后触发;必须从覆盖核心契约的最简方案开始(Baseline-first) |
| 依赖工具系统 | 图构建器、Agentize 必要性判定器、复杂度核算器 |
| 失败处理 | 禁止组合或权限冲突表示为搜索约束;复杂度代价无收益时停止增加 Agent |
| 权限安全 | 候选与 AgentArchitect 不得读取 sealed holdout 内容、标签或结果；只使用已批准的 Sample 合同与分布摘要，不执行候选 |
| 复用价值 | Agentize 条件、成功候选拓扑是 ScenarioAsset 候选 |

### S4. 统一试验 Skill

| 字段 | 内容 |
|---|---|
| 名称 | 统一试验(unified-trial-execution) |
| 类型 | 执行 Skill(沙箱 + 预算控制 + 计量) |
| 使用场景 | ValidationEngineer 在 adaptation、validation 和 stress/failure samples 上执行候选，采集逐样本评价、Episode、Step Trace 与成本 |
| 输入参数 | CandidateGraphSet + SampleSetManifest(adaptation/validation/stress_and_failure) + TrialSpec，以及预算、权限、安全门禁 |
| 输出结果 | 每个 CandidateVersion × SampleVersion × RunIndex 的 SampleEvaluation、完整 Episode 与 Step 级 ExecutionTrace；TaskSample 只描述业务语义单位；成功与失败证据同等保留 |
| 调用条件 | 候选生成后，Human 单独批准 TrialSpec、权限和预算后触发 |
| 依赖工具系统 | 沙箱容器、预算计量器、Trace 采集器、故障注入器 |
| 失败处理 | 预算耗尽即停止，不自动提高预算；工具超时、权限拒绝、环境故障或循环失控按预定义路径回滚；任何 sealed holdout 暴露均使本轮无效 |
| 权限安全 | ValidationEngineer is adaptation/validation/failure only；不能读取或解析 sealed holdout；在沙箱内执行，密钥由基础设施持有，外部写入需 Human 审批 |
| 复用价值 | 评测协议、Trace Schema、故障集是 ScenarioAsset 候选 |

### S5. 独立审计 Skill

| 字段 | 内容 |
|---|---|
| 名称 | 独立审计(independent-audit) |
| 类型 | 审计 Skill(规则 + 校验) |
| 使用场景 | GovernanceAuditor exclusively resolves sealed holdout after candidate freeze，并独立检查完整性、安全、复杂度与证据质量 |
| 输入参数 | 冻结 CandidateVersion、sealed_holdout SampleSetManifest、执行轨迹、安全约束、预算记录(只读) |
| 输出结果 | Holdout EvaluationReport、决策账本、审计结论(选择/否决/降级/保留人工建议) |
| 调用条件 | CandidateVersion 冻结且验证工程师产出 adaptation/validation/failure 轨迹后触发；必须与候选生成和执行上下文隔离 |
| 依赖工具系统 | 只读证据访问、隔离校验器、污染检测器 |
| 失败处理 | sealed holdout 内容或结果反馈候选、发生泄漏或审计隔离失效时判该轮无效；证据不足时不出选择结论 |
| 权限安全 | sealed holdout 只由 GovernanceAuditor 在候选冻结后解析；只读、独立权限与上下文，不修改候选或评测结果 |
| 复用价值 | 审计模板、检查项、污染检测规则是 ScenarioAsset 候选 |

### S6. 人工门禁 Skill

| 字段 | 内容 |
|---|---|
| 名称 | 人工门禁(human-gate) |
| 类型 | 治理 Skill(审批路由 + 记录) |
| 使用场景 | 候选生成前的 Sample/Task 冻结，以及候选生成后的 TrialSpec/权限/预算和其他高风险动作(外部写入、真实发布、责任转移、密钥使用、预算变更)必须分别由 Human 批准、可拒绝、可回滚 |
| 输入参数 | SampleSemanticSpec、TaskSemanticSpec、四份 SampleSetManifest 的单位/分组/cutoff/split/access policy/content hash，或 TrialSpec、权限、预算及其他动作类型、触发条件、风险等级、审批主体、回滚路径 |
| 输出结果 | 审批记录(批准/拒绝/撤销)、回滚记录、Trace 引用 |
| 调用条件 | 任何高风险动作执行前自动触发 |
| 依赖工具系统 | AgentTeams Human 入口、审批记录存储 |
| 失败处理 | 无批准时拒绝执行并保留 Trace;审批超时按预定义降级路径处理 |
| 权限安全 | Human 不是兜底文案,是候选图中的能力与约束对象;必须有触发条件、审批主体、响应时限、拒绝和回滚记录 |
| 复用价值 | 门禁模板跨场景通用 |

### S7. 经验沉淀 Skill

| 字段 | 内容 |
|---|---|
| 名称 | 经验沉淀(asset-consolidation) |
| 类型 | 治理 Skill(脱敏 + 参数化 + 版本化) |
| 使用场景 | 把批次经验转为 BatchAsset 并累积为 ScenarioAsset;经回归池验证后版本化沉淀 |
| 输入参数 | SampleEvaluation、ExecutionTrace、决策账本、复盘条目、成功与失败 Episode |
| 输出结果 | BatchAsset/ScenarioAsset(场景作用域);更新必须绑定证据引用与回归结果 |
| 调用条件 | 交付阶段后触发;任何 L2/L3/L4 资产更新必须先过 RegressionPool 回归与独立审计 |
| 依赖工具系统 | 版本化存储、脱敏器、回归测试器 |
| 失败处理 | 回归池退化、实体污染、适用边界不清或证据被推翻时必须回滚或冻结；失败模式可提出新版本 Skill，但必须经新案例验证后才可晋升 |
| 权限安全 | 共享资产晋升前必须脱敏;不携带密钥或敏感数据 |
| 复用价值 | ScenarioAsset 是场景内持续学习载体;跨场景迁移为远期方向,**未见场景验证前不宣称跨场景学习** |

---

## 与官方 Skills / 工具的协作

| AgentFit Skill | 可能调用的官方/外部能力 | 关系 |
|---|---|---|
| Sample 与任务编译 | 文档解析、知识抽取类 Skill | 复用；AgentFit 在其上增加 Sample/Task Schema、冻结集合与验收约束 |
| 能力对齐 | AgentTeams 能力注册、MCP 目录 | 复用;AgentFit 增加任务—能力对齐分析 |
| 候选建图 | AgentTeams Worker/Team 编排 | 复用;AgentFit 决定何时 Agentize、何时不该 |
| 统一试验 | AgentTeams 容器、沙箱、Skill/MCP 执行 | 复用运行底座;AgentFit 增加预算控制与隔离评测 |
| 独立审计 | AgentTeams 可观测、日志 | 复用数据源;AgentFit 增加独立结论与 holdout 校验 |
| 人工门禁 | AgentTeams Human 入口、审批 | 直接使用 AgentTeams 原生能力 |
| 经验沉淀 | AgentTeams 共享存储 | 复用存储;AgentFit 增加脱敏、参数化、晋升门禁 |

## 结构化上下文设计

AgentFit 以共享状态与轨迹可观测作为两项主上下文机制,真实实现状态为绑定前夜(团队已实例化,绑定属 M1 后续):

1. **共享状态**:计划以项目档案(Project Dossier)作为版本化状态事实源,承载阶段产物、执行轨迹和交付决定;
2. **轨迹可观测**:计划由执行轨迹(ExecutionTrace)记录 Step/Episode 级决策、工具调用、权限审批、成本、重试和回滚。

不采用知识库 RAG。理由:AgentFit 的核心上下文是结构化合同与能力库,而非非结构化文档检索；**样本语义 + 任务语义 + 能力语义 + ExecutionTrace** 构成可审计的结构化上下文，比向量检索更可复现、可审计。Agent 记忆作为局部状态介质存在于候选执行中,但不作为主上下文机制单独声明。

## 当前状态与门禁

本清单的设计契约状态为 `READY`,真实 AgentTeams 绑定状态为 `NOT_STARTED`。当前只能表述为"Skill 设计完成";实际绑定工作启动并更新状态后,才能表述为"Skill 实现进行中"。最终完成态以 [AgentFit 整体方案](../../../docs/agentfit-solution.md) §13 门禁为准。

## 设计摘要

| 设计要点 | AgentFit 定义 |
|---|---|
| 能力链 | 7 个核心 Skill 覆盖编译、对齐、建图、试验、审计、门禁和沉淀 |
| 外部能力复用 | 按必要性复用运行底座类能力,自研方案工程类能力 |
| 契约完整性 | 每项能力都记录输入输出、调用条件、依赖、失败、安全和复用边界 |
| 跨 Agent/场景复用 | 每个 Skill 可被多个 Agent 调用,产物可跨项目沉淀 |
| 版本与恢复 | Skill 产物版本化,失败与回滚路径明确 |
| 能力关系 | 上表记录 AgentFit Skill 与 AgentTeams、官方或外部能力的协作边界 |
