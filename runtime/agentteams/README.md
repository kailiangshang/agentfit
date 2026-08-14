# AgentFit × AgentTeams M0/M1 运行入口

本目录是 AgentFit 在 AgentTeams 上启动 M0/M1 的唯一运行入口。当前采用：

- AgentTeams 官方预构建镜像运行控制面、Manager 和 Worker；
- AgentFit 源码承载 Identity、Skill、Schema、适配器和后续试验逻辑；
- Benchmark、场景模拟器、评测与诊断服务从宿主机源码运行，通过 HTTP/MCP 接入；
- OpenAI-compatible API 提供执行、用户模拟、评测和诊断模型；可接内部 LiteLLM，也可直连 DeepSeek；
- 不进行镜像编译，不修改 AgentTeams 核心，不开发独立 UI。

固定版本为 AgentTeams `v1.1.2`。仓库源码用于审计与固定安装脚本，实际运行使用该版本官方镜像。

## 当前状态

- M0：`READY`。2026-08-14 已完成授权、首个 ProjectCase 选择、官方镜像固定、运行状态回读、LiteLLM/Manager smoke、证据密钥扫描与哈希校验。
- M1：`IN_PROGRESS`。`agentfit-retail-m1` Team 与 Human 已为 `Active`，1 个 Leader 和 4 个 Worker 均为 `Running`；一个单样本诊断轮和一个三样本 ProjectCase-preparation 轮已经完成，四份 SampleSetManifest 合同仍未实例化或经 Human freeze，Candidate、Skill/工具绑定和 EvaluationRun 尚未执行。

平台预检、历史 smoke 或 Benchmark preflight 都不能替代 M1 证据。

当前固定镜像的 tag 与 digest 均对应 `v1.1.2`；但镜像内 `hiclaw version` 的 Controller CLI 仍报告 `dev`。这是官方镜像构建元数据缺口，已经保存在 ignored 证据中，不把它改写成 CLI 已正确报告 `v1.1.2`。

## 1. 从 AgentFit 仓库根目录预检

```bash
python3 runtime/agentteams/preflight.py \
  --agentteams-repo ../AgentTeams \
  --version v1.1.2 \
  --output .local-demo/agentteams/preflight.json
```

首次运行在没有私密模型配置时会返回非零，并在报告中把三个配置项标为 `missing`。这是预期的配置门禁；报告不会保存 API 值、URL 或模型名。

## 2. 在 ignored 文件中配置模型 API

```bash
mkdir -p .local-demo/agentteams
cp runtime/agentteams/private.env.example .local-demo/agentteams/private.env
chmod 600 .local-demo/agentteams/private.env
git check-ignore -q .local-demo/agentteams/private.env
```

只在本地编辑 `.local-demo/agentteams/private.env`。三个逻辑角色以后可以使用不同模型；M0 只配置 AgentTeams Manager 的默认模型，以验证底座。不得把文件内容粘贴到聊天、日志或 Git。

家里只有 Docker 和 DeepSeek API 时，不需要部署 LiteLLM Server。AgentTeams 的 `openai-compat` 入口可以直接连接 DeepSeek；在编辑器中把私密文件配置为以下逻辑值，真实 key 只写本地文件：

```bash
AGENTTEAMS_LLM_API_KEY='<deepseek-api-key>'
AGENTTEAMS_OPENAI_BASE_URL='https://api.deepseek.com/v1'
AGENTTEAMS_DEFAULT_MODEL='deepseek-chat'
```

安装完成后，Manager 使用 `AGENTTEAMS_DEFAULT_MODEL`；Team manifest 中 Leader/Worker 的 `model` 也必须是该入口可识别的模型 ID。不要改动已经用于办公室实测的 canonical manifest，生成 ignored 的家庭版本：

```bash
mkdir -p .local-demo/agentteams/m1
python3 runtime/agentteams/m1/render_model_manifest.py \
  --input-file runtime/agentteams/m1/agentfit-retail-m1.yaml \
  --output-file .local-demo/agentteams/m1/agentfit-retail-m1.deepseek.yaml \
  --model deepseek-chat

printf "export AGENTFIT_TEAM_MANIFEST='%s'\n" \
  '.local-demo/agentteams/m1/agentfit-retail-m1.deepseek.yaml' \
  > .local-demo/agentteams/m1/manifest.env
source .local-demo/agentteams/m1/manifest.env

test "$(stat -c '%a' .local-demo/agentteams/m1/agentfit-retail-m1.deepseek.yaml)" = 600
git check-ignore -q .local-demo/agentteams/m1/agentfit-retail-m1.deepseek.yaml
```

