# AgentFit 最终初赛路演稿说明

> 状态：`READY`。唯一提交版本，17 页 HTML-first（12 页主路演 + 5 页附录）。

## 唯一产品定义

> AgentFit 是面向 AgentTeams 构建的 Agent 方案建筑师：企业提供材料、代表性案例和优先级；它从简单方案开始，依据案例证据调整完整方案，用新案例验证，并交付最小充分的已验证方案包，也允许保留人工或拒绝自动化。

叙事原则：前 4 页坚持业务问题、官方案例、材料编译和样本定义，不谈 ML/NAS；第 5–7 页用“样本构建、批量试验、误差分析和验证停止”的机器学习工程纪律解释完整方案空间、五阶段闭环和责任流水线，并硬映射化——方案空间按四层资产（原子接口/工具封装/可复用知识/DAG 组合）离散治理，误差按层归因、更新按层白名单，场景演化以持续学习语义治理（回归池防遗忘、漂移探针防漂移）；A1 再给出严格候选表示、七层映射、实体污染纪律与复用率推演。该类比不是产品名称，也不声称训练系统、AutoML 或对黑盒节点的可微优化，自动优化器是可插拔工具而非当前能力。OpsPilot 只作官方案例锚点，不作 AgentFit 运行证据。

## 十二页主路演

| 页 | 结论式标题 | 回答的问题 |
|---:|---|---|
| 1 | 企业真正缺少的，是选对 Agent 方案。 | AgentFit 的通用产品价值 |
| 2 | OpsPilot 官方示例：4 个 Worker 加 1 个 Leader，仍未回答该用哪种。 | baseline 为什么是输入而非运行证据 |
| 3 | AgentFit 把业务材料、案例与优先级编译成方案约束。 | 材料如何变成可验收档案 |
| 4 | 两个事故变成 TaskSample：输入、输出与验收。 | 一个样本长什么样 |
| 5 | 方案空间按四层资产组织，调整逐层受控。 | 七个维度各归其层（L1 接口/L2 封装/L3 知识/L4 流程），触达纪律代码强制 |
| 6 | 样本驱动的持续学习：离散信用分配，回归防遗忘。 | 样本分类→层内更新→回归验证→资产沉淀→漂移触发；五阶段闭环降为单轮骨架 |
| 7 | 五个元 Agent 组成 AgentFit Learning Loop，分别负责目标、样本、方案、实验与诊断。 | 五个责任环节如何协作并区别于业务执行 Agent |
| 8 | AgentTeams 承载 Worker、Team、Room、Human；AgentFit 落地 Dossier 与 Trace。 | 平台底座与方案工程层如何分工 |
| 9 | 追溯四件套：实体分组、hash 链账本、检查器族、泳道报告。 | 可机器审计的追溯底座；指标由检查器计算不采信自述 |
| 10 | 交付的不是一张架构图，而是可复现的 AgentSolutionPackage。 | 方案、样本、实验史、证据和边界如何共同交付 |
| 11 | 证据账本：OpsPilot 为官方锚点，retail/airline 仅探索性 Demo。 | 当前进展边界：三轮 preparation 实测（R3：106 事件、治理 SUCCESS 有条件） |
| 12 | 从 OpsPilot 回到通用：Fit 是有证据选对方案。 | 如何从案例回到通用价值 |

## 五页附录

| 页 | 内容 | 阅读重点 |
|---:|---|---|
| A1 | 七层 ML 映射升级为硬映射：持续学习视角、候选四元组与对照即回归 | 每个映射绑定机器可查对象；优化器是工具不是产品 |
| A2 | 五个 Agent Identity 契约 | 身份、责任与 Trace |
| A3 | 七个 Skill、Tool 与 MCP/HTTP 契约、Memory 与 Trace。 | Skill、工具、接口与上下文 |
| A4 | Human 门禁、风险、异常与回滚 | 安全、审批、降级与审计 |
| A5 | 开放、依赖、许可证、baseline 引用与未实现边界 | 开放、合规与事实披露 |

## 事实边界

- OpsPilot Zero 是官方案例锚点，作材料与设计参考，非 AgentFit 运行证据。
- retail/airline overnight 记录使用 DeepSeek、OpenCode、本地路径、自建工具和代理评估器；它们仅为探索性 Demo，不能作为官方 evaluator、正式 Candidate 或官方成绩。
- 五元团队已在 AgentTeams 官方镜像实例化（Team `Active`），完成三轮 ProjectCase preparation（R3：106 事件、治理审查 SUCCESS 有条件、未分配角色零活动）；ProjectCase 冻结、统一候选对照与真实 Episode/Trace 尚未完成，runtime 为 `IN_PROGRESS`。
- 机器学习工程纪律是第 5–7 页的解释桥梁，A1 承载严格技术映射与层级硬映射；本轮不主张训练、自动优化或跨场景 Meta-learning，场景内持续学习为设计契约（M2 起代码化）。

## 可复现生成

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

完成门禁：PPTX/PDF 各 17 页；结构、逐页内容、原生可编辑性、PDF 语义和几何检查通过；简介不超过 500 个非空白字符；联系表完成整体视觉复核。
