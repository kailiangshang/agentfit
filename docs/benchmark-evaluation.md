# AgentFit × DeepSeek-V4-Flash 业务维护评测方案

> 状态：评测设计正本。调研与协议核验日期：2026-08-19。

## 技术摘要

DeepSeek 官网已经正式发布 `deepseek-v4-flash`。官方技术报告给出的模型口径是
284B 总参数、13B 激活参数和 1M 上下文，并公布了 Non-think、High、Max 三种
reasoning effort 下的完整成绩。DeepSeek-V4-Flash-Max 在 Terminal-Bench 2.0、
MCPAtlas Public 和 Toolathlon 上分别为 56.9、69.0 和 47.8。这些成绩是模型能力背景，
不是 AgentFit 主实验的竞争对象。

AgentFit 的业务优势不是替换 Agent 框架，而是把持续变化的 Agent 方案维护拆成四个
有合同、有证据、有回归边界的层级：L1 原子能力、L2 能力组合、L3 知识与路由、L4
Agent/Human 拓扑。主实验固定 DeepSeek-V4-Flash、AgentTeams、初始业务行为、工具、
样本、预算和评分器，只比较两种维护方式：常见的扁平维护与 AgentFit 四层维护。

业务变化按批次进入：原子动作的业务输入、输出或作用语义变化检验 L1，组合条件与
Human Gate 变化检验 L2，政策、Skill 与路由变化检验 L3，角色、通信和升级关系变化
检验 L4，最后再加入一次跨层综合变化。每轮都比较新需求是否达标、旧样本是否回归、
修改范围、达标轮数、成本、复用、回滚和审计证据，而不只比较一次最终成功率。

因此，本方案保留三类证据，但主次重新排序：

1. **Flat Maintenance Base**：在 AgentTeams 中按常见 Prompt、Tool、Knowledge 和 Team
   配置方式维护同一初始业务方案，不使用显式 L1–L4 合同和 ChangeTransaction。
2. **AgentFit Four-layer Maintenance**：在同一 AgentTeams 运行边界内按 L1–L4 归因、
   局部修改、原子提交或回滚，并积累可复用方案资产。
3. **官方外部参照**：保留 DeepSeek 公布的分数及协议边界，不宣称复现，也不进入主实验
   的显著性检验。

当前执行范围进一步收敛为一个 benchmark、一个主业务域和一个复用业务域：只建设
τ²-bench Adapter，先把 telecom 的完整维护闭环做透，再用 retail 检验同一套 Adapter、
scheduler、scorer、Dashboard 和四层资产是否能够低成本复用。其他公开 benchmark 只保留
背景与未来候选身份，不进入当前排期。

本方案要回答的核心问题是：

> 在相同模型、AgentTeams、业务材料、样本、工具和维护预算下，面对连续业务变化，
> AgentFit 四层维护能否以更准确的层级定位、更小的变更范围、更低的累计回归和更少的
> 达标轮次，持续交付满足用户 Objective 的 Agent 方案。

## 1. 官方模型与成绩

### 1.1 模型身份

| 项目 | 官方口径 | 本项目使用规则 |
|---|---|---|
| API model name | `deepseek-v4-flash` | 运行前从 LiteLLM `/v1/models` 回读并保存实际 model ID |
| 参数 | 284B total / 13B activated | 只作模型说明，不作为实验变量 |
| 上下文 | 最长 1M tokens | 每次实验仍冻结实际 context budget |
| reasoning effort | Non-think / High / Max | Flat 与 AgentFit 必须相同 |
| 推理任务温度 | 官方报告为 1.0 | 若 benchmark 有原生规定则服从原生规定，否则双方固定同值 |
| 官方公开 harness | `deepseek-ai/deepseek-harness` | 仅作公开实现参考，不等同官网内部评测 harness |

LiteLLM 只是统一模型路由。它也可以承载用户模拟、评分和诊断模型，但不同职责必须分别
记录 `model_id`、provider route、reasoning effort、context、temperature 和调用成本，不能
只写一个“DeepSeek”。API key 只从运行环境读取，不进入 Git、RunStore 或报告。

### 1.2 DeepSeek-V4-Flash 官方结果

下表只摘录 DeepSeek-V4 技术报告 Table 7 中与 Agent 工具调用直接相关的三项。所有值都
是官方报告值，不是 AgentFit 当前运行结果，也不是本项目当前要复现的主实验。

| Benchmark | 指标 | Non-think | High | Max |
|---|---:|---:|---:|---:|
| Terminal-Bench 2.0 | ACC | 49.1 | 56.6 | 56.9 |
| MCPAtlas Public | Pass@1 | 64.0 | 67.4 | 69.0 |
| Toolathlon | Pass@1 | 40.7 | 43.5 | 47.8 |

