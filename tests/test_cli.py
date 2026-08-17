"""Stable core CLI: train, validate, report and export without platform imports."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from agentfit.models.sample import canonical_hash


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


def _write_case(path: Path) -> None:
    purposes = ("adaptation", "validation", "sealed_holdout", "stress_and_failure")
    samples = []
    sample_sets = []
    for index, purpose in enumerate(purposes, 1):
        sample_id = f"sample-{index}"
        samples.append({
            "id": sample_id,
            "features": {f"condition_{index}": True},
            "expected": {"actions": [{"tool": f"safe_fix_{index}", "params": {}}], "outcome": {}},
            "requires_human": False,
            "complexity": "simple",
        })
        sample_sets.append({
            "purpose": purpose,
            "sample_ids": [sample_id],
            "freeze": {
                "reviewer": "human-owner",
                "approved": True,
                "decided_at": "2026-08-17T15:00:00+08:00",
                "reason": "CLI fixture approved",
            },
        })
    path.write_text(json.dumps({
        "scenario": "cli-fixture",
        "samples": samples,
        "sample_sets": sample_sets,
        "training": {"batch_size": 1, "max_epochs": 1},
    }, ensure_ascii=False), encoding="utf-8")


def test_cli_help_lists_stable_commands() -> None:
    result = _run("--help")
    assert result.returncode == 0, result.stderr
    for command in ("train", "validate", "report", "export"):
        assert command in result.stdout


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
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    decision = json.loads((run_dir / "delivery_decision.json").read_text(encoding="utf-8"))
    assert set(summary["evaluation_by_purpose"]) == {
        "adaptation", "validation", "sealed_holdout", "stress_and_failure",
    }
    assert summary["delivery_approved"] is True
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


def test_each_distinct_sample_starts_at_run_index_zero(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    doc = json.loads(case.read_text(encoding="utf-8"))
    doc["samples"].append({
        "id": "sample-adaptation-extra",
        "features": {"condition_extra": True},
        "expected": {"actions": [{"tool": "safe_fix_extra", "params": {}}], "outcome": {}},
        "requires_human": False,
        "complexity": "simple",
    })
    doc["sample_sets"][0]["sample_ids"].append("sample-adaptation-extra")
    doc["training"]["batch_size"] = 2
    case.write_text(json.dumps(doc), encoding="utf-8")
    trained = _run("train", "--case", str(case), "--output", str(run_dir), "--auto-approve")
    assert trained.returncode == 0, trained.stderr
    episodes = [json.loads(path.read_text(encoding="utf-8"))
                for path in (run_dir / "episodes").glob("*.json")]
    assert len(episodes) == 5
    assert {episode["identity"]["run_index"] for episode in episodes} == {0}


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


def test_validate_requires_episode_for_every_frozen_sample(tmp_path: Path) -> None:
    case = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    _write_case(case)
    doc = json.loads(case.read_text(encoding="utf-8"))
    doc["samples"].append({
        "id": "sample-validation-extra",
        "features": {"validation_extra": True},
        "expected": {"actions": [{"tool": "safe_fix_validation_extra", "params": {}}], "outcome": {}},
        "requires_human": False,
        "complexity": "simple",
    })
    doc["sample_sets"][1]["sample_ids"].append("sample-validation-extra")
    case.write_text(json.dumps(doc), encoding="utf-8")
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
