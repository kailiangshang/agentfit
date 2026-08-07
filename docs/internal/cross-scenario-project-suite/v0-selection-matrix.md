# AgentFit Cross-Scenario v0 Selection Matrix

## Purpose and Decision Rule

This matrix scores the twelve checked evidence cards before any completed `ProjectCase` is created. Scores select evidence-backed task substrates; they do not assert that an Agent or multi-Agent solution is superior.

Each criterion is scored from 0 to 5. The weighted total is:

```text
total = Σ(score / 5 × criterion_weight)
```

| Key | Criterion | Weight |
|---|---|---:|
| C1 | Source credibility | 20 |
| C2 | Task input/output contract clarity | 15 |
| C3 | Ability to distinguish Agentless, single-Agent, and multi-Agent candidates | 20 |
| C4 | Evaluation and holdout feasibility | 15 |
| C5 | Safety or human-boundary value | 10 |
| C6 | Reproducibility, data access, and license | 10 |
| C7 | Cross-project transfer value | 10 |

## Score Summary

`Selected` means proposed for user approval, not approved for implementation.

| Evidence ID | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Total / 100 | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `swe-bench` | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 98 | Selected |
| `aiopslab` | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 96 | Selected |
| `contract-nli` | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 96 | Selected |
| `itbench` | 5 | 5 | 5 | 4 | 5 | 4 | 5 | 95 | Selected |
| `tau-bench` | 5 | 5 | 4 | 5 | 5 | 4 | 4 | 92 | Selected, current task version required |
| `cybench` | 5 | 5 | 4 | 5 | 5 | 4 | 4 | 92 | Deferred by structural coverage and safety cost |
| `masai` | 5 | 5 | 5 | 4 | 4 | 3 | 4 | 89 | Supporting architecture evidence |
| `cuad` | 5 | 4 | 4 | 5 | 5 | 3 | 5 | 89 | Deferred; license unresolved |
| `gaia` | 5 | 5 | 4 | 5 | 3 | 4 | 4 | 88 | Selected for independent-branch research tests |
| `crm-arena` | 5 | 5 | 4 | 4 | 5 | 2 | 4 | 85 | Deferred; restricted access and license |
| `anthropic-multi-agent-research` | 4 | 5 | 5 | 2 | 4 | 1 | 5 | 77 | Supporting production evidence only |
| `purple-llama` | 4 | 3 | 3 | 4 | 5 | 4 | 4 | 75 | Supporting safety capabilities |

`gaia` replaces the equally high-scoring but structurally overlapping `cybench` slot because the shortlist otherwise lacks an open-ended, independently branchable research task on which a multi-Agent candidate can be tested. This is a structural-property decision, not an industry-count decision. Anthropic's production report supports the candidate boundary but does not prove that multi-Agent GAIA will win.

## Source-Backed Scoring Notes

### `swe-bench` — 98

- `C1 5/5`: ICLR benchmark, public datasets, and a widely inspectable Docker harness provide strong source credibility.
- `C2 5/5`: The README explicitly defines codebase plus issue as input and a resolving patch as output.
- `C3 5/5`: The same patch-and-tests contract can evaluate scripted, single-Agent, and modular repair candidates without changing the target.
- `C4 5/5`: Lite and Verified subsets, repository identities, gold patches, and Docker evaluation support sealed repository-level holdouts.
- `C5 4/5`: Verified includes human solvability review and generated patches require deployment review, although no runtime approval protocol is built into the benchmark.
- `C6 5/5`: MIT code, public data, Docker images, documented commands, logs, and result artifacts support reproduction.
- `C7 5/5`: Repair decomposition and test-feedback priors can be tested against MASAI and adjacent diagnose-act-verify domains.

### `masai` — 89

- `C1 5/5`: The paper provides a controlled SWE-bench Lite evaluation and explicit architecture ablations.
- `C2 5/5`: Repository and issue enter a fixed five-stage graph that produces one ranked patch.
- `C3 5/5`: Its modular graph is directly comparable with single-Agent and simpler SWE-bench baselines under a common harness.
- `C4 4/5`: SWE-bench Lite enables holdout construction, but the selected source does not establish an immutable licensed implementation package.
- `C5 4/5`: The paper explicitly requires expert code review before deployment but has no runtime approval node.
- `C6 3/5`: Experimental details are strong, while implementation license and one-command reproduction remain unresolved from the paper source.
- `C7 4/5`: Role-boundary and artifact-passing priors may transfer, but the source already depends on SWE-bench and is not an independent task family.

### `aiopslab` — 96

