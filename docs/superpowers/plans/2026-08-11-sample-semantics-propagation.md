# Sample Semantics Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sample a first-class AgentFit semantic object and propagate the approved definition through the canonical solution, ProjectCase contract, AgentTeams landing design, case simulation, submission contracts, HTML slides, PPTX, and PDF.

**Architecture:** Keep `docs/agentfit-solution.md` as the canonical fact source and derive all competition copy from it. Separate business observations, replayable task samples, and execution episodes; compare candidates only as `CandidateVersion × SampleVersion × RunIndex`. Preserve the HTML-first presentation pipeline and regenerate editable PPTX/PDF artifacts only after all textual contracts pass.

**Tech Stack:** Markdown, JSON, HTML/CSS, Python `unittest`, `python-pptx`, `pypdf`, LibreOffice, Poppler, and the `hands-on-deck` HTML-to-PPTX toolchain.

## Global Constraints

- `Sample` is the smallest business semantic unit independently frozen, replayed, executed, and evaluated under one task contract.
- Keep `SourceObservation`, `TaskSample`, and `Episode` distinct; an Episode is an execution trace, not an input sample.
- Use the approved seven-layer mapping: Sample, Task, Capability, Candidate, Inner Loop, Outer Loop, Cross-project Learning.
- `adaptation`, `validation`, `sealed_holdout`, and `stress_and_failure` are versioned `SampleSetManifest` objects with hashes and access policies.
- Only `GovernanceAuditor` consumes sealed-holdout outcomes after candidates are frozen.
- Public examples and paper simulations remain non-runtime evidence.
- Preserve 12 main slides + 5 appendices and the 500-non-whitespace-character introduction limit.
- Do not add a UI, data-labeling platform, sample generator, cross-project Sample Registry, automatic NAS, or AgentTeams core changes.
- Work in `/home/shangkailiang/workspace/sigen-agent-team/agentfit` on `main`.

## File Map

- Canonical semantics: `docs/agentfit-solution.md`, `docs/internal/contracts/project-case-template.md`.
- Runtime mapping: `competition/2026-08-15/design/agentteams-landing-design.md`.
- Case evidence: `competition/2026-08-15/research/official-case-simulation.md` and `.json`.
- Submission contracts: `agent-identity.md`, `skill-catalog.md`, `risk-and-human-gates.md`, `openness-and-compliance.md`, `work-introduction-draft.md`.
- Roadshow sources: `presentation-redesign.md`, `ppt-outline.md`, slides 04, 06, 07, and 13.
- Validation/artifacts: `test_submission_contract.py`, `validate_presentation.py`, PPTX, PDF, and `readiness-board.md`.

---

### Task 1: Add failing Sample propagation guards

**Files:**
- Modify: `competition/2026-08-15/submission/test_submission_contract.py`
- Modify: `competition/2026-08-15/submission/validate_presentation.py`

**Interfaces:**
- Consumes: active Markdown, JSON, and HTML submission sources.
- Produces: guards requiring Sample terminology in sources and generated PPTX text.

- [ ] **Step 1: Add source paths and JSON support**

Add `import json` and these constants below `VALIDATOR`:

```python
REPO_ROOT = ROOT.parents[2]
SOLUTION = REPO_ROOT / "docs" / "agentfit-solution.md"
PROJECT_CASE = REPO_ROOT / "docs" / "internal" / "contracts" / "project-case-template.md"
LANDING = ROOT.parent / "design" / "agentteams-landing-design.md"
OFFICIAL_CASE_MD = ROOT.parent / "research" / "official-case-simulation.md"
OFFICIAL_CASE_JSON = ROOT.parent / "research" / "official-case-simulation.json"
IDENTITIES = ROOT / "agent-identity.md"
SKILLS = ROOT / "skill-catalog.md"
RISKS = ROOT / "risk-and-human-gates.md"
```

- [ ] **Step 2: Add exact source-level tests**

Add to `SubmissionContractTest`:

