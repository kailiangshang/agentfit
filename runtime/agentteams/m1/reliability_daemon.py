#!/usr/bin/env python3
"""Runtime reliability daemon: keeps the AgentFit platform healthy.

Runs as a background loop:
1. JWT refresh: detects worker credential expiry before agents hit 401,
   rebuilds workers, republishes skills, redistributes batches
2. Skill presence: verifies S1/S5 in all workers, republishes if missing
3. Health check: controller/manager/team status, alerts on degradation

This is operator infrastructure, not AgentFit iteration. It should be
invisible to the iteration loop.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
TEAM_FILE = REPO_ROOT / ".local-demo/agentteams/m1/evidence/team.json"
SKILL_PACKAGES = ("s1-task-compile", "s5-independent-audit")

CHECK_INTERVAL = 120  # seconds
JWT_REFRESH_MARGIN = 300  # refresh 5 min before expiry


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def log(msg: str) -> None:
    print(f"[reliability] {time.strftime('%H:%M:%S')} {msg}", flush=True)


def get_controller() -> str | None:
    result = run(["docker", "ps", "--format", "{{.Names}}"])
    for name in result.stdout.splitlines():
        if name in ("agentteams-controller", "hiclaw-controller"):
            return name
    return None


def check_worker_auth(controller: str, worker: str) -> bool:
    """Check if worker's hiclaw CLI can authenticate (JWT not expired)."""
    result = run([
        "docker", "exec", f"agentteams-worker-{worker}",
        "hiclaw", "get", "workers", worker, "-o", "json",
    ])
    return result.returncode == 0


def check_skill_present(worker: str, package: str) -> bool:
    result = run([
        "docker", "exec", f"agentteams-worker-{worker}",
        "test", "-f",
        f"/root/.copaw-worker/{worker}/skills/{package}/SKILL.md",
    ])
    return result.returncode == 0


def refresh_workers(team: dict) -> bool:
    """Rebuild all workers to get fresh JWTs."""
    manifest_env = REPO_ROOT / ".local-demo/agentteams/m1/manifest.env"
    if not manifest_env.is_file():
        log("manifest.env not found, cannot refresh")
        return False
    env_text = manifest_env.read_text()
    manifest_path = None
    for line in env_text.splitlines():
        if line.startswith("export AGENTFIT_TEAM_MANIFEST="):
            manifest_path = line.split("'")[1] if "'" in line else line.split("=", 1)[1]
            break
    if not manifest_path:
        log("manifest path not found")
        return False

    workers = [team.get("leaderName")] + team.get("workerNames", [])
    for worker in workers:
        if worker:
            run(["docker", "rm", "-f", f"agentteams-worker-{worker}"])

    log_path = REPO_ROOT / ".local-demo/agentteams/m1/apply-auto-refresh.log"
    result = run([
        str(REPO_ROOT / "runtime/agentteams/apply-manifest.sh"),
        "--file", manifest_path,
        "--log-file", str(log_path),
        "--reuse-existing-human",
    ])
    if result.returncode != 0:
        log(f"worker rebuild failed: {result.stderr[:200]}")
        return False
    log(f"workers rebuilt ({len(workers)}), waiting for boot...")
    time.sleep(60)
    return True


