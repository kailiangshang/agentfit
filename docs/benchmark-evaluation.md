# AgentFit × DeepSeek-V4-Flash 业务维护评测方案

> 状态：当前评测与实施正本。初赛提交目录保持冻结。

## 1. 要证明什么

AgentFit 不与模型或 Agent 框架竞争。它要证明的是：面对连续业务变化，把 Agent 方案维护
为 L1 原子能力、L2 能力合同、L3 知识与路由、L4 Agent/Human 拓扑四层，是否比常见的
扁平维护更容易定位问题、减少回归、控制变更范围并复用已有资产。

主实验只比较两个维护组：

| 维护组 | 维护方式 |
|---|---|
| Flat Maintenance Base | 直接维护 AgentTeams 的 Prompt、Tool、Knowledge 和 Team 配置 |
| AgentFit Four-layer Maintenance | 按 L1–L4 归因，以 ChangeTransaction 局部更新、验证或回滚 |

两组使用相同模型、AgentTeams、业务材料、任务、工具、评分器、Trace、Human 次数和预算。
Flat 组不是弱化对照；唯一有意变化的是维护机制。

## 2. 唯一模型与 API

DeepSeek 官网已经正式发布 `deepseek-v4-flash`。当前实验只使用用户自有的 DeepSeek 官网 API：

- API base：`https://api.deepseek.com/v1`；
- model：`deepseek-v4-flash`；
- secret：只从本地 `DEEPSEEK_API_KEY` 或 AgentTeams secret 配置读取；
- 不使用 LiteLLM 网关、代理或路由；
- API key 不写入 Git、RunStore、Trace、日志、Dashboard 或报告。

Agent、用户模拟和诊断调用都固定为同一个 `deepseek-v4-flash`。benchmark 原生的确定性
scorer 仍是主分数；只有 τ²-bench 协议确实要求 LLM judge 时才调用模型，且仍使用相同官网
API。各职责分别记录 prompt hash、reasoning effort、context、temperature、usage、cost 和
错误类型，不能混成一个“DeepSeek 调用”。

**官方外部参照**只说明模型能力背景，不是主实验竞争对象。DeepSeek 公布的
Terminal-Bench、MCPAtlas 和 Toolathlon 分数不宣称已复现；Published Reference 只作为单独一列，
不参加显著性检验。

## 3. 唯一数据路线

当前只建设一个 benchmark adapter：`τ²-bench`。固定
`tau2-bench@1.0.1`，commit 为
`fc0055dc4e0a316c3f83133267fbd6faaa770992`。只使用 telecom 主域和 retail 复用域。

唯一执行顺序是：

1. **telecom 5 题协议与证据 smoke**：验证 API、AgentTeams、Adapter、reward 和 RunStore；
2. **telecom 20 题完整维护闭环**：跑通五波变化、诊断、更新、回归和 Dashboard；
3. **telecom 74 个 train 样本扩大与优化**：扩大 adaptation/validation 并比较更新效果；
4. **telecom 40 个 official test 封存验收**：最终方案冻结后才运行；
5. **retail 小规模复用验证**：验证完整 L1–L4 资产能否低成本迁移。

| Domain | train | test | 额外集合 | 当前用途 |
|---|---:|---:|---:|---|
| telecom | 74 | 40 | small=20，full=2,285 | 主证明 |
| retail | 74 | 40 | - | 小规模复用验证 |

`full=2,285` 不成为执行阶段，也不做全量跑分；20 题闭环稳定后只固定抽取少量边界任务
作为 `stress_and_failure`。airline 与 banking_knowledge 不进入当前范围。

Terminal-Bench、MCPAtlas、SWE-bench、CorpusQA、GDPval、Toolathlon 等只保留为未来候选，
当前不排期、不开发 Adapter、不进入 Dashboard 或验收结论。Toolathlon 状态保持
`BLOCKED_LICENSE`；许可证、数据权利和服务条款快照确认前，禁止 clone、运行、vendor 或调用公共服务。

