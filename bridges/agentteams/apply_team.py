#!/usr/bin/env python3
"""桥接：应用 AgentFit 团队清单到本地 AgentTeams 并回读状态。

用法：
  python bridges/agentteams/apply_team.py --manifest bridges/agentteams/team.yaml
  python bridges/agentteams/apply_team.py --status-only   # 只回读，输出 JSON

库外脚本（src/agentfit 对 AgentTeams 零感知，守护见 tests/test_decoupling.py）。
兼容 BSD/macOS：不依赖 GNU coreutils，全部走 docker exec + controller 内 CLI。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple

CONTROLLER_CANDIDATES = ("agentteams-controller", "hiclaw-controller")
API_VERSION = "hiclaw.io/v1beta1"
TEAM_NAME = "agentfit"
PLATFORM_CONTRACT = "hiclaw-v1.1.2-inline-team"
CANONICAL_LEADER = "agentfit-steward"
CANONICAL_WORKERS = (
    "agentfit-attributor",
    "agentfit-architect",
)


class DriftReport(NamedTuple):
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    changed: tuple[str, ...]
    unverified: tuple[str, ...]

    @property
    def in_sync(self) -> bool:
        return not (self.missing or self.unexpected or self.changed or self.unverified)


def _items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "teams"):
        if isinstance(payload.get(key), list):
            return [item for item in payload[key] if isinstance(item, dict)]
    return [payload]


def _name(item: dict) -> str:
    return str((item.get("metadata") or {}).get("name") or item.get("name") or "")


def _workers(item: dict) -> tuple[str, ...] | None:
    spec = item.get("spec")
    names = []
    if isinstance(spec, dict):
        leader = spec.get("leader") or {}
        if leader.get("name"):
            names.append(leader["name"])
        names.extend(worker["name"] for worker in spec.get("workers", []) if worker.get("name"))
    elif item.get("leaderName") or isinstance(item.get("workerNames"), list):
        if item.get("leaderName"):
            names.append(item["leaderName"])
        names.extend(str(name) for name in item.get("workerNames", []) if name)
    else:
        return None
    return tuple(sorted(names))


def _owned_spec(item: dict) -> dict | None:
    spec = item.get("spec")
    if not isinstance(spec, dict):
        return None

    def role_payload(role: dict) -> dict:
        keys = ("name", "model", "runtime", "state", "identity", "soul")
        return {key: role.get(key) for key in keys if key in role}

    payload = {key: spec[key] for key in ("teamName", "description", "peerMentions") if key in spec}
    if "leader" in spec:
        payload["leader"] = role_payload(spec.get("leader") or {})
    if "workers" in spec:
        payload["workers"] = sorted(
            (role_payload(worker) for worker in spec.get("workers", [])),
            key=lambda worker: worker.get("name", ""),
        )
    return payload


def _compare_owned(expected: Any, actual: Any) -> str:
    """Return equal, changed, or unverified for fields owned by the manifest."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return "changed"
        changed = False
        unverified = False
        for key, expected_value in expected.items():
            if key not in actual:
                unverified = True
                continue
            status = _compare_owned(expected_value, actual[key])
            changed |= status == "changed"
            unverified |= status == "unverified"
        if any(key not in expected for key in actual):
            changed = True
        return "changed" if changed else "unverified" if unverified else "equal"
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            return "changed"
        statuses = [_compare_owned(left, right) for left, right in zip(expected, actual)]
        return "changed" if "changed" in statuses else "unverified" if "unverified" in statuses else "equal"
    return "equal" if expected == actual else "changed"


def reconcile_status(expected: dict, actual: Any) -> DriftReport:
    """Compare only AgentFit-owned Teams; unrelated deployments are out of scope."""
    expected_name = _name(expected)
    actual_items = _items(actual)
    by_name = {_name(item): item for item in actual_items if _name(item)}
    missing = (expected_name,) if expected_name not in by_name else ()
    unexpected = tuple(sorted(
        name for name in by_name if name.startswith("agentfit") and name != expected_name
    ))
    changed: list[str] = []
    unverified: list[str] = []
    current = by_name.get(expected_name)
    if current is not None:
        current_workers = _workers(current)
        expected_workers = _workers(expected)
        if current_workers is None:
            unverified.append(f"{expected_name}:content")
        elif current_workers != expected_workers:
            changed.append(f"{expected_name}:members")
        else:
            current_spec = _owned_spec(current)
            if current_spec is None:
                unverified.append(f"{expected_name}:content")
            else:
                spec_status = _compare_owned(_owned_spec(expected), current_spec)
                if spec_status == "changed":
                    changed.append(f"{expected_name}:spec")
                elif spec_status == "unverified":
                    unverified.append(f"{expected_name}:content")
        expected_hash = (expected.get("metadata") or {}).get("annotations", {}).get("agentfit.io/registry-hash")
        actual_hash = (current.get("metadata") or {}).get("annotations", {}).get("agentfit.io/registry-hash")
        if expected_hash and actual_hash is None:
            unverified.append(f"{expected_name}:registry-hash")
        elif expected_hash and actual_hash != expected_hash:
            changed.append(f"{expected_name}:registry-hash")
    return DriftReport(missing, unexpected, tuple(changed), tuple(unverified))


