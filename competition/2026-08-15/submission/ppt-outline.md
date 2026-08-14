# AgentFit 最终初赛路演稿说明

> 状态：`READY`。唯一提交版本，17 页 HTML-first（12 页主路演 + 5 页附录）。

## 唯一产品定义

> AgentFit 是面向 AgentTeams 构建的 Agent 方案建筑师：企业提供材料、代表性案例和优先级；它从简单方案开始，依据案例证据调整完整方案，用新案例验证，并交付最小充分的已验证方案包，也允许保留人工或拒绝自动化。

叙事原则：前 4 页不谈 ML/NAS；OpsPilot 只作官方案例锚点，不作 AgentFit 运行证据；第 5–6 页说明完整方案空间、五阶段闭环和最简合格者；第 7 页区分元 Agent 与业务执行 Agent；A1 仅以高层工程类比解释严格候选表示，不把 ML、训练或自动优化作为产品或当前能力。

## 十二页主路演

| 页 | 结论式标题 | 回答的问题 |
|---:|---|---|
| 1 | 企业真正缺少的，是选对 Agent 方案。 | AgentFit 的通用产品价值 |
| 2 | OpsPilot 官方示例：4 个 Worker 加 1 个 Leader，仍未回答该用哪种。 | baseline 为什么是输入而非运行证据 |
| 3 | AgentFit 把业务材料、案例与优先级编译成方案约束。 | 材料如何变成可验收档案 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 | 一个样本长什么样 |
| 5 | Tool、Skill、MCP、Memory、模型、Agent 拓扑与 Human 边界组成完整方案空间。 | 为什么 Agent 数量只是变量之一 |
| 6 | 定义案例与验收→构建最小候选→运行测量→分析调整→验证停止。 | 如何由简入繁并以新案例停止 |
| 7 | 五个元 Agent 完成方案闭环，区别于候选业务执行 Agent。 | 两层 Agent 如何区分 |
| 8 | AgentTeams 承载 Worker、Team、Room、Human；AgentFit 落地 Dossier 与 Trace。 | 平台底座与方案工程层如何分工 |
| 9 | Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 | 工程如何支撑 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 | 最终交付什么 |
| 11 | 证据账本：OpsPilot 为官方锚点，retail/airline 仅探索性 Demo。 | 当前进展边界 |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 | 如何从案例回到通用价值 |

## 五页附录

| 页 | 内容 | 阅读重点 |
|---:|---|---|
| A1 | 候选四元组 `(G, Π, θ, ρ)`、DAG 主干、局部 SCC 与高层工程类比 | 严格内部表示，不是训练系统 |
| A2 | 五个 Agent Identity 契约 | 身份、责任与 Trace |
| A3 | 七个 Skill、HTTP/MCP 等价工具、共享状态与 Trace | Skill、工具与上下文 |
| A4 | Human 门禁、风险、异常与回滚 | 安全、审批、降级与审计 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界 | 开放、合规与事实披露 |

## 事实边界

- OpsPilot Zero 是官方案例锚点，作材料与设计参考，非 AgentFit 运行证据。
- retail/airline overnight 记录使用 DeepSeek、OpenCode、本地路径、自建工具和代理评估器；它们仅为探索性 Demo，不能作为官方 evaluator、正式 Candidate 或官方成绩。
- ProjectCase、真实五元团队、统一候选对照、真实 Episode/Trace 尚未完成；正式 AgentFit runtime 为 `NOT_STARTED`。
- ML 只作 A1 的高层工程类比；本轮不主张训练、反向传播、自动优化或 Meta-learning。

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
