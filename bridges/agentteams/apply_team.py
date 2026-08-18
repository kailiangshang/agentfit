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
CANONICAL_WORKERS = (
    "agentfit-steward",
    "agentfit-attributor",
    "agentfit-architect",
)
CANONICAL_MEMBER_REFS = (
    ("agentfit-steward", "team_leader"),
    ("agentfit-attributor", "worker"),
    ("agentfit-architect", "worker"),
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
        members = spec.get("workerMembers")
        if isinstance(members, list):
            names.extend(member["name"] for member in members if isinstance(member, dict) and member.get("name"))
        else:
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

    payload = {key: spec[key] for key in ("teamName", "description", "peerMentions", "workerMembers") if key in spec}
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


def load_resources(path: Path) -> list[dict]:
    """Load an ordered multi-document YAML deployment artifact."""
    text = path.read_text(encoding="utf-8")
    try:
        resource = json.loads(text)
        resources = [resource]
    except json.JSONDecodeError:
        documents = [document.strip() for document in text.split("\n---\n") if document.strip()]
        try:
            resources = [json.loads(document) for document in documents]
        except json.JSONDecodeError:
            try:
                import yaml
            except ImportError as exc:
                raise SystemExit("deployment artifact is non-JSON YAML; install PyYAML") from exc
            resources = list(yaml.safe_load_all(text))
    if not all(isinstance(resource, dict) for resource in resources):
        raise SystemExit("deployment artifact must contain object resources only")
    return resources


def validate_resources(resources: list[dict]) -> None:
    """Fail closed before copying an AgentFit deployment into AgentTeams."""
    if len(resources) != 4:
        raise SystemExit("deployment artifact must contain exactly three Workers and one Team")
    kinds = tuple(str(resource.get("kind", "")) for resource in resources)
    if kinds != ("Worker", "Worker", "Worker", "Team"):
        raise SystemExit("deployment resources must be ordered Worker, Worker, Worker, Team")
    names = tuple(_name(resource) for resource in resources)
    if any(not name for name in names):
        raise SystemExit("deployment resource is missing metadata.name")
    if len(set(names)) != len(names):
        raise SystemExit("deployment artifact contains duplicate resource names")
    if names[:3] != CANONICAL_WORKERS or names[3] != "agentfit":
        raise SystemExit("deployment artifact must use the canonical AgentFit resource names")

    for worker in resources[:3]:
        spec = worker.get("spec")
        if not isinstance(spec, dict):
            raise SystemExit(f"Worker {_name(worker)} is missing spec")
        if spec.get("workerName") != _name(worker):
            raise SystemExit(f"Worker {_name(worker)} must use its canonical workerName")
        for key, expected in (("runtime", "copaw"), ("state", "Running")):
            if spec.get(key) != expected:
                raise SystemExit(f"Worker {_name(worker)} must set {key}={expected}")
        if not isinstance(spec.get("model"), str) or not spec["model"].strip():
            raise SystemExit(f"Worker {_name(worker)} is missing an explicit model")
        if not isinstance(spec.get("identity"), str) or not isinstance(spec.get("soul"), str):
            raise SystemExit(f"Worker {_name(worker)} is missing identity or soul")

    team = resources[-1]
    spec = team.get("spec")
    if not isinstance(spec, dict):
        raise SystemExit("Team agentfit is missing spec")
    if "leader" in spec or "workers" in spec:
        raise SystemExit("Team agentfit must not use inline leader or workers")
    members = spec.get("workerMembers")
    if not isinstance(members, list):
        raise SystemExit("Team agentfit must declare workerMembers")
    refs = tuple(
        (str(member.get("name", "")), str(member.get("role", "")))
        for member in members if isinstance(member, dict)
    )
    if refs != CANONICAL_MEMBER_REFS:
        referenced = {name for name, _ in refs}
        missing = set(CANONICAL_WORKERS) - referenced
        if missing:
            raise SystemExit(f"Team agentfit references missing Worker resources: {', '.join(sorted(missing))}")
        raise SystemExit("Team agentfit workerMembers must use canonical role ordering")


def team_resource(resources: list[dict]) -> dict:
    validate_resources(resources)
    return resources[-1]


def load_manifest(path: Path) -> dict:
    """Compatibility helper returning the Team document from the deployment artifact."""
    return team_resource(load_resources(path))


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
    resources = load_resources(expected_path)
    expected = team_resource(resources)
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
        "dry_run": args.dry_run, "plan": [
            {"kind": resource["kind"], "name": _name(resource)} for resource in resources
        ],
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
