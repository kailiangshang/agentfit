# Evidence Card: Purple Llama

## Identity

- `evidence_id`: `purple-llama`
- `domain`: `security`
- `source_title`: `Purple Llama`
- `canonical_url`: https://github.com/meta-llama/PurpleLlama
- `publication_or_access_date`: source accessed 2026-08-07
- `organization_or_authors`: Meta and Purple Llama contributors
- `evidence_level`: `E3` — open-source evaluation and safeguard components
- `license`: Mixed: evals/benchmarks and Code Shield are MIT; model safeguards use the corresponding Llama Community licenses

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: Component-dependent security-evaluation examples, model inputs/outputs, prompts, or generated code.
- `expected_output`: Evaluation results or safeguard decisions, such as cyber-risk measurements, prompt-injection checks, unsafe-content classification, or code-security findings.
- `reported_roles`: Components include CyberSec Eval, Llama Guard variants, Prompt Guard, and Code Shield; these are tools/models, not a reported Agent team.
- `coordination_topology`: `not_reported_by_source`; the repository presents reusable safeguards and evaluations rather than one end-to-end collaborating Agent workflow.
- `tools_and_state`: Benchmark datasets and runners, safeguard models, prompt-injection detection, code-security scanning, and a reference-system safety layer.
- `human_gate`: `not_reported_by_source` as a mandatory runtime approval mechanism.
- `reported_metrics`: `not_reported_by_source` in the repository README snapshot used for this card.
- `stated_limitations`: Licenses differ by component; repository statements describe risk-reduction goals but do not prove that any one safeguard is sufficient for a deployed system.
- `reproducibility`: Evaluation code and Code Shield are permissively licensed, while model components require separately licensed weights; reproduction is partial across the full suite.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Model these components as shared capability nodes around any Agent graph, not automatically as independent Agents.
- `agentize_signals`: Most safeguards are deterministic or model-call gates; an Agent is justified only when investigation or recovery requires stateful decisions.
- `non_llm_alternatives`: Static analyzers, signatures, allow/deny rules, sandbox policies, taint analysis, schema validation, and manual security review.
- `possible_adaptation_data`: Permissively licensed evaluation examples that match the chosen AgentFit threat model.
- `possible_holdout_data`: New attack families, unseen prompt injections, and held-out insecure-code patterns.
- `possible_failure_injection`: Evasion, false positive, model refusal, license-incompatible component request, bypassed safety node, and unsafe fallback.
- `future_transfer_conditions`: After a real security ProjectCase is complete, compare only targets with compatible threat models, safety-control hooks, evaluation protocols, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether a selected subset provides measurable safety value in AgentTeams without unacceptable latency or false positives.
- `missing_artifacts`: A unified task contract, end-to-end evaluator, and AgentTeams integration are not supplied by the repository overview.
- `license_or_data_questions`: Every chosen model, checkpoint, benchmark, and Code Shield component must be mapped to its specific license; the suite cannot be labeled simply `MIT`.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README `Why purple?`, `License`, `System-Level Safeguards`, `Evals & Benchmarks`, and `Getting Started`
