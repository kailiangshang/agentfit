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

当前材料合同不接受 `backend`、MCP、函数或 Memory 等运行绑定字段；这类字段必须由 bridge 解析。历史 RunStore 是不可变证据，不做原地迁移；需要复验历史证据时使用生成它的 Git 提交，当前 CLI 只验证当前正本合同。

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
| L1 Solid | 最小原子能力合同：标识、读写类型、输入输出与作用语义 | 不声明 API、MCP、函数或供应商后端 |
| L2 Capability | 可复用能力合同：组合哪些 L1、前后置条件、聚合和 Human Gate | 只能引用 L1，不同 L2 不形成隐藏调用链 |
| L3 Knowledge | Skill、路由规则、排查链、阈值和经验 | 只能使用 L2，不形成隐藏的同层执行依赖 |
| L4 Topology | Agent、角色、显式通信边、触发方式和人工位置 | 只能使用 L3；同层协作必须是可审计的显式边 |

纵向存在依赖遵守 `L4 → L3 → L2 → L1`。L1–L3 禁止隐藏的同层执行依赖，L4 只允许通过显式 TopologyEdge 通信。多层变更由 `ChangeTransaction` 自底向上原子应用，验证或回归失败则整体回滚。

四层回答的是“方案里有什么、各自负责什么、如何连接”，不回答“目标平台具体如何实现”。例如 L2 能力可以由 MCP、原生函数、HTTP 或脚本实现；Memory 可以由上下文、文件、数据库或平台对象承载。`src/agentfit/` 不选择这些实现，Executor 或 `bridges/` 在运行时解析，并把平台、部署、沙箱和模型引用写入 `runtime_ref` 证据。当前 Python 类型名 `CapabilityTool` 表达的是 L2 能力合同，不是已绑定的运行时 Tool。

候选方案错误与运行环境错误必须分开。只有完成的 Trace 才能进入 L1–L4 归因与方案更新；沙箱不可用、协议错误、超时或平台故障写成 `result=ERROR`、`error_scope=runtime`。运行环境错误不得归因到 L1–L4，也不得据此增加 Tool、Skill、Memory 或 Agent。

## 样本与证据合同

三个概念必须分开：

- `SourceObservation`：业务材料中的原始事实、日志、流程片段或人工描述。
- `TaskSample`：从一个或多个 Observation 编译出的可执行任务，包含输入、期望、约束与评价方式；每个 ObservationRef 同时绑定稳定 ID 和内容哈希。
- `Episode`：某个候选方案在某个冻结样本上的一次实际运行，包含 `run_index`、Trace、结果、成本与证据引用。

训练开始前必须冻结四个互不混用的样本集合：

| 集合 | 用途 | 访问规则 |
|---|---|---|
| adaptation | 方案更新所用样本 | 训练循环可读取 |
| validation | 每个 Epoch 结束后的候选选择、退化判断和 Early Stopping | Validator/Auditor 可读取，不用于直接归纳规则或修改方案 |
| sealed_holdout | 最终泛化验证 | 候选冻结后仅 Auditor/Validator 可读取结果 |
| stress_and_failure | 极端、组合与失败模式 | 用于边界和鲁棒性评估 |

每个集合由一个不可变 `SampleSetManifest` 描述，至少包含稳定集合名、内容哈希、成员引用、访问策略和 Human Freeze 记录。一次评价单元由 `candidate_ref + sample_ref + run_index` 唯一确定；引用使用内容哈希或不可变运行引用，不把迭代号写进活构件名称。

训练和外部评价都用持久化 `CandidateManifest` 的规范内容哈希确定候选身份，而不是用显示名称或调用方传入的裸哈希。运行绑定不进入四层 Candidate；每个 Trace/Episode 另以 `runtime_ref` 绑定本次 Executor、平台部署和沙箱 provenance。评价身份始终是 `candidate_ref + sample_ref + run_index`。外部 bench 的每条原始记录还必须生成平台无关的 `ExternalEvidenceRecord`，逐条绑定来源记录、CandidateRef、TaskSampleRef、Trace、结果和成本，并形成独立内容哈希链。内部一致性哈希用于发现证据不一致，来源真实性仍需外部签名或可信存储锚点。

## Batch、Step、Epoch 与验证边界

AgentFit 借鉴机器学习的训练纪律，但更新的是四层 Agent 方案而非模型权重。训练调度使用以下唯一语义：

