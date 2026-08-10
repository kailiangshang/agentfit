# AgentFit 初赛准备工作区

> 内部材料冻结日：2026-08-15
>
> 官方初赛提交截止：2026-08-16
>
> 当前状态：准备中，尚未形成可提交终稿

本目录是 AgentFit 为 GOAI「新智基座｜Agent Infra」初赛准备材料的唯一工作区。它负责把总体方案、比赛要求、真实运行证据和最终提交材料连接起来，不取代 [`docs/agentfit-solution.md`](../../docs/agentfit-solution.md)，也不把计划、模拟或平台基础能力写成 AgentFit 已完成能力。

## 1. 8 月 15 日的完成定义

到内部冻结日，应具备：

1. 一份 500 字以内、所有完成态声明都有证据指针的作品简介；
2. 一份内容完整的方案 PPT/PDF，覆盖比赛要求的场景、Agent、协同、Skill、工具、上下文、验证、安全、开放计划与当前进展；
3. 一套在 AgentTeams 上实际运行的 AgentFit 最小闭环证据，至少包含角色配置、任务委派、结构化产物、执行 Trace、失败或降级记录；
4. 一个冻结的首个 ProjectCase，以及 Agentless、单 Agent、多 Agent候选的统一评测设计；
5. Agent Identity、核心 Skill 和 AgentTeams 映射清单；
6. 一份提交前红线、依赖、许可证、数据、模型、既有基础和事实一致性检查结果；
7. 对可选代码包作出明确决定；如提交，必须包含运行入口、依赖、配置、样例输入输出和运行证据。

“基本准备好”不等于完整产品化，也不要求在初赛前完成全部六个 ProjectCase、跨项目 Meta-learning、生产部署、独立前端或飞书集成。

## 2. 目录内容

| 文件 | 作用 | 当前地位 |
|---|---|---|
| [`design/agentteams-landing-design.md`](design/agentteams-landing-design.md) | 记录 AgentFit 如何基于 AgentTeams 落地 | 已批准方向的设计记录，待书面复核 |
| [`design/presentation-redesign.md`](design/presentation-redesign.md) | 路演叙事、视觉令牌与 HTML-first 生产决策 | 已批准并执行 |
| [`planning/readiness-board.md`](planning/readiness-board.md) | 8 月 15 日前的交付顺序、门禁和状态 | 当前执行入口 |
| [`planning/presentation-production-plan.md`](planning/presentation-production-plan.md) | PPTX/PDF 的可复现生成与质量门禁 | HTML-first 版本已执行，后续证据更新继续沿用 |
| [`research/official-case-simulation.md`](research/official-case-simulation.md) | 官网四类案例拆解与软件研发设计模拟 | 已核验，非运行证据 |
| [`submission/work-introduction-draft.md`](submission/work-introduction-draft.md) | 500 字以内作品简介草案 | 内部草案，不可直接提交 |
| [`submission/ppt-outline.md`](submission/ppt-outline.md) | 初赛方案 PPT/PDF 的逐页说明和生成入口 | 与 HTML-first 12 页稿一致 |
| [`submission/slides/`](submission/slides/) | 1280×720 HTML/CSS 幻灯片布局事实源 | 已编译并通过视觉审阅 |
| [`submission/agentfit-preliminary-draft.pptx`](submission/agentfit-preliminary-draft.pptx) | HTML 编译的可编辑初赛演示稿 | 12 页内部草案，结构检查为零问题 |
| [`submission/agentfit-preliminary-draft.pdf`](submission/agentfit-preliminary-draft.pdf) | 与 PPTX 同版的审阅文件 | 内部草案 |

## 3. 事实源优先级

材料发生冲突时按以下顺序处理：

1. 官方参赛手册与赛事最新通知；
2. 可复现的 AgentTeams 运行记录、Trace、评测报告和版本信息；
3. [`docs/agentfit-solution.md`](../../docs/agentfit-solution.md)；
4. [`docs/internal/competition/preliminary-requirements-matrix.md`](../../docs/internal/competition/preliminary-requirements-matrix.md)与[红线检查表](../../docs/internal/competition/preliminary-red-line-checklist.md)；
5. 其他内部证据卡和研究材料；
6. 本目录中的提交草案。

聊天记录、概念图、被忽略的 `demo/` 和历史归档不能单独作为完成证据。

## 4. 当前最短关键路径

```text
批准首个 ProjectCase
→ 冻结任务、数据、预算和验收
→ 在 AgentTeams 创建五个元 Agent
→ 跑通一个最小真实闭环
→ 固化 Identity / Skill / Trace
→ 形成候选对照证据
→ 从证据派生简介和 PPT
→ 8 月 15 日冻结并完成红线复核
```

任何不会缩短该关键路径的工作，包括独立产品界面、上游源码改造和全量场景实现，均不进入本阶段。
