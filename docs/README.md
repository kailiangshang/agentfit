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
L2  能力合同层     组合 + 前后置条件 + 口径 + Human Gate
L1  Solid 层       最小原子能力合同 + 输入输出 + 作用语义
```

四层只声明方案中有什么、职责和连接，不选择 MCP、原生函数、HTTP、脚本或 Memory 产品。L1–L3 禁止隐藏同层执行依赖，L4 通过显式通信边协作；具体绑定由 Executor/bridge 在隔离运行环境中解析并留下 `runtime_ref`。

## 文档

| 文件 | 内容 |
|---|---|
| [架构](architecture.md) | 唯一架构正本：双层架构、样本合同、训练闭环、桥接和验证门禁 |
| [开发计划](development-plan.md) | 稳定收敛、可信证据、运行闭环与真实桥接的实施顺序 |
| [测试场景](test-scenario.md) | Telecom 故障诊断全链路执行方案 |
| [AgentTeams 真实联动](agentteams-live-validation.md) | 已完成的真实模型/Matrix/Worker 往返、证据边界与复现方式 |

## 快速验证

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
read -rsp "G3 demo signing key (at least 32 bytes): " AGENTFIT_G3_SIGNING_KEY
echo
export AGENTFIT_G3_SIGNING_KEY
export AGENTFIT_G3_KEY_ID=local-demo
agentfit compile --bundle examples/telecom-materials.json --output output/telecom-case.json
agentfit train --case output/telecom-case.json --output output/telecom-demo --auto-approve
agentfit validate output/telecom-demo
agentfit report output/telecom-demo
agentfit export output/telecom-demo
```

当前严格示例会被 G3 拒绝导出：四集合各有 3 个样本并要求 100% 通过；本地确定性运行会完成 adaptation 更新，并在 adaptation、validation 和 sealed holdout 达到 3/3，但最简候选在两个复合 stress 样本上失败，因此 stress_and_failure 只有 1/3。`validate` 和 `report` 应成功，`export` 应返回非零状态；这证明单轮训练通过率或部分评价集合通过不能冒充全局验收。要产生可部署包，必须用失败 Trace 改进候选并重新验证四集合，而不是降低演示阈值。

这里的自动批准仅用于本地确定性演示；G3 签名密钥只从运行环境读取，不写入仓库或 RunStore。当前已经实现材料编译、核心闭环、四集合评价调度、Objective/Acceptance、签名 G3 交付门禁、训练/外部评价分型的 RunStore，以及 AgentTeams 上真实 DeepSeek/Matrix/隔离 Worker 的 12 样本 adaptation 更新和四集合往返。当前真实运行因 stress 协议 ERROR 与成本不可观测被 G3 拒绝，只证明桥接、更新和证据门禁可运行，不代表业务副作用或最终泛化已经完成；后续收敛按[开发计划](development-plan.md)推进。

参与开发前请阅读仓库根目录的 [CONTRIBUTING](../CONTRIBUTING.md) 和 [SECURITY](../SECURITY.md)。

## 已冻结的初赛提交

以下目录是已经提交的历史档案，只读保留；后续开发以本库架构正本为准。

| 文件 | 内容 |
|---|---|
| [作品简介](../competition/2026-08-16/submission/work-introduction.md) | 500 字以内 |
| [PPT 大纲](../competition/2026-08-16/submission/ppt-outline.md) | 12 页主路演 + 5 页附录 |
| [Agent Identity](../competition/2026-08-16/submission/agent-identity.md) | 四层架构中的身份定义 |
| [开放与合规](../competition/2026-08-16/submission/openness-and-compliance.md) | MIT 开源 + 依赖 + 未实现披露 |
| [风险与人工门禁](../competition/2026-08-16/submission/risk-and-human-gates.md) | 门禁分类 + 正则保障 |

## License

MIT — 详见 [LICENSE](../LICENSE)
