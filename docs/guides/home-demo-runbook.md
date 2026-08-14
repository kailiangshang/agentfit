# AgentFit 回家 Demo 执行手册

> 目标：用 2–3 小时取得第一批真实、可回放、不夸大完成度的 Demo 证据。本文只把 [AgentFit 整体方案](../agentfit-solution.md)的 M0/M1 变成操作步骤，不是第二套方案。

> 2026-08-14 执行状态：M0 已完成并为 `READY`；M1 仍为 `NOT_STARTED`。AgentTeams 固定版本、官方预构建镜像、私密配置、安装/回读步骤和 `.local-demo/agentteams/evidence` 证据以唯一的[`runtime/agentteams/README.md`](../../runtime/agentteams/README.md)为准。本手册从 retail/τ³-bench 样本准备继续，不再维护第二套 AgentTeams 安装或 M0 证据方式。

## 1. 今晚的准确终点

今晚只选择一个 ProjectCase 方向：**retail 客服工具调用方案设计**。样本来自 τ³-bench；OpsPilot 继续作为比赛官方 baseline 与运维场景锚点。**OpsPilot 与 retail 保持两个独立来源、两个独立 ProjectCase，不混入同一个 SampleSet。**

今晚可以完成：

1. 固定 AgentFit、AgentTeams、τ³-bench 版本、授权范围、运行入口和已知边界，满足 M0；
2. 用 retail 官方 train 任务做 1 → 3 → 12/20 的 τ³-bench 原生 preflight，验证模型、工具、状态变化、评价和日志链；
3. 在 AgentTeams 实例化五元元团队，让它编译 task 0 的样本/任务语义，并在正式试验门禁处停下；
4. 记录一次“答案泄漏”拒绝或预算扩张 Human 门禁；
5. 将状态如实写为 `M1: IN_PROGRESS`。

今晚不会自动完成 M1。原因是 preflight 发生在正式 ProjectCase、四份 manifest、Candidate 和 TrialSpec 冻结前，因此它**不是 AgentFit Candidate**、不是 `EvaluationUnit`，也不能满足 M1 的“冻结 ProjectCase 下执行真实候选”。若今晚只完成上述内容，Demo 的价值是证明底座可运行、语义可编译、无效试验会被门禁拒绝。

硬边界：

- τ³-bench 的公开 `test` split 不是 sealed holdout；
- 不把 12–20 个探索样本临时硬拆成四份正式 manifest；
- 不声称已经公平比较 Agentless、单 Agent 和多 Agent；
- M2/M3/M4 均未启动，不声称自动搜索、自动进化或 Meta-learning；
- 不修改 AgentTeams 核心，不开发新 UI。

## 2. 已核验的样本源

2026-08-13 核验的当前正式来源：

- 仓库：<https://github.com/sierra-research/tau2-bench>
- release：`v1.0.1`，annotated tag 解引用提交为 `fc0055dc4e0a316c3f83133267fbd6faaa770992`
- 项目/CLI 名仍为 `tau2`，README 已将当前基准称为 τ³-bench；`sierra-research/tau3-bench` 不是正确地址；
- License：MIT；Python：`>=3.12,<3.14`；安装工具：`uv`；
- 核心域：`mock`、`airline`、`retail`、`telecom`、`banking_knowledge`；
- retail 有 **114** 个官方任务：`train=74`、`test=40`、`base=114`；
- 每个任务含用户场景、业务状态、期望工具动作和自动评价条件；
- `--save-to X` 写入 `data/simulations/X/results.json`，可用 `tau2 view` 检查。

这里的一条 Sample 是：固定版本的 policy + 一个 task id 的用户场景/初始状态 + 期望工具动作/状态变化/自然语言断言 + 一次具体运行的模型、参数、Trace 和评价。`ProjectCase != Sample`：前者定义任务分布、样本集合、候选空间、预算和评测协议，后者是其中一个可独立冻结、执行和评价的单位。