## 4. 样本、冻结与运行协议

### 4.1 四类集合

每轮实验都使用四个互不重叠、内容寻址、Human freeze 的 SampleSetManifest：

- `adaptation`：允许两个维护组读取各自 Trace 并提出更新；
- `validation`：决定继续、接受或回退，不作为最终效果；
- `sealed_holdout`：最终候选冻结后才运行，结果不得回流；
- `stress_and_failure`：边界、异常与运行失败压力样本。

Pilot 与正式实验使用不同证据身份：

1. `small=20` 在任何候选生成前形成四个互不重叠的 pilot manifest；pilot G0 一次性冻结
   Objective、五波变化材料、预算、权限和访问顺序；
2. 从 pilot adaptation 预先指定 5 题做 smoke；20 题只证明工程闭环，不进入正式效果统计；
3. 正式实验将 74 train 稳定分为 adaptation/validation，40 official test 全部作为
   sealed_holdout，并从 full 中固定抽取少量 stress；
4. 正式四个 manifest 与 Objective 在候选生成前 Human freeze；40 test 在最终方案冻结前
   不向 Steward、Attributor 或 Architect 暴露。

公开题目只能形成**本次运行内的 sealed holdout**，不能证明模型预训练时未见过题目。

### 4.2 连续业务变化

两个维护组接收同样的五波变化：

| 波次 | 变化对象 | AgentFit 主要维护层 |
|---|---|---|
| L1 | 原子动作输入、输出或作用语义 | 原子能力 |
| L2 | 组合条件、前后置约束、Human Gate | 能力合同 |
| L3 | Policy、Skill、Runbook、阈值或路由 | 知识与路由 |
| L4 | 角色、通信、升级关系或人工位置 | Agent/Human 拓扑 |
| 跨层 | 同一变化同时影响能力、规则与协作 | 多层原子事务 |

每波固定执行：冻结变化材料 → adaptation → Trace 诊断 → 两组各自维护 → validation 检查
本波需求和累计旧需求 → 接受或回退 → 封存变更与成本。

### 4.3 AgentTeams 运行边界

每个 `CandidateRef × SampleRef × RunIndex` 使用独立 AgentTeams Worker/session。τ²-bench 的
domain environment、数据库状态、工具与 scorer 是任务权威；AgentTeams 负责装载方案、
调用 DeepSeek 官网 API、执行 Agent 协作并回传结果；AgentFit bridge 把 trajectory 转换为
Trace、Episode 和不可变 RunStore 证据。

## 5. 分阶段门禁

### 阶段 A：官网 API 与环境预检

- 用 `deepseek-v4-flash` 做无敏感信息的最小直连调用；
- 验证 tool call、usage、cost、context 与错误分类可以记录；
- 源码启动 AgentTeams，并确认独立 Worker/session 与 τ²-bench 环境可用。

只证明运行条件，不产生效果结论。

### 阶段 B：telecom 5 题协议与证据 smoke

- 完成 pilot G0 和候选生成前 Human freeze；
- Flat/AgentFit 在预先指定的 5 个 adaptation 样本各运行 1 次；
- 验证 DeepSeek 官网 API → AgentTeams → τ²-bench → Trace/Episode/RunStore 完整往返。

不得报告模型或 AgentFit 效果。

### 阶段 C：telecom 20 题完整维护闭环

- 沿用冻结的 pilot manifest、Objective、五波材料和初始候选；
- 跑完 adaptation、诊断、更新、validation、回退以及最终 holdout/stress；
- Dashboard 展示质量、回归、变更范围、成本、复用和错误类型。

20 题仍是工程 pilot，不做显著性结论。

### 阶段 D：telecom 74 个 train 样本扩大与优化

- 冻结正式四类 manifest、Objective、五波材料和公平预算；
- 按 L1→L2→L3→L4→跨层运行 Flat/AgentFit 配对 trial；
- 展示至少一条“扩大样本 → 失败聚类 → 方案更新 → 回归验证”的可审计路径。

