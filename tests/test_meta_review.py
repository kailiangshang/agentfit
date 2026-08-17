"""运行完成仪制测试：train() 自动产出 训练结果 + AgentFit 自身建议。"""
from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.data.sample_pool import SamplePool
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.models.config import AutoApprove, TrainingConfig

from telecom_world import make_initial_solution, make_samples


def test_run_ritual_produces_both_artifacts(tmp_path):
    run_dir = tmp_path / "ritual-run"
    orch = Orchestrator(make_initial_solution(), SamplePool(make_samples()),
                        SimulatorExecutor(), TrainingConfig(batch_size=21, max_epochs=3,
                                                            review_policy=AutoApprove()),
                        run_dir=str(run_dir), scenario="ritual")
    build_team(orch)
    orch.train()

    report = run_dir / "training_report.md"
    review = run_dir / "meta_review.md"
    assert report.exists(), "训练结果报告必须自动生成"
    assert review.exists(), "AgentFit 自身建议必须自动生成"
    assert "训练报告" in report.read_text(encoding="utf-8")
    review_text = review.read_text(encoding="utf-8")
    assert "运行信号" in review_text and "## 建议" in review_text
    assert any(t in review_text for t in ("Attributor", "Orchestrator", "Architect", "LambdaController"))
