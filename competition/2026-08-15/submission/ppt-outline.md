# AgentFit 最终初赛路演稿说明

> 状态：`READY`。唯一提交版本，17 页 HTML-first（12 页主路演 + 5 页附录）。

## 唯一产品定义

> AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师：给业务任务量体裁衣，交付最小充分、可验收的方案，也允许有证据地保留人工或拒绝自动化。

叙事原则：前 4 页不谈 ML/NAS；OpsPilot 只作首个 ProjectCase 的代码级审计输入，不作 AgentFit 运行证据；第 5–6 页说明统一搜索空间和最简合格者；第 7 页区分元 Agent 与业务执行 Agent；附录 A1 再完整呈现 ML 语义和未来边界。

## 十二页主路演

| 页 | 结论式标题 | 回答的问题 |
|---:|---|---|
| 1 | 企业真正缺少的，是选对 Agent 方案。 | AgentFit 的通用产品价值 |
| 2 | OpsPilot 官方示例：4 个 Worker 加 1 个 Leader，仍未回答该用哪种。 | baseline 为什么是输入而非运行证据 |
| 3 | AgentFit 把 baseline 材料编译成首个 ProjectCase。 | 材料如何变成可验收档案 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 | 一个样本长什么样 |
| 5 | Agentless、单 Agent、多 Agent 与 Human 混合是同一搜索空间。 | Agent 数量为何是变量 |
| 6 | 同一冻结样本、预算与门禁下，最简合格候选胜出。 | 公平比较和由简入繁的搜索顺序 |
| 7 | 五个元 Agent 完成方案闭环，区别于候选业务执行 Agent。 | 两层 Agent 如何区分 |
| 8 | AgentTeams 承载 Worker、Team、Room、Human；AgentFit 落地 Dossier 与 Trace。 | 平台底座与方案工程层如何分工 |
| 9 | Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 | 工程如何支撑 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 | 最终交付什么 |
| 11 | 证据账本：baseline 已代码级审计，候选对照仍待运行。 | 当前进展边界 |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 | 如何从案例回到通用价值 |

## 五页附录

| 页 | 内容 | 阅读重点 |
|---:|---|---|
| A1 | 七层 ML 映射、候选四元组 `(G, Π, θ, ρ)`、DAG 主干、局部 SCC、inner/outer loop | 方法论与未来 Meta-learning 边界 |
| A2 | 五个 Agent Identity 契约 | 身份、责任与 Trace |
| A3 | 七个 Skill、HTTP/MCP 等价工具、共享状态与 Trace | Skill、工具与上下文 |
| A4 | Human 门禁、风险、异常与回滚 | 安全、审批、降级与审计 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界 | 开放、合规与事实披露 |

## 事实边界

- OpsPilot Zero 是官方示例，作首个 ProjectCase 参考，非 AgentFit 运行证据。
- 两个事故是 TaskSample 的设计契约，非运行证据。
- ProjectCase、真实五元团队、统一候选对照、真实 Episode/Trace 尚未完成。
- 跨项目 Meta-learning 当前未实现；本轮结论 `requires_runtime_trial`。

## 可复现生成

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
DECK=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py
THUMB=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/thumbnail.py
SUB=competition/2026-08-15/submission

"$PY" "$SUB/build_presentation.py"
soffice --headless --convert-to pdf --outdir "$SUB" "$SUB/agentfit-submission.pptx"
"$PY" "$THUMB" "$SUB/agentfit-submission.pptx" "$SUB/contact-sheet" --cols 4
"$PY" "$SUB/validate_presentation.py" "$SUB/agentfit-submission.pptx" "$SUB/agentfit-submission.pdf"
"$PY" -m unittest -v "$SUB/test_submission_contract.py"
"$PY" "$DECK" "$SUB/agentfit-submission.pptx" inspect --issues
```

完成门禁：PPTX/PDF 各 17 页；结构、逐页内容、原生可编辑性、PDF 语义和几何检查通过；简介不超过 500 个非空白字符；联系表完成整体视觉复核。
