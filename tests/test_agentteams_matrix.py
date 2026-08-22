from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess

import pytest

from agentfit.adapters.protocols import SandboxRequest


class StepClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        current = self.value
        self.value += 1.0
        return current


def _task() -> dict:
    return {
        "schema": "agentfit.agentteams-task",
        "task_id": "task-123",
        "candidate_ref": "candidate-abc",
        "sample_ref": {"sample_id": "sample-1", "content_hash": "sample-hash"},
        "run_index": 0,
        "runtime_ref": "runtime-abc",
        "solution": {"l1_atoms": [], "l2_tools": []},
        "input_data": {"alarm": "high-latency"},
        "constraints": {"mode": "semantic-dry-run"},
        "requires_human": False,
    }


def _result(task: dict) -> dict:
    return {
        "schema": "agentfit.agentteams-result",
        "task_id": task["task_id"],
        "candidate_ref": task["candidate_ref"],
        "sample_ref": task["sample_ref"],
        "run_index": task["run_index"],
        "runtime_ref": task["runtime_ref"],
        "status": "completed",
        "steps": [],
        "risk_events": [],
    }


def test_matrix_sandbox_sends_label_free_task_and_returns_matching_worker_result() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    task = _task()
    payload = _result(task)

    class RecordingTransport:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str, str]] = []

        def snapshot(self, room_id: str) -> str:
            assert room_id == "!candidate:matrix.example"
            return "s0"

        def send(self, room_id: str, worker_user_id: str, body: str) -> str:
            self.sent.append((room_id, worker_user_id, body))
            return "$dispatch"

        def poll(self, room_id: str, since: str, timeout_seconds: float):
            assert since == "s0"
            assert timeout_seconds > 0
            foreign = module.MatrixEvent("$foreign", "@other:matrix.example", "ignore")
            response = module.MatrixEvent(
                "$result",
                "@candidate:matrix.example",
                "done\nAGENTFIT_RESULT_BEGIN\n```json\n"
                + json.dumps(payload)
                + "\n```\nAGENTFIT_RESULT_END",
            )
            return module.MatrixPoll("s1", (foreign, response))

    transport = RecordingTransport()
    sandbox = module.MatrixSandboxAdapter(
        transport,
        room_id="!candidate:matrix.example",
        worker_user_id="@candidate:matrix.example",
        monotonic=StepClock(),
    )

    result = sandbox.execute(SandboxRequest(
        tool="agentteams.execute_candidate",
        arguments=task,
        timeout_seconds=10,
    ))

    assert result.status == "ok"
    assert result.output == payload
    assert len(transport.sent) == 1
    body = transport.sent[0][2]
    assert body.startswith("@candidate:matrix.example")
    assert "AGENTFIT_TASK_BEGIN" in body
    assert '"task_id":"task-123"' in body
    assert "expected" not in body.lower()
    assert "label" not in body.lower()


def test_matrix_sandbox_rejects_wrong_identity_without_leaking_payload() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    task = _task()
    drifted = {**_result(task), "candidate_ref": "wrong-candidate"}

    class DriftTransport:
        def snapshot(self, room_id: str) -> str:
            return "s0"

        def send(self, room_id: str, worker_user_id: str, body: str) -> str:
            return "$dispatch"

        def poll(self, room_id: str, since: str, timeout_seconds: float):
            response = module.MatrixEvent(
                "$drifted",
                "@candidate:matrix.example",
                "AGENTFIT_RESULT_BEGIN\n"
                + json.dumps(drifted)
                + "\nAGENTFIT_RESULT_END",
            )
            return module.MatrixPoll("s1", (response,))

    sandbox = module.MatrixSandboxAdapter(
        DriftTransport(),
        room_id="!candidate:matrix.example",
        worker_user_id="@candidate:matrix.example",
        monotonic=StepClock(),
    )

    result = sandbox.execute(SandboxRequest(
        tool="agentteams.execute_candidate",
        arguments=task,
        timeout_seconds=3,
    ))

    # 串行批内错序语义：别的任务的迟到回复被跳过（不是错误），
    # 本任务等不到自己的回复最终以 timeout 结束；错误信息不泄漏错配身份。
    assert result.status == "error"
    assert result.error == "agentteams_matrix_timeout"
    assert "candidate-abc" not in result.error
    assert "wrong-candidate" not in result.error


