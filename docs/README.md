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
| [架构](architecture.md) | 唯一架构正本：双层架构、样本合同、训练闭环、桥接和验证门禁 |
| [开发计划](development-plan.md) | 稳定收敛、可信证据、运行闭环与真实桥接的实施顺序 |
| [测试场景](test-scenario.md) | Telecom 故障诊断全链路执行方案 |

## 快速验证

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
read -rsp "G3 demo signing key (at least 32 bytes): " AGENTFIT_G3_SIGNING_KEY
echo
export AGENTFIT_G3_SIGNING_KEY
export AGENTFIT_G3_KEY_ID=local-demo
agentfit train --case examples/telecom-case.json --output output/telecom-demo --auto-approve
agentfit validate output/telecom-demo
agentfit report output/telecom-demo
agentfit export output/telecom-demo
```

这里的自动批准仅用于本地确定性演示；G3 签名密钥只从运行环境读取，不写入仓库或 RunStore。当前已经实现核心闭环、四集合评价调度、签名 G3 交付门禁、可信 RunStore 和离线桥接合同；完整材料编译、生产认知适配器和真实平台效果仍按[开发计划](development-plan.md)推进。

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