### 1.3 官网分数的可比边界

DeepSeek 技术报告明确说明：

- 推理和知识任务的 Non-think、High、Max 上下文分别为 8K、128K、384K；
- 代码 Agent 任务使用内部框架，只提供 bash 与 file-edit，最多 500 个交互步骤，
  最大 512K 上下文；
- 搜索 Agent 使用内部 websearch 与 Python 工具，同样最多 500 步、512K 上下文；
- Terminal-Bench 使用原始 2.0 数据集，而不是 Verified 子集；
- DeepSeek 承认原始 Terminal-Bench 2.0 存在环境问题；报告只给出 DeepSeek-V4-Pro
  在 Verified 子集约 72.0，没有公布 DeepSeek-V4-Flash 的 Verified 分数；
- 公开 `deepseek-harness` 当前提交 `99f6f02fecdb7dff40c3fbc9470f5907c29f74ca`
  的 `BENCHMARK.md` 没有包含官网内部评测的完整配置。

所以只有在原始 Terminal-Bench 2.0、同等工具、500 步、512K 上下文和同评分协议下，
才能把自测结果与 56.9 放在同一张“近似复现”表中。即使如此，也应同时报告 harness
差异，不能写成官方结果已复现。

## 2. 当前执行范围

当前只建设一个 benchmark adapter：`τ²-bench`。当前主业务域只有 telecom，第二业务域
只有 retail；执行顺序不得并行展开，也不能在 telecom 证据链尚未稳定时增加第三个域。

唯一执行梯度是：

1. **telecom 5 题协议与证据 smoke**：只验证 Adapter、AgentTeams、reward 与 RunStore
   往返，不报告效果；
2. **telecom 20 题完整维护闭环**：跑通 Flat/AgentFit、五波变化、诊断、更新、回归和
   Dashboard，证明全流程可运行；
3. **telecom 74 个 train 样本扩大与优化**：扩大 adaptation/validation，比较多轮更新
   前后的质量、回归、变更范围和成本；
4. **telecom 40 个 official test 封存验收**：最终方案 freeze 后成对运行，只用于正式
   泛化验收；
5. **retail 小规模复用验证**：复用相同 Adapter、scheduler、scorer、Dashboard 和四层
   资产，先回答换业务域是否需要重做系统，再决定是否扩大。

telecom `full=2,285` 不是新的执行阶段，也不做全量跑分。只有 20 题完整闭环稳定后，才从
中固定抽取少量边界任务形成 `stress_and_failure`；抽样清单必须在正式 74/40 流程前冻结。

Terminal-Bench、MCPAtlas、SWE-bench、CorpusQA、GDPval、Toolathlon 等均为未来候选：当前
不排期、不开发 Adapter、不进入 Dashboard 和验收结论。DeepSeek 官网成绩只保留为
Published Reference，不能反向扩大当前实施范围。

Toolathlon 当前状态为 `BLOCKED_LICENSE`。在许可证、数据权利和服务条款快照全部确认前，
禁止 clone、运行、vendor 或调用公共服务；即使以后重新考虑，也必须先通过独立 Human
许可审核，不能因公开仓库或公共服务存在而默认可用。

## 3. 为什么只做 τ²-bench telecom → retail

τ²-bench 不在 DeepSeek-V4 官方表中，但它比纯问答或只看最终 patch 的任务更适合回答
AgentFit 的四层维护问题：

- Agent 与用户模拟器持续交互，能观察沟通、澄清和拒绝策略；
- 任务包含真实风格的业务 policy、状态与工具；
- reward 可由数据库状态、动作、环境断言和沟通断言共同构成；
- trajectory 能直接映射为 AgentFit Trace、Episode 和错误归因；
- 相同任务可以让 Flat Maintenance 与 AgentFit Four-layer Maintenance 成对运行；
- 失败能够定位为 L1 能力、L2 合同、L3 知识/路由或 L4 行为拓扑，而不只是“答错”。

当前冻结 `tau2-bench@1.0.1`，提交为
`fc0055dc4e0a316c3f83133267fbd6faaa770992`。当前只使用两个业务域：

| Domain | base | train | test | 额外集合 |
|---|---:|---:|---:|---:|
| telecom | 114 | 74 | 40 | `small=20` 用于工程闭环；`full=2,285` 只抽取 stress |
| retail | 114 | 74 | 40 | 先从 train 固定抽取小规模迁移子集 |

