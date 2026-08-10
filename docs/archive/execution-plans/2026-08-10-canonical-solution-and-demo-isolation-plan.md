# AgentFit Canonical Solution and Demo Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Leave the tracked repository with one canonical AgentFit solution, evidence/reference support, and no tracked simulation Demo, while preserving the existing Demo locally under an ignored root directory.

**Architecture:** `docs/agentfit-solution.md` becomes the only current whole-solution document. Existing methodology, design, and execution-plan files move into explicitly superseded archive directories. The current simulated Python package, scenarios, runner, report, and project configuration move to local `/demo/`, which is ignored and cannot be imported by future formal code.

**Tech Stack:** Markdown, Git, `.gitignore`, shell file operations, `rg`, `jq`.

## Global Constraints

- Work on the current `main` branch as explicitly approved by the user.
- Do not push without separate user authorization.
- Preserve the existing Demo locally; remove it only from tracked formal paths.
- Never copy Demo metrics into the canonical solution as real AgentTeams, real-model, production, or Meta-learning evidence.
- Keep the official competition handbook, requirements matrix, red-line checklist, twelve evidence cards, Evidence Registry, ProjectCase contract, selection matrix, rationale, and v0 Manifest tracked.
- Do not implement the AgentFit runtime, AgentTeams integration, ProjectCases, Skills, MCPs, or Demo improvements in this change.
- Use `docs/agentfit-solution.md` as the only current whole-solution path; do not create dated or `v1` copies.
- Treat archived documents as trace history, not implementation inputs.

---

### Task 1: Isolate the existing simulation Demo from tracked formal code

**Files:**

- Modify: `.gitignore`
- Move locally, then remove from Git tracking: `src/` → `demo/src/`
- Move locally, then remove from Git tracking: `tests/` → `demo/tests/`
- Move locally, then remove from Git tracking: `run_evaluation.py` → `demo/run_evaluation.py`
- Move locally, then remove from Git tracking: `TEST_REPORT.md` → `demo/TEST_REPORT.md`
- Move locally, then remove from Git tracking: `pyproject.toml` → `demo/pyproject.toml`

**Interfaces:**

- Consumes: the currently tracked synthetic pipeline and the approved isolation design.
- Produces: a locally usable but completely ignored `demo/`; later tasks may assume root formal paths no longer contain the simulator.

- [ ] **Step 1: Record and verify the exact source set before moving it**

Run:

```bash
test -d src/agentfit
test -d tests/scenarios
test -f run_evaluation.py
test -f TEST_REPORT.md
test -f pyproject.toml
git ls-files src tests run_evaluation.py TEST_REPORT.md pyproject.toml > /tmp/agentfit-demo-tracked-before.txt
test "$(wc -l < /tmp/agentfit-demo-tracked-before.txt)" -ge 5
```

Expected: every `test` exits 0 and the manifest contains at least the five top-level source groups.

- [ ] **Step 2: Add the root-only Demo ignore rule**

Append this exact documented rule to `.gitignore` using `apply_patch`:

```gitignore

# Local simulation sandbox; never part of the formal AgentFit implementation.
/demo/
```

Run:

```bash
git diff --check -- .gitignore
rg -n '^/demo/$' .gitignore
```

Expected: one `/demo/` rule and no whitespace error.

- [ ] **Step 3: Move the existing simulation locally without deleting its contents**

Run these exact moves after confirming `demo/` does not already exist:

```bash
test ! -e demo
mkdir demo
mv src demo/src
mv tests demo/tests
mv run_evaluation.py demo/run_evaluation.py
mv TEST_REPORT.md demo/TEST_REPORT.md
mv pyproject.toml demo/pyproject.toml
```

Expected: all five destination paths exist and the five original paths do not.

- [ ] **Step 4: Verify local preservation and Git isolation**

Run:

```bash
test -d demo/src/agentfit
test -d demo/tests/scenarios
test -f demo/run_evaluation.py
test -f demo/TEST_REPORT.md
test -f demo/pyproject.toml
git check-ignore -q demo/run_evaluation.py
test -z "$(git ls-files demo)"
test ! -e src
test ! -e tests
test ! -e run_evaluation.py
test ! -e TEST_REPORT.md
test ! -e pyproject.toml
```

Expected: every assertion exits 0. `git status --short` shows tracked deletions at the old paths and no `demo/` entry.

