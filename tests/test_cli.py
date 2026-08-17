"""Stable core CLI: train, validate, report and export without platform imports."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
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
    assert len(list((run_dir / "episodes").glob("*.json"))) == 1
    assert len(list((run_dir / "traces").glob("*.json"))) == 1
    assert (run_dir / "summary.json").is_file()

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
