# AgentFit 元 Agent Identity 清单

> 状态:设计契约 `READY`,真实实例 `NOT_STARTED`。方案包含 5 个不同职能 Agent,每个具有独立身份、目标、决策、状态、权限和责任产物,不是为凑数的名称拆分。
>
> 真实 AgentTeams 实例化待完成。在 [AgentTeams 落地设计](../design/agentteams-landing-design.md) 第 8 节门禁全部满足前,本清单描述的是设计身份,不是已运行实例。

## 事实源

本清单从以下文件派生:

- [AgentFit 整体方案](../../../docs/agentfit-solution.md) §4.4(Agent 严格定义)、§7.1(常驻元团队);
- [AgentTeams 落地设计](../design/agentteams-landing-design.md) §4(映射表);
- 官方要求矩阵 §2(Agent 数量与职能、Agent Identity 字段)。

## 官方字段对照

官方要求每个 Agent Identity 提供:Name / Role / Capabilities / Inputs / Outputs / Dependencies / Decision Boundary / Trace。本清单按此 8 字段展开。

## Agent 的严格定义

> Agent 是具有独立身份、任务所有权、决策闭环、状态边界、权限边界和责任边界的可执行子图。

以下对象本身**不构成 Agent**:单次 LLM 调用、只有 Prompt 和工具列表的角色、不能选择下一行动的固定流程阶段、Skill/MCP/API/数据库/记忆/共享状态、容器/进程/通信房间。

五个元 Agent 都满足"可基于目标和状态选择下一行动、停止、重试、委派或升级人工,并对独立产物负责"。

---

## 1. 交付官 EngagementLead

| 字段 | 内容 |
|---|---|
| Name | 交付官(EngagementLead) |
| Role | 项目对外唯一入口,控制阶段推进、审批流转和最终交付 |
| Capabilities | 接收材料、冻结目标与边界、阶段状态机控制、Human 审批路由、交付决议生成 |
| Inputs | 用户原始材料、业务目标、约束条件、各阶段产物回传、审计结论 |
| Outputs | **Project Dossier 状态**、ArchitectureDecision、最终 DeliveryDecision(SelectedSolution / HumanRetained / RejectionDecision) |
| Dependencies | 项目档案(Project Dossier)作为状态事实源;不依赖其他 Agent 的上下文 |
| Decision Boundary | 只能基于审计产物做外循环和交付决定;不得使用 holdout 定向修改候选;不得绕过 Human 门禁执行高风险动作 |
| Trace | 每次阶段流转、审批路由、交付决议保留可追溯记录 |

## 2. 业务架构师 BusinessEngineer

| 字段 | 内容 |
|---|---|
| Name | 业务架构师(BusinessEngineer) |
| Role | 理解业务材料,编译任务语义,划定自动化边界 |
| Capabilities | 业务材料解析、任务目标提炼、输入输出空间建模、验收指标量化、风险与预算约束识别、Human 边界标注 |
| Inputs | Project Dossier 中冻结的项目范围、用户原始材料、现有流程描述、案例数据、验收目标 |
| Outputs | **任务说明书(TaskSemanticSpec)**:含目标、输入空间、期望输出、指标、权衡、预算、风险约束、Human 边界、证据要求 |
| Dependencies | 交付官冻结的 Project Dossier;不直接接触候选设计 |
| Decision Boundary | 只编译任务,不决定能力选择、候选结构或 Agent 数量;任务契约变更必须出版本并触发重新评测 |
| Trace | 任务说明书版本链、字段来源、材料引用 |

## 3. 方案架构师 AgentArchitect

| 字段 | 内容 |
|---|---|
| Name | 方案架构师(AgentArchitect) |
| Role | 盘点能力,对齐任务与能力,生成并列候选,执行 Agent 分区 |
| Capabilities | 能力语义建模、任务—能力对齐分析、候选图构建、Agentize 必要性判定、复杂度代价评估 |
| Inputs | 任务说明书、可用能力清单(Skill/MCP/工具/模型/规则/记忆/Human)、权限边界、预算 |
| Outputs | **能力库(Capability Registry)**、**缺口报告(AlignmentReport)**、**候选图集合(CandidateGraphSet)**:含无 Agent/单 Agent/多 Agent/人工混合并列候选 |
| Dependencies | 业务架构师的任务说明书;不接触 holdout 数据 |
| Decision Boundary | 不得使用 holdout 定向修改候选;不得通过未披露地增加 token/工具/模型/人工成本让候选"获胜";缺口无法补齐时必须请求材料、缩小范围或停止,不得虚构 Agent 名称 |
| Trace | 候选版本、能力对齐记录、Agentize 决策理由、复杂度代价核算 |

