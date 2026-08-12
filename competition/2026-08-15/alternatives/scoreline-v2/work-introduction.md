# AgentFit 评分主线版（scoreline-v2）作品简介

> 状态：与冻结版并排的替代路演候选。正文按非空白字符计数不得超过 500；完成态只引用仓库内可核验事实。

## 核心主张（一句话）

**AgentFit 用官方 OpsPilot baseline 作首个 ProjectCase，把“该用几个 Agent”变成有证据、可验收的方案选择。**

## 500 字以内作品简介

企业要为故障自愈选 Agent 方案：用 0 个、1 个、多个，还是保留人工？OpsPilot 官方 baseline 证明它值得做，却没回答“该用哪种”。

AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师。它把 OpsPilot baseline 编译成首个 ProjectCase 与证据锚点；用 db_pool_exhausted、slow_sql_degradation 两个事故定义可重放的 TaskSample、输入输出与验收；再由交付官、业务架构师、方案架构师、验证工程师、审计官五元元团队生成 C0 无 Agent、C1 单 Agent、C2 多 Agent、C3 Human 混合候选，在同一冻结样本集、预算与安全门禁下公平比较。HTTP 与 MCP 是等价工具契约，Project Dossier 是事实源。

最终交付可部署、可复验、可回滚的 AgentSolutionPackage，也可有证据地保留人工或拒绝自动化。当前 baseline 已代码级审计、AgentTeams 平台能力已 smoke；AgentFit 的 ProjectCase、五元团队与候选对照仍待真实运行，本轮结论 requires_runtime_trial。

## 字数与事实边界

- 计数口径：仅统计上一节正文，移除所有空白后实测见下方校验脚本；不超过 500。
- OpsPilot Zero 是官方发布示例，作 baseline 与首个 ProjectCase 参考，非 AgentFit 运行证据。
- 两个事故是说明 TaskSample 的设计契约，标“设计契约，非运行证据”。
- AgentTeams 历史 smoke 只证明平台能力，不等于 AgentFit 已集成。
- ProjectCase、真实五元团队、统一候选对照与真实 Episode/Trace 尚未完成；不捏造分数或赢家。
