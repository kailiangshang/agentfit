#!/usr/bin/env python3
"""Independent SampleSetManifest verification (S5 independent-audit).

Generalized from the R4 improvised verify_hashes.py. Recomputes every set
hash from the supplied batch (independent implementation of the frozen
hash recipe), checks uniqueness, batch membership, and - when entity
groups are supplied - that no entity group spans evaluation splits.
Verdict is machine-readable; failures are failures, never warnings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_NAMES = ("adaptation", "validation", "sealed_holdout", "stress_and_failure")


def recompute(batch: dict[str, str], member_ids: list[str]) -> str:
    ordered = sorted(member_ids)
    concat = "".join(batch[i] for i in ordered)
    return hashlib.sha256(concat.encode("ascii")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--entity-groups", type=Path, default=None)
    args = parser.parse_args()

    batch_doc = json.loads(args.batch.read_text(encoding="utf-8"))
    batch = {
        str(s["sample_id"]): s["source_record_sha256"] for s in batch_doc["samples"]
    }
    manifests = json.loads(args.manifests.read_text(encoding="utf-8"))
    if isinstance(manifests, dict):
        for value in manifests.values():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "manifest_name" in value[0]:
                manifests = value
                break
        else:
            if "manifests" in manifests:
                manifests = manifests["manifests"]
            else:
                manifests = {m.get("manifest_name"): m for m in [] }
    if isinstance(manifests, list):
        manifests = {m.get("manifest_name"): m for m in manifests if isinstance(m, dict)}

    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> bool:
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    ok = True
    sample_owner: dict[str, str] = {}
    group_owner: dict[str, str] = {}
    groups: dict[str, list[str]] = {}
    if args.entity_groups is not None:
        groups = json.loads(args.entity_groups.read_text(encoding="utf-8"))
        if isinstance(groups, dict) and "groups" in groups:
            groups = groups["groups"]

    for name in MANIFEST_NAMES:
        manifest = manifests.get(name)
        if manifest is None:
            ok &= record(f"{name}.present", False, "manifest missing")
            continue
        if manifest.get("contract_status") == "not_instantiated":
            reason = manifest.get("not_instantiated_reason", "")
            ok &= record(
                f"{name}.not_instantiated_justified",
                bool(reason.strip()),
                reason or "missing justification",
            )
            continue
        members = manifest.get("membership", [])
        ids = [str(m["sample_id"]) for m in members]
        unknown = [i for i in ids if i not in batch]
        ok &= record(f"{name}.members_in_batch", not unknown, f"unknown: {unknown}")
        claimed = manifest.get("set_hash", {}).get("set_model_sha256", "")
        computed = recompute(batch, ids) if not unknown else ""
        ok &= record(
            f"{name}.set_hash_match",
            bool(claimed) and claimed == computed,
            f"claimed={claimed[:16]}… computed={computed[:16]}…",
        )
        for m in members:
            sid = str(m["sample_id"])
            if sid in sample_owner:
                ok &= record(
                    f"{name}.no_cross_manifest_duplicate",
                    False,
                    f"sample {sid} also in {sample_owner[sid]}",
                )
            else:
                sample_owner[sid] = name
            entity = m.get("entity_group")
            if entity:
                if entity in group_owner and group_owner[entity] != name:
                    ok &= record(
                        f"{name}.no_entity_span",
                        False,
                        f"entity {entity} also in {group_owner[entity]}",
                    )
                else:
                    group_owner[entity] = name

    coverage = sorted(set(batch) - set(sample_owner))
    record(
        "batch_coverage_report",
        True,
        f"unassigned sample ids: {coverage}",
    )

    result = {
        "schema_version": "agentfit.audit-manifest-check/v1",
        "verdict": "PASS" if ok else "FAIL",
        "minimum_next_action": (
            "proceed_to_freeze_review" if ok else "fix_manifest_membership_before_freeze"
        ),
        "freeze_permitted_by_checks": ok,
        "checks": checks,
    }
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