`base` 是完整、与原始 τ-bench 结构相符的评价集合；它不是 AgentFit 的“Base Agent”。
文档和 Dashboard 必须把 `task split` 与 `candidate arm` 分开命名。airline 与
banking_knowledge 不进入当前执行范围；不为它们生成 manifest、Adapter 分支或展示占位。

telecom 是主证明：在一个业务域内完成从 5 到 20、再到 74/40 的全流程、扩样、优化和
验收。retail 是复用证明：先用固定小子集检查已有 L1 能力、L2 合同、L3 知识/路由和 L4
拓扑中哪些可直接复用、哪些必须局部替换。只有小规模证据表明确实在复用同一套运行与
维护机制，而不是重做另一套 Demo，并且预算重新获批，才扩大到 retail train/test。

每次运行至少冻结 repository URL、commit/tag、任务 ID 清单、任务内容哈希、评分器版本、
运行配置和许可证快照。仓库 commit 只描述代码版本，不能替代任务内容哈希。

## 4. 公平对照实验

### 4.1 两个维护组与一个外部背景

| 组 | 内容 | 能回答什么 | 不能回答什么 |
|---|---|---|---|
| Flat Maintenance Base | AgentTeams 中语义等价的初始方案；允许按常见方式修改 Prompt、Tool、Knowledge 和 Team 配置，但没有显式 L1–L4 合同、分层归因和 ChangeTransaction | 常见扁平维护在连续业务变化下的效果、回归和维护负担 | DeepSeek 官方内部 harness 的复现结果 |
| AgentFit Four-layer Maintenance | 同一初始业务行为由 L1–L4 合同表达；只依据 adaptation Trace 分层归因，并以事务执行局部修改、回归或回滚 | 四层维护相对扁平维护的增量价值 | 其他模型或运行平台上的普遍结论 |
| Published Reference | DeepSeek 官方表中的 56.9/69.0/47.8 等 | 模型在官方内部协议下的能力量级 | AgentFit 维护增益或本地可复现性 |

主要因果对照是 Flat Maintenance Base 与 AgentFit Four-layer Maintenance。
Published Reference 只作为单独一列，不参加显著性检验。主实验不要求复现或战胜
DeepSeek 官方 Agent harness；框架比较只在业务维护主结论成立后作为非阻塞扩展。

Flat Base 不能被故意削弱。它获得相同业务材料、失败 Trace、更新模型、Human 决策额度
和运行预算，也允许修改同样的底层资产；唯一缺少的是 AgentFit 的四层合同、归因约束、
依赖边界、事务提交和资产复用机制。

Flat 维护者直接编辑常规 AgentTeams Team/Worker、Prompt、Tool 和知识包。每轮执行前，
bridge 只为证据身份把该包确定性投影为 CandidateManifest；这个只读投影不暴露给 Flat
维护者，也不参与其修改决策。AgentFit 组原生维护 L1–L4 CandidateManifest。两组最终都
以 CandidateRef、SampleRef 和 RunIndex 进入同一评价与 RunStore 合同。

### 4.2 保持不变与允许变化

必须保持不变：

- `deepseek-v4-flash` 的实际 API route、reasoning effort、context 与采样参数；
- 用户模拟模型、评分模型和诊断模型各自的配置；
- benchmark commit/tag、任务内容、工具、沙箱、初始状态和 scorer；
- 每题 step、token、wall time、retry 和工具调用预算；
- trial 数、并发策略、失败重试策略和错误分类；
- 每轮收到的业务变更材料、可读 Trace、更新模型、Human Gate 次数和总维护预算；
- 同一正式评价中两个维护组的 SampleRef 与 RunIndex 配对规则。

唯一允许有意变化的是维护机制。Flat Base 直接修改扁平资产；AgentFit 将变化定位到 L1
原子能力、L2 能力合同、L3 可复用知识与路由或 L4 Agent/Human 行为拓扑，并通过
ChangeTransaction 自底向上原子应用。具体能力由原生函数、MCP、HTTP、脚本或 Memory
实现，不是比较变量；bridge 在相同 benchmark 沙箱中解析它们，并通过 `runtime_ref`
留下证据。

### 4.3 AgentTeams 共同执行外壳

Flat Base 和 AgentFit 都必须经过 AgentTeams，而不是把框架差异混进维护实验：

```text
Frozen SampleSetManifest
          │
          ▼
   Benchmark bridge ── TaskSample ──► AgentTeams isolated Worker/session
          │                                      │
          │                     Flat Maintenance │ AgentFit Four-layer
          │                                      ▼
          └──────── benchmark tools + sandbox + scorer
                                                 │
                                                 ▼
                     Trace + Episode + benchmark-native result
                                                 │
                                                 ▼
                               immutable AgentFit RunStore
```

