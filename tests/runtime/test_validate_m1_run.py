import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "runtime" / "agentteams" / "m1" / "validate_run.py"


class ValidateM1RunTest(unittest.TestCase):
    def test_accepts_ordered_blocked_run_without_answer_payload_matches(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            run_dir = root / "run"
            dossier = root / "dossier" / "business"
            governance = root / "dossier" / "governance" / "workspace"
            run_dir.mkdir(parents=True)
            dossier.mkdir(parents=True)
            governance.mkdir(parents=True)

            leader = "@agentfit-engagement-lead:matrix.example"
            business = "@agentfit-business-engineer:matrix.example"
            auditor = "@agentfit-governance-auditor:matrix.example"
            terminal_prefix = (
                "AGENTFIT-fixture-r2-0123456789abcdef0123456789abcdef"
            )
            events = [
                {
                    "event_id": "$request",
                    "sender": "@admin:matrix.example",
                    "origin_server_ts": 1000,
                    "room": "leader_dm",
                    "body": "request",
                },
                {
                    "event_id": "$delegate-business",
                    "sender": leader,
                    "origin_server_ts": 1100,
                    "room": "team",
                    "body": (
                        f"{business} New task [fixture-project-01]: "
                        "Cross-sample semantic compilation."
                    ),
                    "mentioned_user_ids": [business],
                },
                {
                    "event_id": "$business",
                    "sender": business,
                    "origin_server_ts": 1200,
                    "room": "team",
                    "body": "TASK_COMPLETED",
                },
                {
                    "event_id": "$delegate-audit",
                    "sender": leader,
                    "origin_server_ts": 1300,
                    "room": "team",
                    "body": (
                        "agentfit-governance-auditor New task "
                        "[fixture-project-02]: Independent governance review."
                    ),
                    "mentioned_user_ids": [auditor],
                },
                {
                    "event_id": "$audit",
                    "sender": auditor,
                    "origin_server_ts": 1400,
                    "room": "team",
                    "body": "TASK_COMPLETED",
                },
                {
                    "event_id": "$terminal",
                    "sender": leader,
                    "origin_server_ts": 1500,
                    "room": "leader_dm",
                    "body": f"{terminal_prefix}\nBLOCK Candidate generation\nM1 IN_PROGRESS",
                },
            ]
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            initial_raw_rooms = {
                "team": {"chunk": []},
                "leader_dm": {"chunk": []},
            }
            for event in events:
                initial_raw_rooms[event["room"]]["chunk"].append(
                    {
                        "event_id": event["event_id"],
                        "sender": event["sender"],
                        "origin_server_ts": event["origin_server_ts"],
                        "type": "m.room.message",
                        "content": {
                            "body": event["body"],
                            "m.mentions": {
                                "user_ids": event.get("mentioned_user_ids", [])
                            },
                        },
                    }
                )
            (run_dir / "conversation.raw.json").write_text(
                json.dumps({"rooms": initial_raw_rooms}), encoding="utf-8"
            )
            (run_dir / "send.json").write_text(
                json.dumps(
                    {
                        "run_id": "fixture-r2",
                        "started_at_ms": 900,
                        "entry_room": "leader-dm",
                        "leader_id": leader,
                        "terminal_prefix": terminal_prefix,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "status.json").write_text(
                json.dumps(
                    {
                        "complete": True,
                        "terminal_event_id": "$terminal",
                        "message_event_count": len(events),
                    }
                ),
                encoding="utf-8",
            )

            for name in ("SampleSemanticSpec", "TaskSemanticSpec", "CapabilitySemanticSpec"):
                file_name = name.replace("SemanticSpec", "-semantic-spec").lower() + ".json"
                (dossier / file_name).write_text(
                    json.dumps(
                        {
                            "schema_name": name,
                            "version": "1.0.0-draft",
                            "created_by": "fixture",
                            "source_refs": ["source"],
                            "status": "draft",
                        }
                    ),
                    encoding="utf-8",
                )
            (dossier / "sample-set-manifests.json").write_text(
                json.dumps(
                    {
                        "manifests": [
                            {
                                "manifest_id": manifest_id,
                                "membership": {
                                    "membership_state": "proposed",
                                    "sample_ids": [],
                                },
                                "version": {
                                    "schema_version": "agentfit.samplesetmanifest/v1",
                                    "manifest_version": "not_instantiated",
                                    "content_hash": "not_instantiated",
                                },
                                "access_policy": {
                                    "visibility": (
                                        "auditor" if manifest_id == "sealed_holdout" else "meta_team"
                                    ),
                                    "freeze_approval": "not_instantiated",
                                    "seal_status": (
                                        "sealed"
                                        if manifest_id == "sealed_holdout"
                                        else "not_applicable"
                                        if manifest_id == "adaptation"
                                        else "open"
                                    ),
                                },
                                "isolation_rules": {
                                    "candidate_direct_access": False,
                                    "simulator_access": (
                                        "restricted"
                                        if manifest_id in {"adaptation", "sealed_holdout"}
                                        else "allowed"
                                    ),
                                    "auditor_access": (
                                        "full"
                                        if manifest_id == "sealed_holdout"
                                        else "read_only"
                                    ),
                                    "isolation_note": "fixture",
                                },
                                "status": "draft",
                                "human_freeze": "not_instantiated",
                            }
                            for manifest_id in (
                                "adaptation",
                                "validation",
                                "sealed_holdout",
                                "stress_and_failure",
                            )
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (governance / "governance_review.md").write_text(
                "BLOCK Candidate generation. Instantiate the four SampleSetManifest "
                "objects, then obtain Human freeze approval. M1 IN_PROGRESS.",
                encoding="utf-8",
            )
            project_dir = root / "dossier" / "project"
            governance_dir = root / "dossier" / "governance"
            project_dir.mkdir(parents=True)
            project_meta = {
                "project_id": "fixture-project",
                "status": "completed",
            }
            business_meta = {
                "task_id": "fixture-project-01",
                "project_id": "fixture-project",
                "assigned_to": "agentfit-business-engineer",
                "status": "submitted",
                "depends_on": [],
            }
            governance_meta = {
                "task_id": "fixture-project-02",
                "project_id": "fixture-project",
                "assigned_to": "agentfit-governance-auditor",
                "status": "submitted",
                "depends_on": ["fixture-project-01"],
            }
            for path, value in (
                (project_dir / "meta.json", project_meta),
                (dossier / "meta.json", business_meta),
                (governance_dir / "meta.json", governance_meta),
            ):
                path.write_text(json.dumps(value), encoding="utf-8")
            export_manifest_path = root / "dossier" / "export-manifest.json"

            def write_export_manifest(
                project_id: str = "fixture-project",
                business_task_id: str = "fixture-project-01",
                governance_task_id: str = "fixture-project-02",
            ) -> None:
                artifact_hashes = {
                    str(path.relative_to(root / "dossier")): hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()
                    for path in sorted((root / "dossier").rglob("*"))
                    if path.is_file() and path != export_manifest_path
                }
                export_manifest_path.write_text(
                    json.dumps(
                        {
                            "schema_version": "agentfit.agentteams-dossier-export/v1",
                            "project_id": project_id,
                            "business_task_id": business_task_id,
                            "governance_task_id": governance_task_id,
                            "shared_paths": {
                                "project": f"projects/{project_id}",
                                "business": f"tasks/{business_task_id}",
                                "governance": f"tasks/{governance_task_id}",
                            },
                            "artifact_sha256": artifact_hashes,
                        }
                    ),
                    encoding="utf-8",
                )

            write_export_manifest()
            source_tasks = root / "tasks.json"
            source_tasks.write_text(
                json.dumps(
                    [
                        {
                            "id": "0",
                            "evaluation_criteria": {
                                "actions": [{"name": "secret_action", "arguments": {"x": 1}}]
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                command := [
                    "python3",
                    str(SCRIPT),
                    "--run-dir",
                    str(run_dir),
                    "--dossier-dir",
                    str(root / "dossier"),
                    "--source-tasks",
                    str(source_tasks),
                    "--task-id",
                    "0",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(
                (run_dir / "validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual("PASS", report["verdict"])
            self.assertEqual(0, report["answer_payload_match_count"])
            self.assertEqual(
                ["business_engineer", "governance_auditor"],
                report["observed_worker_path"],
            )
            self.assertEqual(600, report["duration_ms"])
            self.assertEqual(
                "export_manifest_task_meta_and_matrix_assignment",
                report["dossier_identity_binding"],
            )

            raw_rooms = {"team": {"chunk": []}, "leader_dm": {"chunk": []}}
            for event in events:
                raw_rooms[event["room"]]["chunk"].append(
                    {
                        "event_id": event["event_id"],
                        "sender": event["sender"],
                        "origin_server_ts": event["origin_server_ts"],
                        "type": "m.room.message",
                        "content": {
                            "body": event["body"],
                            "m.mentions": {
                                "user_ids": event.get("mentioned_user_ids", [])
                            },
                        },
                    }
                )
            (run_dir / "conversation.raw.json").write_text(
                json.dumps({"rooms": raw_rooms}), encoding="utf-8"
            )
            normalized_without_mentions = [dict(event) for event in events]
            for event in normalized_without_mentions:
                event.pop("mentioned_user_ids", None)
            (run_dir / "conversation.json").write_text(
                json.dumps(normalized_without_mentions), encoding="utf-8"
            )
            raw_bound = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, raw_bound.returncode, raw_bound.stderr)
            raw_report = json.loads(
                (run_dir / "validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "structured_matrix_mentions_from_raw",
                raw_report["assignment_binding"],
            )
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )

            missing_identity_events = [dict(event) for event in events]
            missing_identity_events[3].pop("origin_server_ts")
            (run_dir / "conversation.json").write_text(
                json.dumps(missing_identity_events), encoding="utf-8"
            )
            unbound_incomplete_identity = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, unbound_incomplete_identity.returncode)
            incomplete_identity_report = json.loads(
                (run_dir / "validation.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                "normalized event has an incomplete raw Matrix identity: $delegate-audit",
                incomplete_identity_report["errors"],
            )
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )

            original_assignment_body = events[3]["body"]
            events[3]["body"] = "🔧 **taskflow** auditor mention echoed by a tool call"
            raw_assignment = next(
                raw_event
                for raw_event in raw_rooms["team"]["chunk"]
                if raw_event["event_id"] == events[3]["event_id"]
            )
            raw_assignment["content"]["body"] = events[3]["body"]
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            (run_dir / "conversation.raw.json").write_text(
                json.dumps({"rooms": raw_rooms}), encoding="utf-8"
            )
            echoed_structured_assignment = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, echoed_structured_assignment.returncode)
            events[3]["body"] = original_assignment_body
            raw_assignment["content"]["body"] = original_assignment_body

            raw_assignment["content"]["m.mentions"]["user_ids"] = []
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            (run_dir / "conversation.raw.json").write_text(
                json.dumps({"rooms": raw_rooms}), encoding="utf-8"
            )
            conflicting_mentions = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, conflicting_mentions.returncode)
            raw_assignment["content"]["m.mentions"]["user_ids"] = [auditor]

            raw_rooms["team"]["chunk"].append(
                json.loads(json.dumps(raw_assignment))
            )
            (run_dir / "conversation.raw.json").write_text(
                json.dumps({"rooms": raw_rooms}), encoding="utf-8"
            )
            duplicate_raw_identity = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, duplicate_raw_identity.returncode)
            raw_rooms["team"]["chunk"].pop()
            (run_dir / "conversation.raw.json").write_text(
                json.dumps({"rooms": raw_rooms}), encoding="utf-8"
            )

            different_project = "different-run-project"
            different_business = "different-run-project-01"
            different_governance = "different-run-project-02"
            for path, value in (
                (
                    project_dir / "meta.json",
                    {**project_meta, "project_id": different_project},
                ),
                (
                    dossier / "meta.json",
                    {
                        **business_meta,
                        "project_id": different_project,
                        "task_id": different_business,
                    },
                ),
                (
                    governance_dir / "meta.json",
                    {
                        **governance_meta,
                        "project_id": different_project,
                        "task_id": different_governance,
                        "depends_on": [different_business],
                    },
                ),
            ):
                path.write_text(json.dumps(value), encoding="utf-8")
            write_export_manifest(
                different_project, different_business, different_governance
            )
            mismatched_dossier = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, mismatched_dossier.returncode)
            for path, value in (
                (project_dir / "meta.json", project_meta),
                (dossier / "meta.json", business_meta),
                (governance_dir / "meta.json", governance_meta),
            ):
                path.write_text(json.dumps(value), encoding="utf-8")
            write_export_manifest()

            events[-1]["room"] = "team"
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            wrong_room = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, wrong_room.returncode)

            events[-1]["room"] = "leader_dm"
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            events[3]["mentioned_user_ids"] = []
            business_assignment_body = events[1]["body"]
            events[1]["body"] += f" tool echo {auditor}"
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            echoed_assignment = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, echoed_assignment.returncode)

            events[3]["mentioned_user_ids"] = [auditor]
            events[1]["body"] = business_assignment_body
            (run_dir / "conversation.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            manifests_path = dossier / "sample-set-manifests.json"
            manifest_document = json.loads(manifests_path.read_text(encoding="utf-8"))
            manifest_document["manifests"].append(manifest_document["manifests"][0])
            manifests_path.write_text(json.dumps(manifest_document), encoding="utf-8")
            duplicate_manifest = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, duplicate_manifest.returncode)

            manifest_document["manifests"].pop()
            sealed = next(
                manifest
                for manifest in manifest_document["manifests"]
                if manifest["manifest_id"] == "sealed_holdout"
            )
            sealed["access_policy"]["visibility"] = "meta_team"
            sealed["access_policy"]["seal_status"] = "open"
            sealed["isolation_rules"]["simulator_access"] = "allowed"
            manifests_path.write_text(json.dumps(manifest_document), encoding="utf-8")
            unsafe_holdout = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, unsafe_holdout.returncode)

            sealed["access_policy"]["visibility"] = "auditor"
            sealed["access_policy"]["seal_status"] = "sealed"
            sealed["isolation_rules"]["simulator_access"] = "restricted"
            manifests_path.write_text(json.dumps(manifest_document), encoding="utf-8")
            write_export_manifest()
            missing_source_command = [*command]
            task_id_index = missing_source_command.index("--task-id") + 1
            missing_source_command[task_id_index] = "999"
            missing_source = subprocess.run(
                missing_source_command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, missing_source.returncode)

            sent_document = json.loads((run_dir / "send.json").read_text(encoding="utf-8"))
            sent_document.pop("terminal_prefix")
            (run_dir / "send.json").write_text(
                json.dumps(sent_document), encoding="utf-8"
            )
            legacy = subprocess.run(
                [
                    *command,
                    "--allow-legacy-unbound-prefix",
                    "--legacy-terminal-prefix",
                    terminal_prefix,
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, legacy.returncode, legacy.stderr)
            legacy_report = json.loads(
                (run_dir / "validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "legacy_cli_only", legacy_report["terminal_prefix_binding"]
            )


if __name__ == "__main__":
    unittest.main()