```python
def test_sample_semantics_propagates_to_active_sources(self) -> None:
    required_by_file = {
        SOLUTION: ("SampleSemanticSpec", "SampleSetManifest", "TaskSample", "Episode"),
        PROJECT_CASE: ("sample_semantic_spec", "sample_set_manifests", "sealed_holdout"),
        LANDING: ("SampleSemanticSpec", "SampleSetManifest", "SampleEvaluation"),
        OFFICIAL_CASE_MD: ("SourceObservation", "TaskSample", "Episode"),
        IDENTITIES: ("SampleSemanticSpec", "SampleSetManifest"),
        SKILLS: ("SampleSemanticSpec", "SampleSetManifest"),
        RISKS: ("SampleSetManifest", "content_hash"),
    }
    for path, terms in required_by_file.items():
        text = path.read_text(encoding="utf-8")
        for term in terms:
            with self.subTest(path=path.name, term=term):
                self.assertIn(term, text)

def test_sample_case_json_uses_machine_readable_contracts(self) -> None:
    payload = json.loads(OFFICIAL_CASE_JSON.read_text(encoding="utf-8"))
    self.assertIn("sample_semantic_spec", payload)
    self.assertIn("sample_mapping_examples", payload)
    self.assertEqual(
        "design_simulation_not_runtime_evidence", payload["evidence_status"]
    )

def test_slides_make_sample_unit_and_episode_explicit(self) -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(SLIDES_DIR.glob("*.html"))
    )
    for term in ("七层 ML 映射", "同一冻结样本集", "TaskSample", "Episode"):
        with self.subTest(term=term):
            self.assertIn(term, source)
    self.assertNotIn("六层 ML 映射", source)
```

- [ ] **Step 3: Guard generated deck vocabulary**

Add to `REQUIRED_TERMS` in `validate_presentation.py`:

```python
"Sample",
"TaskSample",
"Episode",
"七层 ML 映射",
"同一冻结样本集",
```

Add `"六层 ML 映射"` to `FORBIDDEN_TERMS`.

- [ ] **Step 4: Verify the new tests fail for missing propagation**

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest competition/2026-08-15/submission/test_submission_contract.py -v
```

Expected: existing tests pass; the three new Sample tests fail because active sources are not yet updated.

- [ ] **Step 5: Commit the failing contract**

```bash
git add competition/2026-08-15/submission/test_submission_contract.py \
  competition/2026-08-15/submission/validate_presentation.py
git commit -m "test: require sample semantics in submission"
```

---

### Task 2: Make Sample first-class in canonical semantics

**Files:**
- Modify: `docs/agentfit-solution.md`
- Modify: `docs/internal/contracts/project-case-template.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-08-11-sample-semantics-design.md`.
- Produces: canonical Sample vocabulary for all downstream documents.

- [ ] **Step 1: Introduce the seven-layer mapping**

Rename section 4 to `样本语义、任务语义、能力语义与 Agent 定义`. Change each core-method summary to `样本语义 + 任务语义 + 能力语义 + 受约束的架构搜索 + 统一评测`. Insert the approved L1–L7 table verbatim from the spec.

- [ ] **Step 2: Add object hierarchy and contracts**

Insert:

```text
SourceObservation = 原始业务观察
TaskSample = 当前任务契约下可独立冻结、重放、执行和评价的最小单位
Episode = 固定候选在固定 TaskSample 上的一次完整执行
EvaluationUnit = CandidateVersion × SampleVersion × RunIndex
```

Add complete `SampleSemanticSpec`, `Sample`, `SampleSetManifest`, and `SampleEvaluation` contracts from the approved spec. State that changing from alert-level to incident-level creates new Sample and Task versions.

- [ ] **Step 3: Make TaskSemanticSpec reference Sample semantics**

Use this contract:

```text
TaskSemanticSpec = {
  spec_id, version, objective,
  sample_spec_ref, sample_distribution,
  expected_output, metrics, tradeoffs,
  acceptance_thresholds, aggregation_rules,
  budgets, risk_constraints, failure_costs,
  human_boundaries, evidence_requirements, provenance
}
```

State that examples cannot replace frozen Sample contracts or manifests.

- [ ] **Step 4: Rewrite loops, roles, flow, Dossier, and metrics**

- `BusinessEngineer` outputs all three Sample/Task contracts.
- `ValidationEngineer` emits `SampleEvaluation[]` for adaptation, validation, and failure samples.
- `GovernanceAuditor` alone resolves sealed holdout after candidate freeze.
- The flow begins `RawMaterials + SourceObservations → SampleSemanticSpec + SampleSetManifest → TaskSemanticSpec`.
- `ProjectDossier` stores sample specs, manifests, evaluations, and then aggregate reports.
- Every metric records sample unit, denominator, aggregation, missing samples, and failed samples.
- `Inner Epoch` is one pass over adaptation; `Outer Generation` selects on validation.

- [ ] **Step 5: Rewrite the ProjectCase contract**

Add sections `sample_semantic_spec`, `samples`, and `sample_set_manifests`. Each section must list the exact immutable IDs, snapshots, hashes, boundaries, replay contract, split membership, and access policy from the spec. Rewrite the four split sections as versioned manifest purposes and add `SampleEvaluation[]` to expected artifacts.

- [ ] **Step 6: Verify canonical source coverage**

```bash
rg -n "SourceObservation|TaskSample|SampleSemanticSpec|SampleSetManifest|SampleEvaluation|EvaluationUnit" \
  docs/agentfit-solution.md docs/internal/contracts/project-case-template.md
