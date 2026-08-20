# 阶段 B 冒烟 · telecom 5 题协议验证（smoke-run-008 最终成功）

- 时间：2026-08-20 深夜 · 模型：deepseek-v4-flash（官网直连）· 平台：AgentTeams 隔离 Worker
- 门禁依据：benchmark-evaluation §5 阶段 B——只验证协议往返，不报告效果结论

## 最终结果（smoke-run-008）

| 项 | 值 |
|---|---|
| 预指定 5 题（adaptation 各 1 次） | 全部真实执行，**execution_errors = 0** |
| 业务结果 | 2 PASS / 3 FAIL（初始候选只有 2 条 bootstrap 规则，属预期） |
| **完整闭环** | 执行 → 归因（3×L3/missing_rule）→ **任务提案 1 条**（混合证据分组归纳）→ G1 → 事务提交 → 方案 v000→**v001** |
| RunStore 证据链 | run/summary/steps/loss_traces/training_traces/training_episodes/messages/solution_versions/optimization_suggestions/dashboard 全齐 |

冒烟全程 8 次运行递进（003-008），累计修复 4 个真实缺陷（见下）。

## 冒烟揭示并修复的缺陷（全部带测试）

1. **worker readiness 路径过时**（003）：桥接查 `/root/hiclaw-fs/...`，v1.2.0 实际在 `/root/.copaw-worker/...` → 双路径探测
2. **结果信封脆弱**（003-005）：worker 偶尔省略 `AGENTFIT_RESULT_BEGIN` 标记、或 JSON 带围栏/尾巴 → `_extract_bare_result` 结构性容错解析（判据=结果 schema+身份字段齐全，不信标记；噪声正确拒绝）
3. **串行批内错序竞态**（006）：任务 N 的 poll 收到任务 N-1 的迟到合法回复 → 语义修正为"跳过继续等本任务回复"（不是错误）
4. **混合证据归纳失败**（007→008）：3 个不同根因样本（data_saver/bad_network/airplane）并成一个 pattern，共性特征合取为空被拒 → 按期望动作分组逐组归纳

另修平台侧（非代码）：MinIO IAM 策略清卷丢失导致 worker 状态同步全线失败（manager 自动重建策略后恢复）。

## 协议验证清单（全部通过）

- [x] DeepSeek 官网 API → AgentTeams 隔离 Worker → Matrix 房间往返
- [x] τ² telecom 任务 → 语义 bundle（tasks_small 20 题，8/4/4/4 四集合冻结，冒烟取预指定 5 题）
- [x] 执行结果 → Trace/Episode → RunStore 落盘 → dashboard/报告
- [x] 归因 → 提案（语义双轨 + origin）→ G1 → ChangeTransaction → 版本前进
- [x] ERROR 与业务 FAIL 分离（008 中 0 混淆）

## 按正本约束的声明

本冒烟只证明协议往返与工程闭环。不报告模型或 AgentFit 效果结论；
20 题完整维护闭环（阶段 C）是下一步，需另行批准。

## 预算消耗

冒烟 8 次 + 诊断 4 次共约 17 个 worker 生命周期、约 60+ 次模型调用，估算 < $0.30（远低于 $50 预算）。
