#!/usr/bin/env python3
"""桥接：AgentTeams 运行结果 → AgentFit Trace 格式（进回归池/重训练分析）。

用法：
  PYTHONPATH=src python bridges/agentteams/import_results.py results.json -o traces.json
输入格式（AgentTeams 侧导出，按平台实际调整解析，不动库）：
  [{"sample_id": "...", "success": true/false, "tool_calls": ["safe_x", ...], "error": null}]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def convert(at_results: list[dict]) -> list[dict]:
    traces = []
    for r in at_results:
        steps = [{"layer": "L2", "element_id": tool, "ok": True} for tool in r.get("tool_calls", [])]
        if r.get("error"):
            steps.append({"layer": "L2", "element_id": r.get("failed_tool", "-"),
                          "ok": False, "error": r["error"]})
        traces.append({"sample_id": r["sample_id"],
                       "result": "PASS" if r.get("success") else "FAIL",
                       "steps": steps,
                       "routed_knowledge_id": r.get("route_id")})
    return traces


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="traces.json")
    args = parser.parse_args()
    traces = convert(json.loads(Path(args.input).read_text(encoding="utf-8")))
    Path(args.output).write_text(json.dumps(traces, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"converted {len(traces)} traces → {args.output}")


if __name__ == "__main__":
    main()