def test_matrix_sandbox_rejects_worker_message_without_result_envelope() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    task = _task()

    class ProseTransport:
        def __init__(self) -> None:
            self.sent = 0

        def snapshot(self, room_id: str) -> str:
            return "s0"

        def send(self, room_id: str, worker_user_id: str, body: str) -> str:
            self.sent += 1
            return f"$dispatch-{self.sent}"

        def poll(self, room_id: str, since: str, timeout_seconds: float):
            response = module.MatrixEvent(
                "$prose",
                "@candidate:matrix.example",
                "I could not produce the requested JSON result.",
            )
            return module.MatrixPoll("s1", (response,))

    transport = ProseTransport()
    sandbox = module.MatrixSandboxAdapter(
        transport,
        room_id="!candidate:matrix.example",
        worker_user_id="@candidate:matrix.example",
        monotonic=StepClock(),
    )

    result = sandbox.execute(SandboxRequest(
        tool="agentteams.execute_candidate",
        arguments=task,
        timeout_seconds=3,
    ))

    # 3 次重试后仍无合法信封 → 超时结束（StepClock 只走到 deadline）；
    # 重试次数 ≤ 3 且每次都发了重试消息
    assert result.status == "error"
    assert result.error in ("agentteams_result_envelope_error", "agentteams_matrix_timeout")
    assert transport.sent <= 5  # 首发任务 + 最多 3 次信封重试 + 3 次结构校验重试有竞态余量
    assert "requested JSON" not in result.error
    assert transport.sent >= 2  # 首发任务 + 至少 1 次重试（3-retry 语义下可能更多）


def test_matrix_sandbox_retries_one_envelope_failure_with_same_task() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    task = _task()
    payload = _result(task)

    class CorrectingTransport:
        def __init__(self) -> None:
            self.sent: list[str] = []
            self.polls = 0

        def snapshot(self, room_id: str) -> str:
            return "s0"

        def send(self, room_id: str, worker_user_id: str, body: str) -> str:
            self.sent.append(body)
            return f"$dispatch-{len(self.sent)}"

        def poll(self, room_id: str, since: str, timeout_seconds: float):
            self.polls += 1
            body = (
                "I need to explain the result first."
                if self.polls == 1
                else "AGENTFIT_RESULT_BEGIN\n"
                + json.dumps(payload)
                + "\nAGENTFIT_RESULT_END"
            )
            return module.MatrixPoll(
                f"s{self.polls}",
                (module.MatrixEvent(
                    f"$worker-{self.polls}",
                    "@candidate:matrix.example",
                    body,
                ),),
            )

    transport = CorrectingTransport()
    sandbox = module.MatrixSandboxAdapter(
        transport,
        room_id="!candidate:matrix.example",
        worker_user_id="@candidate:matrix.example",
        monotonic=StepClock(),
    )

    result = sandbox.execute(SandboxRequest(
        tool="agentteams.execute_candidate",
        arguments=task,
        timeout_seconds=10,
    ))

    assert result.status == "ok"
    assert result.output == payload
    assert len(transport.sent) == 2
    assert '"task_id":"task-123"' in transport.sent[1]
    assert "previous response violated" in transport.sent[1]


def test_matrix_http_transport_emits_visible_structured_mention() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    calls: list[tuple[str, str, dict | None]] = []

    def request(method: str, path: str, payload: dict | None = None, *, timeout: float):
        calls.append((method, path, payload))
        if method == "PUT":
            return {"event_id": "$sent"}
        raise AssertionError(f"unexpected request {method} {path}")

    credentials = module.MatrixCredentials(
        homeserver="http://127.0.0.1:18080",
        user_id="@manager:matrix.example",
        access_token="top-secret-token",
    )
    transport = module.MatrixHttpTransport(credentials, request=request)

    event_id = transport.send(
        "!candidate:matrix.example",
        "@candidate:matrix.example",
        "@candidate:matrix.example task body",
    )

    assert event_id == "$sent"
    payload = calls[0][2]
    assert payload is not None
    assert payload["m.mentions"] == {"user_ids": ["@candidate:matrix.example"]}
    assert payload["format"] == "org.matrix.custom.html"
    assert "https://matrix.to/#/" in payload["formatted_body"]
    assert "top-secret-token" not in repr(credentials)
    assert "top-secret-token" not in repr(transport)


