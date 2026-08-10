# AgentFit 初赛方案 PPT/PDF 骨架

> 状态：内容骨架已形成，证据页必须由真实运行结果补全。
>
> 建议规模：12 页正文，附录放 Identity、Skill、依赖和声明清单。

## 第 1 页：项目与一句话定位

- 项目名：AgentFit；
- 一句话：运行在 AgentTeams 上、为具体任务搜索并验证最小充分 Agent 方案的元团队；
- 当前阶段与证据等级；
- 不使用未经验证的效果数字。

## 第 2 页：真实问题与目标用户

- 企业面对重平台和轻框架两个极端；
- 已有材料、流程和系统无法直接变成可审计 Agent 方案；
- 输入、输出、现有人工/系统基线和失败成本；
- 首个 ProjectCase 获批后用真实场景替代宽泛描述。

## 第 3 页：为什么现有方法不够

- 预设多 Agent，缺少 Agentless 和单 Agent基线；
- Agent、Skill、MCP、Memory 和 Workflow 边界混乱；
- 缺少统一预算下的拓扑对照；
- 缺少拒绝自动化、Human 门禁和审计结果。

## 第 4 页：AgentFit 方法

- TaskSemanticSpec：输入、输出、指标、权衡、预算和风险；
- CapabilitySemanticRegistry：Skill、Tool、MCP、Memory、模型、算法和 Human；
- Candidate `(G, Π, θ, ρ)`；
- 内循环优化局部参数，外循环调整结构；
- Meta-learning 只在跨项目未见任务验证后成立。

## 第 5 页：基于 AgentTeams 的系统边界

- AgentTeams：身份、Worker/Team/Human、通信、容器、文件、凭证、Skill/MCP 绑定；
- AgentFit：语义、候选、实验、审计与交付；
- 使用 AgentTeams 原有 Dashboard 和聊天入口；
- 不开发独立前端，不修改 AgentTeams 核心。

## 第 6 页：五个元 Agent

- EngagementLead；
- BusinessEngineer；
- AgentArchitect；
- ValidationEngineer；
- GovernanceAuditor；
- 对每个 Agent 展示官方 Identity 八字段及独立责任产物。

## 第 7 页：端到端八步闭环

逐项对应官方闭环：任务输入、任务拆解、上下文传递、工具调用、结果验证、执行证据、审批回滚、经验沉淀。每一步展示责任 Agent、输入、输出、AgentTeams 通道和 Trace。

## 第 8 页：Skill、工具与上下文

- 核心 Skill 的契约、调用条件、失败、权限和复用；
- MCP 只用于确定性工具或外部系统接入；
- 至少明确实现共享状态与轨迹可观测；
- Agent 记忆或 RAG 仅在首个 ProjectCase 有必要时采用；
- 阿里云官方 Skill 的使用或不使用均给出必要性证据。

## 第 9 页：候选搜索与公平评测

- Agentless、固定 Workflow、单 Agent、多 Agent和 Human 混合候选；
- adaptation、validation、holdout、failure set 隔离；
- 统一模型、工具、预算、输入和指标；
- Pareto 权衡质量、成本、时延、安全与复杂度；
- 不预设多 Agent获胜。

## 第 10 页：真实运行证据

本页在最小闭环运行后生成，只允许展示：

- 冻结的 ProjectCase 和版本；
- AgentTeams 版本与资源拓扑；
- 一条完整协同 Trace；
- 候选执行结果与成本；
- 一个失败、降级、拒绝或 Human 门禁分支；
- 可复现命令或证据包入口。

运行前不得用本地 `demo/` 或历史 AgentTeams smoke test填充本页。

## 第 11 页：安全、审计和开放边界

- 数据、模型、商业 API、密钥和许可证；
- 高风险动作审批、拒绝、超时与回滚；
- GovernanceAuditor 的独立性；
- 赛前已有 AgentTeams fork与比赛期间 AgentFit 新增贡献；
- 计划开放的 Schema、Skill、样例、评测或插件范围。

## 第 12 页：当前进展与复赛路线

- 用“设计”“已单独试用”“真实集成”“真实评测”区分完成度；
- 初赛前已经完成的事实；
- 复赛代码包、Demo、更多 ProjectCase 和迁移验证计划；
- 不把 AIOpsLab → ITBench 迁移假设写成 Meta-learning 成果。

## 附录

1. 五个 Agent Identity 表；
2. 核心 Skill 清单；
3. 工具、模型、AgentTeams 和第三方依赖版本；
4. 数据来源、授权和可再分发边界；
5. 指标计算与 Trace 字段；
6. 红线检查结果；
7. Evidence Registry 指针。