## 3. 建立可跨终端恢复的本地工作区

从 `agentfit` 仓库根目录开始。第一段会在脏工作树上立即停止，不会继续 pull。

```bash
set -euo pipefail
AGENTFIT_ROOT="$(git rev-parse --show-toplevel)"
test -z "$(git -C "$AGENTFIT_ROOT" status --porcelain)" || { git -C "$AGENTFIT_ROOT" status --short; echo 'STOP: save or commit local changes first'; false; }
git -C "$AGENTFIT_ROOT" fetch origin main
git -C "$AGENTFIT_ROOT" pull --ff-only origin main

AGENTFIT_LABS_ROOT="$AGENTFIT_ROOT/../agentfit-labs"
AGENTFIT_TAU3_ROOT="$AGENTFIT_ROOT/../agentfit-labs/tau2-bench"
AGENTFIT_RUN_ROOT="$AGENTFIT_ROOT/.local-demo/retail-m1"
mkdir -p "$AGENTFIT_LABS_ROOT" "$AGENTFIT_RUN_ROOT"/{baseline,source,native-runs/logs,dossier,agentteams,demo}

printf 'export AGENTFIT_ROOT=%q\nexport AGENTFIT_TAU3_ROOT=%q\nexport AGENTFIT_RUN_ROOT=%q\n' \
  "$AGENTFIT_ROOT" "$AGENTFIT_TAU3_ROOT" "$AGENTFIT_RUN_ROOT" \
  > "$AGENTFIT_RUN_ROOT/session.env"
```

每个新终端先进入 AgentFit，再恢复路径：

```bash
source .local-demo/retail-m1/session.env
test -d "$AGENTFIT_ROOT/.git"
```

`.local-demo/` 已被 AgentFit `.gitignore` 排除，运行原始数据和本地配置默认不得提交。

## 4. 固定 τ³-bench v1.0.1

此段可重跑：已有正确仓库时不会重新 clone；已有同名非 Git 目录则停止。

```bash
source .local-demo/retail-m1/session.env
test ! -e "$AGENTFIT_TAU3_ROOT" || test -d "$AGENTFIT_TAU3_ROOT/.git"
if test ! -d "$AGENTFIT_TAU3_ROOT/.git"; then
  git clone --branch v1.0.1 --depth 1 https://github.com/sierra-research/tau2-bench "$AGENTFIT_TAU3_ROOT"
fi
test "$(git -C "$AGENTFIT_TAU3_ROOT" remote get-url origin)" = 'https://github.com/sierra-research/tau2-bench'
test "$(git -C "$AGENTFIT_TAU3_ROOT" rev-parse HEAD)" = 'fc0055dc4e0a316c3f83133267fbd6faaa770992'
python3 --version
uv --version
UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv --directory "$AGENTFIT_TAU3_ROOT" sync
uv --directory "$AGENTFIT_TAU3_ROOT" run python -c 'import importlib.metadata as m; print(m.version("tau2"))'
uv --directory "$AGENTFIT_TAU3_ROOT" run tau2 intro
uv --directory "$AGENTFIT_TAU3_ROOT" run tau2 run --help | tee "$AGENTFIT_RUN_ROOT/baseline/tau2-run-help.txt"
```

若 Python 不在 3.12–3.13，停止，不要用 3.11/3.14 硬跑。若 `uv` 版本不支持 `--directory`，以子 shell 兼容执行：`(cd "$AGENTFIT_TAU3_ROOT" && uv sync)`；不要改变主终端 cwd。

复制只读来源并实际生成 task 0：

