"""交付（简版）：方案打包 + 适用边界分析。对应 test-scenario.md §六交付树。"""
from __future__ import annotations

from pathlib import Path

from ..models.solution import Solution
from ..store.run_store import RunStore


def export_package(solution: Solution, run_dir: str | Path, monitoring_config: dict | None = None) -> Path:
    """导出可部署方案包（solution_package/，与 RunStore 同级消费）。"""
    store = RunStore(run_dir)
    pkg = {
        "agent_config": {"topology": solution.L4_topology.agents,
                         "trigger_mode": solution.L4_topology.trigger_mode},
        "tool_bindings": [{"tool": t.id, "wraps": t.wraps,
                           "human_gate": t.human_gate.condition if t.human_gate else None}
                          for t in solution.L2_tools],
        "routing_rules": [{"id": r.id, "condition": r.condition, "dispatches_to": r.dispatches_to}
                          for r in solution.L3_knowledge if r.type == "routing_rule" and not r.superseded],
        "human_gates": [g for g in ({t.human_gate.reviewer for t in solution.L2_tools if t.human_gate})],
        "monitoring_config": monitoring_config or {"pass_rate_alert": "-5%", "drift_alert": "15%", "retrain": "manual"},
    }
    out = store.root / "solution_package" / "package.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(__import__("json").dumps(pkg, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return out


def analyze_boundary(run_dir: str | Path) -> dict:
    """适用边界：哪些能自动 / 哪些留人工 / 为什么（LossTrace + 样本统计）。"""
    store = RunStore(run_dir)
    human_samples, eval_errors, automated = [], [], []
    for e in store.epochs():
        lt_dir = store.root / "loss_traces" / f"epoch_{e:03d}"
        if not lt_dir.is_dir():
            continue
        for p in lt_dir.glob("*.json"):
            lt = store.load_json(f"loss_traces/epoch_{e:03d}/{p.name}")
            if lt["root_cause_layer"] == "human":
                human_samples.append(lt["sample_id"])
            elif lt["root_cause_layer"] == "eval_error":
                eval_errors.append(lt["sample_id"])
    samples = store.load_json("samples.json") if (store.root / "samples.json").exists() else {"total": 0}
    human_unique = sorted(set(human_samples))
    auto = samples.get("total", 0) - len(human_unique)
    coverage = auto / max(1, samples.get("total", 1))
    delivery = ("全自动" if coverage >= 0.95 and not human_unique else
                "部分自动" if coverage >= 0.7 else
                "降级" if coverage >= 0.5 else "保留人工")
    return {"automated": auto, "human_required": human_unique,
            "eval_errors": sorted(set(eval_errors)), "coverage": round(coverage, 3),
            "recommended_delivery": delivery,
            "reason": f"自动化覆盖 {coverage:.0%}；人工项均有归因证据"}
