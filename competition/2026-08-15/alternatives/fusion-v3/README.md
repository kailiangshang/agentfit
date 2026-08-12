# AgentFit 融合版（fusion-v3）

> 与冻结版 `submission/`、评分主线版 `scoreline-v2/` 并排的第三套替代路演候选。**不修改** `submission/`、`scoreline-v2/`、`docs/agentfit-solution.md` 或任何 canonical 设计文件；全部产物仅在本目录。

## 这是什么

一套独立的“融合版”初赛材料，把另外两版的优点合并进一条主线：

- **冻结版**（`submission/`）：以“量体裁衣 / Agent 建筑师 / Architecture Search / 七层 ML 映射”为骨架，产品与方法深度强。
- **评分主线版**（`scoreline-v2/`）：以一家公司面对的具体方案选择难题为主线，把官方 OpsPilot baseline 作首个 ProjectCase 与证据锚点，评分主线清晰。
- **本版（fusion-v3）**：以**通用 Agent 方案建筑师**为定位封面，再用 OpsPilot 与两个事故把抽象方法具体化，随后回到统一搜索空间与最简合格者，最后从 Ops 案例提升回通用价值；附录恢复七层 ML 语义、候选四元组与内外循环，并明确 Meta-learning 未来边界。

三者共享同一套产品定义、视觉令牌和事实边界；差异在叙事顺序、视觉重心与方法论深度。

## 目录内容

| 文件 | 作用 |
|---|---|
| `slides/common.css` | 共享视觉令牌（午夜蓝 / 骨白 / 青绿 / 珊瑚 / 琥珀）与组件类 |
| `slides/01-…17-*.html` | 17 页 HTML-first 布局事实源（12 主 + 5 附录） |
| `build_presentation.py` | 用 hands-on-deck 把 HTML 编译为原生可编辑 PPTX |
| `validate_presentation.py` | 校验 17 页、逐页标题/术语、前 4 页 ML/NAS 禁用、原生形状、PDF 逐页文本 |
| `test_fusion_contract.py` | 契约测试（TDD：先 RED 后 GREEN） |
| `work-introduction.md` | ≤500 非空白字符的简介 |
| `ppt-outline.md` | 路演稿说明与生成命令 |
| `agentfit-fusion-v3.pptx` / `.pdf` | 实际交付物 |

## 融合叙事（12 主 + 5 附录）

| 页 | 结论式标题 |
|---:|---|
| 1 | 企业真正缺少的，是选对 Agent 方案。 |
| 2 | OpsPilot 官方示例：4 个 Worker 加 1 个 Leader，仍未回答该用哪种。 |
| 3 | AgentFit 把 baseline 材料编译成首个 ProjectCase。 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 |
| 5 | Agentless、单 Agent、多 Agent 与 Human 混合是同一搜索空间。 |
| 6 | 同一冻结样本、预算与门禁下，最简合格候选胜出。 |
| 7 | 五个元 Agent 完成方案闭环，区别于候选业务执行 Agent。 |
| 8 | AgentTeams 提供 Worker、Team、Room、Human、Dossier 与 Trace。 |
| 9 | Skill、HTTP/MCP 契约、共享状态与风险门禁支撑闭环。 |
| 10 | 交付 AgentSolutionPackage 与五种合法结果。 |
| 11 | 证据账本：baseline 已代码级审计，候选对照仍待运行。 |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 |
| A1 | 七层 ML 映射、候选四元组与内外循环。 |
| A2 | 五个 Agent Identity：判断权、状态边界与责任产物。 |
| A3 | 七个 Skill、HTTP/MCP 等价工具与上下文 4 选 2。 |
| A4 | Human 门禁、风险、异常与回滚。 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界。 |

## 关键产品边界

- AgentFit **不是** OpsPilot，**不是**运维产品；它是运行在 AgentTeams 上的通用 Agent 方案建筑师。
- OpsPilot 是官方发布的可运行 baseline，作为首个 ProjectCase 与证据锚点。
- **两层 Agent 必须区分**：五个是**元 Agent**（设计 / 评测 / 审计 AgentFit 方案）；OpsPilot 式的执行 Agent 属于候选 C2 内部的**业务执行 Agent**。
- 不能声称 AgentFit 已跑通；不捏造候选分数、运行 Trace、ROI 或赢家。
- 纸面 / 设计 Trace 一律标“设计契约，非运行证据”；本轮结论 `requires_runtime_trial`。

## 生成与验证

见 `ppt-outline.md` 的“可复现生成”。预期：17 页、内容校验 PASS、前 4 页无 ML/NAS 术语、PPTX/PDF 逐页标题一致。

## 测试摘要

详见 `REVIEW.md`：初始 16 项契约测试从 RED（实现缺失）转为 GREEN；独立 PDF 视觉复核后又增加 1 项短标签防拆行回归测试，最终共 17 项。
