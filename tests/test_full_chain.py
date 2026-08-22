"""全链路收口测试：冻结样本 → 候选 → 训练 → Episode → 交付。

验证用户视角的完整生命周期（不依赖任何外部平台）。
"""
from __future__ import annotations

import json

from agentfit.agents.orchestrator import Orchestrator
from agentfit.agents.team import build_team
from plugins.dashboard.generate import generate_dashboard
from agentfit.data.sample_pool import SamplePool
from plugins.solution_package import analyze_boundary, export_package
from plugins.boundary import write_boundary
from plugins.solution_package import export_evidence_package
from agentfit.executors.simulator import SimulatorExecutor
from plugins.report import generate_report
from agentfit.models.evidence import CandidateManifest
from agentfit.models.config import AutoApprove, TrainingConfig
from agentfit.models.manifest import (FreezeDecision, SampleSetCollection,
                                      SampleSetManifest, SampleSetPurpose,
                                      default_access_policy)
from agentfit.models.objective import (ObjectiveSpec, PurposeAcceptance,
                                       evaluate_acceptance)
from agentfit.models.sample import Episode, EvaluationIdentity, canonical_hash
from agentfit.monitoring.monitor import check_training_health, detect_drift
from agentfit.solution.builder import build_candidate
from agentfit.solution.validator import validate_existence_dependencies
from agentfit.store.run_store import RunStore

from telecom_world import make_capability_inventory, make_samples


