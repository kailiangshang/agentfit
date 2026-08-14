# AgentFit 最终初赛提交

> 状态：`READY`。本目录是 2026-08-15 初赛材料的唯一提交版本；历史候选只通过 Git 追溯。

## 提交主线

AgentFit 是面向 AgentTeams 构建的 Agent 方案建筑师。企业提供业务材料、代表性案例和用户优先级；它先定义案例与验收，从简单方案开始运行，再依据证据调整完整方案，并以新案例验证后交付最小充分的已验证方案包，也允许保留人工或拒绝自动化。

内部候选严格表示为 `Candidate = (G, Π, θ, ρ)`：能力图、Agent 分区、参数与共享范围。Tool、Skill、MCP、Memory、Model、Agent 拓扑和 Human 边界都是方案变量；这不是以 Agent 数量或 ML 术语命名的产品。

OpsPilot 是官方案例锚点，作为材料和设计参考，不是 AgentFit 运行证据。retail/airline 的 overnight 记录是 DeepSeek + OpenCode、本地路径与自建工具/代理评估器产生的探索性 Demo，非官方 evaluator、非 Candidate、非正式分数。真实 AgentFit 运行保持 `NOT_STARTED`。

阶段边界：2026-08-15 初赛提交阶段只完成本目录材料、验证和上传；是否进入后续 AgentTeams walking skeleton、复赛工程或跨项目试验，由晋级结果、评审反馈、后续赛程和明确授权决定。AgentTeams 承载 Worker、Team、Room、Human；AgentFit 落地 Dossier 与 Trace。

## 最终提交物

| 文件 | 作用 |
|---|---|
| `work-introduction.md` | 500 字以内作品简介 |
| `agentfit-submission.pptx` | 17 页原生可编辑路演稿 |
| `agentfit-submission.pdf` | 与 PPTX 同版的 17 页 PDF |
| `contact-sheet.jpg` | 17 页整体视觉联系表 |
| `ppt-outline.md` | 12 页主路演、5 页附录与复现命令 |
| `agent-identity.md` | 五个元 Agent 的 Identity 契约 |
| `skill-catalog.md` | 七个核心 Skill 的完整字段 |
| `risk-and-human-gates.md` | Human 门禁、风险、异常和回滚 |
| `openness-and-compliance.md` | 开放、依赖、许可与未实现披露 |
| `slides/` | 17 页 HTML/CSS 布局事实源 |
| `build_presentation.py` | 将 HTML 编译为原生 PPTX |
| `validate_presentation.py` | 校验结构、内容、可编辑性和 PDF 逐页语义 |
| `test_submission_contract.py` | 仓库与提交物回归合同 |

## 路演内容

| 页 | 结论式标题 |
|---:|---|
| 1 | 企业真正缺少的，是选对 Agent 方案。 |
| 2 | OpsPilot 官方示例：4 个 Worker 加 1 个 Leader，仍未回答该用哪种。 |
| 3 | AgentFit 把业务材料、案例与优先级编译成方案约束。 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 |
| 5 | Tool、Skill、MCP、Memory、模型、Agent 拓扑与 Human 边界组成完整方案空间。 |
| 6 | 定义案例与验收→构建最小候选→运行测量→分析调整→验证停止。 |
| 7 | 五个元 Agent 完成方案闭环，区别于候选业务执行 Agent。 |
| 8 | AgentTeams 承载 Worker、Team、Room、Human；AgentFit 落地 Dossier 与 Trace。 |
| 9 | Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 |
| 11 | 证据账本：OpsPilot 为官方锚点，retail/airline 仅探索性 Demo。 |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 |
| A1 | 候选四元组 `(G, Π, θ, ρ)`、DAG 主干、局部 SCC 与高层工程类比 |
| A2 | 五个 Agent Identity 契约 |
| A3 | 七个 Skill、HTTP/MCP 等价工具、共享状态与 Trace |
| A4 | Human 门禁、风险、异常与回滚 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界 |

## 事实边界

- 五个元 Agent 分别负责目标/停止控制、业务与样本工程、方案建模、试验执行、错误/治理分析；候选 C2 内的 Agent 才是业务执行 Agent。
- OpsPilot 是官方案例锚点；retail/airline 只是不使用官方 evaluator 的探索性 Demo。
- AgentTeams 历史 smoke test 只证明底座能力，不等于 AgentFit 已集成。
- 不声称已有候选分数、赢家、ROI、生产收益、训练系统或 Meta-learning 证据。
- 生成、验证和最终证据见 [ppt-outline.md](ppt-outline.md) 与 [REVIEW.md](REVIEW.md)。
