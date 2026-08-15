# AgentFit 初赛作品简介

> 状态：初赛唯一提交版本。正文按非空白字符计数不得超过 500；完成态只引用仓库内可核验事实。

## 核心主张（一句话）

**AgentFit 是 Agent 方案建筑师：从企业材料、代表性案例和优先级出发，构建、验证并交付最小充分的完整方案。**

## 500 字以内作品简介

企业提供业务材料、代表性案例和优先级，却常不知道是否该自动化、该用哪些 Agent 与能力。AgentFit 是面向 AgentTeams 构建的 Agent 方案建筑师：把材料与案例编译成验收约束，从最简单方案开始运行；依据证据在四层资产（原子接口、工具封装、可复用知识、DAG 组合）上做受限的层级化调整；用新案例验证后交付最小充分的已验证方案包，也允许保留人工或拒绝自动化。它把机器学习中“样本构建、批量试验、误差分析和验证停止”的工程范式硬映射化：方案空间按层级离散化，以证据驱动的层内更新与场景内持续学习（回归池防遗忘、漂移探针防漂移）取代对黑盒节点的可微性假设；调整的不是模型权重，而是完整 Agent Solution。

OpsPilot 是官方案例锚点，仅作材料与设计参考。retail/airline 探索为非官方 evaluator 的 Demo。真实运行：五元团队已在 AgentTeams 官方镜像实例化并完成三轮 ProjectCase preparation，Candidate 与统一对照尚未运行。

## 字数与事实边界

- 计数口径：仅统计上一节正文，移除所有空白后实测不超过 500。
- OpsPilot Zero 是官方发布示例，作 official-case anchor，非 AgentFit 运行证据。
- retail/airline overnight 探索依赖 DeepSeek、OpenCode、本地路径/原始记录、自建工具与代理评估器；不能替代官方 evaluator 或正式 Candidate。
- AgentTeams 历史 smoke 只证明平台能力，不等于 AgentFit 已集成。
- 真实状态：五元团队已在 AgentTeams 官方镜像实例化（Team `Active`），完成三轮 ProjectCase preparation（Round 3 终态完整、治理审查 SUCCESS 有条件）；四份 SampleSetManifest 尚未实例化冻结，ProjectCase、统一候选对照与真实 Episode/Trace 尚未完成；不捏造分数或赢家。
- 四层资产（原子接口 / 工具封装 / 可复用知识 / DAG 组合）、层内更新白名单、回归池与漂移探针为 v4 设计契约；层级触达校验与持续学习度量属 M2 实现范围。
