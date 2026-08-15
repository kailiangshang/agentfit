#!/usr/bin/env python3
"""Build an answer-free AgentFit ProjectCase preparation batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from .run_identity import new_terminal_prefix, require_run_id
except ImportError:
    from run_identity import new_terminal_prefix, require_run_id


MANIFEST_NAMES = (
    "adaptation",
    "validation",
    "sealed_holdout",
    "stress_and_failure",
)
SUPPORTED_SOURCE_VERSION = "tau2-bench/v1.0.1"
SOURCE_TOP_LEVEL_FIELDS = {
    "id",
    "description",
    "user_scenario",
    "initial_state",
    "evaluation_criteria",
    "issues",
}
VISIBLE_SOURCE_FIELDS = {"id", "description", "user_scenario", "initial_state"}
NESTED_SOURCE_FIELDS = {
    ("description",): {"notes", "purpose", "relevant_policies"},
    ("user_scenario",): {"instructions", "persona"},
    ("user_scenario", "instructions"): {
        "domain",
        "known_info",
        "reason_for_call",
        "task_instructions",
        "unknown_info",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sanitize benchmark source tasks and build an M1 preparation request."
    )
    parser.add_argument("--tasks-file", type=Path, required=True)
    parser.add_argument("--policy-file", type=Path, required=True)
    parser.add_argument("--task-id", action="append", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest-file", type=Path, required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--phase",
        choices=("contracts", "instantiate"),
        default="contracts",
        help="contracts: draft the four manifest contracts; "
        "instantiate: fill entity-group-aware memberships, versions and hashes",
    )
    return parser.parse_args()


def load_tasks(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("tasks file must contain a JSON list")
    if not all(isinstance(task, dict) for task in value):
        raise ValueError("each source task must be a JSON object")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_source_schema(source: dict[str, Any]) -> None:
    unknown = set(source) - SOURCE_TOP_LEVEL_FIELDS
    if unknown:
        raise ValueError(
            f"source schema drift at root: unexpected fields {sorted(unknown)}"
        )
    for required in (
        "id",
        "description",
        "user_scenario",
        "initial_state",
        "evaluation_criteria",
    ):
        if required not in source:
            raise ValueError(f"source schema drift at root: missing field {required}")

    def validate_nested(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            allowed = NESTED_SOURCE_FIELDS.get(path)
            if allowed is None:
                if value:
                    raise ValueError(
                        f"source schema drift at {'.'.join(path)}: nested object is not allowed"
                    )
                return
            unexpected = set(value) - allowed
            if unexpected:
                raise ValueError(
                    f"source schema drift at {'.'.join(path)}: "
                    f"unexpected fields {sorted(unexpected)}"
                )
            for key, child in value.items():
                validate_nested(child, (*path, key))
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, (dict, list)):
                    validate_nested(child, (*path, "[]"))

    for field in VISIBLE_SOURCE_FIELDS - {"id", "initial_state"}:
        validate_nested(source[field], (field,))
    if isinstance(source["initial_state"], (dict, list)) and source["initial_state"]:
        raise ValueError("source schema drift at initial_state: expected null for retail v1.0.1")


def select_samples(
    tasks: list[dict[str, Any]], task_ids: list[str], source_version: str
) -> dict[str, Any]:
    if source_version != SUPPORTED_SOURCE_VERSION:
        raise ValueError(
            f"unsupported source version: {source_version}; expected {SUPPORTED_SOURCE_VERSION}"
        )
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("task ids must be unique")
    by_id = {str(task.get("id")): task for task in tasks}
    missing = [task_id for task_id in task_ids if task_id not in by_id]
    if missing:
        raise ValueError(f"task ids not found: {', '.join(missing)}")

    samples = []
    for task_id in task_ids:
        source = by_id[task_id]
        if not isinstance(source, dict):
            raise ValueError(f"task {task_id} must be a JSON object")
        validate_source_schema(source)
        sanitized = {key: source[key] for key in sorted(VISIBLE_SOURCE_FIELDS)}
        samples.append(
            {
                "sample_id": task_id,
                "sample_class": "official_source_sample",
                "source_ref": f"{source_version}:retail/tasks.json#task-{task_id}",
                "source_record_sha256": sha256_bytes(
                    json.dumps(
                        source,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ),
                "source_material": sanitized,
                "exposure_policy": {
                    "meta_team_visible": [
                        "description",
                        "user_scenario",
                        "initial_state",
                    ],
                    "future_candidate_direct_input": [],
                    "user_simulator_only": ["user_scenario.instructions"],
                    "excluded": ["official_answer_rubric"],
                    "note": (
                        "The meta-team may use simulator instructions to define the "
                        "sample contract, but a future Candidate must receive them only "
                        "through an approved user simulator, never as direct context."
                    ),
                },
            }
        )

    return {
        "schema_version": "agentfit.projectcase-source-batch/v1",
        "source_version": source_version,
        "task_ids": task_ids,
        "answer_material": "excluded",
        "samples": samples,
    }


PHASE_GOALS = {
    "contracts": (
        "Goal: compile the supplied {source_version} retail batch into an "
        "auditable cross-sample semantic draft, define the missing manifest "
        "contracts in the correct lifecycle order, and decide whether Candidate "
        "generation is permitted."
    ),
    "instantiate": (
        "Goal: instantiate the four SampleSetManifest contracts from the "
        "supplied {source_version} retail batch with entity-group-aware "
        "membership assignments, per-manifest version and content-hash fields, "
        "access policies, and isolation rules; then obtain an independent "
        "governance review of membership states and decide whether Human freeze "
        "approval may be requested."
    ),
}

PHASE_STEP_2 = {
    "contracts": (
        "2. BusinessEngineer must publish batch-level `SampleSemanticSpec`, "
        "`TaskSemanticSpec`, and `CapabilitySemanticSpec` drafts, plus all four "
        "SampleSetManifest contracts: {manifests}."
    ),
    "instantiate": (
        "2. BusinessEngineer must instantiate all four SampleSetManifest "
        "contracts ({manifests}) with entity-group-aware membership: no entity "
        "group may span evaluation splits, and near-duplicate entity groups must "
        "stay inside one manifest. Members not assignable from this batch remain "
        "literally `not_instantiated` with an explicit unresolved reason."
    ),
}

PHASE_STEP_3 = {
    "contracts": (
        "3. Every contract or artifact that does not exist must use the literal "
        "`not_instantiated` in the relevant field. Define all four "
        "SampleSetManifest contracts, membership state, version/hash fields, "
        "access policy, and isolation rules before any Human freeze request."
    ),
    "instantiate": (
        "3. Every membership entry must carry its sample reference and a "
        "computed content hash — computed from the supplied batch, never "
        "invented. Version and hash fields must be filled for instantiated "
        "manifests. `sealed_holdout` may stay `not_instantiated` only with an "
        "explicit entity-supply justification and re-supply conditions."
    ),
}

PHASE_STEP_5 = {
    "contracts": (
        "5. GovernanceAuditor must report the earliest missing predecessor as "
        "the minimum next action. It must never recommend Human freeze before "
        "all four manifest contracts and membership states exist."
    ),
    "instantiate": (
        "5. GovernanceAuditor must report the earliest missing predecessor as "
        "the minimum next action, and must audit entity leakage explicitly: a "
        "recommendation of Human freeze is permitted only when all four "
        "manifests have instantiated memberships or justified "
        "`not_instantiated` states, with no entity group spanning splits."
    ),
}


def render_request(
    run_id: str,
    terminal_prefix: str,
    source_version: str,
    batch: dict[str, Any],
    policy: str,
    phase: str = "contracts",
) -> str:
    manifests = ", ".join(f"`{name}`" for name in MANIFEST_NAMES)
    batch_json = json.dumps(batch, ensure_ascii=False, indent=2)
    sample_count = len(batch["samples"])
    goal = PHASE_GOALS[phase].format(source_version=source_version)
    step2 = PHASE_STEP_2[phase].format(manifests=manifests)
    step3 = PHASE_STEP_3[phase]
    step5 = PHASE_STEP_5[phase]
    return f"""# AgentFit runtime experiment: {run_id}

