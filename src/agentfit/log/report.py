"""报告生成（简版）：RunStore → Markdown 训练报告。"""
from __future__ import annotations

from pathlib import Path

from ..store.run_store import RunStore


def generate_report(run_dir: str | Path) -> Path:
    store = RunStore(run_dir)
    s = store.load_json("summary.json") if (store.root / "summary.json").exists() else {}
    lines = [f"# AgentFit 训练报告 · {store.root.name}", ""]

    if s:
        lines += ["## 结果", "",
                  f"- 最终通过率：**{s.get('final_pass_rate', 0):.0%}**（方案 v{s.get('final_solution_version')}）",
                  f"- 训练轮数：{s.get('epochs_run')} · 收敛：{'是' if s.get('converged') else '否'}",
                  f"- 总成本：${s.get('total_cost_usd', 0)} · 哈希链：{'✓ 可验证' if s.get('log_chain_valid') else '✗'}",
                  f"- λ 终值：{s.get('lambda_values')}", ""]

    lines += ["## 各轮概览", "", "| epoch | 通过率 | 更新数 | 回滚 |", "|---|---|---|---|"]
    for e in store.epochs():
        rec = store.load_json(f"epochs/epoch_{e:03d}.json")["entry"]
        lines.append(f"| {rec['epoch']} | {rec['pass_rate']:.0%} | {len(rec['updates_applied'])} |"
                     f" {'是' if rec['rolled_back'] else '否'} |")

    lines += ["", "## 版本演化", ""]
    for v in store.solution_versions():
        meta = store.load_json(f"solution_versions/v{v:03d}.json")
        so = meta["solution"]
        lines.append(f"- **v{v}** {meta.get('note', '')} — L1×{len(so['L1_atoms'])} L2×{len(so['L2_tools'])}"
                     f" L3×{len(so['L3_knowledge'])} Agent×{len(so['L4_topology']['agents'])}")

    tx = s.get("transactions_committed", [])
    if tx:
        lines += ["", "## 提交的事务", ""]
        for t in tx:
            for c in t["changes"]:
                lines.append(f"- v{t['version']} [{c['layer']}/{c['action']}] {c['element']} — {c.get('reason', '')}")

    out = store.root / "training_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