def test_matrix_http_transport_snapshots_and_filters_room_events() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    responses = iter([
        {"next_batch": "s0"},
        {
            "next_batch": "s1",
            "rooms": {"join": {"!candidate:matrix.example": {"timeline": {"events": [
                {"type": "m.room.member", "event_id": "$member", "sender": "@x"},
                {
                    "type": "m.room.message",
                    "event_id": "$message",
                    "sender": "@candidate:matrix.example",
                    "content": {"msgtype": "m.text", "body": "result"},
                },
            ]}}}},
        },
    ])

    def request(method: str, path: str, payload: dict | None = None, *, timeout: float):
        assert method == "GET"
        return next(responses)

    transport = module.MatrixHttpTransport(
        module.MatrixCredentials(
            "http://127.0.0.1:18080",
            "@manager:matrix.example",
            "secret",
        ),
        request=request,
    )

    assert transport.snapshot("!candidate:matrix.example") == "s0"
    batch = transport.poll("!candidate:matrix.example", "s0", 3)
    assert batch.next_batch == "s1"
    assert batch.events == (
        module.MatrixEvent("$message", "@candidate:matrix.example", "result"),
    )


def test_manager_credentials_loader_keeps_secret_out_of_command_and_repr() -> None:
    module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    recorded: list[list[str]] = []

    def runner(args: list[str], **kwargs):
        recorded.append(args)
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps({
                "homeserver": "http://agentteams-controller:6167",
                "user_id": "@manager:matrix.example",
                "access_token": "runtime-only-secret",
            }),
            stderr="",
        )

    credentials = module.load_manager_matrix_credentials(
        manager_container="agentteams-manager",
        homeserver_override="http://127.0.0.1:18080",
        runner=runner,
    )

    assert credentials.homeserver == "http://127.0.0.1:18080"
    assert credentials.user_id == "@manager:matrix.example"
    assert credentials.access_token == "runtime-only-secret"
    assert "runtime-only-secret" not in " ".join(recorded[0])
    assert "runtime-only-secret" not in repr(credentials)


def test_candidate_worker_manifest_and_lifecycle_are_run_scoped() -> None:
    module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    manifest = module.render_candidate_worker(
        candidate_ref="a" * 64,
        run_id="retail-run-20260818",
        model_ref="deepseek/deepseek-chat",
    )
    worker_name = manifest["metadata"]["name"]

    assert manifest["apiVersion"] == "hiclaw.io/v1beta1"
    assert manifest["kind"] == "Worker"
    assert worker_name.startswith("agentfit-candidate-")
    assert manifest["metadata"]["annotations"]["agentfit.io/candidate-ref"] == "a" * 64
    assert manifest["metadata"]["annotations"]["agentfit.io/run-ref"] == "retail-run-20260818"
    assert manifest["spec"]["runtime"] == "copaw"
    assert manifest["spec"]["model"] == "deepseek/deepseek-chat"
    assert "AGENTFIT_RESULT_BEGIN" in manifest["spec"]["agents"]
    assert "semantic dry-run" in manifest["spec"]["agents"]
    assert "downstream must be a JSON array" in manifest["spec"]["agents"]
    assert "never a string" in manifest["spec"]["agents"]
    assert '"schema":"agentfit.agentteams-result"' in manifest["spec"]["agents"]
    assert "risk_events must be a JSON array of strings" in manifest["spec"]["agents"]
    assert "Do not call shell, file, network, or MCP tools" in manifest["spec"]["agents"]
    assert "no prose or Markdown fences" in manifest["spec"]["agents"]
    assert "no declared L3 route or chain matches" in manifest["spec"]["agents"]
    assert "Candidate inability is not a runtime error" in manifest["spec"]["agents"]

    class RecordingControl:
        def __init__(self) -> None:
            self.applied: list[dict] = []
            self.deleted: list[str] = []
            self.states = [
                [{"name": worker_name, "phase": "Pending"}],
                [{
                    "name": worker_name,
                    "phase": "Running",
                    "containerState": "running",
                    "roomID": "!candidate:matrix.example",
                    "matrixUserID": "@candidate:matrix.example",
                }],
                [],
            ]

        def apply(self, document: dict) -> None:
            self.applied.append(document)

        def workers(self) -> list[dict]:
            return self.states.pop(0)

        def worker_channel_ready(self, name: str) -> bool:
            return True

        def delete_worker(self, name: str) -> None:
            self.deleted.append(name)

    control = RecordingControl()
    lifecycle = module.CandidateWorkerLifecycle(
        control,
        monotonic=StepClock(),
        sleep=lambda _: None,
        poll_interval=0,
    )

    endpoint = lifecycle.provision(manifest, timeout_seconds=10)
    lifecycle.retire(worker_name, timeout_seconds=10)

    assert endpoint.name == worker_name
    assert endpoint.room_id == "!candidate:matrix.example"
    assert endpoint.matrix_user_id == "@candidate:matrix.example"
    assert control.applied == [manifest]
    assert control.deleted == [worker_name]


