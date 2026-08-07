# Evidence Card: CRMArena

## Identity

- `evidence_id`: `crm-arena`
- `domain`: `business`
- `source_title`: `CRMArena and CRMArena-Pro`
- `canonical_url`: https://github.com/SalesforceAIResearch/CRMArena
- `publication_or_access_date`: CRMArena 2025 and CRMArena-Pro 2026; source accessed 2026-08-07
- `organization_or_authors`: Salesforce AI Research and the CRMArena authors
- `evidence_level`: `E2` — public benchmark and realistic CRM sandbox
- `license`: CC BY-NC 4.0; research/non-commercial restriction stated by the repository

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: CRM or CRM-Pro tasks, organization schema/data, task strategy configuration, and Salesforce API state.
- `expected_output`: Agent task results and experiment logs produced by interacting with the CRM environment.
- `reported_roles`: The README configures an Agent model and CRM task; it does not report a required multi-Agent team.
- `coordination_topology`: One evaluated Agent interacting with a Salesforce organization and benchmark runner; interactive scenarios are supported in CRMArena-Pro.
- `tools_and_state`: Salesforce organizations and APIs, Hugging Face datasets, schema assets, experiment scripts, model providers, result logs, and optional GUI access.
- `human_gate`: `not_reported_by_source` as a mandatory task-time approval mechanism; researchers must request GUI access separately.
- `reported_metrics`: `not_reported_by_source` in the repository README snapshot used for this card.
- `stated_limitations`: GUI access is no longer public and must be requested; the repository is research-only/non-commercial; external model and Salesforce access configuration is required.
- `reproducibility`: Evaluation code, datasets, scripts, and API-access instructions are public, but restricted GUI access and a non-commercial license make reproduction partial.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare deterministic CRM workflows, a single tool Agent, and role-separated customer-intent, policy, data, and action-verification candidates.
- `agentize_signals`: Business requests combine dialogue, policy, heterogeneous records, and state mutation; high-impact writes create a natural approval boundary.
- `non_llm_alternatives`: CRM rules, SQL or API query templates, process engines, constraint checkers, recommenders, and human operators.
- `possible_adaptation_data`: A small research-only task subset and schema slice with synthetic or non-sensitive records.
- `possible_holdout_data`: New CRM task families, organization types, or interactive user behaviors.
- `possible_failure_injection`: Stale records, insufficient permission, conflicting policy, duplicate write, wrong customer, GUI unavailability, and model-provider failure.
- `transfer_pair_candidates`: `tau-bench` as an adjacent policy-governed business interaction task.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether CRMArena can be included in a publicly demonstrated competition PoC without breaching research-only or platform-access constraints.
- `missing_artifacts`: A credential-free local sandbox and explicit approval/rollback trace are not provided by the selected README.
- `license_or_data_questions`: CC BY-NC 4.0 restricts commercial reuse; Salesforce organization data, model APIs, and GUI access have separate terms. Public test credentials shown by the source were deliberately not copied into this card.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README identity and dataset links, license badge and research-only notice, `Quickstart`, `Accessing the Org via GUI`, `Accessing the Org via API`, and `Running experiments`
