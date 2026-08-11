# Evidence Card Contract

This file defines the required structure of an evidence card. It is not a completed case and contains no external claim.

## Identity

- `evidence_id`
- `domain`
- `source_title`
- `canonical_url`
- `publication_or_access_date`
- `organization_or_authors`
- `evidence_level`
- `license`

## Verified Facts

- `task_input`
- `expected_output`
- `reported_roles`
- `coordination_topology`
- `tools_and_state`
- `human_gate`
- `reported_metrics`
- `stated_limitations`
- `reproducibility`

If a source does not report a field, the evidence card records `not_reported_by_source`; it does not infer a value.

## AgentFit Interpretation

- `candidate_graph_patterns`
- `agentize_signals`
- `non_llm_alternatives`
- `possible_adaptation_data`
- `possible_holdout_data`
- `possible_failure_injection`
- `future_transfer_conditions`

`future_transfer_conditions` records source-specific compatibility criteria only. It must not nominate a project pair before the first real ProjectCase has produced runtime evidence.

This section contains design interpretations only. It must not be cited as a source fact.

## Open Questions

- `unsupported_claims`
- `missing_artifacts`
- `license_or_data_questions`

## Provenance

- `checked_by`
- `checked_at`
- `source_sections`
