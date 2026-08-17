#!/usr/bin/env python3
"""桥接：AgentFit Solution → AgentTeams 项目配置。

库外脚本：src/agentfit 对 AgentTeams 零感知（见 tests/test_decoupling.py 守护）。
用法：
  PYTHONPATH=src python bridges/agentteams/export_solution.py output/run-001 --version 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from agentfit.store.run_store import RunStore  # noqa: E402


def export(run_dir: str, version: int | None = None) -> dict:
    store = RunStore(run_dir)
    if not store.load_json("summary.json").get("delivery_approved"):
        raise SystemExit("G3 delivery approval is required before AgentTeams export")
    versions = store.solution_versions()
    if not versions:
        raise SystemExit("RunStore 无方案版本")
    v = version if version is not None else versions[-1]
    meta = store.load_json(f"solution_versions/v{v:03d}.json")
    so = meta["solution"]

    # AgentTeams 项目配置（目标格式示例；按平台实际 schema 调整此映射，不动库）
    return {
        "project": "agentfit",
        "agents": [{"id": a["id"], "role": a["role"], "knowledge": a["uses"]} for a in so["L4_topology"]["agents"]],
        "tools": [{"id": t["id"], "backend_atoms": t["wraps"],
                   "human_gate": t["human_gate"]["condition"] if t.get("human_gate") else None}
                  for t in so["L2_tools"]],
        "routing": [{"id": r["id"], "condition": r["condition"], "target": r["dispatches_to"]}
                    for r in so["L3_knowledge"] if r["type"] == "routing_rule" and not r.get("superseded")],
        "source": {"run_dir": str(store.root), "solution_version": v},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--version", type=int, default=None)
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    config = export(args.run_dir, args.version)
    out = Path(args.output) if args.output else Path(args.run_dir) / "agentteams_config.json"
    out.write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"agentteams config: {out}")


if __name__ == "__main__":
    main()