- [ ] **Step 5: Commit the isolation boundary**

Run:

```bash
git add .gitignore
git add -u src tests run_evaluation.py TEST_REPORT.md pyproject.toml
git diff --cached --check
test -z "$(git diff --cached --name-only | rg '^demo/' || true)"
git commit -m "chore: isolate local AgentFit demo"
```

Expected: the commit tracks `.gitignore` plus deletions from formal paths, while all Demo files remain present locally and ignored.

### Task 2: Write the single canonical AgentFit solution

**Files:**

- Create: `docs/agentfit-solution.md`
- Read: `docs/architecture/agentfit-methodology.md`
- Read: `docs/design/2026-08-07-agentfit-evidence-and-submission-design.md`
- Read: `docs/internal/competition/preliminary-requirements-matrix.md`
- Read: `docs/internal/competition/preliminary-red-line-checklist.md`
- Read: `docs/internal/cross-scenario-project-suite/v0-selection-rationale.md`
- Read: `docs/internal/cross-scenario-project-suite/v0-manifest.json`

**Interfaces:**

- Consumes: approved methodology, checked evidence state, competition constraints, and v0 selection results.
- Produces: the only normative whole-solution document used by all later formal design and implementation work.

- [ ] **Step 1: Create the canonical document with the exact normative structure**

Use `apply_patch` to create `docs/agentfit-solution.md` with these exact top-level sections:

```markdown
# AgentFit 整体方案

## 1. 文档地位与当前证据状态
## 2. 问题、定位与非目标
## 3. AgentTeams 与 AgentFit 的系统边界
## 4. 任务语义与能力语义
## 5. 候选图与结构搜索
## 6. 内循环、外循环与 Meta-learning
## 7. 元 Agent 团队及执行流程
## 8. 数据、版本、预算与安全约束
## 9. 评测、Holdout、Trace 与审计
## 10. 项目交付物与成长资产
## 11. v0 跨场景项目集与迁移验证
## 12. 比赛映射与证明责任
## 13. 当前未实现范围与下一门禁
## 14. 规范引用
```

The content must make the following statements normative:

- AgentFit is a meta-team running on AgentTeams that designs and evaluates Agent solutions from task and capability semantics.
- LLMs, embeddings, SVD, clustering, graph algorithms, rules, traditional ML, optimization, and human judgment are implementation options rather than the product definition.
- Candidate search always preserves Agentless, fixed Workflow, single-Agent, and multi-Agent alternatives where applicable.
- An Agent is a persistent decision unit with an objective, private state/context, policy, action boundary, and feedback loop; Skill, MCP, Memory, communication, and Human are separate capability or constraint objects.
- Task objectives, metrics, and acceptance criteria cannot change silently; changes create a new `TaskSemanticSpec` version and restart evaluation.
- Inner-loop improvement optimizes local nodes or SCCs; outer-loop improvement optimizes the whole candidate graph; Meta-learning requires a prior to improve an unseen project without holdout regression.
- Internal evidence is the source of truth; competition summaries are derived views.
- Demo results are local simulations and are excluded from formal evidence.
- The proposed v0 set is `swe-bench`, `aiopslab`, `itbench`, `tau-bench`, `gaia`, and `contract-nli`; the proposed transfer pair is `aiopslab → itbench`.
- No real AgentTeams integration, real-model result, production effect, completed ProjectCase, or Meta-learning result has yet been established.

- [ ] **Step 2: Make the execution and deliverable contracts concrete**

In Sections 7–10, include these exact contract families and their relationships:

```text
RawMaterials
  -> TaskSemanticSpec
  -> CapabilitySemanticRegistry
  -> CandidateGraphSet
  -> EvaluationRunSet
  -> SelectedSolution | RejectionDecision
  -> AgentSolutionPackage
  -> CrossProjectLearningRecord
```

Define `AgentSolutionPackage` as containing at minimum:

```text
task_spec_version
agent_identities
skills_and_mcp_bindings
memory_and_communication_topology
human_approval_and_refusal_gates
permissions_and_side_effects
deployment_manifest
evaluation_protocol_and_results
trace_and_audit_artifacts
rollback_and_failure_handling
provenance_dependencies_and_licenses
```

Expected: a reader can determine inputs, outputs, gates, and evidence obligations without opening an archived design.

- [ ] **Step 3: Validate the canonical document against the approved design**

Run:

