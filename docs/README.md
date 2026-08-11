# AgentFit 文档

本目录只保留一个当前整体方案，以及支撑它的事实证据、契约和比赛约束。历史设计不再以并行文档保留，需要追溯时使用 Git 提交记录。

## 唯一当前方案

- [AgentFit 整体方案](agentfit-solution.md)：产品定位、方法论、系统边界、执行闭环、评测治理、跨项目成长和比赛证明责任的唯一有效基线。

当前阶段：初赛材料已经就绪；真实 AgentFit 集成尚未开始。近期唯一执行目标是在 AgentTeams 上用一个冻结 ProjectCase 跑通可复现的 walking skeleton，具体门禁见整体方案第 13 节。

当前初赛材料与 2026 年 8 月 15 日内部冻结工作在 [`competition/2026-08-15/`](../competition/2026-08-15/) 独立管理；该目录从本方案和内部证据派生，不能反向覆盖总体定义。

Git 历史中的旧讨论、旧方法论或执行计划均不具备当前规范地位。

## 内部事实与评测依据

### 比赛约束

- [GOAI Agent Infra 初赛要求矩阵](internal/competition/preliminary-requirements-matrix.md)
- [GOAI Agent Infra 初赛红线与声明检查表](internal/competition/preliminary-red-line-checklist.md)

### 来源证据

- [证据研究规则](internal/evidence-research/README.md)
- [Evidence Registry](internal/evidence-research/evidence-registry.json)
- `internal/evidence-research/cards/`：十二张已核验来源卡

### 跨场景研究输入

- [ProjectCase 契约](internal/cross-scenario-project-suite/project-case-template.md)
- [v0 选择矩阵](internal/cross-scenario-project-suite/v0-selection-matrix.md)
- [v0 选择理由](internal/cross-scenario-project-suite/v0-selection-rationale.md)
- [v0 Manifest](internal/cross-scenario-project-suite/v0-manifest.json)

上述项目集用于后续迁移与跨项目研究，不是近期并行实施清单。

## 原始参考材料

- [《新智基座》Agent Infra 参赛手册](reference/新智基座-参赛手册.pdf)

历史只通过 Git 提交记录追溯，不能作为正式实现输入，也不能覆盖 [AgentFit 整体方案](agentfit-solution.md)中的当前定义、完成状态和证据边界。
