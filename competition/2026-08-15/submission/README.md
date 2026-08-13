# AgentFit 最终初赛提交

> 状态：`READY`。本目录是 2026-08-15 初赛材料的唯一提交版本；历史候选只通过 Git 追溯。

## 提交主线

AgentFit 是运行在 AgentTeams 上的通用 Agent 方案建筑师。它把业务材料编译成 ProjectCase 与 TaskSample，在同一冻结样本、预算、权限和门禁下比较 Agentless、单 Agent、多 Agent及 Human 混合候选，交付最小充分、可验收、可审计的方案，也允许有证据地保留人工或拒绝自动化。

OpsPilot 官方 baseline 是首个 ProjectCase 的代码级审计参考，不是 AgentFit 运行证据。当前真实 ProjectCase、五元 Agent 团队和统一候选对照仍未运行，结论保持 `requires_runtime_trial`。

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
| 3 | AgentFit 把 baseline 材料编译成首个 ProjectCase。 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 |
| 5 | Agentless、单 Agent、多 Agent 与 Human 混合是同一搜索空间。 |
| 6 | 同一冻结样本、预算与门禁下，最简合格候选胜出。 |
| 7 | 五个元 Agent 完成方案闭环，区别于候选业务执行 Agent。 |
| 8 | AgentTeams 承载 Worker、Team、Room、Human；AgentFit 落地 Dossier 与 Trace。 |
| 9 | Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 |
| 11 | 证据账本：baseline 已代码级审计，候选对照仍待运行。 |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 |
| A1 | 七层 ML 映射、候选四元组与内外循环。 |
| A2 | 五个 Agent Identity：判断权、状态边界与责任产物。 |
| A3 | 七个 Skill、HTTP/MCP 等价工具、共享状态与 Trace。 |
| A4 | Human 门禁、风险、异常与回滚。 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界。 |

## 事实边界

- 五个元 Agent 负责设计、评测和审计方案；候选 C2 内的 Agent 才是业务执行 Agent。
- 两个事故用于定义 TaskSample 的设计契约，不是 AgentFit 运行结果。
- AgentTeams 历史 smoke test 只证明底座能力，不等于 AgentFit 已集成。
- 不声称已有候选分数、赢家、ROI、生产收益或 Meta-learning 证据。
- 生成、验证和最终证据见 [ppt-outline.md](ppt-outline.md) 与 [REVIEW.md](REVIEW.md)。