- `Batch`：从 adaptation manifest 取得的一组训练样本；不同 manifest 的样本不得混入同一 Batch。
- `Step`：当前 Candidate 在一个 adaptation Batch 上前向执行，随后完成 Trace 归因、局部 ChangeProposal、反向依赖传播、G1、ChangeTransaction 和回归。一次 Step 不是一个 Epoch。
- `Epoch`：一次完整的 adaptation 数据遍历，包含一个或多个 Step。一个 Epoch 覆盖一次完整的 adaptation 集合；除非 G0 明确批准有放回采样，否则每个 SampleRef 在同一 Epoch 只进入一个 Batch。
- `Validation`：Epoch 结束后冻结当时的 Candidate，再只用 validation manifest 运行评价。Validation 不产生 ChangeProposal，不向 Architect 暴露样本内容或逐样本答案。
- `Early Stopping`：Validator 根据连续 validation 指标、Objective、退化情况、预算和未解决风险决定候选晋升、继续训练、恢复已保留候选或停止；停止条件和窗口必须在 G0 固定。

Epoch 结束后不默认重放完整 adaptation。训练指标由本 Epoch 各 Batch 的实际 Episode 聚合；如果为诊断显式执行完整训练集重放，必须记为 `train_replay`，单独核算成本，不得冒充 validation 或最终泛化证据。回归池用于检查已通过的 adaptation 行为是否遗忘，也不等同于 validation。

validation 结果不得直接生成或修改 L1–L4，也不得把 validation Trace、标签或逐样本结论回流给 Attributor/Architect。Validation 只控制候选选择、退化处理、是否继续下一 Epoch 和 Early Stopping；下一轮方案更新仍只能由 adaptation Episode 驱动。sealed_holdout 与 stress_and_failure 在最终 Candidate 冻结后执行，结果同样不得回流训练。

## 训练闭环

1. Steward 将材料编译为 Observation、TaskSample 和评价合同。
2. Human 冻结四个 SampleSetManifest、目标权重、预算和权限。
3. Architect 构建 Simple First 候选，并通过存在依赖验证。
4. Orchestrator 开始一个 Epoch，按预先冻结的调度把 adaptation 划为一个或多个 Batch。
5. 每个 Step 用当前 Candidate 运行一个 Batch；Attributor 只对该 Batch 的失败 Episode 归因，Architect 提出局部 ChangeProposal，并沿反向依赖传播上层影响。
6. Human Gate 批准或拒绝完整变更集；Validator 用 ChangeTransaction 原子应用，并用回归池检查 adaptation 历史行为，失败则整体回滚。
7. Epoch 的所有 Batch 完成后冻结 Candidate；Validator 只用 validation manifest 评价并执行候选选择、退化判断和 Early Stopping，Validation 不产生 ChangeProposal。
8. Auditor 保存 Batch、Step、Epoch、消息、Trace、事务、validation、成本、哈希链和拒绝理由；未停止时由下一 Epoch 的 adaptation Episode 继续驱动更新。
9. 达到停止条件后冻结最终 Candidate，再运行 sealed_holdout 和 stress_and_failure。
10. Human 确认交付边界，导出方案包、证据包和桥接部署包。

结构化 Material Bundle 由平台无关的 `src/agentfit/materials/compiler.py` 确定性编译。非结构化文件解析或 LLM 抽取属于桥接适配，不得改变上述输出合同。仓库只跟踪材料源；编译生成的 case 是可再生输出，不作为第二个活构件正本。

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
- 通过 `AgentTeamsSandboxExecutor` 把四层 Candidate 和 TaskSample 发到隔离 Worker；
- 将在线或离线 `agentfit.agentteams-result` 标准化为 Trace/Episode 并写回 RunStore；
- 在平台侧把 L1/L2 合同解析为实际 MCP、原生函数、HTTP、脚本或 Memory 载体；
- 检测部署态是否与 Git 正本一致。

AgentTeams Team 的稳定名称为 `agentfit`。部署修订信息只写入 provenance，不进入 Team、Worker 或项目名称。

### τ²-bench

`bridges/tau2bench/` 负责：

- 读取调用方显式提供的候选语义声明，禁止用展示 label 代替 CandidateManifest；
- 在 bridge 内维护 τ² 原始记录的唯一规范投影，并把该投影作为平台无关回调交给
  RunStore 校验器；
- 把 τ² 任务转换为 TaskSample；
- 以核心 Executor 接口运行候选；
- 把真实 simulation、reward、tool call、成本和错误转换为 Episode/Trace；
- 保存原始上传字节、持久化 CandidateManifest，并生成逐条 ExternalEvidenceRecord；
- 在临时兄弟目录完成验证后原子发布 RunStore，不伪造训练 Epoch 或“已验证”状态。

## RunStore 与交付物

RunStore 是一次运行的不可变证据目录，至少包含：

- run manifest 与输入 SampleSetManifest 引用；
- 候选快照及内容哈希；
- Episode、Trace、LossTrace、消息因果链；
- ChangeTransaction、Human 决策和回归结果；
- 与候选和最终证据哈希绑定的 G3 交付决策；
- 真实成本、正则、边界和收敛结果；
- 可重算的哈希链与验证结果。