- `C1 4/5`: Microsoft publishes a runnable open framework, although the README snapshot contains no comparative outcome table.
- `C2 5/5`: A problem binds application, task, fault, workload, APIs, submitted solution, trace, duration, and evaluator.
- `C3 5/5`: Runbooks, one observe-act Agent, and specialist diagnosis/remediation graphs can share identical fault seeds and evaluators.
- `C4 5/5`: Extensible problems, explicit fault injection, Session traces, and custom evaluators support adaptation, holdout, and stress partitions.
- `C5 5/5`: Detection through mitigation includes observable risk boundaries where deterministic action constraints and human approval can be evaluated.
- `C6 5/5`: MIT code and documented kind, Kubernetes, agent, trace, and evaluator paths support local reproduction.
- `C7 5/5`: Its task taxonomy, traces, evaluators, and fault mechanisms form a concrete prior for ITBench.

### `itbench` — 95

- `C1 5/5`: IBM Research's public benchmark, ICML publication record, scenarios, reference Agents, and leaderboards provide strong provenance.
- `C2 5/5`: SRE, CISO, and FinOps scenarios expose operational environments, tasks, tools, and evaluated outcomes.
- `C3 5/5`: The same Kubernetes scenarios can compare scripted remediation, one reference-style Agent, and bounded specialist teams.
- `C4 4/5`: Scenario mechanisms and managed evaluation support holdouts, while the split between hosted and local paths adds reproducibility work.
- `C5 5/5`: Remediation, compliance, and cost actions create explicit permission, approval, rollback, and competing-objective tests.
- `C6 4/5`: Apache-2.0 deployment tooling and open scenarios are available, but managed evaluation and third-party infrastructure remain external.
- `C7 5/5`: It is a direct same-family target for AIOpsLab task, trace, evaluator, and fault-injection priors.

### `tau-bench` — 92

- `C1 5/5`: The benchmark exposes code, trajectories, policy-governed tasks, and Pass^n leaderboards.
- `C2 5/5`: Domain task, policy, user messages, API state, trajectory, and final completion are explicitly represented.
- `C3 4/5`: A policy Workflow and one tool Agent are natural baselines, while a team is testable but not source-prescribed.
- `C4 5/5`: Task IDs, domains, historical trajectories, state-based results, and repeated-run Pass^n support holdouts and stability tests.
- `C5 5/5`: Policy-governed state mutation and user authorization provide a strong place to test approval and refusal boundaries.
- `C6 4/5`: Code is MIT and runnable, but model APIs cost money and the checked repository explicitly marks its tasks outdated.
- `C7 4/5`: Policy, dialogue, and state-validation priors can transfer to CRM or operational action tasks after version alignment.

### `crm-arena` — 85

- `C1 5/5`: Salesforce AI Research supplies papers, datasets, evaluation code, and realistic organization/API environments.
- `C2 5/5`: CRM tasks, organization state, configured strategies, interactions, results, and logs form a clear contract.
- `C3 4/5`: Workflow and single-Agent baselines are direct, while specialist-team value remains an unverified candidate.
- `C4 4/5`: Public datasets and scripts enable partitioning, but GUI access and external organization state restrict sealed local reproduction.
- `C5 5/5`: Customer-record and business-process writes make authorization, approval, and rollback materially important.
- `C6 2/5`: CC BY-NC 4.0 and research-only use, requested GUI access, Salesforce state, and model APIs constrain reuse.
- `C7 4/5`: It is an adjacent target for τ-bench dialogue, policy, and action-validation priors.

### `anthropic-multi-agent-research` — 77

- `C1 4/5`: The source describes an identifiable production system, but its internal evaluation cannot be independently inspected.
- `C2 5/5`: Open-ended query, delegated research branches, aggregation, and cited answer are clearly described.
- `C3 5/5`: The article directly contrasts single- and multi-Agent research and identifies tasks unsuitable for a team.
- `C4 2/5`: The internal query set, grader, exact budgets, traces, and implementation are not public.
- `C5 4/5`: Citation processing and human testing are important boundaries, though no mandatory runtime approval gate is defined.
- `C6 1/5`: No public evaluation package, dataset, code, or reuse license is supplied by the article.
- `C7 5/5`: The reported conditions for useful parallelism are highly reusable as search priors across research-like projects.

### `gaia` — 88

- `C1 5/5`: The paper provides a public benchmark, human baseline, held-out-answer leaderboard, and identifiable authorship.
- `C2 5/5`: Each task has a real-world question and a concise factual answer despite heterogeneous tool paths.
- `C3 4/5`: Tool routing and one assistant are direct baselines, and independently branchable questions can test conditional fan-out without assuming it wins.
- `C4 5/5`: Three levels, 466 questions, and 300 held-out answers support stratified adaptation and sealed evaluation.
- `C5 3/5`: Source citation and tool safety matter, but final-answer grading and the paper provide no runtime human gate.
- `C6 4/5`: Public questions and leaderboard enable evaluation, while dataset licensing and changing web sources need additional controls.
- `C7 4/5`: Research decomposition, tool routing, and source-verification priors can transfer to policy or document tasks.