```bash
source .local-demo/retail-m1/session.env
cp "$AGENTFIT_TAU3_ROOT/data/tau2/domains/retail/policy.md" "$AGENTFIT_RUN_ROOT/source/"
cp "$AGENTFIT_TAU3_ROOT/data/tau2/domains/retail/tasks.json" "$AGENTFIT_RUN_ROOT/source/"
cp "$AGENTFIT_TAU3_ROOT/data/tau2/domains/retail/split_tasks.json" "$AGENTFIT_RUN_ROOT/source/"
jq 'map(select(.id == "0")) | .[0]' "${AGENTFIT_TAU3_ROOT}/data/tau2/domains/retail/tasks.json" > "${AGENTFIT_RUN_ROOT}/source/task-0.json"
jq -e '.id == "0"' "$AGENTFIT_RUN_ROOT/source/task-0.json"
```

## 5. 复核已完成的 M0 基线

### 5.1 回读 AgentTeams，不猜版本

当前 AgentTeams 新版容器/CLI 通常是 `agentteams-controller` + `agt`，较早安装可能是 `hiclaw-controller` + `hiclaw`。下面自动检测，只读，不改平台：

```bash
source .local-demo/retail-m1/session.env
AGENTTEAMS_CONTROLLER="$(docker ps --format '{{.Names}}' | rg -m1 '^(agentteams|hiclaw)-controller$')"
test -n "$AGENTTEAMS_CONTROLLER"
if docker exec "$AGENTTEAMS_CONTROLLER" sh -c 'command -v agt >/dev/null'; then
  AGENTTEAMS_CLI=agt
else
  AGENTTEAMS_CLI=hiclaw
fi
docker exec "$AGENTTEAMS_CONTROLLER" "$AGENTTEAMS_CLI" version | tee "$AGENTFIT_RUN_ROOT/baseline/agentteams-version.txt"
docker exec "$AGENTTEAMS_CONTROLLER" "$AGENTTEAMS_CLI" status -o json | tee "$AGENTFIT_RUN_ROOT/baseline/agentteams-status.json"
```

如果 `status -o json` 在实际版本不支持，先运行 `... status --help` 并保存帮助，再用该版本支持的格式执行；不要猜参数。版本/状态回读失败时 M0 未完成。

### 5.2 复核授权、入口与边界

当前实例不再创建第二套 M0 模板。唯一证据位于 `.local-demo/agentteams/evidence/`：

- `m0-authorization.md`：授权范围、首个 ProjectCase 和禁止项；
- `baseline.json`：AgentFit/AgentTeams 源码 SHA、v1.1.2 镜像 tag/digest，以及 `known_boundary` 中 CLI 报告 `dev` 的已知边界；
- `version.txt`、`status.json`、`managers.json`、`workers.json`、`teams.json`、`containers.txt`、`endpoints.json`：平台状态；
- `litellm-smoke.json`、`manager-smoke.json`：最小模型与 Manager 消息证据；
- `SHA256SUMS`：完整性清单。

离开 M0 前只做只读复核，不复制、改写或提交这些本地证据：

```bash
sha256sum -c .local-demo/agentteams/evidence/SHA256SUMS
jq -e '.kubeMode == "embedded"' .local-demo/agentteams/evidence/status.json
jq -e '.total == 1 and .managers[0].phase == "Running"' .local-demo/agentteams/evidence/managers.json
jq -e '.status == "PASS"' .local-demo/agentteams/evidence/litellm-smoke.json
jq -e '.status == "PASS" and .mutations_requested == false' .local-demo/agentteams/evidence/manager-smoke.json
```

M0 `READY` 只证明 AgentTeams 底座、模型入口和证据边界可用。当前仍无 Worker、Team、Human 或 Candidate，不能把它写成 M1 或闭环证据。

## 6. 配置模型，不泄漏密钥

τ³-bench 使用 LiteLLM。只在 benchmark 仓库本地创建 `.env`，已有文件绝不覆盖：

```bash
source .local-demo/retail-m1/session.env
test -e "$AGENTFIT_TAU3_ROOT/.env" || cp "$AGENTFIT_TAU3_ROOT/.env.example" "$AGENTFIT_TAU3_ROOT/.env"
chmod 600 "$AGENTFIT_TAU3_ROOT/.env"
git -C "$AGENTFIT_TAU3_ROOT" check-ignore -q .env
```

