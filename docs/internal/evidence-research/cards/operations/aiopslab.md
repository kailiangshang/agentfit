# Evidence Card: AIOpsLab

## Identity

- `evidence_id`: `aiopslab`
- `domain`: `operations`
- `source_title`: `AIOpsLab`
- `canonical_url`: https://github.com/microsoft/AIOpsLab
- `publication_or_access_date`: source accessed 2026-08-07
- `organization_or_authors`: Microsoft Research and repository contributors
- `evidence_level`: `E3` — runnable open-source framework and benchmark suite
- `license`: MIT

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: An AIOps problem combining an application, task, injected fault, workload, environment, instructions, and exposed APIs.
- `expected_output`: An Agent-submitted solution evaluated with its action trace and duration; results are stored for later analysis.
- `reported_roles`: An Orchestrator manages the environment and Session while one tested Agent, or a human acting as that Agent, interacts with the problem.
- `coordination_topology`: Orchestrator-to-Agent environment interaction; the README does not prescribe a team of communicating Agents.
- `tools_and_state`: Kubernetes or kind clusters, microservice applications, fault injection, workload generation, telemetry APIs, Session traces, task-specific actions, and custom evaluators.
- `human_gate`: The CLI supports a human as the tested Agent, but the benchmark does not report a mandatory runtime approval gate for autonomous actions.
- `reported_metrics`: `not_reported_by_source`; the README documents evaluation interfaces but no single comparative performance result.
- `stated_limitations`: Local setup depends on Docker and proxy configuration; some fault injectors require Docker on the local/controller machine, so a remote-cluster mode does not expose all functionality.
- `reproducibility`: The repository provides installation, local kind deployment, remote options, example problems, agent onboarding, traces, evaluator extension points, and source code under MIT.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare alert-to-runbook Workflow, a single observe-reason-act Agent, and a bounded specialist graph for detection, localization, analysis, mitigation, and approval.
- `agentize_signals`: Environment state changes after actions and faults are heterogeneous, making a local feedback loop useful; hard safety gates can remain deterministic.
- `non_llm_alternatives`: Threshold detectors, topology/rule correlation, time-series models, causal or graph ranking, scripted runbooks, constrained optimization, and human SRE triage.
- `possible_adaptation_data`: Known applications, fault types, telemetry traces, and low-risk detection/localization tasks.
- `possible_holdout_data`: Unseen applications, fault mechanisms, or task compositions.
- `possible_failure_injection`: Telemetry loss, delayed signals, wrong topology, tool timeout, partial remediation, unsafe mitigation proposal, and cluster setup failure.
- `transfer_pair_candidates`: `itbench` as the strongest same-family transfer target for operational priors and trace schemas.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether multiple Agents outperform one Agent or a scripted runbook after equalizing tool access and action budgets.
- `missing_artifacts`: AgentFit has not yet frozen a small reproducible problem set or produced AgentTeams traces against it.
- `license_or_data_questions`: Application images and third-party dependencies may have licenses separate from the MIT repository.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README introduction, `Requirements`, `Running agents locally`, `How to onboard your agent`, `How to add new problems`, repository layout, and `License`