### `cybench` — 92

- `C1 5/5`: ICLR publication, 40 specified CTF tasks, multi-model experiments, and explicit evaluator design provide strong evidence.
- `C2 5/5`: Task, files, environment, actions, observations, subtasks, and exact flag output form a precise contract.
- `C3 4/5`: Tool scripts and one Agent are natural baselines, while role separation is testable but not source-demonstrated.
- `C4 5/5`: Competition- and vulnerability-family splits plus exact flags and subtasks support holdout and partial scoring.
- `C5 5/5`: Dual-use cyber actions make authorization, isolation, refusal, and human approval central evaluation properties.
- `C6 4/5`: Apache-2.0 framework resources exist, but task artifacts and secure isolated execution add dependencies.
- `C7 4/5`: Tool-loop and safety-gate priors can transfer, although the domain creates exceptional risk rather than a low-cost first transfer.

### `purple-llama` — 75

- `C1 4/5`: Meta publishes recognized eval and safeguard components, but the README is a suite overview rather than one controlled end-to-end task study.
- `C2 3/5`: Inputs and outputs vary by component, so there is no single ProjectCase contract without additional selection.
- `C3 3/5`: Most components are capability gates and do not themselves distinguish full Agent topologies.
- `C4 4/5`: Individual benchmarks can form holdouts, but the suite requires a separately defined integrated evaluation.
- `C5 5/5`: Prompt, content, code, and cyber safeguards are directly relevant to safety and refusal boundaries.
- `C6 4/5`: Evals and Code Shield are MIT, while safeguard models use distinct Llama Community licenses.
- `C7 4/5`: Selected safeguards can transfer as shared capability nodes across many ProjectCases.

### `cuad` — 89

- `C1 5/5`: NeurIPS publication, expert annotations, public code, and checkpoints provide a credible research basis.
- `C2 4/5`: Contract text and review categories map to evidence spans, though the README is less explicit than ContractNLI's fixed hypothesis schema.
- `C3 4/5`: Strong extraction baselines allow Agentless comparison, while team value is possible but not source-demonstrated.
- `C4 5/5`: Document- and category-level partitions, expert labels, and checkpoints support holdout evaluation.
- `C5 5/5`: Legal findings require evidence, abstention, and expert review before action.
- `C6 3/5`: Data and code are available, but no repository license was found and documented dependencies are dated.
- `C7 5/5`: Contract encoders, evidence spans, and clause categories are strong priors for ContractNLI.

### `contract-nli` — 96

- `C1 5/5`: EMNLP publication, 607 expert-annotated contracts, public data, and a cited baseline provide strong provenance.
- `C2 5/5`: Seventeen fixed hypotheses map to three labels plus evidence spans for every contract.
- `C3 4/5`: A supervised Span NLI baseline is strong, while iterative or multi-Agent review remains a falsifiable candidate rather than an assumption.
- `C4 5/5`: Documents, sources, labels, hypotheses, and spans support document-family holdouts and targeted stress sets.
- `C5 5/5`: Evidence-grounded legal conclusions, exceptions, abstention, and expert review form meaningful human boundaries.
- `C6 5/5`: CC BY 4.0 data, schema documentation, downloads, source URLs, and baseline code support task reproduction.
- `C7 5/5`: Contract representation and evidence-span priors can be tested in both directions with CUAD and other long-document tasks.

## Structural Coverage Check

| Required property | Proposed project | Why it is covered |
|---|---|---|
| Fixed Workflow is a serious baseline | `contract-nli` | Fixed hypotheses, supervised labels, and evidence spans make an Agentless NLI pipeline the default challenger. |
| Local feedback loop or single Agent may be necessary | `aiopslab` | Observation changes after actions and evaluators consume full traces. |
| Multi-Agent boundaries may be justified | `gaia` | Only independently branchable research questions enter the multi-Agent candidate arm; Anthropic's E1 report supplies supporting boundary conditions, not a result claim. |
| Meaningful Human approval or refusal boundary | `tau-bench` | Policy-governed state mutation allows explicit approval, refusal, and unauthorized-action tests using a current task snapshot. |
| Same-family or adjacent-family transfer pair | `aiopslab` → `itbench` | Both expose operational environments, diagnosis/remediation tasks, traces, fault mechanisms, and evaluators. |
| At least three domains | Six projects across five domains | Software, operations, business, research, and documents are represented. |

## Selection Boundary

The matrix proposes which task substrates should advance. It does not freeze task splits, create completed `ProjectCase` packages, implement AgentTeams identities, or claim any runtime result. Those actions remain behind user approval.
