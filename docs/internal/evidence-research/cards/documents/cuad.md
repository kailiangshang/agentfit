# Evidence Card: CUAD

## Identity

- `evidence_id`: `cuad`
- `domain`: `documents`
- `source_title`: `Contract Understanding Atticus Dataset`
- `canonical_url`: https://github.com/The-Atticus-Project/cuad
- `publication_or_access_date`: NeurIPS 2021; source accessed 2026-08-07
- `organization_or_authors`: Dan Hendrycks, Collin Burns, Anya Chen, Spencer Ball, and The Atticus Project
- `evidence_level`: `E2` — expert-annotated legal contract benchmark
- `license`: `not_reported_by_source`; no repository license file was found at the checked endpoint

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: Legal contract text and contract-review categories represented in the dataset.
- `expected_output`: Relevant contract spans or category-level review findings.
- `reported_roles`: Expert annotators created the dataset; the benchmark does not prescribe an Agent role.
- `coordination_topology`: Single-model span extraction or classification; no Agent collaboration topology is reported.
- `tools_and_state`: Dataset files, Transformer training/evaluation code, and published RoBERTa-base, RoBERTa-large, and DeBERTa-xlarge checkpoints.
- `human_gate`: Expert annotation provides ground truth, but no runtime legal-review approval gate is specified.
- `reported_metrics`: The repository README says Transformer performance remains strongly affected by model design and training-data size and that substantial room for improvement remains; it does not provide the numeric table used by the associated paper.
- `stated_limitations`: Specialized legal language, dependence on expert labels, model- and data-size sensitivity, and an older documented stack of Python 3.8, PyTorch 1.7, and Transformers 4.3/4.4.
- `reproducibility`: Data, code, requirements, and checkpoints are referenced, but absent repository licensing and dated dependencies make reproduction partial.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Start with an Agentless extraction/classification pipeline; compare one review Agent and a clause-specialist plus verifier graph only if process metrics justify them.
- `agentize_signals`: Long contracts and category interactions may require iterative evidence checking, but the core labeled task is a strong fixed-Workflow baseline.
- `non_llm_alternatives`: Span classifiers, NER, regex and dictionaries, retrieval, similarity search, rules, and human legal review.
- `possible_adaptation_data`: A contract-stratified training subset and limited review categories.
- `possible_holdout_data`: Contracts, templates, or clause categories excluded by document family.
- `possible_failure_injection`: OCR corruption, missing clause, conflicting provisions, negated exception, long-context truncation, and unsupported legal conclusion.
- `future_transfer_conditions`: After a real document ProjectCase is complete, compare only targets with compatible clause taxonomies, evidence spans, abstention rules, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether an Agent topology improves evidence-grounded review over strong document models under the same compute and context budget.
- `missing_artifacts`: A current reproducible environment, process-level trace evaluator, and legal-expert approval protocol are not supplied by the README.
- `license_or_data_questions`: Repository and dataset redistribution terms must be established before any competition package includes the data or checkpoints.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README introduction, dataset download/evaluation commands, `Trained Models`, `Extra Data`, `Requirements`, and `Citation`; repository root checked for a license file
