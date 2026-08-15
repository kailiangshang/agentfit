#!/usr/bin/env python3
"""Lifecycle gate checks (v1): stage completion = structured artifact passes schema.

Implements a stdlib-only validator for the schema subset AgentFit uses
(const / enum / required / type / pattern / properties / allOf-if-then)
plus the Freeze gate: all four SampleSetManifests must be schema-valid
and the audit verdict must be PASS before Human freeze review opens.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "s1-task-compile" / "schema" / "sample-set-manifest.schema.json"
)
MANIFEST_NAMES = ("adaptation", "validation", "sealed_holdout", "stress_and_failure")

STAGES = (
    "Intake", "Discover", "Freeze", "Architect", "Approve",
    "Trial", "Audit", "Deliver", "Learn",
)
ALLOWED_TRANSITIONS = {
    "Intake": ("Discover",),
    "Discover": ("Freeze",),
    "Freeze": ("Architect",),          # only via freeze gate
    "Architect": ("Approve",),
    "Approve": ("Trial",),
    "Trial": ("Audit",),
    "Audit": ("Deliver",),
    "Deliver": ("Learn",),
    "Learn": ("Discover",),            # next continual-learning cycle
}


def transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, ())


# ---------------------------------------------------------------- schema-lite

def validate(instance: Any, schema: dict) -> list[str]:
    errors: list[str] = []

    def fail(msg: str) -> None:
        errors.append(msg)

    def check(value: Any, node: dict, path: str) -> None:
        if "const" in node and value != node["const"]:
            fail(f"{path}: must be {node['const']!r}")
        if "enum" in node and value not in node["enum"]:
            fail(f"{path}: {value!r} not in {node['enum']}")
        declared = node.get("type")
        if declared == "object":
            if not isinstance(value, dict):
                fail(f"{path}: expected object")
                return
            for key in node.get("required", []):
                if key not in value:
                    fail(f"{path}: missing required '{key}'")
            properties = node.get("properties", {})
            for key, sub in properties.items():
                if key in value:
                    check(value[key], sub, f"{path}.{key}")
        elif declared == "array":
            if not isinstance(value, list):
                fail(f"{path}: expected array")
                return
            items = node.get("items")
            if items:
                for index, item in enumerate(value):
                    check(item, items, f"{path}[{index}]")
        elif declared == "string":
            if not isinstance(value, str):
                fail(f"{path}: expected string")
                return
            if "minLength" in node and len(value) < node["minLength"]:
                fail(f"{path}: shorter than minLength {node['minLength']}")
            if "pattern" in node and not re.fullmatch(node["pattern"], value):
                fail(f"{path}: does not match pattern {node['pattern']}")

    if not isinstance(instance, dict):
        return [f"{schema.get('$id', 'root')}: instance must be an object"]
    check(instance, schema, "manifest")
    for rule in schema.get("allOf", []):
        if_stmt = rule.get("if", {}).get("properties", {})
        then_req = rule.get("then", {}).get("required", [])
        match = all(
            instance.get(key) == cond.get("const")
            for key, cond in if_stmt.items()
            if "const" in cond
        )
        if match:
            for key in then_req:
                if key not in instance:
                    errors.append(f"manifest: conditional required '{key}' missing")
    return errors


# ---------------------------------------------------------------- freeze gate

def freeze_gate(
    manifests_path: Path,
    audit_path: Path | None = None,
    schema_path: Path = MANIFEST_SCHEMA_PATH,
) -> dict:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    document = json.loads(manifests_path.read_text(encoding="utf-8"))
    manifests: dict = {}
    if isinstance(document, list):
        manifests = {m.get("manifest_name"): m for m in document if isinstance(m, dict)}
    elif isinstance(document, dict):
        nested = None
        for value in document.values():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "manifest_name" in value[0]:
                nested = value
                break
        if nested is not None:
            manifests = {m.get("manifest_name"): m for m in nested}
        elif "manifests" in document:
            inner = document["manifests"]
            manifests = (
                {m.get("manifest_name"): m for m in inner}
                if isinstance(inner, list)
                else inner
            )
        else:
            manifests = document
    result: dict[str, Any] = {
        "schema_version": "agentfit.lifecycle-freeze-gate/v1",
        "checks": [],
        "freeze_ready": False,
    }

    def record(name: str, ok: bool, detail: str) -> bool:
        result["checks"].append(
            {"check": name, "result": "PASS" if ok else "FAIL", "detail": detail}
        )
        return ok

    ok = True
    for name in MANIFEST_NAMES:
        manifest = manifests.get(name)
        if manifest is None:
            ok &= record(f"{name}.present", False, "manifest missing")
            continue
        errors = validate(manifest, schema)
        ok &= record(f"{name}.schema", not errors, "; ".join(errors[:4]) or "valid")

    if audit_path is not None and audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        verdict = audit.get("verdict")
        ok &= record(
            "audit.verdict",
            verdict == "PASS",
            f"verdict={verdict}",
        )
        ok &= record(
            "audit.freeze_next_action",
            audit.get("minimum_next_action") == "proceed_to_freeze_review",
            f"minimum_next_action={audit.get('minimum_next_action')}",
        )
    else:
        ok &= record("audit.present", False, "audit decision artifact missing")

    result["freeze_ready"] = ok
    result["next_action"] = (
        "human_freeze_review" if ok else "fix_failures_before_freeze"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=None)
    args = parser.parse_args()
    result = freeze_gate(args.manifests, args.audit)
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0 if result["freeze_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