### 阶段 E：telecom 40 个 official test 封存验收

- 两个最终方案 freeze 后，在 40 test 上成对运行；
- 优先每题各 5 次，预算不足时至少 3 次并披露限制；
- stress 最后执行，任何结果都不回流更新。

只有业务质量门和维护优势门都通过，才声明本次 telecom 实验有效。

### 阶段 F：retail 小规模复用验证

- 使用同一个 Adapter、scheduler、scorer、Dashboard 和 AgentTeams 外壳；
- 以封存的 telecom CandidateRef 的完整 L1–L4 为源投影 retail 方案；
- 资产复用账本记录原引用复用、局部替换、无法复用和新增；
- 若需要重做核心合同或运行外壳，停止扩大并判定复用假设未成立。

只有小规模证据表明是在复用而不是重做 Demo，才考虑 retail 74/40。

## 6. 指标与结论边界

主指标不是单次成功率，而是：

| 维度 | 指标 |
|---|---|
| 业务质量 | 新需求 reward、累计旧需求回归、最终 sealed holdout |
| 维护效率 | 达标轮数、token/cost、wall time、Human 次数 |
| 变更控制 | 定位层级、修改资产、依赖变化、无关修改 |
| 资产价值 | 复用、重复新建、回滚成功率 |
| 可靠与安全 | runtime/protocol error、retry、越权副作用、重大风险 |

所有指标的最小身份是 `CandidateVersion × SampleVersion × RunIndex`，代码中对应
`candidate_ref + sample_ref + run_index`。

- smoke 每题 1 次，只检查协议；
- pilot 同一任务两组各 3 次；
- formal 优先各 5 次，预算不足时至少 3 次；
- 先在每个 SampleRef 内汇总同一 arm 的重复 trial，再按 SampleRef 配对计算差值；
- paired bootstrap 以 SampleRef 为重采样 cluster，并保留 cluster 内全部 trial；
- McNemar 使用 sample-level paired outcome；
- trial 不能作为独立样本扩大统计样本量；
- runtime ERROR 与业务 FAIL 分开，不能只重跑失败的一组。

业务质量达到同一门槛后，AgentFit 还必须在累计回归、变更范围、达标成本、复用或回滚中
取得预先定义的改善，且不得牺牲安全与可靠性。样本不足或区间跨过边界时，只报告方向性
结果。

## 7. 交付与展示

每次有效实验交付：

1. `solution_package`：冻结的 L1–L4、Human Gate、平台桥接和监控策略；
2. `evidence_package`：manifest、Candidate、Episode、Trace、ChangeTransaction、统计与哈希；
3. Dashboard：同屏展示 Flat/AgentFit、五波变化、累计回归、成本、资产复用和最终验收。

允许的结论只限定于本次模型、API、benchmark commit、样本 manifest、CandidateRef 和
runtime_ref。不得查看 holdout 后更新、弱化 Flat、给 AgentFit 更多预算、用诊断文本覆盖
原生 reward，或只展示最终平均数。

## 8. 当前下一步

当前只实现阶段 A/B：

1. 把 AgentTeams 当前运行配置切换为用户自有 DeepSeek 官网 API 与
   `deepseek-v4-flash`，完成直连 smoke；
2. 完成 τ²-bench Adapter 的任务锁定、原始结果保存与完整证据往返；
3. 为 `small=20` 生成四个 pilot manifest，完成 pilot G0；
4. 构造语义等价的 Flat/AgentFit 初始方案；
5. 运行预先指定的 telecom 5 题，门禁通过后再批准 20 题闭环。

现在不开发其他 benchmark，不运行 74/40，不提前建设 retail。所有 API secret 只留在本地
运行环境；`competition/2026-08-16/submission/` 保持不变。

## 参考资料

- [DeepSeek-V4 发布页](https://api-docs.deepseek.com/zh-cn/news/news260424)
- [DeepSeek-V4 技术报告](https://arxiv.org/abs/2606.19348)
- [τ²-bench](https://github.com/sierra-research/tau2-bench)
