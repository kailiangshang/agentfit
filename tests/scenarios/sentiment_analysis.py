"""Scenario 2: Product Sentiment Analysis — SCC (self-correction loop) wins.

Expected outcome: evaluator-optimizer or react-loop with SCC significantly
outperforms linear baseline. Demonstrates value of bounded iteration (SCC)
for nuanced understanding tasks.
"""
from __future__ import annotations

from agentfit.agents.llm_sim import LLMSimulator
from agentfit.pipeline.contracts import CandidateCard, TaskExample


CAPS = {
    "linear-keyword": {"keyword_match"},
    "single-llm": {"keyword_match", "basic_llm"},
    "react-scc": {"keyword_match", "basic_llm", "self_correct"},
    "eval-opt-scc": {"keyword_match", "basic_llm", "self_correct", "quality_eval"},
}

SCENARIO_CONFIG = {
    "domain": "ecommerce",
    "facts": [
        {"fact": "Product reviews contain mixed sentiment requiring context understanding", "source": "reviews.csv"},
        {"fact": "Sarcasm and irony are present in ~15% of reviews", "source": "analysis.txt"},
        {"fact": "Single-pass keyword matching misses 45% of nuanced cases", "source": "baseline_test.json"},
    ],
    "automation_boundary": {
        "automate": ["sentiment classification", "aspect extraction", "trend aggregation"],
        "human_review": ["cultural nuance", "brand-sensitive judgments"],
        "reject": ["legal sentiment disputes"],
    },
    "examples": [
        {"task_id": "sent-01", "input": {"text": "Great quality, fast shipping"}, "expected": "positive", "difficulty": "easy", "tags": ["keyword"], "req": ["keyword_match"]},
        {"task_id": "sent-02", "input": {"text": "Terrible, broke in 2 days"}, "expected": "negative", "difficulty": "easy", "tags": ["keyword"], "req": ["keyword_match"]},
        {"task_id": "sent-03", "input": {"text": "Cheap but works, returned it anyway"}, "expected": "mixed", "difficulty": "medium", "tags": ["nuanced"], "req": ["basic_llm"]},
        {"task_id": "sent-04", "input": {"text": "Wow, amazing quality... if you enjoy garbage"}, "expected": "negative", "difficulty": "hard", "tags": ["sarcasm"], "req": ["basic_llm", "self_correct"]},
        {"task_id": "sent-05", "input": {"text": "Good value for money"}, "expected": "positive", "difficulty": "easy", "tags": ["keyword"], "req": ["keyword_match"]},
        {"task_id": "sent-06", "input": {"text": "Used 3 times, hinge snapped. Refund? No response."}, "expected": "negative", "difficulty": "easy", "tags": ["keyword"], "req": ["keyword_match"]},
        {"task_id": "sent-07", "input": {"text": "The specs are great but the execution falls short of promises"}, "expected": "mixed", "difficulty": "hard", "tags": ["nuanced"], "req": ["basic_llm", "self_correct"]},
        {"task_id": "sent-08", "input": {"text": "Perfect gift, recipient loved it"}, "expected": "positive", "difficulty": "easy", "tags": ["keyword"], "req": ["keyword_match"]},
        {"task_id": "sent-09", "input": {"text": "Sure, 'premium' material that peels after a week"}, "expected": "negative", "difficulty": "hard", "tags": ["sarcasm"], "req": ["basic_llm", "self_correct", "quality_eval"]},
        {"task_id": "sent-10", "input": {"text": "Does the job, nothing special"}, "expected": "neutral", "difficulty": "medium", "tags": ["nuanced"], "req": ["basic_llm"]},
    ],
    "candidate_configs": [
        {"id": "linear-keyword", "pattern": "linear", "type": "no-agent",
         "rationale": "Baseline: keyword matching only. Cheapest possible. Expected to underfit on nuanced/sarcastic reviews.",
         "expected_fit": "Clear positive/negative keyword cases",
         "expected_failure": "Sarcasm, mixed sentiment, neutral classification",
         "params": {"stages": [("rule_keyword", "Rule: keyword match"), ("rule_classify", "Rule: classify")]}},
        {"id": "single-llm", "pattern": "router", "type": "single-agent",
         "rationale": "Single LLM pass for nuanced cases. Handles mixed sentiment but may miss sarcasm without self-checking.",
         "expected_fit": "Keyword + nuanced cases, misses sarcasm without iteration",
         "expected_failure": "Sarcastic reviews requiring second-pass reflection",
         "params": {"branches": ["keyword", "nuanced"]}},
        {"id": "react-scc", "pattern": "react", "type": "single-agent",
         "rationale": "ReAct loop with SCC: LLM reasons, checks own output, iterates if uncertain. Self-correction catches sarcasm via second-pass.",
         "expected_fit": "All cases including most sarcasm through iterative reflection",
         "expected_failure": "Very subtle cultural sarcasm",
         "params": {"max_iterations": 3}},
        {"id": "eval-opt-scc", "pattern": "evaluator_optimizer", "type": "single-agent",
         "rationale": "Evaluator-optimizer SCC: generate sentiment → evaluate confidence → refine. Adds explicit quality gate.",
         "expected_fit": "All cases with highest accuracy due to explicit quality evaluation loop",
         "expected_failure": "Extremely ambiguous cases where even evaluator is uncertain",
         "params": {"max_iterations": 3}},
    ],
    "acceptance_criteria": {"accuracy": 0.80, "max_overfit": 0.15, "max_tokens": 100000},
    "complexity_budget": 40.0,
    "train_ratio": 0.5,
}


def resolver(card: CandidateCard, example: TaskExample, is_train: bool) -> bool:
    candidate_caps = CAPS.get(card.candidate_id, set())
    required = set(example.input.get("_req", []))
    return required.issubset(candidate_caps)


def build_llm_simulator() -> LLMSimulator:
    sim = LLMSimulator()
    def handler(ctx, mem, cfg):
        return {"output": "analyzed", "done": True, "iterate": False}
    sim.register_default(handler)
    return sim


SCENARIO_CONFIG["resolver"] = resolver
SCENARIO_CONFIG["build_llm_simulator"] = build_llm_simulator
