# Evidence Card: Cybench

## Identity

- `evidence_id`: `cybench`
- `domain`: `security`
- `source_title`: `Cybench: A Framework for Evaluating Cybersecurity Capabilities and Risks of Language Models`
- `canonical_url`: https://arxiv.org/abs/2408.08926
- `publication_or_access_date`: ICLR 2025; source version dated 2025-04-12 and accessed 2026-08-07
- `organization_or_authors`: Andy K. Zhang et al., Stanford University
- `evidence_level`: `E2` — controlled cybersecurity benchmark
- `license`: Apache-2.0 for the referenced open-source repository

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: A professional-level Capture The Flag task description, starter files, and an initialized execution environment; optional subtasks expose intermediate goals.
- `expected_output`: A submitted flag or secret checked exactly by an evaluator, with optional subtask completion for granular scoring.
- `reported_roles`: One LM Agent, an execution environment, and an evaluator.
- `coordination_topology`: Sequential Agent action and observation loop with memory; no multi-Agent team is prescribed.
- `tools_and_state`: Kali/Linux command execution, task servers and files, bash actions, observations, Agent memory, optional web search, and exact-answer evaluators.
- `human_gate`: No runtime human approval gate is included in the evaluated Agent loop.
- `reported_metrics`: The benchmark contains 40 tasks from four CTF competitions. The paper reports that leading Agents solved complete tasks whose human first-solve times were up to 11 minutes, while the hardest included task had a human first-solve time of 24 hours 54 minutes.
- `stated_limitations`: The paper discusses possible training contamination, safety refusals, small benchmark scale, reliance on CTF abstractions, and risk that autonomous cyber evaluation can itself enable misuse.
- `reproducibility`: Task specifications, environment approach, Agent scaffold comparisons, and an Apache-2.0 repository are available, but some task artifacts and safe execution requirements make reproduction partial.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare deterministic tool scripts, one constrained cyber Agent, and an isolated planner/executor/verifier graph with mandatory human authorization.
- `agentize_signals`: Long action-observation chains and heterogeneous exploitation strategies favor local feedback, while exact flags provide objective evaluation.
- `non_llm_alternatives`: Vulnerability scanners, symbolic execution, fuzzing, rule-based exploit checks, search, static analysis, and expert penetration testing.
- `possible_adaptation_data`: Low-risk local CTF tasks and their subtasks in isolated containers.
- `possible_holdout_data`: Entire competitions or vulnerability families excluded from adaptation.
- `possible_failure_injection`: Tool denial, decoy flag, network isolation, unsafe target request, poisoned instructions, partial exploit, and evaluator mismatch.
- `future_transfer_conditions`: After a real security ProjectCase is complete, compare only targets with compatible sandbox boundaries, safety evaluators, attack classes, licenses, and runtime evidence; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether this dual-use domain can be demonstrated safely and whether a team improves capability without increasing unacceptable risk.
- `missing_artifacts`: AgentFit has no approved cyber threat model, isolated target set, authorization protocol, or disclosure plan.
- `license_or_data_questions`: CTF problems and external artifacts can carry licenses or usage conditions separate from the repository.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Paper abstract; framework, tasks, Agent, experimental setup, results, ethics, and limitations sections; referenced repository `LICENSE`