`run_kind=training` 与 `run_kind=external_evaluation` 使用不同产物合同。训练运行拥有四集合、Solution 快照、Epoch、事务和 G3；外部评价只拥有原始结果、CandidateManifest、TaskSample、ExternalEvidenceRecord、Trace、Episode 和评价汇总，不得混入训练或交付产物。

### Dashboard 呈现合同

训练 Dashboard 固定使用一个八区正本，顺序为：运行概览、四集合验收、材料与四层映射、样本与聚类分组、训练曲线、损失归因全景、L1-L4 方案证据与版本演化、事务与中间链路。新增证据必须归入对应区块，不得通过新增或重命名一级区块形成另一套 Dashboard 结构。

- 运行概览用非技术语言说明初始测试、失败原因、方案更新、回归结果和最终验收状态，同时保留平台、模型与执行边界。
- 四集合验收同时呈现集合汇总和逐样本最终证据；运行错误不得混作业务失败或隐藏在总通过率中。
- 训练曲线必须分开展示 adaptation Batch 指标和 validation 曲线；`train_replay`、validation、sealed_holdout 与 stress_and_failure 不得混成一条通过率。
- 训练曲线、损失归因、方案演化和事务链路分别承载 Step/Epoch 过程、原因、变更和审计证据，不在概览区重复堆叠底层字段。
- Dashboard 的基本证据必须由静态 HTML 直接呈现；JavaScript 只允许增强交互，不得成为看见八区内容的前置条件。
- 外部评价 Dashboard 继续使用独立的最小证据视图，不伪造训练八区、Epoch、Solution 演化或 G3。

## 当前实现边界

| 架构关注点 | 当前状态 | 稳定边界或缺口 |
|---|---|---|
| 材料、样本、四集合、能力清单和 Objective | 已实现平台无关合同 | `materials/`、`models/project.py`、`models/objective.py` |
| 训练、归因、事务、回归和四集合验收 | 单 Batch 更新、事务、回归与最终四集合调度已实现 | 当前 `run_epoch` 实际只运行一个 Batch，并在更新后重放 adaptation；规范 Epoch、Epoch 末 validation、Early Stopping 和反向可达性归因尚未实现 |
| 认知、检索和沙箱 | 仅有 Protocol | `adapters/protocols.py`，尚未注入认知角色和状态机 |
| 候选与运行身份 | 已实现分离证据 | CandidateManifest 绑定四层语义；`runtime_ref` 绑定 Executor/平台/沙箱 |
| AgentTeams | 生成、状态、按运行创建隔离 Worker、真实 Matrix/DeepSeek 执行、Candidate 更新和四集合结果往返已实现 | 12 样本已运行；集合级会话隔离、成本可观测和真实副作用尚未完成 |
| 运行绑定 | 核心保持实现无关 | 每个 bridge 按目标平台解析能力和 Memory；不要求核心自动部署某种技术 |
| RunStore 可信存储 | 内容哈希、验证、训练证据和外部评价原子发布已实现 | Batch/Step/Epoch、validation 与可选 `train_replay` 仍需分型落盘 |
| 正则 | 已接入结构、行为、成本和回归约束 | 新指标只在目标函数或真实失败证据需要时增加，不追求固定数量 |

最终交付包含三个独立但可追溯的部分：

1. 核心 `solution_package`：结构化 L1-L4 方案、`capability_contracts`、Human Gate 和监控策略。
2. `evidence_package`：样本引用、Episode、指标、事务、边界与哈希证明。
3. 平台桥接包：由目标平台桥接器生成，保持稳定部署名称。

任何报告只能根据 RunStore 中真实存在的证据得出结论。人工样本不得计入全自动覆盖；空哈希不得标为有效；未运行的阶段必须标记为未执行。

## 验证门禁

- 单元测试覆盖确定性 ID、λ 调整、边界分类、哈希链、事务和四层依赖。
- 合同测试覆盖四类 Manifest、Human Freeze、访问隔离和评价身份。
- 状态机测试覆盖一个 Epoch 完整且不重复地消费 adaptation、Epoch 末只运行 validation、Validation 不产生 ChangeProposal，以及 Early Stopping 的确定性判定。
- 桥接测试覆盖双向转换、稳定名称和部署漂移检测。
- 全链测试覆盖 `材料 → 样本 → 冻结 → 候选 → Episode → 归因 → 更新 → 回归 → 交付`。
- 仓库级测试扫描活构件中的版本化名称，并用摘要保护冻结提交目录。
- CI 工作流尚未接入；接入后只调用同一组仓库门禁，不维护第二套规则。
- 模拟器通过只证明核心闭环；真实平台和真实 bench 必须分别提供运行证据。
