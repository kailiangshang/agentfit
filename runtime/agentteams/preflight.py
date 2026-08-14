#!/usr/bin/env python3
"""Read-only AgentTeams M0 environment preflight.

The report intentionally records configuration presence only. It never serializes
model credentials, endpoint URLs, or model identifiers.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence


OFFICIAL_REGISTRY = "higress-registry.cn-hangzhou.cr.aliyuncs.com"
OFFICIAL_IMAGES = {
    "embedded": f"{OFFICIAL_REGISTRY}/agentteams/agentteams-embedded",
    "manager": f"{OFFICIAL_REGISTRY}/agentteams/agentteams-manager",
    "worker": f"{OFFICIAL_REGISTRY}/agentteams/agentteams-worker",
}
PINNED_VERSION = "v1.1.2"

MIN_CPU_COUNT = 4
MIN_MEMORY_BYTES = 8 * 1024**3
MIN_DISK_FREE_BYTES = 20 * 1024**3


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    def run(self, argv: Sequence[str], timeout: int = 30) -> CommandResult:
        """Run a command without invoking a shell."""


class SubprocessRunner:
    def run(self, argv: Sequence[str], timeout: int = 30) -> CommandResult:
        try:
            completed = subprocess.run(
                list(argv),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return CommandResult(127, "", type(exc).__name__)
        return CommandResult(
            completed.returncode,
            completed.stdout.strip(),
            completed.stderr.strip(),
        )


@dataclass(frozen=True)
class HostResources:
    cpu_count: int
    memory_bytes: int
    disk_free_bytes: int

    @classmethod
    def detect(cls, disk_path: Path) -> "HostResources":
        memory_bytes = 0
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            for line in meminfo.read_text(encoding="utf-8").splitlines():
                if line.startswith("MemTotal:"):
                    memory_bytes = int(line.split()[1]) * 1024
                    break
        return cls(
            cpu_count=os.cpu_count() or 0,
            memory_bytes=memory_bytes,
            disk_free_bytes=shutil.disk_usage(disk_path).free,
        )


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PreflightReport:
    version: str
    checks: tuple[CheckResult, ...]

    @property
    def ready(self) -> bool:
        return all(check.ok for check in self.checks)

    def by_name(self, name: str) -> CheckResult:
        return next(check for check in self.checks if check.name == name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "agentfit.agentteams-preflight/v1",
            "requested_version": self.version,
            "ready": self.ready,
            "checks": [asdict(check) for check in self.checks],
        }


def _command_check(
    runner: Runner,
    name: str,
    argv: Sequence[str],
    success_detail: str,
    failure_detail: str,
    timeout: int = 30,
) -> CheckResult:
    result = runner.run(argv, timeout=timeout)
    return CheckResult(
        name=name,
        ok=result.returncode == 0,
        detail=success_detail if result.returncode == 0 else failure_detail,
    )


def _resource_check(name: str, actual: int, minimum: int, unit: str) -> CheckResult:
    return CheckResult(
        name=name,
        ok=actual >= minimum,
        detail=f"{actual} {unit}; minimum {minimum} {unit}",
    )


def _configured_check(name: str, variable: str, environ: Mapping[str, str]) -> CheckResult:
    configured = bool(environ.get(variable, "").strip())
    return CheckResult(name=name, ok=configured, detail="configured" if configured else "missing")


def run_preflight(
    repo: Path,
    version: str,
    runner: Runner,
    resources: HostResources,
    environ: Mapping[str, str],
) -> PreflightReport:
    repo = repo.resolve()
    checks: list[CheckResult] = []

    checks.append(
        CheckResult(
            "agentteams.checkout",
            (repo / ".git").exists(),
            "git checkout found" if (repo / ".git").exists() else "git checkout missing",
        )
    )
    checks.append(
        _command_check(
            runner,
            "agentteams.tag",
            ["git", "-C", str(repo), "rev-parse", "--verify", f"refs/tags/{version}"],
            f"found {version}",
            f"missing {version}",
        )
    )
    checks.append(
        _command_check(
            runner,
            "docker.cli",
            ["docker", "--version"],
            "available",
            "unavailable",
        )
    )
    checks.append(
        _command_check(
            runner,
            "docker.daemon",
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            "available",
            "unavailable",
        )
    )
    checks.append(
        _command_check(
            runner,
            "docker.compose",
            ["docker", "compose", "version"],
            "available",
            "unavailable",
        )
    )

    checks.append(_resource_check("host.cpu", resources.cpu_count, MIN_CPU_COUNT, "cores"))
    checks.append(
        _resource_check(
            "host.memory",
            resources.memory_bytes // 1024**3,
            MIN_MEMORY_BYTES // 1024**3,
            "GiB",
        )
    )
    checks.append(
        _resource_check(
            "host.disk",
            resources.disk_free_bytes // 1024**3,
            MIN_DISK_FREE_BYTES // 1024**3,
            "GiB free",
        )
    )

    for role, image in OFFICIAL_IMAGES.items():
        checks.append(
            _command_check(
                runner,
                f"image.{role}",
                ["docker", "manifest", "inspect", f"{image}:{version}"],
                f"official {version} manifest available",
                f"official {version} manifest unavailable",
                timeout=60,
            )
        )

    checks.extend(
        (
            _configured_check("config.api_key", "AGENTTEAMS_LLM_API_KEY", environ),
            _configured_check("config.base_url", "AGENTTEAMS_OPENAI_BASE_URL", environ),
            _configured_check("config.default_model", "AGENTTEAMS_DEFAULT_MODEL", environ),
        )
    )
    return PreflightReport(version=version, checks=tuple(checks))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agentteams-repo", type=Path, required=True)
    parser.add_argument("--version", default=PINNED_VERSION)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_preflight(
        repo=args.agentteams_repo,
        version=args.version,
        runner=SubprocessRunner(),
        resources=HostResources.detect(args.agentteams_repo.parent),
        environ=os.environ,
    )
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    print(f"AgentTeams M0 preflight: {'READY' if report.ready else 'IN_PROGRESS'}")
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