git diff --check
```

Expected: both documents contain each contract and `git diff --check` is silent.

- [ ] **Step 7: Commit canonical semantics**

```bash
git add docs/agentfit-solution.md docs/internal/contracts/project-case-template.md
git commit -m "docs: make sample semantics first class"
```

---

### Task 3: Propagate Sample contracts into AgentTeams landing and case simulation

**Files:**
- Modify: `competition/2026-08-15/design/agentteams-landing-design.md`
- Modify: `competition/2026-08-15/research/official-case-simulation.md`
- Modify: `competition/2026-08-15/research/official-case-simulation.json`

**Interfaces:**
- Consumes: canonical contracts from Task 2.
- Produces: runtime mapping and non-runtime case examples separating observations, samples, and episodes.

- [ ] **Step 1: Update the AgentTeams mapping and flow**

Map Sample contracts to versioned Project Dossier artifacts in shared storage. Use this flow:

```text
Human 提交材料、SourceObservations 和目标
→ BusinessEngineer 生成 SampleSemanticSpec、SampleSetManifest、TaskSemanticSpec
→ AgentArchitect 生成 Capability Registry、AlignmentReport、CandidateGraphSet
→ Human 批准样本边界、数据划分、TrialSpec、权限和预算
→ ValidationEngineer 生成 SampleEvaluation、EvaluationRun 和 ExecutionTrace
→ GovernanceAuditor 在候选冻结后使用 sealed holdout
→ EngagementLead 交付 DeliveryDecision
```

Add Sample schemas, hashes, duplicate rejection, immutable versions, Candidate × Sample trace references, aggregation, and holdout access control to deterministic-code requirements. Require one frozen manifest and one replayed TaskSample in runtime gates.

- [ ] **Step 2: Add human-readable Sample examples**

Add this section before the selected software case:

```markdown
## 样本单位示例

- 告警分类：一条告警是一个 TaskSample。
- 事故处置：一次完整运维事故是一个 TaskSample，多条告警和日志是 SourceObservation。
- 候选比较：C0、C1、C2 处理同一冻结 TaskSample，各自产生一个 Episode。
```

For software development, define one frozen defect package as a TaskSample. Change the paper trace to include Sample contracts and the next gate to use one frozen SampleSet.

- [ ] **Step 3: Add machine-readable objects to the JSON case**

Insert before `task_semantic_spec`:

```json
"sample_mapping_examples": [
  {"task": "告警分类", "task_sample": "一条告警", "source_observations": ["告警字段和当时可见上下文"]},
  {"task": "事故处置", "task_sample": "一次完整运维事故", "source_observations": ["告警", "日志", "变更记录"]}
],
"sample_semantic_spec": {
  "sample_type": "software-defect-package",
  "sample_level": "task",
  "unit_description": "一个可独立定位、修复和冻结测试的软件缺陷包",
  "temporal_boundary": "只允许使用任务冻结时已经存在的材料",
  "replay_contract": "固定仓库快照、测试策略、模型工具边界和预算",
  "evidence_status": "design_only_no_frozen_samples"
},
"sample_set_manifests": {
  "status": "not_instantiated",
  "required_sets": ["adaptation", "validation", "sealed_holdout", "stress_and_failure"]
}
```

Preserve `design_simulation_not_runtime_evidence` and update the paper trace entry.

- [ ] **Step 4: Validate sources**

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m json.tool competition/2026-08-15/research/official-case-simulation.json >/dev/null
rg -n "SourceObservation|TaskSample|Episode|SampleSemanticSpec|SampleSetManifest|SampleEvaluation" \
  competition/2026-08-15/design/agentteams-landing-design.md \
  competition/2026-08-15/research/official-case-simulation.md \
  competition/2026-08-15/research/official-case-simulation.json
```

