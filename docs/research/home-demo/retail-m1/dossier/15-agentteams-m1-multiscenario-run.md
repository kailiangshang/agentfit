# AgentTeams v1.1.2 上的 AgentFit M1 多情景实测

## 结论先行

AgentFit 已在真实 AgentTeams v1.1.2 上完成两轮 ProjectCase preparation：第一轮使用一个官方 retail 样本诊断合同缺口，第二轮同时使用 task 0、2、13 三个官方样本验证改进后的协作和治理顺序。第二轮由 post-run 严格 validator 在显式 legacy prefix override 下验证为 PASS（`terminal_prefix_binding=legacy_cli_only`，`assignment_binding=structured_matrix_mentions_from_raw`，`dossier_identity_binding=legacy_task_meta_and_matrix_assignment`），但证据边界仍是 `M1 PROJECTCASE PREPARATION`：当前 `M1 IN_PROGRESS`，没有 Candidate、TrialSpec、EvaluationRun 或闭环结果。

这次实测证明的不是“多 Agent 一定更好”，而是 AgentFit 能把业务材料批次转成可审计的 Sample/Task/Capability 草案和四类 SampleSetManifest 合同，在前置证据不足时由独立治理角色阻断架构生成。

## 1. 可部署 AgentFit 包

版本化运行包位于 `runtime/agentteams/`：

- `m1/agentfit-retail-m1.yaml`：1 个 EngagementLead、4 个 Worker 和 team-scoped Human 的 AgentTeams 原生声明；
- `apply-manifest.sh`：通过 v1.1.2 Controller 原生 CLI 部署；已有 Human 默认 fail closed，只有核对后显式确认复用才跳过该版本不支持的 Human update；
- `m1/prepare_projectcase.py`：按固定 source schema 选择 benchmark 样本、剥离官方答案/issue 元数据、标注 simulator-only exposure policy，并在发送前生成 0600 输入包与 package provenance；
- `m1/matrix_run.py`：发送前验证 request SHA-256 与 pre-run provenance 一致，再从 Leader DM 发送；分页合并 Team/Leader-DM Trace，按自动生成的 `run_id + 128-bit nonce` token、exact sender、Leader-DM room 和 normalized first line 验证终态，保留结构化 Matrix mentions，并采集累计 token 账本；
- `m1/export_dossier.py`：从 v1.1.2 Leader shared workspace 导出 Project/Business/Governance 工件、收紧权限并生成 artifact hash manifest；
- `m1/validate_run.py`：要求原生 `New task [task_id]` 委派事件，核对 raw/normalized mention 一致性，并验证 Dossier export hash、Project/Task identity、角色顺序、四 manifest 合同、终态边界和答案 payload 结构精确匹配；
- `m1/render_model_manifest.py`：保持 canonical 合同不变，只把 Leader/Worker 模型渲染为家庭 DeepSeek 版本，并生成 0600 hash provenance；
- `README.md`：从部署到证据校验的唯一命令入口。

真实原始输入、Matrix Trace、共享工件和使用量账本保存在 ignored 的 `.local-demo/`，权限为 0600；Git 只保存运行器、合同测试和脱敏结论。

家庭环境只有 Docker 和 DeepSeek API 时，可直接使用 AgentTeams `openai-compat` 连接 `https://api.deepseek.com/v1`，不需要部署 LiteLLM Server。τ³-bench 使用随项目安装的 LiteLLM Python 客户端，以 `deepseek/deepseek-chat` 同时启动执行 Agent 和用户模拟 smoke；完整命令见运行入口与回家手册。

## 2. Trace 与迭代对照