def test_candidate_worker_lifecycle_fails_closed_on_failed_phase() -> None:
    module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    manifest = module.render_candidate_worker(
        candidate_ref="b" * 64,
        run_id="failed-run",
        model_ref="deepseek/deepseek-chat",
    )

    class FailedControl:
        def apply(self, document: dict) -> None:
            pass

        def workers(self) -> list[dict]:
            return [{
                "name": document_name,
                "phase": "Failed",
                "message": "provider rejected request",
            }]

        def worker_channel_ready(self, name: str) -> bool:
            return False

        def delete_worker(self, name: str) -> None:
            pass

    document_name = manifest["metadata"]["name"]
    lifecycle = module.CandidateWorkerLifecycle(
        FailedControl(),
        monotonic=StepClock(),
        sleep=lambda _: None,
        poll_interval=0,
    )

    with pytest.raises(RuntimeError, match="candidate Worker entered Failed phase"):
        lifecycle.provision(manifest, timeout_seconds=5)


def test_candidate_worker_waits_for_matrix_sync_readiness_after_container_running() -> None:
    module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    manifest = module.render_candidate_worker(
        candidate_ref="d" * 64,
        run_id="channel-readiness",
        model_ref="deepseek/deepseek-chat",
    )
    name = manifest["metadata"]["name"]

    class Control:
        def __init__(self) -> None:
            self.readiness = [False, True]
            self.worker_reads = 0

        def apply(self, document: dict) -> None:
            pass

        def workers(self) -> list[dict]:
            self.worker_reads += 1
            return [{
                "name": name,
                "phase": "Running",
                "containerState": "running",
                "roomID": "!candidate:matrix.example",
                "matrixUserID": "@candidate:matrix.example",
            }]

        def worker_channel_ready(self, worker_name: str) -> bool:
            assert worker_name == name
            return self.readiness.pop(0)

        def delete_worker(self, worker_name: str) -> None:
            pass

    control = Control()
    endpoint = module.CandidateWorkerLifecycle(
        control,
        monotonic=StepClock(),
        sleep=lambda _: None,
        poll_interval=0,
    ).provision(manifest, timeout_seconds=10)

    assert endpoint.name == name
    assert control.worker_reads == 2
    assert control.readiness == []


def test_docker_control_submits_json_manifest_and_reads_workers() -> None:
    module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    calls: list[list[str]] = []
    submitted: list[dict] = []

    def runner(args: list[str], **kwargs):
        calls.append(args)
        if args[:2] == ["docker", "cp"]:
            submitted.append(json.loads(Path(args[2]).read_text(encoding="utf-8")))
        stdout = ""
        if args[-4:] == ["get", "workers", "-o", "json"]:
            stdout = json.dumps({"workers": [{"name": "candidate", "phase": "Running"}]})
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    control = module.DockerAgentTeamsControl(runner=runner)
    document = {"apiVersion": "hiclaw.io/v1beta1", "kind": "Worker", "metadata": {"name": "candidate"}}
    control.apply(document)
    workers = control.workers()
    channel_ready = control.worker_channel_ready("candidate")
    control.delete_worker("candidate")

    assert submitted == [document]
    assert workers == [{"name": "candidate", "phase": "Running"}]
    assert channel_ready is True
    assert any(call[-3:] == ["delete", "worker", "candidate"] for call in calls)


