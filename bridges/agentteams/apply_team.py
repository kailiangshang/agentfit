#!/usr/bin/env python3
"""桥接：应用 AgentFit 团队清单到本地 AgentTeams 并回读状态。

用法：
  python bridges/agentteams/apply_team.py --manifest bridges/agentteams/team-agentfit-v2.yaml
  python bridges/agentteams/apply_team.py --status-only   # 只回读，输出 JSON

库外脚本（src/agentfit 对 AgentTeams 零感知，守护见 tests/test_decoupling.py）。
兼容 BSD/macOS：不依赖 GNU coreutils，全部走 docker exec + controller 内 CLI。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CONTROLLER_CANDIDATES = ("agentteams-controller", "hiclaw-controller")


def find_controller() -> str:
    names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                           capture_output=True, text=True, check=True).stdout.split()
    for c in CONTROLLER_CANDIDATES:
        if c in names:
            return c
    raise SystemExit("未找到运行中的 AgentTeams controller 容器")


def controller_cli(controller: str) -> str:
    out = subprocess.run(["docker", "exec", controller, "sh", "-c",
                          "command -v agt || command -v hiclaw"],
                          capture_output=True, text=True, check=True).stdout.strip()
    return out or "hiclaw"


def apply_manifest(controller: str, cli: str, manifest: Path) -> str:
    remote = f"/tmp/agentfit-{manifest.name}"
    subprocess.run(["docker", "cp", str(manifest), f"{controller}:{remote}"], check=True)
    out = subprocess.run(["docker", "exec", controller, cli, "apply", "-f", remote],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def get_teams(controller: str, cli: str) -> list[dict]:
    out = subprocess.run(["docker", "exec", controller, cli, "get", "teams", "-o", "json"],
                         capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip().startswith(("[", "{")):
        return json.loads(out.stdout)
    # 无 -o json 支持时解析表格
    rows = []
    for line in (out.stdout or "").splitlines():
        parts = line.split()
        if parts and parts[0] not in ("NAME",):
            rows.append({"name": parts[0], "phase": parts[1] if len(parts) > 1 else "",
                         "ready": parts[-1] if len(parts) > 3 else ""})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=None, help="团队 YAML（缺省只回读状态）")
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("-o", "--output", default=None, help="状态 JSON 输出路径")
    args = parser.parse_args()

    controller = find_controller()
    cli = controller_cli(controller)
    applied = None
    if args.manifest and not args.status_only:
        applied = apply_manifest(controller, cli, Path(args.manifest))
        print(applied)
    teams = get_teams(controller, cli)
    payload = {"controller": controller, "cli": cli, "applied": applied, "teams": teams}
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
