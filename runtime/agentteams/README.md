# AgentFit × AgentTeams M0 运行入口

本目录是 AgentFit 在 AgentTeams 上启动 M0 的唯一操作入口。当前采用：

- AgentTeams 官方预构建镜像运行控制面、Manager 和 Worker；
- AgentFit 源码承载 Identity、Skill、Schema、适配器和后续试验逻辑；
- Benchmark、场景模拟器、评测与诊断服务从宿主机源码运行，通过 HTTP/MCP 接入；
- LiteLLM OpenAI-compatible API 提供执行、用户模拟、评测和诊断模型；
- 不进行镜像编译，不修改 AgentTeams 核心，不开发独立 UI。

固定版本为 AgentTeams `v1.1.2`。仓库源码用于审计与固定安装脚本，实际运行使用该版本官方镜像。

## 当前状态

- M0：`IN_PROGRESS`。启动已获授权，主机与镜像可用性正在冻结；完成状态必须来自安装后的版本和状态回读。
- M1：`NOT_STARTED`。五元团队、Skill、ProjectCase 和真实 Candidate 尚未在 AgentTeams 中执行。

平台预检、历史 smoke 或 Benchmark preflight 都不能替代 M1 证据。

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

脚本强制：

- `AGENTTEAMS_VERSION=v1.1.2`；
- local-only 网络模式；
- `.local-demo/agentteams/platform` 持久化根目录；
- 独立的 `agentfit-agentteams-data` Docker volume，避免复用其他 AgentTeams smoke 数据；
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

根据 `status --help` 使用该版本支持的格式读取状态，保存到 `.local-demo/agentteams/evidence/status.txt`。不猜测不存在的选项。

只有同时满足以下条件，M0 才能从 `IN_PROGRESS` 变为 `READY`：

1. AgentTeams 版本回读为固定版本；
2. Controller、Manager、Matrix、存储与入口处于可用状态；
3. LiteLLM 最小调用通过；
4. 版本、状态、容器和已知边界均已保存；
5. ignored 证据中不存在密钥；
6. 没有把平台可用性写成 AgentFit 闭环证据。

## 5. M0 之后

M0 通过后才执行 M1：用 AgentTeams 原生 Team、Leader、四个 Worker、Human、Skill 和共享存储实例化五元团队，并运行一个冻结 ProjectCase。Retail/airline 的具体样本与 preflight 操作继续见[回家 Demo 执行手册](../../docs/guides/home-demo-runbook.md)。

在 M1 完成前，准确表述始终是：AgentTeams 底座正在接入，AgentFit 闭环尚未跑通。
