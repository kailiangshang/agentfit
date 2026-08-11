# Evidence Card: Anthropic Multi-Agent Research

## Identity

- `evidence_id`: `anthropic-multi-agent-research`
- `domain`: `research`
- `source_title`: `How we built our multi-agent research system`
- `canonical_url`: https://www.anthropic.com/engineering/multi-agent-research-system
- `publication_or_access_date`: 2025-06-13; source accessed 2026-08-07
- `organization_or_authors`: Anthropic
- `evidence_level`: `E1` — identifiable production system and reported internal evaluation, without a public reproduction package
- `license`: `not_reported_by_source`

## Verified Facts

All statements in this section are `verified_fact` about what Anthropic reports; internal results are not independently reproduced here.

- `task_input`: An open-ended user research query that may require broad, path-dependent information search.
- `expected_output`: A synthesized research answer with source citations.
- `reported_roles`: A lead research Agent plans and delegates parallel searches to subagents; a citation-processing stage checks and attaches citations.
- `coordination_topology`: Lead-Agent fan-out to parallel subagents followed by aggregation and citation processing.
- `tools_and_state`: Web search, Google Workspace, integrations including MCP, separate subagent context windows, memory, artifacts, and citation metadata.
- `human_gate`: No mandatory runtime human approval gate is reported; the article states that human testing remains essential because automated evaluation does not capture all failure modes.
- `reported_metrics`: Anthropic reports that an Opus 4 lead with Sonnet 4 subagents outperformed single-Agent Opus 4 by 90.2% on an internal research evaluation. It also reports multi-Agent systems using about 15 times the tokens of chats.
- `stated_limitations`: High token cost; synchronous coordination bottlenecks; tasks with many dependencies or shared-context requirements are a poor fit; coding offers fewer truly parallel tasks; production reliability and evaluation are difficult.
- `reproducibility`: Architecture and engineering lessons are described, but the internal evaluation set, production implementation, and result artifacts are not public; only scenario-level reproduction is possible from this source.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare serial search Workflow, one iterative research Agent, and a budgeted lead/fan-out/aggregate/citation graph.
- `agentize_signals`: Breadth-first questions with independent search branches, information beyond one context window, and heterogeneous tools are the strongest candidate conditions.
- `non_llm_alternatives`: Search APIs, query expansion, ranking, clustering, deduplication, graph traversal, extractive summarization, and human research.
- `possible_adaptation_data`: A small set of decomposable queries with known source coverage and branch labels.
- `possible_holdout_data`: New topics whose sources and entities do not overlap adaptation queries.
- `possible_failure_injection`: Duplicate branches, missing citations, conflicting sources, stalled subagent, budget overrun, aggregator omission, and synchronized-dependency tasks.
- `future_transfer_conditions`: After a real research ProjectCase is complete, compare only targets with compatible breadth-first search needs, tool access, citation rules, budget constraints, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: The 90.2% internal improvement cannot be treated as an independently reproducible benchmark result or generalized to non-research tasks.
- `missing_artifacts`: Public evaluation queries, grading code, traces, exact budgets, and production source are unavailable.
- `license_or_data_questions`: The article does not grant a code or dataset license.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Article introduction, `Benefits of a multi-agent system`, `Architecture overview for Research`, evaluation discussion, reliability discussion, and limitations/conclusion
