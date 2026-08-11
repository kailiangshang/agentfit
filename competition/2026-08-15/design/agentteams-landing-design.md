# AgentFit 基于 AgentTeams 的落地设计

> 最近同步：2026-08-11
>
> 决策状态：设计边界已认可；真实 AgentFit 集成尚未开始，下一步是首个 walking skeleton
>
> 适用阶段：GOAI Agent Infra 初赛准备及首个真实 ProjectCase

## 1. 决策

AgentFit 采用“AgentTeams 原生底座 + AgentFit 能力包”的落地方式：

- 不开发独立产品界面；
- 不修改 AgentTeams 核心源码；
- 优先使用 AgentTeams 已有 Dashboard、Manager/聊天入口、声明式资源、Worker、Team、Human、Skill、MCP、共享存储和通信能力；
- AgentFit 只开发 AgentTeams 原生配置无法可靠保证的领域能力；
- 第一阶段先在 AgentTeams 上手动或半自动跑通最小闭环，再根据真实失败点确定代码边界。

## 2. 已排除方案

### 2.1 纯界面和 Prompt 配置

该方式适合快速展示角色协作，但不能稳定保证 Schema、阶段门禁、候选隔离、统一预算、holdout 隔离、审计和可重复评测。它可以作为 walking skeleton，不作为最终工程边界。

### 2.2 修改 AgentTeams 核心

把 AgentFit 逻辑直接加入 Dashboard、Controller 或 Manager 会造成上游耦合，并重复承担运行平台的维护责任，因此不进入该路径。真实试验发现的平台缺口记录为外部依赖、上游 Issue 或扩展请求，并选择适配、降级或阻塞，不通过修改 AgentTeams 核心吸收为 AgentFit 功能。

### 2.3 自建 Agent 平台和独立前端

该方式重复实现身份、通信、资源编排、凭证、文件和运行环境，与 AgentFit 的方案工程定位冲突。AgentFit 不开发独立前端，展示与人工介入使用 AgentTeams 原有入口。

## 3. 系统边界

| 层级 | 负责内容 | 不负责内容 |
|---|---|---|
| AgentTeams | Agent 身份、Worker/Team/Human、容器、房间、通信、文件、凭证、Skill/MCP 绑定、生命周期与基础状态 | Task/Capability 语义、候选搜索、统一评测和 AgentFit 审计结论 |
| AgentFit 能力包 | 五个元 Agent 配置、领域 Prompt、Skill、Schema、状态门禁、候选描述、评测、Trace、审计和交付模板 | 通用 Agent 运行时、IM、容器编排、通用权限平台和新产品界面 |
| Human | 提供材料、确认任务契约、批准高风险动作、处理责任边界、接受或否决交付 | 替 AgentFit 静默补全证据或修改评测结果 |

界面只是控制与观察入口，不是 AgentFit 的事实源。聊天中的结论只有写入版本化结构化产物并通过相应门禁后，才能推进项目状态。

## 4. AgentFit 在 AgentTeams 中的映射

| AgentFit 对象 | AgentTeams 落点 | 第一阶段实现方式 |
|---|---|---|
| EngagementLead | Manager 或 Team Leader 入口 | 身份配置、阶段控制 Skill、项目状态文件 |
| BusinessEngineer | 独立 Worker | Worker 配置、Sample/Task 编译 Skill、`SampleSemanticSpec`、`SampleSetManifest`、`TaskSemanticSpec` |
| AgentArchitect | 独立 Worker | Worker 配置、能力对齐与候选设计 Skill |
| ValidationEngineer | 独立 Worker | Worker 配置、沙箱执行和统一评测工具 |
| GovernanceAuditor | 独立 Worker | 独立权限与上下文、审计 Skill、只读证据输入 |
| Project Dossier | AgentTeams 共享存储 | 版本化目录与机器可读 Manifest |
| 阶段委派 | AgentTeams 房间与任务通信 | 结构化 Task Envelope + @mention 通知 |
| Human 审批 | AgentTeams Human/房间 | 明确的批准、拒绝和撤销记录 |
| Skill/MCP | Worker 包、Skill 与 MCP 绑定 | 优先 Skill；需要确定性执行或外部接口时使用工具/MCP |
| Trace | 共享 Artifact + AgentTeams 消息/状态引用 | 统一事件 Schema，保留来源与运行版本 |

最终由实际 AgentTeams 版本支持的资源字段决定打包格式，但不得改变上述责任边界。

`SampleSemanticSpec`、`SampleSetManifest`、`SampleEvaluation` 也是 Project Dossier 共享存储中的版本化工件：前者定义样本单位及重放边界，manifest 固定划分和访问策略，evaluation 记录一次候选在一个冻结样本上的结果。它们由 AgentFit 生成、校验和审计；AgentTeams 只提供 Worker、共享存储、权限与运行时底座，不替 AgentFit 重新定义样本语义或评测结论。

## 5. 最小闭环

首个 ProjectCase 只验证以下链路：

