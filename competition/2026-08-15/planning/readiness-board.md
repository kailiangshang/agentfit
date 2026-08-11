# 2026-08-15 初赛准备看板

> 状态值仅使用：`READY`、`IN_PROGRESS`、`BLOCKED`、`NOT_STARTED`、`NOT_REQUIRED`。
>
> `READY` 必须有仓库文件或可复现证据；真实运行不是冻结初赛方案的前置条件。

## 1. 当前状态

| 工作项 | 状态 | 证据或边界 |
|---|---|---|
| AgentFit 唯一总体方案 | READY | `docs/agentfit-solution.md` |
| 初赛要求矩阵与红线 | READY | `docs/internal/competition/` |
| 路演唯一叙事与 12+5 结构 | READY | `competition/2026-08-15/design/presentation-redesign.md` |
| AgentTeams 落地边界 | READY | `design/agentteams-landing-design.md`；设计基点，不代表已集成 |
| 官网参考案例与软件研发设计模拟 | READY | `research/official-case-simulation.md`；非运行证据 |
| 五个 Agent Identity | READY | `submission/agent-identity.md`；设计契约 |
| 七个核心 Skill | READY | `submission/skill-catalog.md`；设计契约 |
| Human、风险、异常与回滚 | READY | `submission/risk-and-human-gates.md`；设计契约 |
| 开放与合规披露 | READY | `submission/openness-and-compliance.md`；仓库私有、License 未选择 |
| 500 字作品简介 | READY | `submission/work-introduction-draft.md`；468 个非空白字符 |
| 17 页 HTML / PPTX / PDF | READY | 17 页；内容、几何、PPTX/PDF 逐页视觉与一致性复核通过 |
| 首个正式 ProjectCase | NOT_STARTED | 尚未冻结真实任务、数据和预算 |
| AgentFit 真实 AgentTeams 元团队 | NOT_STARTED | 历史 smoke test 只证明平台能力 |
| 真实候选对照评测 | NOT_STARTED | 无冻结 ProjectCase |
| 初赛可选代码包 | NOT_REQUIRED | 未达到干净环境可复现门禁时不提交 |

## 2. 8 月 15 日前唯一关键路径

```text
完成 17 页逐页视觉复核
→ 修复事实、字号、裁切与一致性问题
→ 运行页数 / 内容 / 几何 / 隐私 / Git 红线
→ 冻结简介 + PPTX + PDF
→ 上传前再次核对文件可打开与页数
```

ProjectCase、真实元团队和候选对照可以在初赛后继续，不得阻塞方案冻结，也不得在初赛材料中伪装成已完成。

## 3. 提交门禁

必交材料只有在下列条件全部满足后才可标记 `READY`：

1. 简介不超过 500 个非空白字符；
2. HTML、PPTX、PDF 均为 17 页且页序一致；
3. PPTX 使用原生可编辑形状与文本；
4. 严格 HTML 编译无警告，PPTX 几何检查无问题；
5. PPTX 与 PDF 完成逐页视觉检查；
6. 无虚构指标、过期引用、错误完成态、敏感配置或本地截图；
7. 场景、Agent、协同、Skill、MCP、上下文、验证、安全和开放要求均可定位；
8. 仓库私有与 License 未选择的事实已披露；
9. 第 11 页明确写出“真实运行证据仍待补”。

## 4. 初赛后运行门禁

只有首个 ProjectCase、五元团队、至少一个真实候选、一个失败/降级分支、独立审计 Trace、固定 AgentTeams 版本和干净环境复现全部完成，才可把第 11 页替换为真实运行证据。