This is a real M1 ProjectCase-preparation run on {sample_count} public source sample(s). It is not a Candidate run, Trial, EvaluationRun, or closed-loop result.

{goal}

## Required collaboration chain

1. You are EngagementLead. Create a Project and delegate semantic compilation only to BusinessEngineer in the Team Room. Keep AgentArchitect and ValidationEngineer unassigned.
{step2}
{step3}
4. After BusinessEngineer completes, delegate an independent dependency-order review only to GovernanceAuditor.
{step5}
6. Finish in the Leader DM with a human-facing message whose normalized first line begins `{terminal_prefix}`. Preserve the auditor decision.

## Skill usage (installed in your containers)

- BusinessEngineer: use the published skill `s1-task-compile` for all manifest hashing. Invoke exactly:
  `python3 /root/.copaw-worker/agentfit-business-engineer/skills/s1-task-compile/compute_set_hashes.py --batch <batch.json> --members adaptation=<ids> --members validation=<ids> --members stress_and_failure=<ids>`
  Its `set_model_sha256` output is the only acceptable hash source; do not hand-write hashing logic.
- GovernanceAuditor: use the published skill `s5-independent-audit` for independent verification. Invoke exactly:
  `python3 /root/.copaw-worker/agentfit-governance-auditor/skills/s5-independent-audit/verify_manifests.py --batch <batch.json> --manifests <sample-set-manifests.json>`
  Quote its `verdict` and `minimum_next_action` verbatim in the audit result; its FAIL is a FAIL.
