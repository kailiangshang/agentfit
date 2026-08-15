#!/usr/bin/env python3
"""Deterministic SampleSetManifest set-hash computation (S1 task-compile).

Generalized from the R4 improvised compute_hashes.py. The set hash is
SHA-256 over the concatenation of member source_record_sha256 hex strings
in ascending sample_id order - computed from the supplied batch, never
invented. Any drift, missing member, or duplicate assignment is a hard
error: emit not_instantiated plus the reason instead of guessing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_NAMES = ("adaptation", "validation", "sealed_holdout", "stress_and_failure")


def load_batch(path: Path) -> dict[str, str]:
    batch = json.loads(path.read_text(encoding="utf-8"))
    if batch.get("schema_version") != "agentfit.projectcase-source-batch/v1":
        raise SystemExit(f"batch schema drift: {batch.get('schema_version')}")
    members: dict[str, str] = {}
    for sample in batch["samples"]:
        sample_id = str(sample["sample_id"])
        record_hash = sample.get("source_record_sha256", "")
        if len(record_hash) != 64 or any(c not in "0123456789abcdef" for c in record_hash):
            raise SystemExit(f"sample {sample_id} lacks a valid source_record_sha256")
        if sample_id in members:
            raise SystemExit(f"duplicate sample id in batch: {sample_id}")
        members[sample_id] = record_hash
    return members


def set_hash(batch: dict[str, str], member_ids: list[str]) -> dict:
    ordered = sorted(member_ids)
    missing = [i for i in ordered if i not in batch]
    if missing:
        raise SystemExit(f"members not present in batch: {missing}")
    concat = "".join(batch[i] for i in ordered)
    return {
        "member_order": ordered,
        "concat_length": len(concat),
        "set_model_sha256": hashlib.sha256(concat.encode("ascii")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument(
        "--members",
        action="append",
        default=[],
        help="membership as name=id,id,... (repeatable); manifests left out stay not_instantiated",
    )
    args = parser.parse_args()

    batch = load_batch(args.batch)
    assigned: list[str] = []
    output: dict[str, object] = {
        "schema_version": "agentfit.samplesetmanifest-sethash/v1",
        "batch_sample_count": len(batch),
        "manifests": {},
    }
    for spec in args.members:
        name, _, raw = spec.partition("=")
        if name not in MANIFEST_NAMES:
            raise SystemExit(f"unknown manifest name: {name}")
        ids = [i.strip() for i in raw.split(",") if i.strip()]
        seen = set()
        for i in ids:
            if i in seen:
                raise SystemExit(f"duplicate member {i} within {name}")
            seen.add(i)
            if i in assigned:
                raise SystemExit(f"member {i} assigned to more than one manifest")
            assigned.append(i)
        output["manifests"][name] = {"status": "instantiated", **set_hash(batch, ids)}
    for name in MANIFEST_NAMES:
        if name not in output["manifests"]:
            output["manifests"][name] = {
                "status": "not_instantiated",
                "reason": "no membership supplied for this manifest",
            }
    output["unassigned_sample_ids"] = sorted(set(batch) - set(assigned))
    json.dump(output, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
