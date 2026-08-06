================================================================================
  AgentFit Evaluation Test Report
  ML Methodology for Agent Architecture Selection
================================================================================

## Summary

Scenario               Candidates   Recommendation       Selected   Test Acc
----------------------------------------------------------------------------
Expense Approval                3           deploy router-rule-llm     100.0%
Sentiment Analysis              4           deploy   eval-opt-scc     100.0%
Refund Processing               5           deploy orchestrator-refund     100.0%
Contract Review                 4           reject       REJECTED      40.0%


--------------------------------------------------------------------------------
## Expense Approval

Domain: finance
Pipeline stages: 11 entries, version 11
Dataset: 3 facts extracted, candidates: 3

### State Machine Gates
  [PASS] intake → discover
  [PASS] discover → architect
  [PASS] architect → approve
  [PASS] approve → trial
  [PASS] trial → audit
  [PASS] audit → deliver
  [PASS] deliver → learn

### Candidates (baseline-first ordering)
ID                     Pattern                  Type           Complexity
  ------------------------------------------------------------------------
  linear-rules         linear                 no-agent            2.0
  router-rule-llm      router                 single-agent       13.0
  react-overkill       react                  single-agent       26.0

### Trial Results (train/test split)
Candidate               Train Acc   Test Acc    Overfit     Tokens  Stability
  --------------------------------------------------------------------------
  linear-rules              75.0%      75.0%       0.0%          0      75.0%
  router-rule-llm          100.0%     100.0%       0.0%       6992     100.0%
  react-overkill           100.0%     100.0%       0.0%      13984     100.0%

### Audit Diagnosis
  linear-rules: WELL GENERALIZED: gap 0.0%; MARGINAL: below threshold but promising; UNSTABLE: stability 75.0%
  router-rule-llm: WELL GENERALIZED: gap 0.0%; PASS: meets accuracy threshold
  react-overkill: WELL GENERALIZED: gap 0.0%; PASS: meets accuracy threshold

### Evidence Notes
  • DIMINISHING RETURNS: react-overkill adds 13 complexity for only 0.0% accuracy lift over router-rule-llm

### Recommendation
  Type: DEPLOY
  Select 'router-rule-llm' — minimal sufficient candidate. Test accuracy 100.0%, overfit 0.0%, cost 6992 tokens.

### Assets Produced (for cross-project reuse)
  • [linear] linear-rules — acc=75.0%, domain=finance
  • [router] router-rule-llm — acc=100.0%, domain=finance
  • [react] react-overkill — acc=100.0%, domain=finance


--------------------------------------------------------------------------------
## Sentiment Analysis

Domain: ecommerce
Pipeline stages: 12 entries, version 12
Dataset: 3 facts extracted, candidates: 4

### State Machine Gates
  [PASS] intake → discover
  [PASS] discover → architect
  [PASS] architect → approve
  [PASS] approve → trial
  [PASS] trial → audit
  [PASS] audit → deliver
  [PASS] deliver → learn

### Candidates (baseline-first ordering)
ID                     Pattern                  Type           Complexity
  ------------------------------------------------------------------------
  linear-keyword       linear                 no-agent            2.0
  single-llm           router                 single-agent       17.0
  react-scc            react                  single-agent       26.0
  eval-opt-scc         evaluator_optimizer    single-agent       30.0

### Trial Results (train/test split)
Candidate               Train Acc   Test Acc    Overfit     Tokens  Stability
  --------------------------------------------------------------------------
  linear-keyword            60.0%      40.0%      20.0%          0      50.0%
  single-llm                80.0%      60.0%      20.0%       9080      70.0%
  react-scc                100.0%      80.0%      20.0%      18160      90.0%
  eval-opt-scc             100.0%     100.0%       0.0%      18160     100.0%

### Audit Diagnosis
  linear-keyword: OVERFIT: train 60.0% vs test 40.0% (gap 20.0%); UNDERFIT: significantly below threshold; UNSTABLE: stability 50.0%
  single-llm: OVERFIT: train 80.0% vs test 60.0% (gap 20.0%); UNDERFIT: significantly below threshold; INEFFICIENT: high complexity without payoff; UNSTABLE: stability 70.0%
  react-scc: OVERFIT: train 100.0% vs test 80.0% (gap 20.0%); PASS: meets accuracy threshold
  eval-opt-scc: WELL GENERALIZED: gap 0.0%; PASS: meets accuracy threshold

### Recommendation
  Type: DEPLOY
  Select 'eval-opt-scc' — minimal sufficient candidate. Test accuracy 100.0%, overfit 0.0%, cost 18160 tokens.

### Assets Produced (for cross-project reuse)
  • [evaluator_optimizer] eval-opt-scc — acc=100.0%, domain=ecommerce


--------------------------------------------------------------------------------
## Refund Processing

Domain: ecommerce
Pipeline stages: 11 entries, version 11
Dataset: 4 facts extracted, candidates: 5

### State Machine Gates
  [PASS] intake → discover
  [PASS] discover → architect
  [PASS] architect → approve
  [PASS] approve → trial
  [PASS] trial → audit
  [PASS] audit → deliver
  [PASS] deliver → learn

### Candidates (baseline-first ordering)
ID                     Pattern                  Type           Complexity
  ------------------------------------------------------------------------
  linear-refund        linear                 no-agent            2.0
  router-refund        router                 single-agent       19.0
  react-refund         react                  single-agent       26.0
  orchestrator-refund  orchestrator_worker    multi-agent        28.0
  hierarchical-refund  hierarchical           multi-agent        46.0