渲染器只替换 1 个 Leader 和 4 个 Worker 的 `model` 字段，其他 Identity、SOUL、Human 和门禁合同保持一致；旁路 provenance 文件保存 source/rendered/renderer SHA-256，不包含凭据。`deepseek-reasoner` 也可作为显式试验模型，但今晚先以 `deepseek-chat` 建立可复现基线。

配置后先做不产生容器的检查：

```bash
runtime/agentteams/install-prebuilt.sh --check
```

输出只能包含固定版本、运行模式、持久化目录和三个 `configured` 状态。

## 3. 安装官方预构建版本

```bash
runtime/agentteams/install-prebuilt.sh
```

上游安装器的完整输出只写入 `.local-demo/agentteams/install.log` 私密安装日志，文件必须被 Git ignore 且权限为 `0600`；终端只显示成功/失败和日志位置，避免管理员密码、API 地址或其他运行配置进入共享输出。

脚本强制：

- `AGENTTEAMS_VERSION=v1.1.2`；
- local-only 网络模式；
- `.local-demo/agentteams/platform` 持久化根目录；
- 独立的 `agentfit-agentteams-data` Docker volume，避免复用其他 AgentTeams smoke 数据；
- 不启动独立 Dashboard，使用 AgentTeams 自带的 Element/Matrix 入口；
- `openai-compat` 模型入口；
- 禁止任何 `AGENTTEAMS_INSTALL_*_IMAGE` 覆盖。

安装脚本来自相邻且已审阅的 `../AgentTeams/install/agentteams-install.sh`，不会在运行时下载另一份脚本。

## 4. 回读版本与状态

安装完成后先找到控制器，再检测该固定版本实际提供的 CLI 名称：

```bash
mkdir -p .local-demo/agentteams/evidence
AGENTTEAMS_CONTROLLER="$(docker ps --format '{{.Names}}' | rg -m1 '^(agentteams|hiclaw)-controller$')"
test -n "$AGENTTEAMS_CONTROLLER"

if docker exec "$AGENTTEAMS_CONTROLLER" sh -c 'command -v agt >/dev/null'; then
  AGENTTEAMS_CLI=agt
else
  AGENTTEAMS_CLI=hiclaw
fi

docker exec "$AGENTTEAMS_CONTROLLER" "$AGENTTEAMS_CLI" version \
  | tee .local-demo/agentteams/evidence/version.txt
docker exec "$AGENTTEAMS_CONTROLLER" "$AGENTTEAMS_CLI" status --help \
  > .local-demo/agentteams/evidence/status-help.txt
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' \
  > .local-demo/agentteams/evidence/containers.txt
```

根据 `status --help` 使用该版本支持的格式读取状态，保存到 `.local-demo/agentteams/evidence/status.json`。不猜测不存在的选项。

M0 已按以下门禁从 `IN_PROGRESS` 变为 `READY`：

1. Controller 与 Manager 官方镜像的 tag 和 digest 固定为 `v1.1.2`，并保存 CLI 报告 `dev` 的已知边界；
2. Controller、Manager、Matrix、存储与入口处于可用状态；
3. LiteLLM 最小调用通过；
4. 授权、首个 ProjectCase、版本、状态、容器和已知边界均已保存；
5. ignored 证据中不存在密钥；
6. `SHA256SUMS` 可验证证据完整性；
7. 没有把平台可用性写成 AgentFit 闭环证据。

当前实例的唯一 M0 证据目录是 `.local-demo/agentteams/evidence/`。它是本地、ignored、权限为 `0600` 的运行记录，不进入比赛提交目录。

## 5. M1 原生声明与当前边界

当前实例使用 AgentTeams `v1.1.2` 原生 Team-inline 合同：Team 自己声明 1 个 Leader 和 4 个 Worker，再声明一个 team-scoped Human。唯一版本化入口是：

- `runtime/agentteams/m1/agentfit-retail-m1.yaml`
- `runtime/agentteams/apply-manifest.sh`

