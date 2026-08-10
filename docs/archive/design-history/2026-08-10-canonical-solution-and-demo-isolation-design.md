# AgentFit 唯一方案与 Demo 隔离设计记录

状态：已获用户原则批准，等待书面复核后实施。

本文件只记录仓库治理和迁移决策，属于历史设计记录。实施完成后，`docs/agentfit-solution.md` 是唯一有效的整体方案；本文件不得作为另一版方案使用。

## 1. 问题

当前仓库同时包含：

- 整体方法论、证据研究、参赛交付设计和执行计划；
- 一套使用模拟 LLM、手工场景和合成评分的 Python 原型；
- 由该原型生成的 `TEST_REPORT.md`。

模拟原型适合快速演示方法，但不能证明 AgentTeams 集成、真实模型效果、生产可用性或跨项目迁移。若继续与正式实现共同跟踪，容易让实验假设、合成结果和历史方案进入正式事实源。

## 2. 已选方案

采用“唯一正式方案 + 本地 Demo 沙箱”的彻底隔离方式：

1. 创建稳定路径 `docs/agentfit-solution.md`，作为唯一有效的整体方案。
2. 将现有方法论、设计和执行计划移动到归档目录，不再保留多个当前有效版本。
3. 保留证据卡、Registry、比赛要求和候选评分作为内部支撑材料；它们不是独立方案版本。
4. 将现有模拟代码和报告迁入根目录 `demo/`。
5. 在 `.gitignore` 中加入根路径规则 `/demo/`，确保 Demo 不进入版本控制。
6. 正式实现未来仍使用仓库根部的 `src/`、`tests/` 和正式工程配置；不得从 Demo 目录直接发布或导入代码。

未选择的方案：

- 只忽略未来 Demo：无法消除当前模拟代码对正式代码区的污染。
- 独立 Demo 仓库：隔离更强，但当前阶段引入不必要的仓库和同步成本。

## 3. 目标目录

```text
agentfit/
├── docs/
│   ├── agentfit-solution.md
│   ├── internal/
│   │   ├── competition/
│   │   ├── cross-scenario-project-suite/
│   │   └── evidence-research/
│   ├── reference/
│   └── archive/
│       ├── design-history/
│       ├── superseded-design/
│       └── superseded-plans/
├── demo/                         # 本地存在，Git 整体忽略
│   ├── src/
│   ├── tests/
│   ├── run_evaluation.py
│   ├── TEST_REPORT.md
│   └── pyproject.toml
├── src/                          # 正式实现阶段重新创建
├── tests/                        # 正式测试阶段重新创建
└── .gitignore
```

实施迁移后，若正式实现尚未开始，根目录可以暂时不存在 `src/`、`tests/` 和 `pyproject.toml`；不得为了目录外观复制 Demo 占位代码。

## 4. 唯一正式方案的内容边界

`docs/agentfit-solution.md` 必须完整收敛以下内容，而不是简单建立索引：

1. 产品问题、定位和非目标；
2. AgentTeams 与 AgentFit 的职责边界；
3. `TaskSemanticSpec` 和能力语义模型；
4. Agent、Skill、MCP、Memory、通信、Human 和非 LLM 方法的统一候选表示；
5. Agentless、单 Agent、多 Agent 的候选图搜索；
6. 内循环、外循环和跨项目 Meta-learning 的严格边界；
7. 版本化任务目标、预算、安全约束和审批门禁；
8. 评测、Holdout、Trace、审计和失败注入；
9. 元 Agent 团队如何在 AgentTeams 上执行；
10. 项目交付物、成长资产和比赛要求映射；
11. 已批准的 v0 项目集与 `AIOpsLab → ITBench` 迁移假设；
12. 当前证据状态、尚未实现范围和下一阶段门禁。

文档使用稳定文件名，不在当前规范区同时保留 `v1`、日期版或“新版”方案。后续修改通过 Git 历史和文档内的变更记录追踪，而不是复制新版本文件。

## 5. Demo 边界

### 5.1 迁入范围

以下现有内容整体迁入被忽略的 `demo/`：

- `src/agentfit/`
- `tests/`
- `run_evaluation.py`
- `TEST_REPORT.md`
- `pyproject.toml`

这些文件包含模拟 LLM、手工场景、合成评测和演示性推荐，不再作为正式代码、正式测试或比赛结果被 Git 跟踪。

### 5.2 禁止反向污染

- 正式代码不得 import `demo/` 中的模块。
- 正式测试不得读取 Demo 场景作为真实性证据。
- Demo 结果只能标记为本地模拟，不得写成 AgentTeams、真实模型或生产效果。
- Demo 中发现的方法只有经过证据核验、接口定义、正式实现和独立评测后，才能进入正式方案或代码。
- Demo 目录不得保存真实凭据、敏感数据或唯一不可恢复的研究结果；`.gitignore` 不是安全和备份机制。

### 5.3 Git 行为

只添加 `/demo/` 到 `.gitignore` 不足以处理已跟踪文件。实施时必须：

1. 先将现有模拟文件完整保留到本地 `demo/`；
2. 确认文件数量和关键文件存在；
3. 让 Git 记录它们从正式路径删除；
4. 验证 `git check-ignore` 命中 Demo 文件；
5. 验证 `git ls-files demo` 为空。

该操作不删除本地 Demo，但提交后其他克隆不会包含 Demo。需要共享 Demo 时，应使用单独、明确授权的交付方式，而不是重新取消忽略。

## 6. 历史文档治理

以下类别移动到归档：

- 当前 `docs/architecture/agentfit-methodology.md`；
- 当前 `docs/design/` 下的执行设计；
- 当前 `docs/plans/` 下的路线图和 Phase 计划。

`docs/README.md` 只将 `docs/agentfit-solution.md` 标为当前方案。归档入口必须明确说明：历史文件只用于追溯，不是当前实现输入。

以下内容继续保持内部事实源身份：

- 官方比赛要求矩阵和红线清单；
- 12 张来源证据卡及 Evidence Registry；
- `ProjectCase` 契约、v0 评分矩阵、选择理由和 Manifest；
- 官方参赛手册原件。

它们可以被唯一方案引用，但不得各自扩张为新的总体方案。

## 7. 验收标准

实施完成必须同时满足：

1. `docs/agentfit-solution.md` 存在，并完整包含第 4 节列出的十二项内容。
2. `docs/README.md` 只声明这一份当前有效整体方案。
3. 原 architecture、design 和 plans 文档都位于归档目录。
4. 本地 `demo/` 包含迁移前的模拟源代码、场景、运行器、报告和工程配置。
5. `.gitignore` 包含根路径 `/demo/`。
6. `git check-ignore demo/run_evaluation.py` 成功。
7. `git ls-files demo` 无输出。
8. 仓库根部不再存在模拟版 `run_evaluation.py`、`TEST_REPORT.md` 和模拟工程配置。
9. 唯一方案明确声明尚无真实 AgentTeams、真实模型、生产效果或 Meta-learning 验证结果。
10. `git diff --check` 通过，JSON Registry 和 Manifest 仍可解析且引用路径有效。

## 8. 实施边界

本次实施只做仓库隔离、文档收敛和引用修复，不做以下工作：

- 不实现 AgentFit 正式运行时；
- 不开发或完善 Demo；
- 不运行合成 Demo 并更新结果；
- 不创建完整 `ProjectCase`；
- 不接入 AgentTeams、模型、Skill 或 MCP；
- 不修改已批准的 v0 项目选择；
- 不把归档文档删除出 Git 历史。
