# AgentFit 最终提交验证记录

## 材料定义

本目录只保留一套初赛材料：17 页原生可编辑 PPTX、同版 PDF、500 字以内简介、四份详细设计合同、HTML 源稿和自动验证工具。历史版本和过程文档只通过 Git 追溯。

## 事实边界

- OpsPilot baseline 已完成代码级只读审计，作为首个 ProjectCase 参考。
- 两个事故是 TaskSample 设计样本；没有被写成 AgentFit 运行结果。
- 五元团队已在 AgentTeams 官方镜像实例化并完成三轮 ProjectCase preparation（R3：106 事件、治理审查 SUCCESS 有条件）；统一候选比较尚未运行。
- 当前选择结论是 `requires_runtime_trial`，不声明候选赢家、ROI、生产收益或 Meta-learning。

## 最终验证门禁

2026-08-15 主叙事换轴（四层资产纪律 + 持续学习）后重新生成，结果如下：

| 门禁 | 预期 |
|---|---|
| 契约测试 | 56 项全部通过 |
| PPTX/PDF | 各 17 页 |
| 原生可编辑性 | 通过；无图片替代、嵌入媒体和转场 |
| 逐页语义 | 通过；HTML/PPTX/PDF 标题与关键术语一致 |
| 几何 | overlap / overflow / off-slide 为 0；27 个形状仅有 32 条不影响阅读的 `misaligned` 网格建议 |
| 作品简介 | 换轴后实测不超过 500 个非空白字符 |
| 视觉复核 | 17 页联系表整体复核通过；本轮重构的第 5、6、7、10 页已逐页复核 PPTX 转换结果与 PDF，关键短语断行检查已加入回归 |

## 复现命令

```bash
SUB=competition/2026-08-15/submission

# 依赖(任意机器, uv + 国内镜像示例):
#   uv venv .venv && uv pip install --python .venv/bin/python \
#     --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
#     python-pptx pypdf pymupdf reportlab pillow
PY=.venv/bin/python

"$PY" "$SUB/build_presentation.py"          # 无 hands-on-deck 时自动回退 compile_presentation
"$PY" "$SUB/build_pdf.py"                   # Edge/Chrome 截图视觉层 + PPTX 文本层 + contact-sheet
"$PY" "$SUB/validate_presentation.py" "$SUB/agentfit-submission.pptx" "$SUB/agentfit-submission.pdf"
"$PY" -m unittest "$SUB/test_submission_contract.py"
```

## 作者与审核

方案叙事的一轮收敛曾使用 OpenCode `zhipuai-coding-plan/glm-5.2` 辅助；最终内容选择、事实边界、生成物验证和发布由 Codex 独立检查。工具输出不是权威证据，仓库合同与可复现结果才是提交依据。