在编辑器中填写实际 provider key。OpenCode 订阅或 AgentTeams 内已有模型不自动等于 LiteLLM API 凭据。模型 ID 不是密钥，但仍保存在 ignored 本地配置：

```bash
source .local-demo/retail-m1/session.env
printf '%s\n' \
  "export AGENTFIT_AGENT_MODEL='<litellm-agent-model-id>'" \
  "export AGENTFIT_USER_MODEL='<litellm-user-model-id>'" \
  > "$AGENTFIT_RUN_ROOT/model.env"
```

替换占位后，每个新终端执行：

```bash
source .local-demo/retail-m1/session.env
source "$AGENTFIT_RUN_ROOT/model.env"
export AGENTFIT_AGENT_MODEL AGENTFIT_USER_MODEL
test -n "$AGENTFIT_AGENT_MODEL"
test -n "$AGENTFIT_USER_MODEL"
test "$AGENTFIT_AGENT_MODEL" != '<litellm-agent-model-id>'
test "$AGENTFIT_USER_MODEL" != '<litellm-user-model-id>'
```

`.env`、model.env、原始日志和任何 API key 都不得提交。

## 7. τ³-bench 原生 preflight：1 → 3 → 12/20

本节所有结果均标记 `evidence_role: preflight-only`。它们证明 benchmark 工具链能否工作，**不是 AgentFit Candidate**，不能填入正式 `EvaluationRun`/`EvaluationUnit`。

每次运行前恢复变量并开启 pipeline 失败传播：

```bash
source .local-demo/retail-m1/session.env
source "$AGENTFIT_RUN_ROOT/model.env"
export AGENTFIT_AGENT_MODEL AGENTFIT_USER_MODEL
test -n "$AGENTFIT_AGENT_MODEL"
test -n "$AGENTFIT_USER_MODEL"
set -o pipefail
```

### 7.1 一个 smoke：task 0

```bash
(cd "$AGENTFIT_TAU3_ROOT" && uv run tau2 run \
  --domain retail --task-split-name train --task-ids 0 \
  --agent-llm "$AGENTFIT_AGENT_MODEL" --user-llm "$AGENTFIT_USER_MODEL" \
  --num-trials 1 --seed 42 --max-concurrency 1 --timeout 300 \
  --verbose-logs --save-to agentfit-retail-preflight-1) \
  2>&1 | tee "$AGENTFIT_RUN_ROOT/native-runs/logs/preflight-1.log"
test -f "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-1/results.json"
cp -a "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-1" "$AGENTFIT_RUN_ROOT/native-runs/"
```

task 0 是换货场景，适合检查用户识别、订单读取、商品查询、换货动作、状态变化和评价。

### 7.2 三个样本：task 0、1、2

只有 smoke 产出 `results.json` 后才运行：

```bash
(cd "$AGENTFIT_TAU3_ROOT" && uv run tau2 run \
  --domain retail --task-split-name train --task-ids 0 1 2 \
  --agent-llm "$AGENTFIT_AGENT_MODEL" --user-llm "$AGENTFIT_USER_MODEL" \
  --num-trials 1 --seed 42 --max-concurrency 1 --timeout 300 \
  --verbose-logs --save-to agentfit-retail-preflight-3) \
  2>&1 | tee "$AGENTFIT_RUN_ROOT/native-runs/logs/preflight-3.log"
test -f "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-3/results.json"
cp -a "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-3" "$AGENTFIT_RUN_ROOT/native-runs/"
```

task 0/1 输入接近但回退偏好不同；task 2 同时包含商品统计和多物品退货，容易暴露长工具链问题。

### 7.3 十二或二十个样本

前三个无鉴权、限流或工具错误且预算充足时才运行 12；再满足相同条件才扩到 20。两条命令都要沿用上面的 `2>&1 | tee` 日志模式，不能在失败后盲目扩大。

