# AgentFit 文档

本目录只保留一个当前整体方案，以及支撑它的比赛约束、来源证据和官方参考。历史设计和过程计划不再并行保留，需要追溯时使用 Git。

## 唯一当前方案

- [AgentFit 整体方案](agentfit-solution.md)：产品定位、四层资产纪律、样本驱动的持续学习、元团队、AgentTeams 边界、评测治理、交付和阶段门禁的唯一有效基线。

## 2026-08-15 初赛提交阶段

本阶段只完成简介、PPTX、PDF、Agent Identity、Skill、Human/风险和开放披露，以及上传前验证。真实 AgentTeams 元团队、ProjectCase 和候选对照不是提交前置条件；当前运行结论保持 `requires_runtime_trial`。唯一材料入口见 [初赛提交工作区](../competition/2026-08-15/README.md)。

## 后续阶段

AgentTeams walking skeleton 已获项目所有者授权启动，并按[整体方案 §13.3](agentfit-solution.md#133-后续最小实施顺序与阶段完成定义)的 M0–M4 顺序实施，不另建并行路线图。当前 M0 已完成并为 `READY`，M1 仍为 `IN_PROGRESS`；真实五元团队已完成两轮 ProjectCase preparation（Round 1：task 0；Round 2：task 0、2、13），但四份正式 manifest 尚未实例化和冻结，尚未运行 Candidate。复赛工程、M2–M4、场景内持续学习工程和生产部署仍由晋级结果、评审反馈、运行证据与后续授权共同决定。

- [回家 Demo 执行手册](guides/home-demo-runbook.md)：复用已验收为 `READY` 的 M0 基线，用 τ³-bench retail 样本和 AgentTeams 五元团队完成两轮 ProjectCase preparation，保留部署、回放、Dossier/Trace、结构化验证和下一门禁命令，并保持 M1 `IN_PROGRESS`；它是操作 Runbook，不是第二套方案。
- [AgentTeams M1 多情景实测](research/home-demo/retail-m1/dossier/15-agentteams-m1-multiscenario-run.md)：保存两轮真实 Trace 的脱敏指标、失败恢复、设计更新、求解/适配路径、成本边界和 post-run provenance 限制；机器可读对照与原始私密证据分离。

## 内部依据

### 比赛约束

- [GOAI Agent Infra 初赛要求矩阵](internal/competition/preliminary-requirements-matrix.md)
- [GOAI Agent Infra 初赛红线与声明检查表](internal/competition/preliminary-red-line-checklist.md)

### 来源证据

- [证据研究规则](internal/evidence-research/README.md)
- [Evidence Registry](internal/evidence-research/evidence-registry.json)
- [证据卡模板](internal/evidence-research/evidence-card-template.md)

### 官方参考

- [《新智基座》Agent Infra 参赛手册](reference/新智基座-参赛手册.pdf)

历史内容只通过 Git 追溯，不能覆盖 [AgentFit 整体方案](agentfit-solution.md)中的当前定义、状态和证据边界。
