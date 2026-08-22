"""Stable core CLI: train, validate, report and export without platform imports."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from plugins.materials.compiler import compile_material_bundle
from agentfit.models.loss import Expected, ExpectedAction
from agentfit.models.manifest import AccessPolicy, FreezeDecision, SampleSetManifest, SampleSetPurpose
from agentfit.models.project import CapabilityInventory
from agentfit.models.sample import (
    EvaluationIdentity,
    ObservationRef,
    SampleRef,
    TaskSample,
    canonical_hash,
)
from agentfit.models.solution import CapabilityTool, SolidAtom


REPO = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO / "src"),
        "AGENTFIT_G3_SIGNING_KEY": "agentfit-test-key-not-for-production-0001",
        "AGENTFIT_G3_KEY_ID": "pytest",
    }
    return subprocess.run(
        [sys.executable, "-m", "agentfit", *args],
        cwd=REPO, env=env, capture_output=True, text=True,
    )


def _material_bundle(*, min_pass_rate: float = 0.0) -> dict:
    purposes = ("adaptation", "validation", "sealed_holdout", "stress_and_failure")
    return {
        "scenario": "cli-fixture",
        "materials": [{
            "id": "procedure",
            "kind": "procedure",
            "content": "Diagnose the condition and apply the matching safe fix.",
            "metadata": {"source": "fixture"},
        }],
        "capabilities": {
            "atoms": [
                {"id": f"fix_{index}", "type": "write"}
                for index in range(1, 5)
            ],
            "tools": [
                {"id": f"safe_fix_{index}", "wraps": [f"fix_{index}"]}
                for index in range(1, 5)
            ],
        },
        "objective": {
            "criteria": [{
                "purpose": purpose,
                "min_pass_rate": min_pass_rate,
                "max_errors": 0,
                "max_cost_usd": 1.0,
                "max_risk_events": 0,
            } for purpose in purposes],
            "max_total_evaluation_cost_usd": 3.0,
        },
        "tasks": [{
            "id": f"sample-{index}",
            "purpose": purpose,
            "observation_ids": ["procedure"],
            "input_data": {f"condition_{index}": True},
            "expected": {
                "actions": [{"tool": f"safe_fix_{index}", "params": {}}],
                "outcome": {},
            },
            "requires_human": False,
            "complexity": "simple",
        } for index, purpose in enumerate(purposes, 1)],
        "freeze": {
            "reviewer": "human-owner",
            "approved": True,
            "decided_at": "2026-08-17T15:00:00+08:00",
            "reason": "CLI fixture approved",
        },
        "training": {"batch_size": 1, "max_epochs": 1},
    }


def _write_case(path: Path, *, min_pass_rate: float = 0.0) -> None:
    path.write_text(
        json.dumps(
            compile_material_bundle(
                _material_bundle(min_pass_rate=min_pass_rate)
            ).to_case_document(),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_material_bundle(path: Path, *, min_pass_rate: float = 0.0) -> None:
    path.write_text(
        json.dumps(
            _material_bundle(min_pass_rate=min_pass_rate), ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _append_task_to_case(path: Path, purpose: str, task_id: str,
                         input_data: dict, tool: str) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    source = document["source_observations"][0]
    task = TaskSample(
        id=task_id,
        observation_refs=(ObservationRef(source["id"], source["content_hash"]),),
        input_data=input_data,
        expected=Expected([ExpectedAction(tool)]),
    )
    document["task_samples"].append(asdict(task))
    inventory_data = document["capability_inventory"]
    atom_id = tool.removeprefix("safe_")
    atoms = [SolidAtom(**item) for item in inventory_data["atoms"]]
    tools = [CapabilityTool(**item) for item in inventory_data["tools"]]
    if not any(item.id == atom_id for item in atoms):
        atoms.append(SolidAtom(atom_id, "write"))
    if not any(item.id == tool for item in tools):
        tools.append(CapabilityTool(tool, [atom_id]))
    document["capability_inventory"] = asdict(
        CapabilityInventory.create(atoms=atoms, tools=tools)
    )
    for index, item in enumerate(document["sample_sets"]):
        if item["purpose"] != purpose:
            continue
        policy_data = item["access_policy"]
        policy = AccessPolicy(
            readers=tuple(policy_data["readers"]),
            allows_updates=bool(policy_data.get("allows_updates", False)),
            requires_candidate_freeze=bool(policy_data.get("requires_candidate_freeze", False)),
        )
        freeze = FreezeDecision(**item["freeze"])
        refs = tuple(SampleRef(**ref) for ref in item["sample_refs"]) + (task.ref,)
        manifest = SampleSetManifest.create(SampleSetPurpose(purpose), refs, policy, freeze)
        document["sample_sets"][index] = {
            **asdict(manifest), "purpose": manifest.purpose.value,
        }
        break
    path.write_text(json.dumps(document), encoding="utf-8")


def test_cli_help_lists_stable_commands() -> None:
    result = _run("--help")
    assert result.returncode == 0, result.stderr
    for command in ("compile", "train", "validate", "report", "export"):
        assert command in result.stdout


def test_compile_writes_one_canonical_case_and_refuses_overwrite(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    case = tmp_path / "case.json"
    _write_material_bundle(bundle)

    compiled = _run("compile", "--bundle", str(bundle), "--output", str(case))
    assert compiled.returncode == 0, compiled.stderr
    document = json.loads(case.read_text(encoding="utf-8"))
    assert len(document["source_observations"]) == 1
    assert len(document["task_samples"]) == 4
    assert len(document["sample_sets"]) == 4
    assert len(document["capability_inventory"]["atoms"]) == 4
    assert len(document["objective"]["criteria"]) == 4
    assert document["objective"]["content_hash"]

    repeated = _run("compile", "--bundle", str(bundle), "--output", str(case))
    assert repeated.returncode != 0
    assert "output already exists" in repeated.stderr


def test_compiled_case_trains_and_persists_material_lineage(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_material_bundle(bundle)
    assert _run("compile", "--bundle", str(bundle), "--output", str(case)).returncode == 0

    trained = _run(
        "train", "--case", str(case), "--output", str(run_dir), "--auto-approve",
    )
    assert trained.returncode == 0, trained.stderr
    assert (run_dir / "source_observations.json").is_file()
    assert (run_dir / "task_samples.json").is_file()
    assert (run_dir / "capability_inventory.json").is_file()
    assert (run_dir / "objective.json").is_file()
    assert (run_dir / "acceptance.json").is_file()
    assert json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["run_kind"] == "training"
    assert _run("validate", str(run_dir)).returncode == 0


def test_train_rejects_case_without_capability_inventory(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    _write_case(case)
    document = json.loads(case.read_text(encoding="utf-8"))
    document.pop("capability_inventory")
    case.write_text(json.dumps(document), encoding="utf-8")

    trained = _run(
        "train", "--case", str(case), "--output", str(tmp_path / "run"),
        "--auto-approve",
    )

    assert trained.returncode != 0
    assert "capability inventory" in trained.stderr


def test_train_rejects_case_without_objective(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    _write_case(case)
    document = json.loads(case.read_text(encoding="utf-8"))
    document.pop("objective")
    case.write_text(json.dumps(document), encoding="utf-8")

    trained = _run(
        "train", "--case", str(case), "--output", str(tmp_path / "run"),
        "--auto-approve",
    )

    assert trained.returncode != 0
    assert "objective" in trained.stderr


def test_validate_recomputes_capability_inventory_hash(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run(
        "train", "--case", str(case), "--output", str(run_dir), "--auto-approve",
    ).returncode == 0
    inventory_path = run_dir / "capability_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["atoms"][0]["description"] = "tampered contract"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    validated = _run("validate", str(run_dir))

    assert validated.returncode != 0
    assert "capability inventory content_hash" in validated.stderr


def test_train_rejects_case_without_persisted_source_observations(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    _write_case(case)
    document = json.loads(case.read_text(encoding="utf-8"))
    document.pop("source_observations")
    case.write_text(json.dumps(document), encoding="utf-8")

    trained = _run(
        "train", "--case", str(case), "--output", str(tmp_path / "run"),
        "--auto-approve",
    )

    assert trained.returncode != 0
    assert "source observations" in trained.stderr


def test_validate_recomputes_source_observation_hash(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_material_bundle(bundle)
    assert _run("compile", "--bundle", str(bundle), "--output", str(case)).returncode == 0
    assert _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve").returncode == 0

    path = run_dir / "source_observations.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["observations"][0]["content"] = "tampered material"
    path.write_text(json.dumps(document), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "observation content_hash" in validated.stderr


def test_validate_rejects_task_reference_to_unknown_observation(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_material_bundle(bundle)
    assert _run("compile", "--bundle", str(bundle), "--output", str(case)).returncode == 0
    assert _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve").returncode == 0

    path = run_dir / "source_observations.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["observations"][0]["id"] = "renamed-observation"
    path.write_text(json.dumps(document), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "observation reference mismatch" in validated.stderr


def test_validate_rejects_missing_runstore(tmp_path: Path) -> None:
    result = _run("validate", str(tmp_path / "missing"))
    assert result.returncode != 0
    assert "invalid RunStore" in result.stderr


def test_train_validate_report_and_export_round_trip(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)

    trained = _run(
        "train", "--case", str(case), "--output", str(run_dir),
        "--auto-approve",
    )
    assert trained.returncode == 0, trained.stderr
    assert (run_dir / "sample_sets.json").is_file()
    assert len(list((run_dir / "episodes").glob("*.json"))) == 4
    assert len(list((run_dir / "traces").glob("*.json"))) == 4
    assert (run_dir / "summary.json").is_file()
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    decision = json.loads((run_dir / "delivery_decision.json").read_text(encoding="utf-8"))
    assert set(summary["evaluation_by_purpose"]) == {
        "adaptation", "validation", "sealed_holdout", "stress_and_failure",
    }
    assert summary["delivery_approved"] is True
    assert summary["acceptance_met"] is True
    assert summary["acceptance_failures"] == []
    final_candidate_path = run_dir / "candidate_manifests" / f"{summary['candidate_ref']}.json"
    assert final_candidate_path.is_file()
    final_candidate = json.loads(final_candidate_path.read_text(encoding="utf-8"))
    assert final_candidate["kind"] == "agentfit.solution"
    assert final_candidate["content_hash"] == summary["candidate_ref"]
    for episode_path in (run_dir / "episodes").glob("*.json"):
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        trace = json.loads((run_dir / episode["trace_ref"]).read_text(encoding="utf-8"))
        assert episode["runtime_ref"] == trace["runtime_ref"] == run["runtime_ref"]
    assert decision["signature_algorithm"] == "hmac-sha256"
    assert decision["key_id"] == "pytest"
    assert len(decision["signature"]) == 64
    assert "agentfit-test-key-not-for-production" not in json.dumps(decision)

    validated = _run("validate", str(run_dir))
    assert validated.returncode == 0, validated.stderr
    assert "RunStore valid" in validated.stdout

    reported = _run("report", str(run_dir))
    assert reported.returncode == 0, reported.stderr
    assert (run_dir / "training_report.md").is_file()
    assert (run_dir / "dashboard.html").is_file()
    report = (run_dir / "training_report.md").read_text(encoding="utf-8")
    dashboard = (run_dir / "dashboard.html").read_text(encoding="utf-8")
    for rendered in (report, dashboard):
        assert "训练批次通过率" in rendered
        assert "四集合验收" in rendered
        assert "最终通过率" not in rendered
        for purpose in (
            "adaptation", "validation", "sealed_holdout", "stress_and_failure",
        ):
            assert purpose in rendered
    assert "验收结论：**PASS**" in report
    assert "G3 交付：**APPROVED**" in report
    assert "验收 PASS" in dashboard
    assert "G3 APPROVED" in dashboard

    exported = _run("export", str(run_dir))
    assert exported.returncode == 0, exported.stderr
    package = json.loads((run_dir / "solution_package" / "package.json").read_text(encoding="utf-8"))
    evidence = json.loads((run_dir / "evidence_package" / "manifest.json").read_text(encoding="utf-8"))
    boundary = json.loads((run_dir / "boundary.json").read_text(encoding="utf-8"))
    assert package["package_manifest"]["content_hash"]
    assert package["agent_config"]["topology"]["agents"]
    assert package["delivery_conditions"] == []
    assert "summary.json" in evidence["files"]
    assert boundary["evidence_source"] == "episodes"


def test_unmet_objective_deterministically_rejects_g3_and_export(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case, min_pass_rate=1.0)

    trained = _run(
        "train", "--case", str(case), "--output", str(run_dir),
        "--auto-approve",
    )

    assert trained.returncode == 0, trained.stderr
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    decision = json.loads(
        (run_dir / "delivery_decision.json").read_text(encoding="utf-8")
    )
    assert summary["evaluation_by_purpose"]["adaptation"]["pass_rate"] == 1.0
    assert summary["evaluation_by_purpose"]["validation"]["pass_rate"] == 0.0
    assert summary["acceptance_met"] is False
    assert summary["delivery_approved"] is False
    assert any("validation.pass_rate" in item for item in summary["acceptance_failures"])
    assert decision["approved"] is False
    assert decision["reviewer"] == "objective-gate"
    assert decision["signature_algorithm"] == "unsigned"
    assert _run("validate", str(run_dir)).returncode == 0
    reported = _run("report", str(run_dir))
    assert reported.returncode == 0, reported.stderr
    report = (run_dir / "training_report.md").read_text(encoding="utf-8")
    dashboard = (run_dir / "dashboard.html").read_text(encoding="utf-8")
    assert "验收结论：**REJECT**" in report
    assert "G3 交付：**REJECTED**" in report
    assert "validation.pass_rate" in report
    assert "验收 REJECT" in dashboard
    assert "G3 REJECTED" in dashboard
    assert "validation.pass_rate" in dashboard
    exported = _run("export", str(run_dir))
    assert exported.returncode != 0
    assert "G3" in exported.stderr


def test_validate_recomputes_objective_and_acceptance_hashes(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run(
        "train", "--case", str(case), "--output", str(run_dir), "--auto-approve",
    ).returncode == 0

    objective_path = run_dir / "objective.json"
    objective = json.loads(objective_path.read_text(encoding="utf-8"))
    objective["criteria"][0]["min_pass_rate"] = 0.9
    objective_path.write_text(json.dumps(objective), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "objective content_hash" in validated.stderr


def test_validate_recomputes_epoch_hash_chain(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    trained = _run(
        "train", "--case", str(case), "--output", str(run_dir),
        "--auto-approve",
    )
    assert trained.returncode == 0, trained.stderr

    epoch_path = run_dir / "epochs" / "epoch_001.json"
    epoch = json.loads(epoch_path.read_text(encoding="utf-8"))
    epoch["entry"]["pass_rate"] = 0.123
    epoch_path.write_text(json.dumps(epoch), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "hash chain" in validated.stderr


def test_train_refuses_to_overwrite_existing_runstore(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    first = _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve")
    assert first.returncode == 0, first.stderr
    second = _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve")
    assert second.returncode != 0
    assert "output already exists" in second.stderr


def test_auto_approve_requires_external_signing_key(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    _write_case(case)
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    env.pop("AGENTFIT_G3_SIGNING_KEY", None)
    env.pop("AGENTFIT_G3_KEY_ID", None)
    result = subprocess.run(
        [
            sys.executable, "-m", "agentfit", "train",
            "--case", str(case), "--output", str(tmp_path / "run"), "--auto-approve",
        ],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "AGENTFIT_G3_SIGNING_KEY" in result.stderr


def test_validate_recomputes_sample_set_content_hash(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    trained = _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve")
    assert trained.returncode == 0, trained.stderr
    path = run_dir / "sample_sets.json"
    manifests = json.loads(path.read_text(encoding="utf-8"))
    manifests["manifests"][0]["content_hash"] = "f" * 64
    path.write_text(json.dumps(manifests), encoding="utf-8")
    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "sample-set content hash" in validated.stderr


def test_validate_checks_exported_evidence_manifest(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve").returncode == 0
    assert _run("export", str(run_dir)).returncode == 0
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["delivery_approved"] = False
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "evidence manifest" in validated.stderr


def test_final_evaluation_continues_run_index_per_candidate_and_sample(
    tmp_path: Path,
) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    _append_task_to_case(
        case, "adaptation", "sample-adaptation-extra",
        {"condition_extra": True}, "safe_fix_extra",
    )
    doc = json.loads(case.read_text(encoding="utf-8"))
    doc["training"]["batch_size"] = 2
    case.write_text(json.dumps(doc), encoding="utf-8")
    trained = _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve")
    assert trained.returncode == 0, trained.stderr
    final_episodes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (run_dir / "episodes").glob("*.json")
    ]
    training_episodes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (run_dir / "training_episodes").rglob("*.json")
    ]
    assert len(final_episodes) == 5
    by_evaluation_unit: dict[tuple[str, str], list[int]] = {}
    for episode in training_episodes + final_episodes:
        identity = episode["identity"]
        key = (
            identity["candidate_ref"],
            identity["sample_ref"]["content_hash"],
        )
        by_evaluation_unit.setdefault(key, []).append(identity["run_index"])
    assert all(
        sorted(indices) == list(range(len(indices)))
        for indices in by_evaluation_unit.values()
    )
    assert any(
        episode["identity"]["run_index"] > 0
        for episode in final_episodes
    )


def test_validate_rejects_final_evaluation_index_reused_from_training(
    tmp_path: Path,
) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run(
        "train", "--case", str(case), "--output", str(run_dir), "--auto-approve",
    ).returncode == 0
    episode_path = next(
        path
        for path in (run_dir / "episodes").glob("*.json")
        if json.loads(path.read_text(encoding="utf-8"))["identity"]["run_index"] > 0
    )
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    identity = episode["identity"]
    reused = EvaluationIdentity(
        identity["candidate_ref"],
        SampleRef(**identity["sample_ref"]),
        0,
    )
    old_trace = run_dir / episode["trace_ref"]
    new_trace = run_dir / "traces" / f"{reused.key}.json"
    old_trace.rename(new_trace)
    identity["run_index"] = 0
    episode["trace_ref"] = new_trace.relative_to(run_dir).as_posix()
    episode_path.unlink()
    (run_dir / "episodes" / f"{reused.key}.json").write_text(
        json.dumps(episode), encoding="utf-8",
    )

    validated = _run("validate", str(run_dir))

    assert validated.returncode != 0
    assert "global evaluation run indices" in validated.stderr


def test_export_requires_g3_delivery_approval(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    trained = _run("train", "--case", str(case), "--output", str(run_dir))
    assert trained.returncode == 0, trained.stderr
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["delivery_approved"] is False
    exported = _run("export", str(run_dir))
    assert exported.returncode != 0
    assert "G3" in exported.stderr


def test_g3_approval_cannot_be_forged_by_flipping_summary_bit(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run("train", "--case", str(case), "--output", str(run_dir)).returncode == 0
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["delivery_approved"] is False
    summary["delivery_approved"] = True
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "delivery decision" in validated.stderr
    exported = _run("export", str(run_dir))
    assert exported.returncode != 0


def test_g3_approval_rejects_coordinated_unsigned_edits(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run("train", "--case", str(case), "--output", str(run_dir)).returncode == 0

    decision_path = run_dir / "delivery_decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["approved"] = True
    unsigned = {
        key: value for key, value in decision.items()
        if key not in {"decision_hash", "signature"}
    }
    decision["decision_hash"] = canonical_hash(unsigned)
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["delivery_approved"] = True
    summary["delivery_decision_hash"] = decision["decision_hash"]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "signature" in validated.stderr
    exported = _run("export", str(run_dir))
    assert exported.returncode != 0


def test_validate_rejects_unevaluated_latest_candidate(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve").returncode == 0

    versions = sorted((run_dir / "solution_versions").glob("v*.json"))
    latest = json.loads(versions[-1].read_text(encoding="utf-8"))
    next_version = latest["version"] + 1
    latest["version"] = next_version
    latest["solution"]["version"] = next_version
    latest["solution"]["L4_topology"]["trigger_mode"] = "unevaluated"
    (run_dir / "solution_versions" / f"v{next_version:03d}.json").write_text(
        json.dumps(latest), encoding="utf-8",
    )
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["final_solution_version"] = next_version
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "candidate" in validated.stderr


def test_validate_rejects_duplicate_training_evaluation_identity(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    assert _run(
        "train", "--case", str(case), "--output", str(run_dir), "--auto-approve",
    ).returncode == 0

    episode_path = next((run_dir / "training_episodes").rglob("*.json"))
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    original_trace = run_dir / episode["trace_ref"]
    replay_trace = run_dir / "training_traces" / "replayed" / "epoch_999" / original_trace.name
    replay_episode = run_dir / "training_episodes" / "replayed" / "epoch_999" / episode_path.name
    replay_trace.parent.mkdir(parents=True)
    replay_episode.parent.mkdir(parents=True)
    replay_trace.write_bytes(original_trace.read_bytes())
    episode["trace_ref"] = replay_trace.relative_to(run_dir).as_posix()
    replay_episode.write_text(json.dumps(episode), encoding="utf-8")

    validated = _run("validate", str(run_dir))

    assert validated.returncode != 0
    assert "training evaluation identity" in validated.stderr


def test_validate_requires_episode_for_every_frozen_sample(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    _append_task_to_case(
        case, "validation", "sample-validation-extra",
        {"validation_extra": True}, "safe_fix_validation_extra",
    )
    assert _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve").returncode == 0

    removed = None
    remaining_validation = []
    for episode_path in (run_dir / "episodes").glob("*.json"):
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        sample_id = episode["identity"]["sample_ref"]["sample_id"]
        if sample_id == "sample-validation-extra":
            removed = episode
            episode_path.unlink()
            (run_dir / episode["trace_ref"]).unlink()
        elif sample_id == "sample-2":
            remaining_validation.append(episode)
    assert removed is not None and len(remaining_validation) == 1
    episode = remaining_validation[0]
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["evaluation_by_purpose"]["validation"] = {
        "total": 1,
        "passed": int(episode["result"] == "PASS"),
        "failed": int(episode["result"] == "FAIL"),
        "errors": int(episode["result"] == "ERROR"),
        "pass_rate": 1.0 if episode["result"] == "PASS" else 0.0,
        "cost_usd": episode["cost_usd"],
    }
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    validated = _run("validate", str(run_dir))
    assert validated.returncode != 0
    assert "frozen sample" in validated.stderr


def test_validate_recomputes_summary_and_episode_result(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    _write_case(case)

    summary_run = tmp_path / "summary-run"
    assert _run("train", "--case", str(case), "--output", str(summary_run), "--auto-approve").returncode == 0
    summary_path = summary_run / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["final_pass_rate"] = 0.123
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    validated = _run("validate", str(summary_run))
    assert validated.returncode != 0
    assert "summary" in validated.stderr

    episode_run = tmp_path / "episode-run"
    assert _run("train", "--case", str(case), "--output", str(episode_run), "--auto-approve").returncode == 0
    episode_path = next((episode_run / "episodes").glob("*.json"))
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    episode["result"] = "FAIL" if episode["result"] == "PASS" else "PASS"
    episode_path.write_text(json.dumps(episode), encoding="utf-8")
    validated = _run("validate", str(episode_run))
    assert validated.returncode != 0
    assert "Episode result" in validated.stderr