```bash
# 12 个 train IDs
(cd "$AGENTFIT_TAU3_ROOT" && uv run tau2 run --domain retail --task-split-name train \
  --task-ids 0 1 2 3 4 6 7 8 10 11 13 14 \
  --agent-llm "$AGENTFIT_AGENT_MODEL" --user-llm "$AGENTFIT_USER_MODEL" \
  --num-trials 1 --seed 42 --max-concurrency 1 --timeout 300 \
  --save-to agentfit-retail-preflight-12) \
  2>&1 | tee "$AGENTFIT_RUN_ROOT/native-runs/logs/preflight-12.log"
test -f "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-12/results.json"
cp -a "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-12" "$AGENTFIT_RUN_ROOT/native-runs/"

# 20 个 train IDs
(cd "$AGENTFIT_TAU3_ROOT" && uv run tau2 run --domain retail --task-split-name train \
  --task-ids 0 1 2 3 4 6 7 8 10 11 13 14 15 16 19 20 21 22 23 24 \
  --agent-llm "$AGENTFIT_AGENT_MODEL" --user-llm "$AGENTFIT_USER_MODEL" \
  --num-trials 1 --seed 42 --max-concurrency 1 --timeout 300 \
  --save-to agentfit-retail-preflight-20) \
  2>&1 | tee "$AGENTFIT_RUN_ROOT/native-runs/logs/preflight-20.log"
test -f "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-20/results.json"
cp -a "$AGENTFIT_TAU3_ROOT/data/simulations/agentfit-retail-preflight-20" "$AGENTFIT_RUN_ROOT/native-runs/"
```

12/20 只是探索规模，不是统计显著性、正式 adaptation/validation 或 holdout 声明。若只完成 1 或 3 个，也保留真实结果，不补造数据。

## 8. 在 AgentTeams 建立五元元团队

在 AgentTeams Manager 对话中粘贴下面的请求。完整合同见 [`agent-identity.md`](../../competition/2026-08-15/submission/agent-identity.md)。

```text
请创建 AgentFit retail M1 元团队，不修改 AgentTeams 核心：

Team: agentfit-retail-m1
Team Leader identity: EngagementLead
Workers:
1. BusinessEngineer：把来源材料编译为 SampleSemanticSpec、TaskSemanticSpec 和边界清单；不得生成候选。
2. AgentArchitect：只消费已批准且冻结的 Sample/Task/四份 manifest，生成 Candidate；缺任一项必须 BLOCKED。
3. ValidationEngineer：只按已批准 TrialSpec 执行正式 Candidate；preflight 只能作为工具链证据，不得转成 EvaluationRun。
4. GovernanceAuditor：独立检查来源、版本、权限、失败分支和声明边界；post-freeze sealed-holdout outcome consumer = GovernanceAuditor only。

EngagementLead 负责 Intake、阶段推进、Human 门禁与 DeliveryDecision，不代写其他 Worker 责任产物。任何预算扩张、越权读取、高风险动作或合同变化必须由 Human 明确审批。创建完成后只回复 Team/Leader/Worker 状态和房间 ID，不宣称 ProjectCase 已运行。
```

把 Manager 回复、room id 和实际 Worker 状态保存到 `$AGENTFIT_RUN_ROOT/agentteams/`。确认 Team Leader 与四个 Worker 均可见、房间可投递后，再发任务。

## 9. 发起今晚的语义编译与门禁 Demo

附上 `source/policy.md`、`source/task-0.json`、`source/split_tasks.json`、三方版本、M0 文件，以及已有 preflight 结果。发送：

