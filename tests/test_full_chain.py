"""全链路收口测试：intake → 初始方案构建 → 训练 → 交付 → 报告 → dashboard，一条链跑通。

验证用户视角的完整生命周期（不依赖任何外部平台）。
"""
from __future__ import annotations

import json

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.dashboard import generate_dashboard
from agentfit.data.sample_pool import SamplePool
from agentfit.delivery.package import analyze_boundary, export_package
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.log.report import generate_report
from agentfit.models.config import TrainingConfig
from agentfit.monitoring.monitor import check_training_health, detect_drift
from agentfit.solution.builder import build_initial
from agentfit.solution.validator import validate_existence_dependencies

from telecom_world import make_samples


def test_full_chain_intake_to_delivery(tmp_path):
    samples = make_samples()
    run_dir = tmp_path / "full-chain"

    # intake（简版：直接样本清单）→ 初始方案自动构建（Simple First，覆盖一半聚类）
    initial = build_initial(samples, coverage=0.5)
    assert validate_existence_dependencies(initial) == [], "builder 产物必须过存在依赖验证"
    assert len(initial.L4_topology.agents) == 1, "Simple First：初始单 Agent"

    # 训练（含 RunStore 落盘）
    orch = Orchestrator(initial, SamplePool(samples), SimulatorExecutor(),
                        TrainingConfig(batch_size=21, max_epochs=5),
                        run_dir=str(run_dir), scenario="full-chain")
    build_team(orch)
    outcomes = orch.train()
    assert outcomes[-1].pass_rate >= 0.9, f"全链路训练后应 ≥90%，实际 {outcomes[-1].pass_rate}"

    # 交付：方案包 + 边界分析
    pkg = export_package(orch.solution, run_dir)
    boundary = analyze_boundary(run_dir)
    assert pkg.exists() and "routing_rules" in json.loads(pkg.read_text())
    assert boundary["coverage"] >= 0.9
    assert boundary["recommended_delivery"] in ("全自动", "部分自动")

    # 报告 + dashboard
    report = generate_report(run_dir)
    dash = generate_dashboard(run_dir)
    assert report.exists() and "训练报告" in report.read_text(encoding="utf-8")
    assert dash.exists() and dash.stat().st_size > 5000

    # 监控：健康检查 + 漂移检测接口可用
    summary = json.loads((run_dir / "summary.json").read_text())
    assert check_training_health(summary, budget_usd=10.0) == []
    drift = detect_drift(samples[:10], samples[:10])
    assert drift["alert"] is False