每个 `CandidateRef × SampleRef × RunIndex` 使用独立 Worker/session，避免历史上下文污染。
AgentTeams 可从源码启动；不需要为了 AgentFit 重编 AgentTeams 镜像。τ²-bench 的 domain
environment、数据库状态、工具和 scorer 继续作为任务权威环境，AgentTeams 的隔离环境
作为模型调用、方案装载与会话边界。

### 4.4 四类样本集合

正式实验前创建四个互不重叠、内容寻址、Human freeze 的 SampleSetManifest：

- `adaptation`：两个维护组只从各自在本集合运行所得 Trace 提出方案更新；
- `validation`：决定两组继续修改、接受或回退，不作为最终效果；
- `sealed_holdout`：两个最终方案 freeze 后才能执行，结果不得返回更新闭环；
- `stress_and_failure`：异常、长链路、边界和运行失败压力样本。

τ²-bench telecom 按两种证据身份运行，不在文档中硬编码具体 ID：

1. `small=20` 是工程 pilot：在任何 pilot 候选生成前，经稳定哈希和任务类型分层形成四个
   互不重叠的 pilot manifest，并通过 pilot G0 一次性冻结 Objective、五波变化材料、预算、
   权限和访问顺序；
2. 从 pilot adaptation 中预先指定 5 题做协议与证据 smoke，再用四个 pilot manifest 跑完
   五波维护闭环。5 题可以在 20 题流程中复用，但整个 small 结果只证明工程闭环，不进入
   正式效果统计；
3. 20 题闭环稳定后，74 个 train ID 经稳定哈希和任务类型分层切成正式 adaptation 与
   validation；
4. 40 个 official test ID 全部进入 sealed_holdout，两个最终方案 freeze 前不向
   Steward、Attributor、Architect 暴露结果；
5. 20 题闭环稳定后才从 2,285 个 full telecom 任务中排除 base/small ID，并固定抽取少量
   边界任务形成 stress_and_failure；它们在正式候选生成前与其他三个 manifest 一起冻结；
6. 每个 manifest 保存版本、content hash、access policy 和完整 ID 清单。

公开题目只能形成**本次运行内的 sealed holdout**，不能证明模型预训练时从未见过题目。
报告必须把“实验访问隔离”与“训练语料无污染”分开表述。

### 4.5 用户模拟、评分与诊断

LiteLLM 可以同时提供三类模型调用，但三者不能混成一个 reward：

| 职责 | 建议 | 是否影响主分数 |
|---|---|---|
| Agent model | Flat 与 AgentFit 都用同一 `deepseek-v4-flash` 配置 | 是 |
| User simulator | τ²-bench 两组都用同一模型、prompt 和 seed 规则 | 间接影响，必须冻结 |
| Official scorer | 优先使用 benchmark 的 DB/action/env/assertion/test reward | 是，主指标 |
| LLM judge | 只有 benchmark 原生要求时使用，双方同配置 | 是，需单列不确定性 |
| Diagnostic model | 运行后聚类错误、解释 Trace | 否；不得覆盖官方 reward |

诊断可以帮助 AgentFit 决定下一批修改什么，但最终通过率必须由冻结的 benchmark scorer
重算。诊断模型的自然语言结论不是验收证据。

### 4.6 连续业务变化波次

两个维护组从语义等价、在 smoke 样本上行为一致的初始方案出发。正式运行前由 Human
冻结每一波业务材料、对应 adaptation/validation 样本、允许影响的层级集合和维护预算。
层级集合只用于事后检验定位的 precision/recall 与变更爆炸半径，不能提前暴露给任一
维护者。

| 波次 | 业务变化 | 主要检验 | 典型维护对象 |
|---|---|---|---|
| 初始基线 | 现有 telecom policy、状态和工具 | 两组初始行为是否等价 | 初始 Prompt、Tool、Knowledge、Team |
| L1 变化 | 原子动作的业务输入、输出、读写类型或作用语义变化 | 能否局部定位到底层能力合同 | L1 输入输出与作用语义；runtime binding 仍单独记证据 |
| L2 变化 | 新组合条件、前后置约束或高风险人工审批 | 能否维护可复用能力合同 | L1 组合、聚合条件、Human Gate |
| L3 变化 | 新政策、Runbook、阈值、Skill 或路由经验 | 能否更新知识而不扰动执行边界 | 知识、规则、路由与上下文 |
| L4 变化 | 新角色、升级关系、协作边或人工位置 | 能否显式修改行为拓扑 | Agent/Human、触发方式、TopologyEdge |
| 跨层变化 | 同一业务变更同时影响工具、规则和协作 | 能否原子提交、完整回归和整体回滚 | 多层 ChangeTransaction |

