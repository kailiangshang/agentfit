#!/usr/bin/env python3
"""Publish AgentFit skill packages into team worker containers.

Copies skills/<package> directories into each worker's
/root/.copaw-worker/<agent>/skills/ directory (the CoPaw skills layout)
and verifies the SKILL.md lands. Idempotent; refuses to publish outside
the team file's worker list.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
SKILL_PACKAGES = ("s1-task-compile", "s5-independent-audit")
WORKER_SKILLS_PATH = "/root/.copaw-worker/{agent}/skills"


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def publish(container_command: str, team_file: Path, only: list[str]) -> dict:
    import json

    team = json.loads(team_file.read_text(encoding="utf-8"))
    leader = team.get("leaderName")
    workers = team.get("workerNames", [])
    if not isinstance(leader, str) or not leader:
        raise SystemExit("team file lacks leaderName")
    agents = [leader, *workers]
    packages = only or list(SKILL_PACKAGES)
    for package in packages:
        if not (SKILLS_ROOT / package / "SKILL.md").is_file():
            raise SystemExit(f"skill package incomplete: {package}")

    report = {"published": {}, "verify": {}}
    for agent in agents:
        container = f"agentteams-worker-{agent}"
        target_dir = WORKER_SKILLS_PATH.format(agent=agent)
        inspect = run([container_command, "inspect", container])
        if inspect.returncode != 0:
            report["published"][agent] = f"container missing: {container}"
            continue
        run([container_command, "exec", container, "mkdir", "-p", target_dir])
        for package in packages:
            cp = run(
                [
                    container_command, "cp",
                    str(SKILLS_ROOT / package),
                    f"{container}:{target_dir}/{package}",
                ]
            )
            if cp.returncode != 0:
                report["published"].setdefault(agent, {})[package] = cp.stderr.strip()
                continue
            check = run(
                [
                    container_command, "exec", container,
                    "test", "-f", f"{target_dir}/{package}/SKILL.md",
                ]
            )
            ok = check.returncode == 0
            report["verify"].setdefault(agent, {})[package] = (
                "ok" if ok else "SKILL.md missing after copy"
            )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-file", type=Path, required=True)
    parser.add_argument("--container-command", default="docker")
    parser.add_argument(
        "--only", action="append", default=[],
        help="publish only these skill packages (repeatable)",
    )
    args = parser.parse_args()
    report = publish(args.container_command, args.team_file, args.only)
    import json

    print(json.dumps(report, indent=2))
    failed = [
        (agent, pkg, note)
        for agent, note in report["published"].items()
        for pkg, failure in (note.items() if isinstance(note, dict) else [])
        if failure
    ] or [
        (agent, pkg, note)
        for agent, note in report["verify"].items()
        for pkg, note2 in note.items()
        if note2 != "ok"
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
