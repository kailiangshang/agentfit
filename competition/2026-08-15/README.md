# AgentFit 初赛提交工作区

> 内部冻结日：2026-08-15
>
> 官方提交截止：2026-08-16
>
> 当前状态：必交材料提交候选已生成；PPTX 的 17 页结构、内容与几何验证通过，PDF 的 17 页页数与逐页文本验证通过；4 个受 Sample 影响的关键页视觉复核通过；完整 17 页 PPTX/PDF 的逐页视觉复核仍待完成。

本目录是 AgentFit 参加 GOAI「新智基座｜Agent Infra」初赛的唯一提交工作区。总体方法以 [`docs/agentfit-solution.md`](../../docs/agentfit-solution.md) 为事实源，路演以 [`design/presentation-redesign.md`](design/presentation-redesign.md) 为唯一叙事基线。

## 初赛完成定义

必交材料：

1. 500 字以内作品简介；
2. 12 页主路演 + 5 页附录的可编辑 PPTX；
3. 与 PPTX 同版的 17 页 PDF；
4. Agent Identity、Skill、Human/风险、开放与合规披露；
5. PPTX 的 17 页结构、内容与几何验证通过，PDF 的 17 页页数与逐页文本验证通过；全部 17 页 PPTX/PDF 完成逐页视觉复核；事实与隐私红线全部通过。

真实 AgentFit 运行证据不是冻结初赛方案的前置条件。若截止前仍未形成可复现闭环，第 11 页必须如实保留“真实运行证据仍待补”；初赛可选代码包不提交。

## 关键文件

| 文件 | 作用 | 当前事实 |
|---|---|---|
| [`submission/work-introduction-draft.md`](submission/work-introduction-draft.md) | 500 字以内作品简介 | 实测 488 个非空白字符，符合不超过 500 的门禁 |
| [`submission/ppt-outline.md`](submission/ppt-outline.md) | 17 页内容地图与生成入口 | 与冻结设计一致 |
| [`submission/slides/`](submission/slides/) | 1280×720 HTML/CSS 布局事实源 | 12 页主路演 + 5 页附录 |
| [`submission/agentfit-preliminary-draft.pptx`](submission/agentfit-preliminary-draft.pptx) | 原生可编辑演示稿 | 17 页提交候选 |
| [`submission/agentfit-preliminary-draft.pdf`](submission/agentfit-preliminary-draft.pdf) | 同版审阅/上传文件 | 17 页提交候选 |
| [`submission/agent-identity.md`](submission/agent-identity.md) | 五个 Agent 的 8 字段契约 | 设计契约，未实例化 |
| [`submission/skill-catalog.md`](submission/skill-catalog.md) | 七个 Skill 的 10 字段契约 | 设计契约，未绑定 |
| [`submission/risk-and-human-gates.md`](submission/risk-and-human-gates.md) | Human 门禁、风险、异常、回滚 | 设计契约 |
| [`submission/openness-and-compliance.md`](submission/openness-and-compliance.md) | 开放、依赖、许可与未实现披露 | 初赛披露 `READY`;真实开放未发生 |
| [`research/official-case-simulation.md`](research/official-case-simulation.md) | 官网四案例与软件研发设计模拟 | 非运行证据 |
| [`planning/readiness-board.md`](planning/readiness-board.md) | 当前证据状态与提交门禁 | 唯一状态看板 |

## 事实优先级

材料冲突时依次使用：官方手册与通知 → 可复现运行证据 → 总体方案 → 比赛要求矩阵与红线 → 冻结路演设计 → 提交材料。聊天、概念图、设计模拟和历史 smoke test 不能单独证明 AgentFit 已完成运行。

## 当前非目标

- 不开发独立 AgentFit UI；第一阶段不接入飞书；
- 不修改 AgentTeams 核心；
- 首个 walking skeleton 阶段不实现自动 NAS、全量候选搜索或跨项目 Meta-learning；
- 不虚构 ProjectCase、运行 Trace、量化效果或开源状态。