```bash
python3 -m unittest tests.runtime.test_m1_manifest -v

if test -f .local-demo/agentteams/m1/manifest.env; then
  source .local-demo/agentteams/m1/manifest.env
else
  export AGENTFIT_TEAM_MANIFEST=runtime/agentteams/m1/agentfit-retail-m1.yaml
fi

runtime/agentteams/apply-manifest.sh \
  --file "$AGENTFIT_TEAM_MANIFEST" \
  --log-file .local-demo/agentteams/m1/apply-v112.log \
  --reuse-existing-human
```

家庭 DeepSeek 实例改用上节生成的 ignored manifest：

```bash
runtime/agentteams/apply-manifest.sh \
  --file "$AGENTFIT_TEAM_MANIFEST" \
  --log-file .local-demo/agentteams/m1/apply-deepseek-v112.log
```

全新实例不要附加 `--reuse-existing-human`；只有确认该 Human 是此前由同一 manifest 建立、并核对本地 scope 证据后，重跑才显式附加 `--reuse-existing-human`。Git 只同步代码和脱敏结论，不同步办公室机器的 ignored 容器数据、Matrix 房间或 `.local-demo` 证据；家庭实例必须重新安装、apply 和回读状态。

包装器只调用 Controller 内原生 `agt` 或 `hiclaw apply`，完整输出进入 ignored、`0600` 私密日志，避免 Human 初始密码进入终端。固定 v1.1.2 对已有 Human 不支持 update，GET 又不回显 scope；因此检测到已有 Human 时默认失败，只有操作者先核对原 manifest 和本地证据后显式传入 `--reuse-existing-human`，才会仅更新 Team 并记录复用确认。该确认不是生产 IAM 验证。固定 v1.1.2 镜像只提供 `hiclaw`，其 Team Schema 是 `hiclaw.io/v1beta1` 下的 `leader + workers`；当前 AgentTeams `main` 的宿主脚本改用 `agt`，Team Schema 也改成引用独立 Worker CR，不能拿来直接操作本实例。

当前脱敏证据位于 `.local-demo/agentteams/m1/evidence/`，已回读 Team `Active`、Leader ready、4/4 Worker ready、5 个成员的模型/runtime/role、Human `Active` 和五份根 SOUL 合同。目录内 `SHA256SUMS` 保护的是初始实例化快照；其 manifest 指针对应修改前的版本化文件，不能绑定到 Round 1/2，也不能证明当前 post-run 加固包就是当时执行的字节。新一轮运行前必须由 `prepare_projectcase.py` 重新生成 source/policy/manifest/script provenance。v1.1.2 的 Human 查询不会回显 permissionLevel/accessibleTeams，因此 Human scope 只能由已应用 manifest 与 Active 状态共同证明，不能声称完成了生产级 IAM 验证。

## 6. M1 ProjectCase 可部署运行包

从 AgentFit 根目录创建 ignored、0600 的三样本批次：

```bash
ROUND_DIR=.local-demo/retail-m1/agentteams/round-next
if test -f .local-demo/agentteams/m1/manifest.env; then
  source .local-demo/agentteams/m1/manifest.env
else
  export AGENTFIT_TEAM_MANIFEST=runtime/agentteams/m1/agentfit-retail-m1.yaml
fi

python3 runtime/agentteams/m1/prepare_projectcase.py \
  --tasks-file .local-demo/retail-m1/source/tasks.json \
  --policy-file .local-demo/retail-m1/source/policy.md \
  --task-id 0 --task-id 2 --task-id 13 \
  --run-id retail-next-batch-0-2-13 \
  --manifest-file "$AGENTFIT_TEAM_MANIFEST" \
  --source-version tau2-bench/v1.0.1 \
  --output-dir "$ROUND_DIR"
```

在发送前保存累计 usage，随后从 Leader DM 发起。`team.json` 必须来自当前实例的 `hiclaw get teams ... -o json` 回读，不能手写 room ID：

```bash
python3 runtime/agentteams/m1/matrix_run.py usage-snapshot \
  --team-file .local-demo/agentteams/m1/evidence/team.json \
  --output-file "$ROUND_DIR/usage-before.json"

python3 runtime/agentteams/m1/matrix_run.py send \
  --team-file .local-demo/agentteams/m1/evidence/team.json \
  --request-file "$ROUND_DIR/request.md" \
  --run-id retail-next-batch-0-2-13 \
  --entry-room leader-dm \
  --output-dir "$ROUND_DIR"
```