| 观察项 | Round 1：task 0 | Round 2：task 0/2/13 |
|---|---:|---:|
| 入口 | Team Room | Leader DM |
| Matrix message events | 140 | 155 |
| 验证终态时延 | 465.324 秒 | 757.614 秒 |
| BusinessEngineer 消息 | 20 | 33 |
| GovernanceAuditor 消息 | 43 | 35 |
| 未分配 ValidationEngineer 唤醒 | 2 | 0 |
| AgentArchitect 消息 | 0 | 0 |
| 语义 JSON | 3 | 3 |
| 四 manifest 合同 | 缺失 | 4/4，含 16 个 `not_instantiated` 标记 |
| 生命周期最小下一步 | 错误地先 freeze 草案 | 先实例化四 manifest，再 Human freeze |
| 官方 answer payload 结构精确匹配 | 未建立机器门禁 | 0 |
| terminal prefix provenance | 未绑定 | `legacy_cli_only`；旧 `send.json` 未保存 prefix |
| Worker 委派证据 | 未建立机器门禁 | `structured_matrix_mentions_from_raw`；从旧 raw export 恢复 |
| Dossier identity | 未建立机器门禁 | `legacy_task_meta_and_matrix_assignment`；旧轮无 export manifest |
| 最终决策 | BLOCK | BLOCK |

Round 2 的真实事件顺序是：

1. admin 在 Leader DM 发起三样本 ProjectCase；
2. EngagementLead 创建 Project/DAG，只向 BusinessEngineer 分配第一个节点；
3. BusinessEngineer发布三份跨样本语义规格、四份 manifest 合同和 cross-sample analysis；
4. EngagementLead读取工件后，才向 GovernanceAuditor 分配独立审查；
5. GovernanceAuditor按依赖顺序给出 `BLOCK`；
6. EngagementLead汇总到 Leader DM；
7. validator 拒绝错误的旧轮次 marker，Leader只修订 terminal identity，没有重跑 Worker；
8. exact terminal event 通过，结构化验证 PASS。

## 3. 诊断与设计更新

### Round 1 诊断

- Team Room 直接入场会让未分配 Worker 接收环境事件，ValidationEngineer出现 2 条无效消息；
- 三份 JSON 没有把四份 SampleSetManifest 合同作为显式前置；
- GovernanceAuditor曾建议先 Human freeze 语义草案，再实例化 manifests，顺序错误；
- 仅靠 `contains(marker)` 会被请求正文和 tool echo 误触发。

### Round 2 更新与结果

- 改为 Leader DM 入场，再由 Leader 在 Team Room 精确 @mention；非目标 Worker 消息降为 0；
- BusinessEngineer必须先定义 adaptation、validation、sealed_holdout、stress_and_failure 四份合同、成员状态、版本/hash、访问策略和隔离规则；
- GovernanceAuditor必须报告最早缺失前置，最终正确给出“先实例化四 manifest，再 Human freeze”；
- collector 同时使用 exact sender、Leader-DM room、首行归一化、run-bound random token 和 Matrix event；后续 validator 只接受结构化 `m.mentions` 与首行严格匹配的原生 `New task [task_id]` 事件证明 Worker 委派。Round 2 的旧规范化文件未保留 mention 字段，因此 validator 从私有 `conversation.raw.json` 恢复，只有 event ID、sender、timestamp、body、room 五项一对一完全一致才绑定；normalized/raw 冲突、重复 raw identity 和正文/tool echo 均拒绝；
- Round 2 导出发生在 `export-manifest.json` 加固前，因此只以 Project/Business/Governance meta 的交叉 ID、依赖关系和精确 Matrix assignment 形成 `legacy_task_meta_and_matrix_assignment`，不追认 artifact hash binding。新轮次必须同时验证 export manifest 的全文件 SHA-256、shared paths、三份 meta 与当前 Matrix task IDs；
- validator 检查 8 个 Dossier JSON，官方 evaluation criteria 的非空 JSON 容器精确匹配为 0。它不是任意改写文本、标量或对话内容的通用泄漏检测结果。

### 失败分支

第二轮首次 Delivery 仍使用上一轮的 `AGENTFIT-R1-DELIVERY`。这暴露了固定 Matrix 房间/CoPaw session 的跨轮上下文污染。新 collector 没有将其误判完成；一次只针对 terminal identity 的修订产生正确 `AGENTFIT-R2-DELIVERY`，期间 Business/Governance 消息数没有增加。

另有两个 AgentTeams v1.1.2 运行边界已进入部署设计：

- 已存在 Human 不支持 PUT/update，会返回 HTTP 405；包装器现在默认失败，只有操作者显式确认复用后才只更新 Team；
- Leader `SOUL.md` 是 seed-only，可迭代操作规则必须放入 `spec.leader.agents`，且 apply 后要检查运行文件 marker，不能只看旧的 Active 状态。

