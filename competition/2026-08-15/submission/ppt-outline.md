# AgentFit 初赛路演稿说明

> 状态：17 页 HTML-first 提交候选，包含 12 页主路演与 5 页技术/合规附录。
>
> 唯一叙事基线：[`../design/presentation-redesign.md`](../design/presentation-redesign.md)。

## 唯一产品定义

> AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师。它把业务任务和可用能力编译为可搜索的架构空间，通过统一评测找到“刚好够用”的方案，也允许有证据地保留人工或拒绝自动化。

三层关系固定为：

1. **Fit / Agent 建筑师**：产品价值；
2. **样本语义 + 任务语义 + 能力语义 + 受约束的 Agent Architecture Search + 统一评测**：核心技术方法；
3. **Meta-learning**：跨项目验证后的未来方向，不是当前能力。

## 十二页主路演

| 页 | 结论式标题 | 回答的问题 |
|---:|---|---|
| 1 | Agent 架构不该靠猜 | AgentFit 的产品价值是什么 |
| 2 | 企业不知道的，不只是“用几个 Agent” | 为什么创建 Agent 不是第一步 |
| 3 | 平台提供砖块，但企业仍缺一位建筑师 | 市场缺失的方案工程层是什么 |
| 4 | AgentFit 先定义样本，再编译任务和方案 | Sample 编译 → Task 编译 → 能力编译与候选比较 |
| 5 | 无、单、多 Agent 是同一个搜索空间 | 为什么 Agent 数量是变量而非目标 |
| 6 | 最简单的合格者获胜 | 所有候选共享同一冻结 SampleSetManifest、同一版本化 TaskSample、模型与工具边界、预算、指标、安全和 Human 门禁；复杂度作为成本 |
| 7 | 五个元 Agent 把方案选择变成责任闭环 | BusinessEngineer 负责 Sample/Task 契约，ValidationEngineer 负责每个 TaskSample 的 Episode 与 Step Trace；候选冻结后，仅 GovernanceAuditor 消费 sealed-holdout 结果 |
| 8 | AgentTeams 让团队运行，AgentFit 负责选对方案 | 产品层、项目档案和底座如何分工 |
| 9 | 不同行业，共用一种方案决策方法 | 官网参考场景如何共享任务骨架 |
| 10 | 最终交付的不是 Prompt，而是可验收方案包 | 企业最终拿到什么 |
| 11 | 方法已经收敛，真实运行证据仍待补 | 当前进展与证据边界是什么 |
| 12 | Fit：刚刚好，不多不少 | 产品价值、技术方法和未来方向如何收束 |

## 五页附录

| 页 | 内容 | 覆盖要求 |
|---:|---|---|
| A1 | 七层 ML 映射、`(G, Π, θ, ρ)`、内外循环 | 样本、任务、能力、候选与 Meta-learning 边界 |
| A2 | 五个 Agent Identity 与 8 字段契约 | 至少 3 个不同职能 Agent、身份与 Trace |
| A3 | 七个 Skill、Skill/MCP 关系、上下文 4 选 2 | Skill 必选、MCP、共享状态与轨迹可观测 |
| A4 | Human 门禁、风险、异常和回滚 | 高风险动作、安全、审批、降级与审计 |
| A5 | 开放计划、依赖、许可证和未实现范围 | 开放/开源、商业 API、数据与当前事实 |

## 事实边界

- 官网四类案例是参考场景，非 AgentFit 运行证据；
- 软件研发材料是设计模拟，结论为 `requires_runtime_trial`；
- 历史 AgentTeams smoke test 只证明平台能力；
- ProjectCase、真实五元团队、统一候选对照与跨项目 Meta-learning 尚未完成；
- 第 11 页保持“证据待补”，直到可复现运行门禁真正通过。

## 可复现生成

HTML/CSS 是布局事实源，PPTX 使用原生可编辑文本和形状，不以整页截图充当内容。

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
DECK=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py

"$PY" competition/2026-08-15/submission/build_presentation.py
"$PY" "$DECK" competition/2026-08-15/submission/agentfit-preliminary-draft.pptx inspect --issues
soffice --headless --convert-to pdf \
  --outdir competition/2026-08-15/submission \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx
"$PY" competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pdf
```

预期：HTML、PPTX 与 PDF 均为 17 页；几何检查无问题；内容校验通过。