每次只导出一次并观察 `complete`，不要写一个长时间阻塞的盲等循环：

```bash
python3 runtime/agentteams/m1/matrix_run.py export-once \
  --output-dir "$ROUND_DIR"
```

完成后使用版本限定的导出器从 Leader 的 v1.1.2 shared workspace 复制 Project、Business task 和 Governance task 工件。三个 ID 必须来自本轮 Matrix/taskflow Trace，不得沿用旧轮次；目标目录必须尚不存在：

```bash
PROJECT_ID=retail-next-actual-project-id
BUSINESS_TASK_ID=retail-next-actual-business-task-id
GOVERNANCE_TASK_ID=retail-next-actual-governance-task-id
DOSSIER_DIR=.local-demo/retail-m1/dossier/round-next

python3 runtime/agentteams/m1/export_dossier.py \
  --team-file .local-demo/agentteams/m1/evidence/team.json \
  --project-id "$PROJECT_ID" \
  --business-task-id "$BUSINESS_TASK_ID" \
  --governance-task-id "$GOVERNANCE_TASK_ID" \
  --output-dir "$DOSSIER_DIR"
```

导出器要求三份语义 JSON、四 manifest 合同、治理审查和 Project 状态文件齐全，统一收紧为目录 `0700`/文件 `0600`，并生成 `export-manifest.json` 哈希清单。然后运行证据验证，再保存 usage-after。前后快照相减才是单轮用量；没有冻结价格版本时不得换算货币成本：

```bash
python3 runtime/agentteams/m1/validate_run.py \
  --run-dir "$ROUND_DIR" \
  --dossier-dir "$DOSSIER_DIR" \
  --source-tasks .local-demo/retail-m1/source/tasks.json \
  --task-id 0 --task-id 2 --task-id 13

python3 runtime/agentteams/m1/matrix_run.py usage-snapshot \
  --team-file .local-demo/agentteams/m1/evidence/team.json \
  --output-file "$ROUND_DIR/usage-after.json"
```

新轮次 validator 必须同时得到 `conversation.raw.json` 和 Dossier `export-manifest.json`：它拒绝重复 raw identity、normalized/raw mention 冲突和任意 tool echo，只把 Leader 在 Team Room 发出的精确 `New task [task_id]` 事件视为委派；随后核对 export manifest 全文件 SHA-256、shared paths、Project/Business/Governance meta 与当前 Matrix task IDs。`legacy_cli_only` 与 `legacy_task_meta_and_matrix_assignment` 只用于如实重验 Round 2，不得用于家庭重放或未来 Candidate。

`prepare_projectcase.py` 使用固定 retail v1.0.1 allowlist 拒绝 source schema 漂移，剥离 evaluation/issue 元数据，并在发送前生成 `provenance.json`，固定 source、policy、实际部署的 AgentTeams manifest 和运行脚本 SHA-256；它还自动生成 `run_id + 128-bit nonce` 组成的不可复用 terminal token，调用方不能自行传入通用 R3 marker。`matrix_run.py send` 从 provenance 读取并校验该 token，同时要求待发送 request SHA-256 与 pre-run provenance 完全一致，再写入 send metadata；collector 分页回溯到本轮时间边界，要求 exact Leader sender、Leader-DM room 和归一化首行 token，并保留 Matrix `m.mentions` 用于结构化委派验证。固定房间仍会保留 CoPaw 历史；正式 Candidate 试验前需要每 Run 独立房间/会话或经验证的 session reset。

真实两轮结果与失败恢复见[AgentTeams M1 多情景实测](../../docs/research/home-demo/retail-m1/dossier/15-agentteams-m1-multiscenario-run.md)。Retail/airline 的 benchmark preflight 继续见[回家 Demo 执行手册](../../docs/guides/home-demo-runbook.md)。

下一步是实例化四份 SampleSetManifest、补齐版本/hash，并由 Human freeze；在此之前 AgentArchitect 和 ValidationEngineer保持未分配。

在 M1 完成前，准确表述始终是：AgentTeams 底座正在接入，AgentFit 闭环尚未跑通。
