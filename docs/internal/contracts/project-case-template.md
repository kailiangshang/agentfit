# ProjectCase Contract

> 状态：当前设计契约，尚未实例化真实 ProjectCase。

本文件定义单个 AgentFit ProjectCase 必须具备的结构。它既用于近期 AgentTeams walking skeleton，也可用于后续跨项目研究，但本身不代表任何项目已经获批或运行。

`ProjectCase != Sample`：ProjectCase 描述任务分布、样本集合、候选空间、预算和评测协议；`SourceObservation` 是原始业务观察；`TaskSample` 是当前任务契约下可独立冻结、重放、执行和评价的最小单位；`Episode` 是固定候选在固定 TaskSample 上的一次完整执行。运行的不可省略定位是：

```text
EvaluationUnit = CandidateVersion × SampleVersion × RunIndex
```

Sample can be independently frozen, replayed, executed, and evaluated under one task contract. 从告警级改为事故级会创建新的 Sample 和 Task 版本，并重新批准试验。

## source_evidence

记录可接受的证据 ID、事实边界、来源日期、许可证和可复现状态。

## raw_materials

描述原始任务材料、来源、授权、脱敏和版本。

## sample_semantic_spec

定义 `SampleSemanticSpec`，即样本类型而不是某条业务数据：

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

必须冻结 `sample_spec_id`、`version`、`task_spec_ref`、样本层级和单位描述；明确输入与上下文 schema、期望输出契约、`temporal_boundary`、`grouping_rule`、`identity_rule`、标签或 Oracle、`replay_contract`、指标适用范围、敏感性政策及 provenance 要求。时间边界防止未来信息泄漏；分组与身份规则防止同一业务事件重复计数；重放契约指定输入、环境快照、模拟器与允许的外部依赖。

## samples

保存不可变、可寻址的 `Sample` 实例。它由一个或多个 `SourceObservation` 组成，并在当前契约下成为 `TaskSample`：

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

每条记录必须列出不可变 `sample_id`、版本、样本规格引用、原始观察引用、输入/上下文快照引用及哈希、期望契约引用、事件/截止时间、分组键、split 成员资格、敏感性、provenance 和内容哈希。候选运行时不得改变样本边界；sealed holdout 可隐藏 `expected_contract_ref` 内容，但必须保留仅审计者可解析的受控引用，候选、Prompt 和普通执行 Agent 不得读取。

## sample_set_manifests

所有样本划分使用带版本、内容哈希与访问策略的 `SampleSetManifest`，而不是模糊的“数据集”：

```text
SampleSetManifest = {
  sample_set_id, version, purpose,
  sample_spec_ref, sample_refs,
  selection_rule, distribution_summary,
  access_policy, frozen_at, content_hash
}

adaptation: SampleSetManifest(version, content_hash, access_policy)
validation: SampleSetManifest(version, content_hash, access_policy)
sealed_holdout: SampleSetManifest(version, content_hash, access_policy)
stress_and_failure: SampleSetManifest(version, content_hash, access_policy)
```

每份 manifest 必须列出不可变 `sample_set_id`、版本、purpose、样本规格引用、`sample_refs`（因此明确 split 成员资格）、选择规则、分布摘要、访问策略、冻结时间和内容哈希。相同 `content_hash` 不得跨集合出现；按事故、客户、仓库、环境、模板或时间相关的样本必须分组切分，禁止把同一业务事件的近重复观察随机拆开。

### adaptation

`purpose=adaptation`；允许内循环查看输出和反馈。其版本化 manifest 的 `access_policy` 必须只授予获准的局部适配主体。

### validation

`purpose=validation`；用于候选选择和外循环更新。其版本化 manifest 的 `access_policy` 不得允许以 sealed holdout 内容影响候选。

### sealed_holdout

`purpose=sealed_holdout`；仅供候选冻结后的最终独立审计。其 version、content_hash 和受控 `access_policy` 必须使 GovernanceAuditor 独占解析 `expected_contract_ref` 和结果，任何基于该集合的候选修改都会使本轮失效。

### stress_and_failure

`purpose=stress_and_failure`；覆盖错误输入、工具故障、权限拒绝、超时和不安全动作。其 version、content_hash 和 `access_policy` 必须支持受控故障注入与可重放验证。

## task_semantic_spec

定义冻结的任务目标、样本分布、输出、指标、聚合、阈值、预算、风险、失败成本、Human 边界和证据要求：

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

示例只能帮助理解，不能替代冻结的 `SampleSemanticSpec`、Sample 或 `SampleSetManifest`。目标、样本分布、指标、权衡、聚合规则或验收标准变化时，必须产生新 Task 版本并重新批准比较。

## capability_semantic_registry

定义可用的 Rule、Algorithm、Model、Skill、Tool、MCP、Memory、State、Communication 和 Human 能力及其契约、权限与约束。

## task_capability_alignment

记录完整覆盖、部分覆盖、缺失、冲突、权限受限和不可验证的任务要求。

## candidate_space

定义合法的 Agentless、固定 Workflow、单 Agent、多 Agent、Human 混合、降级和拒绝候选，不预设赢家。

## budgets

定义成本、时延、步骤、token、计算资源和人工复核预算。

## safety_constraints

定义数据、权限、审批、回滚、审计、拒绝和 Human 责任边界。

## evaluation_protocol

定义 baseline、样本级执行、指标、硬门禁、Pareto 比较、消融、统计或人工复核、停止和拒绝规则。每项指标必须记录 sample unit、denominator、aggregation、missing samples、failed samples 和适用范围；项目级结果只能由预先冻结聚合规则下的 `SampleEvaluation[]` 产生，禁止只汇报成功 Episode。

```text
SampleEvaluation = {
  candidate_version, sample_version, run_index,
  seed, environment_snapshot, budget_snapshot,
  result_ref, trace_ref, metric_values,
  status, failure_class, human_actions
}
```

`Inner Epoch` 是固定候选完整处理一轮 adaptation SampleSet；`Outer Generation` 在 validation SampleSet 上选择候选并更新架构。

## expected_artifacts

至少包含 `SampleSemanticSpec`、`Sample[]`、`SampleSetManifest[]`、`TaskSemanticSpec`、`CapabilitySemanticRegistry`、`AlignmentReport`、`CandidateGraphSet`、`TrialSpec`、`SampleEvaluation[]`、`EvaluationRun[]`、`ExecutionTrace[]`、`EvaluationReport`、`ArchitectureDecision`、`DeliveryDecision`，以及对应的方案包、保留人工或拒绝记录。

## provenance_and_license

记录数据血缘、来源版本、许可证、第三方依赖、商业服务和再分发约束。
