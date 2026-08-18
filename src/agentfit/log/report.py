"""报告生成（简版）：RunStore → Markdown 训练报告。"""
from __future__ import annotations

from pathlib import Path

from ..store.run_store import RunStore


_PURPOSES = (
    "adaptation", "validation", "sealed_holdout", "stress_and_failure",
)


def _training_acceptance_lines(store: RunStore, summary: dict) -> list[str]:
    evaluation = summary.get("evaluation_by_purpose") or {}
    objective = (
        store.load_json("objective.json")
        if (store.root / "objective.json").exists() else {}
    )
    acceptance = (
        store.load_json("acceptance.json")
        if (store.root / "acceptance.json").exists() else {}
    )
    decision = (
        store.load_json("delivery_decision.json")
        if (store.root / "delivery_decision.json").exists() else {}
    )
    criteria = {
        item.get("purpose"): item
        for item in objective.get("criteria", [])
        if isinstance(item, dict)
    }
    acceptance_state = (
        "PASS" if acceptance.get("met") is True
        else "REJECT" if acceptance.get("met") is False
        else "PENDING"
    )
    g3_state = (
        "APPROVED" if decision.get("approved") is True
        else "REJECTED" if decision.get("approved") is False
        else "PENDING"
    )
    lines = [
        "## 四集合验收", "",
        f"- 验收结论：**{acceptance_state}**",
        f"- G3 交付：**{g3_state}**",
    ]
    if objective.get("content_hash"):
        lines.append(f"- ObjectiveRef：`{objective['content_hash']}`")
    if acceptance.get("content_hash"):
        lines.append(f"- AcceptanceRef：`{acceptance['content_hash']}`")
    lines += [
        "",
        "| 集合 | 通过率 | PASS / FAIL / ERROR | 成本 | 风险事件 | 验收门槛 | 结果 |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    criteria_met = acceptance.get("criteria_met") or {}
    for purpose in _PURPOSES:
        metrics = evaluation.get(purpose) or {}
        criterion = criteria.get(purpose) or {}
        rate = metrics.get("pass_rate")
        rate_text = f"{rate:.0%}" if isinstance(rate, (int, float)) else "—"
        counts = " / ".join(
            str(metrics.get(key, "—")) for key in ("passed", "failed", "errors")
        )
        if criterion:
            threshold = (
                f"通过率≥{criterion.get('min_pass_rate', 0):.0%}; "
                f"ERROR≤{criterion.get('max_errors', 0)}; "
                f"成本≤${criterion.get('max_cost_usd', 0)}; "
                f"风险≤{criterion.get('max_risk_events', 0)}"
            )
        else:
            threshold = "未定义"
        result = (
            "PASS" if criteria_met.get(purpose) is True
            else "REJECT" if criteria_met.get(purpose) is False
            else "PENDING"
        )
        lines.append(
            f"| {purpose} | {rate_text} | {counts} | "
            f"${metrics.get('cost_usd', 0)} | {metrics.get('risk_events', 0)} | "
            f"{threshold} | {result} |"
        )
    failures = acceptance.get("failures") or summary.get("acceptance_failures") or []
    if failures:
        lines += ["", "### 未满足条件", ""]
        lines.extend(f"- `{failure}`" for failure in failures)
    return lines


def generate_report(run_dir: str | Path) -> Path:
    store = RunStore(run_dir)
    s = store.load_json("summary.json") if (store.root / "summary.json").exists() else {}
    run = store.load_json("run.json") if (store.root / "run.json").exists() else {}
    if run.get("run_kind") == "external_evaluation":
        evaluation = s.get("evaluation") or {}
        candidate = store.load_json("candidate_manifest.json")
        lines = [
            f"# AgentFit 外部评价报告 · {store.root.name}", "",
            "## 证据边界", "",
            "- 类型：外部评价，不是 AgentFit 训练运行",
            f"- 候选：`{candidate.get('candidate_id')}`",
            f"- CandidateRef：`{s.get('candidate_ref')}`",
            f"- 候选 provenance：{'完整' if candidate.get('provenance_complete') else '不完整'}",
            f"- 外部证据记录：{s.get('evidence_records', 0)}",
            f"- 证据链根：`{s.get('evidence_chain_root')}`", "",
            "## 评价结果", "",
            f"- 通过率：**{evaluation.get('pass_rate', 0):.0%}**",
            f"- PASS / FAIL / ERROR：{evaluation.get('passed', 0)} / "
            f"{evaluation.get('failed', 0)} / {evaluation.get('errors', 0)}",
            f"- 总成本：${evaluation.get('cost_usd', 0)}",
            f"- 风险事件：{evaluation.get('risk_events', 0)}", "",
            "> 该报告只证明持久化外部结果内部一致；候选 provenance 不完整时，"
            "不能据此证明完整模型、Prompt、工具或运行环境身份。",
        ]
        out = store.root / "evaluation_report.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        return out
    lines = [f"# AgentFit 训练报告 · {store.root.name}", ""]

    if s:
        final_pass_rate = s.get("final_pass_rate")
        pass_rate_text = (
            f"{final_pass_rate:.0%}"
            if isinstance(final_pass_rate, (int, float)) else "—"
        )
        lines += ["## 训练结果", "",
                  f"- 训练批次通过率：**{pass_rate_text}**（方案证据版本 {s.get('final_solution_version')}）",
                  f"- 训练轮数：{s.get('epochs_run')} · 收敛：{'是' if s.get('converged') else '否'}",
                  f"- 总成本：${s.get('total_cost_usd', 0)} · 哈希链：{'✓ 可验证' if s.get('log_chain_valid') else '✗'}",
                  f"- λ 终值：{s.get('lambda_values')}", ""]
        if final_pass_rate is None:
            lines += ["> 无有效方案评测：执行结果均未进入可归因的 L1–L4 方案评测。", ""]
        lines += _training_acceptance_lines(store, s) + [""]

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
