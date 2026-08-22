#!/usr/bin/env python3
"""Matrix transport for the AgentTeams candidate sandbox contract.

The access token is runtime-only: it is excluded from repr, provenance and
errors.  This module uses the Matrix client API directly but emits the same
three-layer visible mention used by the CoPaw channel implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
import math
import subprocess
import time
from typing import Any, Callable, Protocol
import urllib.error
import urllib.parse
import urllib.request
import uuid

from agentfit.adapters.protocols import SandboxRequest, SandboxResult


TASK_SCHEMA = "agentfit.agentteams-task"
RESULT_SCHEMA = "agentfit.agentteams-result"
TASK_BEGIN = "AGENTFIT_TASK_BEGIN"
TASK_END = "AGENTFIT_TASK_END"
RESULT_BEGIN = "AGENTFIT_RESULT_BEGIN"
RESULT_END = "AGENTFIT_RESULT_END"


@dataclass(frozen=True)
class MatrixCredentials:
    homeserver: str
    user_id: str
    access_token: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.homeserver.startswith(("http://", "https://")):
            raise ValueError("Matrix homeserver must be an HTTP URL")
        if not self.user_id.startswith("@") or not self.access_token:
            raise ValueError("Matrix user_id and access_token are required")


_MANAGER_CREDENTIAL_SCRIPT = r"""
import json
from pathlib import Path

