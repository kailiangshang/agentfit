"""Telecom 端到端演示：方案是训练出来的。

用法：PYTHONPATH=src:. .venv/bin/python examples/run_telecom_demo.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests", "test_scenarios"))

from agentfit.agents.orchestrator import Orchestrator          # noqa: E402
from agentfit.agents.team import build_team                    # noqa: E402
from agentfit.data.sample_pool import SamplePool               # noqa: E402
from agentfit.executors.simulator import SimulatorExecutor     # noqa: E402
from agentfit.models.config import TrainingConfig              # noqa: E402
from agentfit.solution.validator import validate_existence_dependencies  # noqa: E402
from telecom_world import make_initial_solution, make_samples  # noqa: E402


def main() -> None:
    executor = SimulatorExecutor()
    samples = make_samples()
    initial = make_initial_solution()

    baseline = [executor.evaluate(executor.execute(initial, s), s.expected) for s in samples]
    print(f"\nbaseline（初始最简方案）: {sum(baseline)}/{len(samples)} = {sum(baseline)/len(baseline):.0%}\n")

    run_dir = "output/telecom-demo-001"
    orch = Orchestrator(initial, SamplePool(samples), executor, TrainingConfig(batch_size=21, max_epochs=5),
                        run_dir=run_dir, scenario="telecom-demo")
    build_team(orch)
    outcomes = orch.train()

    print("epoch  pass_rate  rolled_back  proposals  note")
    for o in outcomes:
        print(f"  {o.epoch:<3}  {o.pass_rate:>7.0%}  {str(o.rolled_back):>11}  {o.proposals_count:>9}  {'; '.join(o.notes) or '-'}")

    final = outcomes[-1]
    print(f"\n最终: 通过率 {final.pass_rate:.0%} · 方案版本 v{orch.solution.version}"
          f" · 总成本 ${orch.total_cost():.3f} · 哈希链 {'可验证' if orch.log.verify() else '损坏!'}"
          f" · 依赖检查 {'通过' if validate_existence_dependencies(orch.solution) == [] else '失败!'}")
    print(f"λ: {orch.solution.lambda_values}")
    print(f"路由规则数: {len(orch.solution.routing_rules())} · Agent 数: {len(orch.solution.L4_topology.agents)}")

    from agentfit.dashboard import generate_dashboard
    dash = generate_dashboard(run_dir)
    print(f"dashboard: {dash}\n")


if __name__ == "__main__":
    main()
