# AgentFit 初赛路演稿重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 把首版结构型演示稿重做为 12 页比赛路演稿，用用户反馈示意场景讲清 AgentFit，并加入官网四类案例映射和软件研发案例设计模拟。

**Architecture:** 使用 HTML/CSS 作为 1280×720 布局事实源，由浏览器完成排版，再通过 `html2patch` 编译为 PowerPoint 原生可编辑文本和图形；Python 只负责编排构建、元数据和验证。官网案例拆解单独形成可追溯模拟材料，PPTX 只引用经过核验的摘要；`hands-on-deck` 与 PDF 渲染作为最终视觉门禁。

**Tech Stack:** HTML/CSS、Playwright、`html2patch`、Python 3.11、python-pptx 1.0.2、pypdf、hands-on-deck、LibreOffice、Poppler。

## Global Constraints

- 直接在 `main` 工作，不创建 worktree；该选择已由用户明确批准。
- 保留现有米白、深蓝、青绿、橙色和琥珀色配色。
- 16:9，共 12 页，全部使用原生可编辑文本与图形。
- 使用“用户反馈定位”作为贯穿示意场景。
- 展示官网四个参考方向，并深挖“软件研发全流程协同”。
- 官网来源固定为 `https://goaihz.com/tracks?track=infra`，核验日期为 2026-08-10。
- 官网案例模拟必须标记“设计模拟，非运行证据”。
- 不使用虚构指标、成功率、成本或候选排名。
- 不把本地 `demo/`、历史 AgentTeams smoke test或纸面模拟写成 AgentFit 运行证据。

---

### Task 1: 官方案例设计模拟材料

**Files:**
- Create: `competition/2026-08-15/research/official-case-simulation.md`
- Create: `competition/2026-08-15/research/official-case-simulation.json`

**Interfaces:**
- Consumes: 官网四个参考方向及软件研发全流程描述。
- Produces: 可由 PPT 引用的来源、任务契约、能力、候选和 TrialSpec 摘要。

- [x] **Step 1: 写入官网四方向及原文流程摘要**

记录来源 URL、核验日期和四个方向；软件研发流程必须覆盖多源缺陷/需求聚合、代码定位、修复、测试与发布确认、复盘沉淀。

- [x] **Step 2: 写入 AgentFit 设计模拟**

模拟必须定义 `TaskSemanticSpec` 摘要、能力清单、`C0 Agentless`、`C1 单 Agent`、`C2 多 Agent`、统一预算、Human 发布门禁和 `requires_runtime_trial` 结论。

- [x] **Step 3: 核验模拟边界**

Run:

```bash
rg -n "设计模拟|非运行证据|requires_runtime_trial|Agentless|单 Agent|多 Agent|Human" \
  competition/2026-08-15/research/official-case-simulation.*
```

Expected: 两个文件均包含模拟边界与候选定义，不包含量化成绩。

### Task 2: 新版叙事 RED 门禁

**Files:**
- Modify: `competition/2026-08-15/submission/validate_presentation.py`
- Test: `competition/2026-08-15/submission/agentfit-preliminary-draft.pptx`

**Interfaces:**
- Consumes: 旧版 PPTX。
- Produces: 新版必须包含的故事元素检查。

- [x] **Step 1: 扩展必需内容**

新增检查：`用户反馈定位`、`官网参考案例`、四个官网方向、`软件研发全流程协同`、`设计模拟`、`非运行证据`、`requires_runtime_trial`、官网 URL。

- [x] **Step 2: 对旧版执行验证器并确认失败**

Run:

```bash
/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx
```

Expected: FAIL，明确列出新版叙事元素缺失。

### Task 3: 十二页路演稿重构

**Files:**
- Modify: `competition/2026-08-15/submission/build_presentation.py`
- Create: `competition/2026-08-15/submission/slides/common.css`
- Create: `competition/2026-08-15/submission/slides/01-cover.html` through `12-roadmap.html`
- Modify: `competition/2026-08-15/submission/ppt-outline.md`

**Interfaces:**
- Consumes: `design/presentation-redesign.md` 和官方案例模拟材料。
- Produces: 重设计后的 12 页 PPTX。

- [x] **Step 1: 用 HTML/CSS 重写 12 页正文**

按设计文档的十二页故事线实现路径、泳道、对照轴、责任链和分层系统图；构建脚本批量编译 HTML，并把文档元数据写入最终 PPTX。禁止用整页截图替代可编辑内容。

- [x] **Step 2: 重建并通过内容门禁**

Run:

```bash
/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  competition/2026-08-15/submission/build_presentation.py
/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx
```

Expected: `pptx_pages=12`、`content_checks=PASS`。

### Task 4: PPTX/PDF 视觉与交付门禁

**Files:**
- Rebuild: `competition/2026-08-15/submission/agentfit-preliminary-draft.pptx`
- Rebuild: `competition/2026-08-15/submission/agentfit-preliminary-draft.pdf`
- Modify: `competition/2026-08-15/README.md`

**Interfaces:**
- Consumes: Task 3 的新版 PPTX。
- Produces: 0 个结构问题、12 页 PPTX/PDF和逐页视觉通过记录。

- [x] **Step 1: 运行结构门禁**

Run:

```bash
/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  /home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx inspect --issues
```

Expected: `slides: {}`。

- [x] **Step 2: 渲染 12 页并逐页检查**

检查标题结论性、故事连贯性、正文可读性、页面节奏、文字截断、对齐和来源脚注；发现问题必须回到生成器修改。

- [x] **Step 3: 重新导出 PDF 并验证**

Run:

```bash
soffice --headless --convert-to pdf \
  --outdir competition/2026-08-15/submission \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx

/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python \
  competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pdf
```

Expected: PPTX/PDF 均为 12 页，内容门禁通过。

- [ ] **Step 4: 完整仓库门禁与提交**

运行 `git diff --check`、占位符扫描、敏感信息扫描和 `git status --ignored`；仅提交比赛材料，不提交 `__pycache__`、临时渲染或本地配置，然后推送 `main`。