def test_live_batch_injects_agentteams_executor_and_persists_runstore(
    tmp_path: Path,
) -> None:
    module = importlib.import_module("bridges.agentteams.live_batch")
    from agentfit.adapters.protocols import SandboxResult

    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )

    class SemanticSandbox:
        def execute(self, request: SandboxRequest) -> SandboxResult:
            task = request.arguments
            input_data = task["input_data"]
            if input_data.get("roaming_off"):
                selected_tool = "safe_toggle_roaming"
            elif input_data.get("airplane"):
                selected_tool = "safe_reset_airplane_mode"
            else:
                selected_tool = "safe_run_sim_diagnostics"
            return SandboxResult(status="ok", output={
                "schema": "agentfit.agentteams-result",
                "task_id": task["task_id"],
                "candidate_ref": task["candidate_ref"],
                "sample_ref": task["sample_ref"],
                "run_index": task["run_index"],
                "runtime_ref": task["runtime_ref"],
                "status": "completed",
                "steps": [{
                    "layer": "L2",
                    "element_id": selected_tool,
                    "action": "semantic_select",
                    "ok": True,
                }],
                "risk_events": [],
            })

    run_dir = tmp_path / "live-run"
    outcome = module.run_adaptation_batch(
        bundle,
        run_dir,
        SemanticSandbox(),
        deployment_ref="agentteams://worker/candidate",
        sandbox_ref="agentteams://worker/candidate?run=test",
        model_ref="deepseek/deepseek-chat",
        auto_approve=True,
    )

    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    traces = list((run_dir / "training_traces" / "forward" / "epoch_001").glob("*.json"))
    episodes = list((run_dir / "training_episodes" / "forward" / "epoch_001").glob("*.json"))
    assert outcome.pass_rate == 1.0
    assert run["runtime_provenance"]["platform"] == "agentteams"
    assert run["runtime_provenance"]["binding_mode"] == "semantic_dry_run"
    assert run["execution_scope"] == "adaptation_only"
    assert run["lifecycle_state"] == "IN_PROGRESS"
    assert run["stage"] == {"name": "adaptation", "state": "COMPLETE"}
    assert len(traces) == len(episodes) == 3
    assert (run_dir / "sample_sets.json").is_file()
    assert (run_dir / "capability_inventory.json").is_file()
    assert (run_dir / "objective.json").is_file()
    report = (run_dir / "training_report.md").read_text(encoding="utf-8")
    assert "总成本：**不可用**" in report

    from agentfit.cli import CliError, assert_valid_runstore

    assert assert_valid_runstore(run_dir).root == run_dir
    trace = json.loads(traces[0].read_text(encoding="utf-8"))
    trace["steps"][0]["action"] = "tampered"
    traces[0].write_text(json.dumps(trace), encoding="utf-8")
    with pytest.raises(CliError, match="Trace/Episode mismatch"):
        assert_valid_runstore(run_dir)


