#!/usr/bin/env python3
"""Send and export private AgentFit Matrix experiment traces via the controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from .run_identity import require_run_id, require_run_terminal_prefix
except ImportError:
    from run_identity import require_run_id, require_run_terminal_prefix


SEND_SCRIPT = r"""
set -eu
room="$1"
leader_name="$2"
txn="$3"
login_body="$(jq -nc --arg user "$HICLAW_ADMIN_USER" --arg password "$HICLAW_ADMIN_PASSWORD" '{type:"m.login.password",identifier:{type:"m.id.user",user:$user},password:$password}')"
token="$(curl -fsS -X POST http://127.0.0.1:6167/_matrix/client/v3/login -H 'Content-Type: application/json' --data "$login_body" | jq -er .access_token)"
members="$(curl -fsS -H "Authorization: Bearer $token" "http://127.0.0.1:6167/_matrix/client/v3/rooms/$room/joined_members")"
leader_id="$(printf '%s' "$members" | jq -er --arg prefix "@$leader_name:" '.joined | keys[] | select(startswith($prefix))' | head -1)"
request="$(cat)"
payload="$(jq -nc --arg body "$leader_id $request" --arg leader "$leader_id" '{msgtype:"m.text",body:$body,"m.mentions":{user_ids:[$leader]}}')"
event_id="$(curl -fsS -X PUT -H "Authorization: Bearer $token" -H 'Content-Type: application/json' --data "$payload" "http://127.0.0.1:6167/_matrix/client/v3/rooms/$room/send/m.room.message/$txn" | jq -er .event_id)"
jq -nc --arg event_id "$event_id" --arg leader_id "$leader_id" '{event_id:$event_id,leader_id:$leader_id}'
"""


EXPORT_SCRIPT = r"""
set -eu
room="$1"
from_token="${2:-}"
login_body="$(jq -nc --arg user "$HICLAW_ADMIN_USER" --arg password "$HICLAW_ADMIN_PASSWORD" '{type:"m.login.password",identifier:{type:"m.id.user",user:$user},password:$password}')"
token="$(curl -fsS -X POST http://127.0.0.1:6167/_matrix/client/v3/login -H 'Content-Type: application/json' --data "$login_body" | jq -er .access_token)"
if [ -n "$from_token" ]; then
  curl -fsS --get -H "Authorization: Bearer $token" --data-urlencode 'dir=b' --data-urlencode 'limit=1000' --data-urlencode "from=$from_token" "http://127.0.0.1:6167/_matrix/client/v3/rooms/$room/messages"
else
  curl -fsS --get -H "Authorization: Bearer $token" --data-urlencode 'dir=b' --data-urlencode 'limit=1000' "http://127.0.0.1:6167/_matrix/client/v3/rooms/$room/messages"