Expected: JSON is valid and evidence status remains design-only.

- [ ] **Step 5: Commit runtime mapping and case simulation**

```bash
git add competition/2026-08-15/design/agentteams-landing-design.md \
  competition/2026-08-15/research/official-case-simulation.md \
  competition/2026-08-15/research/official-case-simulation.json
git commit -m "docs: map samples into AgentTeams trial design"
```

---

### Task 4: Update submission contracts and narrative

**Files:**
- Modify: `competition/2026-08-15/design/presentation-redesign.md`
- Modify: `competition/2026-08-15/submission/ppt-outline.md`
- Modify: `competition/2026-08-15/submission/agent-identity.md`
- Modify: `competition/2026-08-15/submission/skill-catalog.md`
- Modify: `competition/2026-08-15/submission/risk-and-human-gates.md`
- Modify: `competition/2026-08-15/submission/openness-and-compliance.md`
- Modify: `competition/2026-08-15/submission/work-introduction-draft.md`

**Interfaces:**
- Consumes: canonical definitions and landing flow.
- Produces: competition-facing contracts consistent with the Sample layer.

- [ ] **Step 1: Update roadshow narrative and outline**

Use the five-part method `样本语义 + 任务语义 + 能力语义 + 受约束的 Agent Architecture Search + 统一评测`. Page 4 compiles Sample then Task; page 6 shares a frozen SampleSet; page 7 assigns Sample contracts and Episodes; A1 becomes seven layers. Mirror the same wording in `ppt-outline.md`.

- [ ] **Step 2: Update Agent responsibilities**

- `EngagementLead`: approval for sample unit, split, authorization, budget, and risk.
- `BusinessEngineer`: `SampleSemanticSpec`, `SampleSetManifest`, `TaskSemanticSpec`.
- `AgentArchitect`: sees Sample contracts and distribution summaries, never sealed-holdout content.
- `ValidationEngineer`: adaptation/validation/failure only; emits `SampleEvaluation`, Episode, Step traces.
- `GovernanceAuditor`: sealed holdout only after freeze; feedback invalidates the round.

- [ ] **Step 3: Update the seven Skills without adding an eighth**

S1 inputs become `项目简报、原始材料、SourceObservation、验收目标、约束条件`; outputs become all three Sample/Task contracts. S3 consumes Sample contracts. S4 consumes `CandidateGraphSet + SampleSetManifest + TrialSpec` and emits per-sample evaluation and traces. S5 exclusively resolves sealed holdout. Context becomes `样本语义 + 任务语义 + 能力语义 + ExecutionTrace`.

- [ ] **Step 4: Add freeze, contamination, and openness contracts**

Add a sample-freeze Human gate. Require unit, grouping, cutoff, split, policy, and hash approval. Rewrite R6 around immutable manifests, incident-group leakage, duplicate `content_hash`, run invalidation, and rollback to the last clean manifest. In openness disclosures add planned `SampleSemanticSpec`, `SampleSetManifest`, `SampleEvaluation`, and split-leakage schemas without claiming implementation.

- [ ] **Step 5: Replace the public introduction paragraph**

Use:

```text
AgentFit 是运行在 AgentTeams 上的 Agent 方案建筑师。它先从材料中定义可重放、可验收的业务样本，再编译含输入、输出、指标、预算、风险和 Human 边界的任务语义，然后把模型、规则、Skill、MCP、工具、记忆与人工编译为能力语义，生成 Agentless、单 Agent、多 Agent和人工混合候选，让它们在同一冻结样本集、预算、安全门禁和验收线下比较，以最小复杂度选择合格方案。
```

