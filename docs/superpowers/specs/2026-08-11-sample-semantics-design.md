# AgentFit Sample 语义层设计

> 决策日期：2026-08-11
>
> 状态：已获用户方向确认，待书面规格复核
>
> 适用范围：AgentFit 总体方法、ProjectCase 契约、AgentTeams walking skeleton 与 GOAI 初赛材料

## 1. 问题与决策

现有方案定义了任务语义、能力语义、候选表示、内循环、外循环和跨项目学习，但没有把“候选究竟处理什么、一次评价作用于什么”定义为一等对象。文档虽然零散使用了样例、数据集和 Episode，却没有统一样本边界、版本、重放和聚合口径。

AgentFit 新增独立的 **Sample 语义层**。Sample 不只是 `TaskSemanticSpec.examples` 中的示例，也不等同于一次 Agent 执行；它是架构搜索、统一评测、审计隔离和跨项目比较共同依赖的基本单位。

> Sample 是在特定任务契约下，可以被独立冻结、重放、执行和评价的最小业务语义单元。

原有六层 ML 映射调整为七层：

| 层级 | AgentFit 对象 | ML / 搜索含义 |
|---|---|---|
| L1 | Sample 语义 | 样本单位、实例空间、边界、重放与标注契约 |
| L2 | Task 语义 | 样本分布、目标、输出、损失、指标与权衡 |
| L3 | Capability 语义 | 可用算子、契约、权限、成本和适用域 |
| L4 | Candidate 表示 | 能力图、Agent 分区、参数与共享范围 |
| L5 | Inner Loop | 固定架构，在 adaptation samples 上优化局部参数 |
| L6 | Outer Loop | 在 validation samples 上比较和更新候选架构 |
| L7 | Cross-project Learning | 经未见项目验证后更新搜索先验 |

## 2. 三个不能混淆的对象

### 2.1 SourceObservation

来自业务系统的原始观察，例如一条告警、一条用户反馈、一个 Issue、一条日志或一张工单。它保留来源和时间边界，但是否构成可评价样本由当前任务契约决定。

### 2.2 TaskSample

当前 `TaskSemanticSpec` 下可独立执行和验收的单位。样本粒度具有任务相对性：

- 在告警分类任务中，一条告警可以是一个 `TaskSample`；
- 在事故处置任务中，一次完整运维事故可以是一个 `TaskSample`，其中包含多条告警和日志 `SourceObservation`；
- 同一条告警在一个任务中可以是样本，在另一个任务中只是更大样本的组成证据。

样本边界不得由候选运行时临时改变。若从“单告警”改为“完整事故”，必须生成新的 Sample 和 Task 契约版本，并重新批准试验。

### 2.3 Episode

一个固定候选在一个固定 `TaskSample` 上的一次完整执行。Episode 是运行轨迹，不是输入样本：

```text
EvaluationUnit = CandidateVersion × SampleVersion × RunIndex
Episode        = 一次 EvaluationUnit 的执行与 Trace
```

因此 `ProjectCase != Sample`。一个 ProjectCase 描述任务分布、样本集合、候选空间、预算和评测协议；一个 Sample 是该项目中的具体评价单位。

## 3. 核心契约

### 3.1 SampleSemanticSpec

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

关键字段含义：

- `temporal_boundary`：样本可见事实的截止时间，防止未来信息泄漏；
- `grouping_rule`：多条原始观察何时属于同一个样本；
- `identity_rule`：相同业务事件如何获得稳定 ID，避免重复计数；
- `label_or_oracle`：自动标签、规则 Oracle、人工复核或仅契约验收；
- `replay_contract`：重放所需输入、环境快照、模拟器和允许的外部依赖；
- `metric_applicability`：哪些指标可在单样本计算，哪些只能跨样本聚合。

### 3.2 Sample

`Sample` 是不可变、可寻址的具体实例：

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

sealed holdout 可以隐藏 `expected_contract_ref` 的实际内容，但必须保留由审计者解析的受控引用。候选、Prompt 和普通执行 Agent 不得读取该引用。

### 3.3 SampleSetManifest

数据划分不再用模糊的“数据集”描述，而使用版本化清单：

```text
SampleSetManifest = {
  sample_set_id, version, purpose,
  sample_spec_ref, sample_refs,
  selection_rule, distribution_summary,
  access_policy, frozen_at, content_hash
}
```

一个 ProjectCase 至少包含：

- `adaptation_set`：允许内循环查看输出和反馈；
- `validation_set`：用于候选选择和外循环更新；
- `sealed_holdout_set`：仅供最终独立审计；
- `stress_and_failure_set`：错误输入、工具故障、权限拒绝、超时和不安全动作。

相同 `content_hash` 不得跨集合出现。按事故、客户、仓库、环境、模板或时间相关的样本必须分组切分，不能把同一业务事件的近重复观察随机拆到不同集合。

### 3.4 EvaluationRun 与样本级结果

每个 Episode 必须记录：

```text
SampleEvaluation = {
  candidate_version, sample_version, run_index,
  seed, environment_snapshot, budget_snapshot,
  result_ref, trace_ref, metric_values,
  status, failure_class, human_actions
}
```

项目级结果只能由样本级结果按预先冻结的聚合规则产生。平均值、成功率、成本、人工接管率和失败率必须同时记录分母、缺失样本、失败样本和适用范围，禁止只汇报成功 Episode。

## 4. 内循环、外循环与 Epoch

