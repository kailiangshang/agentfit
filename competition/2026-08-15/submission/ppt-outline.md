# AgentFit 初赛路演稿说明

> 状态:12 页 HTML-first 内部草案;核心概念为 **Fit(量体裁衣)** + **建筑师**;第 11 页进展状态必须在真实运行后更新。

## 核心概念(Fit + 建筑师)

本稿不是技术方案说明书,而是一个让评委记住的路演。核心主张贯穿全稿:

> **企业缺的不是更多 Agent,缺的是"刚好够用"的那一个。AgentFit 给 Agent 量体裁衣。**

辅助类比:AgentFit 是 **Agent 的建筑师**——不砌砖(不造 Agent),画图纸 + 验房(决定该不该造、造几个、验收合格)。实现术语(TaskSemanticSpec、CandidateGraph 等)下沉到备注和附件,不上 PPT 正文。

## 可审阅与可复现文件

- [可编辑 PPTX](agentfit-preliminary-draft.pptx)
- [同版 PDF](agentfit-preliminary-draft.pdf)
- [HTML 幻灯片源稿](slides/)
- [确定性生成器](build_presentation.py)
- [内容与页数校验器](validate_presentation.py)

HTML/CSS 是布局事实源,由浏览器完成 1280×720 排版,再通过 `html2patch` 编译为 PowerPoint 原生可编辑文本、容器和线条。PPTX 不是整页截图;只有未来无法稳定转译的复杂纹理或插画才允许作为图片嵌入。

重新生成并校验(路径为服务器环境,本地 macOS 无法执行):

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

### 第 1 页:封面 — 企业缺的不是更多 Agent,是"刚好够用"的那一个

- Fit 概念登场,反共识钩子;
- 右侧"太多/太少/FIT"视觉隐喻,呼应减法哲学;
- 底部故事主线:材料 → 可验收任务 → 四套方案赛跑 → 人工门禁 → 刚好够用的方案。

### 第 2 页:痛点故事 — 一条用户反馈,背后是四种解法

- 保留"预测结果明显不对"的用户反馈故事;
- 收尾金句:"创建 Agent 只会把不确定性藏进 Prompt";
- 过渡句引向第 3 页:"这就是为什么我们需要先量体,再裁衣。"

### 第 3 页:Missing Layer — 平台和框架之间,缺一个"建筑师"

- HEAVY(重量级平台)vs LIGHT(轻量级框架)对照;
- 中间圆筒:"Agent 的建筑师"——量体、画图、验房;
- 底部硬核主张:"AgentFit 是决策层,不是另一个运行时"。

### 第 4 页:Fit 三步 — 量体 → 裁衣 → 试穿

- 01 量体:把业务说清楚(输入/输出/红线/责任)→ 任务说明书;
- 02 裁衣:盘点可用能力(人/工具/模型/技能/记忆/规则)→ 能力清单 + 缺口报告;
- 03 试穿:无 Agent / 单 Agent / 多 Agent / 人工混合 四套方案赛跑 → 最简单合格方案 + 执行轨迹;
- 底部 pill:"或一份有证据的结论:建议保留人工 / 拒绝自动化"。

### 第 5 页:场景广度 — 四个行业,同一个任务骨架

- 官网四案例并列(零人工运维 / 智能客服 / 软件研发 / 金融风控);
- 五列用具体业务动作(输入/定位/处置/验证/沉淀),不用抽象流程词;
- 来源标注 GOAI 官网 URL 与 2026-08-10 核验日期。

### 第 6 页:反共识洞察 — 先拆任务,不先拆 Agent

- 对照"常见错误路径"(先定 5 个 Agent 再找事做)vs "AgentFit 路径"(先问验收线);
- 金句:"把不确定性藏进了 Agent 之间的通信里";
- 底部:四个案例共享任务骨架,但不共享 Agent 数量。

### 第 7 页:Fit 宣言 — 四条赛道赛跑,最简单的合格者赢

- 赛道 1 无 Agent 基线 / 赛道 2 单 Agent / 赛道 3 多 Agent + 右侧人工门禁;
- 底部宣言:"每多一个 Agent,都必须证明:它带来的收益,大于它增加的通信、状态和审计成本";
- 全稿最有记忆点的一页,删除所有代码符号。