- [ ] **Step 6: Re-run the contract test**

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest competition/2026-08-15/submission/test_submission_contract.py -v
```

Expected: introduction limit passes; only not-yet-updated slide assertions may fail.

- [ ] **Step 7: Commit submission text**

```bash
git add competition/2026-08-15/design/presentation-redesign.md \
  competition/2026-08-15/submission/ppt-outline.md \
  competition/2026-08-15/submission/agent-identity.md \
  competition/2026-08-15/submission/skill-catalog.md \
  competition/2026-08-15/submission/risk-and-human-gates.md \
  competition/2026-08-15/submission/openness-and-compliance.md \
  competition/2026-08-15/submission/work-introduction-draft.md
git commit -m "docs: propagate sample contracts through submission"
```

---

### Task 5: Redesign the four affected HTML slides

**Files:**
- Modify: `competition/2026-08-15/submission/slides/04-compiler.html`
- Modify: `competition/2026-08-15/submission/slides/06-software-dev.html`
- Modify: `competition/2026-08-15/submission/slides/07-trialspec.html`
- Modify: `competition/2026-08-15/submission/slides/13-a1-ml-mapping.html`

**Interfaces:**
- Consumes: frozen wording and existing `common.css`.
- Produces: strict 1280×720 HTML compiled to native PowerPoint shapes.

- [ ] **Step 1: Read slide-design constraints**

```bash
sed -n '1,360p' /home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/designing-slides.md
```

Keep the palette, page count, and native-shape approach; add no transitions or whole-slide images.

- [ ] **Step 2: Update slide 4**

First card copy becomes `先定义可重放样本，再编译任务语义：样本单位、输入、输出、指标与 Human 边界。`; its pill becomes `产物：样本契约 + 任务说明书`. The third card says `让不同候选在同一冻结样本集、预算、指标和安全线下公平赛跑。`.

- [ ] **Step 3: Update slide 6**

Subtitle becomes `候选共享同一冻结样本集；复杂度本身也是成本。`. First card title becomes `同一冻结样本集`; its four lines are `相同 TaskSample / 相同模型与工具边界 / 相同预算 / 相同安全门禁`.

- [ ] **Step 4: Update slide 7**

Use `定义样本与任务 / 产物：样本契约 + 任务说明书` for `BusinessEngineer`, `按 TaskSample 执行 / 产物：Episode + Trace` for `ValidationEngineer`, and `同一项目档案 · 每个样本可重放 · 每次执行有 Episode · 每次决策有 Trace` in the bottom panel.

- [ ] **Step 5: Convert A1 to seven layers**

Title: `七层 ML 映射把“方案设计”变成可优化对象`; label: `SEVEN-LAYER MAPPING`. Use 17px rows at y positions `254, 296, 338, 380, 422, 464, 506`:

```text
L1 样本语义 → 样本单位、边界、重放与标注契约
L2 任务语义 → 分布、输出、指标、损失与权衡
L3 能力语义 → 算子集、契约、权限与适用域
L4 候选表示 → 结构、分区、参数与共享范围
L5 内循环 → adaptation samples 上优化局部参数
L6 外循环 → validation samples 上比较候选架构
L7 跨项目学习 → 未见项目验证后更新搜索先验
```

Amber note: `L7 是未来方向：单项目样本优化不能证明跨项目学习。`. Inner body: `固定 G / Π；更新 θ / ρ；遍历 adaptation samples`. Outer body: `更新 G / Π；比较 validation samples；保留 Pareto 候选`. Footer: `AGENTFIT · SAMPLE × TASK × CAPABILITY × SEARCH`.

- [ ] **Step 6: Run source tests and strict compilation**

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest competition/2026-08-15/submission/test_submission_contract.py -v
"$PY" competition/2026-08-15/submission/build_presentation.py
```

Expected: source tests pass and strict compilation reports the generated PPTX without overflow errors.

- [ ] **Step 7: Commit HTML only**

```bash
git add competition/2026-08-15/submission/slides/04-compiler.html \
  competition/2026-08-15/submission/slides/06-software-dev.html \
  competition/2026-08-15/submission/slides/07-trialspec.html \
  competition/2026-08-15/submission/slides/13-a1-ml-mapping.html
git commit -m "feat: show sample semantics in roadshow"
```

Leave generated binaries unstaged for Task 6.

---

### Task 6: Regenerate and visually verify PPTX/PDF

**Files:**
- Modify: `competition/2026-08-15/submission/agentfit-preliminary-draft.pptx`
- Modify: `competition/2026-08-15/submission/agentfit-preliminary-draft.pdf`

