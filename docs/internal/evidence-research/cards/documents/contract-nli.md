# Evidence Card: ContractNLI

## Identity

- `evidence_id`: `contract-nli`
- `domain`: `documents`
- `source_title`: `ContractNLI: A Dataset for Document-level Natural Language Inference for Contracts`
- `canonical_url`: https://stanfordnlp.github.io/contract-nli/
- `publication_or_access_date`: EMNLP 2021; source accessed 2026-08-07
- `organization_or_authors`: Yuta Koreeda and Christopher D. Manning
- `evidence_level`: `E2` — public expert-annotated document NLI benchmark
- `license`: CC BY 4.0

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: One nondisclosure agreement and 17 fixed hypotheses about contractual obligations or terms.
- `expected_output`: For each hypothesis, Entailment, Contradiction, or NotMentioned, together with supporting evidence spans.
- `reported_roles`: Dataset annotators and one evaluated NLI system; no Agent role is prescribed.
- `coordination_topology`: A document-level classification and evidence-identification pipeline, not a multi-Agent topology.
- `tools_and_state`: 607 annotated contracts, document and span annotations, JSON-formatted data, SEC source links, and a separately published Span NLI BERT baseline.
- `human_gate`: Expert annotation provides reference decisions; the benchmark does not define runtime legal approval.
- `reported_metrics`: The source reports 607 annotated contracts and 17 hypotheses; it states that Span NLI BERT significantly outperforms prior models but does not present the numeric result table on the project page.
- `stated_limitations`: Long documents, label imbalance, contract-specific language, negations by exception, evidence identification, and substantial remaining room for improvement.
- `reproducibility`: Dataset downloads, schema description, baseline repository, source-document URLs, and CC BY 4.0 terms provide strong task-level reproducibility.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Use Span NLI BERT or another fixed pipeline as the primary baseline, then compare one evidence-checking Agent and a bounded clause-review plus verifier graph.
- `agentize_signals`: Evidence conflicts, long context, and exception handling may benefit from iterative review, but fixed hypotheses and labels strongly favor an Agentless baseline.
- `non_llm_alternatives`: Span NLI, long-document classifiers, retrieval, rules, contradiction detection, and human legal review.
- `possible_adaptation_data`: Contracts stratified by source and label, with a subset of hypotheses.
- `possible_holdout_data`: Document templates, SEC filing sources, or hypotheses excluded from adaptation.
- `possible_failure_injection`: Removed evidence span, exception clause, contradictory amendment, long-context truncation, label imbalance, and forced answer where abstention is safer.
- `future_transfer_conditions`: After a real document ProjectCase is complete, compare only targets with compatible contract representations, clause spans, label semantics, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether an Agent improves evidence quality or merely adds cost to a well-specified supervised task.
- `missing_artifacts`: AgentFit has not defined a legal-expert review gate, process-level scoring, or AgentTeams execution trace for this task.
- `license_or_data_questions`: SEC source documents and the separate baseline repository should be checked independently even though the dataset is CC BY 4.0.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Project page task introduction, `Dataset`, data-format description, `Baseline system`, `License`, and cited paper abstract