def test_full_chain_intake_to_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTFIT_G3_SIGNING_KEY", "agentfit-test-key-not-for-production-0001")
    monkeypatch.setenv("AGENTFIT_G3_KEY_ID", "pytest")
    samples = make_samples()
    run_dir = tmp_path / "full-chain"

    freeze = FreezeDecision(
        reviewer="human-owner", approved=True,
        decided_at="2026-08-17T15:00:00+08:00", reason="full-chain fixture",
    )
    refs = [sample.ref for sample in samples]
    by_prefix: dict[str, list] = {}
    for sample in samples:
        by_prefix.setdefault(sample.id.split("-")[0], []).append(sample.ref)
    held_out = {by_prefix["F1"][1], by_prefix["F2"][1], by_prefix["F3"][4]}
    refs_by_purpose = {
        SampleSetPurpose.ADAPTATION: tuple(ref for ref in refs if ref not in held_out),
        SampleSetPurpose.VALIDATION: (by_prefix["F1"][1],),      # 训练后通过
        SampleSetPurpose.SEALED_HOLDOUT: (by_prefix["F2"][1],),  # 训练后通过
        SampleSetPurpose.STRESS_AND_FAILURE: (by_prefix["F3"][4],),  # 由训练归纳修复
    }
    collection = SampleSetCollection(tuple(
        SampleSetManifest.create(
            purpose, refs_by_purpose[purpose], default_access_policy(purpose), freeze,
        ) for purpose in SampleSetPurpose
    ))
    objective = ObjectiveSpec.create(
        criteria=tuple(
            PurposeAcceptance(purpose, 0.9, 0, 1.0, 0)
            for purpose in SampleSetPurpose
        ),
        max_total_evaluation_cost_usd=3.0,
    )

    # Human Freeze → Simple First candidate，且只从 adaptation 构建。
    capability_inventory = make_capability_inventory()
    initial = build_candidate(
        samples, collection, capability_inventory, coverage=0.5,
    )
    assert validate_existence_dependencies(initial) == [], "builder 产物必须过存在依赖验证"
    assert len(initial.L4_topology.agents) == 1, "Simple First：初始单 Agent"

    adaptation_ids = {ref.sample_id for ref in refs_by_purpose[SampleSetPurpose.ADAPTATION]}
    adaptation = [sample for sample in samples if sample.id in adaptation_ids]

    # 训练（含 RunStore 落盘、归因、更新和回归）。
    executor = SimulatorExecutor()
    orch = Orchestrator(initial, SamplePool(adaptation), executor,
                        TrainingConfig(
                            batch_size=18,
                            max_epochs=5,
                            review_policy=AutoApprove(
                                delivery_conditions=("human confirmation before write",),
                            ),
                        ),
                        run_dir=str(run_dir), scenario="full-chain")
    build_team(orch)
    outcomes = orch.train()
    assert outcomes[-1].pass_rate >= 0.9, f"全链路训练后应 ≥90%，实际 {outcomes[-1].pass_rate}"
    assert orch.solution.version > 0
    deferred = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert deferred["delivery_approved"] is False
    assert "deferred" in deferred["delivery_review_reason"]

    # Candidate Freeze 后按各集合访问规则生成可追溯 Episode。
    store = RunStore(run_dir)
    store.save_task_samples(samples)
    store.save_capability_inventory(capability_inventory)
    store.save_sample_manifests(collection)
    store.save_objective(objective)
    candidate = CandidateManifest.for_solution(orch.solution)
    store.save_training_candidate_manifest(candidate)
    candidate_ref = candidate.candidate_ref
    by_id = {sample.id: sample for sample in samples}
    actors = {
        SampleSetPurpose.ADAPTATION: "architect",
        SampleSetPurpose.VALIDATION: "validator",
        SampleSetPurpose.SEALED_HOLDOUT: "auditor",
        SampleSetPurpose.STRESS_AND_FAILURE: "auditor",
    }
    evaluation_by_purpose = {}
    for manifest in collection.manifests:
        manifest.require_access(actors[manifest.purpose], candidate_frozen=True)
        results = []
        for ref in manifest.sample_refs:
            sample = by_id[ref.sample_id]
            trace = executor.execute(orch.solution, sample)
            identity = EvaluationIdentity(candidate_ref, ref, 0)
            trace_path = store.save_trace(identity, trace)
            store.save_episode(Episode(
                identity, trace_path.relative_to(store.root).as_posix(), trace.result,
                trace.cost_usd, canonical_hash(trace),
                risk_events=len(trace.risk_events),
            ))
            results.append(trace)
        passed = sum(trace.result == "PASS" for trace in results)
        evaluation_by_purpose[manifest.purpose.value] = {
            "total": len(results),
            "passed": passed,
            "failed": sum(trace.result == "FAIL" for trace in results),
            "errors": sum(trace.result == "ERROR" for trace in results),
            "pass_rate": passed / len(results),
            "cost_usd": round(sum(trace.cost_usd for trace in results), 4),
            "risk_events": sum(len(trace.risk_events) for trace in results),
        }
    assert len(list((run_dir / "episodes").glob("*.json"))) == len(samples)
    acceptance = evaluate_acceptance(objective, evaluation_by_purpose)
    store.save_acceptance(acceptance)
    assert acceptance.met is True
    decision = orch.finalize_delivery({
        "candidate_ref": candidate_ref,
        "candidate_frozen": True,
        "evaluation_by_purpose": evaluation_by_purpose,
        "objective_ref": objective.content_hash,
        "acceptance_ref": acceptance.content_hash,
        "acceptance_met": acceptance.met,
        "acceptance_failures": list(acceptance.failures),
    })
    assert decision.approved is True
    assert decision.conditions == ("human confirmation before write",)
    finalized = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert finalized["delivery_approved"] is True
    assert finalized["delivery_conditions"] == ["human confirmation before write"]

    # 交付：方案包 + 边界分析
    write_boundary(run_dir)
    pkg = export_package(orch.solution, run_dir, delivery_conditions=decision.conditions)
    evidence = export_evidence_package(run_dir)
    boundary = analyze_boundary(run_dir)
    package = json.loads(pkg.read_text())
    assert pkg.exists() and evidence.exists() and "routing_rules" in package
    assert "capability_contracts" in package
    assert "tool_bindings" not in package
    assert all("backend" not in atom for atom in package["solid_atoms"])
    assert package["delivery_conditions"] == ["human confirmation before write"]
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
