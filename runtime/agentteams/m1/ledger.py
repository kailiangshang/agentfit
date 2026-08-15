#!/usr/bin/env python3
"""RoundRecord / ScenarioLedger: the AgentFit training-log analog.

Each round appends a record whose `prev_record_sha256` chains to the
previous one; a broken chain is unauditable by definition. Round metrics
are computed from the run's own artifacts (conversation trace, usage
snapshots) - never from chat claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

LEDGER_SCHEMA = "agentfit.scenario-ledger/v1"
RECORD_SCHEMA = "agentfit.round-record/v1"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True))


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": LEDGER_SCHEMA, "records": []}
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        raise SystemExit(f"ledger schema drift: {ledger.get('schema_version')}")
    return ledger


def verify_chain(ledger: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = ledger.get("records", [])
    prev = None
    for index, record in enumerate(records):
        if record.get("schema_version") != RECORD_SCHEMA:
            errors.append(f"record {index}: schema drift")
        body = dict(record)
        claimed_self = body.pop("record_sha256", None)
        computed_self = _sha256_json(body)
        if claimed_self != computed_self:
            errors.append(f"record {index}: self hash mismatch")
        claimed_prev = body.get("prev_record_sha256")
        if index == 0:
            if claimed_prev is not None:
                errors.append("record 0: prev hash must be null")
        elif claimed_prev != prev:
            errors.append(f"record {index}: chain break")
        prev = claimed_self
    return errors


def compute_metrics(run_dir: Path, run_id: str) -> dict[str, Any]:
    conversation = run_dir / "conversation.json"
    metrics: dict[str, Any] = {
        "events": None, "per_role": {}, "terminal_messages": 0,
        "tokens": None, "calls": None,
    }
    if conversation.is_file():
        document = json.loads(conversation.read_text(encoding="utf-8"))
        events = document if isinstance(document, list) else document.get("events", [])
        metrics["events"] = len(events)
        per_role: dict[str, int] = {}
        for event in events:
            sender = event.get("sender", "?").split(":")[0].replace("@agentfit-", "")
            per_role[sender] = per_role.get(sender, 0) + 1
        metrics["per_role"] = per_role
        metrics["terminal_messages"] = sum(
            1
            for event in events
            if event.get("room") == "leader_dm"
            and event.get("sender", "").startswith("@agentfit-engagement-lead")
            and str(event.get("body", "")).startswith(f"AGENTFIT-{run_id}")
        )
    before = run_dir / "usage-before.json"
    after = run_dir / "usage-after.json"
    if before.is_file() and after.is_file():
        b = json.loads(before.read_text(encoding="utf-8"))["totals"]
        a = json.loads(after.read_text(encoding="utf-8"))["totals"]
        metrics["tokens"] = a["total_tokens"] - b["total_tokens"]
        metrics["calls"] = a["call_count"] - b["call_count"]
    return metrics


def build_record(
    run_id: str,
    lifecycle_position: str,
    metrics: dict[str, Any],
    findings: list[dict[str, str]],
    design_changes: list[dict[str, str]],
    evidence_refs: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": RECORD_SCHEMA,
        "round_id": run_id,
        "recorded_at_ms": int(time.time() * 1000),
        "lifecycle_position": lifecycle_position,
        "metrics": metrics,
        "findings": findings,
        "design_changes": design_changes,
        "evidence_refs": evidence_refs,
    }


def append(ledger_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    ledger = load_ledger(ledger_path)
    errors = verify_chain(ledger)
    if errors:
        raise SystemExit("refusing to append to broken chain: " + "; ".join(errors))
    records = ledger.get("records", [])
    record = dict(record)
    record["prev_record_sha256"] = (
        records[-1]["record_sha256"] if records else None
    )
    record["record_sha256"] = _sha256_json(record)
    ledger.setdefault("records", []).append(record)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify the hash chain")
    verify.add_argument("--ledger", type=Path, required=True)

    show = sub.add_parser("show", help="print the ledger")
    show.add_argument("--ledger", type=Path, required=True)

    args = parser.parse_args()
    ledger = load_ledger(args.ledger)
    if args.command == "show":
        json.dump(ledger, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    errors = verify_chain(ledger)
    for error in errors:
        print(f"CHAIN ERROR: {error}", file=sys.stderr)
    print(
        f"chain ok: {len(ledger.get('records', []))} records"
        if not errors else "chain broken"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
