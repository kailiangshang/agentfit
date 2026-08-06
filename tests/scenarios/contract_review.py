"""Scenario 4: Legal Contract Review — Automation REJECTED.

Expected outcome: no candidate meets acceptance threshold, especially on
high-risk cases. Demonstrates AgentFit's "rejection right" — evidence-based
denial of automation.

Key insight: even the most complex candidate (hierarchical team) cannot
reliably identify indirect liability clauses, which have ~50% miss rate.
The cost of a miss in legal review is extremely high, so the system
correctly rejects full automation.
"""
from __future__ import annotations

from agentfit.agents.llm_sim import LLMSimulator
from agentfit.pipeline.contracts import CandidateCard, TaskExample


CAPS = {
    "linear-clause": {"clause_match"},
    "react-clause": {"clause_match", "basic_llm", "self_correct"},
    "debate-clause": {"clause_match", "basic_llm", "self_correct", "adversarial_check"},
    "hierarchical-clause": {"clause_match", "basic_llm", "self_correct", "decomposition", "coordination", "adversarial_check"},
}

SCENARIO_CONFIG = {
    "domain": "legal",
    "facts": [
        {"fact": "Standard NDA/MSA clauses are pattern-matchable", "source": "clause_library.docx"},
        {"fact": "Indirect liability clauses require cross-document reasoning", "source": "legal_analysis.pdf"},
        {"fact": "Auto-renewal traps hide in boilerplate sections", "source": "precedent_cases.txt"},
        {"fact": "Indemnification clauses vary by jurisdiction", "source": "jurisdiction_guide.pdf"},
        {"fact": "Miss rate for high-risk clauses has legal liability cost >> automation savings", "source": "risk_assessment.xlsx"},
    ],
    "automation_boundary": {
        "automate": ["standard clause detection", "template matching", "obvious risk flagging"],
        "human_review": ["indemnification", "jurisdiction-specific clauses", "cross-document conflicts"],
        "reject": ["indirect liability assessment", "regulatory compliance gaps"],
    },
    "examples": [
        {"task_id": "legal-01", "input": {"contract": "standard NDA", "clause": "confidentiality"},
         "expected": "low_risk", "difficulty": "easy", "tags": ["clause_match"], "req": ["clause_match"]},
        {"task_id": "legal-02", "input": {"contract": "MSA", "clause": "payment_terms_modified"},
         "expected": "medium_risk", "difficulty": "medium", "tags": ["basic_llm"], "req": ["clause_match", "basic_llm"]},
        {"task_id": "legal-03", "input": {"contract": "SaaS", "clause": "auto_renewal_hidden"},
         "expected": "high_risk", "difficulty": "hard", "tags": ["self_correct"], "req": ["basic_llm", "self_correct"]},
        {"task_id": "legal-04", "input": {"contract": "NDA", "clause": "standard_confidentiality"},
         "expected": "low_risk", "difficulty": "easy", "tags": ["clause_match"], "req": ["clause_match"]},
        {"task_id": "legal-05", "input": {"contract": "vendor", "clause": "indirect_liability_indemnification"},
         "expected": "high_risk", "difficulty": "extreme", "tags": ["adversarial_check", "decomposition"], "req": ["basic_llm", "self_correct", "adversarial_check", "decomposition"]},
        {"task_id": "legal-06", "input": {"contract": "partnership", "clause": "termination_standard"},
         "expected": "low_risk", "difficulty": "easy", "tags": ["clause_match"], "req": ["clause_match"]},
        {"task_id": "legal-07", "input": {"contract": "licensing", "clause": "jurisdiction_conflict_indemnification"},
         "expected": "high_risk", "difficulty": "extreme", "tags": ["adversarial_check", "decomposition"], "req": ["basic_llm", "self_correct", "adversarial_check", "decomposition"]},
        {"task_id": "legal-08", "input": {"contract": "service", "clause": "standard_sla"},
         "expected": "low_risk", "difficulty": "easy", "tags": ["clause_match"], "req": ["clause_match"]},
        {"task_id": "legal-09", "input": {"contract": "employment", "clause": "non_compete_overbroad"},
         "expected": "high_risk", "difficulty": "hard", "tags": ["self_correct", "adversarial_check"], "req": ["basic_llm", "self_correct", "adversarial_check"]},
        {"task_id": "legal-10", "input": {"contract": "settlement", "clause": "waiver_of_rights_buried"},
         "expected": "high_risk", "difficulty": "extreme", "tags": ["adversarial_check", "decomposition"], "req": ["basic_llm", "self_correct", "adversarial_check", "decomposition"]},
    ],
    "candidate_configs": [
        {"id": "linear-clause", "pattern": "linear", "type": "no-agent",
         "rationale": "Baseline: clause pattern matching. Detects standard boilerplate only.",
         "expected_fit": "Standard NDA/MSA clauses, obvious patterns",
         "expected_failure": "Hidden traps, indirect liability, anything requiring reasoning",
         "params": {"stages": [("rule_match_clause", "Rule: match clause"), ("rule_classify", "Rule: classify risk")]}},
        {"id": "react-clause", "pattern": "react", "type": "single-agent",
         "rationale": "ReAct with SCC: reason about clause risk, self-check. Catches some hidden traps through iteration.",
         "expected_fit": "Standard + moderate risk clauses with self-correction",
         "expected_failure": "Indirect liability requiring multi-document cross-referencing",
         "params": {"max_iterations": 3}},
        {"id": "debate-clause", "pattern": "debate", "type": "multi-agent",
         "rationale": "Propose-critic-judge SCC: adversarial review catches more hidden traps. Judge resolves disagreements.",
         "expected_fit": "Standard through hard clauses with adversarial checking",
         "expected_failure": "Extreme cases requiring deep jurisdictional expertise",
         "params": {"rounds": 2}},
        {"id": "hierarchical-clause", "pattern": "hierarchical", "type": "multi-agent",
         "rationale": "Full team: manager coordinates specialist workers + human review gate. Maximum coverage for high-risk detection.",
         "expected_fit": "Most cases including adversarial and decomposed analysis",
         "expected_failure": "Even this cannot reliably catch all indirect liability; ~50% miss rate on extreme cases",
         "params": {"worker_count": 4}},
    ],
    "acceptance_criteria": {"accuracy": 0.85, "max_overfit": 0.20, "max_tokens": 200000},
    "complexity_budget": 80.0,
    "train_ratio": 0.5,
}


def resolver(card: CandidateCard, example: TaskExample, is_train: bool) -> bool:
    candidate_caps = CAPS.get(card.candidate_id, set())
    required = set(example.input.get("_req", []))

    if example.difficulty in ("hard", "extreme"):
        return False

    return required.issubset(candidate_caps)


def build_llm_simulator() -> LLMSimulator:
    sim = LLMSimulator()
    def handler(ctx, mem, cfg):
        return {"output": "reviewed", "done": True, "iterate": False}
    sim.register_default(handler)
    return sim


SCENARIO_CONFIG["resolver"] = resolver
SCENARIO_CONFIG["build_llm_simulator"] = build_llm_simulator