每一波使用相同流程：

```text
冻结业务变化材料
  → 编译本波 TaskSample
  → 两组在 adaptation 上运行
  → 在相同信息与预算下维护方案
  → validation 验证本波需求和累计旧需求
  → 记录变更范围、回归、成本、复用和回滚证据
```

validation 可以决定继续修改、接受或回退，但不能替代最终 sealed_holdout。上一波已经通过
的 validation 样本进入累计回归集合，用来观察维护负担和回归是否随业务变化增长。

## 5. 指标、统计与验收

### 5.1 主指标与护栏

| 类型 | 指标 | 用法 |
|---|---|---|
| Business quality | 本波新需求 reward/pass rate、累计旧需求回归率、最终 sealed-holdout | 判断方案是否持续满足业务目标 |
| Localization | 主要影响层级命中率、无证据跨层修改数、runtime ERROR 误归因数 | 判断四层是否帮助找到真正缺口 |
| Change surface | 修改资产数、涉及层级数、依赖边变化数、未相关资产改动数 | 衡量变更爆炸半径 |
| Maintenance effort | 达标轮数、维护模型 token/cost、wall time、Human 决策次数 | 衡量达到相同验收结果的代价 |
| Reuse | 复用既有 L1/L2/L3 资产数与新增重复资产数 | 判断维护是否形成可复用积累 |
| Recovery | 回滚成功率、回滚后旧样本恢复率、事务不完整数 | 判断错误更新是否可恢复 |
| Reliability | runtime error rate、protocol error rate、retry rate | 运行错误不能混入业务失败或被丢弃 |
| Safety/complexity | 越权副作用、重大风险、Agent 数、上下文和维护负担 | 高通过率不能抵消风险或无界复杂化 |

所有指标的最小评价身份保持为：

`CandidateVersion × SampleVersion × RunIndex`

在代码与证据中分别落到 `candidate_ref + sample_ref + run_index`。展示 label 不能代替
内容寻址身份。

### 5.2 重复运行与统计

- adapter smoke：每题 1 次，只检查协议和证据完整性，不报告模型效果；
- pilot：同一任务 Flat/AgentFit 两组各 3 次；
- formal：优先各 5 次；预算不足时至少 3 次，并在报告中说明功效限制；
- 先在每个 SampleRef 内汇总同一 arm 的重复 trial，再按 SampleRef 配对计算 reward 差值；
- 报告均值、通过率和 95% paired bootstrap confidence interval；
- paired bootstrap 以 SampleRef 为重采样 cluster，并保留该 cluster 内的全部 trial；
- 二元结果可同时给出 discordant pairs；McNemar 使用 sample-level paired outcome，
  其 trial 聚合与二值化规则必须预先写入 ObjectiveSpec；
- trial 级结果和 dispersion 全部单列保留，不能只保存平均数；
- trial 不能作为独立样本扩大统计样本量；
- 并发失败、限流和平台错误单列，不允许只重跑失败的一侧。

正式成功条件应在 sealed_holdout 前写入 ObjectiveSpec，且不能压成一个掩盖取舍的综合
分数。推荐采用两道门：

1. **业务质量门**：AgentFit 在每波 validation 和最终 sealed_holdout 上达到用户阈值，
   相对 Flat Base 的最终质量满足预先冻结的非劣界或取得显著改善；运行错误和重大风险
   不增加。
2. **维护优势门**：在达到相同业务质量的前提下，AgentFit 至少在累计回归、变更范围、
   达标轮数/成本、复用或回滚中取得预先声明的关键改善，且不能以其他护栏明显恶化换取。

每一波分别报告结果，并绘制“累计业务变化 → 质量/回归/维护成本”曲线。波次是同一项目
内的连续状态，不得当作相互独立样本扩大统计量。若样本量不足或置信区间跨过预设边界，
只能报告方向性结果，不能写成“已证明四层维护有效”。

### 5.3 预算预检

不在文档中硬编码 DeepSeek 或 LiteLLM 价格。每轮按实际路由价格预估：

```text
expected_calls = samples × trials × arms × expected_turns
expected_cost  = Σ(input_tokens × input_price + output_tokens × output_price)
```

预检必须包含 Agent、用户模拟、LLM judge 和诊断四类成本，并设置 hard budget、单题
wall timeout 和全局停止条件。预算超限是独立停止原因，不得伪装成任一维护组收敛。