def test_full_live_batch_freezes_candidate_and_evaluates_four_sets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("bridges.agentteams.live_batch")
    from agentfit.adapters.protocols import SandboxResult
    from agentfit.cli import assert_valid_runstore

    monkeypatch.setenv(
        "AGENTFIT_G3_SIGNING_KEY",
        "agentfit-test-key-not-for-production-0001",
    )
    monkeypatch.setenv("AGENTFIT_G3_KEY_ID", "pytest")
    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )

    class SemanticSandbox:
        def execute(self, request: SandboxRequest) -> SandboxResult:
            task = request.arguments
            input_data = task["input_data"]
            tools = []
            if input_data.get("contract_dispute"):
                tools.append("safe_escalate_human")
            else:
                if input_data.get("airplane"):
                    tools.append("safe_reset_airplane_mode")
                if input_data.get("roaming_off"):
                    tools.append("safe_toggle_roaming")
                if input_data.get("sim_ok") is False:
                    tools.append("safe_run_sim_diagnostics")
            return SandboxResult(status="ok", output={
                "schema": "agentfit.agentteams-result",
                "task_id": task["task_id"],
                "candidate_ref": task["candidate_ref"],
                "sample_ref": task["sample_ref"],
                "run_index": task["run_index"],
                "runtime_ref": task["runtime_ref"],
                "status": "completed",
                "steps": [
                    {
                        "layer": "L2",
                        "element_id": tool,
                        "action": "semantic_select",
                        "ok": True,
                    }
                    for tool in tools
                ],
                "risk_events": [],
            })

    run_dir = tmp_path / "full-live-run"
    outcome = module.run_full_evaluation_batch(
        bundle,
        run_dir,
        SemanticSandbox(),
        deployment_ref="agentteams://worker/candidate",
        sandbox_ref="agentteams://worker/candidate?run=test",
        model_ref="deepseek/deepseek-chat",
        auto_approve=True,
    )

    assert outcome.acceptance_met is False
    assert outcome.delivery_approved is False
    assert set(outcome.evaluation_by_purpose) == {
        "adaptation", "validation", "sealed_holdout", "stress_and_failure",
    }
    assert all(
        metrics["passed"] == metrics["total"] == 3
        for metrics in outcome.evaluation_by_purpose.values()
    )
    assert all(
        metrics["cost_observed"] is False
        for metrics in outcome.evaluation_by_purpose.values()
    )
    assert len(list((run_dir / "episodes").glob("*.json"))) == 12
    assert (run_dir / "acceptance.json").is_file()
    assert (run_dir / "delivery_decision.json").is_file()
    assert assert_valid_runstore(run_dir).root == run_dir


def test_live_runner_always_retires_run_scoped_worker(tmp_path: Path) -> None:
    module = importlib.import_module("bridges.agentteams.run_live")
    candidate_module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    matrix_module = importlib.import_module("bridges.agentteams.matrix_sandbox")
    batch_module = importlib.import_module("bridges.agentteams.live_batch")
    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.manifest = None
            self.retired: list[str] = []

        def provision(self, manifest, *, timeout_seconds):
            self.manifest = manifest
            return candidate_module.WorkerEndpoint(
                manifest["metadata"]["name"],
                "!candidate:matrix.example",
                "@candidate:matrix.example",
            )

        def retire(self, name, *, timeout_seconds):
            self.retired.append(name)

    class Transport:
        pass

    lifecycle = Lifecycle()

    def batch_runner(bundle, run_dir, sandbox, **kwargs):
        assert isinstance(sandbox, matrix_module.MatrixSandboxAdapter)
        assert kwargs["model_ref"] == "deepseek/deepseek-chat"
        assert "room=%21candidate%3Amatrix.example" in kwargs["sandbox_ref"]
        return batch_module.LiveBatchOutcome(Path(run_dir), "c" * 64, 1, 1.0, 0)

    result = module.run_live_agentteams_batch(
        bundle,
        tmp_path / "run",
        run_id="test-run",
        model_ref="deepseek/deepseek-chat",
        lifecycle=lifecycle,
        transport=Transport(),
        batch_runner=batch_runner,
        auto_approve=True,
    )

    assert result.worker_retired is True
    assert lifecycle.retired == [lifecycle.manifest["metadata"]["name"]]