def load_resources(path: Path) -> dict:
    """Load the single JSON-compatible YAML Team deployment artifact."""
    text = path.read_text(encoding="utf-8")
    if "\n---\n" in text:
        raise SystemExit("deployment artifact must contain exactly one Team document")
    try:
        resource = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit("deployment artifact must be one JSON-compatible YAML Team document") from exc
    if not isinstance(resource, dict):
        raise SystemExit("deployment artifact must contain one object resource")
    return resource


def validate_resources(team: dict) -> None:
    """Fail closed before copying the v1.1.2 inline Team into AgentTeams."""
    if team.get("apiVersion") != API_VERSION:
        raise SystemExit(f"Team {TEAM_NAME} must set apiVersion={API_VERSION}")
    if team.get("kind") != "Team":
        raise SystemExit("deployment artifact kind must be Team")
    if _name(team) != TEAM_NAME:
        raise SystemExit(f"deployment artifact must use canonical Team name {TEAM_NAME}")

    annotations = (team.get("metadata") or {}).get("annotations")
    if not isinstance(annotations, dict):
        raise SystemExit("Team agentfit is missing required annotations")
    if not isinstance(annotations.get("agentfit.io/registry-hash"), str) or not annotations["agentfit.io/registry-hash"]:
        raise SystemExit("Team agentfit is missing agentfit.io/registry-hash")
    if annotations.get("agentfit.io/source") != "bridges/agentteams/render_team.py":
        raise SystemExit("Team agentfit must use the canonical agentfit.io/source")
    model_ref = annotations.get("agentfit.io/model-ref")
    if not isinstance(model_ref, str) or not model_ref or model_ref == "deepseek-chat":
        raise SystemExit("Team agentfit must use a non-ambiguous agentfit.io/model-ref")
    if annotations.get("agentfit.io/platform-contract") != PLATFORM_CONTRACT:
        raise SystemExit(f"Team agentfit must set agentfit.io/platform-contract={PLATFORM_CONTRACT}")

    spec = team.get("spec")
    if not isinstance(spec, dict):
        raise SystemExit("Team agentfit is missing spec")
    if "workerMembers" in spec:
        raise SystemExit("Team agentfit must not use v1.2 workerMembers")
    if spec.get("teamName") != TEAM_NAME or not isinstance(spec.get("description"), str) or not spec["description"]:
        raise SystemExit("Team agentfit must set canonical teamName and description")
    if spec.get("peerMentions") is not False:
        raise SystemExit("Team agentfit must set peerMentions=false")

    leader = spec.get("leader")
    if not isinstance(leader, dict) or leader.get("name") != CANONICAL_LEADER:
        raise SystemExit("Team agentfit must use canonical inline leader")
    if "runtime" in leader:
        raise SystemExit("Team agentfit leader must not set runtime in v1.1.2")
    workers = spec.get("workers")
    if not isinstance(workers, list) or tuple(worker.get("name") for worker in workers if isinstance(worker, dict)) != CANONICAL_WORKERS:
        raise SystemExit("Team agentfit must use canonical inline worker roles")

    for role in (leader, *workers):
        if not isinstance(role, dict):
            raise SystemExit("Team agentfit inline roles must be objects")
        name = role.get("name")
        if role.get("workerName") != name or role.get("model") != model_ref:
            raise SystemExit("Team agentfit role model must bind to agentfit.io/model-ref")
        if role.get("state") != "Running":
            raise SystemExit("Team agentfit roles must set state=Running")
        if not isinstance(role.get("identity"), str) or not role["identity"]:
            raise SystemExit("Team agentfit roles must include identity")
        if not isinstance(role.get("soul"), str) or "## 步骤" not in role["soul"]:
            raise SystemExit("Team agentfit roles must include canonical Soul/Skill content")
    for worker in workers:
        if worker.get("runtime") != "copaw":
            raise SystemExit("Team agentfit inline workers must set runtime=copaw")


def load_manifest(path: Path) -> dict:
    """Compatibility helper returning the validated Team document."""
    team = load_resources(path)
    validate_resources(team)
    return team


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
    validate_resources(load_resources(manifest))
    remote = f"/tmp/agentfit-{manifest.name}"
    subprocess.run(["docker", "cp", str(manifest), f"{controller}:{remote}"], check=True)
    out = subprocess.run(["docker", "exec", controller, cli, "apply", "-f", remote],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def get_teams(controller: str, cli: str) -> list[dict]:
    out = subprocess.run(["docker", "exec", controller, cli, "get", "teams", "-o", "json"],
                         capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip().startswith(("[", "{")):
        return _items(json.loads(out.stdout))
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
    parser.add_argument("--dry-run", action="store_true", help="验证并回读 drift，不复制或应用资源")
    parser.add_argument("-o", "--output", default=None, help="状态 JSON 输出路径")
    args = parser.parse_args()

    if args.status_only and args.dry_run:
        parser.error("--status-only and --dry-run cannot be used together")
    expected_path = Path(args.manifest) if args.manifest else Path(__file__).with_name("team.yaml")
    expected = load_resources(expected_path)
    validate_resources(expected)
    controller = find_controller()
    cli = controller_cli(controller)
    applied = None
    if args.manifest and not args.status_only and not args.dry_run:
        applied = apply_manifest(controller, cli, expected_path)
        print(applied)
    teams = get_teams(controller, cli)
    drift = reconcile_status(expected, teams)
    payload = {
        "controller": controller, "cli": cli, "applied": applied,
        "dry_run": args.dry_run,
        "plan": [{"kind": expected["kind"], "name": _name(expected)}],
        "teams": teams,
        "drift": {**drift._asdict(), "in_sync": drift.in_sync},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
