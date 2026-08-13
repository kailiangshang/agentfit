# AgentFit 初赛提交工作区

> 内部冻结日：2026-08-15
>
> 官方提交截止：2026-08-16
>
> 当前状态：`READY`。仓库只保留一套最终初赛提交材料。

本目录是 AgentFit 参加 GOAI「新智基座｜Agent Infra」初赛的唯一提交入口。总体方法和事实边界以 [AgentFit 整体方案](../../docs/agentfit-solution.md) 为准；最终材料只位于 [submission/](submission/)。

## 2026-08-15 初赛提交阶段

本阶段只完成、验证并上传以下材料：

| 文件 | 作用 | 当前事实 |
|---|---|---|
| [work-introduction.md](submission/work-introduction.md) | 500 字以内作品简介 | 自动计数门禁 |
| [agentfit-submission.pptx](submission/agentfit-submission.pptx) | 原生可编辑演示稿 | 17 页 |
| [agentfit-submission.pdf](submission/agentfit-submission.pdf) | 同版审阅/上传文件 | 17 页 |
| [contact-sheet.jpg](submission/contact-sheet.jpg) | 17 页整体预览 | 视觉复核入口 |
| [ppt-outline.md](submission/ppt-outline.md) | 内容地图与复现命令 | 12 页主路演 + 5 页附录 |
| [agent-identity.md](submission/agent-identity.md) | 五个元 Agent 的 Identity | 设计契约，未实例化 |
| [skill-catalog.md](submission/skill-catalog.md) | 七个核心 Skill | 设计契约，未绑定 |
| [risk-and-human-gates.md](submission/risk-and-human-gates.md) | Human 门禁、风险与回滚 | 设计契约 |
| [openness-and-compliance.md](submission/openness-and-compliance.md) | 开放、依赖、许可与未实现披露 | 初赛披露 `READY` |

真实 AgentFit 运行不是初赛提交前置条件。OpsPilot baseline 的代码审计和两个事故样本是方案依据，不是 AgentFit 运行证据；ProjectCase、真实五元团队和候选对照仍保持 `requires_runtime_trial`。

## 提交前门禁

1. 作品简介不超过 500 个非空白字符；
2. PPTX/PDF 各 17 页且逐页标题与关键语义一致；
3. PPTX 使用原生可编辑形状，无整页图片、嵌入媒体或转场；
4. 几何无 overlap、overflow 或 off-slide 问题；
5. 四份详细合同与比赛要求、红线和事实状态一致；
6. 联系表和关键页面视觉复核通过；
7. 仓库不存在并行提交版本或过期路径。

## 后续阶段

初赛提交后暂停扩展性开发。是否进入 AgentTeams walking skeleton、复赛工程或跨项目试验，由晋级结果、评审反馈和后续赛程共同决定；未获得新的赛事条件与明确授权前，不把后续设想写成已启动计划。

## 事实优先级

材料冲突时依次使用：官方手册与通知 → 可复现运行证据 → [AgentFit 整体方案](../../docs/agentfit-solution.md) → 比赛要求矩阵与红线 → 最终提交材料。聊天、概念图和历史 smoke test 不能单独证明 AgentFit 已完成运行。
