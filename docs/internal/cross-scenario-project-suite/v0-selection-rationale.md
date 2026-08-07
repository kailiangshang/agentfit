# AgentFit Cross-Scenario v0 Selection Rationale

## Decision Status

Status: `proposed_for_user_approval`.

The shortlist contains six projects from five domains. It is designed to test topology selection and transfer, not to showcase six preselected multi-Agent solutions.

## Proposed Projects

### `swe-bench` — software repair substrate

- Structural role: objective patch-and-test task with a strong single-Agent feedback loop and a modular alternative.
- Primary comparison: retrieval/static-analysis Workflow versus one repair Agent versus a MASAI-inspired modular candidate under equalized budgets.
- Admission condition: use a small repository-stratified split that fits competition compute; do not imply production deployment from benchmark patches.

### `aiopslab` — controlled operations source project

- Structural role: stateful observe-act-verify task with fault injection, traces, and custom evaluators.
- Primary comparison: runbook Workflow versus one operational Agent versus bounded detection/localization/analysis/mitigation roles.
- Admission condition: freeze a low-risk local kind problem subset before architecture search.

### `itbench` — operations transfer target

- Structural role: unseen operational environments for testing whether AIOpsLab priors reduce cold-start search cost.
- Primary comparison: target-from-scratch search versus prior-seeded search with identical ITBench holdout and budgets.
- Admission condition: choose locally reproducible scenarios and document every image, cloud, model, and managed-service dependency.

### `tau-bench` — policy-governed interaction and Human boundary

- Structural role: sequential dialogue plus API state mutation where authorization, refusal, and approval can be made measurable.
- Primary comparison: policy Workflow versus one tool Agent versus conversation/policy/action separation with an explicit Human gate.
- Admission condition: replace the checked legacy task snapshot with a separately verified current τ³-bench snapshot before implementation.

### `gaia` — open-tool research and conditional parallelism

- Structural role: heterogeneous research questions for testing whether independent branches justify a fan-out graph.
- Primary comparison: deterministic tool routing versus one research Agent versus budgeted fan-out only on predeclared branchable cases.
- Admission condition: verify dataset license, freeze web-dependent evidence where possible, and score citations/process in addition to final answers.

### `contract-nli` — Agentless-first document baseline

- Structural role: fixed hypotheses, three labels, and evidence spans make a non-Agent supervised pipeline a serious default.
- Primary comparison: Span NLI-style Workflow versus one evidence-checking Agent versus a narrowly bounded clause reviewer and verifier.
- Admission condition: introduce legal-expert approval and abstention rules before presenting any finding as actionable review.

## Proposed Transfer Pair

### `aiopslab` → `itbench`

- Reusable prior: detection/localization/analysis/mitigation task decomposition, trace and evaluator schema, fault-injection taxonomy, safe-action boundaries, and candidate-graph initialization.
- Expected cold-start benefit: reach an accepted ITBench candidate with fewer architecture/prompt trials, fewer evaluation episodes, or lower token/tool cost than target-from-scratch search.
- Required non-regression condition: on a sealed ITBench holdout, the prior-seeded candidate must not reduce task success, safety, or audit completeness relative to the target-from-scratch candidate under the same budget.
- Meta-learning boundary: success on this one pair is transfer evidence, not yet a general Meta-learning claim; the prior may update only after repeated unseen-project validation.

## High-Profile Sources Not Selected as Standalone Projects

- `masai`: retained as an architecture candidate and decomposition prior inside `swe-bench`; selecting it separately would duplicate the same task substrate, and the source license remains unclear.
- `cybench`: scored 92 but is deferred because the first suite already covers local feedback and safety boundaries, while cyber execution adds a disproportionate dual-use authorization and isolation burden.
- `cuad`: scored 89 and is a strong future transfer source, but `contract-nli` has a clearer output contract and verified CC BY 4.0 license; CUAD redistribution terms remain unresolved.
- `crm-arena`: realistic and valuable, but CC BY-NC 4.0, research-only use, external organization state, and requested GUI access reduce competition-package portability.
- `anthropic-multi-agent-research`: retained as E1 production evidence for when parallelism can help, but the internal eval, traces, exact budgets, code, and reuse license are unavailable.
- `purple-llama`: retained as a source of shared safety capability nodes; it is a mixed-license component suite rather than one complete task contract.

## Risks to Resolve Before Project Modeling

1. Freeze exact source versions, task IDs, dataset splits, and immutable hashes; a URL alone is not a reproducible ProjectCase.
2. Verify GAIA and τ³-bench data licenses and every third-party image/model dependency before redistribution.
3. Keep adaptation, validation, holdout, and failure sets disjoint by repository, environment, domain task, or document family rather than random row split alone.
4. Define common cost, latency, token, tool-call, and wall-clock budgets so topology comparisons cannot win by spending more unnoticed resources.
5. Define Human approval, refusal, rollback, and abstention events before any operational, business-state, code, or legal action is evaluated.
6. Preserve Agentless and single-Agent candidates in every applicable search space; the competition's multi-Agent emphasis does not authorize assuming multi-Agent superiority.
7. Derive all competition claims from recorded traces and internal evidence status; simulations must remain labeled as simulations.

## Approval Gate

No completed `ProjectCase`, Agent Identity set, Skill implementation, AgentTeams deployment, or competition result claim may be produced from this shortlist until the user approves or revises the six IDs and the transfer pair.