## 6. 分阶段执行路线

### 阶段 A：模型与环境预检

1. 从 LiteLLM `/v1/models` 确认 `deepseek-v4-flash` 实际可用；
2. 用无敏感信息的最小调用确认 reasoning effort 和 tool call；
3. 记录 LiteLLM route、模型响应中的 usage、价格表版本和 context limit；
4. 源码启动 AgentTeams，确认每个 EvaluationUnit 可创建独立 Worker/session；
5. 检查 τ²-bench 环境、磁盘和预算，不运行正式样本。

完成定义：只证明运行前置条件，不产生效果结论。

### 阶段 B：telecom 5 题协议与证据 smoke

1. 锁定 `tau2-bench@1.0.1`；
2. 对 `small=20` 执行 pilot G0：形成四个互不重叠的 pilot manifest，冻结 ObjectiveSpec、
   五波变化材料、预算、权限和访问顺序；
3. 在候选生成前完成 Human freeze，再构造语义等价的 Flat 初始方案与 AgentFit 四层初始
   方案；
4. 从 pilot adaptation 中预先指定 5 个协议覆盖样本，两组各跑 1 次；
5. 验证原始 trajectory、reward、TaskSample、Trace、Episode、runtime_ref 和 RunStore
   哈希链能够完整往返；
6. 核对两组可用工具、上下文、预算、初始行为和 scorer 相同。

完成定义：没有身份错配、结果丢失、跨会话污染或无法重算的 reward；没有由 Adapter 或
初始语义不等价造成的系统性组间差异。

### 阶段 C：telecom 20 题完整维护闭环

1. 沿用已经 Human freeze 的四个 pilot manifest、Objective、变化材料和两个初始候选；
2. 用 `small=20` 跑通初始基线与 L1、L2、L3、L4、跨层五波变化；
3. 每波完成 adaptation 运行、Trace 归因、Flat/AgentFit 更新、validation 回归和方案回退；
4. pilot 最终候选 freeze 后才运行 sealed_holdout 和 stress_and_failure，结果不回流更新；
5. 打通业务质量、累计回归、变更范围、达标轮数/成本、复用、回滚和风险的 Dashboard；
6. 允许包含已执行的 5 题 smoke，但整个 20 题结果只标记为工程 pilot，不做显著性结论；
7. 在独立 RunStore 中封存原始 trajectory、模型 usage、Human 决策与 Candidate 变化。

完成定义：从业务变化到可追溯方案更新和结果展示的完整链路可重复运行；失败能区分
业务 FAIL、协议 ERROR、平台 ERROR 和预算停止，且没有靠人工补写结果。

### 阶段 D：telecom 74 个 train 样本扩大与优化

1. 冻结 Flat 与 AgentFit 两组的初始方案身份和语义等价证明；
2. 冻结 L1、L2、L3、L4 和跨层五波业务变化材料及内容哈希；
3. 将 74 个 train 样本稳定分层到 adaptation、validation 和累计回归视图；
4. 只在 20 题闭环稳定后从 `full=2,285` 固定抽取少量 stress_and_failure；
5. 实例化四类 manifest 与 ObjectiveSpec，由 Human 在候选生成前一次性 freeze；
6. 同时冻结每波最大维护轮数、两组可读证据、更新模型、Human 次数、token/cost/time 和
   允许修改资产范围；
7. 按 L1 → L2 → L3 → L4 → 跨层顺序运行，每个 SampleRef 内对 Flat/AgentFit 做配对 trial；
8. validation 同时检查本波新需求和累计旧需求，比较更新前后质量、回归、变更范围、成本、
   复用和回滚，未达标时在 hard budget 内继续或回退。

完成定义：至少得到一条可审计的“扩大样本 → 诊断失败簇 → 更新方案 → 回归验证”路径，
并明确哪些优化有效、哪些无效、哪些因预算或运行错误无法判断。Flat Base 不是弱化对照。

### 阶段 E：telecom 40 个 official test 封存验收

1. 74 train 的维护和 validation 完成后冻结两个最终方案；
2. 在 40 个 official test ID 上成对运行，优先每题各 5 次，预算不足时至少 3 次；
3. stress_and_failure 最后执行，不回流任一维护组；
4. 同时报告最终业务质量、累计回归曲线、变更范围、达标成本、复用、回滚和风险；
5. 只有同时通过业务质量门和维护优势门，才声明四层维护在本次 telecom 实验中有效。

完成定义：能回答 AgentFit 四层维护相对常见扁平维护的业务价值，而不是展示一次高分；
sealed_holdout 访问发生在方案 freeze 之后，结果没有进入任何更新。

