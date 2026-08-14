#!/usr/bin/env python3
"""Export one AgentTeams v1.1.2 shared Project/Task dossier safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
REQUIRED_FILES = (
    "project/meta.json",
    "project/plan.md",
    "project/result.md",
    "business/sample-semantic-spec.json",
    "business/task-semantic-spec.json",
    "business/capability-semantic-spec.json",
    "business/sample-set-manifests.json",
    "governance/workspace/governance_review.md",
)
REPO_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_ROOT = REPO_ROOT / ".local-demo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container-command", default="docker")
    parser.add_argument("--team-file", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--business-task-id", required=True)
    parser.add_argument("--governance-task-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def require_identifier(label: str, value: Any) -> str:
    if not isinstance(value, str) or not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a safe AgentTeams identifier")
    return value


def run_checked(arguments: list[str]) -> None:
    subprocess.run(arguments, check=True, text=True, capture_output=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def secure_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"export contains unsupported symlink: {path.relative_to(root)}")
        path.chmod(0o700 if path.is_dir() else 0o600)
    root.chmod(0o700)


def require_safe_output(path: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as error:
        raise ValueError(
            "repository-local dossier output must be inside ignored .local-demo"
        ) from error


def export(args: argparse.Namespace) -> dict[str, Any]:
    require_safe_output(args.output_dir)
    if args.output_dir.exists():
        raise ValueError("output directory already exists; use a new run-specific path")
    team = json.loads(args.team_file.read_text(encoding="utf-8"))
    if not isinstance(team, dict):
        raise ValueError("team file must contain a JSON object")
    leader_name = require_identifier("leaderName", team.get("leaderName"))
    project_id = require_identifier("project id", args.project_id)
    business_task_id = require_identifier("business task id", args.business_task_id)
    governance_task_id = require_identifier(
        "governance task id", args.governance_task_id
    )
    container = f"agentteams-worker-{leader_name}"
    run_checked([args.container_command, "inspect", container])

    output_parent = args.output_dir.parent.resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=".agentfit-dossier-export-", dir=output_parent)
    )
    shared_root = f"/root/hiclaw-fs/agents/{leader_name}/.copaw/workspaces/default/shared"
    sources = {
        "project": f"projects/{project_id}",
        "business": f"tasks/{business_task_id}",
        "governance": f"tasks/{governance_task_id}",
    }
    try:
        for label, relative in sources.items():
            destination = stage / label
            destination.mkdir(mode=0o700)
            run_checked(
                [
                    args.container_command,
                    "cp",
                    f"{container}:{shared_root}/{relative}/.",
                    str(destination),
                ]
            )
        missing = [relative for relative in REQUIRED_FILES if not (stage / relative).is_file()]
        if missing:
            raise ValueError(f"shared dossier is incomplete: {', '.join(missing)}")
        for relative in REQUIRED_FILES:
            if relative.endswith(".json"):
                json.loads((stage / relative).read_text(encoding="utf-8"))
        secure_tree(stage)
        artifact_hashes = {
            str(path.relative_to(stage)): sha256(path)
            for path in sorted(stage.rglob("*"))
            if path.is_file()
        }
        manifest = {
            "schema_version": "agentfit.agentteams-dossier-export/v1",
            "captured_at_ms": int(time.time() * 1000),
            "agentteams_version": "v1.1.2",
            "leader_name": leader_name,
            "project_id": project_id,
            "business_task_id": business_task_id,
            "governance_task_id": governance_task_id,
            "shared_paths": sources,
            "artifact_sha256": artifact_hashes,
        }
        write_private_json(stage / "export-manifest.json", manifest)
        os.replace(stage, args.output_dir)
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> int:
    args = parse_args()
    try:
        manifest = export(args)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.strip() or f"exit {error.returncode}"
        else:
            detail = str(error)
        print(f"ERROR: {detail}", file=sys.stderr)
        return 1
    print(f"project_id={manifest['project_id']}")
    print(f"artifact_count={len(manifest['artifact_sha256'])}")
    print(f"private_output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
