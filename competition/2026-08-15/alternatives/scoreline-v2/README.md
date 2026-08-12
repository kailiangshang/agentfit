# AgentFit 评分主线版（scoreline-v2）

> 与冻结版 `submission/` 并排的替代路演候选。**不修改** `submission/`、`docs/agentfit-solution.md` 或 canonical 设计文件；全部产物仅在本目录。

## 这是什么

一套独立的“评分主线版”初赛材料，让用户能在两套叙事间并排选择：

- **当前冻结版**（`competition/2026-08-15/submission/`）：以“量体裁衣 / Agent 建筑师 / Architecture Search”为骨架。
- **本版（scoreline-v2）**：以**一家公司面对的具体方案选择难题**为主线，把官方 OpsPilot baseline 作为首个 ProjectCase 与证据锚点，用两个事故解释 TaskSample。

两者共享同一套产品定义、视觉令牌和事实边界；差异在叙事顺序和视觉重心。

## 目录内容

| 文件 | 作用 |
|---|---|
| `slides/common.css` | 共享视觉令牌（午夜蓝 / 骨白 / 青绿 / 珊瑚 / 琥珀）与组件类 |
| `slides/01-…17-*.html` | 17 页 HTML-first 布局事实源（12 主 + 5 附录） |
| `build_presentation.py` | 用 hands-on-deck 把 HTML 编译为原生可编辑 PPTX |
| `validate_presentation.py` | 校验 17 页、逐页标题/术语、前 4 页 ML/NAS 禁用、原生形状、PDF 逐页文本 |
| `test_scoreline_contract.py` | 契约测试（TDD：先 RED 后 GREEN） |
| `work-introduction.md` | ≤500 非空白字符的简介 |
| `ppt-outline.md` | 路演稿说明与生成命令 |
| `agentfit-scoreline-v2.pptx` / `.pdf` | 实际交付物 |

## 关键产品边界

- AgentFit **不是** OpsPilot，**不是**运维产品。
- OpsPilot 是官方发布的可运行 baseline，作为首个 ProjectCase 与证据锚点。
- 五元团队是**设计/评测 Agent 方案的元团队**；C2 候选里才可能出现 OpsPilot 式业务执行 Agent。
- 不能声称 AgentFit 已跑通；不捏造候选分数、运行 Trace、ROI 或赢家。
- 纸面/设计 Trace 一律标“设计契约，非运行证据”。

## 生成与验证

见 `ppt-outline.md` 的“可复现生成”。预期：17 页、内容校验 PASS、前 4 页无 ML/NAS 术语、PPTX/PDF 逐页标题一致。

## 测试摘要

详见 `REVIEW.md`：13 项契约测试从 RED（实现缺失）转为 GREEN（实现就位并通过）。
