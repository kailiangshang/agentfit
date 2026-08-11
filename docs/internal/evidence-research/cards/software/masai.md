# Evidence Card: MASAI

## Identity

- `evidence_id`: `masai`
- `domain`: `software`
- `source_title`: `MASAI: Modular Architecture for Software-engineering AI Agents`
- `canonical_url`: https://arxiv.org/abs/2406.11638
- `publication_or_access_date`: 2024-06-17; source accessed 2026-08-07
- `organization_or_authors`: Daman Arora, Atharv Sonwane, Nalin Wadhwa, Abhav Mehrotra, Saiteja Utpala, Ramakrishna Bairi, Aditya Kanade, and Nagarajan Natarajan
- `evidence_level`: `E2` — controlled evaluation on SWE-bench Lite
- `license`: `not_reported_by_source`

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: A code repository and issue description, plus outputs passed between sub-agents where needed.
- `expected_output`: One ranked patch proposed as the issue resolution.
- `reported_roles`: Five LLM-powered sub-agents: Test Template Generator, Issue Reproducer, Edit Localizer, Fixer, and Ranker.
- `coordination_topology`: A fixed directed composition. Sub-agents exchange artifacts and repository information; the paper describes information flow rather than free-form inter-Agent chat.
- `tools_and_state`: Repository read/list/command/write actions, generated reproduction tests, candidate patches, test results, repository state, and a SWE-bench Lite evaluation harness.
- `human_gate`: The experimental pipeline has no runtime human approval step; the paper says expert developers should review suggested code changes before real-world deployment.
- `reported_metrics`: On 300 SWE-bench Lite issues from 11 Python repositories, MASAI reports 28.33% resolution, 75.00% localization, 95.33% patch application, and average per-issue cost of USD 1.96.
- `stated_limitations`: All sub-agents used GPT-4o; issues were English; alternative model cost/performance was not directly evaluated; generated code requires expert review before deployment.
- `reproducibility`: The paper specifies roles, inputs, strategies, loop limits, model, candidate count, evaluation dataset, and harness, but the selected paper source does not establish a licensed, one-command reproduction package.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Treat MASAI as one modular candidate beside an Agentless pipeline and a single repair Agent, not as the assumed optimum.
- `agentize_signals`: Distinct subproblems use different strategies and intermediate artifacts; objective tests can gate patch ranking.
- `non_llm_alternatives`: Static localization, BM25 or embedding retrieval, syntax-aware edit generation, deterministic test execution, search over patch templates, and human review.
- `possible_adaptation_data`: A repository-stratified subset of SWE-bench Lite used to tune role boundaries and budgets.
- `possible_holdout_data`: Repositories excluded from architecture and prompt selection.
- `possible_failure_injection`: Broken test templates, false reproductions, wrong-file localization, invalid patches, ranker disagreement with tests, and budget exhaustion.
- `future_transfer_conditions`: After a real software ProjectCase is complete, compare only targets with compatible diagnosis patterns, repository/task schemas, evaluation harnesses, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether modularity itself, rather than token budget, model choice, or candidate sampling, causes an improvement under equalized resources.
- `missing_artifacts`: A verified source-code release and immutable environment were not established from the selected paper source.
- `license_or_data_questions`: The arXiv paper does not state a software license; downstream use must locate and verify any implementation license separately.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Paper abstract; Section 2 `MASAI Agent Architecture`; Section 3 `Experimental Setup`; Tables 1 and 2; Section 7 limitations and broader-impact discussion