```text
Inner Loop
  固定 G / Agent 分区 / 权限边界
  在 adaptation SampleSet 上更新 Prompt、模型、阈值、检索或局部配置

Outer Loop
  冻结内循环结果
  在 validation SampleSet 上比较 Agentless、单 Agent、多 Agent和 Human 混合候选
  根据效果、成本、复杂度、风险和审计结果更新架构

Independent Audit
  GovernanceAuditor 在候选冻结后读取 sealed holdout
  任何基于 holdout 的候选修改都会使该轮结果失效
```

运行单位统一为：

| 名称 | 定义 |
|---|---|
| Step | 一次推理、工具调用或环境反馈 |
| Episode | 一个候选在一个固定样本上的一次完整执行 |
| Inner Epoch | 固定候选完整处理一轮 adaptation SampleSet |
| Outer Generation | 一次候选生成、局部适配、validation 和架构更新 |
| Meta Epoch | 跨多个项目更新先验，并在未见项目上验证 |

一次聊天、一次局部 SCC 循环或一次工具调用都不是 Sample，也不能单独称为 Epoch。

## 5. 元团队责任变化

| 责任主体 | Sample 相关责任 | 独立产物 |
|---|---|---|
| EngagementLead | 组织样本边界、数据授权和划分审批 | 批准记录、Project Dossier 状态 |
| BusinessEngineer | 从原始材料定义样本单位、Schema、边界、分布和验收 | `SampleSemanticSpec`、`SampleSetManifest`、`TaskSemanticSpec` |
| AgentArchitect | 基于样本与任务分布设计候选，不读取 sealed holdout 内容 | CandidateGraphSet、复杂度假设 |
| ValidationEngineer | 在 adaptation、validation 和 failure samples 上执行可重放试验 | SampleEvaluation、EvaluationRun、ExecutionTrace |
| GovernanceAuditor | 独占 sealed holdout 评价和泄漏检查 | Holdout EvaluationReport、审计结论 |
| Human | 确认样本代表真实业务并批准数据、预算和高风险动作 | 批准、拒绝、撤销和责任记录 |

## 6. AgentTeams walking skeleton 映射

Sample 及其清单存放在版本化 Project Dossier 中，AgentTeams 只负责 Agent 身份、Team、通信、共享存储和生命周期，不负责定义样本语义。

首个真实 ProjectCase 的最小链路调整为：

```text
RawMaterials + SourceObservations
→ SampleSemanticSpec + SampleSetManifest
→ TaskSemanticSpec
→ CapabilitySemanticRegistry + AlignmentReport
→ CandidateGraphSet + TrialSpec
→ CandidateVersion × SampleVersion
→ SampleEvaluation[] + ExecutionTrace[]
→ EvaluationReport + DeliveryDecision
```

官方运维案例中至少显式区分：

- 告警级样本：适合告警分类、聚合或路由；
- 事故级样本：适合根因分析、修复建议和恢复验证；
- Episode：C0、C1、C2 分别处理同一事故级样本产生的运行轨迹。

公开案例数量不足时，只能证明 walking skeleton 可运行，不能声称具备稳定泛化、独立 holdout 结论或跨项目学习能力。

## 7. 文档与比赛材料传播范围

实施时必须同步更新下列事实源，不能只在总体方案中补一句：

1. `docs/agentfit-solution.md`：新增 Sample 定义、七层映射、运行单位、Dossier 和评测口径；
2. `docs/internal/contracts/project-case-template.md`：新增三个 Sample 契约并重写四类集合；
3. `competition/2026-08-15/design/agentteams-landing-design.md`：调整元团队产物、最小闭环和代码保证项；
4. `competition/2026-08-15/research/official-case-simulation.md/.json`：标注告警级、事故级 Sample 和 Episode；
5. `competition/2026-08-15/submission/agent-identity.md`、`skill-catalog.md`、`risk-and-human-gates.md`：补全责任、Skill 输入输出和隔离规则；
6. `competition/2026-08-15/submission/work-introduction-draft.md`：在 500 字限制内加入样本含义并重新计数；
7. 路演第 4、6、7 页及 A1：将“同一输入”改为“同一冻结样本集”，六层映射改为七层；
8. HTML、PPTX、PDF 和准备看板：重新生成、逐页验证并保持状态声明一致。

## 8. 验收标准

本次文档传播完成必须满足：

1. `Sample`、`SourceObservation`、`TaskSample` 和 `Episode` 在所有事实源中含义一致；
2. `TaskSemanticSpec` 显式引用 `SampleSemanticSpec` 和样本分布，而不再用 `examples` 代替样本契约；
3. adaptation、validation、sealed holdout 和 failure 都是带版本、哈希和访问策略的 `SampleSetManifest`；
4. 每个运行结果都可反向定位到 Candidate、Sample、环境、预算和 Trace；
5. 所有指标声明包含样本单位、分母、聚合方式和适用范围；
6. PPT 主路演仍为 12 页、附录仍为 5 页，HTML/PPTX/PDF 页序与结论一致；
7. 作品简介不超过 500 个非空白字符；
8. 不因新增 Sample 层而把设计模拟、公开案例或历史 smoke test升级为真实 AgentFit 运行证据；
9. 不把单项目样本优化写成 Meta-learning。

## 9. 非目标

本次变化不立即实现完整数据标注平台、自动样本生成、主动学习、数据版本管理产品、跨项目 Sample Registry 或自动 NAS。近期工程目标仍是一个冻结 ProjectCase、一个可重放 SampleSet 和一次可审计的 AgentTeams walking skeleton。
