# AgentFit 评分主线版（scoreline-v2）路演稿说明

> 状态：与冻结版并排的替代提交候选，17 页 HTML-first（12 页主路演 + 5 页附录）。
>
> 目录：`competition/2026-08-15/alternatives/scoreline-v2/`。不修改 `submission/`、`docs/` 或 canonical 设计文件。

## 与当前冻结版的核心差异

- 主线是一条具体的方案选择难题：一家公司要在故障自愈里选 Agent 方案。
- 官方 OpsPilot baseline 作为**首个 ProjectCase 与证据锚点**进入叙事，明确标注“非运行证据”。
- 用 baseline 的两个事故 `db_pool_exhausted`、`slow_sql_degradation` 解释 `TaskSample`、输入输出与验收。
- **前 4 页不用 ML/NAS 术语**（无 Architecture Search / NAS / Meta-learning / 七层 / SVD）；公式与七层映射压在附录 A1。
- 评分主线靠“具体案例 + 证据契约”推进，不靠 ML 术语。

## 唯一产品定义

> AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师：给业务任务量体裁衣，交付最小充分、可验收的方案，也允许有证据地保留人工或拒绝自动化。

## 十二页主路演

| 页 | 结论式标题 | 回答的问题 |
|---:|---|---|
| 1 | 选对 Agent 方案，不该靠猜。 | AgentFit 的产品价值 |
| 2 | OpsPilot 官方 baseline 是首个 ProjectCase 参考。 | baseline 为什么是输入而非运行证据 |
| 3 | AgentFit 把业务难题编译成 ProjectCase。 | 材料如何变成可验收档案 |
| 4 | 一次事故定义 TaskSample、输入输出与验收。 | 一个样本长什么样 |
| 5 | 五元元团队完成方案设计闭环。 | 元团队设计而非业务执行 |
| 6 | C0 / C1 / C2 / C3 是同一搜索空间的候选。 | Agent 数量为何是变量 |
| 7 | 五元团队映射到 AgentTeams 的 Worker / Team / Room / Human。 | 平台底座如何落地 |
| 8 | 公平试验、Episode、Trace 与证据契约尚待真实运行。 | 为何不能编造分数 |
| 9 | 七个 Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 | 工程如何支撑 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 | 企业拿到什么 |
| 11 | 证据账本：baseline 已代码级审计，候选对照仍待运行。 | 当前进展边界 |
| 12 | Fit：不是更多 Agent，而是有证据选对方案。 | 收束 |

## 五页附录

| 页 | 内容 | 覆盖要求 |
|---:|---|---|
| A1 | 极简候选表示 `(G, Π, θ, ρ)`、搜索规则、七层 ML 映射 | 让 ML/NAS 不抢主线 |
| A2 | 五个 Agent Identity 与 8 字段契约 | 不同职能 Agent、身份与 Trace |
| A3 | 七个 Skill、HTTP/MCP 等价工具、上下文 4 选 2 | Skill 必选、工具、上下文 |
| A4 | Human 门禁、风险、异常与回滚 | 安全、审批、降级与审计 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界 | 开放/合规与当前事实 |

## 事实边界

- OpsPilot Zero 是官方示例，作 baseline 与首个 ProjectCase 参考，**非 AgentFit 运行证据**。
- 两个事故是说明 `TaskSample` 的**设计契约，非运行证据**。
- AgentTeams 历史 smoke 只证明平台能力。
- ProjectCase、真实五元团队、统一候选对照、真实 Episode/Trace 尚未完成；不捏造分数或赢家。
- 本轮结论 `requires_runtime_trial`。

## 可复现生成

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
DECK=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py

"$PY" competition/2026-08-15/alternatives/scoreline-v2/build_presentation.py
"$PY" "$DECK" competition/2026-08-15/alternatives/scoreline-v2/agentfit-scoreline-v2.pptx inspect --issues
soffice --headless --convert-to pdf \
  --outdir competition/2026-08-15/alternatives/scoreline-v2 \
  competition/2026-08-15/alternatives/scoreline-v2/agentfit-scoreline-v2.pptx
"$PY" competition/2026-08-15/alternatives/scoreline-v2/validate_presentation.py \
  competition/2026-08-15/alternatives/scoreline-v2/agentfit-scoreline-v2.pptx \
  competition/2026-08-15/alternatives/scoreline-v2/agentfit-scoreline-v2.pdf
"$PY" -m unittest competition/2026-08-15/alternatives/scoreline-v2/test_scoreline_contract.py
```

预期：HTML、PPTX 与 PDF 均为 17 页；内容校验通过；前 4 页无 ML/NAS 术语。