### 阶段 F：retail 小规模复用验证

1. 保持同一个 τ²-bench Adapter、scheduler、scorer、Dashboard 和 AgentTeams 执行外壳；
2. 从 retail train 中稳定抽取小规模任务，冻结业务材料和四类 manifest；
3. 以已封存的 telecom CandidateRef 的完整 L1–L4 为源进行投影，再只替换 retail 必需的
   政策、数据、能力合同和局部拓扑；
4. 建立资产复用账本，逐项记录原引用直接复用、局部替换、无法复用和新增资产，并关联
   迁移后的质量与回归证据；
5. 若迁移必须重做 Adapter、调度、评分、Dashboard 或核心合同，则复用假设未成立，停止
   扩大并先诊断；
6. 只有小规模证据显示是跨域复用而非重做 Demo，且预算重新获批，才决定是否扩大到
   retail 74 train / 40 test。

完成定义：回答“换一个相邻业务域需要改多少”，而不是再产出一套孤立的 retail Demo。

以上六个阶段是当前完整路线。其他 benchmark 当前不排期、不开发 Adapter，也不作为
retail 之后的自动下一阶段。

## 7. AgentFit 应交付和展示什么

### 7.1 可部署方案

每个通过验收的实验交付三个相互引用的包：

1. `solution_package`：冻结的 L1-L4 Solution、能力合同、Human Gate 和监控策略；
2. `evidence_package`：SampleSetManifest、CandidateManifest、Episode、Trace、指标、
   ChangeTransaction、配对统计和哈希证明；
3. 平台桥接包：AgentTeams 稳定 Team/Worker 定义及 runtime binding。

benchmark 的 runner、镜像和任务数据不复制进核心方案包；只保存合法的引用、摘要和哈希。

### 7.2 适配路径与求解路径

训练 Dashboard 继续使用现有八区正本，不新增另一套 Dashboard：

- 运行概览：Flat 与 AgentFit 两组、当前维护波次、模型、benchmark、预算和最终结论；
- 四集合验收：每个集合的样本数、PASS/FAIL/ERROR 与不可见边界；
- 材料与四层映射：业务材料如何形成 TaskSample 与 L1-L4 候选；
- 样本与聚类：失败集中在哪类场景；
- 训练曲线：每个业务变化波次的质量、累计回归、成本和风险；
- 损失归因：Trace 说明错在哪里；
- 方案演化：哪条证据触发了哪项 L1-L4 更新；
- 事务链路：Human 决策、ChangeTransaction、回归和 Candidate freeze。

外部评价 Dashboard 保持最小证据视图，不伪造训练 Epoch 或方案演化。Flat 与 AgentFit
对照需要同时展示逐波 aggregate、累计回归和逐样本 paired result，防止最终平均数掩盖
中途退化与维护成本。

### 7.3 结论模板

允许的结论：

> 在冻结的 τ²-bench telecom 连续业务变化、相同 DeepSeek-V4-Flash、AgentTeams、初始
> 业务行为、工具、样本和维护预算下，AgentFit 四层维护与 Flat Maintenance 均达到最终
> 业务质量门；AgentFit 的累计旧需求回归为 X、变更资产为 Y、达标轮数/成本为 Z，复用、
> 回滚和风险护栏如下。该结论只适用于本次业务变化材料、benchmark commit、manifest、
> CandidateRef 和 runtime_ref。

不允许的结论：

- 故意限制 Flat 组可读 Trace、可修改资产或维护预算，形成弱化对照；
- 用 High 跑 Flat、Max 跑 AgentFit；
- AgentFit 使用更多工具、上下文、维护轮次或 Human 决策却不披露；
- 查看 sealed_holdout 后继续修改任一方案；
- 把 runtime ERROR 当作业务 FAIL，或只重跑失败的一组；
- 用诊断模型的主观判断覆盖 benchmark 原生 reward；
- 只比较最终成功率，不报告中间回归、变更范围和维护成本；
- 一次成功或平均值上升就写成普遍有效。

## 8. 当前代码基础与缺口

