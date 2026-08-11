# GOAI Agent Infra 官方案例拆解与 AgentFit 设计模拟

> 状态：设计模拟，非运行证据
>
> 官网来源：<https://goaihz.com/tracks?track=infra>
>
> 核验日期：2026-08-10

## 1. 官网四个参考方向

官网明确说明以下方向只用于场景启发，不限制参赛范围：

| 参考方向 | 官网闭环摘要 |
|---|---|
| 零人工运维 | 告警聚合 → 根因定位 → 修复执行 → 恢复验证 → 事故复盘 |
| 智能客服自主闭环 | 会话聚合 → 意图与分级 → 方案执行 → 结果与客户确认 → 案例复盘 |
| 软件研发全流程协同 | 缺陷/需求聚合 → 代码定位 → 修复执行 → 测试与发布确认 → 上线复盘 |
| 金融风控与理赔自动化 | 风险信号聚合 → 风险定位 → 处置执行 → 结果与合规审计 → 事件复盘 |

四个方向共享同一种任务骨架：

```text
多源输入 → 定位与判断 → 生成并执行方案 → 独立验证或确认 → 经验沉淀
```

共享骨架不意味着必须使用相同 Agent 数量。数据、权限、失败成本和验证方式不同，会改变最小充分方案。

## 样本单位示例

- 告警分类：一条告警是一个 `TaskSample`。
- 事故处置：一次完整运维事故是一个 `TaskSample`，多条告警和日志是 `SourceObservation`。
- 候选比较：C0、C1、C2 处理同一冻结 `TaskSample`，各自产生一个 `Episode`。

`SourceObservation` 是原始业务观察；`TaskSample` 是在当前任务契约下可独立冻结、重放、执行和评价的最小单位；`Episode` 是固定候选在固定 `TaskSample` 上的一次完整执行。因此，原始观察不等于样本，样本也不等于候选执行轨迹。

## 2. 深挖案例：软件研发全流程协同

官网原始流程包含：

1. 多源缺陷/需求信息聚合与去重，包括 Issue、日志和用户反馈；
2. 代码缺陷自动定位与影响面分析；
3. 修复方案生成与自动化编码执行；
4. 测试验证与灰度发布结果确认；
5. 上线复盘与研发知识库沉淀。

AgentFit 不从“创建几个 Agent”开始，而是先把它编译为可验收任务。

本案例中，一个冻结的软件缺陷包是一个 `TaskSample`：它以 Issue、日志、用户反馈等 `SourceObservation` 为来源，固定仓库快照、测试策略、模型工具边界和预算后才能重放。当前只草拟 `SampleSemanticSpec`、四类 manifest 描述符与 `TaskSemanticSpec` 契约，不实例化任何样本成员或 SampleSetManifest；以下内容仅说明设计契约。

`SampleSemanticSpec` 的设计身份为 `sample-spec:software-defect-package@0.1-design-contract`，并引用 `task-spec:software-defect-repair@0.1-design-contract`。adaptation、validation、sealed_holdout、stress_and_failure 是四个互异的必需 manifest 描述符；每个都要求独立 `version`、`content_hash` 和 `access_policy`，但本案例中的 version 与 content_hash 均为空，状态保持 `not_instantiated`。

## 3. TaskSemanticSpec 摘要

| 字段 | 设计模拟值 |
|---|---|
| sample_spec_ref | `sample-spec:software-defect-package@0.1-design-contract` |
| sample_distribution | adaptation / validation / sealed_holdout / stress_and_failure 四类 manifest 描述符；均为 `not_instantiated` |
| objective | 从多源缺陷线索形成可验证的修复候选，并在人工批准前停止真实发布 |
| input_space | Issue、日志片段、用户反馈、仓库快照、测试与发布策略 |
| expected_output | 去重后的问题单、定位与影响报告、补丁候选、测试证据、发布审批记录、复盘资产 |
| acceptance | 补丁通过冻结测试；定位和影响结论可追溯；无未批准外部写入；失败可回滚 |
| budgets | 固定模型与工具边界；统一 token、工具调用、时间、重试和人工投入上限 |
| risk_constraints | 密钥不进上下文；仓库写入受控；真实发布必须 Human 批准；保留失败证据 |
| human_boundary | Human 在候选生成前冻结 Sample/Task 契约与四份 manifest；候选生成后另行批准 TrialSpec、权限、预算和真实发布 |

