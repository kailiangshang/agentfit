#!/usr/bin/env python3
"""Render the AgentTeams Team artifact from canonical AgentFit Skills."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from agentfit.models.sample import canonical_hash  # noqa: E402
from agentfit.skills.registry import SkillRegistry  # noqa: E402


ROLE_SPECS = {
    "steward": {
        "name": "agentfit-steward",
        "identity": "User-facing material intake, clarification and evidence-based explanation.",
        "skills": ("intake", "clarify", "explain"),
    },
    "attributor": {
        "name": "agentfit-attributor",
        "identity": "Bottom-up failure attribution with explicit confidence and no solution mutation.",
        "skills": ("attribution",),
    },
    "architect": {
        "name": "agentfit-architect",
        "identity": "Simple-first candidate design and evidence-backed change proposals.",
        "skills": ("bootstrap", "aggregation", "proposal", "cascade"),
    },
}
PLATFORM_CONTRACT = "hiclaw-v1.1.2-inline-team"


def _role_payload(role: str, model: str, registry: dict, *, runtime: bool) -> dict:
    spec = ROLE_SPECS[role]
    sections = [
        f"# AgentFit {role.title()}",
        "",
        "## AI Identity",
        "",
        "You are an AI Agent, not a human.",
        "",
        "## Role Boundary",
        "",
        spec["identity"],
        "",
        "Never reveal API keys, passwords, or credentials. Do not invent evidence.",
        "",
        "## Canonical Skills",
    ]
    for skill_name in spec["skills"]:
        sections.extend(("", registry[skill_name].content))
    payload = {
        "name": spec["name"],
        "model": model,
        "state": "Running",
        "workerName": spec["name"],
        "identity": spec["identity"],
        "soul": "\n".join(sections),
    }
    if runtime:
        payload["runtime"] = "copaw"
    return payload


def render_resources(model: str = "deepseek/deepseek-chat") -> dict:
    """Render the single inline Team resource accepted by HiClaw v1.1.2."""
    registry = SkillRegistry().load()
    used = sorted({name for spec in ROLE_SPECS.values() for name in spec["skills"]})
    registry_hash = canonical_hash([(name, registry[name].content_hash) for name in used])
    annotations = {
        "agentfit.io/registry-hash": registry_hash,
        "agentfit.io/source": "bridges/agentteams/render_team.py",
        "agentfit.io/model-ref": model,
        "agentfit.io/platform-contract": PLATFORM_CONTRACT,
    }
    return {
        "apiVersion": "hiclaw.io/v1beta1",
        "kind": "Team",
        "metadata": {
            "name": "agentfit",
            "annotations": annotations,
        },
        "spec": {
            "teamName": "agentfit",
            "description": (
                "AgentFit cognitive bridge team. Steward, Attributor and Architect run on "
                "AgentTeams; Orchestrator, Validator and Auditor remain deterministic core code."
            ),
            "peerMentions": False,
            "leader": _role_payload("steward", model, registry, runtime=False),
            "workers": [
                _role_payload(role, model, registry, runtime=True)
                for role in ("attributor", "architect")
            ],
        },
    }


def render_manifest(model: str = "deepseek/deepseek-chat") -> dict:
    """Compatibility alias for the canonical single Team resource."""
    return render_resources(model)


def render_text(model: str = "deepseek/deepseek-chat") -> str:
    """Emit JSON, which is valid YAML for ``hiclaw apply -f``."""
    return json.dumps(render_resources(model), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek/deepseek-chat")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("team.yaml"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_text(args.model)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            print(f"generated Team artifact is stale: {args.output}", file=sys.stderr)
            return 1
        print(f"generated Team artifact is current: {args.output}")
        return 0
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