```text
New ProjectCase preparation: agentfit-retail-m1

目标：基于 tau2-bench v1.0.1 retail task 0，生成 Intake、SampleSemanticSpec、TaskSemanticSpec 和 CapabilitySemanticSpec 草案，并判断是否具备进入 Candidate generation 的条件。

边界：
- 官方任务是来源样本；任何新增或变异任务只能标为 AgentFit adaptation/synthetic。
- 公开 test split 不是 sealed holdout；当前四份正式 SampleSetManifest 尚未实例化。
- tau2 preflight 不是 AgentFit Candidate/EvaluationUnit，不得写成 M1 候选运行。
- AgentArchitect 必须在四份 manifest 冻结和 Human 批准前 BLOCKED。
- 当前状态 M1: IN_PROGRESS；M2/M3/M4 均未启动。

顺序：EngagementLead → BusinessEngineer → GovernanceAuditor。只有审计确认前置合同齐全，才允许 AgentArchitect；否则输出 blocked DeliveryDecision，列出缺失证据与一个最小下一步。
```

今晚预期的诚实结果是 `blocked`：缺少四份正式 manifest、隔离访问策略和审批。这个结果不是坏 Demo，它展示 AgentFit 不会把公开 benchmark 预跑包装成有效方案比较。

## 10. 失败/Human 分支

让 EngagementLead 提交一个“允许 AgentArchitect 读取 evaluation criteria 后生成 Candidate”的请求。GovernanceAuditor 应拒绝并记录：

```text
decision: rejected
reason: evaluation-answer leakage
required_action: remove expected-answer access and create a new TrialSpec version
runtime_effect: none
```

另一个门禁是从 3 个 preflight 扩到 20 个或换更贵模型：未经 Human 批准就停止。这里的拒绝只证明治理路径被走过，不证明生产权限隔离已完成。

## 11. M1 何时才可以继续

只有按唯一方案完成下列顺序，才能把**新运行**称为 AgentFit Candidate 证据：

1. BusinessEngineer 定义 SampleSemanticSpec、TaskSemanticSpec 和四份互异、不可变、带版本/哈希/访问策略的 SampleSetManifest；
2. 检查近重复、共享客户/订单/模板等分组泄漏；
3. Human 在候选生成前批准并冻结 Sample/Task 和四份 manifest；
4. AgentArchitect 才生成 Candidate；
5. Human 单独批准 TrialSpec、模型/工具、权限、预算和失败规则；
6. ValidationEngineer 执行一条**新的**正式运行，不能重命名 preflight；
7. GovernanceAuditor 在 Candidate 冻结后独占解析 sealed-holdout outcome；
8. EngagementLead 才能形成 DeliveryDecision。

在真实访问隔离和分布划分设计完成前，不要今晚临时做这一步。

## 12. 本地产物

```text
.local-demo/agentteams/evidence/
├── m0-authorization.md
├── baseline.json
├── version.txt
├── status.json
└── SHA256SUMS

.local-demo/retail-m1/
├── session.env
├── model.env
├── baseline/
│   └── tau2-run-help.txt
├── source/{policy.md,tasks.json,split_tasks.json,task-0.json}
├── native-runs/
│   ├── logs/
│   └── agentfit-retail-preflight-*/
├── dossier/
│   ├── 00-intake.md
│   ├── 01-sample-semantic-spec.json
│   ├── 02-task-semantic-spec.json
│   ├── 03-capability-semantic-spec.json
│   ├── 04-governance-gate.md
│   └── 05-delivery-decision.md
├── agentteams/{manager-creation.txt,room-ids.txt,conversation-export.txt}
└── demo/{shot-list.md,run-summary.md}
```

草案 JSON 至少带 `schema_name`、`version`、`created_at`、`created_by`、`source_refs`、`status`。尚未创建的 Candidate、TrialSpec、manifest、EvaluationRun 和 ExecutionTrace 明确写 `not_instantiated`，不要造哈希、审批或运行记录。

## 13. Demo 录制顺序

控制在 3–5 分钟：

