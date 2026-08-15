# AgentFit 开放与合规披露

> 状态:披露内容 `READY`;真实开放、开源和 AgentFit 运行仍未发生。本文件覆盖开放范围、协议、依赖、商业 API、闭源模型、数据授权、脱敏、可复现方式、部署依赖和后续维护计划。

## 事实源

本清单从以下文件派生:

- [AgentFit 整体方案](../../../docs/agentfit-solution.md) §12.5(事实边界)、§13(未实现范围与启动门禁)。

## 1. 开放范围

### 1.1 计划开放（当前尚未发布）

| 资产 | 开放形式 | 状态 |
|---|---|---|
| 样本语义 Schema(SampleSemanticSpec) | 结构化 Schema 文档 + JSON/YAML 样例 | 计划中,尚未实现或发布 |
| 冻结样本集合 Schema(SampleSetManifest) | 结构化 Schema 文档 + JSON/YAML 样例 | 计划中,尚未实现或发布 |
| 样本级评价 Schema(SampleEvaluation) | 结构化 Schema 文档 + JSON/YAML 样例 | 计划中,尚未实现或发布 |
| split-leakage schemas(SplitLeakagePolicy / SplitLeakageReport) | 分组泄漏、重复 content_hash、cutoff 与隔离审计的结构化 Schema 文档 + 样例 | 计划中,尚未实现或发布 |
| 任务说明书 Schema(TaskSemanticSpec) | 结构化 Schema 文档 + JSON/YAML 样例 | 设计中,后续阶段是否开放取决于晋级结果与授权 |
| 能力语义 Schema(CapabilitySemanticSpec) | 结构化 Schema 文档 + 样例 | 设计中,后续阶段是否开放取决于晋级结果与授权 |
| 执行轨迹 Schema(ExecutionTrace) | 结构化 Schema 文档 + 样例 | 设计中,后续阶段是否开放取决于晋级结果与授权 |
| 候选方案描述 Schema(Candidate) | 结构化 Schema 文档 + 样例 | 设计中,后续阶段是否开放取决于晋级结果与授权 |
| 元 Agent Identity 与责任契约 | 本仓库 [agent-identity.md](agent-identity.md) | 私有仓库内完成，尚未发布 |
| 核心 Skill 契约 | 本仓库 [skill-catalog.md](skill-catalog.md) | 私有仓库内完成，尚未发布 |
| 路演 PPT/PDF | 本仓库 [最终提交目录](.) | 私有仓库内最终初赛提交，尚未发布 |

### 1.2 后续阶段候选开放范围

以下不是已承诺计划。只有晋级结果、评审反馈或后续赛程要求继续，且获得明确授权后，才按条件决定是否开放：

| 资产 | 条件 |
|---|---|
| AgentFit 元团队 AgentTeams 配置 | 首个真实 ProjectCase 跑通后 |
| 核心 Skill 实现(S1-S7) | 代码固化并通过干净环境复现后 |
| 首个 ProjectCase 可复现包 | 数据、模型、依赖、配置脱敏后 |
| 统一对照实验(无 Agent/单 Agent/多 Agent)证据 | 真实运行并保留完整 Trace 后 |

### 1.3 不开放

- 原始客户数据、密钥、凭证、内部业务系统访问权;
- 被显式标注为内部材料的 docs/internal/ 下证据研究卡(含第三方 benchmark 的事实摘要,遵循各自 license);
- 未脱敏的 ProjectAsset。

### 1.4 当前仓库与许可事实

- 仓库当前为私有，不得使用“已开源”或“已开放”描述；项目所有者已确认后续将把运行库开源，开源范围与许可证将在冻结后公布；
- 仓库根目录当前没有 AgentFit 项目许可证；
- 对外发布前必须选择项目 License，并完成 AgentTeams、官方 Skills、第三方库、字体、案例材料和数据许可清点；
- 本节是开放计划，不是开放完成证明。