**Interfaces:**
- Consumes: all 17 HTML slides.
- Produces: editable 17-slide PPTX and equivalent 17-page PDF.

- [ ] **Step 1: Regenerate both artifacts**

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" competition/2026-08-15/submission/build_presentation.py
soffice --headless --convert-to pdf \
  --outdir competition/2026-08-15/submission \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx
```

- [ ] **Step 2: Run content and geometry validation**

```bash
DECK=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py
"$PY" competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pdf
"$PY" "$DECK" competition/2026-08-15/submission/agentfit-preliminary-draft.pptx inspect --issues
```

Expected: `pptx_pages=17`, `pdf_pages=17`, `content_checks=PASS`, and no unresolved clipping or covered display text on slides 4, 6, 7, or A1.

- [ ] **Step 3: Render changed slides**

```bash
RENDER_DIR=/tmp/agentfit-sample-semantics-render
rm -rf "$RENDER_DIR"
mkdir -p "$RENDER_DIR"
"$PY" "$DECK" competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  render -o "$RENDER_DIR" --slide 3,5,6,12
```

Review `slide-3.jpg`, `slide-5.jpg`, `slide-6.jpg`, and `slide-12.jpg` in two small batches for hierarchy, wrapping, alignment, contrast, and legibility.

- [ ] **Step 4: Inspect native shape structure**

```bash
for slide in 3 5 6 12; do
  "$PY" "$DECK" competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
    inspect --slide "$slide" --brief
done
```

Expected: all text is editable; no whole-slide image replaces content. If defects exist, fix HTML and repeat Steps 1–4.

- [ ] **Step 5: Commit generated artifacts**

```bash
git add competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pdf
git commit -m "docs: rebuild sample-aware submission deck"
```

---

### Task 7: Reconcile readiness and run the final evidence gate

**Files:**
- Modify: `competition/2026-08-15/planning/readiness-board.md`
- Modify if necessary: `competition/2026-08-15/README.md`

**Interfaces:**
- Consumes: all updated sources and artifacts.
- Produces: one consistent, evidence-backed repository state.

- [ ] **Step 1: Measure the final introduction**

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" - <<'PY'
import re
from pathlib import Path
text = Path("competition/2026-08-15/submission/work-introduction-draft.md").read_text(encoding="utf-8")
body = re.search(
    r"^## 500 字以内作品简介\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
    text,
    flags=re.MULTILINE | re.DOTALL,
).group("body")
print(len(re.sub(r"\s+", "", body)))
PY
```

Expected: integer `<= 500`.

- [ ] **Step 2: Update readiness without changing runtime claims**

Record the measured character count, first-class Sample design, and rebuilt 17-page artifacts. Keep ProjectCase, real AgentTeams meta-team, and real candidate comparison at `NOT_STARTED`; retain “真实运行证据仍待补”. Update `competition/2026-08-15/README.md` only if it contains the old count or six-layer wording.

- [ ] **Step 3: Run complete validation**

```bash
"$PY" -m unittest competition/2026-08-15/submission/test_submission_contract.py -v
"$PY" competition/2026-08-15/submission/validate_presentation.py \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pptx \
  competition/2026-08-15/submission/agentfit-preliminary-draft.pdf
git diff --check
! rg -n "TO[D]O|TB[D]|PLACEHOLD[E]R" docs/agentfit-solution.md \
  docs/internal/contracts/project-case-template.md competition/2026-08-15
! rg -n "六层 ML 映射|相同输入" competition/2026-08-15/design competition/2026-08-15/submission
rg -n "真实运行证据仍待补|design_simulation_not_runtime_evidence|非运行证据" competition/2026-08-15
```

Expected: tests and validators pass; no placeholders or stale active wording; evidence-boundary terms remain.

- [ ] **Step 4: Commit readiness reconciliation**

```bash
git add competition/2026-08-15/planning/readiness-board.md
if ! git diff --quiet -- competition/2026-08-15/README.md; then
  git add competition/2026-08-15/README.md
fi
git commit -m "docs: reconcile sample-aware submission status"
```

- [ ] **Step 5: Verify final scope and clean state**

```bash
git status --short --branch
git log -10 --oneline --decorate
```

Expected: clean worktree; no AgentTeams code, credentials, local renders, or temporary files tracked; `main` remains ahead of `origin/main` until explicitly pushed.
