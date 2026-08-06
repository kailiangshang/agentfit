"""Scenario 3: Customer Refund Processing — Multi-node DAG + SCC wins.

Expected outcome: orchestrator-worker or hierarchical team significantly
outperforms simpler candidates. Demonstrates complexity-value tradeoff:
baseline underfits, moderate candidates improve, complex candidates show
diminishing returns.
"""
from __future__ import annotations

from agentfit.agents.llm_sim import LLMSimulator
from agentfit.pipeline.contracts import CandidateCard, TaskExample


CAPS = {
    "linear-refund": {"rule_match"},
    "router-refund": {"rule_match", "simple_llm"},
    "react-refund": {"rule_match", "simple_llm", "self_correct"},
    "orchestrator-refund": {"rule_match", "simple_llm", "self_correct", "decomposition", "parallel_exec"},
    "hierarchical-refund": {"rule_match", "simple_llm", "self_correct", "decomposition", "parallel_exec", "coordination"},
}

SCENARIO_CONFIG = {
    "domain": "ecommerce",
    "facts": [
        {"fact": "Refund decisions depend on: amount, item status, policy, order history, fraud signals", "source": "refund_policy.pdf"},
        {"fact": "VIP customers have discretionary override up to 20%", "source": "cs_policy.pdf"},
        {"fact": "Cross-referencing policy + history + fraud requires multi-step reasoning", "source": "analysis.txt"},
        {"fact": "High-value refunds (>5000) need escalation chain", "source": "refund_policy.pdf"},
    ],
    "automation_boundary": {
        "automate": ["standard refunds", "policy lookup", "history check", "fraud flag"],
        "human_review": ["VIP discretionary overrides", "high-value escalations"],
        "reject": ["chargeback disputes", "legal liability cases"],
    },
    "examples": [
        {"task_id": "ref-01", "input": {"amount": 150, "status": "unopened", "reason": "wrong_item"},
         "expected": "auto_approve", "difficulty": "easy", "tags": ["rule_match"], "req": ["rule_match"]},
        {"task_id": "ref-02", "input": {"amount": 800, "status": "defective", "reason": "quality"},
         "expected": "approve_after_check", "difficulty": "medium", "tags": ["simple_llm"], "req": ["rule_match", "simple_llm"]},
        {"task_id": "ref-03", "input": {"amount": 3200, "status": "used", "reason": "not_as_described", "history": "good"},
         "expected": "approve_with_review", "difficulty": "hard", "tags": ["self_correct", "decomposition"], "req": ["simple_llm", "self_correct", "decomposition"]},
        {"task_id": "ref-04", "input": {"amount": 200, "status": "unopened", "reason": "changed_mind"},
         "expected": "auto_approve", "difficulty": "easy", "tags": ["rule_match"], "req": ["rule_match"]},
        {"task_id": "ref-05", "input": {"amount": 5500, "status": "used", "reason": "defective", "history": "disputed"},
         "expected": "escalate_review", "difficulty": "hard", "tags": ["decomposition", "parallel_exec"], "req": ["simple_llm", "self_correct", "decomposition"]},
        {"task_id": "ref-06", "input": {"amount": 450, "status": "arrived_damaged", "reason": "shipping"},
         "expected": "auto_approve", "difficulty": "easy", "tags": ["rule_match"], "req": ["rule_match"]},
        {"task_id": "ref-07", "input": {"amount": 1200, "status": "used_30d", "reason": "slow_degradation", "vip": True},
         "expected": "vip_review", "difficulty": "hard", "tags": ["decomposition", "parallel_exec", "coordination"], "req": ["simple_llm", "self_correct", "decomposition", "parallel_exec"]},
        {"task_id": "ref-08", "input": {"amount": 75, "status": "unopened", "reason": "duplicate_order"},
         "expected": "auto_approve", "difficulty": "easy", "tags": ["rule_match"], "req": ["rule_match"]},
        {"task_id": "ref-09", "input": {"amount": 2800, "status": "parts_missing", "reason": "incomplete", "history": "good", "fraud_flag": False},
         "expected": "approve_with_review", "difficulty": "hard", "tags": ["self_correct", "decomposition"], "req": ["simple_llm", "self_correct", "decomposition"]},
        {"task_id": "ref-10", "input": {"amount": 900, "status": "used", "reason": "not_compatible", "history": "new_customer"},
         "expected": "approve_after_check", "difficulty": "medium", "tags": ["simple_llm"], "req": ["rule_match", "simple_llm"]},
    ],
    "candidate_configs": [
        {"id": "linear-refund", "pattern": "linear", "type": "no-agent",
         "rationale": "Baseline: rule-based amount/status routing. Handles only trivial cases.",
         "expected_fit": "Simple auto-approve cases",
         "expected_failure": "Any case requiring policy lookup, history, or fraud check",
         "params": {"stages": [("rule_amount", "Rule: classify"), ("rule_decide", "Rule: decide")]}},
        {"id": "router-refund", "pattern": "router", "type": "single-agent",
         "rationale": "Adds LLM for moderate cases. Single-pass reasoning without iteration.",
         "expected_fit": "Simple + moderate cases requiring basic LLM reasoning",
         "expected_failure": "Complex multi-factor cases requiring decomposition",
         "params": {"branches": ["simple", "moderate", "complex"]}},
        {"id": "react-refund", "pattern": "react", "type": "single-agent",
         "rationale": "ReAct with SCC: reason-check-iterate. Self-correction improves moderate case accuracy.",
         "expected_fit": "Simple through hard cases requiring self-correction",
         "expected_failure": "Cases requiring parallel decomposition of multiple factors",
         "params": {"max_iterations": 3}},
        {"id": "orchestrator-refund", "pattern": "orchestrator_worker", "type": "multi-agent",
         "rationale": "Orchestrator decomposes complex refunds into subtasks (policy check, history check, fraud check) executed in parallel by workers.",
         "expected_fit": "All cases including complex multi-factor decomposition",
         "expected_failure": "Cases needing human coordination beyond system scope",
         "params": {"worker_count": 3}},
        {"id": "hierarchical-refund", "pattern": "hierarchical", "type": "multi-agent",
         "rationale": "Full hierarchical team: manager → team leader → workers + human review gate. Maximum coordination for high-value escalations.",
         "expected_fit": "All cases including VIP and high-value requiring coordination",
         "expected_failure": "Excessive overhead for simple cases; diminishing returns",
         "params": {"worker_count": 3}},
    ],
    "acceptance_criteria": {"accuracy": 0.80, "max_overfit": 0.15, "max_tokens": 200000},
    "complexity_budget": 60.0,
    "train_ratio": 0.5,
}


def resolver(card: CandidateCard, example: TaskExample, is_train: bool) -> bool:
    candidate_caps = CAPS.get(card.candidate_id, set())
    required = set(example.input.get("_req", []))
    return required.issubset(candidate_caps)


def build_llm_simulator() -> LLMSimulator:
    sim = LLMSimulator()
    def handler(ctx, mem, cfg):
        return {"output": "processed", "done": True, "iterate": False}
    sim.register_default(handler)
    return sim


SCENARIO_CONFIG["resolver"] = resolver
SCENARIO_CONFIG["build_llm_simulator"] = build_llm_simulator
