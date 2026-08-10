# AgentFit Evidence-to-Submission Execution Roadmap

> 归档状态：该路线图已被当前唯一方案取代，不得继续作为执行入口。
>
> 当前唯一方案：[AgentFit 整体方案](../../agentfit-solution.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved AgentFit methodology into an evidence-backed cross-scenario project suite, governed meta-agent growth mechanism, internal solution dossier, and competition-ready preliminary submission.

**Architecture:** Work proceeds through five gated phases. Each phase produces reviewable evidence or documents that become immutable inputs to the next phase; the competition submission is derived from the internal source of truth rather than authored independently.

**Tech Stack:** Markdown, JSON, `jq`, `pdftotext`, `curl`, Git, OpenCode 1.18.13 with `zhipuai-coding-plan/glm-5.1`, AgentFit Semantic IR, AgentTeams design contracts.

## Global Constraints

- LLM is one implementation operator; rules, Embedding, SVD, graph algorithms, optimization methods, statistics, and human review remain first-class alternatives.
- Original evidence, semantic representation, task contract, and candidate solution are distinct versioned objects.
- A task objective or acceptance threshold may not change silently; changing it creates a new `TaskSemanticSpec` version and restarts evaluation.
- OpenCode may extract and compare fixed sources, but every external claim requires a human-verifiable citation.
- Production cases, controlled experiments, open-source implementations, and concept examples must remain visibly separated.
- Internal documents are the single source of truth; submission documents may only compress verified internal claims.
- No simulated result may be described as real AgentTeams runtime evidence.
- Each phase ends at an explicit user approval gate.

---

## Phase Map

| Phase | Deliverable | Entry condition | Exit gate |
|---|---|---|---|
| 1. Evidence foundation | Evidence Registry, 12 source cards, scored v0 shortlist | Approved design `51c940b` | User approves 4–6 project IDs and source quality |
| 2. Project modeling | Complete `ProjectCase` packages and Semantic Compile / Agentize / Inner–Outer protocols | Phase 1 shortlist approved | At least two structurally different cases compile under the same protocols |
| 3. Growth validation | ProjectAsset and MetaAsset protocols applied to a transfer pair | Phase 2 project packages approved | Transfer is compared against no-prior baseline with leakage and negative-transfer checks |
| 4. Internal dossier | Complete internal solution, AgentTeams mapping, evaluation and governance | Phase 3 evidence approved | All claims trace to evidence, decision, experiment, or explicit future plan |
| 5. Preliminary submission | 500-character introduction, deck, identities, skills, evidence summary, demo story and Q&A | Phase 4 dossier approved | Red-line audit passes and every completion claim has an internal evidence pointer |

## Plan Decomposition

The approved design spans several independently reviewable systems. Do not execute it as one undifferentiated task.

1. Execute [Phase 1: Evidence Foundation and v0 Selection](2026-08-07-agentfit-phase1-evidence-foundation-plan.md).
2. After the user approves the exact v0 project IDs, write `docs/plans/2026-08-07-agentfit-phase2-project-modeling-plan.md` using those IDs as exact file paths.
3. After Phase 2 proves the common protocols on two different cases, write `docs/plans/2026-08-07-agentfit-phase3-growth-validation-plan.md` around the selected transfer pair.
4. After Phase 3 produces verified evidence, write `docs/plans/2026-08-07-agentfit-phase4-internal-dossier-plan.md` with exact source documents and evidence references.
5. After the internal dossier is approved, write `docs/plans/2026-08-07-agentfit-phase5-preliminary-submission-plan.md` using the official 500-character and PPT/PDF constraints.

Later plans are intentionally generated at their entry gates. Writing exact project paths, metrics, or competition claims before the preceding evidence exists would create fictional detail and violate the approved evidence-first design.

## Repository End State

```text
docs/
├── architecture/
│   └── agentfit-methodology.md
├── design/
│   └── 2026-08-07-agentfit-evidence-and-submission-design.md
├── internal/
│   ├── competition/
│   ├── evidence-research/
│   ├── cross-scenario-project-suite/
│   ├── methodology/
│   ├── meta-agent-team/
│   ├── evaluation/
│   ├── governance/
│   ├── agentteams-mapping/
│   └── decisions-and-risks/
├── submission/
│   ├── preliminary-introduction.md
│   ├── preliminary-deck-outline.md
│   ├── agent-identities.md
│   ├── skill-catalog.md
│   ├── evidence-summary.md
│   ├── demo-storyboard.md
│   └── judge-q-and-a.md
└── plans/
```

## Global Completion Check

Before declaring the full program complete, run:

```bash
git diff --check
rg -n "内容待定|后续补充|未经验证.*已完成|模拟.*生产" docs/internal docs/submission
find docs/internal docs/submission -type f -empty -print
```

Expected:

- `git diff --check` prints nothing;
- the `rg` command prints no deferred-content marker or unsupported completion claim;
- `find` prints no empty artifact.