## 2. 依赖清单

### 2.1 平台依赖

| 依赖 | 角色 | 版本 | License |
|---|---|---|---|
| AgentTeams | 运行底座(身份/通信/容器/权限/共享状态/Skill/MCP/Human) | 待真实集成时固定并披露 | 按官方许可 |
| 阿里云官方 Skills | 按必要性复用运行底座类能力 | 按需 | 按官方许可 |

### 2.2 模型依赖

| 依赖 | 角色 | 披露 |
|---|---|---|
| LLM | 任务编译、候选设计、局部推理、审计辅助 | **闭源商业 API**。真实运行时披露具体模型、版本、API 边界、成本与闭源风险 |
| Embedding(如采用) | 文档表示(非主上下文机制) | 真实采用时披露 |

AgentFit 不绑定特定模型。任务说明书、能力库、执行轨迹、审计结论是模型无关的结构化产物;模型是候选的参数 θ,可替换并重新评测。

### 2.3 探索性 Demo 依赖与证据限制

| 资产或依赖 | 当前用途 | 不可作出的声明 |
|---|---|---|
| OpsPilot | 官方案例锚点、材料与设计参考 | AgentFit 已运行、已集成或已得分 |
| τ³-bench retail / airline 材料 | 探索性 Demo 的案例来源 | AgentFit 正式 ProjectCase、Candidate 或官方结果 |
| DeepSeek | retail/airline 探索中的模型提供方 | 经正式模型冻结与统一对照验证的结论 |
| OpenCode | 本地探索的 CLI 运行环境 | AgentTeams 端到端集成 |
| 自建工具、代理评估器 | 检查局部流程与失败模式 | 官方 evaluator、官方 benchmark 成绩或生产效果 |
| 本地路径与原始记录 | 可追溯的本地探索线索 | 可移植、可公开或可复现实验包 |

retail/airline 的 overnight 运行只属于探索性 Demo 证据。其原始记录可能含环境、路径或未脱敏材料，不能因存在于仓库或本机而自动成为可发布的复现实验资产。正式 AgentFit runtime 仍为 `NOT_STARTED`；只有按冻结 ProjectCase、Candidate、TrialSpec、权限、预算和独立审计门禁重新运行，才可形成正式证据。

### 2.4 第三方库与工具

真实实现时在 `pyproject.toml` 或等价文件中固定并披露。当前仓库未锁定实现依赖,因为核心实现尚未完成。

### 2.5 数据来源