```bash
solution=docs/agentfit-solution.md
test -s "$solution"
for heading in \
  '## 1. 文档地位与当前证据状态' \
  '## 3. AgentTeams 与 AgentFit 的系统边界' \
  '## 4. 任务语义与能力语义' \
  '## 5. 候选图与结构搜索' \
  '## 6. 内循环、外循环与 Meta-learning' \
  '## 9. 评测、Holdout、Trace 与审计' \
  '## 11. v0 跨场景项目集与迁移验证' \
  '## 13. 当前未实现范围与下一门禁'; do
  rg -q -F "$heading" "$solution"
done
for term in \
  'TaskSemanticSpec' \
  'CapabilitySemanticRegistry' \
  'Agentless' \
  'AgentSolutionPackage' \
  'AIOpsLab' \
  'ITBench' \
  '尚未'; do
  rg -q -F "$term" "$solution"
done
if rg -n 'TBD|TODO|内容待定|后续补充|模拟结果证明了.*生产|真实 AgentTeams 集成已完成|Meta-learning 已验证' "$solution"; then exit 1; fi
git diff --check -- "$solution"
```

Expected: all required sections and terms exist, the unsupported-claim scan is empty, and Git reports no whitespace error.

- [ ] **Step 4: Commit the canonical solution before retiring its sources**

Run:

```bash
git add docs/agentfit-solution.md
git diff --cached --check
git commit -m "docs: consolidate canonical AgentFit solution"
```

Expected: the canonical solution is independently reviewable before old active paths move.

### Task 3: Retire duplicate active solution paths

**Files:**

- Move: `docs/architecture/agentfit-methodology.md` → `docs/archive/superseded-design/agentfit-methodology.md`
- Move: `docs/design/2026-08-07-agentfit-evidence-and-submission-design.md` → `docs/archive/superseded-design/agentfit-evidence-and-submission-design.md`
- Move: `docs/plans/2026-08-07-agentfit-execution-roadmap.md` → `docs/archive/superseded-plans/agentfit-execution-roadmap.md`
- Move: `docs/plans/2026-08-07-agentfit-phase1-evidence-foundation-plan.md` → `docs/archive/superseded-plans/agentfit-phase1-evidence-foundation-plan.md`
- Modify: `docs/README.md`
- Modify: `docs/archive/design-history/README.md`
- Modify only if references require it: `docs/internal/evidence-research/evidence-registry.json`
- Modify only if references require it: `docs/internal/cross-scenario-project-suite/v0-manifest.json`

**Interfaces:**

- Consumes: the committed canonical solution from Task 2.
- Produces: one current solution entry point and explicit historical locations for superseded material.

- [ ] **Step 1: Move superseded files into explicit archive categories**

Run:

```bash
mkdir -p docs/archive/superseded-design docs/archive/superseded-plans
mv docs/architecture/agentfit-methodology.md docs/archive/superseded-design/agentfit-methodology.md
mv docs/design/2026-08-07-agentfit-evidence-and-submission-design.md docs/archive/superseded-design/agentfit-evidence-and-submission-design.md
mv docs/plans/2026-08-07-agentfit-execution-roadmap.md docs/archive/superseded-plans/agentfit-execution-roadmap.md
mv docs/plans/2026-08-07-agentfit-phase1-evidence-foundation-plan.md docs/archive/superseded-plans/agentfit-phase1-evidence-foundation-plan.md
rmdir docs/architecture docs/design docs/plans
```

Expected: the old active files no longer exist, the four archive files exist, and empty active directories contain no tracked file.

- [ ] **Step 2: Rewrite the documentation index around one current solution**

Use `apply_patch` to make `docs/README.md` contain these categories:

```markdown
# AgentFit 文档

## 唯一当前方案
- `agentfit-solution.md`

## 内部事实与评测依据
- competition requirements and red lines
- evidence research and registry
- cross-scenario ProjectCase contract, selection matrix, rationale, and Manifest

## 原始参考材料
- official competition handbook

## 历史归档
- design history
- superseded designs
- superseded execution plans
```

State explicitly that no other document is a current whole-solution version.

- [ ] **Step 3: Update the archive index and repair live links**

Update `docs/archive/design-history/README.md` so that:

- `docs/agentfit-solution.md` is identified as the only current solution;
- design-history files are historical discussions;
- `superseded-design/` contains retired normative designs;
- `superseded-plans/` contains completed or retired execution plans.

