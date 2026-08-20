# AgentTeams 2026-08-18 历史联动证据

状态：`ARCHIVAL_EVIDENCE`。本文档记录 2026-08-18 历史证据及其边界，不作为当前运行入口。
运行目录是忽略的本地证据；仓库只保留实现身份和脱敏结论，不提交 Matrix token、模型密钥
或 Worker 运行密钥。

## 历史术语边界

本文中的 `epoch` 是当时 RunStore 的兼容字段，实际只包含一个 adaptation Batch 更新；
`candidate evaluation` 是更新后对同一 adaptation 集合的 adaptation replay，不构成规范 Epoch 的 validation。历史结果只能证明当时的桥接、局部更新和证据往返，不能证明多 Batch Epoch、
Validation 隔离、Early Stopping、反向依赖传播或训练收敛。表格与 CandidateRef 保持原样，
上述解释只收紧结论边界，不改写历史 RunStore。

## 已验证链路

2026-08-18 使用 AgentTeams v1.1.2、CoPaw Candidate Worker 和
`deepseek/deepseek-chat` 完成单样本握手、多样本 adaptation 更新和四集合评价：

```text
Material Bundle
  -> four frozen SampleSetManifest contracts
  -> CandidateManifest
  -> run-scoped standalone Worker
  -> Matrix task without expected/label
  -> DeepSeek structured result
  -> Trace + Episode + epoch hash chain
  -> adaptation RunStore validation
  -> Worker retirement
```

验收 RunStore：`.local-demo/agentteams/e2/run-20260818-e2-green`。该目录不进入 Git；以下
标识用于在持有本地证据的环境中复核：

| 项目 | 结果 |
|---|---|
| CandidateRef | `d5b7234c203a6be4cadb3257197b9098f67b4986d6f75e943e06a2ebe169e8a7` |
| RuntimeRef | `fba8d91b79d6df791bd3ce05819943c7b7a58758af1e473e2c80ec19f234b14e` |
| adaptation | 1 个 Episode，PASS 1 / FAIL 0 / ERROR 0 |
| 证据完整性 | epoch 哈希链有效；`agentfit validate` 通过 |
| 生命周期 | `IN_PROGRESS`；adaptation `COMPLETE` |
| 最终评价 | `NOT_RUN` |
| 交付 | `NOT_REQUESTED` |
| 成本 | 运行时未提供可核验用量，报告为“不可用” |
| Candidate Worker | 运行完成后已退役 |

真实求解路径由模型返回并转换为标准 Trace：

```text
L3 rule_safe_toggle_roaming_0
  -> L4 solo
  -> L2 safe_toggle_roaming
  -> L1 toggle_roaming
```

该路径的 L1 动作明确标记为 dry-run，无外部副作用。

## 多样本适配与评价结果

正式示例材料已扩展为 12 个 TaskSample，四个 SampleSetManifest 各 3 个。它们来自仓库维护
的 demo 材料正本，不复用 `tests/test_scenarios` 的测试夹具冒充正式样本。

多样本 adaptation RunStore：
`.local-demo/agentteams/live/run-20260818-multi-attribution`。

| 阶段 | CandidateRef | 结果 |
|---|---|---|
| forward | `fe59d78fc66970091010fc3632ea82cdaf47adbdf744fef46149896986146232` | 漫游 PASS、飞行模式 PASS、SIM FAIL |
| 归因 | 同上 | SIM 为 L3 `missing_rule`，置信度 0.7 |
| 变更 | `6ec880d3cc2670743c56283f9499eac62f530583e8f644113e49a2a827a2cee1` | 新增 `rule_safe_run_sim_diagnostics_cc6cbe875e89`，事务 COMMITTED |
| candidate evaluation（adaptation replay） | 更新后 Candidate | 3/3 PASS，ERROR 0 |

该运行的 RuntimeRef 为
`300edd2e87d39b0f92153ebd5ca3e5f6ea91c9405f10eb1327b40933c3cb5322`。
训练与最终评价现在共用全局连续的
`CandidateRef + SampleRef + RunIndex`；验证器会拒绝跨阶段重复或断裂的索引。

完整四集合 RunStore：`.local-demo/agentteams/live/run-20260818-full-retry`。最终 Candidate
仍为上表更新后的 Candidate，结果如下：

