# AgentFit 架构

> 本文档是 AgentFit 当前架构的唯一规范正本。架构演化直接修改本文档，由 Git 历史记录变化。

## 目标与边界

AgentFit 把业务材料整理为可执行样本，从最简 Agent 方案起步，在批量运行中收集 Trace、归因失败、提出变更、回归验证并收敛，最终交付边界明确、证据可复验的 Agent 方案包。

AgentFit 不实现新的 Agent 运行时，也不把某个平台写入核心库。AgentTeams、τ²-bench 和其他运行环境均通过 `bridges/` 接入；`src/agentfit/` 只依赖稳定的领域合同和适配器接口。

## 单正本原则

- 每个活构件只有一个稳定名称和一个正本位置，直接原位迭代。
- 源码、架构文档、Skill、配置、桥接清单和部署对象不使用版本后缀、阶段后缀或“最终版”后缀。
- Git 历史记录活构件的演化，不在仓库中维护并行的旧副本。
- 协议版本、发布包版本、外部依赖版本可以作为兼容性元数据保留。
- 实验快照使用不可变 `run_id`、内容哈希和快照引用；它们是证据身份，不是并行活构件。
- `competition/2026-08-16/submission/` 是已提交的冻结档案，不参与后续改写。

## 双层架构

### 元层：训练者

元层负责理解材料、组织训练、诊断失败、生成方案变更和保护证据边界。

| 组件 | 类型 | 职责 |
|---|---|---|
| Steward | 认知角色 | 材料操作化、澄清、解释；用户唯一对话入口 |
| Attributor | 认知角色 | 对失败 Episode 自底向上归因并给出置信度 |
| Architect | 认知角色 | 构建最简候选、聚合失败、提出分层变更 |
| Orchestrator | 确定性官员 | 状态机、路由、预算、收敛和门禁调度 |
| Validator | 确定性官员 | 依赖约束、正则、回归和提交裁决 |
| Auditor | 确定性官员 | 证据落盘、哈希链、成本和漂移告警 |
| Human Gate | 外部裁决者 | 冻结样本、批准变更、调整目标、确认交付 |

只有 Steward、Attributor、Architect 需要 LLM 认知槽位。确定性官员不得由概率性模型替代。所有角色通过消息总线协作，不直接互相调用。

### 对象层：被训练方案

| 层 | 内容 | 约束 |
|---|---|---|
| L1 Solid | API、数据库、知识库、文件系统、人工审核等真实原子能力 | 必须对应已确认基础设施 |
| L2 Capability | 对 L1 的安全包装、组合、统一口径和送审路由 | 只能引用 L1，不同 L2 不互调 |
| L3 Knowledge | Skill、路由规则、排查链、阈值和经验 | 只能使用 L2，执行时不互调 |
| L4 Topology | Agent 数量、角色、通信边、行为序列和人工位置 | 只能使用 L3，复杂化必须有样本证据 |

纵向执行必须遵守 `L4 → L3 → L2 → L1`；每个声明都必须能追溯到下层真实支撑。多层变更由 `ChangeTransaction` 自底向上原子应用，验证或回归失败则整体回滚。

## 样本与证据合同

三个概念必须分开：

- `SourceObservation`：业务材料中的原始事实、日志、流程片段或人工描述。
- `TaskSample`：从一个或多个 Observation 编译出的可执行任务，包含输入、期望、约束与评价方式。
- `Episode`：某个候选方案在某个冻结样本上的一次实际运行，包含 `run_index`、Trace、结果、成本与证据引用。

训练开始前必须冻结四个互不混用的样本集合：

| 集合 | 用途 | 访问规则 |
|---|---|---|
| adaptation | 方案更新所用样本 | 训练循环可读取 |
| validation | 候选选择与回归 | Validator 可读取，不用于直接归纳规则 |
| sealed_holdout | 最终泛化验证 | 候选冻结后仅 Auditor/Validator 可读取结果 |
| stress_and_failure | 极端、组合与失败模式 | 用于边界和鲁棒性评估 |

每个集合由一个不可变 `SampleSetManifest` 描述，至少包含稳定集合名、内容哈希、成员引用、访问策略和 Human Freeze 记录。一次评价单元由 `candidate_ref + sample_ref + run_index` 唯一确定；引用使用内容哈希或不可变运行引用，不把迭代号写进活构件名称。

