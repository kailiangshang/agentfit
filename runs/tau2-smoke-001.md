# τ²-bench 真实冒烟 · agentfit-smoke-001

- 时间：2026-08-16 深夜 · 环境：tau2-bench(telecom) + DeepSeek（10 任务，单轮）
- 命令：`tau2 run --domain telecom --agent-llm deepseek/deepseek-chat --user-llm deepseek/deepseek-chat --num-trials 1 --num-tasks 10 --save-to agentfit-smoke-001`

## 结果

| 指标 | 值 |
|---|---|
| 通过率（Pass¹） | **9/10 = 90%** |
| 总成本 | **$0.0646**（均值 $0.0065/样本） |
| 常规样本成本 | ~$0.0012–0.0016 |
| 失败样本成本 | **$0.0312（≈25 倍，重试循环烧钱）** |

## 逐任务

| 根因组合 | 结果 | 成本 |
|---|---|---|
| airplane_mode_on + bad_network_preference | ✓ | $0.0012 |
| airplane_mode_on + data_mode_off | ✓ | $0.0010 |
| data_saver_mode_on + roaming_off | ✓ | $0.0012 |
| bad_network_preference + roaming_off | ✓ | $0.0012 |
| data_usage_exceeded + roaming_off | ✓ | $0.0015 |
| data_mode_off + data_usage_exceeded | ✓ | $0.0014 |
| data_saver_mode_on + data_usage_exceeded | ✓ | $0.0014 |
| airplane + bad_network + roaming_off（三重复合） | ✓ | $0.0016 |
| **airplane_mode_on + user_abroad_roaming_enabled_off（复合）** | **✗** | **$0.0312** |
| airplane + data_saver + roaming_disabled | ✓ | $0.0229 |

## 关键发现

**唯一失败的样本是 airplane+roaming 复合根因——与模拟器世界的 F4 故障类型完全一致。**
裸跑 baseline 在复合根因上失败且成本 25 倍（重试循环），这正是 AgentFit 训练循环要修的失败类：
归因到 L3/L4 → 排查链知识（多步任务拆解）+ 拓扑升级。真实数据第一次验证了方案设计的针对性。

注意：与提交材料中记录的 80% baseline（10 样本）相比本次为 90%——单轮小样本方差大，
正式对比实验需多 trial（test-scenario.md 的 A/B/C/D 分组设计）。