| 能力 | 当前状态 | 下一步 |
|---|---|---|
| AgentTeams 生成、隔离 Worker、Matrix/DeepSeek 运行和结果往返 | 已有真实 12 样本证据 | 补齐集合级会话隔离、usage/cost 与 stress 协议错误 |
| τ²-bench 命令桥接 | 已能调用外部 τ² CLI | 锁定 tag、任务 ID、参数和原始结果文件，而不是只截取 stdout/stderr |
| τ²-bench 结果导入 | 已能生成 CandidateManifest、TaskSample、Trace、Episode、外部证据链和 RunStore | 保持现有 projector 为唯一规范投影 |
| Flat/AgentFit 初始等价构造 | 尚未实现 | 构造常规 Flat 包及只读 Candidate 投影、AgentFit 原生 Candidate，并用 smoke 证明工具、预算和行为边界一致 |
| 连续业务变化注入 | 尚未实现 | 冻结 L1、L2、L3、L4 和跨层材料、样本与累计回归集合 |
| AgentFit 作为 τ² 原生 Agent | 尚未实现 | 增加 benchmark-native adapter，经 AgentTeams 调用冻结 Candidate |
| 双维护组成对调度 | 尚未实现 | 同一变化波次、SampleRef、trial、更新模型、Human 和预算下运行两组 |
| 维护证据与统计 | 尚未实现 | 记录层级定位、变更范围、累计回归、达标轮数/成本、复用和回滚，并保留 paired statistics |
| telecom → retail 复用路径 | 尚未实现 | 在同一 τ²-bench Adapter 中切换 domain，量化四层资产直接复用、局部替换和重复新建 |

最关键的缺口不是再发明 Agent 抽象或追逐更多榜单，而是建立一个公平的连续维护实验：
让相同业务变化分别进入 Flat 与 AgentFit，两组在同一 AgentTeams/benchmark 沙箱中维护，
并把每波输入、Trace、变更、回归、成本和最终方案完整封存。Tool、MCP、Memory 的具体
技术载体仍由运行时解析；AgentFit 只声明方案中有什么、职责、约束和连接。

## 9. 实施顺序

1. 修正 `bridges/tau2bench/run_bench.py`，锁定版本、输入任务、真实 results 路径和运行
   provenance；
2. 定义 Flat Maintenance arm、只读 Candidate 投影、AgentFit Four-layer arm 和初始语义
   等价门禁；
3. 实现 τ²-bench Agent adapter，使两个维护组都通过 AgentTeams 调用各自冻结方案；
4. 增加业务变化波次、累计回归集合和统一 trial/maintenance scheduler；
5. 把 LiteLLM usage/cost、runtime error、benchmark reward、维护成本和 Human 决策写入
   标准证据；
6. 增加层级定位、变更范围、复用、回滚、配对统计与 Dashboard 映射；
7. 依次完成 telecom 5 题协议与证据 smoke、telecom 20 题完整维护闭环、telecom 74 个
   train 样本扩大与优化、telecom 40 个 official test 封存验收；
8. telecom 正式结果封存后才做 retail 小规模复用验证；当前只建设一个 benchmark
   adapter：`τ²-bench`，其他 benchmark 不排期、不开发 Adapter。

行为变更必须先有失败测试；所有活构件使用稳定名称并原位迭代，Git 记录演化。不可修改
已经冻结的 `competition/2026-08-16/submission/`。

## 10. 运行前冻结清单

- [ ] LiteLLM 返回的实际 `deepseek-v4-flash` model ID 和 provider route
- [ ] reasoning effort、temperature、context、step/token/time/tool budget
- [ ] Agent、user simulator、judge、diagnostic 四类模型配置
- [ ] benchmark repo URL、commit/tag、任务 ID、内容哈希与许可证快照
- [ ] 容器镜像 digest、工具清单、初始状态、scorer 版本
- [ ] adaptation / validation / sealed_holdout / stress_and_failure manifests
- [ ] Flat 初始运行包及只读 Candidate 投影、AgentFit 初始 CandidateManifest、语义等价
  证明和允许的维护资产
- [ ] L1 / L2 / L3 / L4 / 跨层业务变化材料、顺序、内容哈希和盲化层级标签
- [ ] 两组可读 Trace、更新模型、维护轮数、Human 次数和 maintenance budget
- [ ] trial 数、seed 规则、并发、retry 和 platform-error 处理
- [ ] 业务质量门、维护优势门、非劣界、统计方法和 hard budget
- [ ] 变更范围、累计回归、达标轮数/成本、复用和回滚的计算口径
- [ ] AgentTeams Worker/session 隔离与 RunStore 输出目录
- [ ] sealed_holdout 访问控制和 Human freeze 记录

## 参考资料

- [DeepSeek-V4 发布页](https://api-docs.deepseek.com/zh-cn/news/news260424)
- [DeepSeek-V4 技术报告](https://arxiv.org/abs/2606.19348)
- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
- [τ²-bench](https://github.com/sierra-research/tau2-bench)
- [Toolathlon](https://github.com/hkust-nlp/Toolathlon)
