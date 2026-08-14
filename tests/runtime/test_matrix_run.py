import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.agentteams.m1 import matrix_run


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "runtime" / "agentteams" / "m1" / "matrix_run.py"


class MatrixRunTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        fake_docker = self.fake_bin / "docker"
        fake_docker.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = ps ]; then\n"
            "  printf '%s\\n' agentteams-controller\n"
            "elif [ \"$1\" = exec ]; then\n"
            "  cat >/dev/null\n"
            "  /bin/cat \"$FAKE_MATRIX_RESPONSE\"\n"
            "else\n"
            "  exit 64\n"
            "fi\n",
            encoding="utf-8",
        )
        fake_docker.chmod(0o700)
        self.environment = os.environ.copy()
        self.environment["PATH"] = f"{self.fake_bin}:{self.environment['PATH']}"

    def tearDown(self):
        self.tempdir.cleanup()

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_send_records_only_safe_run_metadata(self):
        response = self.write_json(
            "send-response.json",
            {
                "event_id": "$fixture-event",
                "leader_id": "@agentfit-engagement-lead:matrix.example",
            },
        )
        self.environment["FAKE_MATRIX_RESPONSE"] = str(response)
        team = self.write_json(
            "team.json",
            {
                "leaderName": "agentfit-engagement-lead",
                "leaderDMRoomID": "!dm:matrix.example",
                "teamRoomID": "!team:matrix.example",
            },
        )
        request = self.root / "request.md"
        terminal_prefix = "AGENTFIT-retail-r2-0123456789abcdef0123456789abcdef"
        request.write_text(
            f"private request body\n{terminal_prefix}", encoding="utf-8"
        )
        self.write_json(
            "provenance.json",
            {
                "run_id": "retail-r2",
                "terminal_prefix": terminal_prefix,
                "generated": {
                    "request_markdown_sha256": hashlib.sha256(
                        request.read_bytes()
                    ).hexdigest()
                },
            },
        )
        output_dir = self.root / "run"

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "send",
                "--team-file",
                str(team),
                "--request-file",
                str(request),
                "--run-id",
                "retail-r2",
                "--entry-room",
                "leader-dm",
                "--metadata-name",
                "initial-send.json",
                "--output-dir",
                str(output_dir),
            ],
            cwd=REPO_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("private request body", result.stdout + result.stderr)
        sent = json.loads(
            (output_dir / "initial-send.json").read_text(encoding="utf-8")
        )
        self.assertEqual("$fixture-event", sent["event_id"])
        self.assertEqual("leader-dm", sent["entry_room"])
        self.assertEqual("@agentfit-engagement-lead:matrix.example", sent["leader_id"])
        self.assertEqual(terminal_prefix, sent["terminal_prefix"])
        self.assertEqual(
            0o600, (output_dir / "initial-send.json").stat().st_mode & 0o777
        )

    def test_send_rejects_request_changed_after_pre_run_provenance(self):
        team = self.write_json(
            "tampered-team.json",
            {
                "leaderName": "agentfit-engagement-lead",
                "leaderDMRoomID": "!dm:matrix.example",
                "teamRoomID": "!team:matrix.example",
            },
        )
        request = self.root / "tampered-request.md"
        terminal_prefix = "AGENTFIT-retail-r2-0123456789abcdef0123456789abcdef"
        request.write_text(f"original\n{terminal_prefix}", encoding="utf-8")
        self.write_json(
            "provenance.json",
            {
                "run_id": "retail-r2",
                "terminal_prefix": terminal_prefix,
                "generated": {
                    "request_markdown_sha256": hashlib.sha256(
                        request.read_bytes()
                    ).hexdigest()
                },
            },
        )
        request.write_text(f"changed\n{terminal_prefix}", encoding="utf-8")

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "send",
                "--team-file",
                str(team),
                "--request-file",
                str(request),
                "--run-id",
                "retail-r2",
                "--output-dir",
                str(self.root / "tampered-run"),
            ],
            cwd=REPO_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("request hash", result.stderr)

    def test_export_deduplicates_rooms_and_requires_exact_leader_prefix(self):
        terminal_prefix = (
            "AGENTFIT-retail-r2-0123456789abcdef0123456789abcdef"
        )
        events = {
            "start": "old",
            "end": "new",
            "chunk": [
                {
                    "event_id": "$false-admin",
                    "sender": "@admin:matrix.example",
                    "origin_server_ts": 1100,
                    "type": "m.room.message",
                    "content": {"body": f"request contains {terminal_prefix}"},
                },
                {
                    "event_id": "$false-tool",
                    "sender": "@agentfit-engagement-lead:matrix.example",
                    "origin_server_ts": 1200,
                    "type": "m.room.message",
                    "content": {"body": f"tool echo: {terminal_prefix}"},
                },
                {
                    "event_id": "$terminal",
                    "sender": "@agentfit-engagement-lead:matrix.example",
                    "origin_server_ts": 1300,
                    "type": "m.room.message",
                    "content": {"body": f"**{terminal_prefix}** — complete"},
                },
                {
                    "event_id": "$old",
                    "sender": "@agentfit-engagement-lead:matrix.example",
                    "origin_server_ts": 900,
                    "type": "m.room.message",
                    "content": {"body": "old"},
                },
            ],
        }
        response = self.write_json("events.json", events)
        self.environment["FAKE_MATRIX_RESPONSE"] = str(response)
        output_dir = self.root / "run"
        output_dir.mkdir()
        self.write_json(
            "unused.json",
            {},
        )
        (output_dir / "send.json").write_text(
            json.dumps(
                {
                    "run_id": "retail-r2",
                    "started_at_ms": 1000,
                    "terminal_prefix": terminal_prefix,
                    "leader_id": "@agentfit-engagement-lead:matrix.example",
                    "leader_dm_room_id": "!dm:matrix.example",
                    "team_room_id": "!team:matrix.example",
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "export-once",
                "--output-dir",
                str(output_dir),
            ],
            cwd=REPO_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        conversation = json.loads(
            (output_dir / "conversation.json").read_text(encoding="utf-8")
        )
        status = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(3, len(conversation))
        self.assertTrue(status["complete"])
        self.assertEqual("$terminal", status["terminal_event_id"])
        self.assertEqual(3, status["message_event_count"])
        self.assertEqual(0o600, (output_dir / "conversation.json").stat().st_mode & 0o777)

    def test_send_rejects_a_reusable_generic_terminal_prefix(self):
        response = self.write_json(
            "generic-send-response.json",
            {
                "event_id": "$fixture-event",
                "leader_id": "@agentfit-engagement-lead:matrix.example",
            },
        )
        self.environment["FAKE_MATRIX_RESPONSE"] = str(response)
        team = self.write_json(
            "generic-team.json",
            {
                "leaderName": "agentfit-engagement-lead",
                "leaderDMRoomID": "!dm:matrix.example",
                "teamRoomID": "!team:matrix.example",
            },
        )
        request = self.root / "generic-request.md"
        request.write_text("AGENTFIT-R3-DELIVERY", encoding="utf-8")
        self.write_json(
            "provenance.json",
            {"run_id": "retail-r3", "terminal_prefix": "AGENTFIT-R3-DELIVERY"},
        )

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "send",
                "--team-file",
                str(team),
                "--request-file",
                str(request),
                "--run-id",
                "retail-r3",
                "--output-dir",
                str(self.root / "generic-run"),
            ],
            cwd=REPO_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("run-bound", result.stderr)

    def test_terminal_event_requires_leader_dm_room(self):
        leader = "@agentfit-engagement-lead:matrix.example"
        terminal_prefix = (
            "AGENTFIT-retail-r3-0123456789abcdef0123456789abcdef"
        )
        events = [
            {
                "event_id": "$team-terminal",
                "sender": leader,
                "room": "team",
                "body": f"{terminal_prefix} — wrong room",
            },
            {
                "event_id": "$dm-terminal",
                "sender": leader,
                "room": "leader_dm",
                "body": f"{terminal_prefix} — correct room",
            },
        ]
        self.assertEqual(
            "$dm-terminal",
            matrix_run.terminal_event(events, leader, terminal_prefix)["event_id"],
        )

    def test_export_room_pages_until_run_boundary(self):
        pages = [
            {
                "chunk": [
                    {
                        "event_id": "$new",
                        "origin_server_ts": 1300,
                        "type": "m.room.message",
                        "sender": "@leader:example",
                        "content": {"body": "new"},
                    }
                ],
                "end": "page-2",
            },
            {
                "chunk": [
                    {
                        "event_id": "$boundary",
                        "origin_server_ts": 900,
                        "type": "m.room.message",
                        "sender": "@leader:example",
                        "content": {"body": "old"},
                    }
                ],
                "end": "page-3",
            },
        ]
        with patch.object(matrix_run, "controller_json", side_effect=pages) as call:
            result = matrix_run.export_room_pages(
                "docker", "agentteams-controller", "!room:example", 1000
            )
        self.assertEqual(2, result["page_count"])
        self.assertEqual(["$new", "$boundary"], [e["event_id"] for e in result["chunk"]])
        self.assertEqual(2, call.call_count)

    def test_normalized_events_preserve_structured_matrix_mentions(self):
        response = {
            "team": {
                "chunk": [
                    {
                        "event_id": "$assignment",
                        "origin_server_ts": 1100,
                        "type": "m.room.message",
                        "sender": "@agentfit-engagement-lead:example",
                        "content": {
                            "body": "assignment",
                            "m.mentions": {
                                "user_ids": ["@agentfit-business-engineer:example"]
                            },
                        },
                    }
                ]
            }
        }

        events = matrix_run.normalized_events(response, 1000)

        self.assertEqual(
            ["@agentfit-business-engineer:example"],
            events[0]["mentioned_user_ids"],
        )

    def test_usage_snapshot_treats_missing_ledger_as_zero_usage(self):
        response = self.write_json(
            "usage.json",
            {
                "2026-08-14": {
                    "provider:model": {
                        "call_count": 1,
                        "prompt_tokens": 40,
                        "completion_tokens": 10,
                    }
                }
            },
        )
        missing_docker = self.fake_bin / "docker"
        missing_docker.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = ps ]; then\n"
            "  printf '%s\\n' agentteams-controller\n"
            "elif [ \"$1\" = exec ] && [ \"$2\" = agentteams-worker-agentfit-engagement-lead ]; then\n"
            "  cat >/dev/null\n"
            "  printf 'cat: /root/hiclaw-fs/agents/agentfit-engagement-lead/.copaw/token_usage.json: No such file or directory\\n' >&2\n"
            "  exit 1\n"
            "elif [ \"$1\" = exec ]; then\n"
            "  cat >/dev/null\n"
            "  /bin/cat \"$FAKE_MATRIX_RESPONSE\"\n"
            "else\n"
            "  exit 64\n"
            "fi\n",
            encoding="utf-8",
        )
        self.environment["FAKE_MATRIX_RESPONSE"] = str(response)
        team = self.write_json(
            "usage-team-missing.json",
            {
                "leaderName": "agentfit-engagement-lead",
                "leaderDMRoomID": "!dm:matrix.example",
                "teamRoomID": "!team:matrix.example",
                "workerNames": ["agentfit-business-engineer"],
            },
        )
        output = self.root / "usage-snapshot-missing.json"

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "usage-snapshot",
                "--team-file",
                str(team),
                "--output-file",
                str(output),
            ],
            cwd=REPO_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        snapshot = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(2, snapshot["totals"]["agent_count"])
        self.assertEqual(1, snapshot["totals"]["call_count"])
        self.assertEqual(40, snapshot["totals"]["prompt_tokens"])
        self.assertEqual(
            {"call_count": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            snapshot["agents"]["agentfit-engagement-lead"],
        )

    def test_usage_snapshot_aggregates_cumulative_agent_ledgers(self):
        response = self.write_json(
            "usage.json",
            {
                "2026-08-14": {
                    "provider:model": {
                        "call_count": 2,
                        "prompt_tokens": 100,
                        "completion_tokens": 25,
                    }
                }
            },
        )
        self.environment["FAKE_MATRIX_RESPONSE"] = str(response)
        team = self.write_json(
            "usage-team.json",
            {
                "leaderName": "agentfit-engagement-lead",
                "leaderDMRoomID": "!dm:matrix.example",
                "teamRoomID": "!team:matrix.example",
                "workerNames": ["agentfit-business-engineer"],
            },
        )
        output = self.root / "usage-snapshot.json"

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "usage-snapshot",
                "--team-file",
                str(team),
                "--output-file",
                str(output),
            ],
            cwd=REPO_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        snapshot = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(2, snapshot["totals"]["agent_count"])
        self.assertEqual(4, snapshot["totals"]["call_count"])
        self.assertEqual(200, snapshot["totals"]["prompt_tokens"])
        self.assertEqual(50, snapshot["totals"]["completion_tokens"])
        self.assertEqual("cumulative_runtime", snapshot["scope"])
        self.assertEqual(0o600, output.stat().st_mode & 0o777)


if __name__ == "__main__":
    unittest.main()
