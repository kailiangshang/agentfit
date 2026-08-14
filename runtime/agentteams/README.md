# AgentFit × AgentTeams M0/M1 运行入口

本目录是 AgentFit 在 AgentTeams 上启动 M0/M1 的唯一运行入口。当前采用：

- AgentTeams 官方预构建镜像运行控制面、Manager 和 Worker；
- AgentFit 源码承载 Identity、Skill、Schema、适配器和后续试验逻辑；
- Benchmark、场景模拟器、评测与诊断服务从宿主机源码运行，通过 HTTP/MCP 接入；
- LiteLLM OpenAI-compatible API 提供执行、用户模拟、评测和诊断模型；
- 不进行镜像编译，不修改 AgentTeams 核心，不开发独立 UI。

固定版本为 AgentTeams `v1.1.2`。仓库源码用于审计与固定安装脚本，实际运行使用该版本官方镜像。

## 当前状态

- M0：`READY`。2026-08-14 已完成授权、首个 ProjectCase 选择、官方镜像固定、运行状态回读、LiteLLM/Manager smoke、证据密钥扫描与哈希校验。
- M1：`IN_PROGRESS`。`agentfit-retail-m1` Team 已为 `Active`，Team-scoped Human 已为 `Active`，1 个 Leader 和 4 个 Worker 均为 `Running`；ProjectCase、Skill/工具绑定和真实 Candidate 尚未执行。

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

## 2. 在 ignored 文件中配置 LiteLLM

```bash
mkdir -p .local-demo/agentteams
cp runtime/agentteams/private.env.example .local-demo/agentteams/private.env
chmod 600 .local-demo/agentteams/private.env
git check-ignore -q .local-demo/agentteams/private.env
```

只在本地编辑 `.local-demo/agentteams/private.env`。三个逻辑角色以后可以使用不同模型；M0 只配置 AgentTeams Manager 的默认模型，以验证底座。不得把文件内容粘贴到聊天、日志或 Git。

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
runtime/agentteams/apply-manifest.sh \
  --file runtime/agentteams/m1/agentfit-retail-m1.yaml \
  --log-file .local-demo/agentteams/m1/apply-v112.log
```

包装器只调用 Controller 内原生 `agt` 或 `hiclaw apply`，完整输出进入 ignored、`0600` 私密日志，避免 Human 初始密码进入终端。固定 v1.1.2 镜像只提供 `hiclaw`，其 Team Schema 是 `hiclaw.io/v1beta1` 下的 `leader + workers`；当前 AgentTeams `main` 的宿主脚本改用 `agt`，Team Schema 也改成引用独立 Worker CR，不能拿来直接操作本实例。

当前脱敏证据位于 `.local-demo/agentteams/m1/evidence/`，已回读 Team `Active`、Leader ready、4/4 Worker ready、5 个成员的模型/runtime/role、Human `Active`、五份根 SOUL 合同和 SHA-256 完整性。v1.1.2 的 Human 查询不会回显 permissionLevel/accessibleTeams，因此 Human scope 只能由已应用 manifest 与 Active 状态共同证明，不能声称完成了生产级 IAM 验证。

下一步才是向 Team Leader 投递 retail ProjectCase preparation，产生语义草案和预期的治理阻断；Retail/airline 的具体样本与 preflight 操作继续见[回家 Demo 执行手册](../../docs/guides/home-demo-runbook.md)。

在 M1 完成前，准确表述始终是：AgentTeams 底座正在接入，AgentFit 闭环尚未跑通。