| 数据 | 来源 | License / 授权 | 用途 |
|---|---|---|---|
| 官网四类参考案例 | [GOAI Agent Infra 官网](https://goaihz.com/tracks?track=infra) | 官网公开,场景启发,非运行证据 | 附录 A5 来源披露 |
| 参赛手册 | 新智基座 Agent Infra 参赛手册 | 官方文件 | 要求矩阵与红线 |
| 跨场景证据卡(SWE-bench/GAIA/CyBench/τ-bench/CUAD 等) | 各 benchmark 官方 | 各自 license,内部研究用,不二次分发 | 未来 ProjectCase 的任务、能力与评测建模证据;不代表已经选择项目 |

### 2.6 商业 API 与闭源模型披露

AgentFit 的真实运行预期使用商业 LLM API。相关依赖、成本和替换边界将完整披露:

- 真实运行时披露具体模型、API 边界、调用方式、成本口径;
- 不隐瞒任何商业 API 或闭源模型依赖;
- 评测结果中明确标注哪些环节依赖闭源模型,及其可替换性与迁移成本。

## 3. 既有基础与团队新增贡献

### 3.1 既有基础(不构成 AgentFit 贡献)

- AgentTeams 平台(身份、通信、容器、Skill/MCP 绑定、Human 入口等);
- 阿里云官方 Skills;
- 使用的任何开源框架、库、benchmark。

### 3.2 团队新增贡献(AgentFit 独有)

- Sample/Task 编译方法，以及 SampleSemanticSpec、SampleSetManifest、SampleEvaluation 与 split-leakage schemas 的设计契约;
- 能力语义对齐方法与缺口报告;
- 候选图与 Agent 分区(Agentize)必要性判定;
- 无 Agent/单 Agent/多 Agent/人工混合统一对照试验设计;
- 独立审计与 holdout 完整性校验;
- 人工门禁与责任契约模板;
- ProjectAsset/MetaAsset 沉淀与晋升门禁。

## 4. 可复现方式

### 4.1 当前可复现

- 路演 PPT/PDF 生成链:`build_presentation.py` → PPTX → PDF(命令见 [ppt-outline.md](ppt-outline.md));

### 4.2 后续阶段可复现目标

- 元团队 AgentTeams 配置 + 运行入口;
- 首个 ProjectCase 的样例输入输出;
- 统一对照实验的冻结 SampleSetManifest、样本级评价、预算、模型版本、Trace;
- 干净环境复现脚本。

## 5. 部署依赖

真实部署需要:

- AgentTeams 实例(版本待固定);
- 模型 API 访问凭证(由基础设施持有);
- 沙箱执行环境(容器、资源限制、网络隔离);
- 共享存储(项目档案、执行轨迹、决策账本);
- 人工审批入口(AgentTeams Human)。

不部署独立前端;不修改 AgentTeams 核心;不依赖飞书或外部 IM。

## 6. 维护计划

| 阶段 | 维护承诺 |
|---|---|
| 2026-08-15 初赛提交阶段 | 只维护并验证最终提交材料，不以前置开发换取尚不存在的运行结论 |
| 后续阶段 | 由晋级结果、评审反馈、后续赛程和明确授权决定是否维护真实 ProjectCase、可复现实验与 Trace |

## 7. 事实与合规承诺

本项目遵循以下披露原则:

- 不把概念图或本地模拟写成真实运行;
- 不把 DeepSeek + OpenCode 的 retail/airline 探索、代理评估器或本地原始记录写成官方评测、正式 Candidate 或 AgentTeams 集成;
- 不把 AgentTeams 名称当作集成证据;
- 不隐瞒既有仓库、第三方贡献、商业 API 或闭源模型(本文件 §2.6 明确披露);
- 明确披露数据授权、许可证、密钥、权限和依赖的当前状态;
- 设计契约要求高风险动作具备审批、拒绝、回滚和审计;真实链路为 `NOT_STARTED`(见 [risk-and-human-gates.md](risk-and-human-gates.md));
- 不只展示成功,失败、降级、否决证据同等保留;
- 对外材料与内部证据状态一致。

## 8. 当前未实现范围

明确披露以下尚未完成:

- SampleSemanticSpec、Sample、SampleSetManifest、SampleEvaluation、SplitLeakagePolicy、SplitLeakageReport、TaskSemanticSpec、CapabilitySemanticSpec、AlignmentReport、Candidate、CandidateGraphSet、TrialSpec、EvaluationRun、ExecutionTrace、EvaluationReport、DeliveryDecision 的正式机器可执行 Schema;
- 自动候选生成、内外循环搜索、Pareto 选择;
- ProjectAsset/MetaAsset 的正式存储、晋升、回归系统;
- 任一完整 ProjectCase;
- 真实 AgentTeams 元团队、Skill、MCP、共享状态、Trace;
- 统一预算下的无 Agent/单 Agent/多 Agent 真实对照;
- 真实业务或生产效果。

后续工作不会自动启动。只有晋级结果、评审反馈或新的赛程要求继续，且获得明确授权后，才执行:选择并冻结首个 ProjectCase → 在 AgentTeams 跑通最小闭环 → 保留失败或 Human 分支 → 独立审计并复现。真实证据形成后再更新运行状态，不改变已经冻结的产品定义。
