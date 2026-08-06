"""Scenario 1: Expense/Invoice Approval — Linear DAG wins.

Expected outcome: minimal complexity candidate is sufficient.
Demonstrates Occam's Razor in architecture selection.
"""
from __future__ import annotations

from agentfit.agents.llm_sim import LLMSimulator
from agentfit.pipeline.contracts import CandidateCard, TaskExample


CAPS = {
    "linear-rules": {"rule_match"},
    "router-rule-llm": {"rule_match", "simple_llm"},
    "react-overkill": {"rule_match", "simple_llm", "self_correct"},
}

SCENARIO_CONFIG = {
    "domain": "finance",
    "facts": [
        {"fact": "Thresholds: <500 auto, 500-5000 manager, >5000 director", "source": "policy.pdf"},
        {"fact": "Missing tax ID requires rejection", "source": "policy.pdf"},
        {"fact": "Duplicate detection requires 30-day history check", "source": "policy.pdf"},
    ],
    "automation_boundary": {
        "automate": ["amount classification", "threshold routing", "duplicate flag"],
        "human_review": ["policy exceptions >10000"],
        "reject": ["fraud investigation"],
    },
    "examples": [
        {"task_id": "exp-01", "input": {"amount": 200, "type": "meals", "tax_id": "valid", "dup": 0},
         "expected": "approve_auto", "difficulty": "easy", "tags": ["simple"], "req": ["rule_match"]},
        {"task_id": "exp-02", "input": {"amount": 3500, "type": "travel", "tax_id": "valid", "dup": 0},
         "expected": "approve_manager", "difficulty": "easy", "tags": ["simple"], "req": ["rule_match"]},
        {"task_id": "exp-03", "input": {"amount": 200, "type": "meals", "tax_id": "missing", "dup": 0},
         "expected": "reject_tax", "difficulty": "easy", "tags": ["edge"], "req": ["rule_match"]},
        {"task_id": "exp-04", "input": {"amount": 15000, "type": "equipment", "tax_id": "valid", "dup": 3},
         "expected": "flag_dup", "difficulty": "medium", "tags": ["edge"], "req": ["rule_match", "simple_llm"]},
        {"task_id": "exp-05", "input": {"amount": 800, "type": "software", "tax_id": "valid", "dup": 0},
         "expected": "approve_auto", "difficulty": "easy", "tags": ["simple"], "req": ["rule_match"]},
        {"task_id": "exp-06", "input": {"amount": 6500, "type": "travel", "tax_id": "valid", "dup": 0},
         "expected": "approve_director", "difficulty": "easy", "tags": ["simple"], "req": ["rule_match"]},
        {"task_id": "exp-07", "input": {"amount": 4200, "type": "training", "tax_id": "valid", "dup": 1},
         "expected": "approve_manager_dup_review", "difficulty": "medium", "tags": ["edge"], "req": ["rule_match", "simple_llm"]},
        {"task_id": "exp-08", "input": {"amount": 300, "type": "supplies", "tax_id": "valid", "dup": 0},
         "expected": "approve_auto", "difficulty": "easy", "tags": ["simple"], "req": ["rule_match"]},
    ],
    "candidate_configs": [
        {"id": "linear-rules", "pattern": "linear", "type": "no-agent",
         "rationale": "Expense approval is primarily rule-based: thresholds + tax ID. Linear pipeline of rules handles majority of cases.",
         "expected_fit": "Standard approvals, rejections, routing",
         "expected_failure": "Duplicate detection and nuanced edge cases",
         "params": {"stages": [("rule_classify", "Rule: classify amount"), ("rule_decide", "Rule: decide")]}},
        {"id": "router-rule-llm", "pattern": "router", "type": "single-agent",
         "rationale": "Adds LLM branch for edge cases (duplicates) while keeping rule fast path for most traffic.",
         "expected_fit": "All standard + edge case classification",
         "expected_failure": "Complex fraud patterns",
         "params": {"branches": ["simple", "edge"]}},
        {"id": "react-overkill", "pattern": "react", "type": "single-agent",
         "rationale": "Explores whether iterative reasoning improves accuracy. Expected to be overkill for this simple domain.",
         "expected_fit": "Everything router handles, with unnecessary iteration",
         "expected_failure": "High cost, no accuracy gain",
         "params": {"max_iterations": 3}},
    ],
    "acceptance_criteria": {"accuracy": 0.85, "max_overfit": 0.15, "max_tokens": 50000},
    "complexity_budget": 30.0,
    "train_ratio": 0.5,
}


def resolver(card: CandidateCard, example: TaskExample, is_train: bool) -> bool:
    candidate_caps = CAPS.get(card.candidate_id, set())
    required = set(example.input.get("_req", []))
    return required.issubset(candidate_caps)


def build_llm_simulator() -> LLMSimulator:
    sim = LLMSimulator()
    def handler(ctx, mem, cfg):
        return {"output": "processed", "done": True}
    sim.register_default(handler)
    return sim


SCENARIO_CONFIG["resolver"] = resolver
SCENARIO_CONFIG["build_llm_simulator"] = build_llm_simulator