### 第 8 页:元团队 — 五个元 Agent 是一条责任链,不是五张角色卡

- 五个元 Agent(中文名):交付官 / 业务架构师 / 方案架构师 / 验证工程师 / 审计官;
- 产物名全部中文化:项目简报 / 任务说明书 / 候选方案集 / 执行轨迹 / 决策账本;
- 底部责任契约:"同一份项目档案 · 每次交接有产物 · 每次决策有轨迹 · 高风险动作必须有人批"。

### 第 9 页:系统边界 — AgentTeams 让团队跑起来,AgentFit 帮企业选对方案

- 上层 AgentFit 决策层(任务说明/候选方案/执行轨迹/交付方案包);
- 中间项目档案(版本化状态·产物·执行轨迹·决策账本);
- 下层 AgentTeams 运行底座(身份通信/工具技能/容器权限/共享存储/人工入口);
- 与第 3 页形成"为什么 + 长什么样"的呼应。

### 第 10 页:价值收束 — 交付物是一份能验收的方案,不是一段 Prompt

- 四象限:是什么 / 怎么跑 / 凭什么 / 守住线(全部人话化);
- 右侧"企业最终拿到:一份合身的方案,或一份诚实的建议:别自动化";
- 底部:每个方案配一份"架构决策说明"。

### 第 11 页:诚实进度 — 已完成 X,下一步是 Y

- 已完成 ✓:核心主张与方法论 / 官网四案例拆解 / 软件研发设计模拟;
- 下一步 →:首个真实项目案例跑通(五元 Agent + 三赛道对照);
- 右侧三条红线:不把设计说成运行 / 不隐瞒依赖与边界 / 不只展示成功;
- 底部:"没有运行轨迹,不改变项目状态。"

### 第 12 页:收尾 — 初赛交主张,复赛交证据

- 路径:就绪 → 冻结 → 跑通 → 证明;
- 最终主张:可部署 / 可评测 / 可审计 / 可回滚,或有证据地保留人工/拒绝自动化;
- 收尾呼应封面:"Fit —— 刚刚好,不多不少。"

## 文案规则

- 每页标题必须是结论句,不能只是名词标签;
- 每页只解释一个核心因果关系;
- **术语必须配中文人话**(如 TaskSemanticSpec → 任务说明书),内部契约名不上正文;
- **禁止代码符号上 PPT**(如 `selected_candidate = null` 已删除);
- **前 3 页不出现实现术语**(让评委先认同问题);
- 单个说明块不超过 3 行,单页不超过 3 个主要说明块;
- `AgentFit`、`AgentTeams` 和五个元 Agent 中文名保持一致;
- 任何非真实运行内容使用"示意场景""官网参考案例"或"设计模拟"显式标注;
- 真实运行证据使用"证据待补"或"下一步",禁止出现未经验证的量化成绩。

## 事实边界

- 官网案例是参考场景;
- 软件研发拆解是设计模拟;
- 本地 `demo/` 和历史 AgentTeams smoke test 不是 AgentFit 运行证据;
- 不展示未经真实运行验证的成功率、成本、时延、候选排名或跨项目学习成果。

## 术语人话翻译表

| 内部术语 | PPT 人话 |
|---|---|
| TaskSemanticSpec | 任务说明书 |
| CapabilitySemanticSpec / Registry | 能力清单 / 能力库 |
| AlignmentReport | 缺口报告 |
| CandidateGraph / CandidateSet | 候选方案集 |
| TrialSpec | 赛跑规则 / 试验方案 |
| Project Dossier | 项目档案 |
| ExecutionTrace | 执行轨迹 |
| DecisionLedger | 决策账本 |
| EngagementBrief | 项目简报 |
| AgentSolutionPackage | 交付方案包 |
| ArchitectureDecision | 架构决策说明 |
| EngagementLead | 交付官 |
| BusinessEngineer | 业务架构师 |
| AgentArchitect | 方案架构师 |
| ValidationEngineer | 验证工程师 |
| GovernanceAuditor | 审计官 |
| C0 / C1 / C2 / H | 无 Agent / 单 Agent / 多 Agent / 人工 |
| HUMAN GATE | 人工门禁 |
