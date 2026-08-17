#!/usr/bin/env python3
"""桥接：tau2-bench results.json → AgentFit RunStore 标准目录（可出 dashboard）。

用法：
  PYTHONPATH=src python bridges/tau2bench/results_to_runstore.py \
      ../tau2-bench/data/simulations/agentfit-smoke-001/results.json \
      --run-dir output/tau2-smoke-001 --label agentfit-smoke-001
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from agentfit.store.run_store import RunStore  # noqa: E402
from agentfit.log.training_log import EpochEntry, TrainingLog  # noqa: E402

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


def convert(results_path: Path, run_dir: str, label: str) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    store = RunStore(run_dir)
    store.init_run({"scenario": f"tau2-telecom-baseline:{label}", "executor": "tau2bench-bridge",
                    "config": {"num_tasks": len(data["simulations"]), "num_trials": 1},
                    "solution_version_start": 0})

    # 样本（特征从根因组合解析；基线无四层方案，expected 留空）
    from agentfit.models.loss import Expected, Sample
    samples = []
    for i, sim in enumerate(data["simulations"]):
        causes = sim["task_id"].split("]")[1].split("[PERSONA")[0]
        features = {FEATURE_MAP[c]: True for c in causes.split("|") if c in FEATURE_MAP}
        samples.append(Sample(id=f"task-{i:02d}", features=features, expected=Expected(),
                              complexity="compound" if len(features) >= 2 else "simple",
                              group="control"))
    store.save_samples(samples)

    per_task, total_cost = [], 0.0
    for i, sim in enumerate(data["simulations"]):
        reward = (sim.get("reward_info") or {}).get("reward", 0)
        def _cost(c):
            return c if isinstance(c, (int, float)) else (c or {}).get("total_cost_usd", 0)
        cost = _cost(sim.get("agent_cost")) + _cost(sim.get("user_cost"))
        total_cost += cost
        per_task.append({"sample_id": f"task-{i:02d}", "task_id": sim["task_id"],
                         "pass": reward == 1, "reward": reward, "cost_usd": round(cost, 4)})

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
    args = parser.parse_args()
    convert(Path(args.results_json), args.run_dir, args.label)
    print(f"RunStore: {args.run_dir}")


if __name__ == "__main__":
    main()
