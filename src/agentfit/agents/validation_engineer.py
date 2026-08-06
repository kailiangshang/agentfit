"""ValidationEngineer — Validation & reliability engineer.

Responsibilities: create temporary teams, execute tasks, inject faults,
collect evidence. Enforces train/test separation discipline.

Does NOT: modify acceptance criteria after trial starts.

ML methodology in action:
  - fit phase: run candidates on train split (configuration visible)
  - predict phase: run candidates on test split (configuration frozen)
  - fault injection: adversarial testing on both splits
"""

from __future__ import annotations

from typing import Any, Callable

from agentfit.graph.executor import ExecutionResult, GraphExecutor
from agentfit.pipeline.contracts import CandidateCard, CandidateScore, TaskExample, TrialSpec


class ValidationEngineer:
    name = "ValidationEngineer"
    role = "Validation & Reliability Engineer"

    def __init__(self, executor: GraphExecutor):
        self.executor = executor

    def run_trial(
        self,
        candidates: list[CandidateCard],
        graphs: dict[str, Any],
        trial_spec: TrialSpec,
        scenario_config: dict,
    ) -> dict[str, CandidateScore]:
        train_examples = {
            t.task_id: t for t in trial_spec.dataset
            if t.task_id in trial_spec.train_split
        }
        test_examples = {
            t.task_id: t for t in trial_spec.dataset
            if t.task_id in trial_spec.test_split
        }

        resolver: Callable = scenario_config.get("resolver")
        if resolver is None:
            raise ValueError("scenario_config must include a 'resolver' function")

        results: dict[str, CandidateScore] = {}

        for card in candidates:
            graph = graphs.get(card.candidate_id)
            if graph is None:
                continue

            train_results = self._run_split(graph, card, train_examples, trial_spec, resolver, is_train=True)
            test_results = self._run_split(graph, card, test_examples, trial_spec, resolver, is_train=False)

            train_acc = sum(1 for r in train_results if r["solved"]) / max(1, len(train_results))
            test_acc = sum(1 for r in test_results if r["solved"]) / max(1, len(test_results))
            stability = sum(1 for r in train_results + test_results if r["solved"]) / max(1, len(train_results + test_results))

            exec_results = [r["exec_result"] for r in train_results + test_results]
            total_latency = sum(r.total_elapsed_ms for r in exec_results)
            total_tokens = sum(r.token_cost_estimate() for r in exec_results)
            total_human = sum(r.human_interventions for r in exec_results)

            overfit = max(0.0, train_acc - test_acc)

            results[card.candidate_id] = CandidateScore(
                candidate_id=card.candidate_id,
                train_accuracy=train_acc,
                test_accuracy=test_acc,
                latency_ms=total_latency / max(1, len(exec_results)),
                token_cost=total_tokens,
                human_interventions=total_human,
                stability=stability,
                overfit_signal=overfit,
                per_task_results=[
                    {"task_id": r["task_id"], "solved": r["solved"], "split": r["split"]}
                    for r in train_results + test_results
                ],
            )

        return results

    def _run_split(
        self,
        graph,
        card: CandidateCard,
        examples: dict[str, TaskExample],
        trial_spec: TrialSpec,
        resolver: Callable,
        is_train: bool,
    ) -> list[dict]:
        results = []
        split_name = "train" if is_train else "test"

        for task_id, example in examples.items():
            exec_result = self.executor.execute(graph, example.input)
            solved = resolver(card, example, is_train)
            results.append({
                "task_id": task_id,
                "split": split_name,
                "solved": solved,
                "exec_result": exec_result,
            })

        return results