1. 展示三方版本、M0 授权与边界，不显示 `.env`；
2. 展示 retail task 0 的用户目标、policy、工具动作和状态；
3. 展示 τ³ preflight 的真实工具 Trace，并明确标记 `preflight-only`；
4. 展示 EngagementLead → BusinessEngineer → GovernanceAuditor 的委派；
5. 展示 Sample/Task/Capability 草案；
6. 展示 GovernanceAuditor 因 manifest/隔离/审批缺失而阻断 Candidate；
7. 展示答案泄漏或预算扩张拒绝；
8. 展示 `M1: IN_PROGRESS` 和唯一下一门禁。

收尾话术：AgentFit 不证明多 Agent 一定更好；它先阻止无效试验，再用冻结样本、统一预算和审计证据选择刚好够用的方案。

## 14. 可以说 / 不能说

可以说：

- “τ³-bench v1.0.1 retail 有 114 个官方任务，本轮从 train 渐进选择 1/3/12 或 20 个做工具链 preflight。”
- “五元团队在 AgentTeams 完成了当前环境的一次语义编译和治理门禁链。”——仅在真实完成后；
- “AgentFit 拒绝把未冻结、答案可能泄漏的预跑当作候选证据。”

不能说：

- “12/20 个样本就是完整 adaptation、validation 和 sealed holdout。”
- “AgentTeams Worker 执行了 retail 工具。”——除非它确实连接并调用；
- “多 Agent 优于单 Agent。”——M3 未执行；
- “AgentFit 已跑通可复现最小闭环。”——M1 未完成，M4 未执行；
- “官方案例扩写是官方样本。”扩写只能标为 `AgentFit adaptation/synthetic` 并保留 parent source。

## 15. 故障和停止条件

| 症状 | 动作 |
|---|---|
| clone/uv 下载慢 | 重试一次；20 分钟仍失败则保存日志并停止，不换不明来源包 |
| 模型 401/403 | 不显示 key；修正 provider/model 一次，仍失败即停止计费调用 |
| 429/超时 | 并发保持 1，退回 task 0，不扩到 12/20 |
| 无 `results.json` | 本次不算 preflight 证据；保留对应 `2>&1 | tee` 日志 |
| Manager 创建失败/房间不可达 | 重试一次；保留真实失败，不手工伪造委派链 |
| 答案泄漏 | 立即判该轮无效；新建合同版本后才可重跑 |
| 90 分钟仍未完成 smoke | 停止扩大，整理可复现阻塞证据 |
| 达到个人成本上限 | 立即停止；3 个真实样本优于 20 个不可审计样本 |

密钥可能泄漏、版本不能固定、工具状态不能复位、消息不可达、答案泄漏或预算未批准，均为硬停止条件。

## 16. 离开前五分钟检查

```bash
source .local-demo/retail-m1/session.env
git -C "$AGENTFIT_ROOT" status --short --ignored .local-demo/
git -C "$AGENTFIT_TAU3_ROOT" check-ignore -q .env
test -s "$AGENTFIT_TAU3_ROOT/.env"
find "$AGENTFIT_RUN_ROOT" -maxdepth 3 -type f -printf '%P\n' | sort
rg -n '(API_KEY=.+|sk-[A-Za-z0-9]{16,}|Bearer [A-Za-z0-9._-]{20,})' "$AGENTFIT_RUN_ROOT" && echo 'STOP: review possible secret' || true
```

填写 `demo/run-summary.md`：

```text
status: M1 IN_PROGRESS
m0_status: READY
preflight_sample_ids: [实际 IDs]
preflight_result_refs: [results.json 路径]
agentteams_trace_ref: [对话导出路径]
governance_gate: blocked | rejected | not_reached
next_gate: define and approve four immutable manifests with real access isolation
unsupported_claims: Candidate comparison, sealed-holdout result, M1 completion, M2/M3/M4
```

今晚默认不提交 `.local-demo/`。明天只挑选脱敏、来源可追溯、经过审核且比赛确需的派生证据进入仓库。
