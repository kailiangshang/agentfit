#!/usr/bin/env python3
"""Validate an AgentFit M1 ProjectCase-preparation run without exposing answers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

try:
    from .run_identity import require_run_terminal_prefix
except ImportError:
    from run_identity import require_run_terminal_prefix


MANIFEST_IDS = {
    "adaptation",
    "validation",
    "sealed_holdout",
    "stress_and_failure",
}
ROLE_SUFFIXES = (
    ("agentfit-business-engineer", "business_engineer"),
    ("agentfit-governance-auditor", "governance_auditor"),
    ("agentfit-agent-architect", "agent_architect"),
    ("agentfit-validation-engineer", "validation_engineer"),
)
SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--dossier-dir", type=Path, required=True)
    parser.add_argument("--source-tasks", type=Path, required=True)
    parser.add_argument("--task-id", action="append", required=True)
    parser.add_argument("--allow-legacy-unbound-prefix", action="store_true")
    parser.add_argument("--legacy-terminal-prefix")
    return parser.parse_args()


def private_json(path: Path, value: dict[str, Any]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_containers(value: Any) -> Iterator[Any]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_containers(child)
    elif isinstance(value, list):
        yield value
        for child in value:
            yield from walk_containers(child)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def criteria_fingerprints(
    tasks: list[Any], task_ids: set[str]
) -> tuple[set[str], set[str]]:
    fingerprints: set[str] = set()
    found_ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict) or str(task.get("id")) not in task_ids:
            continue
        found_ids.add(str(task["id"]))
        criteria = task.get("evaluation_criteria")
        for value in walk_containers(criteria):
            encoded = canonical(value)
            if len(encoded) >= 40 and value:
                fingerprints.add(encoded)
    return fingerprints, found_ids


def dossier_fingerprints(dossier_dir: Path) -> tuple[set[str], int]:
    fingerprints: set[str] = set()
    count = 0
    for path in sorted(dossier_dir.rglob("*.json")):
        value = load_json(path)
        count += 1
        for child in walk_containers(value):
            fingerprints.add(canonical(child))
    return fingerprints, count


def role_for_sender(sender: str) -> str | None:
    for suffix, role in ROLE_SUFFIXES:
        if sender.startswith(f"@{suffix}:"):
            return role
    return None


def first_line(body: str) -> str:
    value = next((line.strip() for line in body.splitlines() if line.strip()), "")
    return value.lstrip("#>*_ -✅🔧")


def bind_structured_mentions_from_raw(
    run_dir: Path, events: list[Any]
) -> tuple[list[Any], str, list[str]]:
    """Recover missing Matrix mentions only from byte-for-byte matching raw events."""

    raw_path = run_dir / "conversation.raw.json"
    if not raw_path.is_file():
        return events, "structured_matrix_mentions_unavailable", [
            "raw Matrix export is absent"
        ]
    raw_document = load_json(raw_path)
    if not isinstance(raw_document, dict):
        return events, "structured_matrix_mentions_unavailable", [
            "raw Matrix export is not a JSON object"
        ]
    rooms = raw_document.get("rooms")
    if not isinstance(rooms, dict):
        return events, "structured_matrix_mentions_unavailable", [
            "raw Matrix export lacks rooms"
        ]

    raw_mentions: dict[tuple[str, str, int, str, str], list[str]] = {}
    duplicate_keys: set[tuple[str, str, int, str, str]] = set()
    for room_label in ("team", "leader_dm"):
        room = rooms.get(room_label)
        if not isinstance(room, dict) or not isinstance(room.get("chunk"), list):
            continue
        for raw_event in room["chunk"]:
            if not isinstance(raw_event, dict) or raw_event.get("type") != "m.room.message":
                continue
            content = raw_event.get("content")
            if not isinstance(content, dict) or not isinstance(content.get("body"), str):
                continue
            identity_values = (
                raw_event.get("event_id"),
                raw_event.get("sender"),
                raw_event.get("origin_server_ts"),
            )
            if not (
                isinstance(identity_values[0], str)
                and isinstance(identity_values[1], str)
                and isinstance(identity_values[2], int)
            ):
                continue
            mentions = content.get("m.mentions")
            user_ids = mentions.get("user_ids", []) if isinstance(mentions, dict) else []
            if not isinstance(user_ids, list) or not all(
                isinstance(user_id, str) for user_id in user_ids
            ):
                continue
            key = (
                identity_values[0],
                identity_values[1],
                identity_values[2],
                content["body"],
                room_label,
            )
            normalized = sorted(set(user_ids))
            if key in raw_mentions:
                duplicate_keys.add(key)
            raw_mentions[key] = normalized

    bound_events: list[Any] = []
    recovered = False
    integrity_errors: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            bound_events.append(event)
            continue
        bound_event = dict(event)
        direct_mentions = bound_event.get("mentioned_user_ids")
        direct_is_valid = isinstance(direct_mentions, list) and all(
            isinstance(user_id, str) for user_id in direct_mentions
        )
        identity_values = (
            bound_event.get("event_id"),
            bound_event.get("sender"),
            bound_event.get("origin_server_ts"),
            bound_event.get("body"),
            bound_event.get("room"),
        )
        identity_is_valid = (
            isinstance(identity_values[0], str)
            and isinstance(identity_values[1], str)
            and isinstance(identity_values[2], int)
            and isinstance(identity_values[3], str)
            and isinstance(identity_values[4], str)
        )
        if not identity_is_valid:
            event_label = (
                identity_values[0]
                if isinstance(identity_values[0], str)
                else "<unknown>"
            )
            integrity_errors.append(
                f"normalized event has an incomplete raw Matrix identity: {event_label}"
            )
        else:
            event_label = identity_values[0]
            if identity_values in duplicate_keys:
                integrity_errors.append(
                    f"raw Matrix export duplicates event identity {event_label}"
                )
            elif identity_values not in raw_mentions:
                integrity_errors.append(
                    f"normalized event lacks an exact raw Matrix match: {event_label}"
                )
            else:
                recovered_mentions = raw_mentions[identity_values]
                if direct_is_valid:
                    normalized_direct = sorted(set(direct_mentions))
                    bound_event["mentioned_user_ids"] = normalized_direct
                    if normalized_direct != recovered_mentions:
                        integrity_errors.append(
                            f"normalized/raw Matrix mentions conflict: {event_label}"
                        )
                else:
                    bound_event["mentioned_user_ids"] = recovered_mentions
                    recovered = True
        bound_events.append(bound_event)
    all_mentions_bound = all(
        isinstance(event, dict)
        and isinstance(event.get("mentioned_user_ids"), list)
        and all(isinstance(user_id, str) for user_id in event["mentioned_user_ids"])
        for event in bound_events
    )
    if integrity_errors or not all_mentions_bound:
        binding = "structured_matrix_mentions_invalid"
    elif recovered:
        binding = "structured_matrix_mentions_from_raw"
    else:
        binding = "structured_matrix_mentions"
    return bound_events, binding, integrity_errors


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dossier_identity(
    dossier_dir: Path, terminal_prefix_binding: str
) -> tuple[dict[str, str], str, list[str]]:
    errors: list[str] = []

    def object_at(relative: str) -> dict[str, Any]:
        value = load_json(dossier_dir / relative)
        if not isinstance(value, dict):
            raise ValueError(f"{relative} must be a JSON object")
        return value

    project = object_at("project/meta.json")
    business = object_at("business/meta.json")
    governance = object_at("governance/meta.json")
    identities = {
        "project_id": str(project.get("project_id", "")),
        "business_task_id": str(business.get("task_id", "")),
        "governance_task_id": str(governance.get("task_id", "")),
    }
    for label, value in identities.items():
        if not SAFE_IDENTIFIER.fullmatch(value):
            errors.append(f"Dossier {label} is not a safe non-empty identifier")
    project_id = identities["project_id"]
    if business.get("project_id") != project_id:
        errors.append("Business task project_id differs from Project metadata")
    if governance.get("project_id") != project_id:
        errors.append("Governance task project_id differs from Project metadata")
    if business.get("assigned_to") != "agentfit-business-engineer":
        errors.append("Business task assigned_to differs from BusinessEngineer")
    if governance.get("assigned_to") != "agentfit-governance-auditor":
        errors.append("Governance task assigned_to differs from GovernanceAuditor")
    depends_on = governance.get("depends_on")
    if not isinstance(depends_on, list) or identities["business_task_id"] not in depends_on:
        errors.append("Governance task does not depend on the Business task")

    export_path = dossier_dir / "export-manifest.json"
    if not export_path.is_file():
        if terminal_prefix_binding == "legacy_cli_only":
            return identities, "legacy_task_meta_and_matrix_assignment", errors
        errors.append("modern Dossier lacks export-manifest.json")
        return identities, "export_manifest_unavailable", errors

    export_manifest = object_at("export-manifest.json")
    if export_manifest.get("schema_version") != "agentfit.agentteams-dossier-export/v1":
        errors.append("Dossier export manifest has an unexpected schema_version")
    for field, value in identities.items():
        if export_manifest.get(field) != value:
            errors.append(f"Dossier export manifest {field} differs from task metadata")
    expected_paths = {
        "project": f"projects/{identities['project_id']}",
        "business": f"tasks/{identities['business_task_id']}",
        "governance": f"tasks/{identities['governance_task_id']}",
    }
    if export_manifest.get("shared_paths") != expected_paths:
        errors.append("Dossier export manifest shared_paths differ from metadata")

    artifact_hashes = export_manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        errors.append("Dossier export manifest lacks artifact_sha256")
        artifact_hashes = {}
    symlinks = [path for path in dossier_dir.rglob("*") if path.is_symlink()]
    if symlinks:
        errors.append("Dossier contains unsupported symlinks")
    actual_files = {
        str(path.relative_to(dossier_dir))
        for path in dossier_dir.rglob("*")
        if path.is_file() and path != export_path
    }
    if set(artifact_hashes) != actual_files:
        errors.append("Dossier export manifest artifact set differs from exported files")
    dossier_root = dossier_dir.resolve()
    for relative, expected_hash in artifact_hashes.items():
        relative_path = Path(relative)
        unresolved_target = dossier_dir / relative_path
        target = unresolved_target.resolve()
        try:
            target.relative_to(dossier_root)
        except ValueError:
            errors.append(f"Dossier export manifest contains unsafe path: {relative}")
            continue
        if (
            relative_path.is_absolute()
            or unresolved_target.is_symlink()
            or not target.is_file()
        ):
            errors.append(f"Dossier export manifest artifact is unavailable: {relative}")
            continue
        if not isinstance(expected_hash, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_hash
        ):
            errors.append(f"Dossier export manifest hash is invalid: {relative}")
            continue
        if sha256_file(target) != expected_hash:
            errors.append(f"Dossier artifact hash mismatch: {relative}")
    return identities, "export_manifest_task_meta_and_matrix_assignment", errors


def is_native_task_assignment(
    event: dict[str, Any], worker_name: str, worker_id: str, task_id: str
) -> bool:
    mentions = event.get("mentioned_user_ids")
    if mentions != [worker_id]:
        return False
    first = next(
        (line.strip() for line in str(event.get("body", "")).splitlines() if line.strip()),
        "",
    )
    return first.startswith(f"{worker_name} New task [{task_id}]:") or first.startswith(
        f"{worker_id} New task [{task_id}]:"
    )


def validate(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    sent = load_json(args.run_dir / "send.json")
    status = load_json(args.run_dir / "status.json")
    events = load_json(args.run_dir / "conversation.json")
    if not isinstance(events, list) or not events:
        raise ValueError("conversation must be a non-empty JSON list")
    events, assignment_binding, mention_integrity_errors = bind_structured_mentions_from_raw(
        args.run_dir, events
    )
    errors.extend(mention_integrity_errors)

    if sent.get("entry_room") != "leader-dm":
        errors.append("run did not enter through Leader DM")
    recorded_prefix = sent.get("terminal_prefix")
    run_id = sent.get("run_id")
    if isinstance(recorded_prefix, str):
        try:
            terminal_prefix = require_run_terminal_prefix(run_id, recorded_prefix)
            terminal_prefix_binding = "run_bound_send_metadata"
        except ValueError as error:
            terminal_prefix = recorded_prefix
            terminal_prefix_binding = "invalid"
            errors.append(str(error))
    elif (
        recorded_prefix is None
        and args.allow_legacy_unbound_prefix
        and isinstance(args.legacy_terminal_prefix, str)
        and args.legacy_terminal_prefix
    ):
        terminal_prefix = args.legacy_terminal_prefix
        terminal_prefix_binding = "legacy_cli_only"
    else:
        terminal_prefix = ""
        terminal_prefix_binding = "invalid"
        errors.append("terminal prefix is absent from send metadata")
    if status.get("complete") is not True:
        errors.append("collector did not verify a terminal event")
    if status.get("message_event_count") != len(events):
        errors.append("status message count differs from conversation")

    leader_id = sent.get("leader_id")
    terminal_id = status.get("terminal_event_id")
    terminal = next((event for event in events if event.get("event_id") == terminal_id), None)
    if not terminal:
        errors.append("terminal event is absent from conversation")
        terminal_body = ""
    else:
        terminal_body = str(terminal.get("body", ""))
        if terminal.get("sender") != leader_id:
            errors.append("terminal event sender is not the exact Leader")
        if terminal.get("room") != "leader_dm":
            errors.append("terminal event is not in the Leader DM room")
        normalized_terminal = first_line(terminal_body)
        if not normalized_terminal.startswith(terminal_prefix):
            errors.append("terminal event does not begin with the required prefix")
        else:
            remainder = normalized_terminal[
                len(terminal_prefix) : len(terminal_prefix) + 1
            ]
            if remainder and remainder.isalnum():
                errors.append("terminal event prefix has no token boundary")
        if "BLOCK" not in terminal_body or "M1 IN_PROGRESS" not in terminal_body:
            errors.append("terminal event weakens the BLOCK/M1 boundary")

    identities, dossier_identity_binding, dossier_identity_errors = dossier_identity(
        args.dossier_dir, terminal_prefix_binding
    )
    errors.extend(dossier_identity_errors)

    observed_worker_path: list[str] = []
    role_counts: dict[str, int] = {role: 0 for _, role in ROLE_SUFFIXES}
    for event in events:
        role = role_for_sender(str(event.get("sender", "")))
        if role:
            role_counts[role] += 1
            if role not in observed_worker_path:
                observed_worker_path.append(role)
    if observed_worker_path != ["business_engineer", "governance_auditor"]:
        errors.append("worker path is not BusinessEngineer then GovernanceAuditor only")
    role_event_indexes = {
        role: [
            index
            for index, event in enumerate(events)
            if role_for_sender(str(event.get("sender", ""))) == role
        ]
        for _, role in ROLE_SUFFIXES
    }
    business_indexes = role_event_indexes["business_engineer"]
    governance_indexes = role_event_indexes["governance_auditor"]
    terminal_index = next(
        (index for index, event in enumerate(events) if event.get("event_id") == terminal_id),
        None,
    )
    if business_indexes and governance_indexes:
        if max(business_indexes) >= min(governance_indexes):
            errors.append("BusinessEngineer messages continue after governance starts")
        for worker_name, task_id, first_worker_index in (
            (
                "agentfit-business-engineer",
                identities["business_task_id"],
                min(business_indexes),
            ),
            (
                "agentfit-governance-auditor",
                identities["governance_task_id"],
                min(governance_indexes),
            ),
        ):
            worker_id = str(events[first_worker_index].get("sender", ""))
            assigned = any(
                index < first_worker_index
                and event.get("sender") == leader_id
                and event.get("room") == "team"
                and is_native_task_assignment(
                    event, worker_name, worker_id, task_id
                )
                for index, event in enumerate(events)
            )
            if not assigned:
                errors.append(f"Leader assignment for {worker_name} is absent or late")
        if terminal_index is not None and terminal_index <= max(governance_indexes):
            errors.append("terminal event precedes GovernanceAuditor completion")

    business_dir = args.dossier_dir / "business"
    semantic_files = {
        "sample-semantic-spec.json": "SampleSemanticSpec",
        "task-semantic-spec.json": "TaskSemanticSpec",
        "capability-semantic-spec.json": "CapabilitySemanticSpec",
    }
    for file_name, schema_name in semantic_files.items():
        path = business_dir / file_name
        value = load_json(path)
        if not isinstance(value, dict):
            errors.append(f"{file_name} is not a JSON object")
            continue
        for field in ("schema_name", "version", "created_by", "source_refs", "status"):
            if field not in value:
                errors.append(f"{file_name} lacks {field}")
        if value.get("schema_name") != schema_name:
            errors.append(f"{file_name} has an unexpected schema_name")

    manifests = load_json(business_dir / "sample-set-manifests.json")
    if not isinstance(manifests, dict):
        raise ValueError("sample-set-manifests.json must be a JSON object")
    manifest_values = manifests.get("manifests", [])
    if not isinstance(manifest_values, list):
        errors.append("manifest contracts must be a JSON list")
        manifest_values = []
    if not all(isinstance(manifest, dict) for manifest in manifest_values):
        errors.append("every manifest contract must be a JSON object")
        manifest_values = [
            manifest for manifest in manifest_values if isinstance(manifest, dict)
        ]
    manifest_identifiers = [manifest.get("manifest_id") for manifest in manifest_values]
    if (
        len(manifest_values) != 4
        or len(set(manifest_identifiers)) != 4
        or set(manifest_identifiers) != MANIFEST_IDS
    ):
        errors.append("four required manifest contracts are not distinct and complete")
    for manifest in manifest_values:
        identifier = manifest.get("manifest_id", "unknown")
        membership = manifest.get("membership")
        if not isinstance(membership, dict):
            errors.append(f"manifest {identifier} lacks membership contract")
            membership = {}
        if membership.get("membership_state") != "proposed":
            errors.append(f"manifest {identifier} lacks membership state")
        if not isinstance(membership.get("sample_ids"), list):
            errors.append(f"manifest {identifier} lacks sample_ids list")
        version = manifest.get("version")
        if not isinstance(version, dict):
            errors.append(f"manifest {identifier} lacks version contract")
            version = {}
        if version.get("schema_version") != "agentfit.samplesetmanifest/v1":
            errors.append(f"manifest {identifier} lacks schema_version")
        if version.get("manifest_version") != "not_instantiated":
            errors.append(f"manifest {identifier} invents manifest_version")
        if version.get("content_hash") != "not_instantiated":
            errors.append(f"manifest {identifier} invents content_hash")
        if manifest.get("human_freeze") != "not_instantiated":
            errors.append(f"manifest {identifier} invents Human freeze")
        access_policy = manifest.get("access_policy")
        if not isinstance(access_policy, dict):
            errors.append(f"manifest {identifier} lacks access policy")
            access_policy = {}
        for field in ("visibility", "freeze_approval", "seal_status"):
            if field not in access_policy:
                errors.append(f"manifest {identifier} access policy lacks {field}")
        if access_policy.get("freeze_approval") != "not_instantiated":
            errors.append(f"manifest {identifier} invents access freeze approval")
        isolation_rules = manifest.get("isolation_rules")
        if not isinstance(isolation_rules, dict):
            errors.append(f"manifest {identifier} lacks isolation rules")
            isolation_rules = {}
        for field in (
            "candidate_direct_access",
            "simulator_access",
            "auditor_access",
            "isolation_note",
        ):
            if field not in isolation_rules:
                errors.append(f"manifest {identifier} isolation rules lack {field}")
        if isolation_rules.get("candidate_direct_access") is not False:
            errors.append(f"manifest {identifier} permits Candidate direct access")
        if manifest.get("status") != "draft":
            errors.append(f"manifest {identifier} is not a draft contract")
        expected_security = {
            "adaptation": ("meta_team", "not_applicable", "restricted", "read_only"),
            "validation": ("meta_team", "open", "allowed", "read_only"),
            "sealed_holdout": ("auditor", "sealed", "restricted", "full"),
            "stress_and_failure": ("meta_team", "open", "allowed", "read_only"),
        }.get(identifier)
        if expected_security:
            expected_visibility, expected_seal, expected_simulator, expected_auditor = (
                expected_security
            )
            if access_policy.get("visibility") != expected_visibility:
                errors.append(f"manifest {identifier} has unsafe visibility")
            if access_policy.get("seal_status") != expected_seal:
                errors.append(f"manifest {identifier} has unsafe seal_status")
            if isolation_rules.get("simulator_access") != expected_simulator:
                errors.append(f"manifest {identifier} has unsafe simulator_access")
            if isolation_rules.get("auditor_access") != expected_auditor:
                errors.append(f"manifest {identifier} has unsafe auditor_access")

    review_path = args.dossier_dir / "governance" / "workspace" / "governance_review.md"
    review = review_path.read_text(encoding="utf-8")
    instantiate_at = review.lower().find("instantiate the four samplesetmanifest")
    freeze_at = review.lower().find("human freeze approval", instantiate_at + 1)
    if "BLOCK" not in review or instantiate_at < 0 or freeze_at < instantiate_at:
        errors.append("governance review does not preserve instantiate-then-freeze order")

    source_tasks = load_json(args.source_tasks)
    if not isinstance(source_tasks, list):
        raise ValueError("source tasks must be a JSON list")
    requested_task_ids = set(args.task_id)
    criteria, found_task_ids = criteria_fingerprints(source_tasks, requested_task_ids)
    missing_task_ids = requested_task_ids - found_task_ids
    if missing_task_ids:
        errors.append(f"source tasks are missing requested ids: {sorted(missing_task_ids)}")
    if not criteria:
        errors.append("requested source tasks contain no comparable evaluation criteria")
    outputs, json_files_checked = dossier_fingerprints(args.dossier_dir)
    answer_matches = criteria & outputs
    if answer_matches:
        errors.append("official answer payload structure appears in dossier JSON")

    start_ms = int(sent["started_at_ms"])
    end_ms = int(terminal["origin_server_ts"]) if terminal else int(events[-1]["origin_server_ts"])
    report = {
        "schema_version": "agentfit.m1-run-validation/v1",
        "run_id": sent.get("run_id"),
        "verdict": "PASS" if not errors else "FAIL",
        "duration_ms": end_ms - start_ms,
        "message_event_count": len(events),
        "observed_worker_path": observed_worker_path,
        "role_message_counts": role_counts,
        "manifest_contract_count": len(manifest_values),
        "json_files_checked": json_files_checked,
        "answer_payload_match_count": len(answer_matches),
        "answer_match_scope": "exact canonical non-empty JSON containers of length >= 40 in dossier JSON",
        "terminal_prefix_binding": terminal_prefix_binding,
        "assignment_binding": assignment_binding,
        "dossier_identity_binding": dossier_identity_binding,
        "evidence_boundary": "M1 ProjectCase preparation; no Candidate or EvaluationRun",
        "errors": errors,
    }
    return report, errors


def main() -> int:
    args = parse_args()
    try:
        report, errors = validate(args)
        private_json(args.run_dir / "validation.json", report)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"verdict={report['verdict']}")
    print(f"duration_ms={report['duration_ms']}")
    print(f"message_event_count={report['message_event_count']}")
    print(f"answer_payload_match_count={report['answer_payload_match_count']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
