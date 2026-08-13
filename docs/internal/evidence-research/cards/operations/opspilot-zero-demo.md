# Evidence Card: OpsPilot Zero Demo

## Identity

- `evidence_id`: `opspilot-zero-demo`
- `domain`: `operations`
- `source_title`: `OpsPilot Zero Demo` official Agent Infra baseline
- `canonical_url`: https://assets.datawhale.cn/131266/dashboard/1785575974456/opspilot-zero-demo.zip
- `publication_or_access_date`: source audited 2026-08-12
- `organization_or_authors`: GOAI / Datawhale competition organizers; individual authors not reported in the package
- `evidence_level`: `E3` - runnable official reference implementation
- `license`: not reported in the downloaded ZIP; redistribution is not assumed
- `source_sha256`: `0bb0f37c227fb5031cd66b6d69dbcbd533602c26b7d5e93f66f93fa02f653478`

## Verified Facts

All statements in this section are `verified_fact` from the downloaded ZIP and a local read-only audit.

- `task_input`: Two incident fixtures, `db_pool_exhausted` and `slow_sql_degradation`.
- `expected_output`: An incident-handling result assembled through the supplied Agent definitions, Skill contracts, task messages, and mock operational tools.
- `reported_roles`: The package contains 4 个 Agent definitions plus a separate Team Leader specification; the task narrative expands operational responsibilities through the Leader and Workers.
- `coordination_topology`: AgentTeams Manager creates Workers and a Team; the user delegates an incident to the Team Leader, which coordinates Worker execution and reporting.
- `tools_and_state`: 7 个 Skill definitions, HTTP mock tools, an in-process stateful Python mock server, Manager creation messages, Team task messages, and a proposed Nacos/MCP mapping.
- `human_gate`: Risk descriptions and approval boundaries are present in the design materials; a completed AgentFit Human-gate runtime trace is not present.
- `reported_metrics`: No comparative C0/C1/C2/C3 AgentFit score is reported.
- `stated_limitations`: HTTP mocks are not a real MCP server; the registry JSON is a target mapping rather than proof of registration; state is process-local; Agent/Skill definitions are currently inlined into creation messages for execution.
- `reproducibility`: Python sources compile; the mock server health endpoint responds; a configuration rollback changes subsequent metrics; three tool calls are recorded in the mock Trace during the audited sequence.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not claims made by the source.

- `candidate_graph_patterns`: Treat the supplied multi-Agent topology as one C2 candidate, then compare it with C0 Agentless, C1 single-Agent, and C3 Human-mixed candidates under the same frozen samples, budgets, permissions, and gates.
- `agentize_signals`: Incident intake, diagnosis, remediation planning, action, and verification expose stateful hand-offs and risk boundaries that may justify partitioning, but the ZIP alone does not prove that multiple Agents are optimal.
- `non_llm_alternatives`: Rules, runbooks, alert correlation, metric thresholds, SQL diagnostics, and deterministic rollback logic.
- `possible_adaptation_data`: One incident family with known tool contracts and reversible mock actions.
- `possible_holdout_data`: A separately frozen incident family or perturbation that candidates cannot inspect before freeze.
- `possible_failure_injection`: Tool timeout, permission denial, stale telemetry, wrong root cause, rollback failure, and unresolved post-action metrics.
- `future_transfer_conditions`: Only after later-stage authorization, freeze the ProjectCase and four SampleSetManifest objects before generating candidates, then retain complete sample-level Episode and Trace evidence.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Which candidate topology is most effective, whether the official C2 topology is necessary, and whether any result transfers beyond these two mock incidents.
- `missing_artifacts`: No AgentFit ProjectCase run, candidate comparison, sealed holdout result, or independent AgentFit audit exists yet.
- `license_or_data_questions`: The ZIP does not include a Git commit or explicit package license; provenance is therefore locked by source URL, SHA-256, and audit date, and the ZIP is not committed here.

## Provenance

- `checked_by`: Codex
- `checked_at`: 2026-08-12
- `source_sections`: ZIP file tree; Agent and Skill Markdown definitions; Team specification; Manager/Team task messages; two scenario JSON files; Python mock tool server; Nacos/MCP mapping notes

This card proves only that the official baseline package and its mock tool sequence were inspected and runnable. 它不证明 AgentFit 已运行，也不是 AgentFit runtime evidence。
