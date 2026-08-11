# Evidence Card: τ-bench

## Identity

- `evidence_id`: `tau-bench`
- `domain`: `business`
- `source_title`: `τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains`
- `canonical_url`: https://github.com/sierra-research/tau-bench
- `publication_or_access_date`: 2024; source accessed 2026-08-07
- `organization_or_authors`: Sierra Research and τ-bench authors
- `evidence_level`: `E2` — controlled conversational tool-use benchmark
- `license`: MIT

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: A domain task, policy guidelines, simulated-user messages, and airline or retail API state.
- `expected_output`: A completed dialogue and tool trajectory whose resulting state and task completion can be evaluated.
- `reported_roles`: One language Agent, one simulated user, a domain environment, and an evaluator; optional verification/reflection strategies operate inside user simulation.
- `coordination_topology`: Alternating Agent-user interaction mediated by domain APIs and policy, not a team of collaborating task Agents.
- `tools_and_state`: Domain-specific APIs, policy text, airline or retail state, conversation history, user simulators, historical trajectories, result files, and automatic error classification.
- `human_gate`: The benchmark uses an LLM-simulated user by default and does not provide a real-human approval gate.
- `reported_metrics`: The README reports Pass^1 through Pass^4. Its listed best tool-calling row is 0.460/0.326/0.263/0.225 for airline and 0.692/0.576/0.509/0.462 for retail.
- `stated_limitations`: The repository explicitly warns that its airline and retail tasks are outdated and directs users to τ³-bench. Automatic error identification uses an LLM and may be inaccurate; benchmark runs can be costly.
- `reproducibility`: Code, setup commands, task IDs, user-simulator strategies, historical trajectories, and MIT license support reproduction, but model APIs incur external cost and this repository's task versions are superseded.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare a policy-state-machine Workflow, a single tool Agent, and a bounded team separating conversation, policy checking, action planning, and approval.
- `agentize_signals`: User clarification and state changes are sequential and path-dependent; policy checking can remain deterministic while uncertain dialogue may justify an Agent.
- `non_llm_alternatives`: Finite-state dialogue, rules, schema validation, constrained planning, deterministic API orchestration, and human service agents.
- `possible_adaptation_data`: Historical trajectories from one domain and low-risk task classes.
- `possible_holdout_data`: Tasks from another domain, new policy clauses, or unseen user behavior; a future implementation should use a current τ³-bench snapshot rather than silently mixing versions.
- `possible_failure_injection`: Ambiguous user intent, policy conflict, wrong tool arguments, partial goal completion, environment fault, repeated-call instability, and missing approval.
- `future_transfer_conditions`: After a real business-action ProjectCase is complete, compare only targets with compatible policy, approval, state-transition, rollback, license, and runtime-evidence boundaries; this card does not nominate a pair.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether role separation improves Pass^n after equalizing model, tool, and token budgets.
- `missing_artifacts`: A frozen current-version task snapshot and a real-human approval protocol have not been selected.
- `license_or_data_questions`: τ³-bench must be separately checked for current task and license terms before implementation.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README warning and news, introduction, leaderboards, `Run`, `User simulators`, `Auto error identification`, `Historical trajectories`, and `License`; repository `LICENSE`
