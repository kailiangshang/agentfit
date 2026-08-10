# AgentFit 初赛路演稿说明

> 状态：12 页 HTML-first 内部草案；第 11 页中的“证据待补”必须在真实运行后替换。

## 可审阅与可复现文件

- [可编辑 PPTX](agentfit-preliminary-draft.pptx)
- [同版 PDF](agentfit-preliminary-draft.pdf)
- [HTML 幻灯片源稿](slides/)
- [确定性生成器](build_presentation.py)
- [内容与页数校验器](validate_presentation.py)

HTML/CSS 是布局事实源，由浏览器完成 1280×720 排版，再通过 `html2patch` 编译为 PowerPoint 原生可编辑文本、容器和线条。PPTX 不是整页截图；只有未来无法稳定转译的复杂纹理或插画才允许作为图片嵌入。

重新生成并校验：

```bash
/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  competition/2026-08-15/submission/build_presentation.py

/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  /home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  inspect --issues

soffice --headless --convert-to pdf \
  --outdir competition/2026-08-15/submission \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx

/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pdf
```

## 十二页故事线

### 第 1 页：企业缺的不是更多 Agent，而是可验证的架构选择

- 以 Task 为中心展示 Agentless、单 Agent、多 Agent和 Human 混合并列候选；
- 明确搜索目标是满足硬门槛的最简单方案，而不是最多 Agent；
- 用 Search Trace 预告全稿主线。

### 第 2 页：一条用户反馈，背后是四次不同决策

- 使用“预测结果明显不对”的用户反馈定位示意；
- 将任务拆为聚合、定位、核验和交付；
- 显式标注“示意场景，不是运行证据”。

### 第 3 页：平台给了能力，方案决策仍然留给企业

- 对照重平台“什么都有”和轻框架“只有框架”；
- 两条路径共同指向方案工程与证据闭环缺口；
- AgentFit 定位为决策层，不是新的运行时。

### 第 4 页：AgentFit 把“我要自动化”变成可验证搜索

- 编译任务语义；
- 对齐 Skill、MCP、Memory、Human 和 Agent 能力语义；
- 将 Agentless、单 Agent和多 Agent/Human 表示为并列候选拓扑；
- 内循环优化局部执行体，外循环改变结构与门禁。

### 第 5 页：官网四类案例共享同一闭环骨架

- 映射零人工运维、智能客服自主闭环、软件研发全流程协同、金融风控与理赔自动化；
- 四条泳道共同使用聚合输入、定位判断、生成处置、验证确认、经验沉淀五阶段；
- 标注官网 URL 与 2026-08-10 核验日期。

### 第 6 页：软件研发案例先拆任务，不先拆 Agent

- 使用多源聚合、代码定位、修复生成、验证发布和经验沉淀五段流程；
- 区分必须交付与不得假设；
- 输出版本化 `TaskSemanticSpec`；
- 标记“设计模拟，非运行证据”。

### 第 7 页：设计模拟的正确结果是 TrialSpec，不是宣布赢家

- 对照 C0 Agentless、C1 单 Agent、C2 多 Agent 三条赛道；
- 三条赛道共同汇入 Human Gate；
- 结论固定为 `selected_candidate = null`、`requires_runtime_trial`。

### 第 8 页：五个元 Agent 组成责任链

- EngagementLead 冻结目标；
- BusinessEngineer 编译任务；
- AgentArchitect 生成候选；
- ValidationEngineer 执行公平评测；
- GovernanceAuditor 独立门禁；
- 交接产物进入同一项目事实源与 Trace。

### 第 9 页：AgentTeams 负责运行，AgentFit 负责方案选择

- AgentFit 层包含任务契约、能力图、候选 Trial 和方案包；
- Project Dossier 承载版本化状态、Artifact、ExecutionTrace 和 DecisionLedger；
- AgentTeams 层复用身份、人员、通信、容器、文件、Cron、Skill 和 MCP；
- 不开发独立前端，不修改 AgentTeams 核心。

### 第 10 页：交付物是一份能部署、复验和回滚的方案包

- WHAT：任务、身份、拓扑和责任；
- HOW：Skill、MCP、Memory、共享状态和恢复；
- PROOF：统一评测、结果、Trace、审计和来源；
- SAFETY：权限、拒绝、回滚、Provenance 和许可证；
- 未见项目验证前不宣称 Meta-learning。

### 第 11 页：“没有证据”也是可审计结果

- 方法论与官网案例设计模拟分别标记完成状态；
- AgentFit × AgentTeams 集成和真实候选对照继续标记“证据待补”；
- Human 保留批准、拒绝和回滚门禁；
- 没有 Trace，不改变项目状态。

### 第 12 页：初赛交付方法，复赛证明边际价值

- READY：方法论和官网案例拆解；
- FREEZE：首个 ProjectCase、任务、预算和权限；
- RUN：五 Agent Trace 与 C0/C1/C2 对照；
- PROVE：使用真实证据替换第 11 页状态；
- 最终输出可部署、可评测、可审计、可回滚，或有证据地保留人工/拒绝自动化。

## 事实边界

- 官网案例是参考场景；
- 软件研发拆解是设计模拟；
- 本地 `demo/` 和历史 AgentTeams smoke test不是 AgentFit 运行证据；
- 不展示未经真实运行验证的成功率、成本、时延、候选排名或 Meta-learning 成果。
