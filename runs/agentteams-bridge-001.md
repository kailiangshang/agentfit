# AgentTeams 桥接实测 · agentteams-bridge-001

- 时间：2026-08-17 凌晨 · 目标：兑现"从现在起启动 AgentTeams"，库保持零平台依赖

## 结果

| 项 | 值 |
|---|---|
| 新团队 `agentfit-v2` | **Active，2/2 worker 就绪**（steward 领队 + attributor + architect） |
| 确定性边界落地 | 只有 3 个 LLM 认知角色上平台；Orchestrator/Validator/Auditor 是库内纯代码，不占 worker |
| 模型 | deepseek-chat（openai-compat，manager 配置） |
| 接入方式 | `docker exec agentteams-controller hiclaw apply -f <manifest>`（从 git 历史恢复的旧工具链知识） |
| 旧团队 `agentfit-retail-m1` | 仍 Active（旧五角色叙事，未删——见"待决定"） |

## 交付物

- `bridges/agentteams/team-agentfit-v2.yaml` —— 六角色设计的团队清单（identity/soul 从 skills/*.md 浓缩，含安全规则与"不越权"契约）
- `bridges/agentteams/apply_team.py` —— 自动化：找 controller → CLI 探测 → apply → 状态回读 JSON（BSD/macOS 兼容）
- `output/agentteams-bridge-001/team-status.json` —— 平台状态回读证据

## 待决定（明天）

- 旧团队 `agentfit-retail-m1` 是否下线：清单在 git 历史可随时恢复（`git show edb13cf^:runtime/agentteams/m1/agentfit-retail-m1.yaml` + 重新 apply），删除命令 `hiclaw delete team agentfit-retail-m1`。建议下线省资源，但未擅动。
- 下一步真实分工：Steward 接收 intake 消息（材料操作化）→ 分派归因/建议 → 结果回流 RunStore 的完整往返。
