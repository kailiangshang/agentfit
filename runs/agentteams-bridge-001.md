# AgentTeams 桥接实测 · agentteams-bridge-001

- 时间：2026-08-17 凌晨 · 目标：兑现"从现在起启动 AgentTeams"，库保持零平台依赖

## 结果

| 项 | 值 |
|---|---|
| 团队 `agentfit` | **Active，2/2 worker 就绪**（steward 领队 + attributor + architect） |
| 迭代方式 | **唯一正本清单** `bridges/agentteams/team.yaml`——改动后重新 apply 即迭代，不搞 v2/v3 并行版本 |
| 确定性边界落地 | 只有 3 个 LLM 认知角色上平台；Orchestrator/Validator/Auditor 是库内纯代码，不占 worker |
| 模型 | deepseek-chat（openai-compat，manager 配置） |
| 接入方式 | `docker exec agentteams-controller hiclaw apply -f <manifest>`（从 git 历史恢复的旧工具链知识） |

## 清理记录

- 旧团队 `agentfit-retail-m1`（旧五角色）与过渡期 `agentfit-v2` 均已删除；
  过程中发现删除操作会波及共享 worker（新团队一度 Degraded），重建正本后恢复 Active 2/2。
  旧清单仍可从 git 历史找回（`git show edb13cf^:runtime/agentteams/m1/agentfit-retail-m1.yaml`）。

## 交付物

- `bridges/agentteams/team.yaml` —— 唯一正本团队清单（identity/soul 从 skills/*.md 浓缩，含安全规则与"不越权"契约）
- `bridges/agentteams/apply_team.py` —— 自动化：找 controller → CLI 探测 → apply → 状态回读 JSON（BSD/macOS 兼容）
- `output/agentteams-bridge-001/team-status.json` —— 平台状态回读证据

## 下一步

- Steward 消息往返闭环：intake 消息（材料操作化）→ 分派归因/建议 → 结果回流 RunStore
- τ² 适配器 + 50 样本 baseline → 首轮真实训练
