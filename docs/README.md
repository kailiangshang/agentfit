# AgentFit

> Agent 方案训练系统：输入业务场景和样本，输出经过多轮训练、通过率验证、边界明确的可部署 Agent 方案。

## 核心思想

**方案不是设计出来的，是训练出来的。**

```
传统: 设计 → 评审 → 部署（一次性，静态，靠经验）
AgentFit: 训练 → 评估 → 更新 → 再训练 → 收敛 → 部署（迭代，动态，靠数据）
```

## 四层骨架

```
L4  行为拓扑层     Agent 架构 + 协作模式 + 人工介入位置
L3  可复用知识层   Skill + 路由规则 + 排查链 + 经验
L2  可二次开发能力层 安全封装 + 组合 + 口径 + 送审路由
L1  Solid 层       固定原子能力: API + 数据库 + 人工审核
```

三组约束保证天然可维护：纵向逐层调用、横向同层禁止互调、存在依赖全链路追溯。

## 文档

| 文件 | 内容 |
|---|---|
| [四层骨架 v4-FINAL](agentfit-skeleton.md) | 唯一指导性文档（定稿，不改） |
| [AgentFit 方案](agentfit-solution.md) | 基于骨架的完整方案 |
| [落地设计](agentfit-implementation.md) | 真实实现架构：元层 5 Agent + 7 Skill + 交互协议 + 任务分发，及对象层数据结构与算法 |
| [测试场景](test-scenario.md) | Telecom 故障诊断全链路执行方案 |

## 竞赛提交

| 文件 | 内容 |
|---|---|
| [作品简介](../competition/2026-08-16/submission/work-introduction.md) | 500 字以内 |
| [PPT 大纲](../competition/2026-08-16/submission/ppt-outline.md) | 12 页主路演 + 5 页附录 |
| [Agent Identity](../competition/2026-08-16/submission/agent-identity.md) | 四层架构中的身份定义 |
| [开放与合规](../competition/2026-08-16/submission/openness-and-compliance.md) | MIT 开源 + 依赖 + 未实现披露 |
| [风险与人工门禁](../competition/2026-08-16/submission/risk-and-human-gates.md) | 门禁分类 + 正则保障 |

## License

MIT — 详见 [LICENSE](../LICENSE)
