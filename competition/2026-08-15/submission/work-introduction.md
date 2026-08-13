# AgentFit 初赛作品简介

> 状态：初赛唯一提交版本。正文按非空白字符计数不得超过 500；完成态只引用仓库内可核验事实。

## 核心主张（一句话）

**AgentFit 是通用 Agent 方案建筑师：用官方 OpsPilot baseline 作首个 ProjectCase，把“该用几个 Agent”变成有证据、可验收的方案选择，再从案例回到通用方法。**

## 500 字以内作品简介

企业要为故障自愈选 Agent 方案：用 0 个、1 个、多个，还是保留人工？OpsPilot 官方 baseline 证明这类故障值得做，却没回答该用哪种。

AgentFit 是运行在 AgentTeams 上的通用 Agent 方案建筑师。它把 OpsPilot baseline 编译成首个 ProjectCase；用 db_pool_exhausted、slow_sql_degradation 两个事故定义 TaskSample 的输入、输出与验收。四类候选共享同一搜索空间与冻结样本，在同一预算与门禁下比较，最简合格者胜出。

五个元 Agent 设计并评测方案，区别于候选 C2 内的业务执行 Agent；HTTP 与 MCP 是等价工具契约，Project Dossier 是事实源。最终交付可复验、可回滚的 AgentSolutionPackage，或诚实保留人工。

当前 baseline 已代码级审计、AgentTeams 平台已 smoke；AgentFit 的 ProjectCase、五元团队与候选对照仍待真实运行，Meta-learning 是未来方向，本轮结论 requires_runtime_trial。

## 字数与事实边界

- 计数口径：仅统计上一节正文，移除所有空白后实测不超过 500。
- OpsPilot Zero 是官方发布示例，作 baseline 与首个 ProjectCase 参考，非 AgentFit 运行证据。
- 两个事故是说明 TaskSample 的设计契约，标“设计契约，非运行证据”。
- AgentTeams 历史 smoke 只证明平台能力，不等于 AgentFit 已集成。
- ProjectCase、真实五元团队、统一候选对照与真实 Episode/Trace 尚未完成；不捏造分数或赢家。
- 跨项目 Meta-learning 当前未实现。
