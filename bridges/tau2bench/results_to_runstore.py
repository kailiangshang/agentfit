#!/usr/bin/env python3
"""桥接：tau2-bench results.json → AgentFit RunStore 标准目录（可出 dashboard）。

用法：
  PYTHONPATH=src python bridges/tau2bench/results_to_runstore.py \
      ../tau2-bench/data/simulations/agentfit-smoke-001/results.json \
      --run-dir output/tau2-smoke-001 --label agentfit-smoke-001
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from agentfit.store.run_store import RunStore  # noqa: E402
from agentfit.log.training_log import EpochEntry, TrainingLog  # noqa: E402
from agentfit.models.loss import Expected, Sample, Trace, TraceStep  # noqa: E402
from agentfit.models.sample import (Episode, EvaluationIdentity, TaskSample,  # noqa: E402
                                    canonical_hash)

# tau2 telecom 根因 → 布尔特征（聚类展示用）
FEATURE_MAP = {
    "airplane_mode_on": "airplane",
    "data_mode_off": "data_mode_off",
    "data_saver_mode_on": "data_saver",
    "bad_network_preference": "bad_network",
    "data_usage_exceeded": "data_exceeded",
    "user_abroad_roaming_enabled_off": "roaming_off_abroad",
    "user_abroad_roaming_disabled_on": "roaming_on_abroad",
}


def _cost(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return float((value or {}).get("total_cost_usd", 0))


def _features(simulation: dict) -> dict[str, bool]:
    task_id = str(simulation.get("task_id", ""))
    return {feature: True for cause, feature in FEATURE_MAP.items() if cause in task_id}


def simulation_to_task_sample(simulation: dict) -> TaskSample:
    """Convert one τ² task/run record into the canonical semantic Sample."""
    task_id = str(simulation.get("task_id") or canonical_hash(simulation)[:16])
    features = _features(simulation)
    return TaskSample(
        id=task_id,
        observation_refs=(),
        input_data={"task_id": task_id, "features": features},
        expected=Expected(),
        evaluator="tau2_reward",
        constraints={"source": "tau2-bench"},
        complexity="compound" if len(features) >= 2 else "simple",
    )


def _tool_names(simulation: dict) -> list[str]:
    calls = list(simulation.get("tool_calls") or [])
    for message in simulation.get("messages") or []:
        calls.extend(message.get("tool_calls") or [])
    names = []
    for call in calls:
        if isinstance(call, str):
            names.append(call)
        elif isinstance(call, dict):
            name = call.get("name") or (call.get("function") or {}).get("name")
            if name:
                names.append(str(name))
    return names


def simulation_to_episode(simulation: dict, task: TaskSample, *,
                          candidate_ref: str, run_index: int,
                          trace_ref: str | None = None) -> tuple[Episode, Trace]:
    reward = (simulation.get("reward_info") or {}).get("reward", 0)
    error = simulation.get("error") or simulation.get("exception")
    result = "ERROR" if error else "PASS" if reward == 1 else "FAIL"
    trace = Trace(
        sample_id=task.id,
        result="PASS" if result == "PASS" else "FAIL",
        steps=[TraceStep(layer="L2", element_id=name, action="tool_call", ok=True)
               for name in _tool_names(simulation)],
        cost_usd=_cost(simulation.get("agent_cost")) + _cost(simulation.get("user_cost")),
    )
    if error:
        trace.steps.append(TraceStep(
            layer="L2", element_id="tau2_runtime", action="error", ok=False,
            error=str(error),
        ))
    identity = EvaluationIdentity(candidate_ref, task.ref, run_index)
    episode = Episode(
        identity=identity,
        trace_ref=trace_ref or f"traces/{identity.key}.json",
        result=result,
        cost_usd=trace.cost_usd,
        evidence_hash=canonical_hash(simulation),
    )
    return episode, trace


def convert(results_path: Path, run_dir: str, label: str,
            candidate_ref: str | None = None) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    store = RunStore(run_dir)
    candidate_ref = candidate_ref or canonical_hash({
        "bridge": "tau2bench", "candidate": label,
        "config": data.get("config") or data.get("info") or data.get("metadata") or {},
    })
    if not data.get("simulations"):
        raise ValueError("τ² results contain no simulations")
    task_by_id: dict[str, TaskSample] = {}
    trial_counts: dict[str, int] = {}
    for simulation in data["simulations"]:
        task = simulation_to_task_sample(simulation)
        previous = task_by_id.get(task.id)
        if previous is not None and previous.content_hash != task.content_hash:
            raise ValueError(f"τ² task id maps to conflicting content: {task.id}")
        task_by_id.setdefault(task.id, task)
        trial_counts[task.id] = trial_counts.get(task.id, 0) + 1
    store.init_run({"scenario": f"tau2-telecom-baseline:{label}", "executor": "tau2bench-bridge",
                    "config": {"num_tasks": len(task_by_id), "num_trials": max(trial_counts.values())},
                    "candidate_ref": candidate_ref,
                    "source_results_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest()})
    store.save_source_results(data)

    task_samples = list(task_by_id.values())
    store.save_task_samples(task_samples)
    store.save_samples([
        Sample(
            id=task.id, features=dict(task.input_data.get("features", {})), expected=task.expected,
            complexity=task.complexity, group="control",
        ) for task in task_samples
    ])

    per_task, total_cost = [], 0.0
    run_indices: dict[str, int] = {}
    for simulation in data["simulations"]:
        task = task_by_id[simulation_to_task_sample(simulation).id]
        run_index = run_indices.get(task.id, 0)
        run_indices[task.id] = run_index + 1
        episode, trace = simulation_to_episode(
            simulation, task, candidate_ref=candidate_ref, run_index=run_index,
        )
        trace_path = store.save_trace(episode.identity, trace)
        if episode.trace_ref != trace_path.relative_to(store.root).as_posix():
            raise ValueError("τ² trace reference does not match persisted trace")
        store.save_episode(episode)
        total_cost += episode.cost_usd
        reward = (simulation.get("reward_info") or {}).get("reward", 0)
        per_task.append({"sample_id": task.id, "task_id": simulation.get("task_id"),
                         "pass": episode.result == "PASS", "reward": reward,
                         "cost_usd": round(episode.cost_usd, 4)})

    passed = sum(1 for t in per_task if t["pass"])
    log = TrainingLog()
    log.append(EpochEntry(
        epoch=1, solution_version=0, pass_rate=passed / len(per_task),
        loss_distribution={}, updates_applied=[], regularization={}, behavioral={},
        regression={"tested": 0, "passed": 0},
        lambda_values={"L1": 0.1, "L2": 0.2, "L3": 0.3, "L4": 0.4},
        cost_usd=round(total_cost, 4), rolled_back=False,
        note="baseline 裸跑（无 AgentFit 训练）",
    ))
    store.save_epoch(1, log.entries[0], [])
    store.save_messages(1, [])
    store.save_summary({"epochs_run": 1, "final_pass_rate": passed / len(per_task),
                        "final_solution_version": 0, "lambda_values": {},
                        "total_cost_usd": round(total_cost, 4), "converged": True,
                        "budget_exceeded": False, "log_chain_valid": log.verify(),
                        "baseline": True, "per_task": per_task,
                        "transactions_committed": [], "transactions_rolled_back": []})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_json")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--label", default="tau2-run")
    parser.add_argument("--candidate-ref", default=None,
                        help="64-character immutable candidate hash; otherwise derived from label and result config")
    args = parser.parse_args()
    convert(Path(args.results_json), args.run_dir, args.label, args.candidate_ref)
    print(f"RunStore: {args.run_dir}")


if __name__ == "__main__":
    main()