def republish_skills(controller: str) -> bool:
    """Stage skill packages into controller then mc cp to MinIO for all agents."""
    import json as _json

    if not TEAM_FILE.is_file():
        return False
    team = _json.loads(TEAM_FILE.read_text())
    agents = [team.get("leaderName")] + team.get("workerNames", [])

    run(["docker", "exec", controller, "mkdir", "-p", "/tmp/agentfit-skills"])
    for package in SKILL_PACKAGES:
        stage = run([
            "docker", "cp",
            str(SKILLS_ROOT / package),
            f"{controller}:/tmp/agentfit-skills/{package}",
        ])
        if stage.returncode != 0:
            log(f"staging failed for {package}")
            continue
        for agent in agents:
            if not agent:
                continue
            mc = run([
                "docker", "exec", controller, "mc", "cp", "-r",
                f"/tmp/agentfit-skills/{package}",
                f"agentteams/agentteams-storage/agents/{agent}/skills/{package}",
            ])
            if mc.returncode != 0:
                log(f"minio publish failed: {agent}/{package}")

    # Also local cp for immediate availability
    for agent in agents:
        if not agent:
            continue
        container = f"agentteams-worker-{agent}"
        target = f"/root/.copaw-worker/{agent}/skills"
        run(["docker", "exec", container, "mkdir", "-p", target])
        for package in SKILL_PACKAGES:
            run(["docker", "cp", str(SKILLS_ROOT / package), f"{container}:{target}/{package}"])

    log(f"skills republished to {len(agents)} agents")
    return True


def check_team_status(controller: str) -> dict | None:
    result = run([
        "docker", "exec", controller, "hiclaw", "get", "teams", "-o", "json",
    ])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def health_check() -> dict:
    status = {"controller": False, "team": None, "workers": {}, "skills": {}, "actions": []}
    controller = get_controller()
    if not controller:
        status["actions"].append("controller not found")
        return status
    status["controller"] = True

    team_data = check_team_status(controller)
    if team_data:
        for team in team_data.get("teams", []):
            status["team"] = {
                "name": team.get("teamName"),
                "phase": team.get("phase"),
                "leaderReady": team.get("leaderReady"),
                "workers": f"{team.get('readyWorkers')}/{team.get('totalWorkers')}",
            }

    if not TEAM_FILE.is_file():
        status["actions"].append("team file missing")
        return status
    team = json.loads(TEAM_FILE.read_text())
    agents = [team.get("leaderName")] + team.get("workerNames", [])
    needs_refresh = False
    needs_skills = False

    for agent in agents:
        if not agent:
            continue
        container = f"agentteams-worker-{agent}"
        inspect = run(["docker", "inspect", container])
        if inspect.returncode != 0:
            status["workers"][agent] = "container missing"
            needs_refresh = True
            continue

        auth_ok = check_worker_auth(controller, agent)
        status["workers"][agent] = "auth-ok" if auth_ok else "JWT-EXPIRED"
        if not auth_ok:
            needs_refresh = True

        for package in SKILL_PACKAGES:
            present = check_skill_present(agent, package)
            status["skills"][f"{agent}/{package}"] = "ok" if present else "missing"
            if not present:
                needs_skills = True

    if needs_refresh:
        log("credential refresh needed, rebuilding workers...")
        if refresh_workers(team):
            status["actions"].append("workers rebuilt")
            republish_skills(controller)
            status["actions"].append("skills republished")
        else:
            status["actions"].append("REFRESH FAILED")
    elif needs_skills:
        log("skill republish needed...")
        republish_skills(controller)
        status["actions"].append("skills republished")

    return status


def main() -> int:
    log("reliability daemon started")
    last_rebuild = 0.0
    cooldown = 300.0  # 5 min after rebuild, skip auth checks
    while True:
        in_cooldown = (time.time() - last_rebuild) < cooldown
        try:
            if in_cooldown:
                log("cooldown after rebuild, skipping auth check")
                time.sleep(CHECK_INTERVAL)
                continue
            status = health_check()
            if "workers rebuilt" in status.get("actions", []):
                last_rebuild = time.time()
                log(f"actions taken: {status['actions']} (entering cooldown)")
            elif status["actions"]:
                log(f"actions taken: {status['actions']}")
            else:
                workers_ok = all(v == "auth-ok" for v in status["workers"].values())
                skills_ok = all(v == "ok" for v in status["skills"].values())
                if workers_ok and skills_ok:
                    log("all healthy")
        except Exception as exc:
            log(f"health check error: {exc}")
        time.sleep(CHECK_INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
