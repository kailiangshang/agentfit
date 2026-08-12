# Fusion V3 Review

## Purpose

This directory contains a third, fusion-style alternative deck. It combines the scoreline narrative clarity of `scoreline-v2/` with the product and methodology depth of the frozen `submission/`. It does not replace or modify the frozen submission, scoreline-v2, or any canonical design file.

## Implementation provenance

- Primary authoring and redesign: OpenCode with `zhipuai-coding-plan/glm-5.2`.
- Current canonical solution, frozen submission and scoreline-v2 were used as read-only constraints.
- Final independent verification and publication: Codex.

## Main narrative: fusion trade-off vs the other two versions

| Dimension | Frozen submission | Scoreline V2 | Fusion V3 (this) |
|---|---|---|---|
| Cover positioning | General solution architect | One concrete choice problem | **General architect + OpsPilot as first case anchor** |
| Main spine | Method and search space | Concrete Ops choice problem | **Ops case concretizes the method, then returns to the unified search space** |
| OpsPilot handling | Reference breadth only | First ProjectCase and evidence anchor | **First ProjectCase anchor + explicit "not runtime evidence"** |
| Unified search space / simplest qualified candidate | Early main spine | Compressed into appendix | **Restored to main pages 5–6** |
| ML / seven-layer mapping / inner & outer loops | Full appendix | Compressed to keep it off the spine | **Restored in full in A1 + explicit Meta-learning future boundary** |
| Meta-agent vs business-agent layers | Implicit | Distinguished but easy to confuse | **Page 7 splits the two layers explicitly and repeats it** |

Fusion principles applied:

- The first four pages carry no ML / NAS terminology; the ML semantics are fully preserved in appendix A1.
- OpsPilot is only the first ProjectCase input, never AgentFit runtime evidence.
- Page 12 lifts the story back from the Ops case to general Agent solution-architect value.
- Two agent layers are explicit: five meta-agents design/evaluate/audit AgentFit solutions; OpsPilot-style execution agents live inside candidate C2.

AgentFit remains a meta-team for designing and evaluating Agent architectures. It is not presented as an Ops product. The OpsPilot baseline is a reference input and first ProjectCase anchor, not AgentFit runtime evidence.

## TDD record

Initial RED command:

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest -v competition/2026-08-15/alternatives/fusion-v3/test_fusion_contract.py
```

Initial result (before any implementation existed): 16 tests executed, 18 failures and 10 errors (sub-test level), covering missing slides, validator, builder, outline, introduction and built artifacts.

After implementation (HTML slides, validator, builder, outline, introduction), the pre-build run was 12/16 passing; the 4 remaining failures only required the built PPTX/PDF.

Final GREEN command:

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest -v competition/2026-08-15/alternatives/fusion-v3/test_fusion_contract.py
```

Final result:

```text
Ran 17 tests in 1.047s
OK
```

The seventeenth regression test was added after independent PDF inspection exposed compact CJK labels that existed in the source but wrapped orphan characters after PowerPoint/PDF conversion. The test reads the final PDF with layout preservation and requires the five page-7 role labels plus the two page-9 compact labels to remain on one line. It produced seven expected failing sub-tests before the width fixes, then passed after the PPTX/PDF rebuild.

## Build and validation

Generated artifacts:

- `agentfit-fusion-v3.pptx`: 17 native editable slides, no pictures / media / transitions.
- `agentfit-fusion-v3.pdf`: 17 matching pages.
- `contact-sheet.jpg`: 17-page comparison preview.

Build commands:

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
DECK=/home/shangkailiang/workspace/.codex-home/skills/hands-on-deck/scripts/deck.py
"$PY" competition/2026-08-15/alternatives/fusion-v3/build_presentation.py
"$PY" "$DECK" competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pptx inspect --issues
soffice --headless --convert-to pdf --outdir competition/2026-08-15/alternatives/fusion-v3 \
  competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pptx
"$PY" competition/2026-08-15/alternatives/fusion-v3/validate_presentation.py \
  competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pptx \
  competition/2026-08-15/alternatives/fusion-v3/agentfit-fusion-v3.pdf
```

Validator result:

```text
pptx_pages=17
pdf_pages=17
content_checks=PASS
native_editability_checks=PASS
pdf_page_text_checks=PASS
```

The validator enforces:

- exactly 17 PPTX slides and 17 PDF pages;
- per-page conclusion-style titles and required fusion terms (OpsPilot / ProjectCase / TaskSample / db_pool_exhausted / slow_sql_degradation / AgentSolutionPackage / 同一搜索空间 / 七层 ML 映射 / G, Π, θ, ρ / inner loop / outer loop / Meta-learning / EngagementLead / BusinessEngineer / AgentArchitect / ValidationEngineer / GovernanceAuditor / Worker / Team / Room / Dossier / Trace / 元 Agent / 业务执行 Agent, etc.);
- no ML / NAS terminology on the first four pages;
- no fabricated winner, ROI or completed-integration claims;
- no pictures, embedded media or transitions;
- no blank or text-divergent PDF pages.

## Geometry and visual review

`deck.py inspect --issues` on the final PPTX reports:

- overlaps: **0**;
- off-slide / overflow / clipping: **0**;
- advisory grid-alignment near-misses: 21, all in the 0.04"–0.14" band.

A single bounding-box overlap (0.09") appeared on the cover during the first build, caused by the title text box declared width extending behind the "同一任务·四类候选" label. The cover title width was narrowed from 760px to 700px, the PPTX/PDF were rebuilt, and the recheck reported 0 overlaps.

The independent 150 DPI PDF review then found orphan-character wraps that geometry checks did not detect: the two layer labels and five role labels on page 7, the first two table headers on page 8, two compact labels on page 9, and two appendix labels on page 13. The corresponding native HTML text boxes were widened (with a small page-7 role-label font adjustment) without deleting or weakening content, then the PPTX and PDF were rebuilt. A second 150 DPI review of PDF pages 7, 8, 9 and 13 confirmed that all affected labels render on one line.

Title-fit analysis (estimated rendered width vs box width at the actual font size) confirms all 17 titles render on a single line, so no title can wrap into its subtitle. The tightest margins are page 2 (≈11.3" of 12.07") and page 11 (≈11.4" of 12.07"), both single-line.

Page ink analysis on the 17 rendered pages confirms every page carries real content (dark slides 1 and 12 read ≈97% ink by design; slide 13 reads ≈24% because of its dark seven-layer panel; light slides read 4–7%).

Advisory near-misses are not visible defects and were retained to avoid mechanically disturbing intentional spacing, matching the policy used in scoreline-v2.

## Evidence boundary

The alternative states:

- the official OpsPilot baseline has been downloaded, code-level audited and its mock tool server minimally executed outside the AgentFit runtime;
- historical AgentTeams smoke tests establish platform capabilities only;
- AgentFit's first ProjectCase, five-agent meta-team and candidate comparison have not yet run;
- no candidate is selected;
- no AgentFit runtime Trace, benchmark, ROI or business outcome is claimed;
- Meta-learning is a future direction and is not implemented;
- the current decision remains `requires_runtime_trial`.

Every design-time trace is labelled "设计契约，非运行证据".

## Introduction

The alternative introduction (`work-introduction.md`) contains 476 non-whitespace characters (≤ 500) and preserves the same evidence boundary as the deck.

## Scope

All working-tree changes are contained in:

```text
competition/2026-08-15/alternatives/fusion-v3/
```

No frozen submission, scoreline-v2, or canonical solution file was changed by the fusion-v3 build.
