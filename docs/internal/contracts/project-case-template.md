# ProjectCase Contract

> 状态：当前设计契约，尚未实例化真实 ProjectCase。

本文件定义单个 AgentFit ProjectCase 必须具备的结构。它既用于近期 AgentTeams walking skeleton，也可用于后续跨项目研究，但本身不代表任何项目已经获批或运行。

## source_evidence

记录可接受的证据 ID、事实边界、来源日期、许可证和可复现状态。

## raw_materials

描述原始任务材料、来源、授权、脱敏和版本。

## task_semantic_spec

定义目标、输入空间、期望输出、样例、分布、指标、权衡、阈值、预算、风险、失败成本、Human 边界和证据要求。

## capability_semantic_registry

定义可用的 Rule、Algorithm、Model、Skill、Tool、MCP、Memory、State、Communication 和 Human 能力及其契约、权限与约束。

## task_capability_alignment

记录完整覆盖、部分覆盖、缺失、冲突、权限受限和不可验证的任务要求。

## candidate_space

定义合法的 Agentless、固定 Workflow、单 Agent、多 Agent、Human 混合、降级和拒绝候选，不预设赢家。

## adaptation_set

保存内循环允许使用的样例和反馈。

## validation_set

保存候选和架构选择允许使用的样例。

## holdout_set

保存仅供最终独立审计使用的受保护样例。

## stress_and_failure_set

保存错误输入、工具故障、权限拒绝、证据冲突、超时、不安全动作和恢复案例。

## budgets

定义成本、时延、步骤、token、计算资源和人工复核预算。

## safety_constraints

定义数据、权限、审批、回滚、审计、拒绝和 Human 责任边界。

## evaluation_protocol

定义 baseline、指标、硬门禁、Pareto 比较、消融、统计或人工复核、停止和拒绝规则。

## expected_artifacts

至少包含 `TaskSemanticSpec`、`CapabilitySemanticRegistry`、`AlignmentReport`、`CandidateGraphSet`、`TrialSpec`、`EvaluationRun[]`、`ExecutionTrace`、`EvaluationReport`、`ArchitectureDecision`、`DeliveryDecision`，以及对应的方案包、保留人工或拒绝记录。

## provenance_and_license

记录数据血缘、来源版本、许可证、第三方依赖、商业服务和再分发约束。