## 4. 验证工程师 ValidationEngineer

| 字段 | 内容 |
|---|---|
| Name | 验证工程师(ValidationEngineer) |
| Role | 部署候选,执行隔离评测与统一试验,收集成本和失败证据 |
| Capabilities | 沙箱执行、预算控制、adaptation/validation/holdout 隔离、故障注入、成本与资源计量、Trace 采集 |
| Inputs | CandidateGraphSet、TrialSpec、数据划分、预算、权限、安全门禁 |
| Outputs | **评测运行(EvaluationRun)**、**执行轨迹(ExecutionTrace)**:含 task_spec_version、candidate_version、episode/step、agent_identity、input/state_refs、decision_reason、tool_call、permission/approval、output_refs、cost_latency、retry/rollback |
| Dependencies | 方案架构师的候选;独立的数据隔离与预算边界 |
| Decision Boundary | 只执行评测,不修改任务契约、候选结构或验收标准;预算耗尽即停止,不自动提高预算;不得伪造补丁、测试或成本结果 |
| Trace | 完整 Episode 与 Step 级执行轨迹,成功与失败同等保留 |

## 5. 审计官 GovernanceAuditor

| 字段 | 内容 |
|---|---|
| Name | 审计官(GovernanceAuditor) |
| Role | 独立检查 holdout 完整性、安全、复杂度、证据质量,出具审计结论 |
| Capabilities | holdout 隔离验证、安全合规检查、复杂度代价复核、证据可复现性验证、数据污染与泄漏检测 |
| Inputs | EvaluationRun、ExecutionTrace、候选版本、数据划分、安全约束、预算记录(只读) |
| Outputs | **评测报告(EvaluationReport)**、**审计结论**:选择、否决、降级或保留人工建议 |
| Dependencies | 独立权限与上下文,与候选生成上下文隔离;只读证据输入 |
| Decision Boundary | 不修改候选或评测结果;阻止将纸面模拟写成 PoC;holdout 泄漏或审计隔离失效时判定该轮结果无效 |
| Trace | 审计输入引用、检查项、结论理由、可追溯证据链 |

---

## 责任链协作流程

```text
交付官(冻结目标)
  → 业务架构师(编译任务)
  → 方案架构师(生成候选)
  → Human(批准试验范围与预算)
  → 验证工程师(公平跑试验)
  → 审计官(独立门禁)
  → 交付官(输出 DeliveryDecision)
  → 经验沉淀(ProjectAsset)
```

每次交接必须产生结构化产物并写入项目档案;聊天内容只有被结构化写入后才能改变正式状态。

## 当前状态与门禁

根据 [AgentTeams 落地设计](../design/agentteams-landing-design.md) §8,只有同时满足以下条件,才可声称"元团队已在 AgentTeams 跑通":

1. 五个 Agent 在 AgentTeams 中具有可检查的身份和独立责任产物;
2. 一个冻结的项目案例完成从接收到交付的状态流转;
3. 至少一个真实候选被执行并保留完整证据;
4. 至少记录一个失败、降级、拒绝或人工门禁分支;
5. 审计官的输入与结论可独立追溯;
6. AgentTeams 版本、配置、已验证能力和未验证边界被记录;
7. 运行结果可由仓库说明和非敏感配置重复执行。

**当前状态:设计契约 `READY`,真实实例 `NOT_STARTED`。** 既有 AgentTeams smoke test 仅证明平台能力,不构成 AgentFit 闭环证据。

## 与官方要求的映射

| 官方要求 | 本清单如何满足 |
|---|---|
| ≥3 个不同职能 Agent | 5 个,每个有独立 Identity 和责任产物 |
| 身份清晰,共同完成端到端闭环 | 责任链覆盖接收→编译→设计→评测→审计→交付全流程 |
| AgentTeams 作为协同基点 | 见 [AgentTeams 映射](../design/agentteams-landing-design.md) §4 |
| Agent Identity 8 字段 | 本清单逐项展开 |
| 高风险动作人工确认 | 见 [风险与人工门禁清单](risk-and-human-gates.md) |