```text
Human 提交材料、SourceObservations 和目标
→ BusinessEngineer 定义 SampleSemanticSpec、TaskSemanticSpec，并产出 adaptation、validation、sealed_holdout、stress_and_failure 四份互异且不可变的 SampleSetManifest
→ Human 批准并冻结 SampleSemanticSpec、TaskSemanticSpec 与四份 SampleSetManifest
→ AgentArchitect 生成 Capability Registry、AlignmentReport 和 CandidateGraphSet
→ Human 单独批准 TrialSpec、权限和预算
→ ValidationEngineer 生成 SampleEvaluation、EvaluationRun 和 ExecutionTrace
→ GovernanceAuditor 在候选冻结后使用 sealed holdout
→ EngagementLead 交付 DeliveryDecision
```

sealed holdout 的内容和结果有单向访问边界：仅 GovernanceAuditor 可解析或读取 sealed holdout 的结果，且仅在 `CandidateVersion` 冻结后。候选生成、Prompt、AgentArchitect、ValidationEngineer 和普通执行角色均不得访问 sealed holdout 的内容或结果；任何 sealed holdout 结果反馈进候选均使该轮运行无效。

`DeliveryDecision` 只能是 `SelectedSolution`（全自动/部分自动化/降级）、`HumanRetained` 或 `RejectionDecision`。

初次运行允许由人触发阶段和创建资源，但结构化产物、责任归属、候选输入、预算和审计结果不得靠人工口头补齐。

## 6. 必须用代码保证的部分

以下能力一旦仅依赖自然语言就会破坏可复现性，因此应在最小闭环验证后优先固化：

1. `SampleSemanticSpec`、`SampleSetManifest`、`TaskSemanticSpec`、`CapabilitySemanticSpec`、`AlignmentReport`、`Candidate`、`CandidateGraphSet`、`TrialSpec`、`SampleEvaluation`、`EvaluationRun`、`ExecutionTrace`、`EvaluationReport` 和 `DeliveryDecision` 的 Schema 与校验；
2. 所有样本、manifest、任务、候选和评测工件的内容哈希、重复拒绝与不可变版本；
3. 阶段状态、产物版本、批准主体和失败状态的确定性门禁；
4. adaptation、validation、sealed holdout 和 stress/failure set 的隔离，以及 sealed holdout 的访问控制：仅 GovernanceAuditor 在 `CandidateVersion` 冻结后可读取结果，其他候选与执行主体不得访问，结果反馈候选即判该轮无效；
5. Agentless、单 Agent、多 Agent候选使用同一冻结 `SampleSetManifest`、同一版本化 `TaskSample`，并共享相同模型与工具边界、预算、指标和安全门禁；
6. `CandidateVersion × SampleVersion × RunIndex` 的 Trace 引用、样本级结果与预冻结聚合规则；
7. Trace、依赖、模型、AgentTeams 版本和证据指针的自动记录；
8. 高风险动作的拒绝、审批、回滚和超时；
9. 评测汇总和比赛声明到内部证据的反向定位。

代码只存在 AgentFit 仓库中，通过 Worker 包、Skill、CLI、MCP 或适配层接入 AgentTeams。平台级缺口真实复现后，记录为外部依赖、上游 Issue 或扩展请求，不修改 AgentTeams 核心。

## 7. 错误与降级

- Agent 不可用：阶段保持未完成，记录失败，不由其他 Agent 静默冒充责任产物；
- 结构化产物不合法：拒绝推进，返回具体字段错误；
- 能力或权限缺失：请求补充、缩小范围或产生 `RejectionDecision`；
- AgentTeams 通信或房间异常：以 Project Dossier 状态为准，消息恢复后幂等重发；
- 评测预算耗尽：停止候选扩展，审计当前证据，不自动提高预算；
- holdout 泄漏或审计隔离失效：该轮结果无效，重新建立试验；
- 高风险动作无批准：拒绝执行并保留 Trace。

## 8. 首轮验证门禁

只有同时满足以下条件，才可以声称“AgentFit 已在 AgentTeams 上跑通最小闭环”：

1. 五个不同职能 Agent 在 AgentTeams 中具有可检查的身份和独立责任产物；
2. 一个冻结的 ProjectCase 和 adaptation、validation、sealed_holdout、stress_and_failure 四份互异且不可变的 `SampleSetManifest` 完成从 Intake 到 Deliver 的状态流转；
3. 至少有一个真实候选在一个可重放的冻结 `TaskSample` 上被执行，并保留输入、输出、模型、工具、成本或用量和 Trace；
4. 至少记录一个失败、降级、拒绝或人工门禁分支；
5. GovernanceAuditor 的输入与结论可独立追溯；
6. AgentTeams 版本、配置、已验证能力和未验证边界被记录；
7. 运行结果可由仓库中的说明和非敏感配置重复执行。

当前 `NOT_STARTED` 状态只能表述为“设计完成”或“AgentTeams 平台能力已单独试用”。实际创建首个 ProjectCase 或五元团队并把状态更新为 `IN_PROGRESS` 后，才能表述为“AgentFit 集成进行中”；全部门禁满足后才能表述为“已跑通最小闭环”。

## 9. 第一阶段非目标

- 独立 AgentFit 前端或 Dashboard；
- 飞书集成；
- 修改 AgentTeams Controller、Dashboard 或运行时；
- 自动探索全部候选空间；
- 完成六个 ProjectCase；
- 宣称跨项目 Meta-learning 已被验证；
- 生产部署或真实业务收益声明。
