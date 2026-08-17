"""Canonical solution and evidence package export."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from ..models.sample import canonical_hash
from ..models.solution import Solution
from ..store.run_store import RunStore


def export_package(solution: Solution, run_dir: str | Path,
                   monitoring_config: dict | None = None,
                   delivery_conditions: list[str] | tuple[str, ...] | None = None) -> Path:
    """导出可部署方案包（solution_package/，与 RunStore 同级消费）。"""
    store = RunStore(run_dir)
    pkg = {
        "agent_config": {"topology": asdict(solution.L4_topology),
                         "trigger_mode": solution.L4_topology.trigger_mode},
        "solid_atoms": [asdict(atom) for atom in solution.L1_atoms],
        "tool_bindings": [asdict(tool) for tool in solution.L2_tools],
        "knowledge": [asdict(item) for item in solution.L3_knowledge if not item.superseded],
        "routing_rules": [{"id": r.id, "condition": r.condition, "dispatches_to": r.dispatches_to}
                          for r in solution.L3_knowledge if r.type == "routing_rule" and not r.superseded],
        "human_gates": [asdict(tool.human_gate) for tool in solution.L2_tools if tool.human_gate],
        "delivery_conditions": list(delivery_conditions or ()),
        "monitoring_config": monitoring_config or {"pass_rate_alert": "-5%", "drift_alert": "15%", "retrain": "manual"},
        "boundary_analysis": analyze_boundary(store.root),
    }
    pkg["package_manifest"] = {
        "schema": "agentfit.solution-package",
        "content_hash": canonical_hash(pkg),
    }
    out = store.root / "solution_package" / "package.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pkg, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def analyze_boundary(run_dir: str | Path) -> dict:
    """Compatibility import for callers of the original package module."""
    from .boundary import analyze_boundary as _analyze
    return _analyze(run_dir)


def export_evidence_package(run_dir: str | Path) -> Path:
    """Hash every immutable run artifact into a separate evidence manifest."""
    root = Path(run_dir)
    files: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(("solution_package/", "evidence_package/")):
            continue
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "schema": "agentfit.evidence-package",
        "files": files,
        "content_hash": canonical_hash(files),
    }
    out = root / "evidence_package" / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
