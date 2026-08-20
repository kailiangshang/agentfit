"""RunStore 落盘 + Dashboard 生成的架构完整性测试。"""
import json
import re

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.dashboard import generate_dashboard
from agentfit.data.sample_pool import SamplePool
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.log.report import generate_report
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.store.run_store import RunStore

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
    required = ["run.json", "task_samples.json", "summary.json",
                "epochs/epoch_001.json", "loss_traces/epoch_001",
                "solution_versions/v000.json", "solution_versions/v001.json",
                "messages/epoch_001.json"]
    for rel in required:
        assert (run_dir / rel).exists(), f"缺少产物 {rel}"
    assert not (run_dir / "samples.json").exists(), "TaskSample 已是唯一运行样本正本"
    record = json.loads((run_dir / "epochs" / "epoch_001.json").read_text())
    assert "entry" in record and "hash" in record and "previous_hash" in record, "epoch 落盘必须带哈希链"
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["final_pass_rate"] >= 0.9 and summary["log_chain_valid"] is True


def test_dashboard_generates_and_renders(tmp_path):
    run_dir = _train_with_store(tmp_path)
    out = generate_dashboard(run_dir)
    html = out.read_text()
    assert out.exists() and len(html) > 5000
    for section in ("运行概览", "四集合验收", "材料与四层映射", "样本与聚类分组", "训练曲线",
                    "损失归因全景", "版本演化", "事务与中间链路"):
        assert section in html, f"dashboard 缺少区块 {section}"
    assert "训练批次通过率" in html
    assert "最终通过率" not in html
    payload = json.loads(html.split("const DATA = ")[1].split(";\n")[0])
    assert payload["summary"]["final_pass_rate"] >= 0.9


def test_dashboard_surfaces_learning_loop_and_per_sample_evidence(tmp_path):
    run_dir = _train_with_store(tmp_path)
    candidate_ref = "a" * 64
    sample_hash = "b" * 64
    trace_rel = "traces/final-error.json"
    (run_dir / "traces").mkdir(exist_ok=True)
    (run_dir / trace_rel).write_text(json.dumps({
        "sample_id": "stress-sample",
        "result": "ERROR",
        "steps": [],
        "risk_events": [],
        "cost_usd": 0.0,
        "error_scope": "runtime",
        "error_code": "agentteams_result_envelope_error",
    }), encoding="utf-8")
    (run_dir / "episodes").mkdir(exist_ok=True)
    (run_dir / "episodes" / "final-error.json").write_text(json.dumps({
        "identity": {
            "candidate_ref": candidate_ref,
            "sample_ref": {
                "sample_id": "stress-sample",
                "content_hash": sample_hash,
            },
            "run_index": 0,
        },
        "trace_ref": trace_rel,
        "result": "ERROR",
        "cost_usd": 0.0,
        "evidence_hash": "c" * 64,
        "status": "completed",
        "risk_events": 0,
        "runtime_ref": "d" * 64,
    }), encoding="utf-8")
    (run_dir / "sample_sets.json").write_text(json.dumps({
        "manifests": [{
            "purpose": "stress_and_failure",
            "sample_refs": [{
                "sample_id": "stress-sample",
                "content_hash": sample_hash,
            }],
        }],
    }), encoding="utf-8")

    html = generate_dashboard(run_dir).read_text(encoding="utf-8")
    payload = json.loads(html.split("const DATA = ")[1].split(";\n")[0])

    assert "训练阶段发生了什么" in html
    assert "逐样本结果" in html
    assert "真实联动效果" not in html
    assert "逐样本最终证据" not in html
    assert payload["training_evidence"]
    assert payload["evaluation_evidence"] == [{
        "purpose": "stress_and_failure",
        "sample_id": "stress-sample",
        "candidate_ref": candidate_ref,
        "run_index": 0,
        "result": "ERROR",
        "error_code": "agentteams_result_envelope_error",
        "route": [],
    }]


def test_dashboard_preserves_canonical_eight_section_order(tmp_path):
    run_dir = _train_with_store(tmp_path)

    html = generate_dashboard(run_dir).read_text(encoding="utf-8")
    # 八区基本证据由静态 HTML 直接呈现（禁用 JS 仍可阅读），顺序即合同
    numbered_headings = re.findall(
        r"<h2>([①②③④⑤⑥⑦⑧][^<]+)</h2>",
        html,
    )

    assert numbered_headings == [
        "① 运行概览",
        "② 四集合验收",
        "③ 材料与四层映射（初始方案）",
        "④ 样本与聚类分组",
        "⑤ 训练曲线",
        "⑥ 损失归因全景",
        "⑦ L1-L4 方案证据与版本演化",
        "⑧ 事务与中间链路",
    ]


def test_dashboard_is_readable_without_javascript(tmp_path):
    run_dir = _train_with_store(tmp_path)

    html = generate_dashboard(run_dir).read_text(encoding="utf-8")

    # 静态正本合同：基本证据不依赖 JavaScript 渲染（无挂载点、无 DOM 构建）
    assert 'id="app"' not in html
    assert "createElement" not in html
    # 训练曲线分列呈现 adaptation 与 validation，不混成一条通过率
    assert "adaptation 通过率" in html
    assert "validation 通过率" in html


def test_dashboard_contains_long_runtime_evidence_on_mobile(tmp_path):
    run_dir = _train_with_store(tmp_path)

    html = generate_dashboard(run_dir).read_text(encoding="utf-8")

    assert "section{min-width:0;overflow-x:auto" in html
    assert ".flow-step{min-width:0;" in html
    assert ".flow-step span{overflow-wrap:anywhere;" in html


def test_dashboard_treats_runstore_values_as_text_not_html(tmp_path):
    run_dir = _train_with_store(tmp_path)
    attack = "</script><img src=x onerror=alert(1)>"
    run_path = run_dir / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["scenario"] = attack
    run_path.write_text(json.dumps(run), encoding="utf-8")
    samples_path = run_dir / "task_samples.json"
    samples = json.loads(samples_path.read_text(encoding="utf-8"))
    samples["samples"][0]["id"] = attack
    samples_path.write_text(json.dumps(samples), encoding="utf-8")

    html = generate_dashboard(run_dir).read_text(encoding="utf-8")

    assert attack not in html
    assert ".innerHTML" not in html
    assert "\\u003c/script\\u003e" in html


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


def test_training_report_marks_all_runtime_rollbacks_as_no_valid_evaluation(tmp_path):
    run_dir = tmp_path / "runtime-failed"
    store = RunStore(run_dir)
    store.init_run({"run_kind": "training"})
    store.save_summary({
        "final_pass_rate": None,
        "final_solution_version": 0,
        "epochs_run": 2,
        "converged": False,
        "total_cost_usd": 0.02,
        "log_chain_valid": True,
        "lambda_values": {},
        "transactions_committed": [],
        "execution_errors": 2,
    })

    report = generate_report(run_dir).read_text(encoding="utf-8")
    dashboard = generate_dashboard(run_dir).read_text(encoding="utf-8")

    assert "训练批次通过率：**—**" in report
    assert "无有效方案评测" in report
    assert "final_pass_rate||0" not in dashboard
    assert "无有效方案评测" in dashboard
