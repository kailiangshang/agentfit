#!/usr/bin/env python3
"""Run-scoped standalone Worker lifecycle for AgentFit candidate execution."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Callable, Protocol
import uuid

_EXECUTOR_AGENTS = """# AgentFit Candidate Executor

You execute one immutable AgentFit candidate against one TaskSample at a time.

- Treat the enclosed candidate_ref, sample_ref, run_index, and runtime_ref as immutable.
- The task never contains expected answers. Do not request or infer hidden evaluation data.
- This initial runtime binding is a semantic dry-run: select only L1-L4 elements declared in
  the candidate, record the actual reasoning path, and perform no external side effect.
- Do not call shell, file, network, or MCP tools and do not write a result file. The response
  itself is the complete semantic dry-run evidence.
- Do not invent a capability. If the candidate cannot handle the input, return a completed
  result with the steps you actually attempted; the external evaluator determines PASS/FAIL.
- If no declared L3 route or chain matches, still return status completed with the declared
  L3 checks you attempted, no successful L2 step, and no prose. Candidate inability is not a runtime error.
- Only if the runtime itself fails, return status error and a stable error_code.
- Your final response must contain only AGENTFIT_RESULT_BEGIN, one compact JSON object, and
  AGENTFIT_RESULT_END, with no prose or Markdown fences.
- The result schema is agentfit.agentteams-result and must echo task_id, candidate_ref,
  sample_ref, run_index, and runtime_ref byte-for-byte.
- Use this exact object shape and retain the schema field:
  {"schema":"agentfit.agentteams-result","task_id":"<echo>","candidate_ref":"<echo>","sample_ref":<echo object>,"run_index":<echo integer>,"runtime_ref":"<echo>","status":"completed","steps":[],"risk_events":[]}
- A completed result contains steps (layer, element_id, action, ok, optional error/output/
  downstream), risk_events, and optional routed_knowledge_id. When present, downstream must be a JSON array
  of zero-based step indices such as [4], never a string or element id; omit it when
  there is no downstream step. risk_events must be a JSON array of strings, never objects; use []
  when there is no risk. Omit cost_usd when the runtime cannot measure it; never guess a cost.
