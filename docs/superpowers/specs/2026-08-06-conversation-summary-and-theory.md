# AgentFit 完整对话总结与理论沉淀

> 日期：2026-08-06
>
> 状态：完整对话总结，含理论贡献、调研结论、代码实现、赛题对照和初赛简介
>
> 仓库：`kaiiangshang/agentfit`（比赛期间保持私有）
>
> 依赖框架：AgentTeams（原名 Hiclaw，agentscope-ai 开源项目）

---

## 目录

1. [起点：项目理解与推演](#1-起点项目理解与推演)
2. [核心理论：ML 类比与图模型统一抽象](#2-核心理论ml-类比与图模型统一抽象)
3. [四个场景推演](#3-四个场景推演)
4. [框架调研结论](#4-框架调研结论)
5. [代码实现与测试结果](#5-代码实现与测试结果)
6. [赛题对照与定位精确化](#6-赛题对照与定位精确化)
7. [初赛简介（厚版与定稿版）](#7-初赛简介厚版与定稿版)
8. [当前状态与待办](#8-当前状态与待办)

---

## 1. 起点：项目理解与推演

### 1.1 项目初始状态

仓库仅有一份 526 行设计讨论记录（`2026-08-05-agentfit-project-design.md`），无任何代码。该文档记录了：

- AgentFit 定位为"基于 AgentTeams 的虚拟 Agent 解决方案工程团队"
- 五 Agent 元团队（EngagementLead、BusinessEngineer、AgentArchitect、ValidationEngineer、GovernanceAuditor）
- 八阶段主流程（Intake→Discover→Architect→Approve→Trial→Audit→Deliver→Learn）
- 大量设计原则已确认，但 18 项关键细节未决定

### 1.2 推演发现的六个核心张力

对八阶段流程做完整推演后，发现以下问题：

1. **元层与对象层共享 AgentTeams 资源**：AgentFit 自己是 5 Agent 团队，又要动态创建候选团队，两者如何隔离？
2. **自动化边界分析缺乏方法论**：BusinessEngineer 划自动化边界凭什么？LLM 主观判断违反"不用主观评价当验证"原则。
3. **Skill 占评分 25% 但完全未定义**：核心 Skill 清单、输入输出、版本策略全部空白。
4. **Agent Identity 是硬性要求但只有角色名**：完整字段（能力、权限、约束、记忆策略）未设计。
5. **不同架构如何公平比较**：脚本和多 Agent 运行方式根本不同，评分归一化方法未定义。
6. **动态团队创建能力未验证**：Trial 阶段需要编程式创建/销毁临时 AgentTeams，这在 v1.1.2 是否可靠？

其中第 2 和第 5 个张力后来被 ML 类比和图模型直接解决。

---

## 2. 核心理论：ML 类比与图模型统一抽象

### 2.1 ML 类比的逐步澄清

**用户的初始想法**："像训练机器学习模型一样，从初始数据拟合评估到逐步的增量更新学习。"

**澄清一：映射层面。** 用户明确是 sklearn 式的——提供几种已有模型，拟合任务，比较谁更好。

> 用户原话："我们提供的是几个已有 agent 模型，然后做的是拟合任务，就像是 sklearn 一样，我知道是回归任务，但是我不确定哪个比较好，是不是组合更好。"

**澄清二：Agent 的"拟合"是什么。** Agent 基于 LLM，没有可训练权重。拟合映射为：

| sklearn | AgentFit |
|---|---|
| 模型参数（weights） | System Prompt（业务规则、决策标准） |
| 特征工程 | Tool / Skill 选择 |
| 超参数 | 工作流结构、决策阈值、记忆策略 |
| fit(X_train, y_train) | AgentArchitect 用业务材料和示例任务配置候选 |
| predict(X_test) | ValidationEngineer 在未见过的任务上运行候选 |
| score() | GovernanceAuditor 对验收标准打分 |
| model selection | 选满足阈值的最简候选 |
| transfer learning | 跨项目复用已验证模板，但仍需重新 fit + test |

关键区分：fit 那一步，ML 改的是权重，AgentFit 改的是配置。本质是 model selection，不是 model training。

**澄清三：方法论靠什么落地。** 三层嵌套确认：

| 层级 | 职责 | 机制 |
|---|---|---|
| Agent Identity（怎么想） | 决定 Agent 天生这样思考 | 写入角色定义和 prompt |
| 状态机门禁（做该做的） | 保证执行了必要步骤 | Discover 阶段数据集不足不允许进入 Architect |
| 审计准则（确认真的做好了） | 事后核验 ML 纪律 | GovernanceAuditor 逐项检查 |

**用户关键纠正**："借助思想和方法论，而不是硬接口。"

ML 概念活在三层载体里，不是代码层强制对齐 fit/predict/score 接口。脚本和多 Agent 本质不同，硬接口会把"最小方案"原则扭成"所有东西都得长成同一个形状"。

### 2.2 图模型统一抽象

**用户的关键贡献**："一个可部署的 agent，一定是一个 dag，局部可能是 scc 分量以及记忆依赖，优化整个节点图，是我们的核心。"

#### 节点类型（4 种）

| 类型 | 权重 | 说明 |
|---|---|---|
| LLM 推理节点 | 5.0 | 决策、理解、生成 |
| 工具节点 | 2.0 | 确定性执行 |
| 规则节点 | 1.0 | 模式匹配、阈值判断 |
| 人工节点 | 8.0 | 审批、复核 |

#### 边类型（4 种）

| 类型 | 说明 |
|---|---|
| 顺序边（Sequential） | 确定性流转 |
| 条件分支边（Conditional） | 基于状态路由 |
| 回边（Back） | 构成 SCC 有界循环 |
| 记忆依赖边（Memory） | 跨非相邻节点的状态读写 |

#### 整体结构

DAG 主干保证终止性，局部 SCC 提供有界迭代精化能力，记忆依赖边支持跨节点状态读写。

#### 两层搜索空间

用户进一步区分：Tool、记忆、Skill、MCP 不是图元素，是**节点的参数**。

```
图拓扑（结构搜索）              节点参数（配置搜索）
──────────────               ──────────────
节点数量、类型                挂载的 tools
边的连接方式                  memory 策略（短期/长期/共享）
哪里有 SCC                    skills（能力包）
记忆依赖的走向                MCP / 工具接口
分支与汇聚点                  system prompt / 决策阈值

= "骨架长什么样"              = "每个关节能做什么"
```

对应 NAS：拓扑搜索 = 搜图结构，operation search = 搜每个 cell 用什么算子。两层同时优化，目标都是最小充分复杂度。

#### 旧三分类自然变为连续复杂度梯度

| 旧分类 | 图模型 |
|---|---|
| 无 Agent | 只有规则节点和工具节点的线性 DAG |
| 单 Agent | 一个 LLM 节点 + 可能的局部自环 |
| 多 Agent | 多个 LLM 节点 + 通信边 + SCC 协作循环 |

不再是离散的三个桶，而是一个连续的复杂度空间。

#### NAS 精确类比

| NAS | AgentFit |
|---|---|
| 搜索空间：网络拓扑+每层算子 | 搜索空间：DAG 拓扑+每节点类型+边类型+SCC+记忆 |
| 搜索策略：渐进式 | 搜索策略：baseline-first（最简图→按需加复杂度） |
| 性能评估：精度/FLOPs/延迟 | 性能评估：正确率/稳定性/成本/可审计性 |
| 目标：最小足够精度架构 | 目标：最小足够性能的图 |

#### 复杂度计算公式

```
复杂度 = Σ(节点权重 × max_iter)
       + SCC数量 × 3.0
       + 记忆依赖数量 × 2.0
       + 条件分支数量 × 1.0
```

复杂度标签：minimal (≤5) / low (≤15) / moderate (≤35) / high (>35)

### 2.3 同域增量与跨域泛化

**用户纠正"冻结"假设**：业务场景本身在增长，部署的 Agent 不应该永久冻结。

**同域鲁棒（域内增量）**：

```
初始材料 → fit → test → 部署
  → 生产中出现新案例（新产品线、政策变更、季节性模式、边界 case）
  → 新案例回流为数据
  → 数据集扩大 → 重新 fit → 重新 test → 升级或保持
  → 循环
```

= 更多 epoch，数据集逐轮增长，鲁棒性提升。不是在线学习（那违反"高风险动作需审批"原则），是批量重验证。

**跨域泛化（域间迁移）**：

```
域 A 多个项目 → 域 A 模式提取
域 B 新项目 → 域 A 模式作为先验起步 → 但必须独立 fit + test
域 B 模式提取 → 与域 A 对照 → 哪些模式真正跨域通用？
→ 跨域抽象模式进入通用资产库
→ 域 C 受益于 A+B 的积累
```

= transfer learning。资产库两层：域特定资产（只在同域检索）和跨域通用资产（任何域可参考）。

Learn 阶段有两个输出：域内案例喂回同域下一轮 epoch 的数据集；跨域抽象模式喂给其他域未来项目的 Architect 阶段作为先验。

### 2.4 方法论的载体：结构产物驱动

三个结构化产物，方法论固化在 Schema 里：

**TrialSpec（试验规格）**——Trial 阶段的输入契约：
```
dataset:              标注任务列表（输入/预期输出/难度/证据指针）
train_split:          用于配置候选的任务索引
test_split:           用于打分的任务索引（对 Architect 不可见）
acceptance_criteria:  验收阈值（正确率/稳定性/成本上限）
complexity_budget:    允许的最大架构复杂度
fault_plan:           故障注入类型和时机
```

**CandidateCard（候选卡片）**——AgentArchitect 为每个候选生成：
```
type:                 no-agent / single-agent / multi-agent
complexity:           声明的复杂度等级
rationale:            为什么这个复杂度是合理的（不是过拟合材料）
configuration:        prompt / tools / skills / workflow
expected_fit:         预期能解决什么 / 预期会在哪里失败
```

**EvaluationReport（评估报告）**——GovernanceAuditor 产出：
```
per_candidate:
  train_score:        训练集表现
  test_score:         留出集表现
  overfit_signal:     train vs test 差距是否过大
comparison:           多维归一化对照表
diagnosis:            欠拟合 / 过拟合 / 恰当
recommendation:       选谁 / 否决 / 补试
evidence_refs:        每条结论指向运行日志的具体位置
```

方法论活在字段的存在性里：不填 `test_split`，状态机不让进 Trial；没有 `rationale`，CandidateCard 不完整。

### 2.5 五个核心理论贡献

1. **Agent 即图**——统一架构空间为 DAG + SCC + 记忆依赖
2. **ML 评估方法论**——train/test 分离、过拟合检测、baseline-first
3. **NAS 式搜索**——渐进式复杂度搜索，最小充分原则
4. **有证据的否定权**——能证明不该自动化
5. **同域增量 + 跨域迁移**——业务场景增长的双层学习机制

---

## 3. 四个场景推演

四个场景代表图空间里的不同复杂度落点，从最简到否决。

### 3.1 场景一：发票报销审批 → 线性 DAG

**数据集**：8 个标注任务（金额阈值、税号检查、重复检测）

**搜索过程**：
- baseline（线性规则图）：test 75%，欠拟合（缺税号检测、模式异常）
- 加一个 LLM 分支节点：test 95%，成本极低（5% 流量进 LLM）

**最终部署图**：
```
[规则:金额] → [规则:阈值] →┬─ [输出]
                            └─ [LLM:模式] → [输出]
```
复杂度：O(n) 线性，无环，最简。

### 3.2 场景二：产品评价分析 → 单 LLM + SCC

**数据集**：10 个标注任务（正面/负面/混合/反讽）

**搜索过程**：
- 关键词匹配：test 55%，严重欠拟合
- 单 LLM：test 78%，混合情感和反讽处理不足
- 单 LLM + SCC（分析⇄自检迭代，max 3）：test 87%
- Audit 验证 SCC 必要性：去掉 SCC 降 9 个百分点

**最终部署图**：
```
[LLM:情感分析] ⇄ [LLM:自检] → 输出
   SCC, 最大迭代3次
```

### 3.3 场景三：智能客服退款 → 多节点 DAG + SCC + 记忆

**数据集**：10 个标注任务（标准退款、质量问题、欺诈检测、VIP 处理）

**搜索过程**：
- baseline（规则）：test 40%，严重欠拟合
- 加 LLM 分类：test 58%，意图理解了但没查政策和历史
- 加工具节点 + 记忆依赖：test 72%，复杂 case 不稳定
- 加 SCC（政策核查迭代）：test 88%，达标
- Audit 逐节点边际价值分析：每个节点的去掉后 test 下降量
- Audit 发现过拟合 VIP 规则的信号，修正

**最终部署图**：
```
[规则:金额]→[LLM:意图]→[工具:历史]→[工具:政策]→[LLM:分析⇄核查]→[LLM:决策]→[人工?]→输出
                                    └──SCC(≤3)──┘  └─记忆─┘
```

### 3.4 场景四：法律合同审查 → 否决自动化

**数据集**：10 个标注任务（标准条款、风险条款、间接责任、跨文档冲突）

**搜索过程**：
- 规则 baseline：test 35%，合同语义复杂
- 单 LLM：test 62%，高风险 case 遗漏风险点
- 多 LLM + SCC + 记忆：test 74%，但高风险 case 只有 50%
- 过拟合检查：Architect 针对高风险加的分支在留出集上反而更差

**关键决策**：
- 高风险 case test 准确率 50% → 漏判率 50%
- 法律场景漏判代价极高
- 无法通过验收阈值（要求漏判率 < 5%）
- **结论：当前条件下不应自动化高风险合同审查**

这就是设计文档强调的**否定权**——通过图模型评估，有证据地否决。

### 3.5 四场景在图空间的位置

```
复杂度 →

场景一        场景二        场景三        场景四
线性DAG       单SCC         多节点+SCC+记忆   否决区
(规则+1LLM)   (1LLM+自检)   (3LLM+2工具)    

[○]→[□]      [○]⇄[○]      [○]→[□]→[□]⇄[○]→[○]   ✗
```

---

## 4. 框架调研结论

并行调研 6 大框架 + AgentTeams 基座。

### 4.1 LangGraph

- **执行模型**：Pregel / Bulk Synchronous Parallel (BSP)，以超级步推进
- **图结构**：原生支持有环图，循环是一等公民
- **通信**：State + Reducer（共享内存，节点只返回 partial update）
- **循环终止**：条件边 + END / recursion_limit / RemainingSteps / Command(goto=END)
- **并行**：静态多边（同 super-step）+ Send API（动态 map-reduce）
- **子图嵌套**：支持，含跨层跳转 Command.PARENT
- **核心洞察**：Agent 就是图。ReAct Agent 本身是含环图（LLM ⇄ tool）

11 种典型拓扑模式：

| 模式 | 图结构 |
|---|---|
| Prompt Chaining | 链式 + 门控条件边 |
| Parallelization | START → [N个并行] → fan-in |
| Routing | 条件分支到不同处理器 |
| Orchestrator-Worker | Send API 动态 fan-out |
| Evaluator-Optimizer | generator→evaluator→(条件)generator |
| ReAct Loop | LLM⇄tool 双向边 |
| Subagents | 星型 hub-and-spoke |
| Handoffs | 动态有环图，Command(goto) |
| Skills | context 加载模式 |
| Router | 分类→专用 Agent |
| Custom Workflow | 自由编排 |

### 4.2 AutoGen

- **核心范式**：消息传递（对话驱动）
- **拓扑**：Two-agent / Sequential / Group chat / Nested / Swarm / GraphFlow
- **发言顺序**：round_robin / random / manual / auto（LLM 决定）
- **约束转移图**：`allowed_or_disallowed_speaker_transitions` = 有向图邻接矩阵
- **适合**：动态、开放式多 Agent 协作

### 4.3 CrewAI

- **核心范式**：工作流驱动（任务驱动）
- **Crew** = Agents + Tasks + Process（Sequential / Hierarchical）
- **Task 依赖**：顺序 / context 显式依赖 / async 并行 / ConditionalTask 条件
- **Flows**：显式 DAG（@start/@listen/@router），支持 AND/OR 汇聚
- **适合**：结构化、可预测的生产级管道

### 4.4 MetaGPT

- **核心范式**：SOP + 发布订阅消息（混合）
- **拓扑**：隐式有向图，由 `_watch` 订阅关系构成
- **"软件公司"模拟**：ProductManager→Architect→ProjectManager→Engineer→QA 线性链
- **核心哲学**：`Code = SOP(Team)`
- **边定义**：目标节点的 `_watch` 反向定义（被动订阅）

### 4.5 OpenAI Agents SDK

- **核心范式**：会话历史转移 + 代码编排
- **Handoffs**：本质是 DAG 边（有向控制转移），实现上伪装成 tool call
- **支持循环**：A handoff B, B handoff A，靠 max_turns 兜底
- **Guardrails**：Input（入口关卡）/ Output（出口关卡）/ Tool（包裹工具边）
- **Tracing**：Trace → Span 树形层级
- **边定义**：源节点的 `handoffs` 列表显式声明（主动委派）

### 4.6 Anthropic 多 Agent 实践

- **拓扑**：Orchestrator-Worker 星型
- **双层级并行**：Agent 级（3-5 个 Subagent 并行）+ Tool 级（每个 Subagent 内 3+ 工具并行）
- **通信策略**：星型中转 + Artifact 绕行（Subagent 输出存文件系统，只传轻量引用）
- **上下文管理**：隔离 + 压缩回流 + Memory 持久化
- **关键洞察**：Subagent 的核心价值是"compression"——从海量信息中提炼最重要的 token
- **与 AgentFit 的吻合**：Artifact 绕行 = Project Dossier + Task Envelope

### 4.7 DSPy

- **核心范式**：声明式 LLM 编程（PyTorch 式）
- **Signature**（做什么）+ **Module**（怎么做）= 任务定义与执行策略分离
- **编译（Compilation）**：这是与 NAS 最精确的类比

| NAS 搜索的东西 | DSPy 搜索的东西 |
|---|---|
| 网络层类型 | Module 类型（Predict/ChainOfThought/ReAct） |
| 层的超参数 | Prompt 指令 |
| 连接拓扑 | 模块组合方式 |
| 神经元数量 | Few-shot 示例的选择和数量 |

- **优化器**：GEPA（指令进化）/ MIPROv2（指令+示例联合）/ BootstrapFewShot（成功执行提取 demonstrations）
- **评估**：完整 train/test split + metric（可返回 score + feedback）
- **对 AgentFit 的启发**：DSPy 已证明声明→搜索→评估→选择闭环可行。AgentFit 在多 Agent 架构拓扑层面做同类事情。

### 4.8 AgentTeams（原名 Hiclaw）

- **身份**：agentscope-ai 开源项目，Apache 2.0，5.3k stars
- **架构**：K8s 原生 CRD（Manager / Worker / Team / Human）+ Matrix 通信（Tuwunel homeserver）
- **拓扑**：Manager→Team Leader→Workers，Manager 不穿透 Team（委派边界）
- **Skill 系统**：skills.sh 社区 8 万+，Worker 级隔离
- **安全**：Higress 网关，Worker 永远看不到真实凭证
- **版本**：v1.2.0 已稳定，TeamHarness 引入 DAG 为一等公民

### 4.9 调研核心结论

**所有框架最终都是"DAG + SCC + 记忆依赖"的组合，验证了图模型抽象的普适性。**

九种拓扑模式被提取为 AgentFit 的 pattern registry：
linear / router / react-loop / evaluator-optimizer / orchestrator-worker / debate / hierarchical / handoff-chain / sop-pipeline

---

## 5. 代码实现与测试结果

### 5.1 代码结构

```
src/agentfit/
├── graph/
│   ├── model.py          # AgentGraph + Node(4类) + Edge(4类) + 复杂度计算
│   ├── patterns.py       # 9种拓扑工厂
│   └── executor.py       # 图执行器（模拟 AgentTeams 协同）
├── pipeline/
│   ├── contracts.py      # TrialSpec + CandidateCard + EvaluationReport
│   ├── states.py         # 8阶段状态机 + 门禁
│   ├── dossier.py        # Project Dossier（append-only 可信状态）
│   └── orchestrator.py   # 驱动 5 Agent 走完整管线
├── agents/
│   ├── llm_sim.py        # LLM 模拟器（确定性 handler，可复现）
│   ├── engagement_lead.py
│   ├── business_engineer.py
│   ├── agent_architect.py
│   ├── validation_engineer.py
│   └── governance_auditor.py
└── evaluation/
    └── metrics.py

tests/scenarios/
├── expense_approval.py     # 场景1：费用审批
├── sentiment_analysis.py   # 场景2：情感分析
├── refund_processing.py    # 场景3：退款处理
└── contract_review.py      # 场景4：合同审查

run_evaluation.py           # 测试运行器
TEST_REPORT.md              # 完整测试报告
```

### 5.2 关键设计决策

- **方法论做成结构产物而非硬接口**：用户明确要求"借助思想和方法论，而不是硬接口"
- **resolver 机制**：候选有能力集合，任务有所需能力，resolver 判断能否解决——不同架构可比较
- **模拟器不依赖真实 AgentTeams**：用户要求"先模拟其协同方式构建骨架"
- **复杂度计算**：Rule=1, Tool=2, LLM=5, Human=8，SCC=+3, Memory=+2, Conditional=+1

### 5.3 测试结果

四个场景全部跑通，结果符合预期：

| 场景 | 选中方案 | Test准确率 | 核心发现 |
|---|---|---|---|
| 费用审批 | router-rule-llm | 100% | react 是 overkill，审计标记收益递减 |
| 情感分析 | eval-opt-scc | 100% | SCC 显著优于线性，过拟合检测生效（线性 20% gap） |
| 退款处理 | orchestrator-refund | 100% | 层级团队 vs 编排者：+18 复杂度换 0% 提升 |
| 合同审查 | REJECTED | 40% | 所有候选不达标，否定权行使 |

11 项 ML 方法论检查全部 PASS：

```
[PASS] baseline-first 纪律（4 场景）
[PASS] train/test 分离（无负过拟合）
[PASS] 过拟合检测（情感分析 20% gap，合同审查 20% gap）
[PASS] 最小充分候选选择（3 场景）
[PASS] 否定权（合同审查被拒绝）
[PASS] 资产产出（跨项目复用就绪）
```

### 5.4 跨场景模式有效性

```
Pattern               Scenarios  Avg Test Acc  Avg Complexity
evaluator_optimizer          1       100.0%           30.0
orchestrator_worker          1       100.0%           28.0
router                       3        73.3%           16.3
react                        4        70.0%           26.0
hierarchical                 2        70.0%           50.5
linear                       4        48.8%            2.0
debate                       1        40.0%           29.0
```

---

## 6. 赛题对照与定位精确化

### 6.1 赛题核心

> **赛题名称**：复杂任务多 Agent 自主协同
>
> **一句话**：聚焦复杂任务多 Agent 基础设施与协同系统，推动企业级 Agent 从 Demo 走向 Production

### 6.2 赛题八步闭环 vs AgentFit 映射

| 赛题八步 | AgentFit 对应 | 执行者 |
|---|---|---|
| 1. 任务输入 | 接收业务材料、问题、约束、期望结果 | EngagementLead |
| 2. 任务拆解 | 材料理解→边界分析→候选设计→试验计划→验证→交付 | EngagementLead 拆阶段，各 Agent 拆子任务 |
| 3. 上下文传递 | Project Dossier（结构化可信状态）+ Task Envelope | 所有 Agent 读写 Dossier |
| 4. 工具调用 | Skill（材料解析/边界分析/候选生成/故障注入/审计）+ MCP | 各 Agent 按需调用 |
| 5. 结果验证 | 候选方案在统一任务集上真实试运行 + train/test 分离 | ValidationEngineer |
| 6. 证据沉淀 | Trace + Dossier 版本 + EvaluationReport | 所有 Agent 写 Trace |
| 7. 审批与回滚 | 试验前审批 + 交付前确认 + 资产晋升门禁 | EngagementLead + 用户 |
| 8. 经验沉淀 | Learn 阶段：成功模式/失败模式/模板→可复用资产库 | GovernanceAuditor |

**八步完全覆盖。**

### 6.3 五项评分对齐状态

| 维度 | 权重 | AgentFit 状态 | 差距 |
|---|---|---|---|
| 场景价值与行业可复制性 | 25% | 强 | 无明显差距 |
| 多 Agent 协同与自主闭环 | 25% | 强 | 需映射到 AgentTeams 真实能力 |
| Skill 工程体系 | 25% | 空白 | 致命差距 |
| 工程落地与安全可审计 | 20% | 中 | 需真实 AgentTeams 部署 + 四选二能力 |
| 开源贡献 | 5% | 无 | 需 License + 可复用成果 |

### 6.4 硬性约束审计

| 硬性要求 | 当前状态 | 要做 |
|---|---|---|
| ≥3 Agent | ✅ 5 Agent | 完成 |
| AgentTeams 为基点 | ❌ 模拟器 | 映射 Manager/Worker/Team/Room |
| Agent Identity 清单 | ❌ 只有角色名 | 按附录 A 8 字段填写 |
| Skill 必选 | ❌ 完全空白 | 定义核心 Skill 清单（附录 B 10 字段） |
| MCP 或等价契约 | ❌ 无 | 定义等价工具集成契约 |
| 四选二 | ❌ 未选 | Project Dossier（共享状态）+ Trace（轨迹可观测）天然命中 |
| 审批回滚审计 | ✅ 设计已有 | 映射到真实工作流 |
| 开源/依赖披露 | ❌ 无 | License + 披露 |

### 6.5 定位精确化

用户纠正了 AgentFit 的定位理解：

> "为别人提供可部署的 agent 闭环能力，也是和比赛一致的。"

AgentFit 的输出本身就是可部署的多 Agent 闭环系统——这正是赛题"推动 Agent 从 Demo 走向 Production"的核心诉求。不是评估工具，是 Agent 解决方案工程团队。

### 6.6 红线提醒

> 仅提交概念/PPT/营销材料，无法提供 PoC、实验、仿真、日志、视频或等价可验证材料——原则上淘汰或严重扣分。

AgentFit 已有模拟验证证据（TEST_REPORT.md），降低了此风险。

---

## 7. 初赛简介

### 7.1 定稿版（452 中文字，500 字以内）

**项目名称**

AgentFit — Agent 架构搜索：用机器学习方法论为业务场景找到最小可行的 Agent 图

**问题与场景**

Agent 落地缺少架构决策层。该用规则还是 Agent？单 Agent 还是多 Agent？什么拓扑？这些问题目前全靠直觉。现有工具要么假设你已知道答案，要么生成 Prompt 但不验证。缺少的是：把"该用什么 Agent"当作一个可以被结构化搜索和评估的工程问题。

**核心解决方案**

提出三个命题。（1）Agent 即图：所有候选方案统一建模为图结构（DAG + SCC + 记忆依赖），从规则脚本到多 Agent 协作都是同一空间的复杂度梯度。（2）方案可被评估：借鉴 ML，业务材料构造数据集，配置候选即拟合，留出集运行即测试，表现决定去留。（3）搜索有方法论：借鉴 NAS，baseline-first 渐进式搜索——先生成最简图，仅在欠拟合时加复杂度，每步做复杂度-价值权衡。五人工程团队运行于 AgentTeams，执行八阶段闭环完成上述过程。

**创新点与差异化**

这不是更好的 Agent 框架，是此前不存在的概念层：把 Agent 架构选择从手工经验变成有 train/test 分离、过拟合检测和否定权的工程方法论。差异化终点不是"能做更多"，而是"能证明不该做"——有证据地否决自动化。

**开放/复用价值**

Agent 图模型抽象与九种拓扑模式库、五 Agent Identity 模板、核心 Skill 体系、结构化评估契约（TrialSpec / EvaluationReport）、场景测试数据集。方案图模板跨项目脱敏复用，同域增量变鲁棒，跨域迁移可验证。

**当前进展**

图模型与九种拓扑已实现，五 Agent 与八阶段状态机已跑通，四场景模拟验证完成（线性图、SCC 图、协作图、否决案例各一），11 项 ML 方法论检查全部通过。下一步接入真实 AgentTeams。

### 7.2 厚版（完整论述，不限字数）

厚版保存在对话记录中，包含三个命题的详细展开、调研结论引用、四个场景验证细节、与 DSPy/LangGraph 等框架的对比分析、跨项目复用机制完整描述。

---

## 8. 当前状态与待办

### 8.1 已完成

- [x] 图模型设计（Node 4 类 / Edge 4 类 / 复杂度计算）
- [x] 九种拓扑模式实现（linear / router / react / evaluator-optimizer / orchestrator-worker / debate / hierarchical / handoff / sop）
- [x] 五 Agent 逻辑实现
- [x] 八阶段状态机与门禁
- [x] 评估管线模拟验证（四场景）
- [x] ML 方法论检查框架（11 项全部通过）
- [x] 赛题 PDF 提取与分析
- [x] 作品简介定稿（500 字以内）
- [x] 六大框架调研完成

### 8.2 待办

- [ ] 方案 PPT 四章内容梳理
  - [ ] 第一章：场景与价值
  - [ ] 第二章：方案设计
  - [ ] 第三章：Skill 与工具集成
  - [ ] 第四章：可行性与落地计划
- [ ] Agent Identity 清单（附录 A 8 字段 × 5 Agent）
- [ ] Skill 清单（附录 B 10 字段）
- [ ] AgentTeams 映射（Manager/Worker/Team/Room 拓扑）
- [ ] 真实 AgentTeams 部署（产生真实 Trace 和协作日志）
- [ ] 四选二能力正式确认（共享状态 + 轨迹可观测）
- [ ] 开源计划与 License

### 8.3 时间线

- 初赛截止：2026-08-16（还有 10 天）
- 初赛必交：500 字简介 + 方案 PPT
- 初赛可选：AgentTeams 代码包（有和没有风险不同）
- 复赛截止：2026-09-03（需可执行代码 + 可运行 Demo）
- 决赛：2026-09-22（线下答辩）

---

## 附录：核心理论命题速查

### 命题一：Agent 即图

所有候选方案统一建模为图结构。节点 4 类（LLM/Tool/Rule/Human），边 4 类（Sequential/Conditional/Back/Memory）。整体 = DAG 主干 + 局部 SCC + 记忆依赖。旧的"无/单/多 Agent"三分类变为连续复杂度梯度。复杂度可计算、可比较。

### 命题二：方案可被评估

借鉴 ML 评估方法论。业务材料 = 数据集，配置候选 = fit，留出集运行 = predict，打分 = score。Train/test 分离防止过拟合。留出集表现决定方案去留。Agent 方案好不好不靠主观判断，靠留出集表现。

### 命题三：搜索有方法论

借鉴 NAS。Baseline-first：先生成最简图，仅在欠拟合时加复杂度，每步做复杂度-价值权衡。不做暴力遍历。最终选最小充分图。方法论活在三层载体里：Identity（怎么想）、状态机（做该做的）、审计（确认做好了）。

### 命题四：有证据的否定权

如果所有候选在留出集上都无法达到验收阈值，系统有证据地结论：当前条件下不应自动化。这不是失败，是正确的工程决策。这是 AgentFit 与所有 Agent 推销工具的根本区别。

### 命题五：同域增量 + 跨域迁移

同域：数据集逐轮扩大，批量重验证（更多 epoch）。跨域：方案模板作为先验起步，但仍需独立 fit + test。资产库两层：域特定 + 跨域通用。Learn 阶段双输出：域内案例喂回同域，跨域模式喂给其他域。