| 集合 | PASS / FAIL / ERROR | 结论 |
|---|---:|---|
| adaptation | 3 / 0 / 0 | 质量通过，成本不可核验 |
| validation | 3 / 0 / 0 | 质量通过，未反向更新 Candidate |
| sealed_holdout | 3 / 0 / 0 | 候选冻结后运行，未反向更新 Candidate |
| stress_and_failure | 0 / 0 / 3 | 两条缺结果信封，一条身份回显错误 |

该完整 RunStore 通过 `agentfit validate`，但 Acceptance 和 G3 均拒绝。拒绝原因同时包含
stress runtime ERROR 和四集合 `cost_usd unavailable`。Episode 中的兼容数值 `0.0` 不再被
解释为零成本；`cost_observed=false` 是硬验收失败。

真实尝试均保存在独立忽略目录，未覆盖成功证据：

| RunStore | 观察 | 形成的改进 |
|---|---|---|
| `run-20260818-multi-adaptation` | 1 个结果合同错误、2 个 Matrix timeout | Worker 回包 fail-fast 分类 |
| `run-20260818-multi-contract-diagnostic` | 2 PASS、1 缺信封 ERROR | 明确候选能力不足应返回 completed FAIL |
| `run-20260818-multi-attribution` | 2 PASS + 1 L3 FAIL → 更新后 3/3 PASS | 证明 Trace 驱动的 Candidate 更新 |
| `run-20260818-full-evaluation` | 15 个缺信封 ERROR | 对缺信封增加一次有界格式纠错 |
| `run-20260818-full-retry` | 前三集合 9/9 PASS，stress 3 ERROR | 暴露长会话/复杂任务的隔离缺口 |

## 运行中发现并修复的问题

第一次发送消息时，Candidate 容器虽已处于 Running，但 CoPaw 尚未完成 Matrix 首次同步，
导致消息早于 Worker 可消费窗口。当前 readiness 同时要求容器运行、Room/User 已分配，并且
Worker 的 Matrix sync token 已产生；只看容器状态不再视为 ready。

模型早期回包还暴露了两个协议漂移：遗漏 `schema`，以及把 `risk_events` 返回为对象数组。
Candidate Worker 指令现已固定完整结果形状，要求 `schema=agentfit.agentteams-result`、
`risk_events` 为字符串数组，并限制 `downstream` 为零基步骤索引数组。外部解析器仍执行身份、
类型和 Candidate/Sample/run/runtime 引用校验，不因 Prompt 约束而放松验证。

专用 Candidate 房间中，Worker 的第一条消息若缺少合法信封，会收到一次相同、无标签任务的
格式纠正请求；第二次仍不合法即记为 `agentteams_result_envelope_error`。身份错误不重试，
业务 FAIL 不重试。该策略消除了无意义的长时间 timeout，但没有掩盖模型不稳定。

当前 full run 在同一个 Worker/Matrix 会话中连续执行 adaptation 和四集合，stress 位于长会话
尾部时稳定性下降。下一步应按样本集合创建独立 Worker/会话，同时保持同一 CandidateRef 和
RunStore 全局 run_index；在此之前，不能把前三集合 9/9 扩大为完整泛化结论。

## 证据边界

这次运行证明：

- AgentFit 可以按 run 创建和回收独立 Candidate Worker；
- 无 expected/label 的任务可经真实 Matrix 发送给真实模型；
- 结果可以用同一 CandidateRef、SampleRef、run_index、RuntimeRef 写回 RunStore；
- Runtime ERROR 与 L1–L4 方案失败保持分离；
- adaptation 阶段证据不会冒充四集合验收或 G3 交付。

这次运行不证明：

- MCP、HTTP、脚本或原生函数已经被调用；
- 真实业务写操作、回滚或 Human Gate 已执行；
- stress_and_failure 已获得有效方案评价结果；当前三条均为 runtime ERROR；
- 候选具有泛化能力或已经达到交付 Objective；
- 已完成规范 Epoch、Epoch 末 validation 或 Early Stopping；
- token、费用或延迟已有可核验统计。

## 当前复现状态

当前状态：`BLOCKED_NOT_VERIFIED`。历史运行使用的 `deepseek/deepseek-chat` 路由身份必须保留
用于解释既有 RuntimeRef，但旧命令已经停用，不得据此启动新运行。

当前唯一目标是用户自有 DeepSeek 官网 API 的 `deepseek-v4-flash`。AgentTeams provider 的
官网 base、secret binding 和最小调用尚未形成可核验证据，因此当前不提供可复制的在线执行
命令。完成 `docs/test-scenario.md` 的官网直连预检后，再把新的脱敏复现步骤写入现行指南；
历史 RunStore 继续只读保留，不能覆盖或改写。
