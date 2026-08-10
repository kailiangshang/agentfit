# AgentFit Phase 1 Evidence Foundation Implementation Plan

> 归档状态：该 Phase 1 计划已经完成并退役，不得继续作为执行入口。
>
> 当前唯一方案：[AgentFit 整体方案](../../agentfit-solution.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a traceable evidence registry for twelve cross-domain sources and produce a scored 4–6 project v0 shortlist for user approval.

**Architecture:** Official competition constraints and public sources are normalized into small evidence cards. OpenCode analyzes only fixed source snapshots; a human-verifiable registry and weighted selection matrix determine which projects advance to semantic modeling.

**Tech Stack:** Markdown, JSON, `jq`, `pdftotext`, `curl`, Git, OpenCode 1.18.13, `zhipuai-coding-plan/glm-5.1`.

## Global Constraints

- Do not modify application code or claim runtime implementation progress.
- Use E1/E2/E3/E4 evidence grades defined in the approved design.
- Separate `verified_fact`, `agentfit_inference`, and `open_question` in every card.
- Preserve source title, canonical URL, publication or access date, license, and reproducibility status.
- OpenCode output is a draft extraction, not accepted evidence until citations are checked.
- LLM-centric and non-LLM solution candidates must both remain visible.
- Commit after every task; do not push without user authorization.

---

### Task 1: Create the evidence contracts

**Files:**

- Create: `docs/internal/evidence-research/README.md`
- Create: `docs/internal/evidence-research/evidence-card-template.md`
- Create: `docs/internal/evidence-research/evidence-registry.json`
- Create: `docs/internal/cross-scenario-project-suite/project-case-template.md`
- Create: `docs/internal/cross-scenario-project-suite/v0-manifest.json`
- Modify: `docs/README.md`

**Interfaces:**

- Consumes: evidence levels and `ProjectCase` fields from `docs/design/2026-08-07-agentfit-evidence-and-submission-design.md`.
- Produces: the exact evidence-card contract and project manifest used by Tasks 3–5.

- [ ] **Step 1: Add the evidence-research index**

Create `docs/internal/evidence-research/README.md` with these sections:

```markdown
# Evidence Research

## Purpose
This directory contains source-level evidence used to select and model AgentFit cross-scenario projects.

## Evidence Levels
- E1: production case with identifiable environment and verifiable reported result
- E2: controlled experiment, paper, or public benchmark
- E3: runnable open-source implementation or official reference design
- E4: product description, concept example, or design article

## Claim States
- verified_fact
- agentfit_inference
- open_question

## Acceptance Rule
No external claim enters the normative methodology or competition submission until its source and wording are manually verified.
```

- [ ] **Step 2: Add the evidence-card contract**

Create `docs/internal/evidence-research/evidence-card-template.md` with the following required headings:

```markdown
# Evidence Card Contract

## Identity
- evidence_id
- domain
- source_title
- canonical_url
- publication_or_access_date
- organization_or_authors
- evidence_level
- license

## Verified Facts
- task_input
- expected_output
- reported_roles
- coordination_topology
- tools_and_state
- human_gate
- reported_metrics
- stated_limitations
- reproducibility

## AgentFit Interpretation
- candidate_graph_patterns
- agentize_signals
- non_llm_alternatives
- possible_adaptation_data
- possible_holdout_data
- possible_failure_injection
- transfer_pair_candidates

## Open Questions
- unsupported_claims
- missing_artifacts
- license_or_data_questions

## Provenance
- checked_by
- checked_at
- source_sections
```

- [ ] **Step 3: Add machine-readable registries**

Create `docs/internal/evidence-research/evidence-registry.json`:

```json
{
  "schema_version": "1.0.0",
  "generated_from": "docs/internal/evidence-research/evidence-card-template.md",
  "entries": []
}
```

Create `docs/internal/cross-scenario-project-suite/v0-manifest.json`:

```json
{
  "schema_version": "1.0.0",
  "status": "selection_pending_user_approval",
  "selection_policy": "docs/internal/cross-scenario-project-suite/v0-selection-matrix.md",
  "project_ids": [],
  "transfer_pairs": []
}
```

- [ ] **Step 4: Add the ProjectCase contract**

Create `docs/internal/cross-scenario-project-suite/project-case-template.md` with one required section for each field below and explicitly state that the template is a contract, not a completed case:

```text
source_evidence
raw_materials
task_semantic_spec
capability_semantic_registry
task_capability_alignment
candidate_space
adaptation_set
validation_set
holdout_set
stress_and_failure_set
budgets
safety_constraints
evaluation_protocol
expected_artifacts
provenance_and_license
```

- [ ] **Step 5: Validate and commit**

Run:

```bash
jq empty docs/internal/evidence-research/evidence-registry.json
jq empty docs/internal/cross-scenario-project-suite/v0-manifest.json
git diff --check
```

Expected: all commands exit 0 and print no validation error.

Commit:

```bash
git add docs/README.md docs/internal/evidence-research docs/internal/cross-scenario-project-suite
git commit -m "docs: define AgentFit evidence contracts"
```

### Task 2: Extract the official preliminary-round constraint matrix

**Files:**

- Create: `docs/internal/competition/preliminary-requirements-matrix.md`
- Create: `docs/internal/competition/preliminary-red-line-checklist.md`

**Interfaces:**

- Consumes: `docs/reference/新智基座-参赛手册.pdf` and current methodology.
- Produces: hard constraints and scoring dimensions used by the v0 selection matrix and later submission plans.

- [ ] **Step 1: Extract the official text without changing the repository**

Run:

```bash
mkdir -p /tmp/agentfit-phase1
pdftotext -layout docs/reference/新智基座-参赛手册.pdf /tmp/agentfit-phase1/goai-infra-handbook.txt
rg -n -C 4 "初赛提交|500 字|评审维度|严重扣分|Agent Identity|Skill 清单|不少于 3 个|AgentTeams" /tmp/agentfit-phase1/goai-infra-handbook.txt
```

Expected: output contains the initial submission requirements, five scoring dimensions, Identity and Skill requirements, and red-line section.

- [ ] **Step 2: Write the requirements matrix**

Create `docs/internal/competition/preliminary-requirements-matrix.md` with these rows and exact official weights:

| Dimension | Weight | Required internal evidence |
|---|---:|---|
| 场景价值与行业可复制性 | 25% | real inputs/outputs, baseline, value and transfer rationale |
| 多 Agent 协同与自主闭环 | 25% | at least three identities, full loop, exceptions and AgentTeams mapping |
| Skill 工程体系与生态复用 | 25% | Skill contracts, reuse, version, failure and distribution design |
| 工程落地、运行验证与安全可审计 | 20% | PoC or equivalent evidence, Trace, metrics, permissions, approval and rollback |
| 开放 / 开源贡献 | 5% | open scope, license, dependencies, data and maintenance plan |

Also record the mandatory 500-character introduction, PPT/PDF, AgentTeams design basis, Agent Identity list, Skill list, and optional initial-round code package.

- [ ] **Step 3: Write the red-line checklist**

Create `docs/internal/competition/preliminary-red-line-checklist.md` with explicit checks for:

- concept-only material without PoC, experiment, simulation, trace, video, or equivalent evidence;
- unverifiable or exaggerated AgentTeams integration claims;
- undisclosed existing project foundation or third-party contribution;
- unreported data authorization, commercial API, model, dependency, or license;
- high-risk action without approval, rollback, and audit boundaries;
- competition text that differs from internal evidence status.

- [ ] **Step 4: Run a fixed-source OpenCode audit**

Run:

```bash
opencode run --pure \
  --model zhipuai-coding-plan/glm-5.1 \
  --file docs/architecture/agentfit-methodology.md \
  --file /tmp/agentfit-phase1/goai-infra-handbook.txt \
  -- '只读附件，不修改文件。检查 preliminary requirements matrix 是否漏掉初赛必交物、五项评分权重、Agent Identity、Skill、AgentTeams 基点和严重扣分项。只列遗漏或表述错误；没有问题则输出 MATRIX_OK。'
```

Expected: `MATRIX_OK` or a finite list of source-verifiable corrections. Apply only corrections confirmed in the handbook.

- [ ] **Step 5: Validate and commit**

Run:

```bash
rg -n "25%|20%|5%|500 字|Agent Identity|Skill|AgentTeams|严重扣分" docs/internal/competition
git diff --check
```

Expected: every required term is present and Git reports no whitespace error.

Commit:

```bash
git add docs/internal/competition
git commit -m "docs: capture AgentFit preliminary constraints"
```

### Task 3: Build twelve fixed-source evidence cards

**Files:**

- Create: `docs/internal/evidence-research/cards/software/swe-bench.md`
- Create: `docs/internal/evidence-research/cards/software/masai.md`
- Create: `docs/internal/evidence-research/cards/operations/aiopslab.md`
- Create: `docs/internal/evidence-research/cards/operations/itbench.md`
- Create: `docs/internal/evidence-research/cards/business/tau-bench.md`
- Create: `docs/internal/evidence-research/cards/business/crm-arena.md`
- Create: `docs/internal/evidence-research/cards/research/anthropic-multi-agent-research.md`
- Create: `docs/internal/evidence-research/cards/research/gaia.md`
- Create: `docs/internal/evidence-research/cards/security/cybench.md`
- Create: `docs/internal/evidence-research/cards/security/purple-llama.md`
- Create: `docs/internal/evidence-research/cards/documents/cuad.md`
- Create: `docs/internal/evidence-research/cards/documents/contract-nli.md`
- Modify: `docs/internal/evidence-research/evidence-registry.json`

**Interfaces:**

- Consumes: evidence-card contract from Task 1.
- Produces: twelve checked source cards from six domains and registry entries used by Task 4.

- [ ] **Step 1: Verify the canonical source endpoints**

Run the following command for each URL and require HTTP 200 after redirects:

```bash
for url in \
  https://github.com/SWE-bench/SWE-bench \
  https://arxiv.org/abs/2406.11638 \
  https://github.com/microsoft/AIOpsLab \
  https://github.com/IBM/ITBench \
  https://github.com/sierra-research/tau-bench \
  https://github.com/SalesforceAIResearch/CRMArena \
  https://www.anthropic.com/engineering/multi-agent-research-system \
  https://arxiv.org/abs/2311.12983 \
  https://arxiv.org/abs/2408.08926 \
  https://github.com/meta-llama/PurpleLlama \
  https://github.com/TheAtticusProject/cuad \
  https://stanfordnlp.github.io/contract-nli/
do
  curl -L -I --max-time 20 -s -o /dev/null -w '%{http_code} %{url_effective}\n' "$url"
done
```

Expected: twelve lines beginning with `200`. Record redirected canonical URLs in the cards.

- [ ] **Step 2: Create source snapshots in the temporary directory**

Run:

```bash
mkdir -p /tmp/agentfit-phase1/sources

curl -L https://github.com/SWE-bench/SWE-bench -o /tmp/agentfit-phase1/sources/swe-bench.html
curl -L https://arxiv.org/pdf/2406.11638 -o /tmp/agentfit-phase1/sources/masai.pdf
pdftotext -layout /tmp/agentfit-phase1/sources/masai.pdf /tmp/agentfit-phase1/sources/masai.txt

curl -L https://github.com/microsoft/AIOpsLab -o /tmp/agentfit-phase1/sources/aiopslab.html
curl -L https://github.com/IBM/ITBench -o /tmp/agentfit-phase1/sources/itbench.html

curl -L https://github.com/sierra-research/tau-bench -o /tmp/agentfit-phase1/sources/tau-bench.html
curl -L https://github.com/SalesforceAIResearch/CRMArena -o /tmp/agentfit-phase1/sources/crm-arena.html

curl -L https://www.anthropic.com/engineering/multi-agent-research-system -o /tmp/agentfit-phase1/sources/anthropic-multi-agent-research.html
curl -L https://arxiv.org/pdf/2311.12983 -o /tmp/agentfit-phase1/sources/gaia.pdf
pdftotext -layout /tmp/agentfit-phase1/sources/gaia.pdf /tmp/agentfit-phase1/sources/gaia.txt

curl -L https://arxiv.org/pdf/2408.08926 -o /tmp/agentfit-phase1/sources/cybench.pdf
pdftotext -layout /tmp/agentfit-phase1/sources/cybench.pdf /tmp/agentfit-phase1/sources/cybench.txt
curl -L https://github.com/meta-llama/PurpleLlama -o /tmp/agentfit-phase1/sources/purple-llama.html

curl -L https://github.com/TheAtticusProject/cuad -o /tmp/agentfit-phase1/sources/cuad.html
curl -L https://stanfordnlp.github.io/contract-nli/ -o /tmp/agentfit-phase1/sources/contract-nli.html
```

Do not commit downloaded copies; repository cards retain URLs, section references, and checked dates.

Expected: twelve non-empty attachment-ready HTML or text files plus three retained arXiv PDF files under `/tmp/agentfit-phase1/sources/`.

- [ ] **Step 3: Ask OpenCode to extract fixed-source facts in three batches**

Run the software and operations batch:

```bash
opencode run --pure \
  --model zhipuai-coding-plan/glm-5.1 \
  --file /tmp/agentfit-phase1/sources/swe-bench.html \
  --file /tmp/agentfit-phase1/sources/masai.txt \
  --file /tmp/agentfit-phase1/sources/aiopslab.html \
  --file /tmp/agentfit-phase1/sources/itbench.html \
  -- '只读四份固定来源，不搜索网络，不修改文件。分别抽取：来源身份、证据等级、任务输入、期望输出、报告中的角色和协作方式、工具和状态、人工门禁、明确报告的指标、局限、数据与环境可复现性。然后单独列出 AgentFit 可推断的候选图、Agentize 信号、非 LLM 替代方法和可构造的评测。不得把推断写成来源事实，不得补造指标。'
```

Run the business and research batch with the same prompt and these files:

```bash
opencode run --pure \
  --model zhipuai-coding-plan/glm-5.1 \
  --file /tmp/agentfit-phase1/sources/tau-bench.html \
  --file /tmp/agentfit-phase1/sources/crm-arena.html \
  --file /tmp/agentfit-phase1/sources/anthropic-multi-agent-research.html \
  --file /tmp/agentfit-phase1/sources/gaia.txt \
  -- '只读四份固定来源，不搜索网络，不修改文件。分别抽取：来源身份、证据等级、任务输入、期望输出、报告中的角色和协作方式、工具和状态、人工门禁、明确报告的指标、局限、数据与环境可复现性。然后单独列出 AgentFit 可推断的候选图、Agentize 信号、非 LLM 替代方法和可构造的评测。不得把推断写成来源事实，不得补造指标。'
```

Run the security and documents batch with the same prompt and these files:

```bash
opencode run --pure \
  --model zhipuai-coding-plan/glm-5.1 \
  --file /tmp/agentfit-phase1/sources/cybench.txt \
  --file /tmp/agentfit-phase1/sources/purple-llama.html \
  --file /tmp/agentfit-phase1/sources/cuad.html \
  --file /tmp/agentfit-phase1/sources/contract-nli.html \
  -- '只读四份固定来源，不搜索网络，不修改文件。分别抽取：来源身份、证据等级、任务输入、期望输出、报告中的角色和协作方式、工具和状态、人工门禁、明确报告的指标、局限、数据与环境可复现性。然后单独列出 AgentFit 可推断的候选图、Agentize 信号、非 LLM 替代方法和可构造的评测。不得把推断写成来源事实，不得补造指标。'
```

Expected: four clearly separated records with facts and AgentFit inferences in different sections.

- [ ] **Step 4: Write and manually verify each card**

Create the twelve exact card paths listed above. For every `verified_fact`, locate the corresponding source section before accepting it. If a source does not report roles, metrics, human gates, or production use, write `not_reported_by_source` rather than inferring a value.

- [ ] **Step 5: Populate and validate the registry**

Add twelve objects to `evidence-registry.json`, each with:

```json
{
  "evidence_id": "stable-kebab-case-id",
  "domain": "software|operations|business|research|security|documents",
  "card_path": "docs/internal/evidence-research/cards/domain/card.md",
  "canonical_url": "https://verified-source",
  "evidence_level": "E1|E2|E3|E4",
  "fact_check_status": "checked",
  "reproducibility": "full|partial|scenario_only",
  "license_status": "verified|restricted|unclear"
}
```

Run:

```bash
jq -e '.entries | length == 12' docs/internal/evidence-research/evidence-registry.json
jq -e '[.entries[].domain] | unique | length == 6' docs/internal/evidence-research/evidence-registry.json
jq -e 'all(.entries[]; .fact_check_status == "checked")' docs/internal/evidence-research/evidence-registry.json
```

Expected: all commands print `true` and exit 0.

- [ ] **Step 6: Commit**

```bash
git add docs/internal/evidence-research
git commit -m "docs: add cross-domain AgentFit evidence cards"
```

### Task 4: Score and propose the v0 project shortlist

**Files:**

- Create: `docs/internal/cross-scenario-project-suite/v0-selection-matrix.md`
- Create: `docs/internal/cross-scenario-project-suite/v0-selection-rationale.md`
- Modify: `docs/internal/cross-scenario-project-suite/v0-manifest.json`

**Interfaces:**

- Consumes: twelve checked evidence cards, official preliminary constraints, and the project admission gate.
- Produces: a scored shortlist of 4–6 project IDs and at least one transfer pair for user approval.

- [ ] **Step 1: Create the weighted selection matrix**

Use these fixed criteria and weights:

| Criterion | Weight |
|---|---:|
| Source credibility | 20 |
| Task input/output contract clarity | 15 |
| Ability to distinguish Agentless, single-Agent, and multi-Agent candidates | 20 |
| Evaluation and holdout feasibility | 15 |
| Safety or human-boundary value | 10 |
| Reproducibility, data access, and license | 10 |
| Cross-project transfer value | 10 |

Score every evidence card from 0–5 per criterion. Record both the score and a one-sentence source-backed rationale. Compute weighted totals out of 100.

- [ ] **Step 2: Apply structural coverage constraints**

The shortlist must contain 4–6 projects and collectively cover:

- one task where a fixed Workflow is a serious baseline;
- one task where a local feedback loop or single Agent may be necessary;
- one task where multi-Agent boundaries may be justified;
- one task with a meaningful Human approval or refusal boundary;
- one same-family or adjacent-family transfer pair;
- at least three domains.

Do not select a lower-scoring case only to increase industry count unless it adds a missing structural property.

- [ ] **Step 3: Write the rationale and manifest**

In `v0-selection-rationale.md`, list:

- selected project IDs and their structural role;
- rejected high-profile sources and the evidence-based reason;
- the proposed transfer pair and what transfer claim it can test;
- risks that must be resolved before project modeling.

Update `v0-manifest.json` so that `status` is `proposed_for_user_approval`, `project_ids` contains only IDs present in `evidence-registry.json`, and every transfer-pair source and target is a member of `project_ids`. The transfer hypothesis must name the reusable prior, the expected cold-start benefit, and the condition that holdout performance may not regress.

- [ ] **Step 4: Run consistency checks**

Run:

```bash
jq -e '.project_ids | length >= 4 and length <= 6' docs/internal/cross-scenario-project-suite/v0-manifest.json
jq -e '.transfer_pairs | length >= 1' docs/internal/cross-scenario-project-suite/v0-manifest.json
jq -e '.status == "proposed_for_user_approval"' docs/internal/cross-scenario-project-suite/v0-manifest.json
git diff --check
```

Expected: all `jq` commands print `true`, and Git prints no whitespace error.

- [ ] **Step 5: Commit and stop at the approval gate**

```bash
git add docs/internal/cross-scenario-project-suite
git commit -m "docs: propose AgentFit cross-scenario v0 suite"
```

Report the scoring matrix, selected IDs, transfer pair, known evidence gaps, and commit SHA to the user. Do not create completed `ProjectCase` packages until the user approves the shortlist.

## Phase 1 Final Verification

Run:

```bash
jq -e '.entries | length == 12' docs/internal/evidence-research/evidence-registry.json
jq -e '.project_ids | length >= 4 and length <= 6' docs/internal/cross-scenario-project-suite/v0-manifest.json
rg -L "## Verified Facts" docs/internal/evidence-research/cards/**/*.md
rg -n "内容待定|后续补充|未经核验却声明指标|模拟.*生产" docs/internal
git status --short --branch
```

Expected:

- registry contains twelve checked entries;
- manifest contains 4–6 proposed project IDs;
- `rg -L` prints no card path;
- placeholder and unsupported-claim scan prints nothing;
- worktree is clean and the branch is ahead only by intentional local commits.