Run:

```bash
if rg -n 'docs/(architecture|design|plans)/|architecture/agentfit-methodology|design/2026-08-07|plans/2026-08-07' docs \
  --glob '!docs/archive/superseded-design/**' \
  --glob '!docs/archive/superseded-plans/**' \
  --glob '!docs/archive/design-history/2026-08-10-canonical-solution-and-demo-isolation-design.md' \
  --glob '!docs/archive/execution-plans/2026-08-10-canonical-solution-and-demo-isolation-plan.md'; then
  exit 1
fi
```

Expected: no live document points to an old active path. Historical command text inside superseded files may retain original paths.

- [ ] **Step 4: Validate retained JSON facts after archival**

Run:

```bash
jq -e '(.entries | length == 12) and all(.entries[]; .fact_check_status == "checked")' docs/internal/evidence-research/evidence-registry.json
jq -e '(.status == "proposed_for_user_approval") and (.project_ids | length == 6) and (.transfer_pairs | length >= 1)' docs/internal/cross-scenario-project-suite/v0-manifest.json
for card in $(jq -r '.entries[].card_path' docs/internal/evidence-research/evidence-registry.json); do test -s "$card"; done
```

Expected: both `jq` commands print `true`, and all twelve registered card paths exist.

- [ ] **Step 5: Commit the documentation retirement**

Run:

```bash
git add -A docs
git diff --cached --check
git commit -m "docs: archive superseded AgentFit designs"
```

Expected: the commit contains the index updates and explicit moves into archive directories, with no new current whole-solution file.

### Task 4: Run the repository-stability gate

**Files:**

- Verify: `.gitignore`
- Verify: `docs/agentfit-solution.md`
- Verify: `docs/README.md`
- Verify: `docs/internal/evidence-research/evidence-registry.json`
- Verify: `docs/internal/cross-scenario-project-suite/v0-manifest.json`
- Verify locally but never track: `demo/`

**Interfaces:**

- Consumes: Tasks 1–3.
- Produces: evidence that the solution/document boundary is stable and the Demo cannot pollute tracked development.

- [ ] **Step 1: Verify the one-solution rule**

Run:

```bash
test -f docs/agentfit-solution.md
test ! -e docs/architecture
test ! -e docs/design
test ! -e docs/plans
test "$(rg -l '唯一当前方案' docs/README.md | wc -l)" -eq 1
rg -q -F 'agentfit-solution.md' docs/README.md
```

Expected: only the stable canonical path is presented as current; no old active solution directory remains.

- [ ] **Step 2: Verify Demo isolation and local preservation**

Run:

```bash
git check-ignore -q demo/run_evaluation.py
test -z "$(git ls-files demo)"
test -d demo/src/agentfit
test -d demo/tests/scenarios
test -f demo/run_evaluation.py
test -f demo/TEST_REPORT.md
test -f demo/pyproject.toml
test ! -e src
test ! -e tests
test ! -e run_evaluation.py
test ! -e TEST_REPORT.md
test ! -e pyproject.toml
```

Expected: Demo exists locally, is ignored, has no tracked files, and no simulator remains in formal root paths.

- [ ] **Step 3: Verify facts, links, claims, and worktree stability**

Run:

```bash
jq empty docs/internal/evidence-research/evidence-registry.json
jq empty docs/internal/cross-scenario-project-suite/v0-manifest.json
for card in $(jq -r '.entries[].card_path' docs/internal/evidence-research/evidence-registry.json); do test -s "$card"; done
if rg -n 'TBD|TODO|内容待定|后续补充|未经核验却声明指标' docs/agentfit-solution.md docs/README.md; then exit 1; fi
if rg -n -i 'SALESFORCE_(USERNAME|PASSWORD|SECURITY_TOKEN)=|crmarenatest|security_token=' docs/internal/evidence-research/cards; then exit 1; fi
git diff --check
test -z "$(git status --porcelain)"
git status --short --branch
```

Expected: JSON parses, cards exist, scans are empty, Git has no whitespace error, worktree is clean, and only the intentional local commits are ahead of `origin/main`.

## Completion Boundary

Completion means the tracked repository contains one canonical solution and its evidence/reference support, while the existing synthetic prototype remains only as an ignored local Demo. It does not mean AgentFit runtime behavior, AgentTeams integration, or competition performance has been implemented or validated.
