# Evidence Card: SWE-bench

## Identity

- `evidence_id`: `swe-bench`
- `domain`: `software`
- `source_title`: `SWE-bench: Can Language Models Resolve Real-World GitHub Issues?`
- `canonical_url`: https://github.com/SWE-bench/SWE-bench
- `publication_or_access_date`: ICLR 2024; source accessed 2026-08-07
- `organization_or_authors`: Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, and Karthik R. Narasimhan
- `evidence_level`: `E2` — public benchmark with a containerized evaluation harness
- `license`: MIT

## Verified Facts

All statements in this section are `verified_fact`.

- `task_input`: A real GitHub codebase and an issue description.
- `expected_output`: A patch intended to resolve the described issue; the harness evaluates patch predictions against repository tests.
- `reported_roles`: The benchmark does not prescribe Agent roles.
- `coordination_topology`: `not_reported_by_source`; systems are evaluated by their final patch, not by a required internal topology.
- `tools_and_state`: Repository state, issue text, patch predictions, a Docker-based evaluation harness, build logs, evaluation logs, and result files.
- `human_gate`: SWE-bench Verified contains 500 problems that real software engineers confirmed were solvable; the benchmark does not define a runtime approval gate for generated patches.
- `reported_metrics`: The README reports the 500-case Verified subset but does not report one required solver score for this evidence card.
- `stated_limitations`: Local evaluation is resource intensive; the README recommends roughly 120 GB of free virtual disk for Docker Desktop and notes that published images target Linux.
- `reproducibility`: Public datasets, Docker images or local image builds, evaluation commands, gold-patch verification, and stored evaluation outputs support full benchmark reproduction subject to compute and disk requirements.

## AgentFit Interpretation

All statements in this section are `agentfit_inference`, not source claims.

- `candidate_graph_patterns`: Compare a deterministic issue-to-test Workflow, a single repair Agent with a test-feedback loop, and a modular graph separating reproduction, localization, patch generation, and ranking.
- `agentize_signals`: Repository exploration and repair are path-dependent, while test execution provides an objective local feedback signal; multi-Agent separation should be admitted only if it beats simpler candidates under the same budget.
- `non_llm_alternatives`: Retrieval, static analysis, fault localization, rule-based patch templates, test generation, search, and human-authored fixes.
- `possible_adaptation_data`: A fixed subset of training or Lite instances, stratified by repository and issue type.
- `possible_holdout_data`: Unseen repositories or a sealed portion of Verified, preventing same-repository leakage.
- `possible_failure_injection`: Missing dependencies, non-reproducing tests, incorrect localization, patches that only satisfy visible tests, excessive tool use, and Docker setup failure.
- `transfer_pair_candidates`: `masai` as same-task architecture evidence; operational diagnosis tasks as an adjacent diagnose-act-verify family.

## Open Questions

All items in this section are `open_question`.

- `unsupported_claims`: Whether a multi-Agent implementation improves resolution, latency, or cost over a single Agent on the chosen fixed split.
- `missing_artifacts`: A competition-scale sealed split, common budget envelope, and AgentTeams execution traces do not yet exist.
- `license_or_data_questions`: Individual source repositories represented in the benchmark may impose their own licenses even though the SWE-bench code is MIT.

## Provenance

- `checked_by`: Codex, with OpenCode GLM-5.1 used only for draft extraction
- `checked_at`: 2026-08-07
- `source_sections`: Repository README `Overview`, `Set Up`, `Usage`, `Downloads`, and `Citation & license`; README news entries for SWE-bench Verified and Docker evaluation