## 训练闭环

1. Steward 将材料编译为 Observation、TaskSample 和评价合同。
2. Human 冻结四个 SampleSetManifest、目标权重、预算和权限。
3. Architect 构建 Simple First 候选，并通过存在依赖验证。
4. Orchestrator 在 adaptation 批次运行 Episode，Executor 返回 Trace。
5. Attributor 对失败 Episode 归因；Architect 聚合并提出 ChangeProposal。
6. Human Gate 批准或拒绝需要裁决的变更；Validator 原子应用并执行 validation 回归。
7. Auditor 保存消息、Trace、事务、成本、哈希链和拒绝理由。
8. 达到目标后冻结候选，再运行 sealed holdout 和 stress_and_failure。
9. Human 确认交付边界，导出方案包、证据包和桥接部署包。

## Human Gate

- G0：冻结样本集合、评价方式、预算、权限和目标权重。
- G1：批准方案变更；不响应即不应用。
- G2：批准超出自动调整范围的目标权重变化；不响应即保持不变。
- G3：确认交付形态、适用边界和交付条件；批准决策必须用仓库外密钥签名，不响应或签名不可验证即不交付。
- 低置信归因、基础设施缺失、拓扑变化和预算风险必须升级 Human。

测试可以注入显式的自动裁决器，但生产默认不得自动批准。

## Skill 与认知适配

`src/agentfit/skills/` 中每个稳定文件名对应一个 Skill 正本。运行时通过 Skill Registry 加载，不在 AgentTeams YAML、Prompt 或其他文档中复制一份正文。桥接层只读取 Registry 输出并转换为目标平台格式。

LLM、检索、沙箱和 Human Review 均通过通用 Protocol 注入。核心训练逻辑不得读取 AgentTeams、τ²-bench 或供应商专用对象。

## 桥接层

### AgentTeams

`bridges/agentteams/` 负责：

- 从核心角色和 Skill 正本生成稳定名称的 Team 清单；
- apply/reconcile/status 回读；
- 把 Team 消息转换为核心 TaskMsg；
- 把核心 ResultMsg、方案包和证据引用转换为 AgentTeams 可消费对象；
- 检测部署态是否与 Git 正本一致。

AgentTeams Team 的稳定名称为 `agentfit`。部署修订信息只写入 provenance，不进入 Team、Worker 或项目名称。

### τ²-bench

`bridges/tau2bench/` 负责：

- 把 τ² 任务转换为 TaskSample；
- 以核心 Executor 接口运行候选；
- 把真实 simulation、reward、tool call、成本和错误转换为 Episode/Trace；
- 写入 RunStore 后重新计算哈希链，不伪造“已验证”状态。

## RunStore 与交付物

RunStore 是一次运行的不可变证据目录，至少包含：

- run manifest 与输入 SampleSetManifest 引用；
- 候选快照及内容哈希；
- Episode、Trace、LossTrace、消息因果链；
- ChangeTransaction、Human 决策和回归结果；
- 与候选和最终证据哈希绑定的 G3 交付决策；
- 真实成本、正则、边界和收敛结果；
- 可重算的哈希链与验证结果。

最终交付包含三个独立但可追溯的部分：

1. 核心 `solution_package`：结构化 L1-L4 方案、Human Gate 和监控策略。
2. `evidence_package`：样本引用、Episode、指标、事务、边界与哈希证明。
3. 平台桥接包：由目标平台桥接器生成，保持稳定部署名称。

任何报告只能根据 RunStore 中真实存在的证据得出结论。人工样本不得计入全自动覆盖；空哈希不得标为有效；未运行的阶段必须标记为未执行。

## 验证门禁

- 单元测试覆盖确定性 ID、λ 调整、边界分类、哈希链、事务和四层依赖。
- 合同测试覆盖四类 Manifest、Human Freeze、访问隔离和评价身份。
- 桥接测试覆盖双向转换、稳定名称和部署漂移检测。
- 全链测试覆盖 `材料 → 样本 → 冻结 → 候选 → Episode → 归因 → 更新 → 回归 → 交付`。
- CI 扫描活构件中的版本化名称，并保护冻结提交目录。
- 模拟器通过只证明核心闭环；真实平台和真实 bench 必须分别提供运行证据。
