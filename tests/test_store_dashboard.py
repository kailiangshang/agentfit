"""RunStore 落盘 + Dashboard 生成的架构完整性测试。"""
import json

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.dashboard import generate_dashboard
from agentfit.data.sample_pool import SamplePool
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.models.config import AutoApprove, TrainingConfig

from telecom_world import make_initial_solution, make_samples


def _train_with_store(tmp_path):
    samples = make_samples()
    run_dir = tmp_path / "run-001"
    orch = Orchestrator(make_initial_solution(), SamplePool(samples), SimulatorExecutor(),
                        TrainingConfig(batch_size=21, max_epochs=3, review_policy=AutoApprove()),
                        run_dir=str(run_dir), scenario="test-telecom")
    build_team(orch)
    orch.train()
    return run_dir


def test_runstore_full_artifacts(tmp_path):
    run_dir = _train_with_store(tmp_path)
    required = ["run.json", "samples.json", "summary.json",
                "epochs/epoch_001.json", "loss_traces/epoch_001",
                "solution_versions/v000.json", "solution_versions/v001.json",
                "messages/epoch_001.json"]
    for rel in required:
        assert (run_dir / rel).exists(), f"缺少产物 {rel}"
    record = json.loads((run_dir / "epochs" / "epoch_001.json").read_text())
    assert "entry" in record and "hash" in record and "previous_hash" in record, "epoch 落盘必须带哈希链"
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["final_pass_rate"] >= 0.9 and summary["log_chain_valid"] is True


def test_dashboard_generates_and_renders(tmp_path):
    run_dir = _train_with_store(tmp_path)
    out = generate_dashboard(run_dir)
    html = out.read_text()
    assert out.exists() and len(html) > 5000
    for section in ("运行概览", "材料与四层映射", "样本与聚类分组", "训练曲线",
                    "损失归因全景", "版本演化", "事务与中间链路"):
        assert section in html, f"dashboard 缺少区块 {section}"
    payload = json.loads(html.split("const DATA = ")[1].split(";\n")[0])
    assert payload["summary"]["final_pass_rate"] >= 0.9


def test_dashboard_cli(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    run_dir = _train_with_store(tmp_path)
    src = Path(__file__).resolve().parents[1] / "src"
    env = {**os.environ, "PYTHONPATH": str(src)}
    r = subprocess.run([sys.executable, "-m", "agentfit.dashboard", str(run_dir)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert (run_dir / "dashboard.html").exists()
