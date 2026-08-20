# 阶段 A 预检 · 官网 API 与环境（benchmark-evaluation §5 阶段 A）

- 时间：2026-08-20 · 预算批准：$50（本阶段实际消耗 < $0.01）

## 官网 API 直连（deepseek-v4-flash）

| 检查项 | 结果 |
|---|---|
| 最小调用 | ✅ `https://api.deepseek.com/v1` + `deepseek-v4-flash`，回复正常 |
| tool call | ✅ `finish_reason: tool_calls`，参数正确（get_device_state + user_id） |
| usage 记录 | ✅ prompt/completion/total tokens 可核验 |
| secret 处理 | ✅ 只从本地 .env 读取，未进 Git/日志/本文件 |

## τ²-bench 版本钉住

- ✅ checkout 到正本 commit `fc0055dc4e0a316c3f83133267fbd6faaa770992`（v1.0.1），依赖重装完成

## AgentTeams 平台恢复（含故障复盘）

机器重启后 Docker 停机引发连环故障，按序修复：

1. **Matrix 房间 403**（重启后旧房间状态失效，团队 Failed）
   → 清空 controller 数据卷 `agentfit-agentteams-data`（k8s/Matrix/MinIO 状态整体重置，历史 RunStore 证据在仓库只读保留不受影响）→ 团队恢复 Active 2/2
2. **Manager 崩溃循环**（MinIO mc 签名不匹配）
   → 根因一：manager 启动时把平台域名写入自身 /etc/hosts，旧容器内是失效 IP
   → 根因二：旧 manager 容器以 k8s 模式分支运行（等 URL），重建时缺 `AGENTTEAMS_RUNTIME=k8s` 与 `HOME/-w/HOST_ORIGINAL_HOME` 落到 localhost 分支
   → 修复：按官方安装脚本参数重建容器（env-file + k8s 模式 + 工作目录），顺带把 `AGENTTEAMS_DEFAULT_MODEL` 切为 **deepseek-v4-flash**
3. **镜像拉取 401**：清卷 helper 复用本地 agentteams 镜像绕过 Docker Hub 代理故障

## 当前平台状态

| 组件 | 状态 |
|---|---|
| agentteams-manager | Up，控制台 200，MinIO 同步正常，模型 deepseek-v4-flash |
| agentteams-controller | Up |
| team `agentfit` | Active 2/2（steward 领队 + attributor + architect） |

## 结论

阶段 A 门禁通过：只证明运行条件，不产生效果结论。下一步 = 阶段 B
（telecom 5 题协议 smoke：pilot G0 冻结 → 预指定 5 样本各跑 1 次 →
DeepSeek 官网 API → AgentTeams → τ²-bench → Trace/Episode/RunStore 完整往返验证）。
