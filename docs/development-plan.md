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
| AgentTeams 生成、状态、按运行创建 Worker、Matrix 执行与结果往返 | 已完成 12 样本 adaptation 更新和四集合真实运行；G3 因 stress ERROR 与成本不可观测拒绝 | `bridges/agentteams/`、`docs/agentteams-live-validation.md` |
| τ²-bench 外部评价转换 | 已实现原始字节、CandidateManifest、逐条外部证据链、TaskSample、Trace、Episode 与原子发布 | `bridges/tau2bench/` |

这张表描述已经存在的模块和已明确列出的运行证据；局部真实联动不代表真实业务效果或最终泛化已经完成。

## 最高优先级工作

### AgentTeams 集合级运行隔离与成本证据

核心已经用 `CandidateManifest` 固定四层候选，用 `runtime_ref` 单独记录 Executor、部署、
Worker 沙箱和模型 provenance；在线 Executor 与离线 importer 共用
`agentfit.agentteams-result` 语义。12 个正式 demo 样本已经完成真实 adaptation、Candidate
更新和四集合运行；下一步由当前 runtime ERROR 证据驱动，不再扩展抽象层：

- 为 adaptation、validation、sealed_holdout、stress_and_failure 使用独立 Worker/Matrix 会话，
  防止长会话上下文污染，同时保持同一 CandidateRef 和全局连续 `run_index`；
- 从 AgentTeams/LiteLLM 运行证据接入可核验 token/cost，只有 `cost_observed=true` 才评价成本门槛；
- 让 stress 产生可评价的 PASS/FAIL，而不是缺信封或身份错误；
- 保留一次格式纠错上限，第二次协议错误仍作为 runtime ERROR；
- 每次真实运行使用独立 RunStore，不覆盖任何成功或失败证据。

完成定义：四集合 12 个最终 Episode 没有平台/协议 ERROR，成本可核验，报告能从
CandidateRef、SampleRef、run_index 和 runtime_ref 回到 Trace；是否通过 Objective 由真实
结果决定，不以降低阈值收尾。

### 真实场景的逐批适配

本地确定性闭环不代表真实业务维护效果。围绕一个真实项目逐步引入 L1、L2、L3、L4
和跨层业务变化，而不是一次建设所有可能的 Tool、Skill 或 Agent。DeepSeek-V4-Flash、
公开数据、Flat→AgentFit 四层维护对照和外部参照边界以
[业务维护评测](benchmark-evaluation.md) 为正本：

当前只建设一个 benchmark adapter：`τ²-bench`。执行范围固定为 telecom 主证明与 retail
复用证明，且严格按以下顺序推进：

1. **telecom 5 题协议与证据 smoke**：先对 `small=20` 执行 pilot G0，在候选生成前冻结
   四个互不重叠的 pilot manifest、Objective、变化材料、预算和权限，再验证 AgentTeams、
   Adapter、reward、Trace、Episode 和 RunStore 完整往返；
2. **telecom 20 题完整维护闭环**：跑完初始基线、五波业务变化、诊断、更新、回归和
   Dashboard，只作工程 pilot；
3. **telecom 74 个 train 样本扩大与优化**：扩大 adaptation/validation，比较更新前后
   业务质量、累计回归、变更范围、达标成本、复用和回滚；
4. **telecom 40 个 official test 封存验收**：两个最终方案 freeze 后才运行，结果不回流；
5. **retail 小规模复用验证**：从已封存的 telecom CandidateRef 投影完整 L1–L4，复用同一
   Adapter、scheduler、scorer 和 Dashboard，通过资产复用账本量化直接复用、局部替换与
   新增，再决定是否扩大。

telecom `full=2,285` 只在 20 题闭环稳定后抽取少量压力样本，不做全量跑分。Terminal-Bench、
MCPAtlas、SWE-bench、CorpusQA、GDPval、Toolathlon 等当前不排期、不开发 Adapter；不能在
telecom → retail 主线完成前并行建设。

每个阶段仍遵守同一实验协议：从同一业务行为生成语义等价的 Flat 与 AgentFit 初始方案；
由 Human 冻结 SampleSetManifest、变化材料和 Objective；两组获得相同 Trace、更新模型、
Human 次数和维护预算；Flat 直接维护资产，AgentFit 按 L1–L4 归因并事务提交；validation
检查新需求和累计旧需求，运行 ERROR 单列；最终方案冻结后再运行 sealed_holdout 和
stress_and_failure。

完成定义：报告能回答四层维护是否以更小变更和更低回归达到相同业务目标；每个结论都
可回到 `candidate_ref + sample_ref + run_index` 对应的 Episode，评价集合结果不会反向
进入 adaptation 更新。

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
