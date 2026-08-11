# Evidence Card: GAIA

## Identity

- `evidence_id`: `gaia`
- `domain`: `research`
- `source_title`: `GAIA: A Benchmark for General AI Assistants`
- `canonical_url`: https://arxiv.org/abs/2311.12983
- `publication_or_access_date`: 2023-11-21; source accessed 2026-08-07
- `organization_or_authors`: Grégoire Mialon, Clémentine Fourrier, Craig Swift, Thomas Wolf, Yann LeCun, and Thomas Scialom
- `evidence_level`: `E2` — public benchmark with held-out answers and leaderboard
- `license`: `not_reported_by_source`

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: Real-world questions requiring combinations of reasoning, multimodal handling, web browsing, and tool use.
- `expected_output`: A concise factual final answer suitable for automatic evaluation.
- `reported_roles`: One general AI assistant; the benchmark does not prescribe subagents or a manager.
- `coordination_topology`: Single-assistant task execution with optional external tools.
- `tools_and_state`: Web access, files and multimodal inputs, plugins or tools, scratch computation, and a final-answer evaluator.
- `human_gate`: No runtime human approval gate is specified; human respondents provide a comparison baseline.
- `reported_metrics`: 466 questions were created; answers to 300 were retained for the leaderboard. The paper reports 92% average human success versus about 15% for GPT-4 with plugins.
- `stated_limitations`: English-centric questions, web content that can change over time, and final-answer grading that does not itself assess process safety or topology.
- `reproducibility`: Questions and a leaderboard are available, with most answers held out; tool and web drift make reproduction partial.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare tool-routing Workflow, one generalist Agent, and conditional specialist fan-out only for questions with independently searchable branches.
- `agentize_signals`: Tool choice and open-web investigation are path-dependent, but many questions may remain cheaper with one Agent or deterministic tooling.
- `non_llm_alternatives`: Search, OCR, calculators, code execution, entity resolution, retrieval/ranking, and human lookup.
- `possible_adaptation_data`: Public-answer development questions grouped by level and tool type.
- `possible_holdout_data`: Sealed leaderboard questions or an internally frozen, non-overlapping question set.
- `possible_failure_injection`: Stale webpages, conflicting sources, unavailable files, OCR errors, tool-routing failure, and correct answer with unsupported reasoning.
- `future_transfer_conditions`: After a real research ProjectCase is complete, compare only targets with compatible question breadth, tool requirements, evidence expectations, evaluation rules, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether GAIA's open-tool questions provide enough repeatable evidence to choose between single- and multi-Agent structures.
- `missing_artifacts`: A time-frozen web corpus, process-level evaluator, and explicit cost budget are not part of the paper source.
- `license_or_data_questions`: Dataset and attachment licenses require verification from the hosting platform before redistribution.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Paper abstract; benchmark design and dataset sections; level definitions; experimental results; discussion of robustness and limitations