### Trial Results (train/test split)
Candidate               Train Acc   Test Acc    Overfit     Tokens  Stability
  --------------------------------------------------------------------------
  linear-refund             40.0%      40.0%       0.0%          0      40.0%
  router-refund             60.0%      60.0%       0.0%       9100      60.0%
  react-refund              60.0%      60.0%       0.0%      18200      60.0%
  orchestrator-refund      100.0%     100.0%       0.0%       9100     100.0%
  hierarchical-refund      100.0%     100.0%       0.0%      18200     100.0%

### Audit Diagnosis
  linear-refund: WELL GENERALIZED: gap 0.0%; UNDERFIT: significantly below threshold; UNSTABLE: stability 40.0%
  router-refund: WELL GENERALIZED: gap 0.0%; UNDERFIT: significantly below threshold; INEFFICIENT: high complexity without payoff; UNSTABLE: stability 60.0%
  react-refund: WELL GENERALIZED: gap 0.0%; UNDERFIT: significantly below threshold; INEFFICIENT: high complexity without payoff; UNSTABLE: stability 60.0%
  orchestrator-refund: WELL GENERALIZED: gap 0.0%; PASS: meets accuracy threshold
  hierarchical-refund: WELL GENERALIZED: gap 0.0%; PASS: meets accuracy threshold

### Evidence Notes
  • DIMINISHING RETURNS: react-refund adds 7 complexity for only 0.0% accuracy lift over router-refund
  • DIMINISHING RETURNS: hierarchical-refund adds 18 complexity for only 0.0% accuracy lift over orchestrator-refund

### Recommendation
  Type: DEPLOY
  Select 'orchestrator-refund' — minimal sufficient candidate. Test accuracy 100.0%, overfit 0.0%, cost 9100 tokens.

### Assets Produced (for cross-project reuse)
  • [orchestrator_worker] orchestrator-refund — acc=100.0%, domain=ecommerce
  • [hierarchical] hierarchical-refund — acc=100.0%, domain=ecommerce


--------------------------------------------------------------------------------
## Contract Review

Domain: legal
Pipeline stages: 12 entries, version 12
Dataset: 5 facts extracted, candidates: 4

### State Machine Gates
  [PASS] intake → discover
  [PASS] discover → architect
  [PASS] architect → approve
  [PASS] approve → trial
  [PASS] trial → audit
  [PASS] audit → deliver
  [PASS] deliver → learn

### Candidates (baseline-first ordering)
ID                     Pattern                  Type           Complexity
  ------------------------------------------------------------------------
  linear-clause        linear                 no-agent            2.0
  react-clause         react                  single-agent       26.0
  debate-clause        debate                 multi-agent        29.0
  hierarchical-clause  hierarchical           multi-agent        55.0

### Trial Results (train/test split)
Candidate               Train Acc   Test Acc    Overfit     Tokens  Stability
  --------------------------------------------------------------------------
  linear-clause             40.0%      40.0%       0.0%          0      40.0%
  react-clause              60.0%      40.0%      20.0%      18160      50.0%
  debate-clause             60.0%      40.0%      20.0%      36320      50.0%
  hierarchical-clause       60.0%      40.0%      20.0%      18160      50.0%

### Audit Diagnosis
  linear-clause: WELL GENERALIZED: gap 0.0%; UNDERFIT: significantly below threshold; UNSTABLE: stability 40.0%
  react-clause: OVERFIT: train 60.0% vs test 40.0% (gap 20.0%); UNDERFIT: significantly below threshold; INEFFICIENT: high complexity without payoff; UNSTABLE: stability 50.0%
  debate-clause: OVERFIT: train 60.0% vs test 40.0% (gap 20.0%); UNDERFIT: significantly below threshold; INEFFICIENT: high complexity without payoff; UNSTABLE: stability 50.0%
  hierarchical-clause: OVERFIT: train 60.0% vs test 40.0% (gap 20.0%); UNDERFIT: significantly below threshold; INEFFICIENT: high complexity without payoff; UNSTABLE: stability 50.0%

### Evidence Notes
  • DIMINISHING RETURNS: react-clause adds 24 complexity for only 0.0% accuracy lift over linear-clause
  • DIMINISHING RETURNS: hierarchical-clause adds 26 complexity for only 0.0% accuracy lift over debate-clause

### Recommendation
  Type: REJECT
  All candidates scored below 51% on test set. Insufficient capability for automation. REJECT.


================================================================================
## Cross-Scenario Analysis

### Pattern Effectiveness Across Scenarios
Pattern                   Scenarios Avg Test Acc Avg Complexity
  --------------------------------------------------------------
  evaluator_optimizer             1       100.0%           30.0
  orchestrator_worker             1       100.0%           28.0
  router                          3        73.3%           16.3
  react                           4        70.0%           26.0
  hierarchical                    2        70.0%           50.5
  linear                          4        48.8%            2.0
  debate                          1        40.0%           29.0

### ML Methodology Verification

  [PASS] Expense Approval: baseline-first (first candidate is minimal)
  [PASS] Sentiment Analysis: baseline-first (first candidate is minimal)
  [PASS] Refund Processing: baseline-first (first candidate is minimal)
  [PASS] Contract Review: baseline-first (first candidate is minimal)
  [PASS] Train/test split enforced (no negative overfit)
  [PASS] Sentiment Analysis/linear-keyword: overfit detected (20.0% gap)
  [PASS] Contract Review/react-clause: overfit detected (20.0% gap)
  [PASS] Rejection right exercised (Contract Review should reject)
  [PASS] Expense Approval: selected cheapest passing candidate (router-rule-llm, complexity=13.0)
  [PASS] Sentiment Analysis: selected cheapest passing candidate (eval-opt-scc, complexity=30.0)
  [PASS] Refund Processing: selected cheapest passing candidate (orchestrator-refund, complexity=28.0)
  [PASS] Reusable assets produced for cross-project learning

================================================================================
  End of Report
================================================================================