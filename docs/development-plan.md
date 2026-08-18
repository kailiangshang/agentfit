# AgentFit 开发计划

本文档只描述当前正本之后仍需推进的工作。完成项由 Git 历史和测试证明，不在仓库中保留并行方案副本。

## 当前可运行基线

| 能力 | 当前状态 | 证据 |
|---|---|---|
| 四层 Solution 与存在依赖验证 | 已实现 | `src/agentfit/models/solution.py`、`src/agentfit/solution/validator.py` |
| SourceObservation、ObservationRef、TaskSample、Episode | 已实现合同与哈希追溯 | `src/agentfit/models/sample.py` |
| CapabilityInventory | 已实现内容寻址、L2→L1 依赖和候选构建门禁 | `src/agentfit/models/project.py` |
| ObjectiveSpec 与 AcceptanceResult | 已实现四集合阈值、内容寻址验收和确定性拒绝 | `src/agentfit/models/objective.py` |
| Material Bundle 编译与核心 CLI | 已实现确定性编译、四集合生成和 RunStore 追溯 | `src/agentfit/materials/`、`agentfit compile` |
| 四类冻结 SampleSetManifest | 已实现合同与访问门禁 | `src/agentfit/models/manifest.py` |
| 训练、归因、建议、事务、回归 | 已实现确定性内核 | `src/agentfit/core/`、`src/agentfit/agents/orchestrator.py` |
| 正则与 λ 调节 | 已接入结构、行为、成本和回归约束 | `src/agentfit/core/regularization.py` |
| Skill Registry 与认知角色装配 | 已实现 | `src/agentfit/skills/registry.py`、`src/agentfit/agents/team.py` |
| 生产 Human Gate 默认阻断 | 已实现 | `src/agentfit/gates/human.py` |
| RunStore、报告、Dashboard、方案包、证据包 | 已实现四集合验收与 G3 状态一致呈现 | `src/agentfit/store/`、`src/agentfit/log/`、`src/agentfit/dashboard/`、`src/agentfit/delivery/` |
| 稳定核心 CLI | 已实现四集合评价、Objective 验收、签名 G3 和拒绝导出 | `agentfit train/validate/report/export` |
| AgentTeams 生成、状态、沙箱执行与结果往返 | 已实现桥接合同和离线测试 | `bridges/agentteams/` |
| τ²-bench 外部评价转换 | 已实现原始字节、CandidateManifest、逐条外部证据链、TaskSample、Trace、Episode 与原子发布 | `bridges/tau2bench/` |

这张表只代表模块和离线测试存在，不代表真实平台运行、真实业务效果或最终泛化已经完成。

## 最高优先级工作

### AgentTeams 真实批次闭环

核心已经用 `CandidateManifest` 固定四层候选，用 `runtime_ref` 单独记录 Executor、部署、
Worker 沙箱和模型 provenance；在线 Executor 与离线 importer 共用
`agentfit.agentteams-result` 语义。下一步不是再设计一套运行描述对象，而是在真实
AgentTeams 上完成小批次：

- 将同一冻结 Candidate 和 TaskSample 批次发送到隔离 Worker；
- 平台桥接按现场条件把 L1/L2 合同解析为 MCP、原生函数、HTTP、脚本或 Memory 载体；
- 在线或离线写回标准 Trace/Episode，保留连续 `run_index`；
- 从 RunStore 重算结果，确认沙箱/协议错误只进入 execution error，不触发四层更新；
- 每次真实运行使用独立 RunStore，不覆盖 smoke 或历史证据。

完成定义：至少一个真实批次能从 Candidate/Task 发出，经过 AgentTeams 隔离 Worker，
再以相同 CandidateRef、SampleRef、run_index 和 runtime_ref 回到 RunStore。

### 真实场景的逐批适配

本地确定性闭环不代表真实模型效果。围绕一个真实项目逐步扩大样本，而不是一次建设
所有可能的 Tool、Skill 或 Agent：

1. 从业务材料编译并由 Human 冻结四个 SampleSetManifest；
2. 先跑最简 Candidate 的 adaptation 小批次；
3. 用 Trace 判断缺口属于 L1、L2、L3 还是 L4，运行 ERROR 单独处理；
4. 只对有证据的缺口提交方案变更并回归；
5. 候选冻结后再运行 validation、sealed_holdout 和 stress_and_failure；
6. 比较质量、成本、风险和复杂度，达到用户 Objective 后停止。

完成定义：报告中的每个结论都可回到 `candidate_ref + sample_ref + run_index` 对应的
Episode，评价集合结果不会反向进入 adaptation 更新。

### 认知角色接入

Steward、Attributor、Architect 已有稳定职责和 Skill，确定性内核仍是裁决边界。下一步
在 AgentTeams bridge 或通用 Protocol 实现中接入真实模型、检索和结构化输出：

- Steward 产出带 ObservationRef 的样本草案，由 Human 执行 G0；
- Attributor 只对非 ERROR Trace 生成带证据引用的归因；
- Architect 只提出四层语义变更，不选择运行实现；
- Orchestrator、Validator、Auditor 继续确定性执行预算、门禁和落盘。

完成定义：切换 LiteLLM、直连 API 或 AgentTeams 模型配置时，`src/agentfit` 的四层合同
与训练状态机不改变。

### 控制与可信呈现

- 贯通仍公开的 `TrainingConfig` 参数与停止原因；
- 对同一候选和样本执行多次独立运行，报告分布而非单次偶然值；
- 补齐 Acceptance、风险事件和 G3 引用的定向篡改测试；
- 报告对“无有效方案评测”、未运行集合、人工处理和运行错误使用独立状态；
- 接入 CI，复用本地同一组门禁，不维护第二套规则。

完成定义：训练停止、四集合验收和 G3 交付是三个独立状态，Dashboard 和报告不互相冒充。

## 后续工作

- 增加非结构化文件解析器和真实 Human G0 冻结交互；
- 扩展材料类型、行业 Sample Compiler 和安全策略；
- 增加多模型、多目标和多次运行的统计比较；
- 建立方案资产目录、漂移监控和回归触发器；
- 按真实部署需要增加发布包兼容性和长期维护策略；
- 只在 Objective 或失败证据需要时增加新的正则指标；
- 在真实项目中验证成本、延迟、安全和维护性，而不只优化通过率。

## 每次合入门禁

1. 活构件稳定命名，原位修改，Git 记录演化。
2. `competition/2026-08-16/submission/` 摘要不变。
3. 行为变更先有失败测试，再实现通过。
4. 核心不导入 AgentTeams、τ²-bench 或供应商 SDK。
5. 报告从 RunStore 重算；空证据、未运行阶段和人工处理不得伪装成自动成功。
6. 运行 `pytest`、桥接生成物检查、编译检查和 `git diff --check`。
