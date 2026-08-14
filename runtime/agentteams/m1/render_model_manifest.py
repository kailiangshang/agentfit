#!/usr/bin/env python3
"""Render a private AgentTeams manifest with one operator-selected model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?im)^\s*(?:api[_-]?key|password|secret|token)\s*:\s*(?!<|$)\S+"
)
DIRECT_SECRET = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{16,}|\bBearer\s+[A-Za-z0-9._-]{20,})"
)
REPO_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_ROOT = REPO_ROOT / ".local-demo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--model", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
        path.chmod(0o600)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def private_json(path: Path, value: dict[str, Any]) -> None:
    private_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def require_private_output(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT.resolve())
    except ValueError as error:
        raise ValueError("output file must be inside the repository .local-demo directory") from error
    return resolved


def render(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Any]]:
    if not MODEL_ID.fullmatch(args.model):
        raise ValueError("model must be a non-placeholder OpenAI-compatible model id")

    source = args.input_file.resolve()
    output = require_private_output(args.output_file)
    if source == output:
        raise ValueError("output file must not overwrite the source manifest")
    if not source.is_file():
        raise ValueError(f"input manifest does not exist: {source}")

    source_text = source.read_text(encoding="utf-8")
    if CREDENTIAL_ASSIGNMENT.search(source_text) or DIRECT_SECRET.search(source_text):
        raise ValueError("input manifest contains a credential-like value")
    documents = list(yaml.safe_load_all(source_text))
    if not documents or not all(isinstance(document, dict) for document in documents):
        raise ValueError("input manifest must contain only YAML objects")
    teams = [document for document in documents if document.get("kind") == "Team"]
    if len(teams) != 1:
        raise ValueError("input manifest must contain exactly one Team")

    team = teams[0]
    spec = team.get("spec")
    if not isinstance(spec, dict):
        raise ValueError("Team spec must be an object")
    leader = spec.get("leader")
    workers = spec.get("workers")
    if not isinstance(leader, dict) or not isinstance(workers, list) or not workers:
        raise ValueError("Team must contain one leader and a non-empty workers list")
    if not all(isinstance(worker, dict) for worker in workers):
        raise ValueError("every Team worker must be an object")

    leader["model"] = args.model
    for worker in workers:
        worker["model"] = args.model

    rendered_text = yaml.safe_dump_all(
        documents,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    private_write(output, rendered_text)
    provenance_path = output.with_suffix(output.suffix + ".provenance.json")
    provenance = {
        "schema_version": "agentfit.model-manifest-render/v1",
        "source_manifest": str(source.relative_to(REPO_ROOT)),
        "rendered_manifest": str(output.relative_to(REPO_ROOT)),
        "model": args.model,
        "changed_member_count": 1 + len(workers),
        "source_manifest_sha256": sha256(source),
        "rendered_manifest_sha256": sha256(output),
        "renderer_sha256": sha256(Path(__file__)),
        "contains_credentials": False,
    }
    private_json(provenance_path, provenance)
    return output, provenance_path, provenance


def main() -> int:
    args = parse_args()
    try:
        output, provenance_path, provenance = render(args)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"model={provenance['model']}")
    print(f"changed_member_count={provenance['changed_member_count']}")
    print(f"private_manifest={output}")
    print(f"private_provenance={provenance_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
