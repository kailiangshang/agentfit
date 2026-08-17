"""全链路收口测试：冻结样本 → 候选 → 训练 → Episode → 交付。

验证用户视角的完整生命周期（不依赖任何外部平台）。
"""
from __future__ import annotations

import json
import copy

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from agentfit.dashboard import generate_dashboard
from agentfit.data.sample_pool import SamplePool
from agentfit.delivery.package import analyze_boundary, export_package
from agentfit.delivery.boundary import write_boundary
from agentfit.delivery.package import export_evidence_package
from agentfit.executors.simulator import SimulatorExecutor
from agentfit.log.report import generate_report
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.models.manifest import (FreezeDecision, SampleSetCollection,
                                      SampleSetManifest, SampleSetPurpose,
                                      default_access_policy)
from agentfit.models.sample import Episode, EvaluationIdentity, canonical_hash, task_sample_from_legacy
from agentfit.monitoring.monitor import check_training_health, detect_drift
from agentfit.solution.builder import build_candidate
from agentfit.solution.validator import validate_existence_dependencies
from agentfit.store.run_store import RunStore

from telecom_world import make_samples


def test_full_chain_intake_to_delivery(tmp_path):
    samples = make_samples()
    run_dir = tmp_path / "full-chain"

    freeze = FreezeDecision(
        reviewer="human-owner", approved=True,
        decided_at="2026-08-17T15:00:00+08:00", reason="full-chain fixture",
    )
    refs = [task_sample_from_legacy(sample).ref for sample in samples]
    refs_by_purpose = {
        SampleSetPurpose.ADAPTATION: tuple(refs[:18]),
        SampleSetPurpose.VALIDATION: (refs[18],),
        SampleSetPurpose.SEALED_HOLDOUT: (refs[19],),
        SampleSetPurpose.STRESS_AND_FAILURE: (refs[20],),
    }
    collection = SampleSetCollection(tuple(
        SampleSetManifest.create(
            purpose, refs_by_purpose[purpose], default_access_policy(purpose), freeze,
        ) for purpose in SampleSetPurpose
    ))

    # Human Freeze → Simple First candidate，且只从 adaptation 构建。
    initial = build_candidate(samples, collection, coverage=0.5)
    assert validate_existence_dependencies(initial) == [], "builder 产物必须过存在依赖验证"
    assert len(initial.L4_topology.agents) == 1, "Simple First：初始单 Agent"

    adaptation_ids = {ref.sample_id for ref in refs_by_purpose[SampleSetPurpose.ADAPTATION]}
    adaptation = []
    for sample in samples:
        if sample.id in adaptation_ids:
            clone = copy.deepcopy(sample)
            clone.group = "train"
            adaptation.append(clone)

    # 训练（含 RunStore 落盘、归因、更新和回归）。
    executor = SimulatorExecutor()
    orch = Orchestrator(initial, SamplePool(adaptation), executor,
                        TrainingConfig(batch_size=18, max_epochs=5, review_policy=AutoApprove()),
                        run_dir=str(run_dir), scenario="full-chain")
    build_team(orch)
    outcomes = orch.train()
    assert outcomes[-1].pass_rate >= 0.9, f"全链路训练后应 ≥90%，实际 {outcomes[-1].pass_rate}"
    assert orch.solution.version > 0

    # Candidate Freeze 后按各集合访问规则生成可追溯 Episode。
    store = RunStore(run_dir)
    store.save_samples(samples)
    store.save_sample_manifests(collection)
    candidate_ref = canonical_hash(orch.solution)
    by_id = {sample.id: sample for sample in samples}
    actors = {
        SampleSetPurpose.ADAPTATION: "architect",
        SampleSetPurpose.VALIDATION: "validator",
        SampleSetPurpose.SEALED_HOLDOUT: "auditor",
        SampleSetPurpose.STRESS_AND_FAILURE: "auditor",
    }
    for manifest in collection.manifests:
        manifest.require_access(actors[manifest.purpose], candidate_frozen=True)
        for ref in manifest.sample_refs:
            sample = by_id[ref.sample_id]
            trace = executor.execute(orch.solution, sample)
            identity = EvaluationIdentity(candidate_ref, ref, 0)
            trace_path = store.save_trace(identity, trace)
            store.save_episode(Episode(
                identity, trace_path.relative_to(store.root).as_posix(), trace.result,
                trace.cost_usd, canonical_hash(trace),
            ))
    assert len(list((run_dir / "episodes").glob("*.json"))) == len(samples)

    # 交付：方案包 + 边界分析
    write_boundary(run_dir)
    pkg = export_package(orch.solution, run_dir)
    evidence = export_evidence_package(run_dir)
    boundary = analyze_boundary(run_dir)
    assert pkg.exists() and evidence.exists() and "routing_rules" in json.loads(pkg.read_text())
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
