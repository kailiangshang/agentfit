# AgentFit 测试与桥接指南

本文档只列出仓库当前可执行的路径，并明确区分核心模拟器、AgentTeams 和 τ²-bench 三类证据。

## 本地核心闭环

### 安装

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
```

### 运行示例

`examples/telecom-case.json` 包含四个互不重叠的样本及四类已冻结 SampleSetManifest。`--auto-approve` 只用于本地确定性演示；生产默认 Human Gate 会阻断未明确批准的变更和交付。

```bash
agentfit train \
  --case examples/telecom-case.json \
  --output output/telecom-demo \
  --auto-approve

agentfit validate output/telecom-demo
agentfit report output/telecom-demo
agentfit export output/telecom-demo
```

### 实际产物

```text
output/telecom-demo/
├── run.json
├── samples.json
├── sample_sets.json
├── epochs/
├── solution_versions/
├── messages/
├── traces/
├── episodes/
├── summary.json
├── delivery_decision.json
├── training_report.md
├── meta_review.md
├── dashboard.html
├── boundary.json
├── solution_package/package.json
└── evidence_package/manifest.json
```

`agentfit validate` 会从磁盘重新计算 epoch 哈希链、四类冻结样本的 Episode 覆盖和最终候选身份，不接受 `summary.json` 中未经验证的布尔值。`delivery_decision.json` 将 Human G3 结果绑定到获评测候选、四集合指标和决策前证据哈希；核心与 AgentTeams 导出共用该门禁。`evidence_package/manifest.json` 为导出时存在的运行证据逐文件记录 SHA-256。

本地命令只用 adaptation 集合驱动方案更新；候选冻结后会分别为四类集合生成 Episode 和指标，再请求 G3。validation、sealed_holdout 和 stress_and_failure 只用于评价，不把结果反向写入方案。当前 Executor 仍是确定性模拟器，因此这些结果只能证明合同和调度闭环，不得描述为真实模型泛化效果。

## AgentTeams 桥接

AgentTeams 是外部运行底座，核心库不导入其 SDK。`team.yaml` 是由 Skill Registry 生成的部署正本，不手工维护 Skill 副本。

```bash
# 检查生成物是否与 Registry 一致
python bridges/agentteams/render_team.py --check

# 只读回读运行态并输出精确 drift
python bridges/agentteams/apply_team.py --status-only

# 维护者审核 drift 后再显式 apply
python bridges/agentteams/apply_team.py \
  --manifest bridges/agentteams/team.yaml
```

状态回读只把 `agentfit` 前缀的其他 Team 识别为本项目遗留对象，不触碰无关 Team。AgentTeams v1.1.2 的扁平列表结果只能核对 Team/Worker 成员；拿不到 model、runtime、soul 和 Registry 注解时，对应项明确标记为 `unverified`，不会误报 `in_sync` 或伪称完整规格一致。完整 drift 需要平台返回原始 Team/Worker 规格。

AgentTeams 的 Team Active 只证明部署对象存在；只有 Matrix 消息、模型清单、工具 Trace、成本和导出哈希齐全时，才能证明一次真实运行完成。

## τ²-bench 桥接

批量运行包装器和结果转换器都位于核心库之外：

```bash
python bridges/tau2bench/run_bench.py \
  --tau2-dir ../agentfit-labs/tau2-bench \
  --domain telecom \
  --num-tasks 10 \
  --agent-llm deepseek/deepseek-chat \
  --user-llm deepseek/deepseek-chat \
  --output output/tau2-command.json

PYTHONPATH=src python bridges/tau2bench/results_to_runstore.py \
  /absolute/path/to/tau2/results.json \
  --run-dir output/tau2-run \
  --label telecom-baseline
```

第一个文件是命令执行日志，不是 τ² 结果本身；转换器必须接收 τ² 实际生成的 `results.json`。转换后每条 simulation 对应一个 TaskSample、Trace 和 Episode，成本来自 agent/user cost，评价身份为 `candidate_ref + sample_ref + run_index`。

## 推荐测试顺序

1. `pytest -q`：核心、合同、桥接 fixture 和冻结目录门禁。
2. 本地核心闭环：确认训练、验证、报告、导出均可重放。
3. τ² 小批量：先固定模型清单和独立输出目录，再扩大样本。
4. AgentTeams 只读 drift：确认精确创建、修改和遗留项。
5. 维护者审核后 apply，并保留真实平台证据。
6. 用相同冻结 SampleSetManifest 对比候选，不跨集合调参。

## 结论边界

| 证据 | 能说明什么 | 不能说明什么 |
|---|---|---|
| 核心模拟器测试 | 状态机、合同、归因和交付机制可重复 | 真实模型效果 |
| τ² fixture | 转换器和证据落盘正确 | 真实 API 或完整 bench 表现 |
| τ² 真实 results | 指定模型、样本和运行参数下的效果与成本 | AgentTeams 部署正确 |
| AgentTeams Active | Team/Worker 被控制器接受 | 任务已完成或方案有效 |
| 完整 RunStore | 指定运行的证据可重算 | 未运行集合的效果 |
