# Scoreline V2 Review

## Purpose

This directory contains a parallel judging-scoreline-oriented alternative. It does not replace or modify the frozen submission in `competition/2026-08-15/submission/`.

## Implementation provenance

- Primary authoring and redesign: OpenCode 1.18.13 with `zhipuai-coding-plan/glm-5.2`.
- Final independent verification and visible-overlap fixes: Codex.
- Current canonical solution and frozen submission were used as read-only constraints.

## Main narrative difference

| Frozen submission | Scoreline V2 |
|---|---|
| Product and methodology first | Concrete ProjectCase and judging evidence first |
| Cross-industry breadth in the main story | Official OpsPilot baseline as one disclosed first ProjectCase |
| Search space and selection method occupy early pages | User, incident samples, meta-team, AgentTeams mapping and evidence contract precede search details |
| Official cases are reference breadth | OpsPilot code package and its two incidents explain the concrete input |
| ML mapping is a full appendix emphasis | Search representation is compressed and explicitly prevented from taking over the main story |

AgentFit remains a meta-team for designing and evaluating Agent architectures. It is not presented as an Ops product. The OpsPilot baseline is a reference input and first ProjectCase anchor, not AgentFit runtime evidence.

## TDD record

Initial RED command:

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest -v   competition/2026-08-15/alternatives/scoreline-v2/test_scoreline_contract.py
```

Initial result: 13 tests executed against missing implementation, with 12 expected failures and 8 errors. Failures covered missing slides, validator, outline, introduction and built artifacts.

Final GREEN command:

```bash
PY=/home/shangkailiang/workspace/.codex-home/venvs/document-skills/bin/python
"$PY" -m unittest -q   competition/2026-08-15/alternatives/scoreline-v2/test_scoreline_contract.py
```

Final result:

```text
Ran 13 tests in 1.004s
OK
```

## Build and validation

Generated artifacts:

- `agentfit-scoreline-v2.pptx`: 17 native editable slides.
- `agentfit-scoreline-v2.pdf`: 17 matching pages.
- `contact-sheet.jpg`: 17-page comparison preview.

Validator result:

```text
pptx_pages=17
pdf_pages=17
content_checks=PASS
native_editability_checks=PASS
pdf_page_text_checks=PASS
```

The validator rejects:

- missing per-page titles and required scoreline terms;
- ML/NAS terminology on the first four pages;
- fabricated winner, ROI or completed-integration claims;
- pictures, media and transitions;
- blank or text-divergent PDF pages.

## Visual review

The 17-page contact sheet was reviewed. Slides 7 and 9 initially had visible title/subtitle overlap after long titles wrapped in LibreOffice. Their HTML sources were corrected with smaller title sizes and lower subtitle/rule positions, then PPTX/PDF were rebuilt and rechecked at full-page resolution.

Final geometry inspection has:

- no overflow;
- no clipping;
- no unexpected overlap;
- 20 advisory grid-alignment near-misses of 0.04–0.15 inches.

The advisory near-misses do not correspond to visible defects and were retained to avoid mechanically disturbing intentional spacing.

## Evidence boundary

The alternative states:

- the official OpsPilot baseline has been downloaded, code-level audited and its mock tool server minimally executed outside the AgentFit runtime;
- historical AgentTeams smoke tests establish platform capabilities only;
- AgentFit's first ProjectCase, five-agent meta-team and candidate comparison have not yet run;
- no candidate is selected;
- no AgentFit runtime Trace, benchmark, ROI or business outcome is claimed;
- the current decision remains `requires_runtime_trial`.

## Introduction

The alternative introduction contains 499 non-whitespace characters and preserves the same evidence boundary as the deck.

## Scope

All working-tree changes are contained in:

```text
competition/2026-08-15/alternatives/scoreline-v2/
```

No frozen submission or canonical solution file was changed by scoreline-v2.
