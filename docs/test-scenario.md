# AgentFit 测试与桥接指南

本文档只列出仓库当前可执行的路径，并明确区分核心模拟器、AgentTeams 和 τ²-bench 三类证据。

## 本地核心闭环

### 安装

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
```

### 运行示例

`examples/telecom-materials.json` 是唯一跟踪的示例材料正本。先编译出包含 SourceObservation、TaskSample 和四类已冻结 SampleSetManifest 的 case；生成 case 写入忽略的 `output/`，不作为第二个仓库正本。`--auto-approve` 只用于本地确定性演示；生产默认 Human Gate 会阻断未明确批准的变更和交付。

获批的 G3 决策必须由运行环境中的外部密钥签名。密钥不得写入仓库、RunStore、命令参数或日志；训练、验证和导出进程需要由本地 secret manager 注入同一个密钥与 key id。本地演示可在当前 shell 隐式输入：

```bash
read -rsp "G3 demo signing key (at least 32 bytes): " AGENTFIT_G3_SIGNING_KEY
echo
export AGENTFIT_G3_SIGNING_KEY
export AGENTFIT_G3_KEY_ID=local-demo
```

```bash
agentfit compile \
  --bundle examples/telecom-materials.json \
  --output output/telecom-case.json

agentfit train \
  --case output/telecom-case.json \
  --output output/telecom-demo \
  --auto-approve

agentfit validate output/telecom-demo
agentfit report output/telecom-demo
agentfit export output/telecom-demo
```

当前严格示例会被 G3 拒绝导出：它的四个集合都要求 100% 通过，但 adaptation 只提供一个构建样本。前两条命令应成功，`agentfit export` 应返回非零状态。这个拒绝是可信验收链的预期证据，不是演示失败；只有四集合 Objective 真正满足后才允许生成部署包。

### 实际产物

```text
output/telecom-demo/
├── run.json
├── source_observations.json
├── task_samples.json
├── sample_sets.json
├── objective.json
├── acceptance.json
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
│   # 以下仅在四集合验收与 G3 均批准后由 export 生成
├── boundary.json
├── solution_package/package.json
└── evidence_package/manifest.json
```

`agentfit validate` 会从磁盘重新计算 epoch 哈希链、四类冻结样本的 Episode 覆盖、Objective、AcceptanceResult 和候选身份，不接受 `summary.json` 中未经验证的布尔值。`delivery_decision.json` 将 Human G3 结果、交付条件、获评测候选、四集合指标、ObjectiveRef、AcceptanceRef 和决策前证据哈希绑定；只有 Objective 已满足的人审批准才使用外部密钥生成 HMAC-SHA256，未满足时生成确定性 unsigned 拒绝。核心与 AgentTeams 导出共用该门禁并携带交付条件。`evidence_package/manifest.json` 为导出时存在的运行证据逐文件记录 SHA-256。

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

真实执行通过 `bridges/agentteams/executor.py` 中的 `AgentTeamsSandboxExecutor` 注入核心
Orchestrator。它只发送四层 Candidate、SampleRef、输入和约束，不发送 expected/label；
目标 Worker 在 AgentTeams 隔离沙箱中自行把 L1/L2 合同解析为现场可用实现。结果必须使用
`agentfit.agentteams-result` 信封，并带回 CandidateRef、SampleRef、run_index、步骤、成本
和 runtime_ref。在线执行会直接落训练 Trace/Episode。

如果平台先批量导出结果，再离线写回已有 training RunStore，可调用同一协议解析器：

```python
import json
from pathlib import Path

from bridges.agentteams.import_results import import_results_to_runstore

results = json.loads(Path("/absolute/path/to/agentteams-results.json").read_text())
count = import_results_to_runstore(
    results,
    "output/agentteams-run",
    epoch=1,
    phase="agentteams",
)
print(f"imported {count} AgentTeams episodes")
```

导入器会在写文件前校验 CandidateManifest、TaskSample、run_index 和 runtime_ref；候选
漂移、重复评价身份或协议错误都会拒绝整批，不生成部分 Episode。沙箱不可用、超时等
执行错误则保存为 runtime ERROR，并排除在 L1–L4 归因和方案更新之外。

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
  --candidate-spec examples/tau2-candidate.json
```

`--candidate-spec` 是被测系统的显式语义声明，不是展示标签。相同声明在不同模型、
沙箱或部署上复验时保持同一 CandidateRef，运行差异写入 runtime_ref；不同被测系统
必须使用不同声明。转换器会使用 τ² bridge 内的规范投影从原始 simulation 重算
TaskSample、Trace、Episode、成本与结果，再发布 RunStore。

需要复核已有结果时，必须重新调用同一个 bridge projector，而不是只做内部哈希检查：

```bash
PYTHONPATH=src python bridges/tau2bench/results_to_runstore.py \
  --validate-run-dir output/tau2-run
```

第一个文件是命令执行日志，不是 τ² 结果本身；转换器必须接收 τ² 实际生成的 `results.json`。转换后每条 simulation 对应一个 TaskSample、Trace 和 Episode，成本来自 agent/user cost，评价身份为 `candidate_ref + sample_ref + run_index`。

转换结果是 `run_kind=external_evaluation` 的独立 RunStore：

```text
output/tau2-run/
├── run.json
├── source_results.json
├── candidate_manifest.json
├── task_samples.json
├── external_evidence/
├── traces/
├── episodes/
└── summary.json
```

转换器原样保存上传字节并校验其 SHA-256；每条原始 simulation 通过 `ExternalEvidenceRecord` 绑定 CandidateManifest、TaskSample、Trace、Episode、结果、成本和 run_index。`agentfit validate` 负责平台无关的内部证据一致性；上述 bridge 复核命令还会从 τ² 原始记录重算 TaskSample、Trace/Episode、连续 run_index、成本和通过率。

外部评价不生成训练 Epoch、Solution snapshot、四类 Human-frozen SampleSetManifest 或 G3 决策，也拒绝这些产物混入。`agentfit report` 生成 `evaluation_report.md` 和外部评价 Dashboard；不得执行 `agentfit export`。只有进入冻结 ProjectCase 并完成训练、四集合评价和 G3 后，才允许导出方案包。

## 推荐测试顺序

1. `pytest -q`：核心、合同、桥接 fixture 和冻结目录门禁。
2. 本地核心闭环：确认训练、验证和报告可重放，并确认严格示例被 G3 阻断导出。
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