- The four manifests must also be published as machine-readable JSON in one file `sample-set-manifests.json` (each manifest conforming to `agentfit.samplesetmanifest/v1`: schema_version, manifest_name, contract_status, freeze_state, membership[{{sample_id, source_ref, content_sha256, entity_group, membership_state}}], set_hash{{method, member_order, set_model_sha256}}, access_policy, isolation_rules; `not_instantiated` requires not_instantiated_reason). Markdown summaries may accompany but never replace the JSON.

## Binding evidence and access boundaries

- The {sample_count} selected record(s) are public official source samples, not sealed holdout evidence.
- The official answer rubric was deliberately removed before this request was built.
- `user_scenario.instructions` is visible to the meta-team only for sample construction. A future Candidate must receive it only through an approved user simulator, not as direct input.
- No Sample/Task contract or SampleSetManifest has Human freeze approval.
- No CandidateVersion, TrialSpec, EvaluationUnit, or ExecutionTrace has been instantiated.
- Do not invent hashes, approvals, tool results, benchmark outcomes, or sealed members.
- Entity pollution discipline: the same entity (person, order, ticket) appearing across tasks is dataset pollution, not reuse evidence. Entity keys are for leakage-control grouping only; all reuse signals must be computed from task semantics.
- Keep M1 `IN_PROGRESS`; M2/M3/M4 are not started.

## Cross-sample questions

- What semantics stay invariant across the selected samples, and which distinctions are sample-specific?
- Which distinctions belong in Tool, Skill, Memory, MCP, Agent topology, or Human boundaries?
- Which information is meta-team-only, simulator-only, Candidate-visible, or auditor-only?
- Which manifest memberships can be proposed from these public samples, and which must remain explicitly unresolved?

## Sanitized source batch

```json
{batch_json}
```

## Official retail policy

{policy.rstrip()}
"""


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
    path.chmod(0o600)


def provenance_document(
    args: argparse.Namespace,
    terminal_prefix: str,
    request: str,
    batch_text: str,
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    files = {
        "source_tasks": args.tasks_file,
        "retail_policy": args.policy_file,
        "agentteams_manifest": args.manifest_file,
        "prepare_projectcase": Path(__file__).resolve(),
        "matrix_run": Path(__file__).resolve().with_name("matrix_run.py"),
        "validate_run": Path(__file__).resolve().with_name("validate_run.py"),
        "run_identity": Path(__file__).resolve().with_name("run_identity.py"),
    }

    def label(path: Path) -> str:
        resolved = path.resolve()
        try:
            return str(resolved.relative_to(repo_root))
        except ValueError:
            return path.name

    return {
        "schema_version": "agentfit.pre-run-provenance/v1",
        "capture_timing": "pre_run",
        "run_id": args.run_id,
        "terminal_prefix": terminal_prefix,
        "source_version": args.source_version,
        "files": {
            role: {"label": label(path), "sha256": sha256_bytes(path.read_bytes())}
            for role, path in files.items()
        },
        "generated": {
            "samples_json_sha256": sha256_bytes(batch_text.encode("utf-8")),
            "request_markdown_sha256": sha256_bytes(request.encode("utf-8")),
        },
    }


def main() -> int:
    args = parse_args()
    try:
        tasks = load_tasks(args.tasks_file)
        require_run_id(args.run_id)
        terminal_prefix = new_terminal_prefix(args.run_id)
        batch = select_samples(tasks, args.task_id, args.source_version)
        policy = args.policy_file.read_text(encoding="utf-8")
        manifest_bytes = args.manifest_file.read_bytes()
        batch["source_tasks_sha256"] = sha256_bytes(args.tasks_file.read_bytes())
        batch["policy_sha256"] = sha256_bytes(policy.encode("utf-8"))
        batch["agentteams_manifest_sha256"] = sha256_bytes(manifest_bytes)
        request = render_request(
            args.run_id,
            terminal_prefix,
            args.source_version,
            batch,
            policy,
            phase=args.phase,
        )
        if "evaluation_criteria" in json.dumps(batch, ensure_ascii=False):
            raise ValueError("sanitized batch still contains evaluation criteria")
        batch_text = json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
        write_private(
            args.output_dir / "samples.json",
            batch_text,
        )
        write_private(args.output_dir / "request.md", request)
        write_private(
            args.output_dir / "provenance.json",
            json.dumps(
                provenance_document(args, terminal_prefix, request, batch_text),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 1

    print(f"run_id={args.run_id}")
    print(f"sample_count={len(batch['samples'])}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