"""


def _sandbox_name(candidate_ref: str, run_id: str) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {"candidate_ref": candidate_ref, "run_id": run_id},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()[:12]
    return f"agentfit-candidate-{digest}"


def render_candidate_worker(
    *,
    candidate_ref: str,
    run_id: str,
    model_ref: str,
) -> dict[str, Any]:
    if not candidate_ref or not run_id or not model_ref:
        raise ValueError("candidate_ref, run_id and model_ref are required")
    name = _sandbox_name(candidate_ref, run_id)
    return {
        "apiVersion": "hiclaw.io/v1beta1",
        "kind": "Worker",
        "metadata": {
            "name": name,
            "labels": {
                "agentfit.io/component": "candidate-sandbox",
            },
            "annotations": {
                "agentfit.io/candidate-ref": candidate_ref,
                "agentfit.io/run-ref": run_id,
                "agentfit.io/binding-mode": "semantic-dry-run",
            },
        },
        "spec": {
            "model": model_ref,
            "runtime": "copaw",
            "identity": (
                "Name: AgentFit Candidate Executor\n"
                "Role: execute a frozen candidate in an isolated run boundary"
            ),
            "soul": (
                "Evidence before claims. Preserve evaluation identity. "
                "Never expose or reconstruct hidden answers."
            ),
            "agents": _EXECUTOR_AGENTS,
            "state": "Running",
        },
    }


class AgentTeamsControl(Protocol):
    def apply(self, document: dict[str, Any]) -> None: ...

    def workers(self) -> list[dict[str, Any]]: ...

    def worker_channel_ready(self, name: str) -> bool: ...

    def delete_worker(self, name: str) -> None: ...


class DockerAgentTeamsControl:
    """Operate the v1.1.2 CLI in the Manager container without printing secrets."""

    def __init__(
        self,
        manager_container: str = "agentteams-manager",
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.manager_container = manager_container
        self.runner = runner

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        completed = self.runner(args, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            operation = " ".join(args[:3])
            raise RuntimeError(f"AgentTeams control command failed: {operation}")
        return completed

    def apply(self, document: dict[str, Any]) -> None:
        remote = f"/tmp/agentfit-candidate-{uuid.uuid4().hex}.yaml"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".json", delete=False
            ) as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
                temporary = Path(stream.name)
            self._run(["docker", "cp", str(temporary), f"{self.manager_container}:{remote}"])
            self._run([
                "docker", "exec", self.manager_container,
                "hiclaw", "apply", "-f", remote,
            ])
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self.runner(
                ["docker", "exec", self.manager_container, "rm", "-f", remote],
                capture_output=True,
                text=True,
                check=False,
            )

    def workers(self) -> list[dict[str, Any]]:
        completed = self._run([
            "docker", "exec", self.manager_container,
            "hiclaw", "get", "workers", "-o", "json",
        ])
        try:
            document = json.loads(completed.stdout)
        except json.JSONDecodeError:
            raise RuntimeError("AgentTeams workers response was not JSON") from None
        workers = document.get("workers") if isinstance(document, dict) else None
        if not isinstance(workers, list) or any(not isinstance(item, dict) for item in workers):
            raise RuntimeError("AgentTeams workers response was invalid")
        return workers

    def worker_channel_ready(self, name: str) -> bool:
        if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", name) is None:
            raise ValueError("candidate Worker name is invalid")
        container = f"agentteams-worker-{name}"
        sync_token = f"/root/hiclaw-fs/agents/{name}/.copaw/matrix_sync_token"
        completed = self.runner(
            ["docker", "exec", container, "test", "-s", sync_token],
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.returncode == 0

    def delete_worker(self, name: str) -> None:
        self._run([
            "docker", "exec", self.manager_container,
            "hiclaw", "delete", "worker", name,
        ])


@dataclass(frozen=True)
class WorkerEndpoint:
    name: str
    room_id: str
    matrix_user_id: str


class CandidateWorkerLifecycle:
    def __init__(
        self,
        control: AgentTeamsControl,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        poll_interval: float = 2.0,
    ) -> None:
        self.control = control
        self.monotonic = monotonic
        self.sleep = sleep
        self.poll_interval = poll_interval

    def provision(
        self,
        document: dict[str, Any],
        *,
        timeout_seconds: float = 180,
    ) -> WorkerEndpoint:
        name = ((document.get("metadata") or {}).get("name"))
        if not isinstance(name, str) or not name:
            raise ValueError("candidate Worker manifest has no name")
        self.control.apply(document)
        deadline = self.monotonic() + timeout_seconds
        while self.monotonic() < deadline:
            worker = next(
                (item for item in self.control.workers() if item.get("name") == name),
                None,
            )
            if worker is not None:
                phase = worker.get("phase")
                if phase == "Failed":
                    raise RuntimeError("candidate Worker entered Failed phase")
                if phase == "Running" and worker.get("containerState") == "running":
                    room_id = worker.get("roomID")
                    matrix_user_id = worker.get("matrixUserID")
                    if (
                        isinstance(room_id, str)
                        and isinstance(matrix_user_id, str)
                        and self.control.worker_channel_ready(name)
                    ):
                        return WorkerEndpoint(name, room_id, matrix_user_id)
            self.sleep(self.poll_interval)
        raise TimeoutError("candidate Worker did not become ready")

    def retire(self, name: str, *, timeout_seconds: float = 180) -> None:
        self.control.delete_worker(name)
        deadline = self.monotonic() + timeout_seconds
        while self.monotonic() < deadline:
            if not any(item.get("name") == name for item in self.control.workers()):
                return
            self.sleep(self.poll_interval)
        raise TimeoutError("candidate Worker did not retire")

    def retire_if_present(self, name: str, *, timeout_seconds: float = 180) -> bool:
        if not any(item.get("name") == name for item in self.control.workers()):
            return False
        self.retire(name, timeout_seconds=timeout_seconds)
        return True
