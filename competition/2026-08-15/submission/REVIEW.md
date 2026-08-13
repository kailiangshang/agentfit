# AgentFit 最终提交验证记录

## 材料定义

本目录只保留一套初赛材料：17 页原生可编辑 PPTX、同版 PDF、500 字以内简介、四份详细设计合同、HTML 源稿和自动验证工具。历史版本和过程文档只通过 Git 追溯。

## 事实边界

- OpsPilot baseline 已完成代码级只读审计，作为首个 ProjectCase 参考。
- 两个事故是 TaskSample 设计样本；没有被写成 AgentFit 运行结果。
- AgentFit 的真实 ProjectCase、五元团队和统一候选比较尚未运行。
- 当前选择结论是 `requires_runtime_trial`，不声明候选赢家、ROI、生产收益或 Meta-learning。

## 最终验证门禁

2026-08-13 从最终 HTML 源重新生成后，结果如下：

| 门禁 | 预期 |
|---|---|
| 契约测试 | 41 项全部通过 |
| PPTX/PDF | 各 17 页 |
| 原生可编辑性 | 通过；无图片替代、嵌入媒体和转场 |
| 逐页语义 | 通过；HTML/PPTX/PDF 标题与关键术语一致 |
| 几何 | overlap / overflow / off-slide 为 0；仅保留不影响阅读的网格对齐建议 |
| 作品简介 | 476 个非空白字符 |
| 视觉复核 | 整体联系表及关键变更页独立复核通过；第 2、7、17 页断字已修复并加入 PDF 回归，第 8、11、12 页归属与阶段边界已复核 |

## 复现命令

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

## 作者与审核

方案叙事的一轮收敛曾使用 OpenCode `zhipuai-coding-plan/glm-5.2` 辅助；最终内容选择、事实边界、生成物验证和发布由 Codex 独立检查。工具输出不是权威证据，仓库合同与可复现结果才是提交依据。
