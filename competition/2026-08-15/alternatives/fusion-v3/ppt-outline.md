# AgentFit 融合版（fusion-v3）路演稿说明

> 状态：与冻结版、评分主线版并排的第三套替代提交候选，17 页 HTML-first（12 页主路演 + 5 页附录）。
>
> 目录：`competition/2026-08-15/alternatives/fusion-v3/`。不修改 `submission/`、`scoreline-v2/`、`docs/` 或 canonical 设计文件。

## 与另外两版的融合取舍

| 维度 | 冻结版 | 评分主线版 | 融合版（本版） |
|---|---|---|---|
| 封面定位 | 通用方案建筑师 | 一道真实选择题 | **通用方案建筑师 + OpsPilot 作首个案例锚点** |
| 主线 | 方法论与搜索空间 | 具体 Ops 选择难题 | **用 Ops 案例具体化方法，再回到通用搜索空间** |
| OpsPilot 处理 | 仅作参考广度 | 首个 ProjectCase 与证据锚点 | **首个 ProjectCase 锚点 + 明确“非运行证据”** |
| 搜索空间 / 最简合格者 | 主线早期 | 压在附录 | **回到主线第 5–6 页** |
| ML / 七层映射 / 内外循环 | 附录完整呈现 | 压缩并明确不让其抢主线 | **附录 A1 完整恢复 + 明确 Meta-learning 未来边界** |
| 元 Agent vs 业务 Agent | 隐含 | 有区分但易混 | **第 7 页显式分两层并复述** |

融合原则：**前 4 页不谈 ML/NAS**；ML 语义完整保留在附录 A1；OpsPilot 只作首个 ProjectCase 输入，不作运行证据；从 Ops 案例在第 12 页提升回通用价值。

## 唯一产品定义

> AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师：给业务任务量体裁衣，交付最小充分、可验收的方案，也允许有证据地保留人工或拒绝自动化。

## 十二页主路演

| 页 | 结论式标题 | 回答的问题 |
|---:|---|---|
| 1 | 企业真正缺少的，是选对 Agent 方案。 | AgentFit 的通用产品价值 |
| 2 | OpsPilot 官方示例：4 个 Worker 加 1 个 Leader，仍未回答该用哪种。 | baseline 为什么是输入而非运行证据 |
| 3 | AgentFit 把 baseline 材料编译成首个 ProjectCase。 | 材料如何变成可验收档案 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 | 一个样本长什么样 |
| 5 | Agentless、单 Agent、多 Agent 与 Human 混合是同一搜索空间。 | Agent 数量为何是变量 |
| 6 | 同一冻结样本、预算与门禁下，最简合格候选胜出。 | 公平比较规则 + 候选复杂度对照示意（C0–C3，非真实数据） |
| 7 | 五个元 Agent 完成方案闭环，区别于候选业务执行 Agent。 | 元团队与业务执行的两层区分 |
| 8 | AgentTeams 提供 Worker、Team、Room、Human、Dossier 与 Trace。 | 平台底座如何落地 |
| 9 | Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 | 工程如何支撑 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 | 企业拿到什么 |
| 11 | 证据账本：baseline 已代码级审计，候选对照仍待运行。 | 当前进展边界 |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 | 从案例回到通用价值 |

## 五页附录

| 页 | 内容 | 覆盖要求 |
|---:|---|---|
| A1 | 七层 ML 映射、候选四元组 `(G, Π, θ, ρ)`、G 结构图（DAG 主干 + 局部 SCC + Π 分区）、inner / outer loop、Meta-learning 未来边界 | 完整恢复 ML 语义 + 候选图可视化 + 明确未来边界 |
| A2 | 五个 Agent Identity 与 8 字段契约 | 元 Agent 身份与 Trace |
| A3 | 七个 Skill、HTTP/MCP 等价工具、上下文 4 选 2 | Skill 必选、工具、上下文 |
| A4 | Human 门禁、风险、异常与回滚 | 安全、审批、降级与审计 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界 | 开放 / 合规与当前事实 |

## 事实边界

- OpsPilot Zero 是官方示例，作 baseline 与首个 ProjectCase 参考，**非 AgentFit 运行证据**。
- 两个事故是说明 `TaskSample` 的**设计契约，非运行证据**。
- AgentTeams 历史 smoke 只证明平台能力。
- ProjectCase、真实五元团队、统一候选对照、真实 Episode/Trace 尚未完成；不捏造分数或赢家。
- 跨项目 Meta-learning 是未来方向，当前未实现。
- 本轮结论 `requires_runtime_trial`。

## 可复现生成

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
DECK=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py

"$PY" competition/2026-08-15/alternatives/fusion-v3/build_presentation.py
"$PY" "$DECK" competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pptx inspect --issues
soffice --headless --convert-to pdf \
  --outdir competition/2026-08-15/alternatives/fusion-v3 \
  competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pptx
"$PY" competition/2026-08-15/alternatives/fusion-v3/validate_presentation.py \
  competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pptx \
  competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pdf
"$PY" -m unittest competition/2026-08-15/alternatives/fusion-v3/test_fusion_contract.py
```

预期：HTML、PPTX 与 PDF 均为 17 页；内容校验通过；前 4 页无 ML/NAS 术语。
