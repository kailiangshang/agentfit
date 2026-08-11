# Evidence Card: ITBench

## Identity

- `evidence_id`: `itbench`
- `domain`: `operations`
- `source_title`: `ITBench`
- `canonical_url`: https://github.com/itbench-hub/ITBench
- `publication_or_access_date`: source accessed 2026-08-07
- `organization_or_authors`: IBM Research, ITBench maintainers, and repository contributors
- `evidence_level`: `E2` — public benchmark with reproducible operational scenarios
- `license`: Apache-2.0

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: Real-world-inspired SRE, CISO, or FinOps scenarios deployed in operational Kubernetes environments.
- `expected_output`: An Agent's environment interactions and submitted outcome, evaluated through benchmark metrics and leaderboards.
- `reported_roles`: The repository exposes separate SRE and CISO reference Agents built with CrewAI; it does not establish that those two references collaborate on one task.
- `coordination_topology`: Each reference Agent interacts with its scenario environment; a required multi-Agent topology is `not_reported_by_source`.
- `tools_and_state`: Push-button deployment, Kubernetes environments, scenario mechanisms, natural-language tools, configurable model backends, managed evaluation, and leaderboard submission.
- `human_gate`: `not_reported_by_source` as a mandatory runtime approval mechanism.
- `reported_metrics`: The repository lists 6 SRE scenarios with 21 mechanisms, 4 CISO scenario categories, and 1 FinOps scenario. A 2026 announcement reports 59 ITBench-AA SRE tasks with all evaluated models below 50%.
- `stated_limitations`: Managed scenarios and self-hosted components have different access and setup paths; the README does not provide a single result that demonstrates one topology is best across SRE, CISO, and FinOps.
- `reproducibility`: Open deployment tooling, scenario definitions, sample environments, reference Agents, and leaderboards provide partial reproduction; managed evaluation remains an external service path.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Benchmark deterministic runbooks, a single operational Agent, and role-separated diagnosis/remediation/compliance candidates under common scenario seeds.
- `agentize_signals`: Cross-tool diagnosis and stateful remediation can require iterative observation; destructive actions should be isolated behind approval and rollback nodes.
- `non_llm_alternatives`: Rules, topology graphs, anomaly detection, causal ranking, constraint checking, optimization, and operator-authored remediation plans.
- `possible_adaptation_data`: A subset of mechanisms from known applications and non-destructive tasks.
- `possible_holdout_data`: New applications, unseen mechanisms, or cross-use-case tasks.
- `possible_failure_injection`: Alert ambiguity, hidden dependencies, stale telemetry, permission denial, rollback failure, and conflicting SRE/CISO/FinOps objectives.
- `future_transfer_conditions`: After a real operations ProjectCase is complete, compare only targets with compatible incident semantics, action boundaries, evaluators, trace schemas, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether a specialist team offers value beyond the reference single-Agent patterns on the selected scenarios.
- `missing_artifacts`: A frozen local scenario subset, comparable budgets, and AgentTeams integration trace are not yet present in AgentFit.
- `license_or_data_questions`: Container images, cloud providers, model APIs, and individual scenario dependencies require separate license and access review.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README `Announcements`, `Overview`, `What's Included`, `Leaderboard`, `Scenarios`, and `Agents`; repository root license metadata
