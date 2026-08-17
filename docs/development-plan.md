# AgentFit 开发计划

本文档只描述当前正本之后仍需推进的工作。完成项由 Git 历史和测试证明，不在仓库中保留并行方案副本。

## 当前可运行基线

| 能力 | 当前状态 | 证据 |
|---|---|---|
| 四层 Solution 与存在依赖验证 | 已实现 | `src/agentfit/models/solution.py`、`src/agentfit/solution/validator.py` |
| SourceObservation、TaskSample、Episode | 已实现合同 | `src/agentfit/models/sample.py` |
| 四类冻结 SampleSetManifest | 已实现合同与访问门禁 | `src/agentfit/models/manifest.py` |
| 训练、归因、建议、事务、回归、正则 | 已实现确定性内核 | `src/agentfit/core/`、`src/agentfit/agents/orchestrator.py` |
| Skill Registry 与认知角色装配 | 已实现 | `src/agentfit/skills/registry.py`、`src/agentfit/agents/team.py` |
| 生产 Human Gate 默认阻断 | 已实现 | `src/agentfit/gates/human.py` |
| RunStore、报告、Dashboard、方案包、证据包 | 已实现 | `src/agentfit/store/`、`src/agentfit/delivery/` |
| 稳定核心 CLI | 已实现 | `agentfit train/validate/report/export` |
| AgentTeams 生成、状态与漂移桥接 | 已实现离线合同 | `bridges/agentteams/` |
| τ²-bench TaskSample、Trace、Episode 转换 | 已实现离线合同 | `bridges/tau2bench/` |

这张表只代表模块和离线测试存在，不代表真实平台运行、真实业务效果或最终泛化已经完成。

## 最高优先级工作

### 材料编译闭环

把文件、流程、日志和人工描述转成可追溯的 `SourceObservation`，再编译为 `TaskSample`。需要补齐：

- 材料解析器和 Observation Store；
- Observation 到 TaskSample 的证据引用；
- 样本冲突、缺失和重复检查；
- Human G0 的冻结交互，而不只接受已经批准的 JSON。

完成定义：任意 TaskSample 都能回溯到原始材料片段，修改材料会改变内容哈希并使旧冻结失效。

### 四集合评价生命周期

当前 CLI 只用 adaptation 训练，并生成 adaptation Episode；validation、sealed holdout 和 stress 集合已有合同，但尚未形成完整运行调度。下一步需要：

- 显式 Candidate Freeze；
- validation 只做选择和回归，不直接生成规则；
- Candidate Freeze 后才允许 sealed holdout 和 stress 运行；
- 四集合指标分别报告，不把训练通过率当泛化结果；
- G3 必须发生在最终评价之后。

完成定义：报告中的每个结果都由 `candidate_ref + sample_ref + run_index` 对应的 Episode 重算。

### 生产认知适配器

Steward、Attributor、Architect 已有稳定角色与 Skill，核心也已在 `src/agentfit/adapters/protocols.py` 留出平台无关合同，但当前认知实现仍以确定性内核为主。下一步需要在桥接侧实现并注入：

- LLM 调用与模型清单；
- 检索与证据引用；
- 沙箱工具执行；
- 预算、超时、重试、结构化输出和错误分类。

完成定义：更换 LiteLLM、直连 API 或 AgentTeams 时，`src/agentfit` 的领域合同和训练状态机不改变。

### 真实桥接验证

- AgentTeams：先用 `--status-only` 输出精确 drift，再由维护者确认 apply 或删除；不得按前缀批量删除。
- τ²-bench：保留原始 results、模型和成本 provenance，再转换为 TaskSample、Trace、Episode。
- 每次真实运行使用独立 RunStore，不覆盖 smoke 或历史证据。

完成定义：平台运行、核心模拟器和 bench 结果各有独立证据，任何一种都不冒充另外一种。

## 后续工作

- 扩展材料类型、行业 Sample Compiler 和安全策略；
- 增加多模型、多目标和多次运行的统计比较；
- 建立方案资产目录、漂移监控和回归触发器；
- 增加发布包兼容性、迁移和长期维护策略；
- 在真实项目中验证成本、延迟、安全和维护性，而不只优化通过率。

## 每次合入门禁

1. 活构件稳定命名，原位修改，Git 记录演化。
2. `competition/2026-08-16/submission/` 摘要不变。
3. 行为变更先有失败测试，再实现通过。
4. 核心不导入 AgentTeams、τ²-bench 或供应商 SDK。
5. 报告从 RunStore 重算；空证据、未运行阶段和人工处理不得伪装成自动成功。
6. 运行 `pytest`、桥接生成物检查、编译检查和 `git diff --check`。
