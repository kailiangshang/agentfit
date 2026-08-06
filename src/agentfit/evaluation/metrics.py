"""Evaluation metrics for comparing candidate performance."""
from __future__ import annotations

from typing import Any


def accuracy(predictions: list[Any], ground_truth: list[Any]) -> float:
    if not predictions:
        return 0.0
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(predictions)


def normalized_score(cost: int, accuracy: float, max_cost: int = 100000) -> float:
    if max_cost == 0:
        return accuracy
    cost_factor = 1.0 - (cost / max_cost)
    return accuracy * 0.7 + cost_factor * 0.3


def pareto_efficient(scores: list[dict[str, float]], keys: list[str]) -> list[dict]:
    result = []
    for i, s in enumerate(scores):
        dominated = False
        for j, other in enumerate(scores):
            if i == j:
                continue
            if all(other.get(k, 0) >= s.get(k, 0) for k in keys):
                dominated = True
                break
        if not dominated:
            result.append(s)
    return result