正式 Candidate 试验前仍应增加“每 Run 独立房间/会话”或等价的 session reset 机制，避免长历史和旧 marker 进入下一轮。

Round 1/2 未保存 pre-run package provenance；现有证据用 request SHA、原始 Matrix event、Dossier 和本地哈希链证明观察结果，但不能证明本轮结束后修订的最终运行包与当时执行字节完全相同。当前运行包已补上发送前 source/policy/manifest/script 哈希和 Dossier export manifest；进入 Candidate 前必须用最终包新开隔离会话重放，不能把后补 provenance 追认到旧轮次。

## 4. 求解路径

当前已经验证到治理阻断的主路径：

> 业务材料 → SourceObservation → TaskSample 批次 → Sample/Task/Capability 语义规格 → 四类 SampleSetManifest 合同 → 实例化 immutable manifests → Human freeze → CandidateVersion → TrialSpec/权限/预算审批 → EvaluationUnit（CandidateVersion × SampleVersion × RunIndex）→ ExecutionTrace → Governance audit → DeliveryDecision

本轮只走到“四类合同 → BLOCK”。后半段保留为显式门禁，而不是用 preflight、历史 mock 或文案补齐。

## 5. 适配路径

接入新行业时不复制整套 Team，只替换和增量更新以下层次：

1. Source adapter：把流程、文档、工单、日志或 benchmark record 映射成 SourceObservation；
2. Sample adapter：定义一个业务事件何时构成一个 TaskSample，并声明 simulator-only、Candidate-visible、auditor-only 边界；
3. Semantic compiler：提取目标、验收、失败、权限和跨样本不变量；
4. Capability mapping：判断差异应该落在 Tool、Skill、Memory、MCP、Agent topology 或 Human boundary；
5. Manifest policy：形成 adaptation、validation、sealed_holdout、stress_and_failure 四类不可变集合；
6. Candidate adapter：只在 Human freeze 后把冻结合同编译成 AgentTeams 可运行的 Identity/Skill/Tool/Team 包；
7. Evaluation adapter：由用户给出质量、成本、时延、风险和复杂度权重，保存 Trace 后做诊断和下一轮更新。

因此，新增 retail/airline/运维/研发场景的主要工作是 source/sample/tool adapter，而不是重写 AgentFit meta-team。

## 6. 成本与时延

Round 1 到验证终态为 465.324 秒。Round 2 首次 Delivery 为 666.109 秒，marker 修订后的验证终态为 757.614 秒。

当前 CoPaw 账本是 M1 团队创建以来的累计值：117 次模型调用、3,459,115 prompt tokens、67,285 completion tokens、合计 3,526,400 tokens。其中 EngagementLead累计 2,267,966 tokens。由于 Round 2 前没有保存 usage snapshot，而且模型价格没有冻结在 TrialSpec 中，不能把累计值冒充第二轮成本，也不能给出可信货币费用。

这个结果本身给出两个诊断：长房间历史与 tool echo 明显放大 Leader prompt；正式试验必须在每轮前后各保存 usage snapshot，并把模型价格版本写入 TrialSpec。运行包已经提供 `usage-snapshot` 支持前后差分。

## 7. 能力边界与下一门禁

已经有证据支持：真实 AgentTeams 委派、三样本批量语义编译、四 manifest 合同、独立审计、错误终态拒绝与恢复、时延和累计 token 观测。

仍然没有证据支持：Candidate 已生成、Tool/Skill/MCP 已绑定运行、用户模拟已执行、EvaluationUnit 已完成、sealed holdout 已建立、闭环已收敛、或多 Agent 优于单 Agent。

最小下一动作仍是：实例化四份独立 immutable SampleSetManifest，补齐 `manifest_version` 和 `content_hash`，然后由 Human 审核并 freeze。没有这个审批，不启动 AgentArchitect 和 ValidationEngineer。

机器可读对照见 [`agentteams-m1-round-comparison.json`](../batch-runs/agentteams-m1-round-comparison.json)。