path = Path('/root/manager-workspace/.copaw/workspaces/default/agent.json')
document = json.loads(path.read_text(encoding='utf-8'))
matrix = (document.get('channels') or {}).get('matrix') or {}
print(json.dumps({
    'homeserver': matrix.get('homeserver', ''),
    'user_id': matrix.get('user_id', ''),
    'access_token': matrix.get('access_token', ''),
}, separators=(',', ':')))
"""


def load_manager_matrix_credentials(
    *,
    manager_container: str = "agentteams-manager",
    homeserver_override: str = "",
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> MatrixCredentials:
    """Read Manager credentials without placing the token in argv or logs."""
    completed = runner(
        ["docker", "exec", manager_container, "python3", "-c", _MANAGER_CREDENTIAL_SCRIPT],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("could not load Matrix credentials from AgentTeams Manager")
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("AgentTeams Manager returned invalid Matrix credentials") from None
    if not isinstance(document, dict):
        raise RuntimeError("AgentTeams Manager returned invalid Matrix credentials")
    return MatrixCredentials(
        homeserver=homeserver_override or str(document.get("homeserver", "")),
        user_id=str(document.get("user_id", "")),
        access_token=str(document.get("access_token", "")),
    )


@dataclass(frozen=True)
class MatrixEvent:
    event_id: str
    sender: str
    body: str


@dataclass(frozen=True)
class MatrixPoll:
    next_batch: str
    events: tuple[MatrixEvent, ...]


class MatrixTransport(Protocol):
    def snapshot(self, room_id: str) -> str: ...

    def send(self, room_id: str, worker_user_id: str, body: str) -> str: ...

    def poll(self, room_id: str, since: str, timeout_seconds: float) -> MatrixPoll: ...


RequestFunction = Callable[..., dict[str, Any]]


class MatrixHttpTransport:
    """Small synchronous Matrix client with injectable HTTP for tests."""

    def __init__(
        self,
        credentials: MatrixCredentials,
        *,
        request: RequestFunction | None = None,
    ) -> None:
        self._credentials = credentials
        self._request_override = request

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(homeserver={self._credentials.homeserver!r}, "
            f"user_id={self._credentials.user_id!r})"
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float,
    ) -> dict[str, Any]:
        if self._request_override is not None:
            return self._request_override(method, path, payload, timeout=timeout)
        body = None
        headers = {
            "Authorization": f"Bearer {self._credentials.access_token}",
            "Accept": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._credentials.homeserver.rstrip("/") + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=max(timeout, 1.0)) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Matrix HTTP request failed with status {exc.code}") from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("Matrix HTTP request failed") from None
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            raise RuntimeError("Matrix HTTP response was not JSON") from None
        if not isinstance(result, dict):
            raise RuntimeError("Matrix HTTP response was not an object")
        return result

    def snapshot(self, room_id: str) -> str:
        document = self._request("GET", "/_matrix/client/v3/sync?timeout=0", timeout=10)
        cursor = document.get("next_batch")
        if not isinstance(cursor, str) or not cursor:
            raise RuntimeError("Matrix sync response has no cursor")
        return cursor

    def send(self, room_id: str, worker_user_id: str, body: str) -> str:
        room = urllib.parse.quote(room_id, safe="")
        transaction = uuid.uuid4().hex
        encoded_user = urllib.parse.quote(worker_user_id, safe="")
        escaped = html.escape(body).replace("\n", "<br>\n")
        visible = html.escape(worker_user_id)
        anchor = (
            f'<a href="https://matrix.to/#/{encoded_user}">{visible}</a>'
        )
        formatted = escaped.replace(visible, anchor, 1)
        payload = {
            "msgtype": "m.text",
            "body": body,
            "format": "org.matrix.custom.html",
            "formatted_body": formatted,
            "m.mentions": {"user_ids": [worker_user_id]},
        }
        response = self._request(
            "PUT",
            f"/_matrix/client/v3/rooms/{room}/send/m.room.message/{transaction}",
            payload,
            timeout=15,
        )
        event_id = response.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise RuntimeError("Matrix send response has no event id")
        return event_id

    def poll(self, room_id: str, since: str, timeout_seconds: float) -> MatrixPoll:
        milliseconds = max(0, min(int(timeout_seconds * 1000), 30_000))
        query = urllib.parse.urlencode({"since": since, "timeout": milliseconds})
        document = self._request(
            "GET",
            f"/_matrix/client/v3/sync?{query}",
            timeout=max(timeout_seconds + 5, 10),
        )
        cursor = document.get("next_batch")
        if not isinstance(cursor, str) or not cursor:
            raise RuntimeError("Matrix sync response has no cursor")
        joined = ((document.get("rooms") or {}).get("join") or {})
        room_document = joined.get(room_id) or {}
        raw_events = ((room_document.get("timeline") or {}).get("events") or [])
        events: list[MatrixEvent] = []
        for event in raw_events:
            if not isinstance(event, dict) or event.get("type") != "m.room.message":
                continue
            content = event.get("content") or {}
            body = content.get("body")
            sender = event.get("sender")
            event_id = event.get("event_id")
            if all(isinstance(value, str) and value for value in (body, sender, event_id)):
                events.append(MatrixEvent(event_id, sender, body))
        return MatrixPoll(cursor, tuple(events))


def _forbidden_answer_key(value: Any) -> bool:
    forbidden = {"expected", "label", "labels", "ground_truth", "answer"}
    if isinstance(value, dict):
        return any(
            str(key).casefold() in forbidden or _forbidden_answer_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_forbidden_answer_key(item) for item in value)
    return False


def _task_message(worker_user_id: str, task: dict[str, Any]) -> str:
    document = json.dumps(task, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"{worker_user_id} Execute the enclosed AgentFit candidate task in your isolated "
        "semantic dry-run boundary. Return only the required result envelope.\n"
        f"{TASK_BEGIN}\n{document}\n{TASK_END}"
    )


def _retry_message(worker_user_id: str, task: dict[str, Any]) -> str:
    return (
        f"{worker_user_id} Your previous response violated the AgentFit result envelope. "
        "Retry this same task once. Return only AGENTFIT_RESULT_BEGIN, one compact JSON "
        "object, and AGENTFIT_RESULT_END; do not add prose or Markdown.\n"
        + _task_message(worker_user_id, task)
    )


def _extract_result(body: str) -> dict[str, Any] | None:
    begin = body.find(RESULT_BEGIN)
    if begin < 0:
        return _extract_bare_result(body)
    begin += len(RESULT_BEGIN)
    end = body.find(RESULT_END, begin)
    if end < 0:
        return None
    payload = body[begin:end].strip()
    if payload.startswith("```"):
        first_newline = payload.find("\n")
        if first_newline < 0:
            return None
        payload = payload[first_newline + 1 :]
        if payload.endswith("```"):
            payload = payload[:-3].rstrip()
    try:
        result = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None


def _extract_bare_result(body: str) -> dict[str, Any] | None:
    """容错解析：模型偶尔省略信封标记、或把 JSON 包进围栏并附加 prose。

    结构性判据（不信标记信标记）：解析出的对象必须携带结果 schema 与
    身份字段，否则视为闲聊/中间输出。身份匹配由调用方 _identity_matches
    再校验，因此这里只需保证 schema 与字段形状。
    """
    text = body
    start = text.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    for index in range(start, len(text)):
        if text[index] != "{":
            continue
        try:
            candidate, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(candidate, dict):
            continue
        if candidate.get("schema") == "agentfit.agentteams-result" and all(
            candidate.get(key) is not None
            for key in ("task_id", "candidate_ref", "sample_ref", "run_index", "runtime_ref")
        ):
            return candidate
    return None


def _identity_matches(result: dict[str, Any], task: dict[str, Any]) -> bool:
    return all(
        result.get(key) == task.get(key)
        for key in ("task_id", "candidate_ref", "sample_ref", "run_index", "runtime_ref")
    )


class MatrixSandboxAdapter:
    """Turn a Matrix Worker room into the stable SandboxAdapter contract."""

    def __init__(
        self,
        transport: MatrixTransport,
        *,
        room_id: str,
        worker_user_id: str,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not room_id.startswith("!") or not worker_user_id.startswith("@"):
            raise ValueError("Matrix room_id and worker_user_id are invalid")
        self.transport = transport
        self.room_id = room_id
        self.worker_user_id = worker_user_id
        self.monotonic = monotonic

    def execute(self, request: SandboxRequest) -> SandboxResult:
        task = request.arguments
        if (
            request.tool != "agentteams.execute_candidate"
            or not isinstance(task, dict)
            or task.get("schema") != TASK_SCHEMA
            or _forbidden_answer_key(task)
        ):
            return SandboxResult(status="error", error="agentteams_task_contract_error")
        try:
            cursor = self.transport.snapshot(self.room_id)
            self.transport.send(
                self.room_id,
                self.worker_user_id,
                _task_message(self.worker_user_id, task),
            )
        except Exception:
            return SandboxResult(status="error", error="agentteams_matrix_transport_error")

        from agentfit.models.envelope import validate_envelope, retry_message_with_errors
        deadline = self.monotonic() + max(request.timeout_seconds, 0.0)
        retries_used = 0
        max_retries = 3
        last_validation_error = "no parseable result"
        while True:
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                return SandboxResult(status="error", error="agentteams_matrix_timeout")
            try:
                batch = self.transport.poll(self.room_id, cursor, remaining)
            except Exception:
                return SandboxResult(status="error", error="agentteams_matrix_transport_error")
            cursor = batch.next_batch
            for event in batch.events:
                if event.sender != self.worker_user_id:
                    continue
                result = _extract_result(event.body)
                if result is None or result.get("schema") != RESULT_SCHEMA:
                    if retries_used < max_retries:
                        retries_used += 1
                        try:
                            self.transport.send(
                                self.room_id,
                                self.worker_user_id,
                                _retry_message(self.worker_user_id, task),
                            )
                        except Exception:
                            return SandboxResult(
                                status="error",
                                error="agentteams_matrix_transport_error",
                            )
                        continue
                    return SandboxResult(
                        status="error",
                        error="agentteams_result_envelope_error",
                    )
                # Pydantic 结构校验：失败时带具体错误重试（不是笼统"格式错了"）
                envelope, validation_error = validate_envelope(result)
                if envelope is None:
                    last_validation_error = validation_error or "unknown"
                    if retries_used < max_retries:
                        retries_used += 1
                        try:
                            self.transport.send(
                                self.room_id,
                                self.worker_user_id,
                                retry_message_with_errors(
                                    self.worker_user_id, task, last_validation_error),
                            )
                        except Exception:
                            return SandboxResult(
                                status="error",
                                error="agentteams_matrix_transport_error",
                            )
                        continue
                    return SandboxResult(
                        status="error",
                        error="agentteams_result_contract_error",
                    )
                if not _identity_matches(result, task):
                    # 串行批内常见错序：这是之前任务的迟到回复（合法信封、
                    # 别的 task_id）。跳过继续等本任务的回复，不是错误。
                    continue
                raw_cost = result.get("cost_usd", 0.0)
                cost = (
                    float(raw_cost)
                    if not isinstance(raw_cost, bool)
                    and isinstance(raw_cost, (int, float))
                    and math.isfinite(float(raw_cost))
                    and float(raw_cost) >= 0
                    else 0.0
                )
                return SandboxResult(status="ok", output=result, cost_usd=cost)