## 4. 能力语义盘点

| 能力 | 类型 | 作用 | 关键边界 |
|---|---|---|---|
| 线索标准化与去重 | Rule / Algorithm | 合并重复 Issue、日志和反馈 | 保留来源，不覆盖原始材料 |
| 仓库检索与依赖分析 | Tool / Skill | 形成候选文件和影响面 | 默认只读 |
| 修复候选生成 | LLM / Skill | 产生补丁与解释 | 不允许直接发布 |
| 测试执行 | Tool | 在隔离环境运行冻结测试 | 超时、资源和网络受限 |
| 结果审计 | Rule / Human | 检查证据、风险和预算 | 与候选生成上下文隔离 |
| 发布批准 | Human | 承担真实写入和责任转移 | 可拒绝、撤销和回滚 |

## 5. 三个候选

### C0 · Agentless

固定 Workflow 执行线索去重、规则筛选、仓库检索和冻结测试。它是必须保留的强基线，适合输入稳定、变更模式已知的任务；对跨文件不确定定位和修复策略选择能力有限。

### C1 · 单 Agent

一个责任主体完成定位、影响分析、补丁生成和测试重试，Human 批准真实发布。它减少通信成本，但长上下文、权限集中和自我验证偏差需要重点检查。

### C2 · 多 Agent

定位/影响、修复、独立验证由不同责任主体完成，Human 保留发布门禁。它有利于上下文和审计隔离，但增加通信、状态同步、预算和错误归因成本。

三者必须使用同一冻结 `SampleSetManifest`、同一版本化 `TaskSample`、相同模型与工具边界、冻结测试、安全门禁和预算口径。多 Agent 不能通过额外模型、工具或人工投入获得隐性优势。运行身份只能写为 `CandidateVersion × SampleVersion × RunIndex`；`TaskSample` 只描述业务语义单位，不能代替 `SampleVersion`。

## 6. 纸面协作 Trace

```text
T01 EngagementLead
    接收官网案例 → 建立 design-simulation dossier

T02 BusinessEngineer
    草拟 SampleSemanticSpec、四类 SampleSetManifest 与 TaskSemanticSpec 契约 → 不实例化任何成员或 manifest

T03 EngagementLead
    标注候选生成前的 Sample/Task 冻结门禁 → 本设计模拟不冒充真实审批

T04 AgentArchitect
    盘点能力与权限 → 生成 C0 / C1 / C2 → 不预设多 Agent 胜出

T05 ValidationEngineer
    只定义 TrialSpec、SampleEvaluation 和 CandidateVersion × SampleVersion × RunIndex Trace 契约 → 不伪造补丁、测试或成本结果

T06 GovernanceAuditor
    检查数据隔离、预算、公平性与发布门禁 → 阻止将纸面模拟写成 PoC

T07 EngagementLead
    输出 requires_runtime_trial → 下一步进入真实受控试验
```

## 7. 模拟结论

```text
decision: requires_runtime_trial
selected_candidate: null
reason: 没有真实仓库执行、冻结测试、成本和失败证据，当前不能选择赢家
next_gate: 在同一冻结 SampleSetManifest、同一版本化 TaskSample、相同模型与工具边界、预算和安全门禁下执行 C0 / C1 / C2
```

该结果证明的是 AgentFit 能把官网场景转换为可运行试验设计，不证明 AgentFit 或任何候选已经完成运行验证。
