# AgentFit

> Agent 方案训练系统：输入业务场景和样本，输出经过多轮训练、通过率验证、边界明确的可部署 Agent 方案。

## 核心思想

**方案不是设计出来的，是训练出来的。**

```
传统: 设计 → 评审 → 部署（一次性，静态，靠经验）
AgentFit: adaptation Batch → 归因与更新 → Epoch validation → 再训练/停止 → 封存验收 → 部署
```

adaptation 负责更新，validation 负责选择：一个 Epoch 完整覆盖一次 adaptation，每个 Batch
产生 Trace、归因和方案 Step；Epoch 结束后冻结 Candidate，只用 validation 判断继续、恢复、
Early Stopping 或候选晋升。validation、sealed_holdout 和 stress_and_failure 都不得直接生成或
修改 L1–L4，最终封存集合也不会回流训练。完整定义以[架构正本](architecture.md)为准。

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
| [AgentTeams 历史联动证据](agentteams-live-validation.md) | 2026-08-18 真实模型/Matrix/Worker 往返及证据边界；当前复现入口阻断 |
| [业务维护评测](benchmark-evaluation.md) | 唯一 τ²-bench 路线：先做透 telecom 5→20→74/40，再用 retail 验证四层资产复用 |

当前评测目标模型固定为用户自有 DeepSeek 官网 API 的 `deepseek-v4-flash`；AgentTeams
通过 AI Gateway 连接该上游，模型凭证只保存在本地 `AGENTTEAMS_LLM_API_KEY` 或平台 secret
中。

## DeepSeek 本地配置

仓库只提交无密钥的 `.env.example`。首次使用时复制为本地 `.env`，填写
`AGENTTEAMS_LLM_API_KEY`，再加载到启动 AgentTeams 或运行桥接命令的同一个 shell：

```bash
cp .env.example .env
chmod 600 .env
${EDITOR:-vi} .env
set -a
. ./.env
set +a
```

`.env` 和其他本地变体均被 Git 忽略，只有 `.env.example` 可以提交。不要在聊天、命令参数、
日志、RunStore、Trace、Dashboard 或报告中输出密钥。

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

当前严格示例会被 G3 拒绝导出：四集合各有 3 个样本并要求 100% 通过；现行本地确定性实现会完成一次 adaptation Batch 更新，并在候选冻结后运行四集合评价。其 adaptation、validation 和 sealed_holdout 为 3/3，但最简候选在两个复合 stress 样本上失败，因此 stress_and_failure 只有 1/3。`validate` 和 `report` 应成功，`export` 应返回非零状态；这证明单轮更新通过率或部分评价集合通过不能冒充 Epoch 收敛或全局验收。要产生可部署包，必须先完成规范状态机，再由 adaptation 失败 Trace 改进候选并重新验证，而不是降低演示阈值。

这里的自动批准仅用于本地确定性演示；G3 签名密钥只从运行环境读取，不写入仓库或 RunStore。当前已经实现材料编译（含层级类型学与 Case 注册制扩展）、Batch/Step/Epoch/validation 训练状态机（每 Epoch 完整不重复覆盖 adaptation、Epoch 末只读 validation、Early Stopping 停止原因可重算、反向可达性归因、`train_replay` 分型）、正则传播（trained 子集计算、简化提案与任务提案同门禁、冲突标注、frozen 元素只出 advisory）（每 Epoch 完整不重复覆盖 adaptation、Epoch 末只读 validation、Early Stopping 停止原因可重算、反向可达性归因与反向依赖传播、`train_replay` 分型）、最终四集合评价调度、Objective/Acceptance、签名 G3 交付门禁、训练/外部评价分型的 RunStore、禁用 JavaScript 仍可完整阅读的静态 Dashboard，以及 AgentTeams 上真实 DeepSeek/Matrix/隔离 Worker 的往返。多 Epoch 真实（非模拟器）运行证据仍待积累。既有真实运行只证明桥接、局部更新和证据门禁可运行，不代表训练已收敛、业务副作用或最终泛化已经完成；后续收敛按[开发计划](development-plan.md)推进。

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