def test_live_runner_selects_full_evaluation_when_explicitly_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("bridges.agentteams.run_live")
    candidate_module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    batch_module = importlib.import_module("bridges.agentteams.live_batch")
    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.retired: list[str] = []

        def provision(self, manifest, *, timeout_seconds):
            return candidate_module.WorkerEndpoint(
                manifest["metadata"]["name"],
                "!candidate:matrix.example",
                "@candidate:matrix.example",
            )

        def retire(self, name, *, timeout_seconds):
            self.retired.append(name)

    called: list[str] = []

    def full_runner(bundle, run_dir, sandbox, **kwargs):
        called.append("full")
        return batch_module.LiveEvaluationOutcome(
            Path(run_dir),
            "c" * 64,
            1,
            1.0,
            0,
            False,
            False,
            {
                purpose: {
                    "total": 3,
                    "passed": 3,
                    "failed": 0,
                    "errors": 0,
                    "pass_rate": 1.0,
                    "cost_usd": 0.0,
                    "cost_observed": False,
                    "risk_events": 0,
                }
                for purpose in (
                    "adaptation", "validation", "sealed_holdout",
                    "stress_and_failure",
                )
            },
        )

    monkeypatch.setattr(module, "run_full_evaluation_batch", full_runner, raising=False)
    lifecycle = Lifecycle()
    result = module.run_live_agentteams_batch(
        bundle,
        tmp_path / "full-run",
        run_id="full-run",
        model_ref="deepseek/deepseek-chat",
        lifecycle=lifecycle,
        transport=object(),
        final_evaluation=True,
    )

    assert called == ["full"]
    assert result.batch.acceptance_met is False
    assert len(lifecycle.retired) == 1


def test_live_runner_retires_worker_when_batch_fails(tmp_path: Path) -> None:
    module = importlib.import_module("bridges.agentteams.run_live")
    candidate_module = importlib.import_module("bridges.agentteams.candidate_sandbox")
    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.retired: list[str] = []

        def provision(self, manifest, *, timeout_seconds):
            return candidate_module.WorkerEndpoint(
                manifest["metadata"]["name"],
                "!candidate:matrix.example",
                "@candidate:matrix.example",
            )

        def retire(self, name, *, timeout_seconds):
            self.retired.append(name)

    lifecycle = Lifecycle()

    def failed_batch(*args, **kwargs):
        raise RuntimeError("batch failed")

    with pytest.raises(RuntimeError, match="batch failed"):
        module.run_live_agentteams_batch(
            bundle,
            tmp_path / "run",
            run_id="failed-run",
            model_ref="deepseek/deepseek-chat",
            lifecycle=lifecycle,
            transport=object(),
            batch_runner=failed_batch,
        )

    assert len(lifecycle.retired) == 1


def test_live_runner_cleans_up_worker_when_provisioning_fails(tmp_path: Path) -> None:
    module = importlib.import_module("bridges.agentteams.run_live")
    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.cleaned: list[str] = []

        def provision(self, manifest, *, timeout_seconds):
            raise TimeoutError("not ready")

        def retire_if_present(self, name, *, timeout_seconds):
            self.cleaned.append(name)
            return True

    lifecycle = Lifecycle()
    with pytest.raises(TimeoutError, match="not ready"):
        module.run_live_agentteams_batch(
            bundle,
            tmp_path / "run",
            run_id="provision-failed",
            model_ref="deepseek/deepseek-chat",
            lifecycle=lifecycle,
            transport=object(),
        )

    assert len(lifecycle.cleaned) == 1


def test_executor_preserves_safe_matrix_error_code() -> None:
    executor_module = importlib.import_module("bridges.agentteams.executor")
    from agentfit.adapters.protocols import SandboxResult
    from plugins.materials.compiler import compile_material_bundle
    from agentfit.solution.builder import build_candidate

    bundle = json.loads(
        (Path(__file__).parents[1] / "examples" / "telecom-materials.json").read_text(
            encoding="utf-8"
        )
    )
    compiled = compile_material_bundle(bundle)
    solution = build_candidate(
        list(compiled.task_samples), compiled.sample_sets, compiled.capability_inventory
    )
    sample = next(
        item for item in compiled.task_samples if item.id == "adapt-roaming-abroad"
    )

    class TimedOutMatrix:
        def execute(self, request):
            return SandboxResult(status="error", error="agentteams_matrix_timeout")

    trace = executor_module.AgentTeamsSandboxExecutor(
        TimedOutMatrix(),
        deployment_ref="agentteams://worker/candidate",
        sandbox_ref="agentteams://worker/candidate?run=test",
    ).execute(solution, sample)

    assert trace.result == "ERROR"
    assert trace.error_code == "agentteams_matrix_timeout"