fi
"""


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--container-command", default="docker")
    commands = root.add_subparsers(dest="command", required=True)

    send = commands.add_parser("send", help="Send one request to the Team Leader.")
    send.add_argument("--team-file", type=Path, required=True)
    send.add_argument("--request-file", type=Path, required=True)
    send.add_argument("--run-id", required=True)
    send.add_argument("--entry-room", choices=("leader-dm", "team"), default="leader-dm")
    send.add_argument("--metadata-name", default="send.json")
    send.add_argument("--output-dir", type=Path, required=True)

    export = commands.add_parser(
        "export-once", help="Export both Team and Leader-DM events once."
    )
    export.add_argument("--output-dir", type=Path, required=True)

    usage = commands.add_parser(
        "usage-snapshot", help="Capture cumulative CoPaw token ledgers for team members."
    )
    usage.add_argument("--team-file", type=Path, required=True)
    usage.add_argument("--output-file", type=Path, required=True)
    return root


def private_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(value)
    path.chmod(0o600)


def run_checked(
    arguments: list[str], *, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )


def find_controller(container_command: str) -> str:
    result = run_checked([container_command, "ps", "--format", "{{.Names}}"])
    for name in result.stdout.splitlines():
        if name in {"agentteams-controller", "hiclaw-controller"}:
            return name
    raise RuntimeError("running AgentTeams controller was not found")


def controller_json(
    container_command: str,
    controller: str,
    script: str,
    arguments: list[str],
    *,
    input_text: str = "",
) -> dict[str, Any]:
    result = run_checked(
        [
            container_command,
            "exec",
            "-i",
            controller,
            "sh",
            "-ceu",
            script,
            "sh",
            *arguments,
        ],
        input_text=input_text,
    )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("controller command did not return a JSON object")
    return value


def require_team_fields(team: dict[str, Any]) -> tuple[str, str, str]:
    values = (
        team.get("leaderName"),
        team.get("leaderDMRoomID"),
        team.get("teamRoomID"),
    )
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError("team file lacks leaderName, leaderDMRoomID, or teamRoomID")
    return values  # type: ignore[return-value]


def send(args: argparse.Namespace) -> int:
    if Path(args.metadata_name).name != args.metadata_name:
        raise ValueError("metadata name must be a file name, not a path")
    team = json.loads(args.team_file.read_text(encoding="utf-8"))
    leader_name, leader_dm_room_id, team_room_id = require_team_fields(team)
    room_id = leader_dm_room_id if args.entry_room == "leader-dm" else team_room_id
    request = args.request_file.read_text(encoding="utf-8")
    provenance = load_json_file(args.request_file.with_name("provenance.json"))
    if not isinstance(provenance, dict):
        raise ValueError("request provenance must be a JSON object")
    if provenance.get("run_id") != args.run_id:
        raise ValueError("request provenance run_id differs from send run_id")
    terminal_prefix = require_run_terminal_prefix(
        args.run_id, provenance.get("terminal_prefix")
    )
    if terminal_prefix not in request:
        raise ValueError("request does not contain the declared terminal prefix")
    generated = provenance.get("generated")
    expected_request_hash = (
        generated.get("request_markdown_sha256")
        if isinstance(generated, dict)
        else None
    )
    request_hash = hashlib.sha256(request.encode("utf-8")).hexdigest()
    if (
        not isinstance(expected_request_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_request_hash)
        or expected_request_hash != request_hash
    ):
        raise ValueError("request hash differs from pre-run provenance")
    controller = find_controller(args.container_command)
    started_at_ms = int(time.time() * 1000)
    safe_run = re.sub(r"[^A-Za-z0-9._-]", "-", args.run_id)
    transaction = f"agentfit-{safe_run}-{started_at_ms}"
    response = controller_json(
        args.container_command,
        controller,
        SEND_SCRIPT,
        [room_id, leader_name, transaction],
        input_text=request,
    )
    event_id = response.get("event_id")
    leader_id = response.get("leader_id")
    if not isinstance(event_id, str) or not isinstance(leader_id, str):
        raise RuntimeError("Matrix send response lacks event_id or leader_id")

    metadata = {
        "schema_version": "agentfit.matrix-run/v2",
        "run_id": args.run_id,
        "terminal_prefix": terminal_prefix,
        "status": "sent",
        "started_at_ms": started_at_ms,
        "event_id": event_id,
        "entry_room": args.entry_room,
        "entry_room_id": room_id,
        "leader_id": leader_id,
        "leader_dm_room_id": leader_dm_room_id,
        "team_room_id": team_room_id,
        "request_sha256": request_hash,
    }
    metadata_path = args.output_dir / args.metadata_name
    private_write(metadata_path, json.dumps(metadata, indent=2) + "\n")
    print(f"run_id={args.run_id}")
    print(f"entry_room={args.entry_room}")
    print(f"event_id={event_id}")
    print(f"private_output={metadata_path}")
    return 0


def normalized_events(
    room_responses: dict[str, dict[str, Any]], started_at_ms: int
) -> list[dict[str, Any]]:
    by_event: dict[str, dict[str, Any]] = {}
    for room_label, response in room_responses.items():
        chunk = response.get("chunk", [])
        if not isinstance(chunk, list):
            continue
        for event in chunk:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "m.room.message":
                continue
            timestamp = event.get("origin_server_ts")
            content = event.get("content")
            if not isinstance(timestamp, int) or timestamp < started_at_ms:
                continue
            if not isinstance(content, dict) or not isinstance(content.get("body"), str):
                continue
            event_id = event.get("event_id")
            sender = event.get("sender")
            if not isinstance(event_id, str) or not isinstance(sender, str):
                continue
            by_event[event_id] = {
                "event_id": event_id,
                "sender": sender,
                "origin_server_ts": timestamp,
                "room": room_label,
                "body": content["body"],
                "mentioned_user_ids": sorted(
                    {
                        user_id
                        for user_id in (
                            content.get("m.mentions", {}).get("user_ids", [])
                            if isinstance(content.get("m.mentions"), dict)
                            else []
                        )
                        if isinstance(user_id, str)
                    }
                ),
            }
    return sorted(
        by_event.values(), key=lambda event: (event["origin_server_ts"], event["event_id"])
    )


def export_room_pages(
    container_command: str,
    controller: str,
    room_id: str,
    started_at_ms: int,
    *,
    max_pages: int = 100,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    from_token = ""
    first_start: Any = None
    last_end: Any = None
    for page_count in range(1, max_pages + 1):
        response = controller_json(
            container_command,
            controller,
            EXPORT_SCRIPT,
            [room_id, from_token],
        )
        chunk = response.get("chunk", [])
        if not isinstance(chunk, list):
            raise RuntimeError("Matrix room page does not contain a chunk list")
        if first_start is None:
            first_start = response.get("start")
        events.extend(event for event in chunk if isinstance(event, dict))
        timestamps = [
            event.get("origin_server_ts")
            for event in chunk
            if isinstance(event, dict)
            and isinstance(event.get("origin_server_ts"), int)
        ]
        last_end = response.get("end")
        if not chunk or any(timestamp < started_at_ms for timestamp in timestamps):
            break
        if not isinstance(last_end, str) or not last_end or last_end == from_token:
            break
        from_token = last_end
    else:
        raise RuntimeError(
            f"Matrix pagination exceeded {max_pages} pages before the run boundary"
        )
    return {
        "start": first_start,
        "end": last_end,
        "page_count": page_count,
        "chunk": events,
    }


def normalize_first_line(body: str) -> str:
    first = next((line.strip() for line in body.splitlines() if line.strip()), "")
    return first.lstrip("#>*_ -✅🔧")


def terminal_event(
    events: list[dict[str, Any]], leader_id: str, prefix: str
) -> dict[str, Any] | None:
    for event in events:
        if event["sender"] != leader_id:
            continue
        if event.get("room") != "leader_dm":
            continue
        first = normalize_first_line(event["body"])
        if first.startswith(prefix):
            remainder = first[len(prefix) : len(prefix) + 1]
            if not remainder or not remainder.isalnum():
                return event
    return None


def conversation_markdown(events: list[dict[str, Any]]) -> str:
    parts = ["# AgentFit Matrix conversation\n"]
    for event in events:
        parts.append(
            f"## {event['origin_server_ts']} · {event['sender']} · {event['room']}\n\n"
            f"{event['body'].rstrip()}\n"
        )
    return "\n".join(parts)


def export_once(args: argparse.Namespace) -> int:
    send_path = args.output_dir / "send.json"
    sent = json.loads(send_path.read_text(encoding="utf-8"))
    stored_prefix = sent.get("terminal_prefix")
    if not isinstance(stored_prefix, str) or not stored_prefix:
        raise ValueError("send metadata lacks terminal_prefix")
    stored_prefix = require_run_terminal_prefix(sent.get("run_id"), stored_prefix)
    controller = find_controller(args.container_command)
    room_responses = {
        "team": export_room_pages(
            args.container_command,
            controller,
            sent["team_room_id"],
            int(sent["started_at_ms"]),
        ),
        "leader_dm": export_room_pages(
            args.container_command,
            controller,
            sent["leader_dm_room_id"],
            int(sent["started_at_ms"]),
        ),
    }
    events = normalized_events(room_responses, int(sent["started_at_ms"]))
    terminal = terminal_event(events, sent["leader_id"], stored_prefix)
    raw = {
        "schema_version": "agentfit.matrix-export/v2",
        "started_at_ms": sent["started_at_ms"],
        "rooms": room_responses,
    }
    status = {
        "schema_version": "agentfit.matrix-run-status/v1",
        "run_id": sent["run_id"],
        "complete": terminal is not None,
        "terminal_event_id": terminal["event_id"] if terminal else None,
        "message_event_count": len(events),
        "first_event_at_ms": events[0]["origin_server_ts"] if events else None,
        "last_event_at_ms": events[-1]["origin_server_ts"] if events else None,
        "sender_counts": {
            sender: sum(event["sender"] == sender for event in events)
            for sender in sorted({event["sender"] for event in events})
        },
    }
    private_write(
        args.output_dir / "conversation.raw.json",
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
    )
    private_write(
        args.output_dir / "conversation.json",
        json.dumps(events, ensure_ascii=False, indent=2) + "\n",
    )
    private_write(args.output_dir / "conversation.md", conversation_markdown(events))
    private_write(
        args.output_dir / "status.json",
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
    )
    print(f"run_id={sent['run_id']}")
    print(f"message_event_count={len(events)}")
    print(f"complete={str(terminal is not None).lower()}")
    return 0


def usage_totals(ledger: dict[str, Any]) -> dict[str, int]:
    totals = {"call_count": 0, "prompt_tokens": 0, "completion_tokens": 0}
    for models in ledger.values():
        if not isinstance(models, dict):
            continue
        for usage in models.values():
            if not isinstance(usage, dict):
                continue
            for field in totals:
                value = usage.get(field, 0)
                if isinstance(value, int):
                    totals[field] += value
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    return totals


def usage_snapshot(args: argparse.Namespace) -> int:
    team = load_json_file(args.team_file)
    leader_name, _, _ = require_team_fields(team)
    worker_names = team.get("workerNames", [])
    if not isinstance(worker_names, list) or not all(
        isinstance(name, str) and name for name in worker_names
    ):
        raise ValueError("team file lacks workerNames")
    agents = [leader_name, *worker_names]
    find_controller(args.container_command)
    per_agent: dict[str, dict[str, int]] = {}
    for agent in agents:
        result = run_checked(
            [
                args.container_command,
                "exec",
                f"agentteams-worker-{agent}",
                "cat",
                f"/root/hiclaw-fs/agents/{agent}/.copaw/token_usage.json",
            ],
            input_text="",
        )
        ledger = json.loads(result.stdout)
        if not isinstance(ledger, dict):
            raise RuntimeError(f"token ledger for {agent} is not a JSON object")
        per_agent[agent] = usage_totals(ledger)
    totals = {
        "agent_count": len(agents),
        "call_count": sum(value["call_count"] for value in per_agent.values()),
        "prompt_tokens": sum(value["prompt_tokens"] for value in per_agent.values()),
        "completion_tokens": sum(
            value["completion_tokens"] for value in per_agent.values()
        ),
    }
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    snapshot = {
        "schema_version": "agentfit.copaw-usage-snapshot/v1",
        "captured_at_ms": int(time.time() * 1000),
        "scope": "cumulative_runtime",
        "note": "Subtract a pre-run snapshot from a post-run snapshot for per-run usage.",
        "agents": per_agent,
        "totals": totals,
    }
    private_write(args.output_file, json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(f"agent_count={totals['agent_count']}")
    print(f"call_count={totals['call_count']}")
    print(f"total_tokens={totals['total_tokens']}")
    print(f"scope={snapshot['scope']}")
    return 0


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "send":
            return send(args)
        if args.command == "export-once":
            return export_once(args)
        return usage_snapshot(args)
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.strip() or f"exit {error.returncode}"
        else:
            detail = str(error)
        print(f"ERROR: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
