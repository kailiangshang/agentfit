"""BusinessEngineer — Business discovery engineer.

Responsibilities: read materials, extract facts, problems, constraints,
evidence gaps, and automation boundary. Produces the labeled dataset.

Does NOT: decide final agent architecture.
"""

from __future__ import annotations

from typing import Any

from agentfit.pipeline.contracts import TaskExample


class BusinessEngineer:
    name = "BusinessEngineer"
    role = "Business Discovery Engineer"

    def discover(
        self,
        materials: list[dict],
        problem: str,
        scenario_config: dict[str, Any],
        dossier,
    ) -> dict:
        facts = scenario_config.get("facts", [])
        boundary = scenario_config.get("automation_boundary", {})

        dossier.write("discover", self.name, "write_facts", {"facts": facts})
        dossier.write("discover", self.name, "write_boundary", {"boundary": boundary})

        dataset = self._build_dataset(scenario_config)
        dossier.write("discover", self.name, "write_dataset", {
            "dataset": [
                {
                    "task_id": t.task_id,
                    "input": t.input,
                    "expected_output": t.expected_output,
                    "difficulty": t.difficulty,
                    "tags": t.tags,
                }
                for t in dataset
            ],
        })

        return {"facts_count": len(facts), "dataset_size": len(dataset), "boundary": boundary}

    def _build_dataset(self, config: dict) -> list[TaskExample]:
        raw_examples = config.get("examples", [])
        dataset = []
        for idx, ex in enumerate(raw_examples):
            input_with_meta = dict(ex["input"])
            input_with_meta["_req"] = ex.get("req", [])
            input_with_meta["_difficulty"] = ex.get("difficulty", "medium")
            dataset.append(TaskExample(
                task_id=ex.get("task_id", f"ex-{idx:02d}"),
                input=input_with_meta,
                expected_output=ex["expected"],
                difficulty=ex.get("difficulty", "medium"),
                tags=ex.get("tags", []),
            ))
        return dataset

    def create_trial_spec(
        self,
        dataset: list[TaskExample],
        scenario_config: dict,
    ) -> dict:
        train_ratio = scenario_config.get("train_ratio", 0.5)
        split_idx = int(len(dataset) * train_ratio)

        difficulties = {}
        for ex in dataset:
            d = ex.difficulty
            difficulties.setdefault(d, []).append(ex)

        train_ids = [t.task_id for t in dataset[:split_idx]]
        test_ids = [t.task_id for t in dataset[split_idx:]]

        return {
            "dataset": dataset,
            "train_split": train_ids,
            "test_split": test_ids,
            "acceptance_criteria": scenario_config.get("acceptance_criteria", {
                "accuracy": 0.80,
                "max_overfit": 0.15,
                "max_tokens": 50000,
            }),
            "complexity_budget": scenario_config.get("complexity_budget", 50.0),
            "fault_plan": scenario_config.get("fault_plan", []),
        }
